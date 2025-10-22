#!/usr/bin/env python3
"""
Compare M4B tags between old and new implementations
"""

import sys
from pathlib import Path
from mutagen.mp4 import MP4, MP4FreeForm
from tabulate import tabulate

def extract_tags(file_path):
    """Extract all tags from an M4B file"""
    try:
        audio = MP4(file_path)
        if not audio.tags:
            return {}
        
        tags = {}
        
        # Basic tags
        basic_tags = {
            'Title': '\xa9nam',
            'Album': '\xa9alb', 
            'Artist': '\xa9ART',
            'Album Artist': 'aART',
            'Composer': '\xa9wrt',
            'Year': '\xa9day',
            'Genre': '\xa9gen',
            'Comment': '\xa9cmt',
            'Copyright': '\xa9cpy'
        }
        
        for tag_name, tag_key in basic_tags.items():
            if tag_key in audio.tags:
                value = audio.tags[tag_key]
                if isinstance(value, list) and len(value) > 0:
                    tags[tag_name] = str(value[0])
                else:
                    tags[tag_name] = str(value)
            else:
                tags[tag_name] = 'N/A'
        
        # Custom tags
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
            'Rating WMP': '----:com.apple.iTunes:RATING WMP',
            'Explicit': '----:com.apple.iTunes:EXPLICIT',
            'Publisher': '----:com.apple.iTunes:PUBLISHER',
            'Description': '----:com.apple.iTunes:DESCRIPTION',
            'Genres': '----:com.apple.iTunes:GENRES',
            'ISBN': '----:com.apple.iTunes:ISBN',
            'WWW Audio File': '----:com.apple.iTunes:WWWAUDIOFILE',
            'iTunes Advisory': '----:com.apple.iTunes:ITUNESADVISORY',
            'Movement': '----:com.apple.iTunes:MOVEMENT',
            'Movement Name': '----:com.apple.iTunes:MOVEMENTNAME',
            'TMP Genre 1': '----:com.apple.iTunes:TMP_GENRE1',
            'TMP Genre 2': '----:com.apple.iTunes:TMP_GENRE2',
            'Composer': '----:com.apple.iTunes:COMPOSER'
        }
        
        for tag_name, tag_key in custom_tags.items():
            if tag_key in audio.tags:
                value = audio.tags[tag_key]
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], MP4FreeForm):
                        tags[tag_name] = value[0].decode('utf-8', errors='replace')
                    else:
                        tags[tag_name] = str(value[0])
                else:
                    tags[tag_name] = str(value)
            else:
                tags[tag_name] = 'N/A'
        
        # Additional tags
        additional_tags = {
            'Album Sort': 'soal',
            'Content Group': '\xa9grp',
            'Publisher Alt': '\xa9pub',
            'Narrator Alt': '\xa9nrt',
            'Series Alt': '\xa9mvn',
            'Description Alt': 'desc',
            'Description Alt2': '\xa9des',
            'ASIN Alt': 'asin',
            'CDEK ASIN': 'CDEK',
            'Show Movement': 'shwm',
            'Stick': 'stik',
            'Gapless': 'pgap'
        }
        
        for tag_name, tag_key in additional_tags.items():
            if tag_key in audio.tags:
                value = audio.tags[tag_key]
                if isinstance(value, list) and len(value) > 0:
                    # Handle boolean values properly
                    if isinstance(value[0], bool):
                        tags[tag_name] = str(value[0])
                    else:
                        tags[tag_name] = str(value[0])
                else:
                    # Handle boolean values properly
                    if isinstance(value, bool):
                        tags[tag_name] = str(value)
                    else:
                        tags[tag_name] = str(value)
            else:
                tags[tag_name] = 'N/A'
        
        return tags
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {}

def compare_files(new_file, old_file):
    """Compare tags between new and old implementations"""
    
    print(f"🔍 Comparing tags between:")
    print(f"   NEW: {new_file}")
    print(f"   OLD: {old_file}")
    print("=" * 80)
    
    # Extract tags from both files
    new_tags = extract_tags(new_file)
    old_tags = extract_tags(old_file)
    
    if not new_tags and not old_tags:
        print("❌ Could not read tags from either file")
        return
    
    # Get all unique tag names
    all_tags = set(new_tags.keys()) | set(old_tags.keys())
    all_tags = sorted(all_tags)
    
    # Create comparison table
    table_data = []
    for tag_name in all_tags:
        new_value = new_tags.get(tag_name, 'N/A')
        old_value = old_tags.get(tag_name, 'N/A')
        
        # Convert all values to strings and handle special cases
        new_str = str(new_value) if new_value != 'N/A' else 'N/A'
        old_str = str(old_value) if old_value != 'N/A' else 'N/A'
        
        # Truncate long values for display
        if len(new_str) > 50:
            new_str = new_str[:47] + "..."
        if len(old_str) > 50:
            old_str = old_str[:47] + "..."
        
        # Mark differences
        if new_str != old_str:
            status = "🔄 DIFF"
        elif new_str == 'N/A' and old_str == 'N/A':
            status = "⚪ BOTH N/A"
        else:
            status = "✅ SAME"
        
        table_data.append([tag_name, new_str, old_str, status])
    
    # Print markdown table
    print("\n| Tag Name | NEW Implementation | OLD Implementation | Status |")
    print("|----------|-------------------|-------------------|--------|")
    for row in table_data:
        print(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")
    
    # Summary
    diff_count = sum(1 for row in table_data if "DIFF" in row[3])
    same_count = sum(1 for row in table_data if "SAME" in row[3])
    na_count = sum(1 for row in table_data if "BOTH N/A" in row[3])
    
    print(f"\n📊 SUMMARY:")
    print(f"   🔄 Different: {diff_count}")
    print(f"   ✅ Same: {same_count}")
    print(f"   ⚪ Both N/A: {na_count}")
    print(f"   📝 Total tags: {len(table_data)}")

def main():
    """Main function to find and compare files"""
    
    # Find files with _old suffix and their counterparts
    library_path = Path("data/library")
    
    old_files = list(library_path.rglob("*_old.m4b"))
    
    if not old_files:
        print("❌ No files with '_old' suffix found in library")
        return
    
    for old_file in old_files:
        # Find corresponding new file
        new_file_name = old_file.name.replace("_old.m4b", ".m4b")
        new_file = old_file.parent / new_file_name
        
        if new_file.exists():
            print(f"\n{'='*80}")
            compare_files(str(new_file), str(old_file))
        else:
            print(f"❌ Could not find corresponding new file for: {old_file}")

if __name__ == "__main__":
    main()
