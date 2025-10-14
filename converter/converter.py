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
            
            if not all([book_name, source_path, rss_item_id]):
                logger.error(f"Invalid message data: {message_data}")
                return
            
            logger.info(f"Processing download complete for: {book_name}")
            self.log_to_api("INFO", f"Processing download complete for: {book_name}")
            
            # Create backup before conversion
            backup_path = self.backup_manager.create_backup(book_name, source_path)
            if not backup_path:
                logger.error(f"Failed to create backup for {book_name}")
                self.log_to_api("ERROR", f"Failed to create backup for {book_name}")
                return
            
            # Track backup usage
            self.backup_manager.track_backup_usage(book_name, backup_path, rss_item_id)
            
            # Start conversion
            success = self._perform_conversion(book_name, source_path, rss_item_id)
            
            if success:
                # Publish conversion complete event
                self._publish_conversion_complete(book_name, rss_item_id)
                
                # Clean up old backups if retention limit reached
                self.backup_manager.cleanup_old_backups(book_name)
            else:
                # Publish conversion failed event
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
                logger.error(f"No backup found for retry: {book_name}")
                self.log_to_api("ERROR", f"No backup found for retry: {book_name}")
                return
            
            # Restore from backup
            source_path = f"/input/{book_name}"  # Expected input path
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
    
    def _perform_conversion(self, book_name: str, source_path: str, rss_item_id: int) -> bool:
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
            # Update job status to processing
            self._update_conversion_job_status(book_name, rss_item_id, "processing")
            
            # Perform conversion
            output_path = "/output"
            success = self.m4b_converter.convert_audiobook(source_path, output_path, book_name)
            
            if success:
                # Update job status to completed
                self._update_conversion_job_status(book_name, rss_item_id, "completed")
                
                # Increment backup usage count
                self.backup_manager.increment_backup_usage(book_name)
                
                logger.info(f"Conversion completed successfully: {book_name}")
                self.log_to_api("INFO", f"Conversion completed successfully: {book_name}")
                return True
            else:
                # Update job status to failed
                self._update_conversion_job_status(book_name, rss_item_id, "failed", "Conversion process failed")
                
                logger.error(f"Conversion failed: {book_name}")
                self.log_to_api("ERROR", f"Conversion failed: {book_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error during conversion: {e}")
            self.log_to_api("ERROR", f"Error during conversion: {e}")
            self._update_conversion_job_status(book_name, rss_item_id, "failed", str(e))
            return False
    
    def _update_conversion_job_status(self, book_name: str, rss_item_id: int, 
                                    status: str, error_message: str = None):
        """Update conversion job status in database"""
        try:
            import sqlite3
            from config import DB_PATH
            
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            cursor = conn.cursor()
            
            # Update or create conversion job record
            cursor.execute('''
                INSERT OR REPLACE INTO conversion_jobs 
                (rss_item_id, book_name, status, error_message, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (rss_item_id, book_name, status, error_message))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update conversion job status: {e}")
    
    def _get_backup_path(self, book_name: str) -> str:
        """Get backup path for a book"""
        try:
            import sqlite3
            from config import DB_PATH
            
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            cursor = conn.cursor()
            
            cursor.execute('SELECT conversion_backup_path FROM rss_items WHERE title = ?', (book_name,))
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result and result[0] else None
            
        except Exception as e:
            logger.error(f"Failed to get backup path: {e}")
            return None
    
    def _publish_conversion_complete(self, book_name: str, rss_item_id: int):
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
    
    def _publish_conversion_failed(self, book_name: str, rss_item_id: int, error_message: str):
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
