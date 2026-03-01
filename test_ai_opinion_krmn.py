#!/usr/bin/env python3
"""Test AI opinion for KRMN to diagnose the 'half working' issue"""

import sys
from datetime import datetime, timedelta, timezone
from main import LayoffTracker

def test_krmn_ai_opinion():
    """Test AI opinion for KRMN with Nov 13, 2025 bearish date"""
    print("=" * 80)
    print("KRMN AI OPINION DIAGNOSIS TEST")
    print("=" * 80)
    print()
    
    ticker = "KRMN"
    company_name = "Karman Holdings"
    
    # Dates from the user's query
    bearish_date = datetime(2025, 11, 13, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 31, tzinfo=timezone.utc)
    
    print(f"Testing: {ticker} ({company_name})")
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    print()
    
    # Initialize tracker
    print("Step 1: Initializing LayoffTracker...")
    tracker = LayoffTracker()
    
    # Check API key
    print(f"Step 2: Checking API key...")
    if not tracker.claude_api_key:
        print("❌ ERROR: No API key found!")
        return False
    
    if not tracker.claude_api_key:
        print("❌ ERROR: API key is still using placeholder value!")
        return False
    
    print(f"✅ API key found: {tracker.claude_api_key[:20]}...{tracker.claude_api_key[-10:]}")
    print()
    
    # Fetch price history
    print("Step 3: Fetching price history...")
    try:
        price_history = tracker.get_stock_price_history(ticker, bearish_date - timedelta(days=90), target_date)
        if not price_history:
            print("  ❌ Could not fetch price history")
            return False
        print(f"  ✅ Fetched {len(price_history)} price points")
    except Exception as e:
        print(f"  ❌ Error fetching price history: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Extract prices
    print("Step 4: Extracting prices...")
    try:
        bearish_price, actual_bearish_date = tracker.extract_price_from_history(price_history, bearish_date)
        target_price, actual_target_date = tracker.extract_price_from_history(price_history, target_date)
        
        if bearish_price is None or target_price is None:
            print("  ❌ Could not extract prices")
            return False
        
        print(f"  ✅ Bearish price: ${bearish_price:.2f} (date: {actual_bearish_date})")
        print(f"  ✅ Target price: ${target_price:.2f} (date: {actual_target_date})")
        
        # Calculate drop percentage
        prev_price = bearish_price * 1.1144  # Assuming -11.44% drop
        pct_drop = ((bearish_price - prev_price) / prev_price) * 100
        recovery_pct = ((target_price - bearish_price) / bearish_price) * 100
        
        print(f"  ✅ Drop: {pct_drop:.2f}%")
        print(f"  ✅ Recovery: {recovery_pct:.2f}%")
    except Exception as e:
        print(f"  ❌ Error extracting prices: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Fetch events
    print()
    print("Step 5: Fetching events...")
    try:
        sec_events = tracker._check_earnings_dividends_sec(ticker, bearish_date - timedelta(days=90), target_date, future_days=0)
        yfinance_events = tracker._check_earnings_dividends_yfinance(ticker, bearish_date - timedelta(days=90), target_date, future_days=0)
        
        events_during = sec_events.get('events_during', [])
        if yfinance_events:
            yfinance_events_during = yfinance_events.get('events_during', [])
            if yfinance_events_during:
                events_during.extend(yfinance_events_during)
        
        print(f"  ✅ Found {len(events_during)} events during period")
        for event in events_during[:5]:  # Show first 5
            print(f"     - {event.get('date')}: {event.get('type')} - {event.get('name')}")
    except Exception as e:
        print(f"  ⚠️  Error fetching events: {e}")
        events_during = []
    
    # Build stock_data
    print()
    print("Step 6: Building stock_data...")
    stock_data = {
        'company_name': company_name,
        'industry': 'Technology',
        'market_cap': 59000000,  # $59M (from user's display)
        'bearish_date': actual_bearish_date or bearish_date.strftime('%Y-%m-%d'),
        'bearish_price': bearish_price,
        'prev_price': prev_price,
        'pct_drop': pct_drop,
        'target_date': actual_target_date or target_date.strftime('%Y-%m-%d'),
        'target_price': target_price,
        'recovery_pct': recovery_pct,
        'price_history': price_history,
        'earnings_dividends': {'events_during': events_during, 'next_events': []}
    }
    
    print(f"  ✅ Stock data prepared")
    print(f"     - Market cap: ${stock_data['market_cap']:,.0f}")
    print(f"     - Price history points: {len(stock_data['price_history'])}")
    print()
    
    # Test AI opinion
    print("Step 7: Calling get_ai_recovery_opinion...")
    print("  (This may take 30-90 seconds)")
    print()
    
    try:
        result = tracker.get_ai_recovery_opinion(ticker, company_name, stock_data)
        
        if result:
            print("✅ SUCCESS! AI opinion returned:")
            print(f"   Score: {result.get('score')}/10")
            explanation = result.get('explanation', '')
            print(f"   Explanation length: {len(explanation)} characters")
            
            if explanation:
                print()
                print("   First 500 characters of explanation:")
                print("   " + "-" * 76)
                print(f"   {explanation[:500]}...")
                print("   " + "-" * 76)
                
                # Check for common issues
                if len(explanation) < 100:
                    print()
                    print("   ⚠️  WARNING: Explanation is very short (< 100 chars)")
                
                if "error" in explanation.lower() or "failed" in explanation.lower():
                    print()
                    print("   ⚠️  WARNING: Explanation contains error/failed keywords")
                
                # Check if it's valid JSON that wasn't parsed
                if explanation.strip().startswith('{'):
                    print()
                    print("   ⚠️  WARNING: Explanation looks like raw JSON (may not have been parsed)")
            
            return True
        else:
            print("❌ FAILED: get_ai_recovery_opinion returned None")
            print("   This usually means:")
            print("   - API request failed (check network)")
            print("   - API key is invalid")
            print("   - Response parsing failed")
            print()
            print("   Check the server logs for [AI OPINION] error messages")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_krmn_ai_opinion()
    print()
    if success:
        print("=" * 80)
        print("✅ TEST COMPLETE: AI opinion is working!")
        print("=" * 80)
    else:
        print("=" * 80)
        print("❌ TEST COMPLETE: AI opinion is NOT working")
        print("   Check the error messages above for details")
        print("=" * 80)
    sys.exit(0 if success else 1)

