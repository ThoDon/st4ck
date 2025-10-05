#!/bin/bash

# Audiobook Pipeline Startup Script

# Check for clean parameter
if [ "$1" = "clean" ]; then
    echo "🧹 Cleaning all local data files..."
    
    # Stop all containers
    echo "🛑 Stopping all containers..."
    docker-compose down
    
    # Remove all data directories and files
    echo "🗑️  Removing data directories..."
    rm -rf data/
    
    # Remove any Docker volumes (optional, more thorough cleanup)
    echo "🗑️  Removing Docker volumes..."
    docker-compose down -v 2>/dev/null || true
    
    echo "✅ Cleanup complete!"
    echo ""
    echo "🚀 Starting fresh pipeline..."
fi

echo "🚀 Starting Audiobook Pipeline..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from example..."
    cat > .env << EOF
# RSS Feed Configuration (YggTorrent example)
RSS_FEED_URL=https://example.com/feed.xml

# JWT Secret Key (change this in production!)
JWT_SECRET_KEY=your-secure-secret-key-change-this

# Transmission Configuration
TRANSMISSION_USER=admin
TRANSMISSION_PASS=admin

# API Configuration
VITE_API_URL=http://localhost:8000
EOF
    echo "✅ Created .env file. Please edit it with your RSS feed URL and secure JWT secret."
fi

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/{torrents,downloading,toMerge,toTag,library,db,torrents-storage}

# Start services
echo "🐳 Starting Docker Compose services..."
docker-compose up -d

echo "✅ Pipeline started!"
echo ""
echo "🌐 Access points:"
echo "   UI: http://localhost:3000"
echo "   API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   Transmission: http://localhost:9091 (admin/admin)"
echo ""
echo "📊 Check status: docker-compose ps"
echo "📝 View logs: docker-compose logs -f [service-name]"
echo ""
echo "🧹 To clean all data and start fresh: ./start.sh clean"
