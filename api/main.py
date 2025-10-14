#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os
import requests
import json
import redis
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Audiobook Pipeline API",
    description="Central API for RSS-to-Audiobook pipeline",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration - Authentication removed

# Database path
DB_PATH = os.getenv("DB_PATH", "/app/db/rss.sqlite")

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# External service URLs
TRANSMISSION_HOST = os.getenv("TRANSMISSION_HOST", "transmission")
TRANSMISSION_PORT = os.getenv("TRANSMISSION_PORT", "9091")
TRANSMISSION_USER = os.getenv("TRANSMISSION_USER", "admin")
TRANSMISSION_PASS = os.getenv("TRANSMISSION_PASS", "admin")
# AUTO_M4B_TAGGER_URL removed - functionality integrated into API

# Pydantic models
class RSSItem(BaseModel):
    id: int
    title: str
    link: str
    pub_date: Optional[str]
    description: Optional[str]
    author: Optional[str]
    year: Optional[str]
    format: Optional[str]
    file_size: Optional[str]
    seeders: int
    leechers: int
    torrent_url: Optional[str]
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]
    download_status: Optional[str] = None
    download_date: Optional[str] = None

class Download(BaseModel):
    id: int
    rss_item_id: int
    status: str
    path: Optional[str]
    torrent_file: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

class LogEntry(BaseModel):
    id: int
    level: str
    message: str
    service: Optional[str]
    created_at: Optional[str]

class TorrentInfo(BaseModel):
    id: int
    name: str
    status: str
    progress: float
    downloadDir: str

class ConversionItem(BaseModel):
    path: str
    name: str
    status: str

class TaggingItem(BaseModel):
    id: Optional[int] = None
    name: str
    path: str
    folder: Optional[str] = None
    status: str
    size: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class TaggingItemCreate(BaseModel):
    name: str
    path: str
    folder: Optional[str] = None
    status: str = "waiting"
    size: Optional[int] = None

class AudibleSearchRequest(BaseModel):
    query: str
    locale: str = "com"

class AudibleBookData(BaseModel):
    asin: str
    title: str
    author: str
    narrator: Optional[str] = None
    series: Optional[str] = None
    series_part: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    duration: Optional[str] = None
    release_date: Optional[str] = None
    language: Optional[str] = None
    publisher: Optional[str] = None
    locale: str = "com"

class TagFileRequest(BaseModel):
    file_path: str
    book_data: AudibleBookData

class ParseFilenameRequest(BaseModel):
    filename: str

class ConversionTracking(BaseModel):
    id: int
    book_name: str
    total_files: int
    converted_files: int
    current_file: Optional[str]
    status: str
    progress_percentage: float
    estimated_eta_seconds: Optional[int]
    merge_folder_path: Optional[str]
    temp_folder_path: Optional[str]
    created_at: str
    updated_at: str
    
    @property
    def estimated_eta_formatted(self) -> Optional[str]:
        """Format ETA in human-readable format"""
        if not self.estimated_eta_seconds:
            return None
        
        seconds = self.estimated_eta_seconds
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds}s" if remaining_seconds > 0 else f"{minutes}m"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            return f"{hours}h {remaining_minutes}m" if remaining_minutes > 0 else f"{hours}h"

class ConversionJob(BaseModel):
    id: int
    rss_item_id: Optional[int]
    book_name: str
    source_path: str
    backup_path: Optional[str]
    status: str
    attempts: int
    max_attempts: int
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]
    created_at: str
    updated_at: str

class ConversionTriggerRequest(BaseModel):
    book_name: str
    source_path: str
    rss_item_id: Optional[int] = None

class ConversionRetryRequest(BaseModel):
    force: bool = False

class BackupInfo(BaseModel):
    name: str
    path: str
    size: int
    created: str
    modified: str


# Database helper
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    # Enable WAL mode for better concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
    return conn

def log_to_db(level: str, message: str, service: str = "api"):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO logs (level, message, service) VALUES (?, ?, ?)',
            (level, message, service)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log to database: {e}")

# Redis helper
def get_redis_client():
    """Get Redis client connection"""
    try:
        return redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None

