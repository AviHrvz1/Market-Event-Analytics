#!/usr/bin/env python3
"""
Test Financial Modeling Prep API company screener endpoint
"""
import requests
import json
from datetime import datetime

def test_financialmodelingprep_screener():
    """Test the Financial Modeling Prep company screener API"""
    
    api_key = "0oeuez6rdvl3dDBS7xHvRCAQI6YJ3FVI"
    
    # Build URL with parameters
    base_url = "https://financialmodelingprep.com/stable/company-screener"
    params = {
        'marketCapMoreThan': 50000000000,  # $50B+
        'priceMoreThan': 40,
        'volumeMoreThan': 2000000,
        'betaLessThan': 2,
        'country': 'US',
        'limit': 1000,
        'apikey': api_key
    }
    
    print("=" * 80)
    print("Testing Financial Modeling Prep Company Screener API")
    print("=" * 80)
    print(f"\nURL: {base_url}")
    print(f"Parameters:")
    for key, value in params.items():
        if key != 'apikey':
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {'*' * 20} (hidden)")
    
    print(f"\nFull URL: {base_url}?marketCapMoreThan={params['marketCapMoreThan']}&priceMoreThan={params['priceMoreThan']}&volumeMoreThan={params['volumeMoreThan']}&betaLessThan={params['betaLessThan']}&country={params['country']}&limit={params['limit']}&apikey={api_key[:10]}...")
    
    try:
        print("\n" + "-" * 80)
        print("Making API request...")
        print("-" * 80)
        
        response = requests.get(base_url, params=params, timeout=30)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                print(f"\n✅ SUCCESS: API returned data")
                print(f"Response Type: {type(data)}")
                
                if isinstance(data, list):
                    print(f"Number of companies returned: {len(data)}")
                    
                    if len(data) > 0:
                        print(f"\nFirst company sample:")
                        first_company = data[0]
                        print(json.dumps(first_company, indent=2))
                        
                        # Check for expected fields
                        expected_fields = ['symbol', 'companyName', 'marketCap', 'price', 'volume', 'beta']
                        print(f"\nFields in response:")
                        if isinstance(first_company, dict):
                            for field in first_company.keys():
                                print(f"  - {field}")
                            
                            missing_fields = [f for f in expected_fields if f not in first_company]
                            if missing_fields:
                                print(f"\n⚠️  Missing expected fields: {missing_fields}")
                            else:
                                print(f"\n✅ All expected fields present")
                        
                        # Summary statistics
                        if len(data) > 0 and isinstance(data[0], dict):
                            print(f"\nSummary Statistics:")
                            if 'marketCap' in data[0]:
                                market_caps = [c.get('marketCap', 0) for c in data if isinstance(c.get('marketCap'), (int, float))]
                                if market_caps:
                                    print(f"  Market Cap Range: ${min(market_caps):,.0f} - ${max(market_caps):,.0f}")
                            
                            if 'price' in data[0]:
                                prices = [c.get('price', 0) for c in data if isinstance(c.get('price'), (int, float))]
                                if prices:
                                    print(f"  Price Range: ${min(prices):.2f} - ${max(prices):.2f}")
                            
                            if 'volume' in data[0]:
                                volumes = [c.get('volume', 0) for c in data if isinstance(c.get('volume'), (int, float))]
                                if volumes:
                                    print(f"  Volume Range: {min(volumes):,} - {max(volumes):,}")
                            
                            if 'beta' in data[0]:
                                betas = [c.get('beta', 0) for c in data if isinstance(c.get('beta'), (int, float))]
                                if betas:
                                    print(f"  Beta Range: {min(betas):.2f} - {max(betas):.2f}")
                    else:
                        print("⚠️  API returned empty list (no companies match criteria)")
                elif isinstance(data, dict):
                    print(f"\nResponse is a dictionary:")
                    print(json.dumps(data, indent=2))
                    
                    # Check for error messages
                    if 'Error Message' in data or 'error' in data:
                        print(f"\n❌ API returned error: {data.get('Error Message', data.get('error', 'Unknown error'))}")
                else:
                    print(f"\n⚠️  Unexpected response type: {type(data)}")
                    print(f"Response: {str(data)[:500]}")
                    
            except json.JSONDecodeError as e:
                print(f"\n❌ Failed to parse JSON response")
                print(f"Error: {e}")
                print(f"Response text (first 500 chars): {response.text[:500]}")
        elif response.status_code == 402:
            print(f"\n⚠️  HTTP 402 - Payment Required")
            print(f"This endpoint requires a paid subscription plan.")
            print(f"Response text: {response.text[:500]}")
            
            # Try to parse as JSON for error details
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                pass
            
            print(f"\n💡 Note: The API key is valid, but the company-screener endpoint")
            print(f"   requires a premium subscription. The API connection works correctly.")
        else:
            print(f"\n❌ HTTP Error {response.status_code}")
            print(f"Response text: {response.text[:500]}")
            
            # Try to parse as JSON for error details
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                pass
                
    except requests.exceptions.Timeout:
        print(f"\n❌ Request timed out after 30 seconds")
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Connection error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Test completed")
    print("=" * 80)

if __name__ == '__main__':
    test_financialmodelingprep_screener()
