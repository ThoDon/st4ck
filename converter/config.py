#!/usr/bin/env python3
"""
Configuration constants for the converter service
"""

import os

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Database Configuration
DB_PATH = os.getenv("DB_PATH", "/app/db/rss.sqlite")

# Conversion Settings
CONVERSION_MAX_RETRIES = int(os.getenv("CONVERSION_MAX_RETRIES", "3"))
CONVERSION_BACKUP_RETENTION = int(os.getenv("CONVERSION_BACKUP_RETENTION", "3"))
CONVERSION_TIMEOUT = int(os.getenv("CONVERSION_TIMEOUT", "7200"))  # 2 hours

# m4b-tool Settings
M4B_TOOL_BITRATE = os.getenv("M4B_TOOL_BITRATE", "64k")
M4B_TOOL_CODEC = os.getenv("M4B_TOOL_CODEC", "aac")

# Paths
INPUT_PATH = "/input"  # /toMerge
OUTPUT_PATH = "/output"  # /converted
BACKUP_PATH = "/backups"  # /conversion-backups

# Redis Channels
CHANNEL_DOWNLOAD_COMPLETE = "audiobook:download_complete"
CHANNEL_CONVERSION_COMPLETE = "audiobook:conversion_complete"
CHANNEL_CONVERSION_FAILED = "audiobook:conversion_failed"
CHANNEL_RETRY_CONVERSION = "audiobook:retry_conversion"

# API Configuration
API_URL = os.getenv("API_URL", "http://api:8000")
