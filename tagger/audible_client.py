#!/usr/bin/env python3
"""
Audible API Client for searching and getting book details
Streamlined from auto-m4b-audible-tagger
"""

import re
import json
import logging
from typing import Dict, List, Optional
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class AudibleAPIClient:
    """Client for interacting with Audible's API"""
    
    def __init__(self):
        # Audible API headers (simulating a browser)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Base URLs for different locales
        self.base_urls = {
            "com": "https://www.audible.com",
            "uk": "https://www.audible.co.uk", 
            "de": "https://www.audible.de",
            "fr": "https://www.audible.fr",
            "ca": "https://www.audible.ca",
            "au": "https://www.audible.com.au",
            "jp": "https://www.audible.jp",
            "in": "https://www.audible.in"
        }
    
    def clean_html_text(self, html_text: str) -> str:
        """Clean HTML text and format for plain text"""
        if not html_text:
            return ""
        
        # Replace common HTML entities
        html_text = html_text.replace("&nbsp;", " ")
        html_text = html_text.replace("&amp;", "&")
        html_text = html_text.replace("&lt;", "<")
        html_text = html_text.replace("&gt;", ">")
        html_text = html_text.replace("&quot;", '"')
        html_text = html_text.replace("&#39;", "'")
        html_text = html_text.replace("&apos;", "'")
        html_text = html_text.replace("&ldquo;", '"')
        html_text = html_text.replace("&rdquo;", '"')
        html_text = html_text.replace("&lsquo;", "'")
        html_text = html_text.replace("&rsquo;", "'")
        html_text = html_text.replace("&mdash;", "—")
        html_text = html_text.replace("&ndash;", "–")
        html_text = html_text.replace("&hellip;", "...")
        
        # Remove HTML tags
        clean_text = re.sub(r"<[^>]+>", "", html_text)
        
        # Split into paragraphs and clean each one
        paragraphs = clean_text.split("\n")
        clean_text = "\n\n".join([p.strip() for p in paragraphs if p.strip()])
        
        return clean_text
    
    def _is_translator_name(self, name: str) -> bool:
        """Return True if the provided name likely denotes a translator/translation credit."""
        lowered = (name or "").lower()
        # French variants: traducteur / traductrice, and words containing "traduct"
        if "traduct" in lowered:
            return True
        # English variant
        if "translator" in lowered:
            return True
        return False

    def _is_illustrator_name(self, name: str) -> bool:
        """Return True if the provided name likely denotes an illustrator/illustration credit."""
        lowered = (name or "").lower()
        # French variants: illustrateur / illustratrice, and words containing "illustr"
        if "illustr" in lowered:
            return True
        # English variant
        if "illustrator" in lowered:
            return True
        return False

    def _format_person_list(self, names: List[str]) -> str:
        """Join a list of names into a natural-language string."""
        names = [n.strip() for n in names if n and n.strip()]
        if not names:
            return "Unknown Author"
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return f"{', '.join(names[:-1])}, and {names[-1]}"

    def process_authors(self, authors: List[Dict]) -> str:
        """Process authors list and return formatted author string"""
        if not authors:
            return "Unknown Author"
        
        author_names = []
        for author in authors:
            name = author.get("name", "").strip()
            if name and not self._is_translator_name(name) and not self._is_illustrator_name(name):
                author_names.append(name)
        return self._format_person_list(author_names)
    
    def parse_filename(self, filename: str) -> tuple[str, str]:
        """Parse filename to extract title and author"""
        # Remove file extension
        name = Path(filename).stem
        
        # Common patterns for audiobook filenames
        patterns = [
            r"^(.+?)\s+by\s+(.+?)$",  # "Title by Author"
            r"^(.+?)\s+-\s+(.+?)$",   # "Title - Author"
            r"^(.+?)\s+\((.+?)\)$",   # "Title (Author)"
            r"^(.+?)\s+\[(.+?)\]$",   # "Title [Author]"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, name, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                author = match.group(2).strip()
                return title, author
        
        # If no pattern matches, assume the whole filename is the title
        return name, "Unknown Author"
    
    def search_audible(self, query: str, locale: str = "fr") -> List[Dict]:
        """Search Audible for books matching the query using the official API"""
        try:
            # Use baked-in search locales with preferred locale first
            locales = [
                "fr",
                "com",
                "co.uk", 
                "ca",
                "de",
                "it",
                "es",
                "co.jp",
                "com.au",
                "com.br",
            ]
            preferred_locale = locale

            # Put preferred locale first in search order
            if preferred_locale in locales:
                locales.remove(preferred_locale)
            locales.insert(0, preferred_locale)

            results = []

            for search_locale in locales:
                try:
                    # Search API endpoint
                    search_url = f"https://api.audible.{search_locale}/1.0/catalog/products"
                    params = {
                        "keywords": query,
                        "response_groups": "category_ladders,contributors,media,product_desc,product_attrs,product_extended_attrs,rating,series",
                        "image_sizes": "500,1000",
                        "num_results": "5",
                    }

                    response = requests.get(
                        search_url, params=params, headers=self.headers, timeout=10
                    )
                    response.raise_for_status()

                    data = response.json()
                    if "products" in data:
                        for product in data["products"]:
                            # Extract basic info
                            asin = product.get("asin", "")
                            title = product.get("title", "Unknown Title")

                            # Extract authors using the new processing method
                            author = self.process_authors(product.get("authors", []))

                            # Extract narrators
                            narrators = []
                            if "narrators" in product:
                                for narrator in product["narrators"]:
                                    narrators.append(narrator.get("name", ""))

                            narrator = ", ".join(narrators) if narrators else ""

                            # Extract series information
                            series = ""
                            series_part = ""
                            if "series" in product and product["series"]:
                                series_data = product["series"]
                                if isinstance(series_data, list) and len(series_data) > 0:
                                    # Take the first series if multiple exist
                                    series_info = series_data[0]
                                    series = series_info.get("title", "")
                                    series_part = series_info.get("sequence", "")  # sequence is already a string in the API
                                elif isinstance(series_data, dict):
                                    series = series_data.get("title", "")
                                    series_part = series_data.get("sequence", "")

                            # Check if we already have this ASIN
                            if not any(r["asin"] == asin for r in results):
                                # Extract additional fields for UI compatibility
                                description = product.get("publisher_summary", "")
                                if description:
                                    description = self.clean_html_text(description)
                                
                                cover_url = ""
                                if "product_images" in product:
                                    images = product["product_images"]
                                    cover_url = images.get("1000", images.get("500", ""))
                                
                                duration = ""
                                if "runtime_length_min" in product:
                                    duration = f"{product['runtime_length_min']} minutes"
                                
                                release_date = product.get("publication_datetime", "")
                                if release_date:
                                    try:
                                        from datetime import datetime
                                        dt = datetime.fromisoformat(release_date.replace("Z", "+00:00"))
                                        release_date = dt.strftime("%Y-%m-%d")
                                    except:
                                        release_date = release_date[:10] if len(release_date) >= 10 else ""
                                
                                results.append(
                                    {
                                        "title": title,
                                        "author": author,
                                        "narrator": narrator,
                                        "series": series,
                                        "series_part": series_part,
                                        "asin": asin,
                                        "locale": search_locale,
                                        "description": description,
                                        "cover_url": cover_url,
                                        "duration": duration,
                                        "release_date": release_date,
                                        "language": product.get("language", ""),
                                        "publisher": product.get("publisher_name", ""),
                                    }
                                )

                        # If we found results, we can stop searching other locales
                        if results:
                            break

                except Exception as e:
                    logger.warning(f"Error searching Audible {search_locale}: {e}")
                    continue

            logger.info(f"Found {len(results)} search results for query: {query}")
            return results[:5]  # Limit to 5 results

        except Exception as e:
            logger.error(f"Error searching Audible: {e}")
            return []
    
    
    def get_book_details(self, asin: str, locale: str = "fr") -> Optional[Dict]:
        """Get detailed book information from Audible using the official API"""
        try:
            # Use the official Audible API
            url = f"https://api.audible.{locale}/1.0/catalog/products/{asin}"
            params = {
                "response_groups": "category_ladders,contributors,media,product_desc,product_attrs,product_extended_attrs,rating,series",
                "image_sizes": "500,1000",
            }

            response = requests.get(
                url, params=params, headers=self.headers, timeout=10
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"API Response keys: {list(data.keys())}")

            if "product" not in data:
                logger.error(
                    f"No 'product' key in API response. Available keys: {list(data.keys())}"
                )
                return None
            # Validate into our Pydantic models
            # Load Pydantic models robustly from tagger/types.py to avoid stdlib 'types' collision
            try:
                import importlib.util
                from pathlib import Path as _Path
                types_path_candidates = [
                    _Path(__file__).parent / "types.py",
                    _Path("/app/tagger/types.py"),
                ]
                AudibleAPIResponse = None
                for _p in types_path_candidates:
                    if _p.exists():
                        spec = importlib.util.spec_from_file_location("tagger_types", str(_p))
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                            if hasattr(mod, "AudibleAPIResponse"):
                                AudibleAPIResponse = getattr(mod, "AudibleAPIResponse")
                                break
                if AudibleAPIResponse is None:
                    raise ImportError("AudibleAPIResponse not found in types module")
            except Exception as e:
                logger.error(f"Failed to load AudibleAPIResponse model: {e}")
                return None

            api_response = AudibleAPIResponse.model_validate(data)  # type: ignore[call-arg]
            product = api_response.product
            logger.info(f"Product keys parsed via model. ASIN={product.asin}, title={product.title}")
            return product

        except Exception as e:
            logger.error(f"Error fetching book details: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def download_cover(self, cover_url: str, asin: str, covers_dir: Path) -> Optional[str]:
        """Download cover image for a book"""
        try:
            if not cover_url:
                return None
            
            # Create covers directory if it doesn't exist
            covers_dir.mkdir(exist_ok=True)
            
            # Determine file extension
            if '.jpg' in cover_url.lower() or '.jpeg' in cover_url.lower():
                ext = '.jpg'
            elif '.png' in cover_url.lower():
                ext = '.png'
            else:
                ext = '.jpg'  # Default to jpg
            
            cover_path = covers_dir / f"{asin}_cover{ext}"
            
            # Download the cover
            response = requests.get(cover_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            with open(cover_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded cover for {asin}: {cover_path}")
            return str(cover_path)
            
        except Exception as e:
            logger.error(f"Error downloading cover for {asin}: {e}")
            return None
    
    def handle_no_search_results(self, query: str, locale: str = "fr") -> List[Dict]:
        """Handle cases where no search results are found"""
        logger.info(f"No results found for query: {query}")
        
        # Try alternative search strategies
        alternative_queries = [
            # Remove common words
            re.sub(r'\b(the|and|or|in|on|at|to|for|of|with|from|by)\b', '', query, flags=re.IGNORECASE).strip(),
            # Try just the first few words
            ' '.join(query.split()[:3]),
            # Try without numbers
            re.sub(r'\d+', '', query).strip(),
            # Try with quotes for exact phrase
            f'"{query}"'
        ]
        
        for alt_query in alternative_queries:
            if alt_query and alt_query != query:
                logger.info(f"Trying alternative query: {alt_query}")
                results = self.search_audible(alt_query, locale)
                if results:
                    return results
        
        return []
