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
import shutil
import re
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from config import DB_PATH, M4B_TOOL_BITRATE, M4B_TOOL_CODEC, CONVERSION_TIMEOUT

logger = logging.getLogger(__name__)

class M4BConverter:
    """Wrapper around m4b-tool for audiobook conversion"""
    
    def __init__(self):
        self.db_path = DB_PATH

    def sanitize_folder_name(self, folder_name: str) -> str:
        """
        Sanitize folder name for m4b-tool compatibility by removing spaces and special characters
        
        Args:
            folder_name: Original folder name
            
        Returns:
            Sanitized folder name safe for m4b-tool
        """
        # Replace spaces with underscores and remove special characters
        sanitized = re.sub(r'[^\w\-_.]', '_', folder_name)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized

    def create_temp_sanitized_directory(self, original_path: str, original_book_name: str) -> str:
        """
        Create a temporary sanitized directory for m4b-tool conversion
        
        Args:
            original_path: Original path with spaces
            original_book_name: Original book name for reference
            
        Returns:
            Path to temporary sanitized directory
        """
        original_dir = Path(original_path)
        sanitized_name = self.sanitize_folder_name(original_book_name)
        temp_dir = Path("/tmp") / f"m4b_conversion_{sanitized_name}_{int(time.time())}"
        
        # Create temporary directory
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all files from original directory to temp directory
        logger.info(f"Creating temporary sanitized directory: {temp_dir}")
        for item in original_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, temp_dir)
                logger.info(f"Copied {item.name} to temporary directory")
        
        return str(temp_dir)

    def cleanup_temp_directory(self, temp_path: str):
        """
        Clean up temporary directory after conversion
        
        Args:
            temp_path: Path to temporary directory to remove
        """
        try:
            temp_dir = Path(temp_path)
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary directory {temp_path}: {e}")
    
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
        Convert audiobook using m4b-tool with sanitized folder names
        
        Args:
            input_path: Path to input MP3 files
            output_path: Path to output M4B file
            book_name: Name of the book
            
        Returns:
            True if conversion successful, False otherwise
        """
        temp_dir = None
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

            # Create temporary sanitized directory for m4b-tool
            logger.info(f"Creating sanitized directory for m4b-tool compatibility")
            temp_dir = self.create_temp_sanitized_directory(input_path, book_name)
            
            # Build m4b-tool command with sanitized paths
            output_file = output_dir / f"{book_name}.m4b"
            
            # Use the temporary sanitized directory for input
            input_absolute = temp_dir + "/"
            output_absolute = str(output_file)

            # Use shell=True with proper quoting to ensure paths are handled correctly
            # Force quotes around paths to ensure m4b-tool receives them properly
            quoted_input = f'"{input_absolute}"'
            quoted_output = f'"{output_absolute}"'
            
            # Change to parent directory before running m4b-tool for better path resolution
            parent_dir = Path(input_absolute).parent
            cmd_str = f"cd {shlex.quote(str(parent_dir))} && m4b-tool merge {quoted_input} --output-file {quoted_output} --audio-bitrate {M4B_TOOL_BITRATE} --audio-codec {M4B_TOOL_CODEC} --jobs 1 --verbose 3"

            logger.info(f"Running command: {cmd_str}")

            # Start conversion process
            result = subprocess.run(
                cmd_str,
                shell=True,
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
        finally:
            # Always cleanup temporary directory
            if temp_dir:
                self.cleanup_temp_directory(temp_dir)
    
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
