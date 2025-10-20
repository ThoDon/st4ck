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

# Create simplified pipeline directories
echo "   Creating pipeline directories..."
mkdir -p "$DATA_DIR/toMerge"
mkdir -p "$DATA_DIR/converted"
mkdir -p "$DATA_DIR/conversion-backups"

echo "✅ All required directories created successfully!"
echo ""
echo "📋 Directory structure:"
echo "   $DATA_DIR/"
echo "   ├── db/"
echo "   ├── downloads/"
echo "   ├── covers/"
echo "   ├── toTag/"
echo "   ├── toMerge/"
echo "   ├── converted/"
echo "   ├── conversion-backups/"
echo "   ├── drop-torrents/"
echo ""
if [ "$DATA_DIR" != "$LIBRARY_DIR" ]; then
    echo "   $LIBRARY_DIR/"
    echo "   └── (library files)"
    echo ""
fi
echo "🚀 Directory initialization complete! Other services can now start."
