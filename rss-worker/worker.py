#!/usr/bin/env python3
import feedparser
import sqlite3
import os
import sys
import logging
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RSSWorker:
    def __init__(self):
        self.rss_url = os.getenv('RSS_FEED_URL', 'https://example.com/feed.xml')
        self.db_path = os.getenv('DB_PATH', '/app/db/rss.sqlite')
        self.torrents_dir = '/app/saved-torrents-files'
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.torrents_dir, exist_ok=True)
        
        self.scheduler = BlockingScheduler()
        
    def get_db_connection(self):
        """Get database connection with proper settings"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        # Enable WAL mode for better concurrent access
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
        return conn

    def log_to_db(self, level, message):
        """Log message to database with retry logic"""
        max_retries = 5
        for attempt in range(max_retries):
            conn = None
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO logs (level, message, service) VALUES (?, ?, ?)',
                    (level, message, 'rss-worker')
                )
                conn.commit()
                return  # Success, exit the retry loop
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                if ("database is locked" in error_msg or "locking protocol" in error_msg) and attempt < max_retries - 1:
                    # Wait a bit and retry with exponential backoff
                    import time
                    wait_time = 0.5 * (2 ** attempt)  # Exponential backoff: 0.5, 1, 2, 4 seconds
                    logger.warning(f"Database locked, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Failed to log to database after {attempt + 1} attempts: {e}")
                    break
            except Exception as e:
                logger.error(f"Failed to log to database: {e}")
                break
            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
    
    def download_torrent(self, torrent_url, title):
        """Download torrent file"""
        try:
            # Sanitize filename
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_title}.torrent"
            filepath = os.path.join(self.torrents_dir, filename)
            
            response = requests.get(torrent_url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded torrent: {filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to download torrent {torrent_url}: {e}")
            return None
    
    def parse_yggtorrent_entry(self, entry):
        """Parse YggTorrent RSS entry to extract structured data"""
        import re
        
        # Extract author, year, and format from title
        # Example: "Louis-San - Jiken 2 - Faits réels au Japon [2025] [mp3 à 128 Kb/s]"
        title = entry.title
        author = ""
        year = ""
        format_info = ""
        
        # Try to extract year and format from title
        year_match = re.search(r'\[(\d{4})\]', title)
        if year_match:
            year = year_match.group(1)
        
        format_match = re.search(r'\[([^\]]*mp3[^\]]*)\]', title)
        if format_match:
            format_info = format_match.group(1)
        
        # Extract author (everything before the first " - " that contains year/format)
        author_match = re.match(r'^([^-]+(?: - [^-]+)*?)(?:\s*-\s*[^[]*\[)', title)
        if author_match:
            author = author_match.group(1).strip()
        
        # Parse description for additional metadata
        description = entry.get('description', '')
        file_size = ""
        seeders = 0
        leechers = 0
        
        # Extract file size
        size_match = re.search(r'Taille de l\'upload:\s*([0-9.]+[A-Za-z]+)', description)
        if size_match:
            file_size = size_match.group(1)
        
        # Extract seeders and leechers
        seeder_match = re.search(r'(\d+)\s*seeders', description)
        if seeder_match:
            seeders = int(seeder_match.group(1))
        
        leecher_match = re.search(r'(\d+)\s*leechers', description)
        if leecher_match:
            leechers = int(leecher_match.group(1))
        
        return {
            'title': title,
            'author': author,
            'year': year,
            'format': format_info,
            'file_size': file_size,
            'seeders': seeders,
            'leechers': leechers,
            'description': description
        }

    def process_rss_feed(self):
        """Process RSS feed and download new torrents"""
        max_retries = 3
        for attempt in range(max_retries):
            conn = None
            try:
                logger.info(f"Processing RSS feed: {self.rss_url} (attempt {attempt + 1}/{max_retries})")
                
                # Parse RSS feed
                feed = feedparser.parse(self.rss_url)
                
                if feed.bozo:
                    logger.warning(f"RSS feed parsing warning: {feed.bozo_exception}")
                
                # Use a single connection for the entire operation
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                # Write initial log message to database
                cursor.execute(
                    'INSERT INTO logs (level, message, service) VALUES (?, ?, ?)',
                    ('INFO', f"Processing RSS feed: {self.rss_url}", 'rss-worker')
                )
            
                new_items = 0
                # Process entries in reverse order so newest items get higher IDs
                for entry in reversed(feed.entries):
                    # Check if item already exists
                    cursor.execute('SELECT id FROM rss_items WHERE link = ?', (entry.link,))
                    if cursor.fetchone():
                        continue
                
                    # Parse structured data from YggTorrent entry
                    parsed_data = self.parse_yggtorrent_entry(entry)
                
                    # Insert new RSS item with all parsed data
                    pub_date = entry.get('published', '')
                    
                    # Keep the original RFC 2822 format from the RSS feed
                    if not pub_date:
                        # If no pub_date, use current timestamp in RFC 2822 format
                        from email.utils import formatdate
                        pub_date = formatdate()
                    
                    cursor.execute('''
                        INSERT INTO rss_items 
                        (title, link, pub_date, description, author, year, format, 
                         file_size, seeders, leechers, status) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        parsed_data['title'], 
                        entry.link, 
                        pub_date,
                        parsed_data['description'],
                        parsed_data['author'],
                        parsed_data['year'],
                        parsed_data['format'],
                        parsed_data['file_size'],
                        parsed_data['seeders'],
                        parsed_data['leechers'],
                        'new'
                    ))
                    rss_item_id = cursor.lastrowid
                
                    # Look for torrent links in the entry
                    torrent_url = None
                    if hasattr(entry, 'enclosures'):
                        for enclosure in entry.enclosures:
                            if enclosure.type == 'application/x-bittorrent':
                                torrent_url = enclosure.href
                                break
                    
                    # Also check for torrent links in content
                    if not torrent_url and hasattr(entry, 'content'):
                        for content in entry.content:
                            if '.torrent' in content.value:
                                # Extract torrent URL from content
                                import re
                                torrent_match = re.search(r'https?://[^\s]+\.torrent', content.value)
                                if torrent_match:
                                    torrent_url = torrent_match.group(0)
                                    break
                    
                    # For YggTorrent, the torrent URL is typically in the link
                    if not torrent_url and 'yggtorrent' in entry.link:
                        # Construct torrent download URL from the page link
                        torrent_url = entry.link.replace('/torrent/', '/torrent/download/')
                    
                    if torrent_url:
                        # Update the torrent_url in the database
                        cursor.execute(
                            'UPDATE rss_items SET torrent_url = ? WHERE id = ?',
                            (torrent_url, rss_item_id)
                        )
                        
                        # Download torrent file
                        torrent_path = self.download_torrent(torrent_url, parsed_data['title'])
                        if torrent_path:
                            # Create download record
                            cursor.execute(
                                'INSERT INTO downloads (rss_item_id, status, torrent_file) VALUES (?, ?, ?)',
                                (rss_item_id, 'downloaded', torrent_path)
                            )
                            logger.info(f"Added new item: {parsed_data['title']} by {parsed_data['author']}")
                            new_items += 1
                    else:
                        logger.warning(f"No torrent found for: {parsed_data['title']}")
                
                # Write final log message to database
                cursor.execute(
                    'INSERT INTO logs (level, message, service) VALUES (?, ?, ?)',
                    ('INFO', f"RSS processing complete. New items: {new_items}", 'rss-worker')
                )
                
                conn.commit()
                logger.info(f"RSS processing complete. New items: {new_items}")
                return  # Success, exit retry loop
                
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                if ("database is locked" in error_msg or "locking protocol" in error_msg) and attempt < max_retries - 1:
                    # Wait and retry
                    import time
                    wait_time = 1.0 * (2 ** attempt)  # Exponential backoff: 1, 2, 4 seconds
                    logger.warning(f"Database locked during RSS processing, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Database error processing RSS feed after {attempt + 1} attempts: {e}")
                    self.log_to_db('ERROR', f"Database error processing RSS feed: {e}")
                    break
            except Exception as e:
                logger.error(f"Error processing RSS feed: {e}")
                self.log_to_db('ERROR', f"Error processing RSS feed: {e}")
                break
            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
    
    def start(self):
        """Start the RSS worker scheduler"""
        logger.info("Starting RSS worker...")
        self.log_to_db('INFO', 'RSS worker started')
        
        # Schedule RSS processing every hour
        self.scheduler.add_job(
            self.process_rss_feed,
            trigger=IntervalTrigger(hours=1),
            id='rss_processor',
            name='RSS Feed Processor',
            replace_existing=True
        )
        
        # Run once immediately
        self.process_rss_feed()
        
        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("RSS worker stopped")
            self.log_to_db('INFO', 'RSS worker stopped')
            self.scheduler.shutdown()

if __name__ == "__main__":
    worker = RSSWorker()
    worker.start()
