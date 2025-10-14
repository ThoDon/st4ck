#!/usr/bin/env python3
import os
import time
import requests
import json
import redis
import signal
from datetime import datetime
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaggerService:
    def __init__(self, api_url="http://api:8000", redis_host="redis", redis_port=6379):
        self.api_url = api_url
        self.to_tag_path = Path("/toTag")
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_client = None
        self.running = True
        
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
        """Scan toTag directory for new m4b files"""
        try:
            if not self.to_tag_path.exists():
                logger.warning("toTag directory does not exist")
                return
            
            logger.info("🔍 Scanning toTag directory for new files...")
            
            # Look for m4b files directly in toTag directory
            m4b_files = list(self.to_tag_path.glob("*.m4b"))
            
            for m4b_file in m4b_files:
                logger.info(f"🎵 Found m4b file: {m4b_file.name}")
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
        
        # Create pub/sub object
        pubsub = self.redis_client.pubsub()
        
        # Subscribe to conversion complete channel
        pubsub.subscribe("audiobook:conversion_complete")
        
        logger.info("👀 Listening for conversion complete events...")
        self.log_to_api("INFO", "Tagger service started and listening for Redis events")
        
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
    service = TaggerService()
    service.start()

if __name__ == "__main__":
    main()
