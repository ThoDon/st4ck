#!/usr/bin/env python3
"""
Backup management for conversion retry mechanism
"""

import os
import shutil
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from config import DB_PATH, BACKUP_PATH, CONVERSION_BACKUP_RETENTION

logger = logging.getLogger(__name__)

class BackupManager:
    """Manages backup creation, restoration, and cleanup for conversion retries"""
    
    def __init__(self):
        self.backup_path = Path(BACKUP_PATH)
        self.backup_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"BackupManager initialized with backup path: {self.backup_path}")
    
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn
    
    def create_backup(self, book_name: str, source_path: str) -> Optional[str]:
        """
        Create backup of source files before conversion
        
        Args:
            book_name: Name of the book for backup directory
            source_path: Path to source files to backup
            
        Returns:
            Path to backup directory or None if failed
        """
        try:
            source = Path(source_path)
            if not source.exists():
                logger.error(f"Source path does not exist: {source_path}")
                return None
            
            # Create backup directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.backup_path / f"{book_name}_{timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all files and directories
            if source.is_dir():
                shutil.copytree(source, backup_dir, dirs_exist_ok=True)
            else:
                shutil.copy2(source, backup_dir)
            
            logger.info(f"Created backup: {backup_dir}")
            return str(backup_dir)
            
        except Exception as e:
            logger.error(f"Failed to create backup for {book_name}: {e}")
            return None
    
    def restore_from_backup(self, backup_path: str, target_path: str) -> bool:
        """
        Restore files from backup to target location
        
        Args:
            backup_path: Path to backup directory
            target_path: Path to restore files to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backup = Path(backup_path)
            target = Path(target_path)
            
            if not backup.exists():
                logger.error(f"Backup path does not exist: {backup_path}")
                return False
            
            # Ensure target directory exists
            target.mkdir(parents=True, exist_ok=True)
            
            # Copy files from backup to target
            if backup.is_dir():
                # Clear target directory first
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(backup, target)
            else:
                shutil.copy2(backup, target)
            
            logger.info(f"Restored from backup: {backup_path} -> {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore from backup {backup_path}: {e}")
            return False
    
    def track_backup_usage(self, book_name: str, backup_path: str, rss_item_id: int) -> bool:
        """
        Track backup usage in database
        
        Args:
            book_name: Name of the book
            backup_path: Path to backup directory
            rss_item_id: RSS item ID for tracking
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Update RSS item with backup path
            cursor.execute('''
                UPDATE rss_items 
                SET conversion_backup_path = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (backup_path, rss_item_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to track backup usage: {e}")
            return False
    
    def increment_backup_usage(self, book_name: str) -> int:
        """
        Increment backup usage count for successful conversions
        
        Args:
            book_name: Name of the book
            
        Returns:
            Current usage count
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get current conversion attempts
            cursor.execute('SELECT conversion_attempts FROM rss_items WHERE title = ?', (book_name,))
            result = cursor.fetchone()
            
            if result:
                current_attempts = result[0] or 0
                new_attempts = current_attempts + 1
                
                # Update attempts count
                cursor.execute('''
                    UPDATE rss_items 
                    SET conversion_attempts = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE title = ?
                ''', (new_attempts, book_name))
                
                conn.commit()
                conn.close()
                return new_attempts
            
            conn.close()
            return 0
            
        except Exception as e:
            logger.error(f"Failed to increment backup usage: {e}")
            return 0
    
    def cleanup_old_backups(self, book_name: str) -> bool:
        """
        Clean up old backups based on retention policy
        
        Args:
            book_name: Name of the book
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get current conversion attempts
            cursor.execute('SELECT conversion_attempts FROM rss_items WHERE title = ?', (book_name,))
            result = cursor.fetchone()
            
            if result and result[0] and result[0] >= CONVERSION_BACKUP_RETENTION:
                # Get backup path
                cursor.execute('SELECT conversion_backup_path FROM rss_items WHERE title = ?', (book_name,))
                backup_result = cursor.fetchone()
                
                if backup_result and backup_result[0]:
                    backup_path = Path(backup_result[0])
                    if backup_path.exists():
                        shutil.rmtree(backup_path)
                        logger.info(f"Cleaned up old backup: {backup_path}")
                    
                    # Clear backup path from database
                    cursor.execute('''
                        UPDATE rss_items 
                        SET conversion_backup_path = NULL, updated_at = CURRENT_TIMESTAMP
                        WHERE title = ?
                    ''', (book_name,))
                    
                    conn.commit()
                    conn.close()
                    return True
            
            conn.close()
            return False
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return False
    
    def cleanup_backup_on_tagging_success(self, book_name: str) -> bool:
        """
        Clean up backup and original files after successful tagging (allows for quality validation)
        
        Args:
            book_name: Name of the book
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get backup path
            cursor.execute('SELECT conversion_backup_path FROM rss_items WHERE title = ?', (book_name,))
            result = cursor.fetchone()
            
            logger.info(f"Looking for backup cleanup for book: {book_name}")
            if result:
                logger.info(f"Found backup path in database: {result[0]}")
            else:
                logger.info(f"No backup path found in database for: {book_name}")
            
            cleanup_success = True
            
            # Clean up backup directory
            if result and result[0]:
                backup_path = Path(result[0])
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                    logger.info(f"Cleaned up backup after successful tagging: {backup_path}")
                else:
                    logger.warning(f"Backup path from database does not exist: {backup_path}")
                
                # Clear backup path from database
                cursor.execute('''
                    UPDATE rss_items 
                    SET conversion_backup_path = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE title = ?
                ''', (book_name,))
            else:
                logger.info(f"No backup path found in database for {book_name}, trying pattern matching...")
                # Debug: List all backup directories
                logger.info(f"Available backup directories:")
                for backup_dir in self.backup_path.iterdir():
                    if backup_dir.is_dir():
                        logger.info(f"  - {backup_dir.name}")
                
                # Fallback: find backup directory by pattern matching
                backup_found = self._cleanup_backup_by_pattern(book_name)
                if not backup_found:
                    logger.info(f"No backup found to clean up for {book_name}")
            
            # Note: toMerge files are cleaned up by folder_m4b_builder.sh after successful conversion
            
            # Clean up converted file from converted directory
            converted_file = Path(f"/converted/{book_name}.m4b")
            if converted_file.exists():
                converted_file.unlink()
                logger.info(f"Cleaned up converted file: {converted_file}")
            else:
                logger.info(f"No converted file found for {book_name}")
            
            conn.commit()
            conn.close()
            return cleanup_success
            
        except Exception as e:
            logger.error(f"Failed to cleanup files on tagging success: {e}")
            return False
    
    def _cleanup_backup_by_pattern(self, book_name: str) -> bool:
        """
        Find and clean up backup directory by pattern matching (fallback method)
        
        Args:
            book_name: Name of the book
            
        Returns:
            True if backup was found and cleaned up, False otherwise
        """
        try:
            # Look for backup directories that start with the book name
            for backup_folder in self.backup_path.iterdir():
                if backup_folder.is_dir() and backup_folder.name.startswith(f"{book_name}_"):
                    logger.info(f"Found backup directory by pattern: {backup_folder}")
                    shutil.rmtree(backup_folder)
                    logger.info(f"Cleaned up backup directory by pattern: {backup_folder}")
                    return True
            
            logger.info(f"No backup directory found matching pattern: {book_name}_*")
            return False
            
        except Exception as e:
            logger.error(f"Failed to cleanup backup by pattern: {e}")
            return False
    
    def list_backups(self) -> List[Dict]:
        """
        List all backups with metadata
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        try:
            if not self.backup_path.exists():
                return backups
            
            for backup_dir in self.backup_path.iterdir():
                if backup_dir.is_dir():
                    # Get directory size
                    total_size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
                    
                    backups.append({
                        'name': backup_dir.name,
                        'path': str(backup_dir),
                        'size': total_size,
                        'created': datetime.fromtimestamp(backup_dir.stat().st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(backup_dir.stat().st_mtime).isoformat()
                    })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created'], reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    def delete_backup(self, backup_path: str) -> bool:
        """
        Delete a specific backup
        
        Args:
            backup_path: Path to backup to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backup = Path(backup_path)
            if backup.exists():
                shutil.rmtree(backup)
                logger.info(f"Deleted backup: {backup_path}")
                return True
            else:
                logger.warning(f"Backup does not exist: {backup_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_path}: {e}")
            return False
