#!/usr/bin/env python3
"""
Test to diagnose .env file loading issues
"""

import os
import sys

print("=" * 80)
print("ENVIRONMENT VARIABLE LOADING TEST")
print("=" * 80)
print()

# Test 1: Check if .env file exists
print("TEST 1: Checking .env file")
print("-" * 80)
env_path = os.path.join(os.path.dirname(__file__), '.env')
print(f".env file path: {env_path}")
print(f".env file exists: {os.path.exists(env_path)}")
if os.path.exists(env_path):
    print(f".env file readable: {os.access(env_path, os.R_OK)}")
    try:
        with open(env_path, 'r') as f:
            content = f.read()
            has_claude_key = 'CLAUDE_API_KEY' in content
            print(f"Contains CLAUDE_API_KEY: {has_claude_key}")
            if has_claude_key:
                # Show first few chars (don't expose full key)
                lines = content.split('\n')
                for line in lines:
                    if 'CLAUDE_API_KEY' in line and not line.strip().startswith('#'):
                        key_preview = line.split('=')[1].strip()[:20] if '=' in line else 'N/A'
                        print(f"  Key preview: {key_preview}...")
                        break
    except Exception as e:
        print(f"Error reading .env: {e}")
print()

# Test 2: Try loading with dotenv
print("TEST 2: Loading .env with dotenv")
print("-" * 80)
try:
    from dotenv import load_dotenv
    result = load_dotenv()
    print(f"load_dotenv() returned: {result}")
except PermissionError as e:
    print(f"❌ PermissionError loading .env: {e}")
except Exception as e:
    print(f"❌ Error loading .env: {e}")
print()

# Test 3: Check environment variable after loading
print("TEST 3: Checking CLAUDE_API_KEY in environment")
print("-" * 80)
claude_key = os.getenv('CLAUDE_API_KEY', '')
if claude_key:
    print(f"✅ CLAUDE_API_KEY found: {claude_key[:10]}...{claude_key[-5:]}")
else:
    print("❌ CLAUDE_API_KEY NOT FOUND in environment")
print()

# Test 4: Import config and check
print("TEST 4: Importing config.py")
print("-" * 80)
try:
    import config
    print("✅ config.py imported successfully")
    # Check if config loaded dotenv
    claude_key_after_config = os.getenv('CLAUDE_API_KEY', '')
    if claude_key_after_config:
        print(f"✅ CLAUDE_API_KEY found after config import: {claude_key_after_config[:10]}...{claude_key_after_config[-5:]}")
    else:
        print("❌ CLAUDE_API_KEY still not found after config import")
except Exception as e:
    print(f"❌ Error importing config: {e}")
    import traceback
    traceback.print_exc()
print()

# Test 5: Check LayoffTracker initialization
print("TEST 5: Initializing LayoffTracker")
print("-" * 80)
try:
    from main import LayoffTracker
    tracker = LayoffTracker()
    if tracker.claude_api_key:
        print(f"✅ LayoffTracker has API key: {tracker.claude_api_key[:10]}...{tracker.claude_api_key[-5:]}")
    else:
        print("❌ LayoffTracker does NOT have API key")
except Exception as e:
    print(f"❌ Error initializing LayoffTracker: {e}")
    import traceback
    traceback.print_exc()
print()

print("=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)

