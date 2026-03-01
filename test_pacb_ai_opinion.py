#!/usr/bin/env python3
"""
Unit test to check AI opinion for PACB on November 12, 2025
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_pacb_ai_opinion():
    """Test AI opinion for PACB on November 12, 2025"""
    print("=" * 80)
    print("TESTING AI OPINION FOR PACB (November 12, 2025)")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test parameters
    ticker = "PACB"
    company_name = "Pacific Biosciences of California"
    bearish_date = datetime(2025, 11, 12, 0, 0, 0, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
    
    print(f"Test Parameters:")
    print(f"  Ticker: {ticker}")
    print(f"  Company: {company_name}")
    print(f"  Bearish Date: {bearish_date.strftime('%Y-%m-%d')} (November 12, 2025)")
    print(f"  Target Date: {target_date.strftime('%Y-%m-%d')} (December 31, 2025)")
    print()
    
    # Step 1: Fetch actual stock data
    print("-" * 80)
    print("STEP 1: Fetching stock data")
    print("-" * 80)
    print()
    
    try:
        # Fetch price history (120 days before bearish date to target date)
        graph_start_date = bearish_date - timedelta(days=120)
        price_history_end_date = target_date + timedelta(days=1)
        price_history = tracker.get_stock_price_history(ticker, graph_start_date, price_history_end_date)
        
        if not price_history:
            print(f"❌ Could not fetch price history for {ticker}")
            return False
        
        print(f"✅ Fetched {len(price_history)} price data points")
        print()
        
        # Extract prices for bearish and target dates
        bearish_price, actual_bearish_date = tracker.extract_price_from_history(price_history, bearish_date)
        target_price, actual_target_date = tracker.extract_price_from_history(price_history, target_date)
        
        if bearish_price is None:
            print(f"❌ Could not find bearish price for {ticker} on {bearish_date.strftime('%Y-%m-%d')}")
            return False
        
        if target_price is None:
            print(f"❌ Could not find target price for {ticker} on {target_date.strftime('%Y-%m-%d')}")
            return False
        
        # Find previous price for bearish date
        sorted_history = sorted(price_history, key=lambda x: x.get('date', ''))
        actual_bearish_date_str = actual_bearish_date if actual_bearish_date else bearish_date.strftime('%Y-%m-%d')
        prev_price_entry = None
        for entry in sorted_history:
            entry_date = entry.get('date', '')
            if entry_date and entry_date < actual_bearish_date_str:
                if prev_price_entry is None or entry_date > prev_price_entry.get('date', ''):
                    prev_price_entry = entry
        
        prev_price = prev_price_entry.get('price') if prev_price_entry else bearish_price
        
        # Calculate percentages
        pct_drop = ((bearish_price - prev_price) / prev_price) * 100 if prev_price and prev_price > 0 else 0
        recovery_pct = ((target_price - bearish_price) / bearish_price) * 100 if bearish_price and bearish_price > 0 else 0
        
        print(f"Price Data:")
        print(f"  Bearish Date: {actual_bearish_date_str}")
        print(f"  Bearish Price: ${bearish_price:.2f}")
        print(f"  Previous Price: ${prev_price:.2f}")
        print(f"  Drop: {pct_drop:.2f}%")
        print(f"  Target Date: {actual_target_date if actual_target_date else target_date.strftime('%Y-%m-%d')}")
        print(f"  Target Price: ${target_price:.2f}")
        print(f"  Recovery: {recovery_pct:.2f}%")
        print()
        
    except Exception as e:
        print(f"❌ Error fetching stock data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Build stock_data
    print("-" * 80)
    print("STEP 2: Building stock_data")
    print("-" * 80)
    print()
    
    # Get company info
    companies = tracker._get_large_cap_companies_with_options()
    company_info = companies.get(ticker, {})
    
    stock_data = {
        'company_name': company_name,
        'industry': company_info.get('industry', 'Healthcare'),
        'market_cap': company_info.get('market_cap', 0),
        'bearish_date': actual_bearish_date_str,
        'bearish_price': bearish_price,
        'prev_price': prev_price,
        'pct_drop': pct_drop,
        'target_date': actual_target_date if actual_target_date else target_date.strftime('%Y-%m-%d'),
        'target_price': target_price,
        'recovery_pct': recovery_pct,
        'price_history': price_history,
        'earnings_dividends': {
            'events_during': [],
            'next_events': [],
            'has_events_during': False,
            'has_next_events': False
        }
    }
    
    print("stock_data prepared:")
    print(f"  Industry: {stock_data['industry']}")
    print(f"  Market Cap: ${stock_data['market_cap']:,.0f}")
    print(f"  Price History Points: {len(stock_data['price_history'])}")
    print()
    
    # Step 3: Call AI opinion
    print("-" * 80)
    print("STEP 3: Calling get_ai_recovery_opinion")
    print("-" * 80)
    print()
    print("⏳ Calling Claude API...")
    print("   (This may take 30-90 seconds as Claude searches the web)")
    print()
    
    try:
        result = tracker.get_ai_recovery_opinion(ticker, company_name, stock_data)
        
        if result:
            print("✅ AI opinion returned successfully!")
            print()
            print("=" * 80)
            print("RESULT")
            print("=" * 80)
            print()
            print(f"Score: {result.get('score')}/10")
            print()
            print("Explanation:")
            print("-" * 80)
            explanation = result.get('explanation', '')
            print(explanation)
            print()
            print("-" * 80)
            print(f"Explanation length: {len(explanation)} characters")
            print()
            return True
        else:
            print("❌ AI opinion returned None")
            print("   This could mean:")
            print("   - API key is invalid")
            print("   - API request failed")
            print("   - Response parsing failed")
            return False
            
    except Exception as e:
        print(f"❌ Error calling get_ai_recovery_opinion: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pacb_ai_opinion()
    print()
    if success:
        print("✅ Test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Test failed!")
        sys.exit(1)

