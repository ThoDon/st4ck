#!/bin/bash
# Simple wrapper script for library processing

# Default values
ACTION="clean-and-tag"
LOCALE="fr"
LIBRARY_PATH="data/library"
REMOVE_ASIN=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            ACTION="clean"
            shift
            ;;
        --tag)
            ACTION="tag"
            shift
            ;;
        --clean-and-tag)
            ACTION="clean-and-tag"
            shift
            ;;
        --locale)
            LOCALE="$2"
            shift 2
            ;;
        --library-path)
            LIBRARY_PATH="$2"
            shift 2
            ;;
        --remove-asin)
            REMOVE_ASIN="--remove-asin"
            shift
            ;;
        --help|-h)
            echo "Library Processor Wrapper"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --clean              Only clean files (preserve ASIN)"
            echo "  --tag                Only tag files (requires existing ASIN)"
            echo "  --clean-and-tag      Clean and re-tag files (default)"
            echo "  --locale LOCALE      Audible locale (default: fr)"
            echo "  --library-path PATH  Library directory (default: data/library)"
            echo "  --remove-asin        Remove ASIN tags when cleaning"
            echo "  --help, -h           Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Clean and re-tag all files"
            echo "  $0 --clean                           # Only clean files"
            echo "  $0 --tag --locale com                # Tag with US locale"
            echo "  $0 --clean --remove-asin             # Clean completely"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run the library processor
echo "🚀 Starting library processing..."
python3 library_processor.py \
    --action "$ACTION" \
    --locale "$LOCALE" \
    --library-path "$LIBRARY_PATH" \
    $REMOVE_ASIN

echo "✅ Library processing completed!"
