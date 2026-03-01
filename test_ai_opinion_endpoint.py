#!/usr/bin/env python3
"""
Test the AI opinion API endpoint to diagnose 500 error
"""

import sys
import json
from datetime import datetime, timezone
from flask import Flask
from app import app

def test_ai_opinion_endpoint():
    """Test the /api/ai-opinion endpoint"""
    print("=" * 80)
    print("TESTING /api/ai-opinion ENDPOINT")
    print("=" * 80)
    print()
    
    # Create a test client
    with app.test_client() as client:
        # Prepare test data (similar to what frontend sends)
        test_data = {
            'ticker': 'AAPL',
            'bearish_date': '2025-12-11',
            'target_date': '2025-12-31',
            'score_only': False,
            'stock_data': {
                'company_name': 'Apple Inc.',
                'industry': 'Technology',
                'market_cap': 3000000000000,
                'bearish_date': '2025-12-11',
                'bearish_price': 150.0,
                'prev_price': 160.0,
                'pct_drop': -6.25,
                'target_date': '2025-12-31',
                'target_price': 155.0,
                'recovery_pct': 3.33,
                'price_history': [
                    {'date': '2025-12-11', 'price': 150.0},
                    {'date': '2025-12-12', 'price': 151.0},
                    {'date': '2025-12-31', 'price': 155.0}
                ],
                'earnings_dividends': {
                    'events_during': [],
                    'has_events_during': False
                }
            }
        }
        
        print("Sending POST request to /api/ai-opinion")
        print(f"Ticker: {test_data['ticker']}")
        print(f"Bearish Date: {test_data['bearish_date']}")
        print(f"Target Date: {test_data['target_date']}")
        print()
        
        try:
            response = client.post(
                '/api/ai-opinion',
                json=test_data,
                content_type='application/json'
            )
            
            print(f"Response Status: {response.status_code}")
            print()
            
            if response.status_code == 200:
                data = json.loads(response.data)
                print("✅ SUCCESS!")
                print(f"Score: {data.get('score')}")
                print(f"Explanation length: {len(data.get('explanation', ''))}")
                return True
            else:
                print(f"❌ ERROR: Status {response.status_code}")
                print()
                try:
                    error_data = json.loads(response.data)
                    print("Error response:")
                    print(json.dumps(error_data, indent=2))
                except:
                    print("Response body:")
                    print(response.data.decode('utf-8'))
                return False
                
        except Exception as e:
            print(f"❌ Exception during request: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    # Check if API key is configured
    from config import CLAUDE_API_KEY
    if not CLAUDE_API_KEY:
        print("⚠️  WARNING: Claude API key is still using placeholder value")
        print("   Update config.py with your actual API key")
        print()
    
    success = test_ai_opinion_endpoint()
    sys.exit(0 if success else 1)

