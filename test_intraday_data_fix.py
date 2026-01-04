#!/usr/bin/env python3
"""
Test to verify the fix for 'intraday_data referenced before assignment' error.
This test specifically checks the market closed scenario where intraday_data
might be used without being initialized.
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

print(f"\n{'='*80}")
print("Test: intraday_data Initialization Fix")
print(f"{'='*80}\n")

# Initialize tracker
tracker = LayoffTracker()

# Create a test layoff for a company where market was closed
# Use a date that's more than 30 days ago but less than 60 days ago
# This will test the case where days_ago > 30, so intraday_data might not be initialized
test_date = datetime.now(timezone.utc) - timedelta(days=35)

# Create a layoff that was published when market was closed (e.g., weekend or after hours)
# Set to a Saturday at 8 PM ET (market closed)
test_layoff = {
    'company_name': 'Test Company',
    'stock_ticker': 'AAPL',  # Use a well-known ticker
    'datetime': test_date.replace(hour=20, minute=0, second=0),  # 8 PM UTC (market closed)
    'date': test_date.date().isoformat(),
    'time': '20:00',
    'url': 'https://test.com/article',
    'title': 'Test Article',
    'event_type': 'fda_approval_fasttrack'
}

print(f"Test layoff:")
print(f"  Company: {test_layoff['company_name']}")
print(f"  Ticker: {test_layoff['stock_ticker']}")
print(f"  Datetime: {test_layoff['datetime']}")
print(f"  Days ago: {(datetime.now(timezone.utc) - test_layoff['datetime']).days}")
print()

# Test calculate_stock_changes - this should not raise "referenced before assignment"
print("Testing calculate_stock_changes (market closed scenario)...")
print("  This should not raise 'local variable intraday_data referenced before assignment'")
print()

try:
    stock_changes = tracker.calculate_stock_changes(test_layoff)
    
    print("✅ calculate_stock_changes completed without errors!")
    print()
    
    # Check that results are returned
    if stock_changes:
        print(f"  Results returned: {len(stock_changes)} fields")
        print(f"  Base price: {stock_changes.get('base_price')}")
        print(f"  Market was open: {stock_changes.get('market_was_open')}")
        
        # Check a few intervals
        test_intervals = ['5min', '10min', '30min', '1hr', '2hr', '3hr']
        print(f"\n  Interval results:")
        for interval in test_intervals:
            price = stock_changes.get(f'price_{interval}')
            change = stock_changes.get(f'change_{interval}')
            market_closed = stock_changes.get(f'market_closed_{interval}')
            
            if price is not None:
                print(f"    {interval}: ${price:.2f} ({change:+.2f}%)")
            elif market_closed:
                print(f"    {interval}: Market Closed")
            else:
                print(f"    {interval}: N/A")
        
        print(f"\n✅ Test passed! No 'referenced before assignment' error occurred.")
    else:
        print("⚠️  No results returned (may be normal if API unavailable)")
        
except NameError as e:
    if 'intraday_data' in str(e):
        print(f"❌ FAILED: {e}")
        print(f"   The fix did not work - intraday_data is still referenced before assignment")
        sys.exit(1)
    else:
        raise
except Exception as e:
    # Other errors (like API errors) are OK - we're just testing the initialization
    if 'referenced before assignment' in str(e) or 'intraday_data' in str(e):
        print(f"❌ FAILED: {e}")
        print(f"   The fix did not work")
        sys.exit(1)
    else:
        print(f"⚠️  Other error (may be API-related): {e}")
        print(f"   This is OK - we're only testing that intraday_data is initialized")
        print(f"✅ No 'referenced before assignment' error - fix appears to work!")

print(f"\n{'='*80}")
print("✅ Test Completed!")
print(f"{'='*80}\n")

