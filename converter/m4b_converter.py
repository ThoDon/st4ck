#!/usr/bin/env python3
"""
m4b-tool wrapper for audiobook conversion
"""

import os
import subprocess
import sqlite3
import logging
import time
import shlex
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
        max_retries = 3
        for attempt in range(max_retries):
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
                return  # Success, exit retry loop
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Database locked, retrying in 1 second (attempt {attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
                else:
                    logger.error(f"Failed to update conversion progress after {max_retries} attempts: {e}")
                    break
            except Exception as e:
                logger.error(f"Failed to update conversion progress: {e}")
                break
    
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
            
            # Ensure input path exists
            if not input_dir.exists():
                logger.error(f"Input path does not exist: {input_path}")
                return False
            
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
            
            # Build m4b-tool command with relative paths
            output_file = output_dir / f"{book_name}.m4b"
            
            # Use absolute paths since the Docker wrapper mounts the entire root directory
            input_absolute = input_path + "/"
            output_absolute = str(output_file)
            
            # Debug: Check if the input directory exists and what's in it
            logger.info(f"Checking input directory: {input_path}")
            logger.info(f"Input directory exists: {input_dir.exists()}")
            if input_dir.exists():
                try:
                    files = list(input_dir.iterdir())
                    logger.info(f"Input directory contains {len(files)} items:")
                    for item in files:
                        logger.info(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")
                except Exception as e:
                    logger.error(f"Error listing input directory: {e}")
            
            # Debug: Check the absolute paths that will be used
            logger.info(f"Input absolute path: {input_absolute}")
            logger.info(f"Output absolute path: {output_absolute}")
            
            # Debug: Check what's in the toMerge directory
            test_cmd = ["bash", "-c", f"ls -la /toMerge/"]
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            logger.info(f"toMerge directory listing return code: {result.returncode}")
            logger.info(f"toMerge directory listing STDOUT: {result.stdout}")
            logger.info(f"toMerge directory listing STDERR: {result.stderr}")
            
            # Debug: Check what's in the specific book directory
            test_cmd2 = ["bash", "-c", f"ls -la {shlex.quote(input_absolute)}"]
            result2 = subprocess.run(test_cmd2, capture_output=True, text=True, timeout=10)
            logger.info(f"Book directory listing return code: {result2.returncode}")
            logger.info(f"Book directory listing STDOUT: {result2.stdout}")
            logger.info(f"Book directory listing STDERR: {result2.stderr}")
            
            # Test m4b-tool with a simple command first
            test_cmd = ["m4b-tool", "--version"]
            test_result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            logger.info(f"m4b-tool version test return code: {test_result.returncode}")
            logger.info(f"m4b-tool version test STDOUT: {test_result.stdout}")
            logger.info(f"m4b-tool version test STDERR: {test_result.stderr}")
            
            # Test if m4b-tool can see the directory
            test_cmd2 = ["bash", "-c", f"m4b-tool merge --help | head -10"]
            test_result2 = subprocess.run(test_cmd2, capture_output=True, text=True, timeout=10)
            logger.info(f"m4b-tool help test return code: {test_result2.returncode}")
            logger.info(f"m4b-tool help test STDOUT: {test_result2.stdout}")
            
            # Test if m4b-tool can access the directory with a simple ls command
            test_cmd3 = ["bash", "-c", f"m4b-tool merge {shlex.quote(input_absolute)} --dry-run"]
            test_result3 = subprocess.run(test_cmd3, capture_output=True, text=True, timeout=30)
            logger.info(f"m4b-tool dry-run test return code: {test_result3.returncode}")
            logger.info(f"m4b-tool dry-run test STDOUT: {test_result3.stdout}")
            logger.info(f"m4b-tool dry-run test STDERR: {test_result3.stderr}")
            
            cmd = [
                "m4b-tool", "merge",
                input_absolute,
                "--output-file", output_absolute,
                "--audio-bitrate", M4B_TOOL_BITRATE,
                "--audio-codec", M4B_TOOL_CODEC,
                "--jobs", "1",
                "--verbose", "3"
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Start conversion process
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CONVERSION_TIMEOUT
            )
            logger.info(f"m4b-tool return code: {result.returncode}")
            logger.info(f"m4b-tool STDOUT:\n{result.stdout}")
            logger.info(f"m4b-tool STDERR:\n{result.stderr}")
            
            return_code = result.returncode
            
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
                        book_name, "failed", "Output file not created", 0.0, total_files, 0
                    )
                    return False
            else:
                logger.error(f"Conversion failed with return code: {return_code}")
                self.update_conversion_progress(
                    book_name, "failed", f"Process failed with code {return_code}", 0.0, total_files, 0
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
