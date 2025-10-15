#!/bin/bash
set -e

echo "🚀 Starting Folder M4B builder for converter service"

# Input and output paths
INPUT_DIR="$1"
OUTPUT_DIR="$2"
BOOK_NAME="$3"

if [[ -z "$INPUT_DIR" || -z "$OUTPUT_DIR" || -z "$BOOK_NAME" ]]; then
    echo "❌ Usage: $0 <input_dir> <output_dir> <book_name>"
    exit 1
fi

echo "📁 Processing: $BOOK_NAME"
echo "   Input: $INPUT_DIR"
echo "   Output: $OUTPUT_DIR"

# Check if input directory exists
if [[ ! -d "$INPUT_DIR" ]]; then
    echo "❌ Input directory does not exist: $INPUT_DIR"
    exit 1
fi

# Get list of MP3 files
FILES=()
while IFS= read -r -d $'\0' f; do FILES+=("$f"); done < <(find "$INPUT_DIR" -maxdepth 1 -iname "*.mp3" -print0 | sort -z)

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "⚠️  No MP3 files found — skipping."
    exit 1
fi

echo "🎵 Found ${#FILES[@]} MP3 files"

# Read tags from first file
META="${FILES[0]}"
AUTHOR=$(ffprobe -v error -show_entries format_tags=artist -of default=nw=1:nk=1 "$META" 2>/dev/null || echo "Unknown Author")
ALBUM=$(ffprobe -v error -show_entries format_tags=album -of default=nw=1:nk=1 "$META" 2>/dev/null || echo "$BOOK_NAME")
YEAR=$(ffprobe -v error -show_entries format_tags=date -of default=nw=1:nk=1 "$META" 2>/dev/null || echo "2023")
COMMENT=$(ffprobe -v error -show_entries format_tags=comment -of default=nw=1:nk=1 "$META" 2>/dev/null || echo "")

echo "🎯 Metadata:"
echo "   Album : ${ALBUM}"
echo "   Author: ${AUTHOR}"
echo "   Year  : ${YEAR}"
echo "   Comment: ${COMMENT}"

# Cover image
COVER_IMAGE="$INPUT_DIR/cover.jpg"
COVER_ARG=()
if [[ -f "$COVER_IMAGE" ]]; then
    COVER_ARG=(--cover "$COVER_IMAGE")
    echo "🖼️  Cover image found."
else
    echo "⚠️  No cover image found."
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Output file path
OUTPUT_FILE="$OUTPUT_DIR/${BOOK_NAME}.m4b"

# Run m4b-tool
echo "🎧 Creating: $OUTPUT_FILE"
m4b-tool merge "$INPUT_DIR" \
    --output-file="$OUTPUT_FILE" \
    --name="$ALBUM" \
    --album="$ALBUM" \
    --artist="$AUTHOR" \
    --year="${YEAR}" \
    --genre="Audiobook" \
    --comment="$COMMENT" \
    --use-filenames-as-chapters \
    --no-chapter-reindexing \
    --audio-bitrate=128k \
    --audio-codec=aac \
    --jobs=1 \
    "${COVER_ARG[@]}"

if [[ $? -eq 0 && -f "$OUTPUT_FILE" ]]; then
    echo "✅ Successfully created: $OUTPUT_FILE"
    exit 0
else
    echo "❌ Failed to create: $OUTPUT_FILE"
    exit 1
fi
