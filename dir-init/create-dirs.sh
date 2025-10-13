#!/bin/bash

# Script to create required directories for the audiobook pipeline
# This runs as an init container to ensure directories exist before other services start

echo "📁 Initializing directories for audiobook pipeline..."

# Get data directory from environment or use default
DATA_DIR=${DATA_DIR:-./data}
LIBRARY_DIR=${LIBRARY_DIR:-./data}

echo "   Using DATA_DIR: $DATA_DIR"
echo "   Using LIBRARY_DIR: $LIBRARY_DIR"

# Create main data directories
echo "   Creating main data directories..."
mkdir -p "$DATA_DIR/db"
mkdir -p "$DATA_DIR/downloads"
# Create library directory (can be separate from data)
if [ "$DATA_DIR" = "$LIBRARY_DIR" ]; then
    # If same as data dir, add /library suffix
    mkdir -p "$LIBRARY_DIR/library"
else
    # If different from data dir, use as-is (user specified exact path)
    mkdir -p "$LIBRARY_DIR"
fi
mkdir -p "$DATA_DIR/covers"
mkdir -p "$DATA_DIR/toTag"
mkdir -p "$DATA_DIR/drop-torrents"
mkdir -p "$DATA_DIR/saved-torrents-files"

# Create auto-m4b directories
echo "   Creating auto-m4b directories..."
mkdir -p "$DATA_DIR/auto-m4b/config"
mkdir -p "$DATA_DIR/auto-m4b/temp/recentlyadded"
mkdir -p "$DATA_DIR/auto-m4b/temp/untagged"
mkdir -p "$DATA_DIR/auto-m4b/temp/merge"
mkdir -p "$DATA_DIR/auto-m4b/temp/backup"
mkdir -p "$DATA_DIR/auto-m4b/temp/delete"
mkdir -p "$DATA_DIR/auto-m4b/temp/fix"

echo "✅ All required directories created successfully!"
echo ""
echo "📋 Directory structure:"
echo "   $DATA_DIR/"
echo "   ├── db/"
echo "   ├── downloads/"
echo "   ├── covers/"
echo "   ├── toTag/"
echo "   ├── drop-torrents/"
echo "   ├── saved-torrents-files/"
echo "   └── auto-m4b/"
echo "       ├── config/"
echo "       └── temp/"
echo "           ├── recentlyadded/"
echo "           ├── untagged/"
echo "           ├── merge/"
echo "           ├── backup/"
echo "           ├── delete/"
echo "           └── fix/"
echo ""
if [ "$DATA_DIR" != "$LIBRARY_DIR" ]; then
    echo "   $LIBRARY_DIR/"
    echo "   └── (library files)"
    echo ""
fi
echo "🚀 Directory initialization complete! Other services can now start."
