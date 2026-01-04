#!/usr/bin/env python3
"""
Unit test to verify bearish analytics with parameters from the image:
- Bullish/Bearish Date: 03/11/2025 (March 11, 2025)
- Target Date: 29/12/2025 (December 29, 2025)
- Industry: Technology
- Filter Type: Bearish Drop
- Min % Change: -3
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker

def test_bearish_analytics_image_params():
    """Test bearish analytics with exact parameters from the image"""
    print("=" * 80)
    print("BEARISH ANALYTICS TEST - Image Parameters")
    print("=" * 80)
    print()
    
    # Parameters from the image
    bearish_date_str = "2025-03-11"  # 03/11/2025
    target_date_str = "2025-12-29"   # 29/12/2025
    industry = "Technology"
    filter_type = "bearish"  # Bearish Drop
    pct_threshold = -3.0  # Min % Change: -3
    
    print(f"📅 Bullish/Bearish Date: {bearish_date_str}")
    print(f"📅 Target Date: {target_date_str}")
    print(f"🏭 Industry: {industry}")
    print(f"🔍 Filter Type: {filter_type}")
    print(f"📊 Min % Change: {pct_threshold}%")
    print()
    
    try:
        # Parse dates
        bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        
        print(f"✅ Dates parsed successfully")
        print(f"   Bearish Date: {bearish_date}")
        print(f"   Target Date: {target_date}")
        print()
        
        # Initialize tracker
        print("🚀 Initializing LayoffTracker...")
        tracker = LayoffTracker()
        print("✅ Tracker initialized")
        print()
        
        # Run bearish analytics
        print("📊 Running get_bearish_analytics...")
        print("   This may take a few minutes...")
        print()
        
        results, logs = tracker.get_bearish_analytics(
            bearish_date=bearish_date,
            target_date=target_date,
            industry=industry,
            filter_type=filter_type,
            pct_threshold=pct_threshold
        )
        
        print()
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        
        # Print logs
        print("📋 Processing Logs:")
        print("-" * 80)
        for log in logs[-20:]:  # Show last 20 logs
            print(f"  {log}")
        print()
        
        # Print results summary
        print(f"✅ Analysis Complete!")
        print(f"   Found {len(results)} stocks matching criteria")
        print()
        
        if len(results) > 0:
            print("📊 Top 10 Results:")
            print("-" * 80)
            for i, stock in enumerate(results[:10], 1):
                print(f"{i}. {stock.get('ticker', 'N/A')} - {stock.get('company_name', 'N/A')}")
                print(f"   Industry: {stock.get('industry', 'N/A')}")
                print(f"   Bearish Date ({stock.get('bearish_date', 'N/A')}): ${stock.get('bearish_price', 0):.2f} ({stock.get('pct_change', 0):.2f}%)")
                print(f"   Target Date ({stock.get('target_date', 'N/A')}): ${stock.get('target_price', 0):.2f} ({stock.get('recovery_pct', 0):+.2f}%)")
                
                # Check earnings/dividends data
                earnings_data = stock.get('earnings_dividends', {})
                events_during = earnings_data.get('events_during', [])
                next_events = earnings_data.get('next_events', [])
                
                if events_during:
                    print(f"   Events During Period: {len(events_during)} event(s)")
                    for event in events_during[:2]:  # Show first 2
                        print(f"     - {event.get('name', 'N/A')} on {event.get('date', 'N/A')}")
                else:
                    print(f"   Events During Period: None")
                
                if next_events:
                    print(f"   Next Events: {len(next_events)} event(s)")
                    for event in next_events[:2]:  # Show first 2
                        print(f"     - {event.get('name', 'N/A')} on {event.get('date', 'N/A')}")
                else:
                    print(f"   Next Events: None")
                
                print()
        else:
            print("⚠️  No stocks found matching the criteria")
            print("   Possible reasons:")
            print("   - No stocks dropped >= 3% on March 11, 2025")
            print("   - No Technology stocks with drops")
            print("   - Date range issues")
            print()
        
        # Check for errors in logs
        error_logs = [log for log in logs if '❌' in log or 'Error' in log or 'error' in log.lower()]
        if error_logs:
            print("=" * 80)
            print("⚠️  ERRORS FOUND IN LOGS")
            print("=" * 80)
            for error_log in error_logs:
                print(f"  {error_log}")
            print()
            return False
        else:
            print("=" * 80)
            print("✅ NO ERRORS DETECTED")
            print("=" * 80)
            print()
            return True
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ TEST FAILED WITH EXCEPTION")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bearish_analytics_image_params()
    sys.exit(0 if success else 1)

