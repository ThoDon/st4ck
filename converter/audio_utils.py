#!/usr/bin/env python3
"""
Audio utilities for duration calculation and validation
"""

import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

class AudioUtils:
    """Utility class for audio file operations"""
    
    @staticmethod
    def get_audio_duration(file_path: str) -> Optional[float]:
        """
        Get duration of an audio file in seconds using ffprobe
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Duration in seconds, or None if failed
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                logger.debug(f"Duration of {file_path}: {duration:.2f} seconds")
                return duration
            else:
                logger.warning(f"Failed to get duration for {file_path}: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting duration for {file_path}: {e}")
            return None
    
    @staticmethod
    def calculate_total_duration(mp3_files: List[str]) -> Optional[float]:
        """
        Calculate total duration of multiple MP3 files
        
        Args:
            mp3_files: List of MP3 file paths
            
        Returns:
            Total duration in seconds, or None if failed
        """
        total_duration = 0.0
        successful_files = 0
        
        for mp3_file in mp3_files:
            duration = AudioUtils.get_audio_duration(mp3_file)
            if duration is not None:
                total_duration += duration
                successful_files += 1
            else:
                logger.warning(f"Could not get duration for {mp3_file}")
        
        if successful_files == 0:
            logger.error("Could not get duration for any MP3 files")
            return None
        
        if successful_files < len(mp3_files):
            logger.warning(f"Could only get duration for {successful_files}/{len(mp3_files)} files")
        
        logger.info(f"Total duration: {total_duration:.2f} seconds ({total_duration/3600:.2f} hours)")
        return total_duration
    
    @staticmethod
    def validate_conversion_duration(source_duration: float, converted_duration: float, 
                                   tolerance_percent: float = 5.0) -> Tuple[bool, str]:
        """
        Validate that converted file duration is within tolerance of source duration
        
        Args:
            source_duration: Source total duration in seconds
            converted_duration: Converted file duration in seconds
            tolerance_percent: Tolerance percentage (default 5%)
            
        Returns:
            Tuple of (is_valid, message)
        """
        if source_duration <= 0:
            return False, "Invalid source duration"
        
        if converted_duration <= 0:
            return False, "Invalid converted duration"
        
        # Calculate tolerance in seconds
        tolerance_seconds = source_duration * (tolerance_percent / 100.0)
        
        # Check if converted duration is within tolerance
        duration_diff = abs(source_duration - converted_duration)
        
        if duration_diff <= tolerance_seconds:
            return True, f"Duration validation passed (diff: {duration_diff:.2f}s, tolerance: {tolerance_seconds:.2f}s)"
        else:
            return False, f"Duration validation failed (diff: {duration_diff:.2f}s, tolerance: {tolerance_seconds:.2f}s)"
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format duration in seconds to human readable format
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