def publish_redis_event(channel: str, message: dict):
    """Publish event to Redis channel"""
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.publish(channel, json.dumps(message))
            logger.info(f"Published to {channel}: {message}")
        else:
            logger.error(f"Failed to publish to {channel}: Redis not available")
    except Exception as e:
        logger.error(f"Failed to publish to {channel}: {e}")

# Transmission RPC helper
def transmission_rpc(method: str, arguments: dict = None):
    url = f"http://{TRANSMISSION_HOST}:{TRANSMISSION_PORT}/transmission/rpc"
    
    headers = {
        "Content-Type": "application/json",
        "X-Transmission-Session-Id": getattr(transmission_rpc, 'session_id', '')
    }
    
    data = {
        "method": method,
        "arguments": arguments or {}
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, 
                               auth=(TRANSMISSION_USER, TRANSMISSION_PASS), timeout=10)
        
        if response.status_code == 409:  # Session ID required
            session_id = response.headers.get('X-Transmission-Session-Id')
            transmission_rpc.session_id = session_id
            headers["X-Transmission-Session-Id"] = session_id
            response = requests.post(url, json=data, headers=headers,
                                   auth=(TRANSMISSION_USER, TRANSMISSION_PASS), timeout=10)
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Transmission RPC error: {e}")
        raise HTTPException(status_code=500, detail=f"Transmission RPC error: {e}")


# Routes
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Audiobook Pipeline API",
        "version": "1.0.0",
        "endpoints": {
            "rss_items": "/rss-items",
            "downloads": "/downloads", 
            "torrents": "/torrents",
            "tagging": "/tagging",
            "conversions": "/conversions",
            "logs": "/logs",
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }


@app.get("/rss-items", response_model=List[RSSItem])
async def get_rss_items():
    """Get all RSS items with download status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Join with downloads table to get download status
        cursor.execute('''
            SELECT r.*, d.status as download_status, d.created_at as download_date
            FROM rss_items r
            LEFT JOIN downloads d ON r.id = d.rss_item_id
        ''')
        items = []
        for row in cursor.fetchall():
            # Convert timestamps to ISO format strings
            def format_timestamp(timestamp):
                if timestamp is None:
                    return None
                if isinstance(timestamp, (int, float)):
                    # Unix timestamp
                    return datetime.fromtimestamp(timestamp).isoformat()
                elif isinstance(timestamp, str):
                    # Already a string, return as-is
                    return timestamp
                else:
                    return str(timestamp)
            
            # Create RSSItem with download status
            rss_item = RSSItem(
                id=row[0],
                title=row[1],
                link=row[2],
                pub_date=row[3],
                description=row[4],
                author=row[5],
                year=row[6],
                format=row[7],
                file_size=row[8],
                seeders=row[9],
                leechers=row[10],
                torrent_url=row[11],
                status=row[12],
                created_at=format_timestamp(row[17]) or datetime.now().isoformat(),
                updated_at=format_timestamp(row[18]) or datetime.now().isoformat(),
                download_status=row[19] if row[19] else 'not_downloaded',
                download_date=format_timestamp(row[20]) if row[20] else None
            )
            items.append(rss_item)
        
        # Sort items by publication date (newer first)
        def parse_pub_date(pub_date_str):
            if not pub_date_str:
                return datetime.min
            try:
                # All dates are stored in RFC 2822 format
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(pub_date_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse pub_date '{pub_date_str}': {e}")
                return datetime.min
        
        items.sort(key=lambda x: parse_pub_date(x.pub_date), reverse=True)
        conn.close()
        return items
    except Exception as e:
        logger.error(f"Error fetching RSS items: {e}")
        log_to_db("ERROR", f"Error fetching RSS items: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/downloads", response_model=List[Download])
async def get_downloads():
    """Get all downloads"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM downloads ORDER BY created_at DESC')
        downloads = []
        for row in cursor.fetchall():
            # Convert timestamps to ISO format strings
            def format_timestamp(timestamp):
                if timestamp is None:
                    return None
                if isinstance(timestamp, (int, float)):
                    # Unix timestamp
                    return datetime.fromtimestamp(timestamp).isoformat()
                elif isinstance(timestamp, str):
                    # Already a string, return as-is
                    return timestamp
                else:
                    return str(timestamp)
            
            downloads.append(Download(
                id=row[0],
                rss_item_id=row[1],
                status=row[2],
                path=row[3],
                torrent_file=row[4],
                created_at=format_timestamp(row[5]),
                updated_at=format_timestamp(row[6])
            ))
        conn.close()
        return downloads
    except Exception as e:
        logger.error(f"Error fetching downloads: {e}")
        log_to_db("ERROR", f"Error fetching downloads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/torrents", response_model=List[TorrentInfo])
