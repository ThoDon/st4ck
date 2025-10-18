#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import requests
import os
import logging
from datetime import datetime
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YGG Gateway API",
    description="Gateway service for YGG API integration",
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

# Configuration
YGG_API_BASE_URL = os.getenv("YGG_API_BASE_URL", "https://yggapi.eu")
YGG_API_KEY = os.getenv("YGG_API_KEY", "")

# Pydantic models
class YGGSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    limit: Optional[int] = 50

class YGGTorrent(BaseModel):
    id: int
    title: str
    category_id: int
    size: int
    seeders: int
    leechers: int
    downloads: Optional[int] = None
    uploaded_at: str
    link: str
    slug: Optional[str] = None  # deprecated field

class YGGSearchResponse(BaseModel):
    torrents: List[YGGTorrent]
    total: int
    page: int
    per_page: int

# Categories models removed - YGG API doesn't provide categories

class TorrentDownloadRequest(BaseModel):
    torrent_id: str
    download_type: str = "magnet"  # "magnet" or "torrent"

class TorrentDownloadResponse(BaseModel):
    success: bool
    message: str
    download_url: Optional[str] = None
    magnet_url: Optional[str] = None
    torrent_content: Optional[str] = None
    download_type: Optional[str] = None

# YGG API client
class YGGAPIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def search_torrents(self, query: str, category: Optional[str] = None, limit: int = 50, page: int = 1) -> Dict[str, Any]:
        """Search for torrents using YGG API"""
        try:
            # Convert limit to valid per_page value
            per_page = "25" if limit <= 25 else "50" if limit <= 50 else "100"
            
            params = {
                "q": query,
                "page": page,
                "per_page": per_page,
                "order_by": "uploaded_at"
            }
            
            # Convert category string to integer if provided
            if category and category.isdigit():
                params["category_id"] = int(category)
            
            response = self.session.get(f"{self.base_url}/torrents", params=params, timeout=30)
            response.raise_for_status()
            
            # The API returns an array directly, not wrapped in an object
            torrents = response.json()
            
            # Transform to match our expected format
            return {
                "torrents": torrents,
                "total": len(torrents),  # API doesn't provide total count
                "page": page,
                "per_page": int(per_page)
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"YGG API search error: {e}")
            raise HTTPException(status_code=500, detail=f"YGG API error: {str(e)}")
    
    # Categories method removed - YGG API doesn't provide categories endpoint
    
    def get_torrent_details(self, torrent_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific torrent"""
        try:
            response = self.session.get(f"{self.base_url}/torrent/{torrent_id}", timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"YGG API torrent details error: {e}")
            raise HTTPException(status_code=500, detail=f"YGG API error: {str(e)}")
    
    def get_torrent_download(self, torrent_id: str, download_type: str = "magnet") -> Dict[str, Any]:
        """Get download link or magnet for a torrent"""
        try:
            if not YGG_API_KEY:
                raise HTTPException(status_code=500, detail="YGG_API_KEY environment variable is required for downloads")
            
            params = {
                "passkey": YGG_API_KEY,
                "tracker_domain": "tracker.p2p-world.net"  # Default tracker domain
            }
            response = self.session.get(f"{self.base_url}/torrent/{torrent_id}/download", params=params, timeout=30)
            
            # Log the response status for debugging
            logger.info(f"YGG API download response: {response.status_code}")
            
            if response.status_code == 422:
                logger.error(f"YGG API returned 422 for torrent {torrent_id}: {response.text}")
                raise HTTPException(status_code=422, detail=f"Torrent {torrent_id} not available for download: {response.text}")
            elif response.status_code == 404:
                logger.error(f"YGG API returned 404 for torrent {torrent_id}: {response.text}")
                raise HTTPException(status_code=404, detail=f"Torrent {torrent_id} not found")
            
            response.raise_for_status()
            
            # The API returns the torrent file content directly, not JSON
            # We need to return it in a format that our API can handle
            import base64
            torrent_content = response.content
            torrent_b64 = base64.b64encode(torrent_content).decode('utf-8')
            
            return {
                "success": True,
                "message": "Torrent file retrieved successfully",
                "torrent_content": torrent_b64,
                "download_type": "torrent_file"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"YGG API download error: {e}")
            raise HTTPException(status_code=500, detail=f"YGG API error: {str(e)}")

# Initialize YGG API client
ygg_client = YGGAPIClient(YGG_API_BASE_URL, YGG_API_KEY)

# Routes
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "YGG Gateway API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/search",
            "categories": "/categories",
            "torrent_details": "/torrent/{torrent_id}",
            "download": "/torrent/{torrent_id}/download",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "ygg_api_configured": bool(YGG_API_KEY)
    }

@app.post("/search", response_model=YGGSearchResponse)
async def search_torrents(request: YGGSearchRequest):
    """Search for torrents using YGG API"""
    try:
        logger.info(f"Searching for: '{request.query}' in category: {request.category}")
        
        # Call YGG API
        result = ygg_client.search_torrents(
            query=request.query,
            category=request.category,
            limit=request.limit
        )
        
        # Transform response to our format
        torrents = []
        for item in result.get("torrents", []):
            torrent = YGGTorrent(
                id=item.get("id", 0),
                title=item.get("title", ""),
                category_id=item.get("category_id", 0),
                size=item.get("size", 0),
                seeders=item.get("seeders", 0),
                leechers=item.get("leechers", 0),
                downloads=item.get("downloads"),
                uploaded_at=item.get("uploaded_at", ""),
                link=item.get("link", ""),
                slug=item.get("slug")
            )
            torrents.append(torrent)
        
        return YGGSearchResponse(
            torrents=torrents,
            total=result.get("total", 0),
            page=result.get("page", 1),
            per_page=result.get("per_page", request.limit)
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_model=YGGSearchResponse)
async def search_torrents_get(
    q: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None, description="Category filter"),
    limit: int = Query(50, description="Number of results per page"),
    page: int = Query(1, description="Page number")
):
    """Search for torrents using YGG API (GET endpoint)"""
    request = YGGSearchRequest(query=q, category=category, limit=limit)
    return await search_torrents(request)

# Categories endpoint removed - YGG API doesn't provide categories endpoint
# Categories are handled via RSS feed IDs instead

@app.get("/torrent/{torrent_id}", response_model=YGGTorrent)
async def get_torrent_details(torrent_id: str):
    """Get detailed information about a specific torrent"""
    try:
        logger.info(f"Fetching details for torrent: {torrent_id}")
        
        result = ygg_client.get_torrent_details(torrent_id)
        
        torrent = YGGTorrent(
            id=str(result.get("id", torrent_id)),
            name=result.get("name", ""),
            category=result.get("category", ""),
            category_id=result.get("category_id", 0),
            size=result.get("size", 0),
            seeders=result.get("seeders", 0),
            leechers=result.get("leechers", 0),
            upload_date=result.get("upload_date", ""),
            download_url=result.get("download_url"),
            magnet_url=result.get("magnet_url"),
            description=result.get("description")
        )
        
        return torrent
        
    except Exception as e:
        logger.error(f"Torrent details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/torrent/{torrent_id}/download", response_model=TorrentDownloadResponse)
async def get_torrent_download(torrent_id: str, request: TorrentDownloadRequest):
    """Get download link or magnet for a torrent"""
    try:
        logger.info(f"Getting download for torrent: {torrent_id}, type: {request.download_type}")
        
        result = ygg_client.get_torrent_download(torrent_id, request.download_type)
        
        return TorrentDownloadResponse(
            success=result.get("success", True),
            message=result.get("message", "Download link retrieved successfully"),
            download_url=result.get("download_url"),
            magnet_url=result.get("magnet_url"),
            torrent_content=result.get("torrent_content"),
            download_type=result.get("download_type")
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/torrent/{torrent_id}/download", response_model=TorrentDownloadResponse)
async def get_torrent_download_get(
    torrent_id: str,
    type: str = Query("magnet", description="Download type: magnet or torrent")
):
    """Get download link or magnet for a torrent (GET endpoint)"""
    request = TorrentDownloadRequest(torrent_id=torrent_id, download_type=type)
    return await get_torrent_download(torrent_id, request)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
