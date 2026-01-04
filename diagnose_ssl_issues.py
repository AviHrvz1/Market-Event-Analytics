#!/usr/bin/env python3
"""
Diagnostic script to identify SSL/connection issues:
- Tests VPN connectivity
- Tests device permissions  
- Tests Claude API server status
- Tests other APIs for comparison
"""

import requests
import ssl
import socket
import os
import sys
import platform

def test_basic_https():
    """Test basic HTTPS connectivity"""
    print("=" * 80)
    print("TEST 1: Basic HTTPS Connectivity")
    print("=" * 80)
    
    test_urls = [
        'https://www.google.com',
        'https://www.anthropic.com',
        'https://api.anthropic.com',
        'https://finance.yahoo.com',
        'https://api.prixe.io',
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=5, verify=True)
            print(f"✅ {url}: Status {response.status_code}")
        except requests.exceptions.SSLError as e:
            print(f"❌ {url}: SSL Error - {str(e)[:100]}")
        except requests.exceptions.ConnectionError as e:
            print(f"❌ {url}: Connection Error - {str(e)[:100]}")
        except Exception as e:
            print(f"⚠️  {url}: {type(e).__name__} - {str(e)[:100]}")
    print()

def test_claude_api():
    """Test Claude API specifically"""
    print("=" * 80)
    print("TEST 2: Claude API Connectivity")
    print("=" * 80)
    
    from main import LayoffTracker
    tracker = LayoffTracker()
    
    # Test actual API call
    print("Testing Claude API call...")
    try:
        payload = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 10,
            'messages': [{'role': 'user', 'content': 'Say "test"'}]
        }
        
        response = requests.post(
            tracker.claude_api_url,
            headers={
                'x-api-key': tracker.claude_api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json=payload,
            timeout=10,
            verify=True
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Claude API is working!")
        else:
            print(f"   Response: {response.text[:200]}")
    except requests.exceptions.SSLError as e:
        error_str = str(e)
        print(f"   ❌ SSL Error: {error_str[:150]}")
        if "Operation not permitted" in error_str:
            print("   💡 DEVICE PERMISSIONS issue (macOS TCC)")
        elif "certificate verify" in error_str.lower():
            print("   💡 SSL CERTIFICATE configuration issue")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection Error: {str(e)[:150]}")
        print("   💡 Could be VPN, firewall, or network issue")
    except Exception as e:
        print(f"   ⚠️  Error: {type(e).__name__} - {str(e)[:150]}")
    print()

def test_ssl_without_verify():
    """Test with SSL verification disabled"""
    print("=" * 80)
    print("TEST 3: SSL Verification Disabled (diagnostic)")
    print("=" * 80)
    
    from main import LayoffTracker
    tracker = LayoffTracker()
    
    try:
        payload = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 10,
            'messages': [{'role': 'user', 'content': 'Say "test"'}]
        }
        
        response = requests.post(
            tracker.claude_api_url,
            headers={
                'x-api-key': tracker.claude_api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json=payload,
            timeout=10,
            verify=False  # Disable SSL verification
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Works with verify=False")
            print("   💡 Confirms it's SSL certificate issue, NOT VPN/network")
        else:
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ⚠️  Still fails: {type(e).__name__} - {str(e)[:100]}")
        print("   💡 Suggests deeper network/permission issue")
    print()

def test_prixe_api():
    """Test Prixe.io API for comparison"""
    print("=" * 80)
    print("TEST 4: Prixe.io API (for comparison)")
    print("=" * 80)
    
    from config import PRIXE_API_KEY, PRIXE_BASE_URL, PRIXE_PRICE_ENDPOINT
    
    try:
        response = requests.post(
            f'{PRIXE_BASE_URL}{PRIXE_PRICE_ENDPOINT}',
            json={'ticker': 'AAPL', 'start_date': '2024-01-01', 'end_date': '2024-01-02', 'interval': '1d'},
            headers={'X-API-Key': PRIXE_API_KEY},
            timeout=10,
            verify=True
        )
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 401, 403]:
            print("   ✅ Prixe.io API connects (SSL works for this)")
            print("   💡 If Prixe works but Claude doesn't → Claude-specific issue")
        else:
            print(f"   Response: {response.text[:200]}")
    except requests.exceptions.SSLError as e:
        print(f"   ❌ Prixe.io SSL Error: {str(e)[:100]}")
        print("   💡 If Prixe also fails → System-wide SSL issue")
    except Exception as e:
        print(f"   ⚠️  Prixe.io Error: {type(e).__name__} - {str(e)[:100]}")
    print()

def test_dns_and_connectivity():
    """Test DNS and network connectivity"""
    print("=" * 80)
    print("TEST 5: DNS & Network Connectivity")
    print("=" * 80)
    
    # Test DNS resolution
    print("DNS Resolution:")
    try:
        ip = socket.gethostbyname('api.anthropic.com')
        print(f"   ✅ api.anthropic.com → {ip}")
    except Exception as e:
        print(f"   ❌ DNS failed: {e}")
        print("   💡 Could indicate VPN/DNS issue")
    
    # Test raw socket connection
    print("\nRaw Socket Connection (port 443):")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('api.anthropic.com', 443))
        sock.close()
        if result == 0:
            print("   ✅ Can connect to port 443")
            print("   💡 Network/VPN is NOT blocking")
        else:
            print(f"   ❌ Cannot connect (error: {result})")
            print("   💡 VPN or firewall may be blocking")
    except Exception as e:
        print(f"   ❌ Socket test failed: {e}")
    print()

def test_device_permissions():
    """Check macOS permissions"""
    print("=" * 80)
    print("TEST 6: Device Permissions (macOS)")
    print("=" * 80)
    
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    
    # Check certifi
    try:
        import certifi
        cert_path = certifi.where()
        with open(cert_path, 'r') as f:
            cert_count = len([l for l in f if 'BEGIN CERTIFICATE' in l])
        print(f"✅ Can read certifi bundle ({cert_count} certificates)")
    except PermissionError as e:
        print(f"❌ Permission denied: {e}")
        print("   💡 DEVICE PERMISSIONS issue (macOS TCC)")
        print("   💡 Fix: System Settings → Privacy & Security → Full Disk Access")
    except Exception as e:
        print(f"⚠️  Error: {e}")
    
    print(f"\nSSL_CERT_FILE: {os.environ.get('SSL_CERT_FILE', 'Not set')}")
    print(f"REQUESTS_CA_BUNDLE: {os.environ.get('REQUESTS_CA_BUNDLE', 'Not set')}")
    print()

if __name__ == "__main__":
    print()
    print("🔍 SSL/Connection Diagnostic Tool")
    print("=" * 80)
    print()
    
    test_basic_https()
    test_claude_api()
    test_ssl_without_verify()
    test_prixe_api()
    test_dns_and_connectivity()
    test_device_permissions()
    
    print("=" * 80)
    print("DIAGNOSIS GUIDE")
    print("=" * 80)
    print()
    print("Interpretation:")
    print()
    print("1. If ALL HTTPS sites fail with SSL errors:")
    print("   → Device permissions (macOS TCC) or SSL certificate config")
    print()
    print("2. If Claude fails but Prixe.io works:")
    print("   → Claude-specific issue (server, API key, or blocking)")
    print()
    print("3. If DNS/socket connection fails:")
    print("   → VPN or firewall blocking")
    print()
    print("4. If works with verify=False but not verify=True:")
    print("   → SSL certificate configuration issue")
    print()
    print("5. If 'Operation not permitted' in error:")
    print("   → macOS TCC permissions (check System Settings)")
    print()

