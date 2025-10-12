#!/usr/bin/env python3
"""
Conversion Watcher Service

Monitors auto-m4b conversion progress by watching:
1. auto-m4b/temp/merge - for total files to convert
2. auto-m4b/temp/untagged - for current conversion progress

Tracks conversion progress and updates database with:
- Total files count
- Current converting file
- Progress percentage
- Status updates
"""

import os
import sys
import time
import sqlite3
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DB_PATH = os.getenv("DB_PATH", "/app/db/rss.sqlite")
API_URL = os.getenv("API_URL", "http://api:8000")
AUTO_M4B_TEMP_PATH = os.getenv("AUTO_M4B_TEMP_PATH", "/app/auto-m4b/temp")
MERGE_PATH = os.path.join(AUTO_M4B_TEMP_PATH, "merge")
UNTAGGED_PATH = os.path.join(AUTO_M4B_TEMP_PATH, "untagged")

class ConversionTracker:
    """Tracks conversion progress for auto-m4b"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.api_url = API_URL
        
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
        return conn
    
    def log_to_api(self, level: str, message: str):
        """Log message to API service with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.api_url}/logs/external",
                    json={
                        "level": level,
                        "message": message,
                        "service": "conversion-watcher"
                    },
                    timeout=5
                )
                response.raise_for_status()
                return  # Success
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    import time
                    wait_time = 2 * (attempt + 1)  # 2, 4, 6 seconds
                    logger.warning(f"API not ready, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"API service not available after {max_retries} attempts: {e}")
                    return
            except Exception as e:
                logger.error(f"Failed to log to API: {e}")
                return
    
    def get_merge_files(self) -> List[str]:
        """Get all files in merge folder"""
        merge_files = []
        if os.path.exists(MERGE_PATH):
            for item in os.listdir(MERGE_PATH):
                item_path = os.path.join(MERGE_PATH, item)
                if os.path.isfile(item_path) and item.endswith('.m4b'):
                    merge_files.append(item)
        return merge_files
    
    def get_untagged_folders(self) -> List[str]:
        """Get all folders in untagged directory"""
        untagged_folders = []
        if os.path.exists(UNTAGGED_PATH):
            for item in os.listdir(UNTAGGED_PATH):
                item_path = os.path.join(UNTAGGED_PATH, item)
                if os.path.isdir(item_path):
                    untagged_folders.append(item)
        return untagged_folders
    
    def find_converting_file(self, book_folder: str) -> Optional[str]:
        """Find the currently converting file in a book folder"""
        book_path = os.path.join(UNTAGGED_PATH, book_folder)
        if not os.path.exists(book_path):
            return None
            
        # Look for files ending with "-converting.m4b" in the book folder and subfolders
        for root, dirs, files in os.walk(book_path):
            for file in files:
                if file.endswith('-converting.m4b'):
                    return file
        return None
    
    def has_finished_files(self, book_folder: str) -> bool:
        """Check if folder has files with -finished suffix"""
        book_path = os.path.join(UNTAGGED_PATH, book_folder)
        if not os.path.exists(book_path):
            return False
            
        # Look for files ending with "-finished.m4b" in the book folder and subfolders
        for root, dirs, files in os.walk(book_path):
            for file in files:
                if file.endswith('-finished.m4b'):
                    return True
        return False
    
    def get_converted_files_count(self, book_folder: str) -> int:
        """Count converted files in a book folder (including finished files as they are completed)"""
        book_path = os.path.join(UNTAGGED_PATH, book_folder)
        if not os.path.exists(book_path):
            return 0
            
        converted_count = 0
        for root, dirs, files in os.walk(book_path):
            for file in files:
                if (file.endswith('.m4b') and 
                    not file.endswith('-converting.m4b')):
                    # Count both finished files and fully converted files
                    converted_count += 1
        return converted_count
    
    def extract_book_name_from_folder(self, folder_name: str) -> str:
        """Extract book name from folder name"""
        if folder_name.endswith('-tmpfiles'):
            return folder_name[:-9]  
        return folder_name
    
    def update_conversion_tracking(self, book_name: str, merge_folder_path: str, temp_folder_path: str):
        """Update or create conversion tracking record"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check if conversion_tracking table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversion_tracking'")
            if not cursor.fetchone():
                logger.warning("conversion_tracking table does not exist yet, skipping update")
                conn.close()
                return
            
            # Get total files from merge folder
            merge_files_count = len(self.get_merge_files())
            
            # Get current conversion status
            untagged_folders = self.get_untagged_folders()
            current_file = None
            converted_files = 0
            status = "pending"
            progress_percentage = 0.0
            
            # Find the book folder in untagged
            book_folder = None
            for folder in untagged_folders:
                extracted_name = self.extract_book_name_from_folder(folder)
                if extracted_name == book_name or folder == book_name:
                    book_folder = folder
                    break
            
            # Determine total files count - prioritize merge folder count
            total_files = merge_files_count
            
            # If no files in merge folder, try to get it from existing database record first
            if total_files == 0:
                cursor.execute('SELECT total_files FROM conversion_tracking WHERE book_name = ?', (book_name,))
                existing_record = cursor.fetchone()
                if existing_record and existing_record[0] > 0:
                    total_files = existing_record[0]
                    logger.info(f"Using existing total_files count from database: {total_files}")
            
            # If we still don't have a total count, try to determine from untagged folder
            if total_files == 0 and book_folder:
                # Count all .m4b files in the book folder (including those with suffixes)
                book_path = os.path.join(UNTAGGED_PATH, book_folder)
                if os.path.exists(book_path):
                    all_m4b_files = []
                    for root, dirs, files in os.walk(book_path):
                        for file in files:
                            if file.endswith('.m4b'):
                                all_m4b_files.append(file)
                    total_files = len(all_m4b_files)
                    logger.info(f"Determined total_files from untagged folder: {total_files}")
            
            if book_folder:
                # Check if there's a converting file
                converting_file = self.find_converting_file(book_folder)
                has_finished_files = self.has_finished_files(book_folder)
                
                converted_files = self.get_converted_files_count(book_folder)
                
                if converting_file:
                    current_file = converting_file
                    status = "converting"
                elif has_finished_files:
                    # Has -finished files, conversion is still in progress
                    status = "converting"
                    current_file = "Processing finished files..."
                else:
                    # Check if all files are converted (no suffixes)
                    if converted_files > 0:
                        if converted_files >= total_files:
                            status = "completed"
                            current_file = None
                        else:
                            status = "converting"
                            current_file = "Finalizing conversion..."
                    else:
                        status = "pending"
                        current_file = None
                
                # Calculate progress percentage
                if total_files > 0:
                    progress_percentage = (converted_files / total_files) * 100
            
            # Check if record exists
            cursor.execute(
                'SELECT id FROM conversion_tracking WHERE book_name = ?',
                (book_name,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute('''
                    UPDATE conversion_tracking 
                    SET total_files = ?, converted_files = ?, current_file = ?, 
                        status = ?, progress_percentage = ?, merge_folder_path = ?,
                        temp_folder_path = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE book_name = ?
                ''', (total_files, converted_files, current_file, status, 
                      progress_percentage, merge_folder_path, temp_folder_path, book_name))
            else:
                # Create new record
                cursor.execute('''
                    INSERT INTO conversion_tracking 
                    (book_name, total_files, converted_files, current_file, status, 
                     progress_percentage, merge_folder_path, temp_folder_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (book_name, total_files, converted_files, current_file, status,
                      progress_percentage, merge_folder_path, temp_folder_path))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated conversion tracking for '{book_name}': {status} ({progress_percentage:.1f}%) - Total: {total_files}, Converted: {converted_files}, Merge files: {merge_files_count}")
            self.log_to_api("INFO", f"Updated conversion tracking for '{book_name}': {status} ({progress_percentage:.1f}%) - Total: {total_files}, Converted: {converted_files}")
            
        except Exception as e:
            logger.error(f"Error updating conversion tracking: {e}")
            self.log_to_api("ERROR", f"Error updating conversion tracking: {e}")
    
    def scan_all_conversions(self):
        """Scan all current conversions and update tracking"""
        try:
            # Get all merge files to determine books being processed
            merge_files = self.get_merge_files()
            untagged_folders = self.get_untagged_folders()
            
            # Process each book
            processed_books = set()
            
            # First, process books that have folders in untagged
            for folder in untagged_folders:
                book_name = self.extract_book_name_from_folder(folder)
                if book_name not in processed_books:
                    merge_folder_path = MERGE_PATH
                    temp_folder_path = os.path.join(UNTAGGED_PATH, folder)
                    self.update_conversion_tracking(book_name, merge_folder_path, temp_folder_path)
                    processed_books.add(book_name)
            
            # Then process any remaining books that might be in merge but not yet in untagged
            for merge_file in merge_files:
                # Extract book name from filename (remove .m4b extension)
                book_name = merge_file[:-4] if merge_file.endswith('.m4b') else merge_file
                if book_name not in processed_books:
                    merge_folder_path = MERGE_PATH
                    temp_folder_path = None
                    self.update_conversion_tracking(book_name, merge_folder_path, temp_folder_path)
                    processed_books.add(book_name)
                    
        except Exception as e:
            logger.error(f"Error scanning conversions: {e}")
            self.log_to_api("ERROR", f"Error scanning conversions: {e}")

class ConversionEventHandler(FileSystemEventHandler):
    """Handles file system events for conversion monitoring"""
    
    def __init__(self, tracker: ConversionTracker):
        self.tracker = tracker
        self.last_scan_time = 0
        self.scan_cooldown = 5  # seconds
    
    def on_any_event(self, event):
        """Handle any file system event"""
        if event.is_directory:
            return
            
        current_time = time.time()
        if current_time - self.last_scan_time < self.scan_cooldown:
            return
            
        self.last_scan_time = current_time
        
        # Small delay to ensure file operations are complete
        time.sleep(1)
        
        logger.info(f"File system event detected: {event.event_type} - {event.src_path}")
        self.tracker.log_to_api("INFO", f"File system event: {event.event_type} - {event.src_path}")
        
        # Trigger a full scan
        self.tracker.scan_all_conversions()

def main():
    """Main function"""
    logger.info("Starting Conversion Watcher Service")
    
    # Ensure directories exist
    os.makedirs(MERGE_PATH, exist_ok=True)
    os.makedirs(UNTAGGED_PATH, exist_ok=True)
    
    # Initialize tracker
    tracker = ConversionTracker()
    
    # Initial scan
    logger.info("Performing initial scan...")
    tracker.scan_all_conversions()
    
    # Log startup after initial setup (API might not be ready immediately)
    tracker.log_to_api("INFO", "Conversion Watcher Service started")
    
    # Set up file system monitoring
    event_handler = ConversionEventHandler(tracker)
    observer = Observer()
    
    # Watch both merge and untagged directories
    observer.schedule(event_handler, MERGE_PATH, recursive=True)
    observer.schedule(event_handler, UNTAGGED_PATH, recursive=True)
    
    observer.start()
    logger.info(f"Watching directories: {MERGE_PATH}, {UNTAGGED_PATH}")
    
    try:
        # Periodic full scan every 30 seconds
        while True:
            time.sleep(30)
            logger.debug("Performing periodic scan...")
            tracker.scan_all_conversions()
            
    except KeyboardInterrupt:
        logger.info("Stopping Conversion Watcher Service...")
        observer.stop()
        tracker.log_to_api("INFO", "Conversion Watcher Service stopped")
    
    observer.join()
    logger.info("Conversion Watcher Service stopped")

if __name__ == "__main__":
    main()
