#!/usr/bin/env python3
"""
M4B File Tagger for adding metadata to audiobook files
Streamlined from auto-m4b-audible-tagger
"""

import logging
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm

from .constants import TagConstants

logger = logging.getLogger(__name__)

class M4BTagger:
    """Class for tagging M4B files with metadata"""
    
    def __init__(self, library_dir: Path, covers_dir: Path):
        self.library_dir = library_dir
        self.covers_dir = covers_dir
        
        # Create directories if they don't exist
        self.library_dir.mkdir(exist_ok=True)
        self.covers_dir.mkdir(exist_ok=True)
    
    def tag_file(self, file_path: Path, book_data: Dict, cover_path: Optional[str] = None) -> bool:
        """Tag an M4B file with book metadata"""
        try:
            logger.info(f"Tagging file: {file_path}")
            
            # Load the M4B file
            audio = MP4(file_path)
            
            # Set basic tags
            logger.info("Setting basic tags...")
            self._set_basic_tags(audio, book_data)
            logger.info("Basic tags set successfully")
            
            # Set custom iTunes tags
            logger.info("Setting custom tags...")
            self._set_custom_tags(audio, book_data)
            logger.info("Custom tags set successfully")
            
            # Add cover if available
            if cover_path and Path(cover_path).exists():
                logger.info(f"Adding cover art: {cover_path}")
                self._add_cover(audio, cover_path)
                logger.info("Cover art added successfully")
            
            # Save the tags
            logger.info("Saving file...")
            audio.save()
            logger.info(f"Successfully tagged: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error tagging file {file_path}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def _set_basic_tags(self, audio: MP4, book_data: Dict):
        """Set basic M4B tags"""
        # Title
        if book_data.get("title"):
            audio[TagConstants.TITLE] = self._ensure_string(book_data["title"])
        
        # Album (same as title for audiobooks)
        if book_data.get("title"):
            audio[TagConstants.ALBUM] = self._ensure_string(book_data["title"])
        
        # Artist (author)
        if book_data.get("author"):
            audio[TagConstants.ARTIST] = self._ensure_string(book_data["author"])
        
        # Album Artist
        if book_data.get("author"):
            audio[TagConstants.ALBUM_ARTIST] = self._ensure_string(book_data["author"])
        
        # Year
        if book_data.get("release_time"):
            release_time_str = self._ensure_string(book_data["release_time"])
            year = self._extract_year(release_time_str)
            if year:
                audio[TagConstants.YEAR] = year
        elif book_data.get("release_date"):
            release_date_str = self._ensure_string(book_data["release_date"])
            year = self._extract_year(release_date_str)
            if year:
                audio[TagConstants.YEAR] = year
        
        # Genre
        audio[TagConstants.GENRE] = "Audiobook"
        
        # Comment
        if book_data.get("description"):
            # Truncate description if too long
            description = self._ensure_string(book_data["description"])
            if len(description) > 500:
                description = description[:500] + "..."
            audio[TagConstants.COMMENT] = description
    
    def _set_custom_tags(self, audio: MP4, book_data: Dict):
        """Set custom iTunes tags"""
        # ASIN
        if book_data.get("asin"):
            logger.info(f"Processing ASIN: {book_data['asin']} (type: {type(book_data['asin'])})")
            asin_str = self._ensure_string(book_data["asin"])
            asin_tag = MP4FreeForm(asin_str.encode("utf-8"))
            audio[TagConstants.ASIN] = [asin_tag]
            audio[TagConstants.AUDIBLE_ASIN] = [asin_tag]
        
        # Language
        if book_data.get("language"):
            lang_str = self._ensure_string(book_data["language"])
            lang_tag = MP4FreeForm(lang_str.encode("utf-8"))
            audio[TagConstants.LANGUAGE] = [lang_tag]
        
        # Format
        format_tag = MP4FreeForm(b"Audiobook")
        audio[TagConstants.FORMAT] = [format_tag]
        
        # Series information
        if book_data.get("series"):
            series_str = self._ensure_string(book_data["series"])
            series_tag = MP4FreeForm(series_str.encode("utf-8"))
            audio[TagConstants.SERIES] = [series_tag]
        
        if book_data.get("series_part"):
            series_part_str = self._ensure_string(book_data["series_part"])
            series_part_tag = MP4FreeForm(series_part_str.encode("utf-8"))
            audio[TagConstants.SERIES_PART] = [series_part_tag]
        
        # Narrator
        if book_data.get("narrator"):
            logger.info(f"Processing narrator: {book_data['narrator']} (type: {type(book_data['narrator'])})")
            narrator_str = self._ensure_string(book_data["narrator"])
            logger.info(f"Narrator after _ensure_string: {narrator_str} (type: {type(narrator_str)})")
            audio[TagConstants.NARRATOR_ALT] = narrator_str
        
        # Publisher
        if book_data.get("publisher_name"):
            publisher_str = self._ensure_string(book_data["publisher_name"])
            audio[TagConstants.PUBLISHER_ALT] = publisher_str
        elif book_data.get("publisher"):
            publisher_str = self._ensure_string(book_data["publisher"])
            audio[TagConstants.PUBLISHER_ALT] = publisher_str
        
        # Duration
        if book_data.get("runtime_length_min"):
            duration_str = self._ensure_string(book_data["runtime_length_min"])
            audio[TagConstants.DESC_ALT] = duration_str
        elif book_data.get("duration"):
            duration_str = self._ensure_string(book_data["duration"])
            audio[TagConstants.DESC_ALT] = duration_str
    
    def _add_cover(self, audio: MP4, cover_path: str):
        """Add cover art to the M4B file"""
        try:
            with open(cover_path, 'rb') as f:
                cover_data = f.read()
            
            # Determine cover format
            if cover_path.lower().endswith('.png'):
                cover = MP4Cover(cover_data, MP4Cover.FORMAT_PNG)
            else:
                cover = MP4Cover(cover_data, MP4Cover.FORMAT_JPEG)
            
            audio['covr'] = [cover]
            logger.info(f"Added cover art from: {cover_path}")
            
        except Exception as e:
            logger.error(f"Error adding cover art: {e}")
    
    def _extract_year(self, date_string: str) -> Optional[str]:
        """Extract year from date string"""
        import re
        
        # Try to find 4-digit year
        year_match = re.search(r'\b(19|20)\d{2}\b', date_string)
        if year_match:
            return year_match.group()
        
        return None
    
    def move_to_library(self, file_path: Path, book_data: Dict, cover_path: Optional[str] = None) -> Optional[Path]:
        """Move tagged file to library with organized structure"""
        try:
            # Create organized directory structure
            author = self._clean_filename(book_data.get("author", "Unknown Author"))
            title = self._clean_filename(book_data.get("title", "Unknown Title"))
            series = book_data.get("series", "")
            series_part = book_data.get("series_part", "")
            
            # Debug logging
            logger.info(f"Library structure - Author: '{author}', Title: '{title}'")
            logger.info(f"Library structure - Series: '{series}', Series Part: '{series_part}'")
            
            # Create author directory
            author_dir = self.library_dir / author
            author_dir.mkdir(exist_ok=True)
            
            # Determine the final directory structure
            if series:
                # Clean series name - remove part number if present
                clean_series = series
                if " #" in series:
                    clean_series = series.split(" #")[0].strip()
                    logger.info(f"Cleaned series name: '{series}' -> '{clean_series}'")
                
                # Create series directory under author
                series_dir = author_dir / self._clean_filename(clean_series)
                series_dir.mkdir(exist_ok=True)
                
                # Create book directory with series info in the name
                if series_part:
                    book_dir_name = f"{title} ({clean_series} #{series_part})"
                else:
                    book_dir_name = f"{title} ({clean_series})"
                
                book_dir = series_dir / self._clean_filename(book_dir_name)
            else:
                # Single book, no series - put directly under author
                book_dir = author_dir / self._clean_filename(title)
            
            book_dir.mkdir(exist_ok=True)
            
            # Create the final filename for the M4B file
            if series and series_part:
                m4b_filename = f"{title} ({clean_series} #{series_part}).m4b"
            elif series:
                m4b_filename = f"{title} ({clean_series}).m4b"
            else:
                m4b_filename = f"{title}.m4b"
            
            # Move the M4B file
            dest_file = book_dir / self._clean_filename(m4b_filename)
            shutil.move(str(file_path), str(dest_file))
            
            # Move cover if it exists
            if cover_path and Path(cover_path).exists():
                cover_ext = Path(cover_path).suffix
                dest_cover = book_dir / f"cover{cover_ext}"
                shutil.move(cover_path, str(dest_cover))
            
            # Create metadata files
            self.create_additional_metadata_files(book_dir, book_data, cover_path)
            
            logger.info(f"Moved to library: {dest_file}")
            return dest_file
            
        except Exception as e:
            logger.error(f"Error moving file to library: {e}")
            return None
    
    def create_opf_content(self, metadata: Dict) -> str:
        """Create OPF (Open Packaging Format) content for metadata"""
        try:
            logger.info(f"Creating OPF content for metadata: {metadata.get('title', 'Unknown')}")
            title = self._ensure_string(metadata.get("title", "Unknown Title"))
            author = self._ensure_string(metadata.get("author", "Unknown Author"))
            description = self._ensure_string(metadata.get("description", ""))
            narrator = self._ensure_string(metadata.get("narrator", ""))
            series = self._ensure_string(metadata.get("series", ""))
            series_part = self._ensure_string(metadata.get("series_part", ""))
            asin = self._ensure_string(metadata.get("asin", ""))
            publisher = self._ensure_string(metadata.get("publisher_name", metadata.get("publisher", "")))
            language = self._ensure_string(metadata.get("language", "en"))
            release_date = self._ensure_string(metadata.get("release_date", ""))
            
            # Create unique identifier
            identifier = asin if asin else f"book_{hash(title + author)}"
            
            # Build series information
            series_info = ""
            if series:
                series_info = f'<dc:subject opf:authority="series">{series}</dc:subject>'
                if series_part:
                    series_info += f'\n        <meta property="series-part">{series_part}</meta>'
            
            # Build narrator information
            narrator_info = ""
            if narrator:
                narrator_info = f'<dc:contributor role="nrt">{narrator}</dc:contributor>'
            
            # Build publisher information
            publisher_info = ""
            if publisher:
                publisher_info = f'<dc:publisher>{publisher}</dc:publisher>'
            
            # Build language information
            language_info = f'<dc:language>{language}</dc:language>'
            
            # Build date information
            date_info = ""
            if release_date:
                # Extract year from release date
                year_match = re.search(r'\b(19|20)\d{2}\b', release_date)
                if year_match:
                    date_info = f'<dc:date>{year_match.group()}</dc:date>'
            
            opf_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:identifier id="BookId">{identifier}</dc:identifier>
        <dc:title>{title}</dc:title>
        <dc:creator>{author}</dc:creator>
        {publisher_info}
        <dc:language>{language}</dc:language>
        <dc:description>{description}</dc:description>
        <dc:subject>Fiction</dc:subject>
        <dc:subject>Audiobook</dc:subject>
        {self._build_subject_tags(metadata)}
        {date_info}
        <dc:identifier opf:scheme="ASIN">{identifier}</dc:identifier>
        {narrator_info}
        {series_info}
        <meta property="duration">{metadata.get("duration", "0")}</meta>
        <meta property="rating">{metadata.get("rating", "0")}</meta>
    </metadata>
<manifest>
    <item id="cover" href="cover.jpg" media-type="image/jpeg"/>
</manifest>
<spine>
    <itemref idref="cover"/>
</spine>
</package>'''
            
            return opf_content
            
        except Exception as e:
            logger.error(f"Error creating OPF content: {e}")
            return ""
    
    def create_additional_metadata_files(self, dest_dir: Path, metadata: Dict, cover_path: Optional[Path] = None) -> None:
        """Create additional metadata files compatible with Audiobookshelf"""
        try:
            logger.info(f"Creating additional metadata files in: {dest_dir}")
            # Create desc.txt (description)
            if metadata.get("description"):
                desc_content = self._ensure_string(metadata["description"])
                desc_file = dest_dir / "desc.txt"
                with open(desc_file, "w", encoding="utf-8") as f:
                    f.write(desc_content)
            
            # Create reader.txt (narrator)
            if metadata.get("narrator"):
                reader_content = self._ensure_string(metadata["narrator"])
                reader_file = dest_dir / "reader.txt"
                with open(reader_file, "w", encoding="utf-8") as f:
                    f.write(reader_content)
            
            # Create series.txt if series information exists
            if metadata.get("series"):
                series_file = dest_dir / "series.txt"
                series_info = self._ensure_string(metadata["series"])
                if metadata.get("series_part"):
                    series_part = self._ensure_string(metadata["series_part"])
                    series_info += f" #{series_part}"
                with open(series_file, "w", encoding="utf-8") as f:
                    f.write(series_info)
            
            # Create OPF file (Open Packaging Format)
            logger.info("Creating OPF file...")
            opf_content = self.create_opf_content(metadata)
            if opf_content:
                logger.info("OPF content created successfully")
                # Get the .m4b file in the destination directory
                m4b_files = list(dest_dir.glob("*.m4b"))
                if m4b_files:
                    # Use the first .m4b file found (should be the processed one)
                    m4b_name = m4b_files[0].stem  # Get filename without extension
                else:
                    # Fallback: construct the filename from metadata to match the new naming convention
                    title = self._ensure_string(metadata.get("title", "Unknown Title"))
                    series = self._ensure_string(metadata.get("series", ""))
                    series_part = self._ensure_string(metadata.get("series_part", ""))
                    
                    # Clean series name - remove part number if present
                    clean_series = series
                    if " #" in series:
                        clean_series = series.split(" #")[0].strip()
                    
                    # Create filename that matches the new M4B naming convention
                    if series and series_part:
                        m4b_name = f"{title} ({clean_series} #{series_part})"
                    elif series:
                        m4b_name = f"{title} ({clean_series})"
                    else:
                        m4b_name = title
                
                opf_file = dest_dir / f"{m4b_name}.opf"
                with open(opf_file, "w", encoding="utf-8") as f:
                    f.write(opf_content)
                logger.info(f"OPF file created: {opf_file}")
            else:
                logger.warning("OPF content creation failed - no content generated")
            
        except Exception as e:
            logger.error(f"Error creating metadata files: {e}")
    
    def _build_subject_tags(self, metadata: Dict) -> str:
        """Build subject tags from metadata"""
        subjects = []
        
        # Add genre if available
        if metadata.get("genre"):
            subjects.append(f'<dc:subject>{self._ensure_string(metadata["genre"])}</dc:subject>')
        
        # Add categories if available
        if metadata.get("categories"):
            categories = metadata["categories"]
            if isinstance(categories, list):
                for category in categories:
                    subjects.append(f'<dc:subject>{self._ensure_string(category)}</dc:subject>')
            elif isinstance(categories, str):
                subjects.append(f'<dc:subject>{self._ensure_string(categories)}</dc:subject>')
        
        return '\n        '.join(subjects) if subjects else ""
    
    def _ensure_string(self, value) -> str:
        """Ensure a value is a string, handling bytes and other types safely"""
        if isinstance(value, str):
            return value
        elif isinstance(value, bytes):
            try:
                return value.decode("utf-8", errors="replace")
            except UnicodeDecodeError:
                return str(value)
        elif hasattr(value, 'decode'):  # Handle MP4FreeForm and similar objects
            try:
                return value.decode("utf-8", errors="replace")
            except:
                return str(value)
        elif hasattr(value, '__str__'):  # Handle any object with string representation
            return str(value)
        else:
            return str(value)

    def _clean_filename(self, filename: str) -> str:
        """Clean filename for filesystem compatibility"""
        import re
        
        if not filename:
            return "Unknown"
        
        # Remove or replace invalid characters
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove extra spaces and dots
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = cleaned.strip('.')
        
        # Limit length
        if len(cleaned) > 100:
            cleaned = cleaned[:100].strip()
        
        return cleaned
    
    def extract_asin_from_file(self, file_path: Path) -> Optional[str]:
        """Extract ASIN from existing tags in an M4B file"""
        try:
            audio = MP4(file_path)
            if not audio.tags:
                return None
            
            # Check for ASIN in various possible tag locations
            asin_candidates = [
                TagConstants.ASIN,
                TagConstants.AUDIBLE_ASIN,
                TagConstants.SIMPLE_ASIN,
                TagConstants.CDEK_ASIN,
            ]
            
            for tag_name in asin_candidates:
                if tag_name in audio.tags:
                    asin_value = audio.tags[tag_name]
                    if isinstance(asin_value, list) and len(asin_value) > 0:
                        # Handle MP4FreeForm objects
                        if hasattr(asin_value[0], "decode"):
                            asin = asin_value[0].decode("utf-8", errors="replace")
                        else:
                            asin = str(asin_value[0])
                        
                        # Clean up the ASIN value
                        asin = asin.strip()
                        if asin and len(asin) >= 10:  # ASINs are typically 10 characters
                            logger.info(f"Found ASIN in {file_path.name}: {asin}")
                            return asin
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting ASIN from {file_path}: {e}")
            return None
