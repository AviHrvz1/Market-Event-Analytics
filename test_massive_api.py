#!/usr/bin/env python3
"""
Test Massive API (Polygon data source) REST endpoints
Based on documentation: https://massive.com/docs/rest/quickstart
"""
import requests
import json
from datetime import datetime, timedelta

def test_massive_api():
    """Test the Massive REST API with Polygon data source"""
    
    api_key = "HV_uayoWEzdv3FpeWLrgmHUFPEtGIgTX"
    # Try both Massive and Polygon API base URLs (Massive acquired Polygon)
    base_urls_to_try = [
        "https://api.massive.com",
        "https://api.polygon.io",  # Polygon API (now Massive)
        "https://api.polygon.io/v2",  # Polygon v2 API
    ]
    
    print("=" * 80)
    print("Testing Massive/Polygon REST API")
    print("=" * 80)
    print(f"\nAPI Key: {api_key[:10]}... (hidden)")
    print(f"\nDocumentation: https://massive.com/docs/rest/quickstart")
    print(f"Note: Massive acquired Polygon, testing both API structures")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Test 1: Try Polygon API structure (since Massive acquired Polygon)
    print("\n" + "=" * 80)
    print("TEST 1: Polygon API Endpoints (Massive uses Polygon data)")
    print("=" * 80)
    
    # Polygon API endpoints to test
    polygon_endpoints = [
        # Aggregates (bars) endpoint
        {
            'url': f"https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}",
            'params': {'apiKey': api_key},
            'name': 'Aggregates (Bars)'
        },
        # Ticker details
        {
            'url': f"https://api.polygon.io/v3/reference/tickers/AAPL",
            'params': {'apiKey': api_key},
            'name': 'Ticker Details'
        },
        # Previous close
        {
            'url': f"https://api.polygon.io/v2/aggs/ticker/AAPL/prev",
            'params': {'apiKey': api_key},
            'name': 'Previous Close'
        },
    ]
    
    for endpoint in polygon_endpoints:
        print(f"\nTesting: {endpoint['name']}")
        print(f"URL: {endpoint['url']}")
        
        try:
            response = requests.get(endpoint['url'], params=endpoint['params'], timeout=15)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ SUCCESS!")
                try:
                    data = response.json()
                    print(f"  Response type: {type(data)}")
                    if isinstance(data, dict):
                        print(f"  Top-level keys: {list(data.keys())[:10]}")
                        # Show sample of response
                        print(f"  Sample response: {json.dumps(data, indent=2)[:500]}")
                except:
                    print(f"  Response: {response.text[:300]}")
                break  # Found working endpoint
            elif response.status_code == 401:
                print(f"  ❌ Unauthorized - API key may be invalid")
                print(f"  Response: {response.text[:200]}")
            elif response.status_code == 403:
                print(f"  ❌ Forbidden - API key may not have access")
                print(f"  Response: {response.text[:200]}")
            else:
                print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test 2: Try Massive API structure
    print("\n" + "=" * 80)
    print("TEST 2: Massive API Endpoints")
    print("=" * 80)
    
    massive_endpoints = [
        f"https://api.massive.com/dividends",
        f"https://api.massive.com/v1/dividends",
        f"https://api.massive.com/rest/dividends",
    ]
    
    params = {
        'apiKey': api_key,
        'startDate': start_date.strftime('%Y-%m-%d'),
        'endDate': end_date.strftime('%Y-%m-%d'),
        'limit': 10
    }
    
    for endpoint_url in massive_endpoints:
        print(f"\nTrying: {endpoint_url}")
        try:
            response = requests.get(endpoint_url, params=params, timeout=10)
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ SUCCESS!")
                try:
                    data = response.json()
                    print(f"  Response: {json.dumps(data, indent=2)[:500]}")
                except:
                    print(f"  Response: {response.text[:300]}")
                break
            elif response.status_code != 404:
                print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test 3: Try Polygon Dividends endpoint
    print("\n" + "=" * 80)
    print("TEST 3: Polygon Dividends Endpoint")
    print("=" * 80)
    
    ticker = "AAPL"
    dividends_url = f"https://api.polygon.io/v3/reference/dividends"
    params_dividends = {
        'apiKey': api_key,
        'ticker': ticker,
        'limit': 10
    }
    
    print(f"\nURL: {dividends_url}")
    print(f"Parameters:")
    for key, value in params_dividends.items():
        if key != 'apiKey':
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {'*' * 20} (hidden)")
    
    try:
        response = requests.get(dividends_url, params=params_dividends, timeout=15)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\n✅ SUCCESS: Dividends endpoint returned data")
                
                if isinstance(data, dict):
                    results = data.get('results', [])
                    status = data.get('status', 'unknown')
                    count = data.get('count', 0)
                    request_id = data.get('request_id', 'N/A')
                    
                    print(f"  status: {status}")
                    print(f"  count: {count}")
                    print(f"  request_id: {request_id}")
                    print(f"  results: {len(results)} items")
                    
                    if len(results) > 0:
                        print(f"\n✅ Sample dividend record:")
                        print(json.dumps(results[0], indent=2))
                else:
                    print(f"Response: {str(data)[:200]}")
            except json.JSONDecodeError as e:
                print(f"\n❌ Failed to parse JSON: {e}")
                print(f"Response text: {response.text[:500]}")
        else:
            print(f"\n⚠️  HTTP {response.status_code}")
            print(f"Response: {response.text[:300]}")
            
    except Exception as e:
        print(f"\n⚠️  Error testing dividends endpoint: {e}")
    
    print("\n" + "=" * 80)
    print("Test completed")
    print("=" * 80)
    print("\n💡 Note: Massive API uses Polygon as data source")
    print("   Documentation: https://massive.com/docs/rest/quickstart")

if __name__ == '__main__':
    test_massive_api()
