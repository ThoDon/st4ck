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
from config import DB_PATH, CONVERSION_TIMEOUT
from audio_utils import AudioUtils

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
        Convert audiobook using m4b-tool with auto-m4b-ubuntu approach
        
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

            # Calculate source total duration before conversion
            logger.info("Calculating source total duration...")
            source_total_duration = AudioUtils.calculate_total_duration(mp3_files)
            
            if source_total_duration is None:
                logger.warning("Could not calculate source duration, proceeding without validation")
            else:
                logger.info(f"Source total duration: {AudioUtils.format_duration(source_total_duration)}")

            # Update initial progress
            self.update_conversion_progress(
                book_name, "converting", "Starting conversion...", 0.0, total_files, 0
            )

            # Use the folder_m4b_builder.sh script (auto-m4b-ubuntu approach)
            script_path = Path(__file__).parent / "folder_m4b_builder.sh"
            
            if not script_path.exists():
                logger.error(f"Conversion script not found: {script_path}")
                return False

            # Build command to run the conversion script
            cmd = [
                str(script_path),
                str(input_dir),
                str(output_dir),
                book_name
            ]

            logger.info(f"Running conversion script: {' '.join(cmd)}")

            # Start conversion process
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CONVERSION_TIMEOUT
            )
            
            logger.info(f"Conversion script return code: {result.returncode}")
            logger.info(f"Conversion script STDOUT:\n{result.stdout}")
            logger.info(f"Conversion script STDERR:\n{result.stderr}")

            return_code = result.returncode

            if return_code == 0:
                # Check if output file was created
                output_file = output_dir / f"{book_name}.m4b"
                if output_file.exists():
                    logger.info(f"Conversion completed successfully: {output_file}")
                    
                    # Validate duration if we have source duration
                    duration_validation_passed = None
                    if source_total_duration is not None:
                        logger.info("Validating converted file duration...")
                        converted_duration = AudioUtils.get_audio_duration(str(output_file))
                        
                        if converted_duration is not None:
                            is_valid, message = AudioUtils.validate_conversion_duration(
                                source_total_duration, converted_duration
                            )
                            duration_validation_passed = is_valid
                            logger.info(f"Duration validation: {message}")
                            
                            if not is_valid:
                                logger.warning(f"Duration validation failed: {message}")
                        else:
                            logger.warning("Could not get converted file duration for validation")
                    
                    # Update conversion job with duration information
                    self._update_conversion_job_duration(
                        book_name, source_total_duration, 
                        AudioUtils.get_audio_duration(str(output_file)) if output_file.exists() else None,
                        duration_validation_passed
                    )
                    
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
    
    def _update_conversion_job_duration(self, book_name: str, source_duration: Optional[float], 
                                      converted_duration: Optional[float], 
                                      validation_passed: Optional[bool]):
        """
        Update conversion job with duration information
        
        Args:
            book_name: Name of the book
            source_duration: Source total duration in seconds
            converted_duration: Converted file duration in seconds
            validation_passed: Whether duration validation passed
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                # Update the most recent conversion job for this book
                cursor.execute('''
                    UPDATE conversion_jobs 
                    SET source_total_duration_seconds = ?, 
                        converted_duration_seconds = ?, 
                        duration_validation_passed = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE book_name = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', (source_duration, converted_duration, validation_passed, book_name))
                
                conn.commit()
                conn.close()
                return  # Success, exit retry loop
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Database locked, retrying in 1 second (attempt {attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
                else:
                    logger.error(f"Failed to update conversion job duration after {max_retries} attempts: {e}")
                    break
            except Exception as e:
                logger.error(f"Failed to update conversion job duration: {e}")
                break
