#!/usr/bin/env python3
"""
m4b-tool wrapper for audiobook conversion
"""

import os
import subprocess
import sqlite3
import logging
import time
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from config import DB_PATH, M4B_TOOL_BITRATE, M4B_TOOL_CODEC, CONVERSION_TIMEOUT

logger = logging.getLogger(__name__)

class M4BConverter:
    """Wrapper around m4b-tool for audiobook conversion"""
    
    def __init__(self):
        self.db_path = DB_PATH
    
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn
    
    def find_mp3_files(self, input_path: str) -> List[str]:
        """
        Find all MP3 files in input directory
        
        Args:
            input_path: Path to search for MP3 files
            
        Returns:
            List of MP3 file paths
        """
        mp3_files = []
        input_dir = Path(input_path)
        
        if not input_dir.exists():
            logger.warning(f"Input path does not exist: {input_path}")
            return mp3_files
        
        # Recursively find all MP3 files
        for mp3_file in input_dir.rglob("*.mp3"):
            if mp3_file.is_file():
                mp3_files.append(str(mp3_file))
        
        logger.info(f"Found {len(mp3_files)} MP3 files in {input_path}")
        return mp3_files
    
    def get_book_name_from_path(self, input_path: str) -> str:
        """
        Extract book name from input path
        
        Args:
            input_path: Path to extract name from
            
        Returns:
            Book name
        """
        path = Path(input_path)
        # Use the directory name or filename as book name
        if path.is_dir():
            return path.name
        else:
            return path.stem
    
    def update_conversion_progress(self, book_name: str, status: str, 
                                 current_file: Optional[str] = None,
                                 progress_percentage: float = 0.0,
                                 total_files: int = 0,
                                 converted_files: int = 0):
        """
        Update conversion progress in database
        
        Args:
            book_name: Name of the book being converted
            status: Current conversion status
            current_file: Currently processing file
            progress_percentage: Progress percentage (0-100)
            total_files: Total number of files
            converted_files: Number of converted files
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check if record exists
            cursor.execute('SELECT id FROM conversion_tracking WHERE book_name = ?', (book_name,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute('''
                    UPDATE conversion_tracking 
                    SET status = ?, current_file = ?, progress_percentage = ?,
                        total_files = ?, converted_files = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE book_name = ?
                ''', (status, current_file, progress_percentage, total_files, converted_files, book_name))
            else:
                # Create new record
                cursor.execute('''
                    INSERT INTO conversion_tracking 
                    (book_name, status, current_file, progress_percentage, total_files, converted_files)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (book_name, status, current_file, progress_percentage, total_files, converted_files))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update conversion progress: {e}")
    
    def convert_audiobook(self, input_path: str, output_path: str, book_name: str) -> bool:
        """
        Convert audiobook using m4b-tool
        
        Args:
            input_path: Path to input MP3 files
            output_path: Path to output M4B file
            book_name: Name of the book
            
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            input_dir = Path(input_path)
            output_dir = Path(output_path)
            
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Find MP3 files
            mp3_files = self.find_mp3_files(input_path)
            if not mp3_files:
                logger.error(f"No MP3 files found in {input_path}")
                return False
            
            total_files = len(mp3_files)
            logger.info(f"Starting conversion of {book_name} with {total_files} files")
            
            # Update initial progress
            self.update_conversion_progress(
                book_name, "converting", "Starting conversion...", 0.0, total_files, 0
            )
            
            # Build m4b-tool command
            output_file = output_dir / f"{book_name}.m4b"
            
            cmd = [
                "m4b-tool", "merge",
                input_path,
                "--output-file", str(output_file),
                "--audio-bitrate", M4B_TOOL_BITRATE,
                "--audio-codec", M4B_TOOL_CODEC,
                "--no-chapter-reencoding",
                "--jobs", "1"  # Single job for better progress tracking
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Start conversion process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor progress
            converted_files = 0
            start_time = time.time()
            
            while True:
                # Check if process is still running
                if process.poll() is not None:
                    break
                
                # Check timeout
                if time.time() - start_time > CONVERSION_TIMEOUT:
                    logger.error(f"Conversion timeout after {CONVERSION_TIMEOUT} seconds")
                    process.terminate()
                    self.update_conversion_progress(
                        book_name, "failed", "Conversion timeout", 0.0, total_files, converted_files
                    )
                    return False
                
                # Read output line by line
                try:
                    line = process.stdout.readline()
                    if line:
                        logger.debug(f"m4b-tool: {line.strip()}")
                        
                        # Parse progress from output (basic parsing)
                        if "Processing" in line or "Converting" in line:
                            # Estimate progress based on time elapsed
                            elapsed = time.time() - start_time
                            estimated_total = elapsed * 1.2  # Rough estimate
                            progress = min((elapsed / estimated_total) * 100, 95)
                            
                            self.update_conversion_progress(
                                book_name, "converting", line.strip(), progress, total_files, converted_files
                            )
                        
                        # Check for completion indicators
                        if "completed" in line.lower() or "finished" in line.lower():
                            converted_files = total_files
                            break
                            
                except Exception as e:
                    logger.warning(f"Error reading process output: {e}")
                    break
                
                time.sleep(1)  # Small delay to prevent excessive CPU usage
            
            # Wait for process to complete
            return_code = process.wait()
            
            if return_code == 0:
                # Check if output file was created
                if output_file.exists():
                    logger.info(f"Conversion completed successfully: {output_file}")
                    self.update_conversion_progress(
                        book_name, "completed", None, 100.0, total_files, total_files
                    )
                    return True
                else:
                    logger.error(f"Conversion completed but output file not found: {output_file}")
                    self.update_conversion_progress(
                        book_name, "failed", "Output file not created", 0.0, total_files, converted_files
                    )
                    return False
            else:
                logger.error(f"Conversion failed with return code: {return_code}")
                self.update_conversion_progress(
                    book_name, "failed", f"Process failed with code {return_code}", 0.0, total_files, converted_files
                )
                return False
                
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            self.update_conversion_progress(
                book_name, "failed", str(e), 0.0, 0, 0
            )
            return False
    
    def get_conversion_status(self, book_name: str) -> Optional[Dict]:
        """
        Get current conversion status from database
        
        Args:
            book_name: Name of the book
            
        Returns:
            Dictionary with conversion status or None
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT status, current_file, progress_percentage, total_files, converted_files,
                       created_at, updated_at
                FROM conversion_tracking 
                WHERE book_name = ?
            ''', (book_name,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'status': result[0],
                    'current_file': result[1],
                    'progress_percentage': result[2],
                    'total_files': result[3],
                    'converted_files': result[4],
                    'created_at': result[5],
                    'updated_at': result[6]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get conversion status: {e}")
            return None
