#!/bin/sh

# Install curl and redis-cli if not present
if ! command -v curl >/dev/null 2>&1; then
    apk add --no-cache curl
fi

if ! command -v redis-cli >/dev/null 2>&1; then
    apk add --no-cache redis
fi

echo '📦 Mover service started. Checking for completed downloads...'

# Function to log to API
log_to_api() {
    local level="$1"
    local message="$2"
    local service="${3:-mover}"
    
    curl -s -X POST http://api:8000/logs/external \
        -H "Content-Type: application/json" \
        -d "{\"level\": \"$level\", \"message\": \"$message\", \"service\": \"$service\"}" \
        2>/dev/null || echo "⚠️ Failed to log to API: $message"
}

# Function to publish Redis event
publish_redis_event() {
    local channel="$1"
    local message="$2"
    
    redis-cli -h redis -p 6379 publish "$channel" "$message" 2>/dev/null || {
        echo "⚠️ Failed to publish Redis event: $channel"
        log_to_api "ERROR" "Failed to publish Redis event: $channel"
    }
}

# Function to move directories from downloads and trigger conversion
move_download_directories() {
    find /downloads -mindepth 1 -maxdepth 1 ! -name 'incomplete' -type d | while read -r dir; do
        if [ -n "$dir" ]; then
            echo "➡️ Moving folder: $dir"
            if mv "$dir" /toMerge/ 2>/dev/null; then
                echo "✅ Successfully moved folder: $dir"
                log_to_api "INFO" "Moved folder: $dir to /toMerge"
                
                # Extract book name from directory
                book_name=$(basename "$dir")
                
                # Publish Redis event to trigger conversion
                message="{\"book_name\":\"$book_name\",\"path\":\"/toMerge/$book_name\",\"rss_item_id\":null}"
                publish_redis_event "audiobook:download_complete" "$message"
                echo "📡 Published conversion trigger for: $book_name"
            else
                echo "❌ Failed to move folder: $dir"
                log_to_api "ERROR" "Failed to move folder: $dir"
            fi
        fi
    done
}

# Function to move completed m4b files from converted to toTag
move_converted_m4b() {
    find /converted -mindepth 1 -maxdepth 1 -name "*.m4b" -type f | while read -r file; do
        if [ -n "$file" ]; then
            echo "➡️ Moving completed m4b file: $file"
            if mv "$file" /toTag/ 2>/dev/null; then
                echo "✅ Successfully moved m4b file: $file"
                log_to_api "INFO" "Moved completed m4b file: $file to /toTag"
                
                # Extract book name from filename
                book_name=$(basename "$file" .m4b)
                
                # Publish Redis event to trigger tagging
                message="{\"book_name\":\"$book_name\",\"file_path\":\"/toTag/$(basename "$file")\",\"rss_item_id\":null}"
                publish_redis_event "audiobook:conversion_complete" "$message"
                echo "📡 Published tagging trigger for: $book_name"
            else
                echo "❌ Failed to move m4b file: $file"
                log_to_api "ERROR" "Failed to move m4b file: $file"
            fi
        fi
    done
}

# One-time scan for orphaned files on startup
echo "🔍 Scanning for orphaned files..."
move_download_directories
move_converted_m4b

echo "✅ Initial scan complete. Mover service will now respond to Redis events."
log_to_api "INFO" "Mover service started and completed initial scan"

# Keep service running but don't poll continuously
# The service will be triggered by external events (Transmission completion detection)
while true; do
    # Light monitoring - check every 30 seconds for any missed files
    sleep 30
    echo "🔍 Periodic check for missed files..."
    move_download_directories
    move_converted_m4b
done