async def get_torrents():
    """Get active torrents from Transmission"""
    try:
        result = transmission_rpc("torrent-get", {
            "fields": ["id", "name", "status", "percentDone", "downloadDir"]
        })
        
        torrents = []
        for torrent in result.get("arguments", {}).get("torrents", []):
            torrents.append(TorrentInfo(
                id=torrent["id"],
                name=torrent["name"],
                status=str(torrent["status"]),
                progress=torrent["percentDone"] * 100,
                downloadDir=torrent["downloadDir"]
            ))
        
        return torrents
    except Exception as e:
        logger.error(f"Error fetching torrents: {e}")
        log_to_db("ERROR", f"Error fetching torrents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/torrents/{torrent_id}/start")
async def start_torrent(torrent_id: int):
    """Start a torrent"""
    try:
        result = transmission_rpc("torrent-start", {"ids": [torrent_id]})
        log_to_db("INFO", f"Started torrent {torrent_id}")
        return {"message": f"Torrent {torrent_id} started"}
    except Exception as e:
        logger.error(f"Error starting torrent: {e}")
        log_to_db("ERROR", f"Error starting torrent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/torrents/{torrent_id}/stop")
async def stop_torrent(torrent_id: int):
    """Stop a torrent"""
    try:
        result = transmission_rpc("torrent-stop", {"ids": [torrent_id]})
        log_to_db("INFO", f"Stopped torrent {torrent_id}")
        return {"message": f"Torrent {torrent_id} stopped"}
    except Exception as e:
        logger.error(f"Error stopping torrent: {e}")
        log_to_db("ERROR", f"Error stopping torrent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/torrents/add")
