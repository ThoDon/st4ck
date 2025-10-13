#!/bin/bash

# Audiobook Pipeline Startup Script

# Function to create .env file if it doesn't exist
create_env_file() {
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            echo "⚠️  No .env file found. Creating from .env.example..."
            cp .env.example .env
            echo "✅ Created .env file from template."
            echo "📝 Please edit .env with your configuration:"
            echo "   - RSS_FEED_URL: Set to your actual RSS feed"
            echo "   - TRANSMISSION_USER/PASS: Change from default admin/admin"
            echo "   - VITE_API_URL: Update for production if needed"
        else
            echo "⚠️  No .env file found. Creating basic configuration..."
            cat > .env << EOF
# RSS Feed Configuration
RSS_FEED_URL=https://example.com/feed.xml

# Transmission Configuration
TRANSMISSION_USER=admin
TRANSMISSION_PASS=admin

# API Configuration
VITE_API_URL=http://localhost:8081

# System Configuration
PUID=1000
PGID=1000
TZ=UTC

# Auto-m4b Configuration
CPU_CORES=2
SLEEPTIME=1m
MAKE_BACKUP=N
EOF
            echo "✅ Created basic .env file. Please edit it with your configuration."
        fi
    fi
}

# Initialize flags
CLEAN_MODE=false
DEV_FRONTEND_MODE=false

# Check for parameters
for arg in "$@"; do
    case $arg in
        --clean)
            CLEAN_MODE=true
            ;;
        --dev-frontend)
            DEV_FRONTEND_MODE=true
            ;;
        *)
            echo "❌ Unknown parameter: $arg"
            echo "Usage: $0 [--clean] [--dev-frontend]"
            exit 1
            ;;
    esac
done

# Handle clean mode
if [ "$CLEAN_MODE" = true ]; then
    echo "🧹 Cleaning all local data files..."
    
    # Stop all containers
    echo "🛑 Stopping all containers..."
    docker-compose down
    
    # Get data directory from environment or use default
    DATA_DIR=${DATA_DIR:-./data}
    LIBRARY_DIR=${LIBRARY_DIR:-./data}
    
    # Remove all data directories and files
    echo "🗑️  Removing data directories..."
    echo "   Removing: $DATA_DIR"
    echo "   Removing: $LIBRARY_DIR"
    rm -rf "$DATA_DIR/"
    rm -rf "$LIBRARY_DIR/"
    
    # Remove any Docker volumes (optional, more thorough cleanup)
    echo "🗑️  Removing Docker volumes..."
    docker-compose down -v 2>/dev/null || true
    
    echo "✅ Cleanup complete!"
    echo ""
    echo "🚀 Starting fresh pipeline..."
fi

# Handle dev-frontend mode
if [ "$DEV_FRONTEND_MODE" = true ]; then
    echo "🚀 Starting Audiobook Pipeline in Development Mode..."
    echo "   Backend services will run in Docker"
    echo "   Frontend will run in development mode with live reload"
    echo ""
    
    # Create .env file
    create_env_file

    # Start backend services only (exclude UI)
    echo "🐳 Starting backend services..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

    echo "✅ Backend services started!"
    echo ""
    echo "🌐 Backend access points:"
    echo "   API: http://localhost:8081"
    echo "   API Docs: http://localhost:8081/docs"
    echo "   Transmission: http://localhost:9091 (admin/admin)"
    echo ""
    echo "🎨 Starting frontend in development mode..."
    
    # Get the absolute path to the project directory
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Open new terminal and start frontend development server
    osascript -e "tell application \"Terminal\" to do script \"cd '$PROJECT_DIR/ui' && npm run dev\""
    
    echo "✅ Frontend development server starting in new terminal!"
    echo "   Frontend will be available at: http://localhost:8080"
    echo ""
    echo "📊 Check backend status: docker-compose ps"
    echo "📝 View backend logs: docker-compose logs -f [service-name]"
    echo ""
    echo "🛑 To stop backend services: docker-compose down"
    exit 0
fi

echo "🚀 Starting Audiobook Pipeline..."

# Create .env file
create_env_file

# Start services
echo "🐳 Starting Docker Compose services..."
docker-compose up -d

echo "✅ Pipeline started!"
echo ""
echo "🌐 Access points:"
echo "   UI: http://localhost:8080"
echo "   API: http://localhost:8081"
echo "   API Docs: http://localhost:8081/docs"
echo "   Transmission: http://localhost:9091 (admin/admin)"
echo ""
echo "📊 Check status: docker-compose ps"
echo "📝 View logs: docker-compose logs -f [service-name]"
echo ""
echo "🧹 To clean all data and start fresh: ./start.sh --clean"
echo "🔧 For frontend development mode (backend only in docker): ./start.sh --dev-frontend"
echo "🧹🔧 To clean and start in dev mode: ./start.sh --clean --dev-frontend"
