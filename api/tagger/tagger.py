#!/usr/bin/env python3
import os
import time
import requests
import json
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaggerEventHandler(FileSystemEventHandler):
    def __init__(self, api_url="http://api:8000"):
        self.api_url = api_url
        self.to_tag_path = Path("/toTag")
        
    def log_to_api(self, level: str, message: str, retries: int = 3):
        """Log message to the API with retry logic"""
        for attempt in range(retries):
            try:
                response = requests.post(
                    f"{self.api_url}/logs/external",
                    json={
                        "level": level,
                        "message": message,
                        "service": "tagger"
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    return  # Success
                else:
                    logger.warning(f"Failed to log to API (attempt {attempt + 1}): {response.status_code}")
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error to API (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"Error logging to API (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        
        logger.error(f"Failed to log to API after {retries} attempts: {message}")
    
    def on_created(self, event):
        """Handle file/folder creation events"""
        if event.is_directory:
            self.handle_new_folder(event.src_path)
        else:
            self.handle_new_file(event.src_path)
    
    def on_moved(self, event):
        """Handle file/folder move events"""
        if event.is_directory:
            self.handle_new_folder(event.dest_path)
        else:
            self.handle_new_file(event.dest_path)
    
    def handle_new_folder(self, folder_path):
        """Handle new folder in toTag directory"""
        folder_path = Path(folder_path)
        
        # Check if it's in the toTag directory
        try:
            relative_path = folder_path.relative_to(self.to_tag_path)
            if relative_path.parts[0] == "..":  # Not in toTag directory
                return
        except ValueError:
            return
        
        # Check if folder contains .m4b files
        m4b_files = list(folder_path.glob("*.m4b"))
        if m4b_files:
            logger.info(f"📁 New m4b folder detected: {folder_path.name}")
            self.log_to_api("INFO", f"New m4b folder detected: {folder_path.name}")
            self.report_to_api(folder_path)
        else:
            logger.info(f"📁 New folder detected (no m4b): {folder_path.name}")
    
    def handle_new_file(self, file_path):
        """Handle new file in toTag directory"""
        file_path = Path(file_path)
        
        # Check if it's an m4b file
        if file_path.suffix.lower() == '.m4b':
            logger.info(f"🎵 New m4b file detected: {file_path.name}")
            self.log_to_api("INFO", f"New m4b file detected: {file_path.name}")
            self.report_to_api(file_path.parent)
    
    def report_to_api(self, folder_path, retries: int = 3):
        """Report new tagging item to API with retry logic"""
        try:
            folder_path = Path(folder_path)
            relative_path = folder_path.relative_to(self.to_tag_path)
            
            # Get all m4b files in the folder
            m4b_files = list(folder_path.glob("*.m4b"))
            
            for m4b_file in m4b_files:
                # Make path relative to toTag directory for API container
                relative_file_path = m4b_file.relative_to(self.to_tag_path)
                api_path = f"/app/toTag/{relative_file_path}"
                
                item_data = {
                    "name": m4b_file.name,
                    "path": api_path,
                    "folder": str(relative_path),
                    "status": "waiting",
                    "size": m4b_file.stat().st_size,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Send to API with retry logic
                for attempt in range(retries):
                    try:
                        response = requests.post(
                            f"{self.api_url}/tagging/items",
                            json=item_data,
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            logger.info(f"✅ Reported tagging item: {m4b_file.name}")
                            break  # Success, exit retry loop
                        else:
                            logger.warning(f"⚠️ Failed to report tagging item (attempt {attempt + 1}): {response.status_code}")
                            
                    except requests.exceptions.ConnectionError as e:
                        logger.warning(f"Connection error reporting to API (attempt {attempt + 1}): {e}")
                        if attempt < retries - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                    except Exception as e:
                        logger.error(f"Error reporting to API (attempt {attempt + 1}): {e}")
                        if attempt < retries - 1:
                            time.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to report tagging item after {retries} attempts: {m4b_file.name}")
                    
        except Exception as e:
            logger.error(f"Error in report_to_api: {e}")

def scan_existing_files():
    """Scan existing files in toTag directory on startup"""
    to_tag_path = Path("/toTag")
    
    if not to_tag_path.exists():
        logger.warning("toTag directory does not exist")
        return
    
    logger.info("🔍 Scanning existing files in toTag directory...")
    
    for item in to_tag_path.iterdir():
        if item.is_dir():
            m4b_files = list(item.glob("*.m4b"))
            if m4b_files:
                logger.info(f"📁 Found existing m4b folder: {item.name}")
                # Report existing items
                handler = TaggerEventHandler()
                handler.report_to_api(item)

def wait_for_api(api_url="http://api:8000", max_retries=30):
    """Wait for the API service to be available"""
    logger.info("🔍 Waiting for API service to be available...")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ API service is available")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if attempt < max_retries - 1:
            logger.info(f"⏳ API not ready, waiting... (attempt {attempt + 1}/{max_retries})")
            time.sleep(2)
    
    logger.error("❌ API service is not available after maximum retries")
    return False

def main():
    """Main function"""
    logger.info("🏷️ Tagger service started")
    
    # Wait for API to be available
    if not wait_for_api():
        logger.error("Cannot start tagger service without API connection")
        return
    
    # Scan existing files
    scan_existing_files()
    
    # Set up file system watcher
    event_handler = TaggerEventHandler()
    observer = Observer()
    observer.schedule(event_handler, "/toTag", recursive=True)
    
    try:
        observer.start()
        logger.info("👀 Watching /toTag directory for changes...")
        
        # Keep the service running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Tagger service stopping...")
        observer.stop()
    
    observer.join()
    logger.info("✅ Tagger service stopped")

if __name__ == "__main__":
    main()
