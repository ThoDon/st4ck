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
from typing import Optional, Union

logger = logging.getLogger(__name__)

# Import our Pydantic model
try:
    from .types import AudibleProduct  # type: ignore
    BookDataType = AudibleProduct
    logger.info("Successfully imported AudibleProduct from .types")
except Exception as e:
    logger.warning(f"Failed to import AudibleProduct from .types: {e}")
    try:
        from types import AudibleProduct  # type: ignore
        BookDataType = AudibleProduct
        logger.info("Successfully imported AudibleProduct from types")
    except Exception as e2:
        logger.warning(f"Failed to import AudibleProduct from types: {e2}")
        # If we can't import AudibleProduct, we'll use a different validation approach
        AudibleProduct = None  # type: ignore
        BookDataType = object  # Fallback type
from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm

from constants import TagConstants

class M4BTagger:
    """Class for tagging M4B files with metadata"""
    
    def __init__(self, library_dir: Path, covers_dir: Path):
        self.library_dir = library_dir
        self.covers_dir = covers_dir
        
        # Create directories if they don't exist
        self.library_dir.mkdir(exist_ok=True)
        self.covers_dir.mkdir(exist_ok=True)
    
    def tag_file(self, file_path: Path, book_data: BookDataType, cover_path: Optional[str] = None) -> bool:
        """Tag an M4B file with book metadata"""
        try:
            logger.info(f"Tagging file: {file_path}")
            logger.info(f"Book data: {book_data}")
            
            # Validate that book_data conforms to AudibleProduct model (if available)
            if AudibleProduct is not None:
                if not isinstance(book_data, AudibleProduct):
                    raise ValueError(f"book_data must be an instance of AudibleProduct, got {type(book_data)}")
                
                # Validate required fields
                if not book_data.asin:
                    raise ValueError("book_data.asin is required")
                if not book_data.title:
                    raise ValueError("book_data.title is required")
            else:
                logger.warning("AudibleProduct model not available - skipping validation")
                # Basic validation for required attributes
                if not hasattr(book_data, 'asin') or not book_data.asin:
                    raise ValueError("book_data.asin is required")
                if not hasattr(book_data, 'title') or not book_data.title:
                    raise ValueError("book_data.title is required")
            
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
    
    def _set_basic_tags(self, audio: MP4, book_data: BookDataType):
        """Set basic M4B tags"""
        # Title
        if book_data.title:
            audio[TagConstants.TITLE] = book_data.title
        
        # Album (same as title for audiobooks)
        if book_data.title:
            audio[TagConstants.ALBUM] = book_data.title
        
        # Artist (author) - get first author name
        if book_data.authors:
            author_name = book_data.authors[0].name
            audio[TagConstants.ARTIST] = author_name
            audio[TagConstants.ALBUM_ARTIST] = author_name
        
        # Year
        if book_data.publication_datetime:
            year = self._extract_year(book_data.publication_datetime)
            if year:
                audio[TagConstants.YEAR] = year
        elif book_data.release_date:
            year = self._extract_year(book_data.release_date)
            if year:
                audio[TagConstants.YEAR] = year
        
        # Genre
        audio[TagConstants.GENRE] = "Audiobook"
        
        # Comment - use best available description
        description = (book_data.publisher_summary or 
                      book_data.extended_product_description or 
                      book_data.merchandising_summary or "")
        if description:
            # Truncate description if too long
            if len(description) > 500:
                description = description[:500] + "..."
            audio[TagConstants.COMMENT] = description
    
    def _set_custom_tags(self, audio: MP4, book_data: BookDataType):
        """Set custom iTunes tags"""
        # ASIN
        if book_data.asin:
            logger.info(f"Processing ASIN: {book_data.asin} (type: {type(book_data.asin)})")
            asin_tag = MP4FreeForm(book_data.asin.encode("utf-8"))
            audio[TagConstants.ASIN] = [asin_tag]
            audio[TagConstants.AUDIBLE_ASIN] = [asin_tag]
        
        # Language
        if book_data.language:
            lang_tag = MP4FreeForm(book_data.language.encode("utf-8"))
            audio[TagConstants.LANGUAGE] = [lang_tag]
        
        # Format
        format_tag = MP4FreeForm(b"Audiobook")
        audio[TagConstants.FORMAT] = [format_tag]
        
        # Series information
        if book_data.series:
            series_title = book_data.series[0].title
            if series_title:
                series_tag = MP4FreeForm(series_title.encode("utf-8"))
                audio[TagConstants.SERIES] = [series_tag]
            
            series_part = book_data.series[0].sequence
            if series_part:
                series_part_tag = MP4FreeForm(series_part.encode("utf-8"))
                audio[TagConstants.SERIES_PART] = [series_part_tag]
        
        # Narrator
        if book_data.narrators:
            narrator_names = [narrator.name for narrator in book_data.narrators]
            narrator_str = ", ".join(narrator_names)
            logger.info(f"Processing narrator: {narrator_str} (type: {type(narrator_str)})")
            audio[TagConstants.NARRATOR_ALT] = narrator_str
        
        # Publisher
        if book_data.publisher_name:
            audio[TagConstants.PUBLISHER_ALT] = book_data.publisher_name
        
        # Duration
        if book_data.runtime_length_min:
            duration_str = str(book_data.runtime_length_min)
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
    
    def move_to_library(self, file_path: Path, book_data: BookDataType, cover_path: Optional[str] = None) -> Optional[Path]:
        """Move tagged file to library with organized structure"""
        try:
            # Validate that book_data conforms to AudibleProduct model (if available)
            if AudibleProduct is not None:
                if not isinstance(book_data, AudibleProduct):
                    raise ValueError(f"book_data must be an instance of AudibleProduct, got {type(book_data)}")
            else:
                logger.warning("AudibleProduct model not available - skipping validation")
                # Basic validation for required attributes
                if not hasattr(book_data, 'asin') or not book_data.asin:
                    raise ValueError("book_data.asin is required")
                if not hasattr(book_data, 'title') or not book_data.title:
                    raise ValueError("book_data.title is required")
            
            # Create organized directory structure
            author_name = book_data.authors[0].name if book_data.authors else "Unknown Author"
            author = self._clean_filename(author_name)
            title = self._clean_filename(book_data.title)
            series = book_data.series[0].title if book_data.series else ""
            series_part = book_data.series[0].sequence if book_data.series else ""
            
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
    
    def create_opf_content(self, metadata: BookDataType) -> str:
        """Create OPF (Open Packaging Format) content for metadata"""
        try:
            logger.info(f"Creating OPF content for metadata: {metadata.title}")
            title = metadata.title
            author_name = metadata.authors[0].name if metadata.authors else "Unknown Author"
            author = author_name
            description = (metadata.publisher_summary or 
                          metadata.extended_product_description or 
                          metadata.merchandising_summary or "")
            narrator_names = [narrator.name for narrator in metadata.narrators] if metadata.narrators else []
            narrator = ", ".join(narrator_names)
            series = metadata.series[0].title if metadata.series else ""
            series_part = metadata.series[0].sequence if metadata.series else ""
            asin = metadata.asin
            publisher = metadata.publisher_name or ""
            language = metadata.language or "en"
            release_date = metadata.release_date or metadata.publication_datetime or ""
            
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
        {self._build_subject_tags(metadata)}
        {date_info}
        <dc:identifier opf:scheme="ASIN">{identifier}</dc:identifier>
        {narrator_info}
        {series_info}
        <meta property="duration">{metadata.runtime_length_min or "0"}</meta>
        <meta property="rating">{metadata.rating.overall_distribution.average_rating if metadata.rating and metadata.rating.overall_distribution and metadata.rating.overall_distribution.average_rating else "0"}</meta>
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
    
    def create_additional_metadata_files(self, dest_dir: Path, metadata: BookDataType, cover_path: Optional[Path] = None) -> None:
        """Create additional metadata files compatible with Audiobookshelf"""
        try:
            logger.info(f"Creating additional metadata files in: {dest_dir}")
            # Create desc.txt (description)
            description = (metadata.publisher_summary or 
                          metadata.extended_product_description or 
                          metadata.merchandising_summary or "")
            if description:
                desc_file = dest_dir / "desc.txt"
                with open(desc_file, "w", encoding="utf-8") as f:
                    f.write(description)
            
            # Create reader.txt (narrator)
            if metadata.narrators:
                narrator_names = [narrator.name for narrator in metadata.narrators]
                reader_content = ", ".join(narrator_names)
                reader_file = dest_dir / "reader.txt"
                with open(reader_file, "w", encoding="utf-8") as f:
                    f.write(reader_content)
            
            # Create series.txt if series information exists
            if metadata.series:
                series_file = dest_dir / "series.txt"
                series_info = metadata.series[0].title
                if metadata.series[0].sequence:
                    series_info += f" #{metadata.series[0].sequence}"
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
                    title = metadata.title
                    series = metadata.series[0].title if metadata.series else ""
                    series_part = metadata.series[0].sequence if metadata.series else ""
                    
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
    
    def _build_subject_tags(self, metadata: BookDataType) -> str:
        """Build subject tags from metadata"""
        subjects = []

        # Add categories from category_ladders if available
        if metadata.category_ladders:
            for ladder_group in metadata.category_ladders:
                for ladder in ladder_group.ladder:
                    subjects.append(f'<dc:subject>{ladder.name}</dc:subject>')
        
        return '\n        '.join(subjects) if subjects else ""
    


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
