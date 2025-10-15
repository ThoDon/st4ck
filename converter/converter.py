#!/usr/bin/env python3
"""
Main converter service with Redis event listener
"""

import os
import sys
import time
import json
import logging
import signal
import requests
from pathlib import Path
from typing import Dict, Any
import redis
from config import (
    REDIS_HOST, REDIS_PORT, REDIS_DB,
    CHANNEL_DOWNLOAD_COMPLETE, CHANNEL_CONVERSION_COMPLETE, CHANNEL_CONVERSION_FAILED,
    CHANNEL_RETRY_CONVERSION, API_URL, CONVERSION_MAX_RETRIES
)
from m4b_converter import M4BConverter
from backup_manager import BackupManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConverterService:
    """Main converter service that listens to Redis events and manages conversions"""
    
    def __init__(self):
        self.redis_client = None
        self.m4b_converter = M4BConverter()
        self.backup_manager = BackupManager()
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def connect_redis(self) -> bool:
        """Connect to Redis server"""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    def log_to_api(self, level: str, message: str):
        """Log message to API service"""
        try:
            requests.post(
                f"{API_URL}/logs/external",
                json={
                    "level": level,
                    "message": message,
                    "service": "converter"
                },
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Failed to log to API: {e}")
    
    def handle_download_complete(self, message_data: Dict[str, Any]):
        """
        Handle download complete event from mover service
        
        Args:
            message_data: Dictionary containing book_name, path, rss_item_id
        """
        try:
            book_name = message_data.get('book_name')
            source_path = message_data.get('path')
            rss_item_id = message_data.get('rss_item_id')
            
            if not all([book_name, source_path]):
                logger.error(f"Invalid message data: {message_data}")
                return
            
            # If rss_item_id is not provided, try to find it by book name
            if not rss_item_id:
                rss_item_id = self._find_rss_item_id_by_name(book_name)
                if not rss_item_id:
                    logger.warning(f"Could not find rss_item_id for book: {book_name}, proceeding without it")
                    rss_item_id = None
            
            logger.info(f"Processing download complete for: {book_name}")
            self.log_to_api("INFO", f"Processing download complete for: {book_name}")
            
            # Check if source path exists before creating backup
            source_path_obj = Path(source_path)
            if not source_path_obj.exists():
                logger.warning(f"Source path does not exist yet: {source_path}")
                
                # Debug: List what's actually in the toMerge directory
                tomerge_dir = Path("/toMerge")
                if tomerge_dir.exists():
                    logger.info(f"Contents of /toMerge directory:")
                    for item in tomerge_dir.iterdir():
                        logger.info(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")
                else:
                    logger.warning("/toMerge directory does not exist")
                
                logger.info(f"Waiting 5 seconds for files to be moved...")
                time.sleep(5)
                
                # Check again after waiting
                if not source_path_obj.exists():
                    logger.error(f"Source path still does not exist after waiting: {source_path}")
                    self.log_to_api("ERROR", f"Source path does not exist: {source_path}")
                    return
            
            # Create backup before conversion
            backup_path = self.backup_manager.create_backup(book_name, source_path)
            if not backup_path:
                logger.error(f"Failed to create backup for {book_name}")
                self.log_to_api("ERROR", f"Failed to create backup for {book_name}")
                return
            
            # Track backup usage (only if rss_item_id is available)
            if rss_item_id:
                self.backup_manager.track_backup_usage(book_name, backup_path, rss_item_id)
            
            # Start conversion
            success = self._perform_conversion(book_name, source_path, rss_item_id)
            
            if success:
                # Publish conversion complete event
                if rss_item_id:
                    self._publish_conversion_complete(book_name, rss_item_id)
                
                # Note: Backup cleanup is now handled by tagger service after successful tagging
                # This allows for duration validation and quality checks before cleanup
            else:
                # Publish conversion failed event
                if rss_item_id:
                    self._publish_conversion_failed(book_name, rss_item_id, "Conversion failed")
            
        except Exception as e:
            logger.error(f"Error handling download complete: {e}")
            self.log_to_api("ERROR", f"Error handling download complete: {e}")
    
    def handle_retry_conversion(self, message_data: Dict[str, Any]):
        """
        Handle retry conversion event from API/UI
        
        Args:
            message_data: Dictionary containing book_name, rss_item_id, etc.
        """
        try:
            book_name = message_data.get('book_name')
            rss_item_id = message_data.get('rss_item_id')
            
            if not all([book_name, rss_item_id]):
                logger.error(f"Invalid retry message data: {message_data}")
                return
            
            logger.info(f"Retrying conversion for: {book_name}")
            self.log_to_api("INFO", f"Retrying conversion for: {book_name}")
            
            # Check if we have a backup to restore from
            backup_path = self._get_backup_path(book_name)
            if not backup_path:
                # Try to find backup in filesystem even if not in database
                logger.warning(f"No backup path in database, checking filesystem...")
                backup_path = self._find_backup_in_filesystem(book_name)
                
                if not backup_path:
                    logger.error(f"No backup found for retry: {book_name}")
                    self.log_to_api("ERROR", f"No backup found for retry: {book_name}")
                    return
                else:
                    logger.info(f"Found backup in filesystem: {backup_path}")
            
            # Restore from backup
            source_path = f"/toMerge/{book_name}"  # Expected input path
            if not self.backup_manager.restore_from_backup(backup_path, source_path):
                logger.error(f"Failed to restore from backup: {book_name}")
                self.log_to_api("ERROR", f"Failed to restore from backup: {book_name}")
                return
            
            # Retry conversion
            success = self._perform_conversion(book_name, source_path, rss_item_id)
            
            if success:
                self._publish_conversion_complete(book_name, rss_item_id)
            else:
                self._publish_conversion_failed(book_name, rss_item_id, "Retry conversion failed")
            
        except Exception as e:
            logger.error(f"Error handling retry conversion: {e}")
            self.log_to_api("ERROR", f"Error handling retry conversion: {e}")
    
    def _perform_conversion(self, book_name: str, source_path: str, rss_item_id: int = None) -> bool:
        """
        Perform the actual conversion
        
        Args:
            book_name: Name of the book
            source_path: Path to source files
            rss_item_id: RSS item ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update job status to processing (only if rss_item_id is available)
            if rss_item_id:
                self._update_conversion_job_status(book_name, "processing", rss_item_id, source_path=source_path)
            
            # Perform conversion
            output_path = "/converted"
            success = self.m4b_converter.convert_audiobook(source_path, output_path, book_name)
            
            if success:
                # Update job status to completed (only if rss_item_id is available)
                if rss_item_id:
                    self._update_conversion_job_status(book_name, "completed", rss_item_id, source_path=source_path)
                
                # Increment backup usage count
                self.backup_manager.increment_backup_usage(book_name)
                
                logger.info(f"Conversion completed successfully: {book_name}")
                self.log_to_api("INFO", f"Conversion completed successfully: {book_name}")
                return True
            else:
                # Update job status to failed (only if rss_item_id is available)
                if rss_item_id:
                    self._update_conversion_job_status(book_name, "failed", rss_item_id, "Conversion process failed", source_path=source_path)
                
                logger.error(f"Conversion failed: {book_name}")
                self.log_to_api("ERROR", f"Conversion failed: {book_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error during conversion: {e}")
            self.log_to_api("ERROR", f"Error during conversion: {e}")
            if rss_item_id:
                self._update_conversion_job_status(book_name, "failed", rss_item_id, str(e), source_path=source_path)
            return False
    
    def _update_conversion_job_status(self, book_name: str, status: str, 
                                    rss_item_id: int = None, error_message: str = None, source_path: str = None):
        """Update conversion job status in database"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                import sqlite3
                from config import DB_PATH
                
                conn = sqlite3.connect(DB_PATH, timeout=30.0)
                cursor = conn.cursor()
                
                # Use default source path if not provided
                if not source_path:
                    source_path = f"/toMerge/{book_name}"
                
                # Update or create conversion job record
                cursor.execute('''
                    INSERT OR REPLACE INTO conversion_jobs 
                    (rss_item_id, book_name, source_path, status, error_message, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (rss_item_id, book_name, source_path, status, error_message))
                
                conn.commit()
                conn.close()
                return  # Success, exit retry loop
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Database locked, retrying in 1 second (attempt {attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
                else:
                    logger.error(f"Failed to update conversion job status after {max_retries} attempts: {e}")
                    break
            except Exception as e:
                logger.error(f"Failed to update conversion job status: {e}")
                break
    
    def _find_rss_item_id_by_name(self, book_name: str) -> int:
        """Find RSS item ID by book name with improved matching"""
        try:
            import sqlite3
            from config import DB_PATH
            
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            cursor = conn.cursor()
            
            # Try exact match first
            cursor.execute('SELECT id FROM rss_items WHERE title = ?', (book_name,))
            result = cursor.fetchone()
            
            if not result:
                # Try partial match (book name might be truncated)
                cursor.execute('SELECT id FROM rss_items WHERE title LIKE ?', (f'%{book_name}%',))
                result = cursor.fetchone()
            
            if not result:
                # Try reverse partial match (RSS title might be truncated)
                cursor.execute('SELECT id FROM rss_items WHERE ? LIKE "%" || title || "%"', (book_name,))
                result = cursor.fetchone()
            
            if not result:
                # Try fuzzy matching by removing common separators and comparing core parts
                # Remove common separators and normalize
                normalized_book = book_name.replace(' - ', ' ').replace('_', ' ').replace('.', ' ').lower().strip()
                
                # Get all RSS items and try to find best match
                cursor.execute('SELECT id, title FROM rss_items')
                all_items = cursor.fetchall()
                
                best_match = None
                best_score = 0
                
                for item_id, item_title in all_items:
                    normalized_item = item_title.replace(' - ', ' ').replace('_', ' ').replace('.', ' ').lower().strip()
                    
                    # Calculate similarity score based on common words
                    book_words = set(normalized_book.split())
                    item_words = set(normalized_item.split())
                    
                    if book_words and item_words:
                        common_words = book_words.intersection(item_words)
                        score = len(common_words) / max(len(book_words), len(item_words))
                        
                        if score > best_score and score > 0.3:  # At least 30% similarity
                            best_score = score
                            best_match = item_id
                
                if best_match:
                    result = (best_match,)
                    logger.info(f"Found fuzzy match for '{book_name}' -> RSS ID {best_match} (score: {best_score:.2f})")
            
            conn.close()
            
            if result:
                logger.info(f"Found RSS item ID {result[0]} for book: {book_name}")
                return result[0]
            else:
                logger.warning(f"No RSS item found for book: {book_name}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to find rss_item_id for {book_name}: {e}")
            return None

    def _get_backup_path(self, book_name: str) -> str:
        """Get backup path for a book"""
        try:
            import sqlite3
            from config import DB_PATH
            
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            cursor = conn.cursor()
            
            # Look for backup path in rss_items table (where it's actually stored by track_backup_usage)
            logger.info(f"Looking for backup path for book: {book_name}")
            cursor.execute('SELECT conversion_backup_path FROM rss_items WHERE title = ?', (book_name,))
            result = cursor.fetchone()
            
            if result and result[0]:
                logger.info(f"Found backup path: {result[0]}")
                conn.close()
                return result[0]
            else:
                logger.warning(f"No backup path found in rss_items for book: {book_name}")
                
                # Fallback: Look in conversion_jobs table
                cursor.execute('SELECT backup_path FROM conversion_jobs WHERE book_name = ? ORDER BY created_at DESC LIMIT 1', (book_name,))
                job_result = cursor.fetchone()
                
                if job_result and job_result[0]:
                    logger.info(f"Found backup path in conversion_jobs: {job_result[0]}")
                    conn.close()
                    return job_result[0]
                else:
                    logger.warning(f"No backup path found in conversion_jobs either")
                    
                    # Debug: Show all records for this book
                    cursor.execute('SELECT id, title, conversion_backup_path FROM rss_items WHERE title LIKE ?', (f'%{book_name}%',))
                    rss_items = cursor.fetchall()
                    logger.info(f"RSS items for {book_name}: {rss_items}")
                    
                    cursor.execute('SELECT id, book_name, backup_path FROM conversion_jobs WHERE book_name = ?', (book_name,))
                    all_jobs = cursor.fetchall()
                    logger.info(f"All jobs for {book_name}: {all_jobs}")
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Failed to get backup path: {e}")
            return None
    
    def _find_backup_in_filesystem(self, book_name: str) -> str:
        """Find backup in filesystem even if not in database"""
        try:
            from pathlib import Path
            from config import BACKUP_PATH
            
            backup_dir = Path(BACKUP_PATH)
            if not backup_dir.exists():
                logger.warning(f"Backup directory does not exist: {BACKUP_PATH}")
                return None
            
            # Look for backup directories that start with the book name
            for backup_folder in backup_dir.iterdir():
                if backup_folder.is_dir() and backup_folder.name.startswith(book_name):
                    logger.info(f"Found backup folder: {backup_folder}")
                    return str(backup_folder)
            
            logger.warning(f"No backup folder found starting with: {book_name}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to find backup in filesystem: {e}")
            return None
    
    def _publish_conversion_complete(self, book_name: str, rss_item_id: int = None):
        """Publish conversion complete event"""
        try:
            message = {
                'book_name': book_name,
                'rss_item_id': rss_item_id,
                'status': 'completed',
                'timestamp': time.time()
            }
            
            self.redis_client.publish(CHANNEL_CONVERSION_COMPLETE, json.dumps(message))
            logger.info(f"Published conversion complete event for: {book_name}")
            
        except Exception as e:
            logger.error(f"Failed to publish conversion complete event: {e}")
    
    def _publish_conversion_failed(self, book_name: str, rss_item_id: int = None, error_message: str = None):
        """Publish conversion failed event"""
        try:
            message = {
                'book_name': book_name,
                'rss_item_id': rss_item_id,
                'status': 'failed',
                'error_message': error_message,
                'timestamp': time.time()
            }
            
            self.redis_client.publish(CHANNEL_CONVERSION_FAILED, json.dumps(message))
            logger.info(f"Published conversion failed event for: {book_name}")
            
        except Exception as e:
            logger.error(f"Failed to publish conversion failed event: {e}")
    
    def start(self):
        """Start the converter service"""
        logger.info("Starting Converter Service...")
        self.log_to_api("INFO", "Converter Service starting...")
        
        # Connect to Redis
        if not self.connect_redis():
            logger.error("Failed to connect to Redis, exiting...")
            return
        
        # Create pub/sub object
        pubsub = self.redis_client.pubsub()
        
        # Subscribe to channels
        pubsub.subscribe(
            CHANNEL_DOWNLOAD_COMPLETE,
            CHANNEL_RETRY_CONVERSION
        )
        
        logger.info(f"Subscribed to channels: {CHANNEL_DOWNLOAD_COMPLETE}, {CHANNEL_RETRY_CONVERSION}")
        self.log_to_api("INFO", "Converter Service started and listening for events")
        
        try:
            # Main event loop
            while self.running:
                try:
                    # Get message with timeout
                    message = pubsub.get_message(timeout=1.0)
                    
                    if message and message['type'] == 'message':
                        channel = message['channel']
                        data = json.loads(message['data'])
                        
                        logger.info(f"Received message on {channel}: {data}")
                        
                        if channel == CHANNEL_DOWNLOAD_COMPLETE:
                            self.handle_download_complete(data)
                        elif channel == CHANNEL_RETRY_CONVERSION:
                            self.handle_retry_conversion(data)
                    
                except redis.ConnectionError as e:
                    logger.error(f"Redis connection error: {e}")
                    # Try to reconnect
                    if not self.connect_redis():
                        logger.error("Failed to reconnect to Redis")
                        break
                    pubsub = self.redis_client.pubsub()
                    pubsub.subscribe(CHANNEL_DOWNLOAD_COMPLETE, CHANNEL_RETRY_CONVERSION)
                    
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(5)  # Wait before continuing
        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        
        finally:
            # Cleanup
            pubsub.close()
            if self.redis_client:
                self.redis_client.close()
            
            logger.info("Converter Service stopped")
            self.log_to_api("INFO", "Converter Service stopped")

def main():
    """Main function"""
    service = ConverterService()
    service.start()

if __name__ == "__main__":
    main()
