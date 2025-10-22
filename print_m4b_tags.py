#!/usr/bin/env python3
"""
Simple script to print M4B file tags without cover art
Reads all .m4b files in the library directory and displays their metadata
"""

import os
import sys
from pathlib import Path
from mutagen.mp4 import MP4
from mutagen.mp4 import MP4Cover

def print_m4b_tags(file_path):
    """Print tags for a single M4B file"""
    try:
        print(f"\n{'='*80}")
        print(f"File: {file_path}")
        print(f"{'='*80}")
        
        # Load the M4B file
        audio = MP4(file_path)
        
        if not audio:
            print("❌ Could not load file or file has no tags")
            return
        
        def format_value(value):
            """Format tag values, handling bytes and long strings"""
            if value is None:
                return "N/A"
            if isinstance(value, bytes):
                try:
                    return value.decode('utf-8')
                except UnicodeDecodeError:
                    return str(value)
            if isinstance(value, str) and len(value) > 100:
                return value[:100] + "..."
            return str(value)
        
        # Basic tags - read from individual fields
        basic_tags = {
            'Title': '©nam',
            'Album': '©alb', 
            'Artist': '©ART',
            'Album Artist': 'aART',
            'Composer': '©wrt',
            'Year': '©day',
            'Genre': '©gen',
            'Comment': '©cmt',
            'Copyright': '©cpy'
        }
        
        print("\n📖 BASIC TAGS:")
        print("-" * 40)
        for tag_name, tag_key in basic_tags.items():
            if tag_key in audio:
                value = audio[tag_key][0] if audio[tag_key] else "N/A"
                print(f"{tag_name:15}: {format_value(value)}")
            else:
                print(f"{tag_name:15}: N/A")
        
        # iTunes custom tags
        custom_tags = {
            'ASIN': '----:com.apple.iTunes:ASIN',
            'Language': '----:com.apple.iTunes:LANGUAGE',
            'Format': '----:com.apple.iTunes:FORMAT',
            'Subtitle': '----:com.apple.iTunes:SUBTITLE',
            'Release Time': '----:com.apple.iTunes:RELEASETIME',
            'Album Artists': '----:com.apple.iTunes:ALBUMARTISTS',
            'Series': '----:com.apple.iTunes:SERIES',
            'Series Part': '----:com.apple.iTunes:SERIES-PART',
            'Rating': '----:com.apple.iTunes:RATING',
            'Explicit': '----:com.apple.iTunes:EXPLICIT',
            'Publisher': '----:com.apple.iTunes:PUBLISHER',
            'Description': '----:com.apple.iTunes:DESCRIPTION',
            'Genres': '----:com.apple.iTunes:GENRES',
            'ISBN': '----:com.apple.iTunes:ISBN'
        }
        
        print("\n🏷️  CUSTOM TAGS:")
        print("-" * 40)
        for tag_name, tag_key in custom_tags.items():
            if tag_key in audio:
                value = audio[tag_key][0] if audio[tag_key] else "N/A"
                print(f"{tag_name:15}: {format_value(value)}")
            else:
                print(f"{tag_name:15}: N/A")
        
        # Audio properties
        print("\n🎵 AUDIO PROPERTIES:")
        print("-" * 40)
        if hasattr(audio, 'info'):
            info = audio.info
            print(f"{'Length':15}: {info.length:.2f} seconds ({info.length/60:.2f} minutes)")
            print(f"{'Bitrate':15}: {info.bitrate} bps")
            print(f"{'Sample Rate':15}: {info.sample_rate} Hz")
            print(f"{'Channels':15}: {info.channels}")
        
        # Check for cover art (but don't display it)
        has_cover = False
        if 'covr' in audio:
            has_cover = True
            cover_count = len(audio['covr'])
            print(f"\n🖼️  COVER ART: {cover_count} image(s) present (not displayed)")
        else:
            print(f"\n🖼️  COVER ART: None")
            
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")

def find_m4b_files(library_path):
    """Find all .m4b files in the library directory"""
    m4b_files = []
    library_dir = Path(library_path)
    
    if not library_dir.exists():
        print(f"❌ Library directory not found: {library_path}")
        return m4b_files
    
    # Recursively find all .m4b files
    for m4b_file in library_dir.rglob("*.m4b"):
        m4b_files.append(m4b_file)
    
    return sorted(m4b_files)

def main():
    """Main function"""
    # Default library path
    library_path = "/Users/donet/Downloads/st4ck/data/library"
    
    # Allow custom library path as command line argument
    if len(sys.argv) > 1:
        library_path = sys.argv[1]
    
    print(f"🔍 Searching for M4B files in: {library_path}")
    
    # Find all M4B files
    m4b_files = find_m4b_files(library_path)
    
    if not m4b_files:
        print("❌ No M4B files found in the library directory")
        return
    
    print(f"📚 Found {len(m4b_files)} M4B file(s)")
    
    # Print tags for each file
    for m4b_file in m4b_files:
        print_m4b_tags(m4b_file)
    
    print(f"\n{'='*80}")
    print(f"✅ Finished processing {len(m4b_files)} file(s)")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