async def add_torrent(request: dict):
    """Manually add a torrent file to Transmission using RSS item ID"""
    try:
        rss_item_id = request.get("rss_item_id")
        if not rss_item_id:
            raise HTTPException(status_code=400, detail="rss_item_id is required")
            
        # Get torrent file path from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT torrent_file FROM downloads WHERE rss_item_id = ? AND status = "downloaded"',
            (rss_item_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="Torrent file not found for this RSS item")
            
        torrent_path = result[0]
        if not os.path.exists(torrent_path):
            raise HTTPException(status_code=404, detail="Torrent file not found on disk")
        
        # Read torrent file content
        with open(torrent_path, 'rb') as f:
            torrent_data = f.read()
        
        # Add torrent to Transmission (use base64 encoding)
        import base64
        result = transmission_rpc("torrent-add", {
            "metainfo": base64.b64encode(torrent_data).decode('utf-8'),
            "download-dir": "/downloads"
        })
        
        if result.get("result") == "success":
            # Update download status to indicate torrent was added to Transmission
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE downloads SET status = "transmission_added", updated_at = CURRENT_TIMESTAMP WHERE rss_item_id = ?',
                (rss_item_id,)
            )
            conn.commit()
            conn.close()
            
            log_to_db("INFO", f"Added torrent to Transmission for RSS item {rss_item_id}")
            return {"message": f"Torrent for RSS item {rss_item_id} added successfully"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to add torrent: {result}")
            
    except Exception as e:
        logger.error(f"Error adding torrent: {e}")
        log_to_db("ERROR", f"Error adding torrent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/torrents/available")
async def get_available_torrents():
    """Get list of available torrent files that can be added to Transmission"""
    try:
        torrents_dir = "/app/saved-torrents-files"
        torrent_files = []
        
        if os.path.exists(torrents_dir):
            for filename in os.listdir(torrents_dir):
                if filename.endswith('.torrent'):
                    file_path = os.path.join(torrents_dir, filename)
                    file_size = os.path.getsize(file_path)
                    torrent_files.append({
                        "filename": filename,
                        "size": file_size,
                        "path": file_path
                    })
        
        return {"torrents": torrent_files}
        
    except Exception as e:
        logger.error(f"Error listing torrents: {e}")
        log_to_db("ERROR", f"Error listing torrents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tagging", response_model=List[TaggingItem])
async def get_tagging_items():
    """Get tagging items from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tagging_items ORDER BY created_at DESC')
        items = []
        for row in cursor.fetchall():
            items.append(TaggingItem(
                id=row[0],
                name=row[1],
                path=row[2],
                folder=row[3],
                status=row[4],
                size=row[5],
                created_at=row[6],
                updated_at=row[7]
            ))
        conn.close()
        return items
    except Exception as e:
        logger.error(f"Error fetching tagging items: {e}")
        log_to_db("ERROR", f"Error fetching tagging items: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tagging/items", response_model=TaggingItem)
async def create_tagging_item(item: TaggingItemCreate):
    """Create a new tagging item"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if item already exists
        cursor.execute(
            'SELECT id FROM tagging_items WHERE path = ?',
            (item.path,)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing item
            cursor.execute('''
                UPDATE tagging_items 
                SET name = ?, folder = ?, status = ?, size = ?, updated_at = CURRENT_TIMESTAMP
                WHERE path = ?
            ''', (item.name, item.folder, item.status, item.size, item.path))
            item_id = existing[0]
        else:
            # Create new item
            cursor.execute('''
                INSERT INTO tagging_items (name, path, folder, status, size)
                VALUES (?, ?, ?, ?, ?)
            ''', (item.name, item.path, item.folder, item.status, item.size))
            item_id = cursor.lastrowid
        
        conn.commit()
        
        # Get the created/updated item
        cursor.execute('SELECT * FROM tagging_items WHERE id = ?', (item_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return TaggingItem(
                id=row[0],
                name=row[1],
                path=row[2],
                folder=row[3],
                status=row[4],
                size=row[5],
                created_at=row[6],
                updated_at=row[7]
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create tagging item")
            
    except Exception as e:
        logger.error(f"Error creating tagging item: {e}")
        log_to_db("ERROR", f"Error creating tagging item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/tagging/items/{item_id}/status")
async def update_tagging_item_status(item_id: int, status: str):
    """Update tagging item status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tagging_items 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, item_id))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Tagging item not found")
        
        conn.commit()
        conn.close()
        
        log_to_db("INFO", f"Updated tagging item {item_id} status to {status}")
        return {"message": f"Tagging item {item_id} status updated to {status}"}
        
    except Exception as e:
        logger.error(f"Error updating tagging item status: {e}")
        log_to_db("ERROR", f"Error updating tagging item status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tagging/status")
async def get_tagging_status():
    """Get the status of the integrated tagging service"""
    try:
        # Check if our integrated tagging modules are available
        try:
            import sys
            # Add tagger directory to Python path
            tagger_path = '/app/tagger'
            if tagger_path not in sys.path:
                sys.path.insert(0, tagger_path)
            from audible_client import AudibleAPIClient
            from m4b_tagger import M4BTagger
            
            return {
                "service": "integrated-tagger",
                "status": "healthy",
                "features": ["audible-search", "m4b-tagging", "cover-download"]
            }
        except ImportError as e:
            return {
                "service": "integrated-tagger",
                "status": "unhealthy",
                "error": f"Missing modules: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"Error checking tagging status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tagging/search")
async def search_audible_books(request: AudibleSearchRequest):
    """Search Audible for books matching the query"""
    try:
        # Import the AudibleAPIClient
        import sys
        import os
        # Add tagger directory to Python path
        tagger_path = '/app/tagger'
        if tagger_path not in sys.path:
            sys.path.insert(0, tagger_path)
        from audible_client import AudibleAPIClient
        
        client = AudibleAPIClient()
        
        # First try the main search
        results = client.search_audible(request.query, request.locale)
        
        # If no results, try alternative strategies
        if not results:
            results = client.handle_no_search_results(request.query, request.locale)
        
        log_to_db("INFO", f"Audible search performed: '{request.query}' - {len(results)} results")
        return {"results": results}
        
    except Exception as e:
        logger.error(f"Error searching Audible: {e}")
        log_to_db("ERROR", f"Error searching Audible: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tagging/parse-filename")
async def parse_filename_for_search(request: ParseFilenameRequest):
    """Parse filename to extract title and author for search"""
    try:
        # Import the AudibleAPIClient
        import sys
        import os
        # Add tagger directory to Python path
        tagger_path = '/app/tagger'
        if tagger_path not in sys.path:
            sys.path.insert(0, tagger_path)
        from audible_client import AudibleAPIClient
        
        client = AudibleAPIClient()
        title, author = client.parse_filename(request.filename)
        
        # Build search query similar to original implementation
        if author == "Unknown Author":
            search_query = title.strip()
        else:
            search_query = f"{title} {author}".strip()
            # Remove common words that might interfere with search
            import re
            search_query = re.sub(
                r'\b(by|the|and|or|in|on|at|to|for|of|with|from)\b',
                '',
                search_query,
                flags=re.IGNORECASE
            )
            # Clean up extra whitespace
            search_query = re.sub(r'\s+', ' ', search_query).strip()
        
        return {
            "filename": request.filename,
            "title": title,
            "author": author,
            "suggested_query": search_query
        }
        
    except Exception as e:
        logger.error(f"Error parsing filename: {e}")
        log_to_db("ERROR", f"Error parsing filename: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tagging/tag-file")
async def tag_file_with_metadata(request: TagFileRequest):
    """Tag a file with selected book metadata"""
    try:
        logger.info(f"Starting tag-file request for: {request.file_path}")
        logger.info(f"Book data: {request.book_data}")
        
        # Import the M4BTagger
        import sys
        import os
        # Add tagger directory to Python path
        tagger_path = '/app/tagger'
        if tagger_path not in sys.path:
            sys.path.insert(0, tagger_path)
        logger.info("Importing tagger modules...")
        from m4b_tagger import M4BTagger
        from audible_client import AudibleAPIClient
        from pathlib import Path
        logger.info("Tagger modules imported successfully")
        
        file_path = Path(request.file_path)
        logger.info(f"Checking file path: {file_path}")
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            raise HTTPException(status_code=404, detail="File not found")
        
        # Create directories
        library_dir = Path("/app/library")
        covers_dir = Path("/app/covers")
        logger.info(f"Library dir: {library_dir}, Covers dir: {covers_dir}")
        
        # Initialize tagger
        logger.info("Initializing M4BTagger...")
        tagger = M4BTagger(library_dir, covers_dir)
        logger.info("M4BTagger initialized successfully")
        
        # Download cover if available
        cover_path = None
        if request.book_data.cover_url:
            logger.info(f"Downloading cover from: {request.book_data.cover_url}")
            client = AudibleAPIClient()
            cover_path = client.download_cover(
                request.book_data.cover_url,
                request.book_data.asin,
                covers_dir
            )
            logger.info(f"Cover downloaded to: {cover_path}")
        else:
            logger.info("No cover URL provided")
        
        # Convert Pydantic model to dict
        book_data = request.book_data.dict()
        logger.info(f"Book data converted to dict: {book_data}")
        
        # Tag the file
        logger.info("Starting file tagging...")
        if tagger.tag_file(file_path, book_data, cover_path):
            # Move to library
            dest_path = tagger.move_to_library(file_path, book_data, cover_path)
            
            if dest_path:
                # Update database status
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tagging_items 
                    SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                    WHERE path = ?
                ''', (str(file_path),))
                conn.commit()
                conn.close()
                
                log_to_db("INFO", f"Successfully tagged and moved file: {file_path.name}")
                return {
                    "message": "File tagged and moved successfully",
                    "destination": str(dest_path)
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to move file to library")
        else:
            raise HTTPException(status_code=500, detail="Failed to tag file")
            
    except HTTPException:
        # Re-raise HTTPExceptions (like 404 File not found) without modification
        raise
    except Exception as e:
        import traceback
        error_msg = str(e) if str(e) else "Unknown error occurred"
        error_traceback = traceback.format_exc()
        
        logger.error(f"Error tagging file: {error_msg}")
        logger.error(f"Full traceback: {error_traceback}")
        log_to_db("ERROR", f"Error tagging file: {error_msg}")
        
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/logs", response_model=List[LogEntry])
async def get_logs():
    """Get recent logs"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM logs ORDER BY created_at DESC LIMIT 100')
        logs = []
        for row in cursor.fetchall():
            # Convert timestamps to ISO format strings
            def format_timestamp(timestamp):
                if timestamp is None:
                    return None
                if isinstance(timestamp, (int, float)):
                    # Unix timestamp
                    return datetime.fromtimestamp(timestamp).isoformat()
                elif isinstance(timestamp, str):
                    # Already a string, return as-is
                    return timestamp
                else:
                    return str(timestamp)
            
            logs.append(LogEntry(
                id=row[0],
                level=row[1],
                message=row[2],
                service=row[3],
                created_at=format_timestamp(row[4])
            ))
        conn.close()
        return logs
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        log_to_db("ERROR", f"Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ExternalLogRequest(BaseModel):
    level: str
    message: str
    service: Optional[str] = "external"

@app.post("/logs/external")
async def log_external(request: ExternalLogRequest):
    """Log a message from external services"""
    try:
        log_to_db(request.level, request.message, request.service)
        return {"message": "Log entry created successfully"}
    except Exception as e:
        logger.error(f"Error logging external message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversions", response_model=List[ConversionTracking])
async def get_conversions():
    """Get all conversion tracking records"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM conversion_tracking ORDER BY created_at DESC')
        conversions = []
        for row in cursor.fetchall():
            conversions.append(ConversionTracking(
                id=row[0],
                book_name=row[1],
                total_files=row[2],
                converted_files=row[3],
                current_file=row[4],
                status=row[5],
                progress_percentage=row[6],
                estimated_eta_seconds=row[7],
                merge_folder_path=row[8],
                temp_folder_path=row[9],
                created_at=row[10],
                updated_at=row[11]
            ))
        conn.close()
        return conversions
    except Exception as e:
        logger.error(f"Error fetching conversions: {e}")
        log_to_db("ERROR", f"Error fetching conversions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversions/{conversion_id}", response_model=ConversionTracking)
async def get_conversion(conversion_id: int):
    """Get a specific conversion tracking record"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM conversion_tracking WHERE id = ?', (conversion_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Conversion tracking record not found")
        
        return ConversionTracking(
            id=row[0],
            book_name=row[1],
            total_files=row[2],
            converted_files=row[3],
            current_file=row[4],
            status=row[5],
            progress_percentage=row[6],
            estimated_eta_seconds=row[7],
            merge_folder_path=row[8],
            temp_folder_path=row[9],
            created_at=row[10],
            updated_at=row[11]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversion: {e}")
        log_to_db("ERROR", f"Error fetching conversion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# New conversion management endpoints
@app.post("/conversions/trigger")
async def trigger_conversion(request: ConversionTriggerRequest):
    """Manually trigger conversion for a book"""
    try:
        # Publish Redis event to trigger conversion
        message = {
            "book_name": request.book_name,
            "path": request.source_path,
            "rss_item_id": request.rss_item_id
        }
        
        publish_redis_event("audiobook:download_complete", message)
        log_to_db("INFO", f"Manually triggered conversion for: {request.book_name}")
        
        return {"message": f"Conversion triggered for {request.book_name}"}
        
    except Exception as e:
        logger.error(f"Error triggering conversion: {e}")
        log_to_db("ERROR", f"Error triggering conversion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversions/{conversion_id}/retry")
async def retry_conversion(conversion_id: int, request: ConversionRetryRequest):
    """Retry a failed conversion"""
    try:
        logger.info(f"Retry request for conversion_id: {conversion_id}, force: {request.force}")
        
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get conversion tracking details
        cursor.execute('SELECT * FROM conversion_tracking WHERE id = ?', (conversion_id,))
        tracking = cursor.fetchone()
        
        if not tracking:
            conn.close()
            raise HTTPException(status_code=404, detail="Conversion tracking record not found")
        
        # Get the book name from tracking record
        book_name = tracking[1]  # book_name is at index 1
        
        # Find the corresponding conversion job if it exists
        cursor.execute('SELECT * FROM conversion_jobs WHERE book_name = ? ORDER BY created_at DESC LIMIT 1', (book_name,))
        job = cursor.fetchone()
        
        # Check if retry is allowed (only if we have a job record)
        if job:
            attempts = int(job[6]) if job[6] is not None else 0      # attempts is at index 6
            max_attempts = int(job[7]) if job[7] is not None else 3  # max_attempts is at index 7
            if attempts >= max_attempts and not request.force:
                conn.close()
                raise HTTPException(status_code=400, detail="Maximum retry attempts reached. Use force=true to override.")
        
        # Publish retry event
        message = {
            "book_name": book_name,
            "rss_item_id": job[1] if job else None,  # rss_item_id from job if available
            "conversion_id": conversion_id
        }
        
        publish_redis_event("audiobook:retry_conversion", message)
        
        conn.close()
        return {"message": f"Retry triggered for conversion {conversion_id}", "book_name": book_name}
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error retrying conversion: {e}")
        logger.error(f"Full traceback: {error_traceback}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/conversions/{conversion_id}/cancel")
async def cancel_conversion(conversion_id: int):
    """Cancel an in-progress conversion"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update job status to cancelled
        cursor.execute('''
            UPDATE conversion_jobs 
            SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'processing'
        ''', (conversion_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Conversion job not found or not in progress")
        
        conn.commit()
        conn.close()
        
        log_to_db("INFO", f"Cancelled conversion {conversion_id}")
        return {"message": f"Conversion {conversion_id} cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling conversion: {e}")
        log_to_db("ERROR", f"Error cancelling conversion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversions/jobs", response_model=List[ConversionJob])
async def get_conversion_jobs():
    """Get all conversion jobs"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM conversion_jobs ORDER BY created_at DESC')
        jobs = []
        for row in cursor.fetchall():
            jobs.append(ConversionJob(
                id=row[0],
                rss_item_id=row[1],
                book_name=row[2],
                source_path=row[3],
                backup_path=row[4],
                status=row[5],
                attempts=row[6],
                max_attempts=row[7],
                started_at=row[8],
                completed_at=row[9],
                error_message=row[10],
                created_at=row[11],
                updated_at=row[12]
            ))
        conn.close()
        return jobs
    except Exception as e:
        logger.error(f"Error fetching conversion jobs: {e}")
        log_to_db("ERROR", f"Error fetching conversion jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversions/backups", response_model=List[BackupInfo])
async def get_backups():
    """Get list of all backups with metadata"""
    try:
        import os
        from pathlib import Path
        
        backup_dir = Path("/app/conversion-backups")
        backups = []
        
        if backup_dir.exists():
            for backup_path in backup_dir.iterdir():
                if backup_path.is_dir():
                    # Calculate total size
                    total_size = sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file())
                    
                    backups.append(BackupInfo(
                        name=backup_path.name,
                        path=str(backup_path),
                        size=total_size,
                        created=datetime.fromtimestamp(backup_path.stat().st_ctime).isoformat(),
                        modified=datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat()
                    ))
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x.created, reverse=True)
        return backups
        
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        log_to_db("ERROR", f"Error listing backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/conversions/backups/{backup_name}")
async def delete_backup(backup_name: str):
    """Delete a specific backup"""
    try:
        import shutil
        from pathlib import Path
        
        backup_path = Path("/app/conversion-backups") / backup_name
        
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup not found")
        
        shutil.rmtree(backup_path)
        log_to_db("INFO", f"Deleted backup: {backup_name}")
        
        return {"message": f"Backup {backup_name} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting backup: {e}")
        log_to_db("ERROR", f"Error deleting backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/health")
async def system_health():
    """Overall system health check"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }
        
        # Check Redis
        redis_client = get_redis_client()
        if redis_client:
            try:
                redis_client.ping()
                health_status["services"]["redis"] = "healthy"
            except:
                health_status["services"]["redis"] = "unhealthy"
                health_status["status"] = "degraded"
        else:
            health_status["services"]["redis"] = "unavailable"
            health_status["status"] = "degraded"
        
        # Check database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            health_status["services"]["database"] = "healthy"
        except:
            health_status["services"]["database"] = "unhealthy"
            health_status["status"] = "unhealthy"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.get("/system/redis/status")
async def redis_status():
    """Redis connection status"""
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.ping()
            return {"status": "connected", "host": REDIS_HOST, "port": REDIS_PORT}
        else:
            return {"status": "disconnected", "error": "Failed to create Redis client"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
