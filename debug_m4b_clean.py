#!/usr/bin/env python3
"""
Debug script to clean M4B files by removing all tags except ASIN
This helps debug tagging issues by starting with a clean file
"""

import sys
import os
from pathlib import Path
from mutagen.mp4 import MP4

def clean_m4b_tags(file_path, preserve_asin=True):
    """
    Remove all tags from M4B file except ASIN (if preserve_asin=True)
    
    Args:
        file_path (str): Path to the M4B file
        preserve_asin (bool): Whether to preserve ASIN tags
    """
    try:
        print(f"🧹 Cleaning tags from: {file_path}")
        
        # Load the M4B file
        audio = MP4(file_path)
        
        if not audio:
            print("❌ Could not load file or file has no tags")
            return False
        
        # Store ASIN if we need to preserve it
        preserved_asin = None
        if preserve_asin:
            asin_tags = [
                "----:com.apple.iTunes:ASIN",
                "----:com.apple.iTunes:AUDIBLE_ASIN", 
                "asin",
                "CDEK"
            ]
            
            for tag in asin_tags:
                if tag in audio:
                    if tag.startswith("----:"):
                        # FreeForm tag
                        asin_value = audio[tag][0]
                        if hasattr(asin_value, 'decode'):
                            preserved_asin = asin_value.decode('utf-8')
                        else:
                            preserved_asin = str(asin_value)
                    else:
                        # Regular tag
                        preserved_asin = audio[tag][0]
                    break
        
        # Clear all tags
        audio.clear()
        
        # Restore ASIN if we preserved it
        if preserve_asin and preserved_asin:
            print(f"✅ Preserved ASIN: {preserved_asin}")
            audio["asin"] = [preserved_asin]
            audio["CDEK"] = [preserved_asin]
        
        # Save the cleaned file
        audio.save()
        print("✅ Successfully cleaned all tags from file")
        
        # Verify the cleaning
        audio_verify = MP4(file_path)
        remaining_tags = list(audio_verify.keys())
        
        if preserve_asin and preserved_asin:
            expected_tags = ['asin', 'CDEK']
            remaining_tags = [tag for tag in remaining_tags if tag not in expected_tags]
        
        if remaining_tags:
            print(f"⚠️  Warning: {len(remaining_tags)} tags still remain: {remaining_tags}")
        else:
            print("✅ File is completely clean (except ASIN if preserved)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning file: {e}")
        return False

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("Usage: python3 debug_m4b_clean.py <m4b_file_path> [--remove-asin]")
        print("  --remove-asin: Also remove ASIN tags (default: preserve ASIN)")
        sys.exit(1)
    
    file_path = sys.argv[1]
    preserve_asin = "--remove-asin" not in sys.argv
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    if not file_path.lower().endswith('.m4b'):
        print("❌ File must be an M4B file")
        sys.exit(1)
    
    print(f"🔍 Debug M4B Cleaner")
    print(f"File: {file_path}")
    print(f"Preserve ASIN: {preserve_asin}")
    print("-" * 50)
    
    # Show current tags before cleaning
    try:
        audio = MP4(file_path)
        if audio:
            print(f"📋 Current tags ({len(audio.keys())}):")
            for key in sorted(audio.keys()):
                if key not in ['covr', 'APIC:']:  # Skip cover art
                    print(f"  {key}")
        print()
    except Exception as e:
        print(f"⚠️  Could not read current tags: {e}")
        print()
    
    # Clean the file
    success = clean_m4b_tags(file_path, preserve_asin)
    
    if success:
        print("\n🎉 File cleaning completed successfully!")
    else:
        print("\n❌ File cleaning failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
