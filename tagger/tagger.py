#!/usr/bin/env python3
import os
import time
import requests
import json
import redis
import signal
import threading
from datetime import datetime
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaggerService:
    def __init__(self, api_url="http://api:8000", redis_host="redis", redis_port=6379, scan_interval=60):
        self.api_url = api_url
        self.to_tag_path = Path("/toTag")
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_client = None
        self.running = True
        self.scan_interval = scan_interval  # Scan interval in seconds (default: 60 seconds = 1 minute)
        self.scan_timer = None
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
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
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        if self.scan_timer:
            self.scan_timer.cancel()
    
    def connect_redis(self) -> bool:
        """Connect to Redis server"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    def handle_conversion_complete(self, message_data: dict):
        """Handle conversion complete event from converter service"""
        try:
            book_name = message_data.get('book_name')
            file_path = message_data.get('file_path')
            
            if not book_name:
                logger.error(f"Invalid conversion complete message: {message_data}")
                return
            
            logger.info(f"📁 Conversion complete event received for: {book_name}")
            self.log_to_api("INFO", f"Conversion complete event received for: {book_name}")
            
            # Scan toTag directory for the new file
            self.scan_to_tag_directory()
            
        except Exception as e:
            logger.error(f"Error handling conversion complete: {e}")
            self.log_to_api("ERROR", f"Error handling conversion complete: {e}")
    
    def scan_to_tag_directory(self):
        """Scan toTag directory for new m4b files and auto-tag if ASIN is found"""
        try:
            if not self.to_tag_path.exists():
                logger.warning("toTag directory does not exist")
                return
            
            logger.info("🔍 Scanning toTag directory for new files...")
            
            # Look for m4b files directly in toTag directory
            m4b_files = list(self.to_tag_path.glob("*.m4b"))
            
            for m4b_file in m4b_files:
                logger.info(f"🎵 Found m4b file: {m4b_file.name}")
                
                # Try to auto-tag if ASIN is found
                if self.auto_tag_if_asin_found(m4b_file):
                    continue  # Skip manual processing if auto-tagged
                
                self.report_to_api(m4b_file.parent, m4b_file)
            
            # Also look for folders containing m4b files
            for item in self.to_tag_path.iterdir():
                if item.is_dir():
                    folder_m4b_files = list(item.glob("*.m4b"))
                    if folder_m4b_files:
                        logger.info(f"📁 Found m4b folder: {item.name}")
                        self.report_to_api(item)
                        
        except Exception as e:
            logger.error(f"Error scanning toTag directory: {e}")
            self.log_to_api("ERROR", f"Error scanning toTag directory: {e}")
    
    def auto_tag_if_asin_found(self, m4b_file: Path) -> bool:
        """Try to auto-tag M4B file if ASIN is found in existing tags"""
        try:
            logger.info(f"🔍 Checking for ASIN in {m4b_file.name}...")
            
            # Import M4BTagger to extract ASIN
            import sys
            import os
            
            # Add current directory to path for imports
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            from m4b_tagger import M4BTagger
            from audible_client import AudibleAPIClient
            from pathlib import Path
            
            # Create tagger instance
            library_dir = Path(os.getenv("LIBRARY_PATH", "/app/library"))
            covers_dir = Path(os.getenv("COVERS_PATH", "/app/data/covers"))
            
            # Ensure covers directory exists
            covers_dir.mkdir(parents=True, exist_ok=True)
            
            tagger = M4BTagger(library_dir, covers_dir)
            
            # Extract ASIN from file
            asin = tagger.extract_asin_from_file(m4b_file)
            
            if not asin:
                logger.info(f"❌ No ASIN found in {m4b_file.name}")
                return False
            
            logger.info(f"✅ Found ASIN: {asin} in {m4b_file.name}")
            
            # Try to fetch metadata and tag automatically
            try:
                client = AudibleAPIClient()
                details = client.get_book_details(asin, "fr")  # Default to French locale
                
                if not details:
                    logger.warning(f"❌ Could not fetch metadata for ASIN: {asin}")
                    return False
                
                logger.info(f"📚 Fetched metadata for: {getattr(details, 'title', 'Unknown')}")
                
                # Download cover if available
                cover_path = None
                if getattr(details, "product_images", None):
                    cover_url = getattr(details.product_images, "image_1000", None) or getattr(details.product_images, "image_500", None)
                    if cover_url:
                        cover_path = client.download_cover(cover_url, asin, covers_dir)
                
                # Tag the file
                if tagger.tag_file(m4b_file, details, cover_path):
                    logger.info(f"✅ Successfully auto-tagged: {m4b_file.name}")
                    self.log_to_api("INFO", f"Auto-tagged {m4b_file.name} with ASIN: {asin}")
                    
                    # Move to library
                    final_path = tagger.move_to_library(m4b_file, details, cover_path)
                    if final_path:
                        logger.info(f"📁 Moved to library: {final_path}")
                        self.log_to_api("INFO", f"Moved auto-tagged file to library: {final_path}")
                        
                        # Update tagging item to mark as auto-tagged
                        self.update_tagging_item_auto_tagged(m4b_file, True)
                        return True
                    else:
                        logger.error(f"❌ Failed to move to library: {m4b_file.name}")
                        return False
                else:
                    logger.error(f"❌ Failed to tag file: {m4b_file.name}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error during auto-tagging: {e}")
                self.log_to_api("ERROR", f"Auto-tagging failed for {m4b_file.name}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error checking ASIN in {m4b_file.name}: {e}")
            return False
    
    def update_tagging_item_auto_tagged(self, m4b_file: Path, auto_tagged: bool):
        """Update the tagging item to mark it as auto-tagged"""
        try:
            import requests
            
            # Find the tagging item by path
            response = requests.get(f"{self.api_url}/tagging")
            if response.status_code == 200:
                items = response.json()
                for item in items:
                    if item.get('path') == str(m4b_file):
                        # Update the item to mark as auto-tagged
                        update_data = {
                            "name": item['name'],
                            "path": item['path'],
                            "folder": item.get('folder'),
                            "status": "completed",  # Mark as completed since it was auto-tagged
                            "size": item.get('size'),
                            "auto_tagged": auto_tagged
                        }
                        
                        # Create/update the tagging item
                        update_response = requests.post(f"{self.api_url}/tagging/items", json=update_data)
                        if update_response.status_code == 200:
                            logger.info(f"✅ Updated tagging item for {m4b_file.name} as auto-tagged")
                        else:
                            logger.warning(f"⚠️ Failed to update tagging item for {m4b_file.name}")
                        break
                        
        except Exception as e:
            logger.error(f"❌ Error updating tagging item: {e}")
    
    def report_to_api(self, folder_path, specific_file=None, retries: int = 3):
        """Report new tagging item to API with retry logic"""
        try:
            folder_path = Path(folder_path)
            relative_path = folder_path.relative_to(self.to_tag_path)
            
            # Get m4b files to report
            if specific_file:
                m4b_files = [specific_file]
            else:
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
    
    def _periodic_scan(self):
        """Periodic scan method that runs every scan_interval seconds"""
        if not self.running:
            return
            
        try:
            logger.info("🔄 Periodic scan triggered")
            self.scan_to_tag_directory()
        except Exception as e:
            logger.error(f"Error in periodic scan: {e}")
            self.log_to_api("ERROR", f"Error in periodic scan: {e}")
        
        # Schedule the next scan
        if self.running:
            self.scan_timer = threading.Timer(self.scan_interval, self._periodic_scan)
            self.scan_timer.start()
    
    def start(self):
        """Start the tagger service"""
        logger.info("🏷️ Tagger service started")
        
        # Wait for API to be available
        if not wait_for_api():
            logger.error("Cannot start tagger service without API connection")
            return
        
        # Connect to Redis
        if not self.connect_redis():
            logger.error("Failed to connect to Redis, exiting...")
            return
        
        # Scan existing files on startup
        self.scan_to_tag_directory()
        
        # Start periodic scanning
        logger.info(f"⏰ Starting periodic scan every {self.scan_interval} seconds")
        self.scan_timer = threading.Timer(self.scan_interval, self._periodic_scan)
        self.scan_timer.start()
        
        # Create pub/sub object
        pubsub = self.redis_client.pubsub()
        
        # Subscribe to conversion complete channel
        pubsub.subscribe("audiobook:conversion_complete")
        
        logger.info("👀 Listening for conversion complete events...")
        self.log_to_api("INFO", f"Tagger service started with periodic scan every {self.scan_interval} seconds")
        
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
                        
                        if channel == "audiobook:conversion_complete":
                            self.handle_conversion_complete(data)
                    
                except redis.ConnectionError as e:
                    logger.error(f"Redis connection error: {e}")
                    # Try to reconnect
                    if not self.connect_redis():
                        logger.error("Failed to reconnect to Redis")
                        break
                    pubsub = self.redis_client.pubsub()
                    pubsub.subscribe("audiobook:conversion_complete")
                    
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(5)  # Wait before continuing
        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        
        finally:
            # Cleanup
            if self.scan_timer:
                self.scan_timer.cancel()
            pubsub.close()
            if self.redis_client:
                self.redis_client.close()
            
            logger.info("✅ Tagger service stopped")
            self.log_to_api("INFO", "Tagger service stopped")

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
    # Get scan interval from environment variable (default: 60 seconds)
    scan_interval = int(os.getenv("TAGGER_SCAN_INTERVAL", "60"))
    
    service = TaggerService(scan_interval=scan_interval)
    service.start()

if __name__ == "__main__":
    main()
