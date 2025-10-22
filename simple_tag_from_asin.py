#!/usr/bin/env python3
"""
Simple script to tag an M4B file by reading its ASIN and fetching data from the API
This version doesn't require complex type imports
"""

import sys
import os
import json
import requests
from pathlib import Path
from mutagen.mp4 import MP4, MP4FreeForm

def extract_asin_from_file(file_path):
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
                        print(f"✅ Found ASIN: {asin} (from {tag_name})")
                        return asin
        
        return None
        
    except Exception as e:
        print(f"❌ Error extracting ASIN: {e}")
        return None

def fetch_book_data(asin, locale="fr"):
    """Fetch book data from Audible API"""
    try:
        print(f"🔍 Fetching data for ASIN: {asin} (locale: {locale})")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Use the official Audible API
        url = f"https://api.audible.{locale}/1.0/catalog/products/{asin}"
        params = {
            "response_groups": "category_ladders,contributors,media,product_desc,product_attrs,product_extended_attrs,rating,series",
            "image_sizes": "500,1000",
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if "product" not in data:
            print(f"❌ No 'product' key in API response")
            return None
        
        product = data["product"]
        print(f"✅ Successfully fetched data for: {product.get('title', 'Unknown Title')}")
        
        return product
        
    except Exception as e:
        print(f"❌ Error fetching book data: {e}")
        return None

def apply_tags_to_file(file_path, product_data):
    """Apply tags to M4B file using the product data"""
    try:
        print("🏷️  Applying tags...")
        
        audio = MP4(file_path)
        if not audio:
            print("❌ Could not load M4B file")
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
        
        # Narrators
        narrators = product_data.get("narrators", [])
        if narrators:
            narrator_names = [narrator.get("name", "") for narrator in narrators if narrator.get("name")]
            if narrator_names:
                audio["\xa9wrt"] = [", ".join(narrator_names)]
                audio["\xa9nrt"] = [", ".join(narrator_names)]
        
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
                audio["\xa9gen"] = [" / ".join(genres)]
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
            # Truncate if too long
            if len(description) > 500:
                description = description[:500] + "..."
            audio["\xa9cmt"] = [description]
            audio["desc"] = [description]
            audio["\xa9des"] = [description]
            audio["----:com.apple.iTunes:DESCRIPTION"] = [MP4FreeForm(description.encode("utf-8"))]
        
        # ASIN
        asin = product_data.get("asin", "")
        if asin:
            audio["asin"] = [asin]
            audio["CDEK"] = [asin]
            audio["----:com.apple.iTunes:ASIN"] = [MP4FreeForm(asin.encode("utf-8"))]
            audio["----:com.apple.iTunes:AUDIBLE_ASIN"] = [MP4FreeForm(asin.encode("utf-8"))]
            
            # WWW Audio File
            locale = "fr"  # Default locale
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
                audio["\xa9mvn"] = [series_title]
            
            if series_part:
                audio["----:com.apple.iTunes:SERIES-PART"] = [MP4FreeForm(str(series_part).encode("utf-8"))]
                audio["shwm"] = [int(series_part)]
            
            # Album sort
            if series_title and series_part:
                album_sort = f"{series_title} {series_part} - {title}"
            elif series_title:
                album_sort = f"{series_title} - {title}"
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
        print("✅ Successfully applied all tags!")
        return True
        
    except Exception as e:
        print(f"❌ Error applying tags: {e}")
        return False

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("Usage: python3 simple_tag_from_asin.py <m4b_file_path> [--locale <locale>]")
        print("  --locale: Audible locale (default: fr)")
        print("  Example: python3 simple_tag_from_asin.py 'book.m4b' --locale com")
        sys.exit(1)
    
    file_path = sys.argv[1]
    locale = "fr"  # Default locale
    
    # Parse locale argument
    if "--locale" in sys.argv:
        try:
            locale_index = sys.argv.index("--locale")
            if locale_index + 1 < len(sys.argv):
                locale = sys.argv[locale_index + 1]
        except (ValueError, IndexError):
            print("❌ Invalid --locale argument")
            sys.exit(1)
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    if not file_path.lower().endswith('.m4b'):
        print("❌ File must be an M4B file")
        sys.exit(1)
    
    print(f"🎧 Simple ASIN-based M4B Tagger")
    print(f"File: {file_path}")
    print(f"Locale: {locale}")
    print("-" * 50)
    
    # Extract ASIN from file
    asin = extract_asin_from_file(file_path)
    if not asin:
        print("❌ No ASIN found in file")
        sys.exit(1)
    
    # Fetch book data
    product_data = fetch_book_data(asin, locale)
    if not product_data:
        print("❌ Failed to fetch book data")
        sys.exit(1)
    
    # Apply tags
    success = apply_tags_to_file(file_path, product_data)
    
    if success:
        print("\n🎉 File tagging completed successfully!")
    else:
        print("\n❌ File tagging failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
