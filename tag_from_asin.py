#!/usr/bin/env python3
"""
Script to tag an M4B file by reading its ASIN and fetching data from the API
"""

import sys
import os
import json
import requests
from pathlib import Path
from mutagen.mp4 import MP4

# Add the tagger directory to the path
sys.path.append('/Users/donet/Downloads/st4ck/tagger')

try:
    from m4b_tagger import M4BTagger
    from tagger.types import BookDataType
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the st4ck directory")
    sys.exit(1)

class ASINTagger:
    def __init__(self):
        self.tagger = M4BTagger()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
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
                            print(f"✅ Found ASIN: {asin} (from {tag_name})")
                            return asin
            
            return None
            
        except Exception as e:
            print(f"❌ Error extracting ASIN: {e}")
            return None
    
    def fetch_book_data(self, asin, locale="fr"):
        """Fetch book data from Audible API"""
        try:
            print(f"🔍 Fetching data for ASIN: {asin} (locale: {locale})")
            
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
                print(f"❌ No 'product' key in API response")
                return None
            
            product = data["product"]
            print(f"✅ Successfully fetched data for: {product.get('title', 'Unknown Title')}")
            
            return self._convert_to_book_data(product)
            
        except Exception as e:
            print(f"❌ Error fetching book data: {e}")
            return None
    
    def _convert_to_book_data(self, product):
        """Convert Audible API product data to BookDataType"""
        try:
            # Extract basic information
            asin = product.get("asin", "")
            title = product.get("title", "")
            subtitle = product.get("subtitle", "")
            language = product.get("language", "")
            publisher_name = product.get("publisher_name", "")
            format_type = product.get("format_type", "")
            is_adult_product = product.get("is_adult_product", False)
            
            # Extract authors
            authors = []
            if "authors" in product:
                for author in product["authors"]:
                    if author.get("name"):
                        authors.append(type('Author', (), {'name': author["name"]})())
            
            # Extract narrators
            narrators = []
            if "narrators" in product:
                for narrator in product["narrators"]:
                    if narrator.get("name"):
                        narrators.append(type('Narrator', (), {'name': narrator["name"]})())
            
            # Extract series information
            series = []
            if "series" in product and product["series"]:
                series_info = product["series"][0]
                series.append(type('Series', (), {
                    'title': series_info.get("title", ""),
                    'sequence': str(series_info.get("sequence", ""))
                })())
            
            # Extract description
            description = ""
            if "publisher_summary" in product:
                description = product["publisher_summary"]
            elif "merchandising_summary" in product:
                description = product["merchandising_summary"]
            elif "product_desc" in product:
                description = product["product_desc"]
            
            # Extract genres from category ladders
            category_ladders = []
            if "category_ladders" in product:
                for ladder_group in product["category_ladders"]:
                    if ladder_group.get("root") == "Genres":
                        ladder_items = []
                        for category in ladder_group.get("ladder", []):
                            ladder_items.append(type('LadderItem', (), {'name': category.get("name", "")})())
                        category_ladders.append(type('LadderGroup', (), {'ladder': ladder_items})())
            
            # Extract rating
            rating = None
            if "rating" in product:
                rating_data = product["rating"]
                if "overall_distribution" in rating_data:
                    rating = rating_data["overall_distribution"].get("display_average_rating")
            
            # Extract release date
            publication_datetime = product.get("publication_datetime", "")
            release_date = product.get("release_date", "")
            
            # Create BookDataType object
            book_data = BookDataType(
                asin=asin,
                title=title,
                subtitle=subtitle,
                authors=authors,
                narrators=narrators,
                series=series,
                publisher_name=publisher_name,
                language=language,
                format_type=format_type,
                is_adult_product=is_adult_product,
                publisher_summary=description,
                extended_product_description=description,
                merchandising_summary=description,
                category_ladders=category_ladders,
                rating=rating,
                publication_datetime=publication_datetime,
                release_date=release_date
            )
            
            return book_data
            
        except Exception as e:
            print(f"❌ Error converting book data: {e}")
            return None
    
    def tag_file_from_asin(self, file_path, locale="fr"):
        """Tag a file by reading its ASIN and fetching data"""
        try:
            print(f"🎧 Tagging file from ASIN: {file_path}")
            
            # Extract ASIN from file
            asin = self.extract_asin_from_file(file_path)
            if not asin:
                print("❌ No ASIN found in file")
                return False
            
            # Fetch book data
            book_data = self.fetch_book_data(asin, locale)
            if not book_data:
                print("❌ Failed to fetch book data")
                return False
            
            # Tag the file
            print("🏷️  Applying tags...")
            success = self.tagger.tag_file(file_path, book_data)
            
            if success:
                print("✅ Successfully tagged file!")
                return True
            else:
                print("❌ Failed to tag file")
                return False
                
        except Exception as e:
            print(f"❌ Error tagging file: {e}")
            return False

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("Usage: python3 tag_from_asin.py <m4b_file_path> [--locale <locale>]")
        print("  --locale: Audible locale (default: fr)")
        print("  Example: python3 tag_from_asin.py 'book.m4b' --locale com")
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
    
    print(f"🎧 ASIN-based M4B Tagger")
    print(f"File: {file_path}")
    print(f"Locale: {locale}")
    print("-" * 50)
    
    # Create tagger and process file
    tagger = ASINTagger()
    success = tagger.tag_file_from_asin(file_path, locale)
    
    if success:
        print("\n🎉 File tagging completed successfully!")
    else:
        print("\n❌ File tagging failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
