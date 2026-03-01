#!/usr/bin/env python3
"""
Unit test to diagnose why AI opinion is not working
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
import json

def test_ai_opinion():
    """Test AI opinion functionality"""
    print("=" * 80)
    print("AI OPINION DIAGNOSTIC TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Use a known date range
    bearish_date = datetime(2025, 12, 11, 0, 0, 0, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
    
    print(f"Test Parameters:")
    print(f"  Analysis Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"  Target Date: {target_date.strftime('%Y-%m-%d')}")
    print()
    
    # Step 1: Get bearish analytics to find a stock
    print("-" * 80)
    print("STEP 1: Getting bearish analytics to find a stock")
    print("-" * 80)
    print()
    
    try:
        results, logs = tracker.get_bearish_analytics(
            bearish_date=bearish_date,
            target_date=target_date,
            industry="All Industries",
            filter_type="bearish",
            pct_threshold=-5.0
        )
        
        print(f"Found {len(results)} stocks")
        print()
        
        if len(results) == 0:
            print("❌ No stocks found! Cannot test AI opinion.")
            return False
        
        # Use the first stock
        test_stock = results[0]
        ticker = test_stock.get('ticker')
        company_name = test_stock.get('company_name', ticker)
        
        print(f"Testing AI opinion for: {ticker} ({company_name})")
        print()
        
        # Step 2: Prepare stock_data for AI opinion
        print("-" * 80)
        print("STEP 2: Preparing stock_data")
        print("-" * 80)
        print()
        
        # Check what fields are in test_stock
        print("Fields in test_stock:")
        for key in test_stock.keys():
            print(f"  - {key}: {type(test_stock[key]).__name__}")
        print()
        
        # Build stock_data from test_stock
        stock_data = {
            'company_name': company_name,
            'industry': test_stock.get('industry', 'Unknown'),
            'market_cap': test_stock.get('market_cap', 0),
            'bearish_date': test_stock.get('bearish_date'),
            'bearish_price': test_stock.get('bearish_price'),
            'prev_price': test_stock.get('prev_price'),
            'pct_drop': test_stock.get('pct_change', 0),
            'target_date': test_stock.get('target_date'),
            'target_price': test_stock.get('target_price'),
            'recovery_pct': test_stock.get('recovery_pct', 0),
            'price_history': test_stock.get('price_history'),
            'earnings_dividends': test_stock.get('earnings_dividends', {})
        }
        
        print("stock_data fields:")
        for key, value in stock_data.items():
            if key == 'price_history' and value:
                print(f"  - {key}: {type(value).__name__} (length: {len(value) if hasattr(value, '__len__') else 'N/A'})")
            elif key == 'earnings_dividends' and value:
                print(f"  - {key}: {type(value).__name__} (keys: {list(value.keys()) if isinstance(value, dict) else 'N/A'})")
            else:
                print(f"  - {key}: {value} (type: {type(value).__name__})")
        print()
        
        # Step 3: Test AI opinion function
        print("-" * 80)
        print("STEP 3: Calling get_ai_recovery_opinion")
        print("-" * 80)
        print()
        
        try:
            result = tracker.get_ai_recovery_opinion(ticker, company_name, stock_data)
            
            if result:
                print("✅ AI opinion returned successfully!")
                print()
                print("Result:")
                print(f"  Score: {result.get('score')}")
                print(f"  Explanation length: {len(result.get('explanation', ''))}")
                print()
                return True
            else:
                print("❌ AI opinion returned None")
                print()
                return False
                
        except Exception as e:
            print(f"❌ Error calling get_ai_recovery_opinion: {e}")
            import traceback
            traceback.print_exc()
            print()
            return False
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ai_opinion()
    sys.exit(0 if success else 1)

