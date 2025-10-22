#!/usr/bin/env python3
"""
Unified library processor for M4B files
Can clean and re-tag all files in the library directory
"""

import sys
import os
import json
import requests
import re
from pathlib import Path
from mutagen.mp4 import MP4, MP4FreeForm

def clean_html(text: str) -> str:
    """Remove HTML tags from text content"""
    if not text:
        return ""
    
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    clean_text = clean_text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    clean_text = clean_text.replace('&quot;', '"').replace('&#39;', "'")
    # Clean up extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text
import argparse

class LibraryProcessor:
    def __init__(self, library_path="data/library"):
        self.library_path = Path(library_path)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    def find_m4b_files(self):
        """Find all M4B files in the library directory"""
        m4b_files = list(self.library_path.rglob("*.m4b"))
        print(f"🔍 Found {len(m4b_files)} M4B files in library")
        return m4b_files
    
    def extract_asin_from_file(self, file_path):
        """Extract ASIN from existing tags in an M4B file"""
        try:
            audio = MP4(file_path)
            if not audio:
                return None
            
            # Check for ASIN in various possible tag locations
            asin_candidates = [
                "----:com.apple.iTunes:ASIN",
                "----:com.apple.iTunes:AUDIBLE_ASIN", 
                "asin",
                "CDEK"
            ]
            
            for tag_name in asin_candidates:
                if tag_name in audio:
                    asin_value = audio[tag_name]
                    if isinstance(asin_value, list) and len(asin_value) > 0:
                        # Handle MP4FreeForm objects
                        if hasattr(asin_value[0], 'decode'):
                            asin = asin_value[0].decode('utf-8')
                        else:
                            asin = str(asin_value[0])
                        
                        # Clean up the ASIN value
                        asin = asin.strip()
                        if asin and len(asin) >= 10:  # ASINs are typically 10 characters
                            return asin
            
            return None
            
        except Exception as e:
            print(f"❌ Error extracting ASIN from {file_path.name}: {e}")
            return None
    
    def clean_m4b_tags(self, file_path, preserve_asin=True):
        """Remove all tags from M4B file except ASIN (if preserve_asin=True)"""
        try:
            audio = MP4(file_path)
            if not audio:
                return False
            
            # Store ASIN if we need to preserve it
            preserved_asin = None
            if preserve_asin:
                asin_candidates = [
                    "----:com.apple.iTunes:ASIN",
                    "----:com.apple.iTunes:AUDIBLE_ASIN", 
                    "asin",
                    "CDEK"
                ]
                
                for tag in asin_candidates:
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
                audio["asin"] = [preserved_asin]
                audio["CDEK"] = [preserved_asin]
            
            # Save the cleaned file
            audio.save()
            return True
            
        except Exception as e:
            print(f"❌ Error cleaning {file_path.name}: {e}")
            return False
    
    def fetch_book_data(self, asin, locale="fr"):
        """Fetch book data from Audible API"""
        try:
            # Use the official Audible API
            url = f"https://api.audible.{locale}/1.0/catalog/products/{asin}"
            params = {
                "response_groups": "category_ladders,contributors,media,product_desc,product_attrs,product_extended_attrs,rating,series",
                "image_sizes": "500,1000",
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "product" not in data:
                return None
            
            return data["product"]
            
        except Exception as e:
            print(f"❌ Error fetching data for ASIN {asin}: {e}")
            return None
    
    def apply_tags_to_file(self, file_path, product_data, locale="fr"):
        """Apply tags to M4B file using the product data"""
        try:
            audio = MP4(file_path)
            if not audio:
                return False
            
            # Clear existing tags first
            audio.clear()
            
            # Basic tags
            title = product_data.get("title", "")
            if title:
                audio["\xa9nam"] = [title]
                audio["\xa9alb"] = [title]
            
            # Authors
            authors = product_data.get("authors", [])
            if authors:
                author_names = [author.get("name", "") for author in authors if author.get("name")]
                if author_names:
                    audio["\xa9ART"] = [", ".join(author_names)]
                    audio["aART"] = [author_names[0]]  # First author as album artist
                    audio["----:com.apple.iTunes:ALBUMARTISTS"] = [MP4FreeForm(", ".join(author_names).encode("utf-8"))]
            
            # Narrators (COMPOSER field)
            narrators = product_data.get("narrators", [])
            if narrators:
                narrator_names = [narrator.get("name", "") for narrator in narrators if narrator.get("name")]
                if narrator_names:
                    narrator_str = ", ".join(narrator_names)
                    # Set COMPOSER field (standard MP4 field)
                    audio["\xa9wrt"] = [narrator_str]
                    # Alternative narrator tags
                    audio["\xa9nrt"] = [narrator_str]
                    # Explicit COMPOSER tag for MP3Tag compatibility
                    audio["----:com.apple.iTunes:COMPOSER"] = [MP4FreeForm(narrator_str.encode("utf-8"))]
            
            # Year
            if "publication_datetime" in product_data:
                try:
                    year = product_data["publication_datetime"][:4]
                    if year:
                        audio["\xa9day"] = [year]
                except:
                    pass
            
            # Genre
            if "category_ladders" in product_data:
                genres = []
                for ladder_group in product_data["category_ladders"]:
                    if ladder_group.get("root") == "Genres":
                        for category in ladder_group.get("ladder", []):
                            genres.append(category.get("name", ""))
                if genres:
                    genres_str = " / ".join(genres)
                    audio["\xa9gen"] = [genres_str]
                    # Set GENRES field for MP3Tag compatibility
                    audio["----:com.apple.iTunes:GENRES"] = [MP4FreeForm(genres_str.encode("utf-8"))]
                    # Set first genre in TMP_GENRE1
                    audio["----:com.apple.iTunes:TMP_GENRE1"] = [MP4FreeForm(genres[0].encode("utf-8"))]
                    if len(genres) > 1:
                        audio["----:com.apple.iTunes:TMP_GENRE2"] = [MP4FreeForm(genres[1].encode("utf-8"))]
            else:
                audio["\xa9gen"] = ["Audiobook"]
            
            # Description/Comment
            description = ""
            if "publisher_summary" in product_data:
                description = product_data["publisher_summary"]
            elif "merchandising_summary" in product_data:
                description = product_data["merchandising_summary"]
            elif "product_desc" in product_data:
                description = product_data["product_desc"]
            
            if description:
                # Clean HTML tags and truncate if too long
                clean_description = clean_html(description)
                if len(clean_description) > 500:
                    clean_description = clean_description[:500] + "..."
                audio["\xa9cmt"] = [clean_description]
                audio["desc"] = [clean_description]
                audio["\xa9des"] = [clean_description]
                audio["----:com.apple.iTunes:DESCRIPTION"] = [MP4FreeForm(clean_description.encode("utf-8"))]
            
            # Subtitle
            subtitle = product_data.get("subtitle", "")
            if subtitle:
                audio["----:com.apple.iTunes:SUBTITLE"] = [MP4FreeForm(subtitle.encode("utf-8"))]
            
            # ASIN
            asin = product_data.get("asin", "")
            if asin:
                audio["asin"] = [asin]
                audio["CDEK"] = [asin]
                audio["----:com.apple.iTunes:ASIN"] = [MP4FreeForm(asin.encode("utf-8"))]
                audio["----:com.apple.iTunes:AUDIBLE_ASIN"] = [MP4FreeForm(asin.encode("utf-8"))]
                
                # WWW Audio File
                audible_url = f"https://www.audible.{locale}/pd/{asin}"
                audio["----:com.apple.iTunes:WWWAUDIOFILE"] = [MP4FreeForm(audible_url.encode("utf-8"))]
            
            # Language
            language = product_data.get("language", "")
            if language:
                audio["----:com.apple.iTunes:LANGUAGE"] = [MP4FreeForm(language.encode("utf-8"))]
            
            # Format
            format_type = product_data.get("format_type", "unabridged")
            audio["----:com.apple.iTunes:FORMAT"] = [MP4FreeForm(format_type.encode("utf-8"))]
            
            # Publisher
            publisher = product_data.get("publisher_name", "")
            if publisher:
                audio["\xa9pub"] = [publisher]
                audio["----:com.apple.iTunes:PUBLISHER"] = [MP4FreeForm(publisher.encode("utf-8"))]
                audio["\xa9cpy"] = [publisher]
            
            # Series
            if "series" in product_data and product_data["series"]:
                series_info = product_data["series"][0]
                series_title = series_info.get("title", "")
                series_part = series_info.get("sequence", "")
                
                if series_title:
                    audio["----:com.apple.iTunes:SERIES"] = [MP4FreeForm(series_title.encode("utf-8"))]
                    audio["----:com.apple.iTunes:MOVEMENTNAME"] = [MP4FreeForm(series_title.encode("utf-8"))]
                    audio["\xa9mvn"] = [series_title]
                
                if series_part:
                    audio["----:com.apple.iTunes:SERIES-PART"] = [MP4FreeForm(str(series_part).encode("utf-8"))]
                    audio["----:com.apple.iTunes:MOVEMENT"] = [MP4FreeForm(str(series_part).encode("utf-8"))]
                
                # Album sort with subtitle
                subtitle = product_data.get("subtitle", "")
                if series_title and series_part:
                    if subtitle:
                        album_sort = f"{series_title} {series_part} - {title}, {subtitle}"
                    else:
                        album_sort = f"{series_title} {series_part} - {title}"
                elif series_title:
                    if subtitle:
                        album_sort = f"{series_title} - {title}, {subtitle}"
                    else:
                        album_sort = f"{series_title} - {title}"
                else:
                    if subtitle:
                        album_sort = f"{title}, {subtitle}"
                    else:
                        album_sort = title
                audio["soal"] = [album_sort]
            
            # Handle album sort for non-series books
            if not product_data.get("series"):
                subtitle = product_data.get("subtitle", "")
                if subtitle:
                    album_sort = f"{title}, {subtitle}"
                else:
                    album_sort = title
                audio["soal"] = [album_sort]
            
            # Rating
            if "rating" in product_data:
                rating_data = product_data["rating"]
                if "overall_distribution" in rating_data:
                    rating = rating_data["overall_distribution"].get("display_average_rating")
                    if rating:
                        audio["----:com.apple.iTunes:RATING"] = [MP4FreeForm(str(rating).encode("utf-8"))]
                        audio["----:com.apple.iTunes:RATING WMP"] = [MP4FreeForm(str(rating).encode("utf-8"))]
            
            # Release time
            if "publication_datetime" in product_data:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(product_data["publication_datetime"].replace("Z", "+00:00"))
                    release_time = dt.strftime("%Y-%m-%d")
                    audio["----:com.apple.iTunes:RELEASETIME"] = [MP4FreeForm(release_time.encode("utf-8"))]
                except:
                    pass
            
            # Explicit/Adult content
            is_adult = product_data.get("is_adult_product", False)
            audio["----:com.apple.iTunes:EXPLICIT"] = [MP4FreeForm(b"1" if is_adult else b"0")]
            audio["----:com.apple.iTunes:ITUNESADVISORY"] = [MP4FreeForm(b"1" if is_adult else b"2")]
            
            # Audiobook specific tags
            audio["stik"] = [2]  # Audiobook
            audio["pgap"] = [True]  # Gapless
            
            # Save the file
            audio.save()
            return True
            
        except Exception as e:
            print(f"❌ Error applying tags to {file_path.name}: {e}")
            return False
    
    def process_file(self, file_path, action, locale="fr", preserve_asin=True):
        """Process a single M4B file"""
        print(f"\n📁 Processing: {file_path.name}")
        
        if action == "clean":
            success = self.clean_m4b_tags(file_path, preserve_asin)
            if success:
                print(f"✅ Cleaned: {file_path.name}")
            else:
                print(f"❌ Failed to clean: {file_path.name}")
            return success
        
        elif action == "tag":
            # Extract ASIN
            asin = self.extract_asin_from_file(file_path)
            if not asin:
                print(f"⚠️  No ASIN found in: {file_path.name}")
                return False
            
            # Fetch data
            print(f"🔍 Fetching data for ASIN: {asin}")
            product_data = self.fetch_book_data(asin, locale)
            if not product_data:
                print(f"❌ Failed to fetch data for: {file_path.name}")
                return False
            
            # Apply tags
            success = self.apply_tags_to_file(file_path, product_data, locale)
            if success:
                print(f"✅ Tagged: {file_path.name}")
            else:
                print(f"❌ Failed to tag: {file_path.name}")
            return success
        
        elif action == "clean-and-tag":
            # First clean
            clean_success = self.clean_m4b_tags(file_path, preserve_asin)
            if not clean_success:
                print(f"❌ Failed to clean: {file_path.name}")
                return False
            
            # Then tag
            asin = self.extract_asin_from_file(file_path)
            if not asin:
                print(f"⚠️  No ASIN found in: {file_path.name}")
                return False
            
            print(f"🔍 Fetching data for ASIN: {asin}")
            product_data = self.fetch_book_data(asin, locale)
            if not product_data:
                print(f"❌ Failed to fetch data for: {file_path.name}")
                return False
            
            success = self.apply_tags_to_file(file_path, product_data, locale)
            if success:
                print(f"✅ Cleaned and tagged: {file_path.name}")
            else:
                print(f"❌ Failed to tag: {file_path.name}")
            return success
        
        return False
    
    def process_library(self, action="clean-and-tag", locale="fr", preserve_asin=True):
        """Process all M4B files in the library"""
        print(f"🎧 Library Processor - {action.upper()}")
        print(f"Library: {self.library_path}")
        print(f"Locale: {locale}")
        print(f"Preserve ASIN: {preserve_asin}")
        print("=" * 60)
        
        # Find all M4B files
        m4b_files = self.find_m4b_files()
        if not m4b_files:
            print("❌ No M4B files found in library")
            return
        
        # Process each file
        successful = 0
        failed = 0
        
        for file_path in m4b_files:
            try:
                success = self.process_file(file_path, action, locale, preserve_asin)
                if success:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ Unexpected error processing {file_path.name}: {e}")
                failed += 1
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 PROCESSING COMPLETE")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📁 Total files: {len(m4b_files)}")
        
        if successful > 0:
            print(f"\n🎉 Successfully processed {successful} files!")

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Unified library processor for M4B files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clean and re-tag all files (default)
  python3 library_processor.py
  
  # Only clean files (preserve ASIN)
  python3 library_processor.py --action clean
  
  # Only tag files (requires existing ASIN)
  python3 library_processor.py --action tag
  
  # Clean and tag with US locale
  python3 library_processor.py --locale com
  
  # Clean completely (remove ASIN too)
  python3 library_processor.py --action clean --remove-asin
        """
    )
    
    parser.add_argument(
        "--action",
        choices=["clean", "tag", "clean-and-tag"],
        default="clean-and-tag",
        help="Action to perform (default: clean-and-tag)"
    )
    
    parser.add_argument(
        "--locale",
        default="fr",
        help="Audible locale for API calls (default: fr)"
    )
    
    parser.add_argument(
        "--library-path",
        default="data/library",
        help="Path to library directory (default: data/library)"
    )
    
    parser.add_argument(
        "--remove-asin",
        action="store_true",
        help="Remove ASIN tags when cleaning (default: preserve ASIN)"
    )
    
    args = parser.parse_args()
    
    # Create processor
    processor = LibraryProcessor(args.library_path)
    
    # Process library
    processor.process_library(
        action=args.action,
        locale=args.locale,
        preserve_asin=not args.remove_asin
    )

if __name__ == "__main__":
    main()
