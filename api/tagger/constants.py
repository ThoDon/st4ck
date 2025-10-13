#!/usr/bin/env python3
"""
Constants for M4B tag names - Compliant with MP3Tag's Audible API
Based on auto-m4b-audible-tagger TagConstants
"""

class TagConstants:
    """Constants for M4B tag names - Compliant with MP3Tag's Audible API.inc"""
    
    # Basic tags
    TITLE = "\\xa9nam"
    ALBUM = "\\xa9alb"
    YEAR = "\\xa9day"
    ARTIST = "\\xa9ART"
    ALBUM_ARTIST = "aART"
    COMPOSER = "\\xa9wrt"
    COMMENT = "\\xa9cmt"
    COPYRIGHT = "\\xa9cpy"
    GENRE = "\\xa9gen"
    
    # iTunes custom tags
    ASIN = "----:com.apple.iTunes:ASIN"
    LANGUAGE = "----:com.apple.iTunes:LANGUAGE"
    FORMAT = "----:com.apple.iTunes:FORMAT"
    SUBTITLE = "----:com.apple.iTunes:SUBTITLE"
    RELEASETIME = "----:com.apple.iTunes:RELEASETIME"
    ALBUMARTISTS = "----:com.apple.iTunes:ALBUMARTISTS"
    SERIES = "----:com.apple.iTunes:SERIES"
    SERIES_PART = "----:com.apple.iTunes:SERIES-PART"
    RATING = "----:com.apple.iTunes:RATING"
    RATING_WMP = "----:com.apple.iTunes:RATING WMP"
    EXPLICIT = "----:com.apple.iTunes:EXPLICIT"
    WWWAUDIOFILE = "----:com.apple.iTunes:WWWAUDIOFILE"
    AUDIBLE_ASIN = "----:com.apple.iTunes:AUDIBLE_ASIN"
    
    # Alternative tags for compatibility
    ALBUM_SORT = "soal"
    SHOW_MOVEMENT_ALT = "shwm"
    GAPLESS_ALT = "pgap"
    STICK = "stik"
    SIMPLE_ASIN = "asin"
    CDEK_ASIN = "CDEK"
    DESC_ALT = "desc"
    DESC_ALT2 = "\\xa9des"
    PUBLISHER_ALT = "\\xa9pub"
    NARRATOR_ALT = "\\xa9nrt"
    SERIES_ALT = "\\xa9mvn"
    GROUP = "\\xa9grp"
