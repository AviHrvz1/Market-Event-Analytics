#!/usr/bin/env python3
"""
Simple test to verify Claude API works the same way the app calls it
"""

import requests
from main import LayoffTracker

def test_claude_like_app():
    """Test Claude API call exactly like the app does"""
    print("Testing Claude API (same way as app)...")
    print()
    
    tracker = LayoffTracker()
    
    try:
        headers = {
            'x-api-key': tracker.claude_api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        
        payload = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 10,
            'messages': [
                {
                    'role': 'user',
                    'content': 'Say "test"'
                }
            ]
        }
        
        print(f"URL: {tracker.claude_api_url}")
        print(f"API Key: {tracker.claude_api_key[:20]}...")
        print()
        print("Making request...")
        
        response = requests.post(
            tracker.claude_api_url,
            headers=headers,
            json=payload,
            timeout=30,
            verify=False
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('content', [])
            if content:
                text = content[0].get('text', '').strip()
                print(f"✅ SUCCESS! Response: {text}")
                return True
            else:
                print(f"⚠️  Response 200 but no content: {data}")
                return False
        else:
            print(f"❌ Error {response.status_code}: {response.text[:200]}")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL Error: {str(e)[:200]}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: {str(e)[:200]}")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)[:200]}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("Claude API Test (App Method)")
    print("=" * 80)
    print()
    
    success = test_claude_like_app()
    
    print()
    print("=" * 80)
    if success:
        print("✅ Claude API works! The issue is likely with the diagnostic script's")
        print("   execution environment (sandbox restrictions), not the actual app.")
    else:
        print("❌ Claude API failed. Check the error above.")
    print("=" * 80)

