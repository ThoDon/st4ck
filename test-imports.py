#!/usr/bin/env python3

import sys
import os

# Add tagger directory to Python path
tagger_path = '/app/tagger'
if tagger_path not in sys.path:
    sys.path.insert(0, tagger_path)

print(f"Python path: {sys.path}")
print(f"Tagger path exists: {os.path.exists(tagger_path)}")

try:
    from audible_client import AudibleAPIClient
    print("✅ audible_client import successful")
except ImportError as e:
    print(f"❌ audible_client import failed: {e}")

try:
    from m4b_tagger import M4BTagger
    print("✅ m4b_tagger import successful")
except ImportError as e:
    print(f"❌ m4b_tagger import failed: {e}")
