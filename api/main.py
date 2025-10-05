#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os
import requests
import json
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

# External service URLs
TRANSMISSION_HOST = os.getenv("TRANSMISSION_HOST", "transmission")
TRANSMISSION_PORT = os.getenv("TRANSMISSION_PORT", "9091")
TRANSMISSION_USER = os.getenv("TRANSMISSION_USER", "admin")
TRANSMISSION_PASS = os.getenv("TRANSMISSION_PASS", "admin")
AUTO_M4B_TAGGER_URL = os.getenv("AUTO_M4B_TAGGER_URL", "http://auto-m4b-tagger:8080")

# Security removed

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
    created_at: str
    updated_at: str
    download_status: Optional[str] = None
    download_date: Optional[str] = None

class Download(BaseModel):
    id: int
    rss_item_id: int
    status: str
    path: Optional[str]
    torrent_file: Optional[str]
    created_at: str
    updated_at: str

class LogEntry(BaseModel):
    id: int
    level: str
    message: str
    service: Optional[str]
    created_at: str

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
    path: str
    name: str
    status: str

# Authentication models and functions removed

# Database helper
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    # Enable WAL mode for better concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    conn.execute("PRAGMA temp_store=MEMORY")
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
            "conversion": "/conversion",
            "tagging": "/tagging",
            "logs": "/logs",
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }

# Authentication endpoint removed

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
            ORDER BY r.created_at DESC
        ''')
        items = []
        for row in cursor.fetchall():
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
                created_at=row[13],
                updated_at=row[14],
                download_status=row[15] if row[15] else 'not_downloaded',
                download_date=row[16] if row[16] else None
            )
            items.append(rss_item)
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
            downloads.append(Download(
                id=row[0],
                rss_item_id=row[1],
                status=row[2],
                path=row[3],
                torrent_file=row[4],
                created_at=row[5],
                updated_at=row[6]
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
        torrents_dir = "/app/torrents-storage"
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

@app.get("/conversion", response_model=List[ConversionItem])
async def get_conversion_items():
    """Get items in toMerge directory"""
    try:
        to_merge_dir = "/app/toMerge"
        items = []
        
        if os.path.exists(to_merge_dir):
            for item in os.listdir(to_merge_dir):
                item_path = os.path.join(to_merge_dir, item)
                if os.path.isdir(item_path):
                    items.append(ConversionItem(
                        path=item_path,
                        name=item,
                        status="waiting"
                    ))
        
        return items
    except Exception as e:
        logger.error(f"Error fetching conversion items: {e}")
        log_to_db("ERROR", f"Error fetching conversion items: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tagging", response_model=List[TaggingItem])
async def get_tagging_items():
    """Get items in toTag directory"""
    try:
        to_tag_dir = "/app/toTag"
        items = []
        
        if os.path.exists(to_tag_dir):
            for item in os.listdir(to_tag_dir):
                if item.endswith('.m4b'):
                    item_path = os.path.join(to_tag_dir, item)
                    items.append(TaggingItem(
                        path=item_path,
                        name=item,
                        status="waiting"
                    ))
        
        return items
    except Exception as e:
        logger.error(f"Error fetching tagging items: {e}")
        log_to_db("ERROR", f"Error fetching tagging items: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tagging/trigger")
async def trigger_tagging():
    """Trigger the auto-m4b-audible-tagger"""
    try:
        # This would typically call the auto-m4b-audible-tagger API
        # For now, we'll just log the action
        log_to_db("INFO", "Tagging triggered manually")
        return {"message": "Tagging process triggered"}
    except Exception as e:
        logger.error(f"Error triggering tagging: {e}")
        log_to_db("ERROR", f"Error triggering tagging: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs", response_model=List[LogEntry])
async def get_logs():
    """Get recent logs"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM logs ORDER BY created_at DESC LIMIT 100')
        logs = []
        for row in cursor.fetchall():
            logs.append(LogEntry(
                id=row[0],
                level=row[1],
                message=row[2],
                service=row[3],
                created_at=row[4]
            ))
        conn.close()
        return logs
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        log_to_db("ERROR", f"Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
