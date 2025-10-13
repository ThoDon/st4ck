#!/bin/sh

# Install curl if not present
if ! command -v curl >/dev/null 2>&1; then
    apk add --no-cache curl
fi

echo '📦 Mover service started. Scanning every 60s...'

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

# Function to move directories from downloads
move_download_directories() {
    find /downloads -mindepth 1 -maxdepth 1 ! -name 'incomplete' -type d | while read -r dir; do
        if [ -n "$dir" ]; then
            echo "➡️ Moving folder: $dir"
            if mv "$dir" /toMerge/ 2>/dev/null; then
                echo "✅ Successfully moved folder: $dir"
                log_to_api "INFO" "Moved folder: $dir to /toMerge"
            else
                echo "❌ Failed to move folder: $dir"
                log_to_api "ERROR" "Failed to move folder: $dir"
            fi
        fi
    done
}

# Function to move completed m4b files from untagged to toTag
move_untagged_m4b() {
    find /untagged -mindepth 1 -maxdepth 1 -type d | while read -r dir; do
        if [ -n "$dir" ]; then
            # Skip folders containing "-tmpfiles" in their name
            if echo "$dir" | grep -q -- "-tmpfiles"; then
                echo "⏭️ Skipping tmpfiles folder: $dir"
                continue
            fi
            
            # Check if directory contains any .m4b files
            m4b_files=$(find "$dir" -name "*.m4b" -type f)
            if [ -z "$m4b_files" ]; then
                echo "⏳ Skipping folder (no .m4b files yet): $dir"
                continue
            fi
            
            # Check if there are any files still converting or with -finished suffix
            converting_files=$(find "$dir" -name "*-converting.m4b" -type f)
            finished_files=$(find "$dir" -name "*-finished.m4b" -type f)
            
            if [ -n "$converting_files" ]; then
                echo "⏳ Skipping folder (still converting): $dir"
                echo "   Converting files: $(echo "$converting_files" | wc -l)"
                continue
            fi
            
            if [ -n "$finished_files" ]; then
                echo "⏳ Skipping folder (has -finished files, conversion not complete): $dir"
                echo "   Finished files: $(echo "$finished_files" | wc -l)"
                continue
            fi
            
            # Check if all .m4b files are properly named (no suffixes)
            all_m4b_files=$(find "$dir" -name "*.m4b" -type f)
            proper_m4b_files=$(find "$dir" -name "*.m4b" -type f ! -name "*-converting.m4b" ! -name "*-finished.m4b")
            
            if [ "$all_m4b_files" != "$proper_m4b_files" ]; then
                echo "⏳ Skipping folder (has files with conversion suffixes): $dir"
                echo "   All files: $(echo "$all_m4b_files" | wc -l), Proper files: $(echo "$proper_m4b_files" | wc -l)"
                continue
            fi
            
            # All checks passed - move the folder
            echo "➡️ Moving completed m4b folder: $dir"
            if mv "$dir" /toTag/ 2>/dev/null; then
                echo "✅ Successfully moved m4b folder: $dir"
                log_to_api "INFO" "Moved completed m4b folder: $dir to /toTag"
            else
                echo "❌ Failed to move m4b folder: $dir"
                log_to_api "ERROR" "Failed to move m4b folder: $dir"
            fi
        fi
    done
}

# Main loop
while true; do
    move_download_directories
    move_untagged_m4b
    sleep 60
done
