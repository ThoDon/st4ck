# 📦 Audiobook Pipeline

A complete Docker Compose stack for automating RSS feed → Torrent download → Audio conversion → Tagging → Central API → UI pipeline.

## 🚀 Quick Start

1. **Set environment variables:**

   ```bash
   export RSS_FEED_URL="https://example.com/feed.xml"
   ```

   **Note**: The system is optimized for YggTorrent RSS feeds and will automatically parse:

   - Author names from titles
   - Publication years
   - Audio formats (MP3 quality)
   - File sizes
   - Seeder/leecher counts

2. **Start the stack:**

   ```bash
   docker-compose up -d
   ```

3. **Access the UI:**
   - Open http://localhost:8080

## 📁 Directory Structure

```
project-root/
├── data/
│   ├── torrents/        # .torrent files
│   ├── downloads/     # active downloads
│   ├── toMerge/         # mp3 folders waiting for conversion
│   ├── toTag/           # m4b files waiting for tagging
│   ├── library/         # final tagged m4b files
│   └── db/              # sqlite database
├── rss-worker/          # Python RSS parser
├── api/                 # FastAPI service
├── ui/                  # React TypeScript UI
└── docker-compose.yml
```

## 🔧 Services

- **rss-worker**: Parses RSS feed every hour, downloads torrents
- **transmission**: Torrent client (headless)
- **api**: FastAPI central gateway
- **auto-m4b**: Converts MP3 folders to M4B files
- **auto-m4b-tagger**: Tags M4B files with metadata
- **ui**: React TypeScript dashboard

## 🌐 Ports

- **UI**: http://localhost:8080
- **API**: http://localhost:8081 (docs at /docs)
- **Transmission**: http://localhost:9091 (admin/admin)

## 📊 API Endpoints

- `GET /rss-items` - List RSS items
- `GET /torrents` - Active torrents
- `GET /tagging` - Items in tagging queue
- `GET /logs` - System logs

## 🐛 Troubleshooting

1. **Check logs:**

   ```bash
   docker-compose logs -f [service-name]
   ```

2. **Reset database:**

   ```bash
   rm -rf data/db/*
   docker-compose up db-init
   ```

3. **View Transmission Web UI:**
   - Go to http://localhost:9091
   - Username: admin, Password: admin

## ⚙️ Configuration

Edit `docker-compose.yml` to customize:

- RSS feed URL
- Volume paths
- Service configurations

## 🔄 Pipeline Flow

1. RSS worker fetches feed → downloads torrents
2. Transmission downloads torrents → moves to toMerge/toTag
3. auto-m4b converts MP3 folders → outputs M4B files
4. auto-m4b-tagger processes M4B files → moves to library
5. UI displays all pipeline states via API
