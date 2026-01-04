#!/usr/bin/env python3
"""Unit test to investigate BYD (1211.HK) data - why all prices are the same"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

print("=" * 80)
print("BYD (1211.HK) Data Investigation")
print("=" * 80)

tracker = LayoffTracker()

# Test article data - Sun, Nov 30, 2025 04:48 UTC
article_date = datetime(2025, 11, 30, 4, 48, tzinfo=timezone.utc)

print(f"\n📰 Article Date: {article_date.strftime('%a, %b %d, %Y %H:%M')} UTC")
print(f"   Market Status: {'Open' if tracker.is_market_open(article_date) else 'Closed'}")

# Create mock layoff entry
mock_layoff = {
    'company_name': 'BYD Company Limited',
    'stock_ticker': '1211.HK',
    'datetime': article_date,
    'date': article_date.strftime('%Y-%m-%d'),
    'time': article_date.strftime('%H:%M:%S'),
    'url': 'https://test.com/byd',
    'title': 'BYD test article'
}

print(f"\n🔍 Testing stock change calculation for {mock_layoff['stock_ticker']}...")

try:
    stock_changes = tracker.calculate_stock_changes(mock_layoff)
    
    print(f"\n📊 Results:")
    print(f"  Base Price: ${stock_changes.get('base_price'):.2f}" if stock_changes.get('base_price') else "  Base Price: None")
    print(f"  Market Was Open: {stock_changes.get('market_was_open')}")
    
    # Check all intervals
    intervals = ['5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr', '3hr']
    
    print(f"\n📈 Interval Prices and Changes:")
    all_same = True
    first_price = None
    prices_found = []
    
    for interval in intervals:
        price = stock_changes.get(f'price_{interval}')
        change = stock_changes.get(f'change_{interval}')
        volume_change = stock_changes.get(f'volume_change_{interval}')
        market_closed = stock_changes.get(f'market_closed_{interval}')
        is_daily_close = stock_changes.get(f'is_daily_close_{interval}')
        
        if price:
            prices_found.append(price)
            if first_price is None:
                first_price = price
            elif abs(price - first_price) > 0.01:  # Allow small floating point differences
                all_same = False
            
            status = []
            if market_closed:
                status.append("Market Closed")
            if is_daily_close:
                status.append("Daily Close")
            
            status_str = f" [{', '.join(status)}]" if status else ""
            
            change_str = f"{change:+.2f}%" if change is not None else "N/A"
            vol_str = f"{volume_change:+.2f}%" if volume_change is not None else "N/A"
            
            print(f"  {interval:6s}: ${price:.2f} ({change_str}) Vol: {vol_str}{status_str}")
        else:
            print(f"  {interval:6s}: N/A")
    
    if all_same and first_price:
        print(f"\n⚠️  WARNING: All prices are the same (${first_price:.2f})")
        print(f"   This could mean:")
        print(f"   1. Stock price genuinely didn't move")
        print(f"   2. Prixe.io returned same price for all intervals")
        print(f"   3. Intraday data is missing/incorrect")
        print(f"   4. Using daily close price for all intervals")
    
    # Check if intraday data was fetched
    print(f"\n🔍 Checking intraday data availability...")
    ticker = '1211.HK'
    
    # Article was on Sunday, so check Monday (Dec 1, 2025) for intraday data
    next_trading_day = datetime(2025, 12, 1, 0, 0, tzinfo=timezone.utc)
    
    print(f"  Checking intraday data for: {next_trading_day.strftime('%Y-%m-%d')}")
    intraday_data = tracker._fetch_intraday_data_for_day(ticker, next_trading_day, interval='5min')
    
    if intraday_data:
        print(f"  ✅ Intraday data available")
        data = intraday_data.get('data', {})
        # Prixe.io returns prices in 'close' array, not 'price' (which is a single value)
        prices = data.get('close', []) or data.get('price', [])
        timestamps = data.get('timestamp', [])
        volumes = data.get('volume', [])
        
        if prices and timestamps:
            # Handle both list and single value
            if isinstance(prices, list):
                price_list = prices
            else:
                price_list = [prices]
            
            if isinstance(timestamps, list):
                ts_list = timestamps
            else:
                ts_list = [timestamps]
            
            print(f"  Data points: {len(price_list)}")
            if len(price_list) > 0:
                unique_prices = set([round(p, 2) for p in price_list if p is not None])
                print(f"  Unique prices: {len(unique_prices)}")
                if len(unique_prices) == 1:
                    print(f"  ⚠️  All data points have same price: ${list(unique_prices)[0]:.2f}")
                    print(f"     This suggests Prixe.io data may be incorrect or stock didn't trade")
                else:
                    price_list_sorted = sorted(unique_prices)
                    print(f"  Price range: ${min(price_list_sorted):.2f} - ${max(price_list_sorted):.2f}")
                    print(f"  Sample prices: {price_list_sorted[:5]} ... {price_list_sorted[-5:]}")
                    print(f"  ✅ Prixe.io HAS varying prices - issue is in price extraction logic")
                
                # Check volumes
                if volumes:
                    non_zero_volumes = [v for v in volumes if v and v > 0]
                    if non_zero_volumes:
                        print(f"  Volume range: {min(non_zero_volumes):,.0f} - {max(non_zero_volumes):,.0f}")
                    else:
                        print(f"  ⚠️  All volumes are zero - stock may not have traded")
        else:
            print(f"  ⚠️  No price data in response")
            print(f"     Response structure: {list(data.keys())}")
    else:
        print(f"  ❌ No intraday data available")
        print(f"     This could mean:")
        print(f"     1. Prixe.io doesn't support 1211.HK intraday data")
        print(f"     2. Data is not available for this date")
        print(f"     3. API request failed")
    
    # Check daily price data
    print(f"\n🔍 Checking daily price data...")
    start_date = article_date - timedelta(days=5)
    end_date = article_date + timedelta(days=3)
    
    daily_data = tracker._fetch_price_data_batch(ticker, start_date, end_date, '1d')
    
    if daily_data:
        print(f"  ✅ Daily data available")
        data = daily_data.get('data', {})
        closes = data.get('close', [])
        timestamps = data.get('timestamp', [])
        
        if closes and timestamps:
            print(f"  Daily close prices:")
            for i, (ts, close) in enumerate(zip(timestamps[:10], closes[:10])):
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                print(f"    {dt.strftime('%Y-%m-%d')}: ${close:.2f}")
    else:
        print(f"  ❌ No daily data available")
    
    # Test price extraction
    print(f"\n🔍 Testing price extraction for specific intervals...")
    if intraday_data:
        # Test extracting price at different times on Dec 1
        test_times = [
            datetime(2025, 12, 1, 9, 35, tzinfo=timezone.utc),  # 9:35 AM ET
            datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc),  # 10:00 AM ET
            datetime(2025, 12, 1, 12, 0, tzinfo=timezone.utc),  # 12:00 PM ET
        ]
        
        for test_time in test_times:
            price = tracker._extract_intraday_price_from_batch(intraday_data, test_time)
            volume = tracker._extract_intraday_volume_from_batch(intraday_data, test_time)
            print(f"  {test_time.strftime('%H:%M')} UTC: ${price:.2f}" if price else f"  {test_time.strftime('%H:%M')} UTC: N/A", end="")
            if volume:
                print(f" Vol: {volume:,.0f}")
            else:
                print()
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Summary:")
print("=" * 80)
print("If all prices are the same, it could be:")
print("1. Legitimate: Stock price didn't move (unlikely for all intervals)")
print("2. Data issue: Prixe.io returning same price for all intervals")
print("3. Missing data: Prixe.io doesn't have intraday data for 1211.HK")
print("4. Fallback: System using daily close price for all intervals")

