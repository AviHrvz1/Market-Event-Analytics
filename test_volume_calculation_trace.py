#!/usr/bin/env python3
"""Trace volume calculation step by step for Airbus EADSY"""

from main import LayoffTracker
from datetime import datetime, timezone, timedelta

print("=" * 80)
print("Volume Calculation Trace for Airbus EADSY")
print("=" * 80)

tracker = LayoffTracker()
article_datetime = datetime(2025, 12, 2, 5, 33, tzinfo=timezone.utc)

# Get next trading day
next_trading_day = tracker.get_next_trading_day(article_datetime, 'EADSY')
print(f"\n📅 Article: Dec 2, 2025 05:33 UTC (Market Closed)")
print(f"   Next trading day: {next_trading_day.strftime('%Y-%m-%d') if next_trading_day else 'None'}")

if next_trading_day:
    # Get market open time
    market_open_utc = tracker._get_market_open_time(next_trading_day, 'EADSY')
    print(f"   Market open: {market_open_utc.strftime('%H:%M')} UTC ({(market_open_utc - timedelta(hours=5)).strftime('%H:%M')} ET)")
    
    # Fetch intraday data
    intraday_data = tracker._fetch_intraday_data_for_day('EADSY', next_trading_day, interval='5min')
    
    if intraday_data:
        data = intraday_data.get('data', {})
        timestamps = data.get('timestamp', [])
        volumes = data.get('volume', [])
        closes = data.get('close', [])
        
        print(f"\n📊 Intraday Data:")
        print(f"   Total data points: {len(timestamps)}")
        
        # Find base volume (at market open)
        market_open_ts = int(market_open_utc.timestamp())
        base_volume = tracker._extract_intraday_volume_from_batch(intraday_data, market_open_utc)
        
        print(f"\n🔍 Base Volume Calculation:")
        print(f"   Market open timestamp: {market_open_ts}")
        print(f"   Base volume (from _extract_intraday_volume_from_batch): {base_volume:,.0f}" if base_volume else "   Base volume: None")
        
        # If base volume is None or 0, find first non-zero within 30 minutes
        if (base_volume is None or base_volume == 0):
            market_open_plus_30min_ts = market_open_ts + (30 * 60)
            print(f"   Searching for first non-zero volume within 30 minutes...")
            print(f"   Search range: {market_open_ts} to {market_open_plus_30min_ts}")
            
            for i, ts in enumerate(timestamps):
                if market_open_ts <= ts <= market_open_plus_30min_ts and i < len(volumes):
                    vol = volumes[i]
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    et = dt - timedelta(hours=5)
                    print(f"     Check {i}: {dt.strftime('%H:%M')} UTC ({et.strftime('%H:%M')} ET) - Volume: {vol:,.0f}" if vol else f"     Check {i}: {dt.strftime('%H:%M')} UTC ({et.strftime('%H:%M')} ET) - Volume: None")
                    if vol and vol > 0:
                        base_volume = float(vol)
                        print(f"   ✅ Found base volume: {base_volume:,.0f} at {dt.strftime('%H:%M')} UTC ({et.strftime('%H:%M')} ET)")
                        break
        
        if not base_volume:
            print(f"   ❌ No base volume found")
        
        # Check volumes at interval times
        print(f"\n📋 Interval Volume Calculations:")
        intervals = {
            '5min': market_open_utc + timedelta(minutes=5),
            '10min': market_open_utc + timedelta(minutes=10),
            '30min': market_open_utc + timedelta(minutes=30),
            '1hr': market_open_utc + timedelta(hours=1),
        }
        
        for interval_name, target_time in intervals.items():
            target_volume = tracker._extract_intraday_volume_from_batch(intraday_data, target_time)
            
            if target_volume and base_volume:
                vol_change = ((target_volume - base_volume) / base_volume) * 100
                et = target_time - timedelta(hours=5)
                print(f"   {interval_name} ({et.strftime('%H:%M')} ET):")
                print(f"      Target volume: {target_volume:,.0f}")
                print(f"      Base volume: {base_volume:,.0f}")
                print(f"      Change: {vol_change:+.2f}%")
            elif target_volume:
                et = target_time - timedelta(hours=5)
                print(f"   {interval_name} ({et.strftime('%H:%M')} ET): Volume {target_volume:,.0f}, Base volume missing")
            else:
                et = target_time - timedelta(hours=5)
                print(f"   {interval_name} ({et.strftime('%H:%M')} ET): No volume data")

# Now test actual calculation
print(f"\n🔍 Testing calculate_stock_changes...")
mock_layoff = {
    'company_name': 'Airbus',
    'stock_ticker': 'EADSY',
    'datetime': article_datetime,
    'date': article_datetime.strftime('%Y-%m-%d'),
    'time': article_datetime.strftime('%H:%M:%S'),
    'url': 'https://test.com/airbus',
    'title': 'Airbus test article'
}

stock_changes = tracker.calculate_stock_changes(mock_layoff)

print(f"\n📊 System Results:")
for interval in ['5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr']:
    price = stock_changes.get(f'price_{interval}')
    change = stock_changes.get(f'change_{interval}')
    vol_change = stock_changes.get(f'volume_change_{interval}')
    datetime_str = stock_changes.get(f'datetime_{interval}')
    
    if price:
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        et = dt - timedelta(hours=5)
        print(f"   {interval} ({et.strftime('%H:%M')} ET): ${price:.2f} ({change:+.2f}%), Vol: {vol_change:+.2f}%" if vol_change is not None else f"   {interval} ({et.strftime('%H:%M')} ET): ${price:.2f} ({change:+.2f}%), Vol: None")

print("\n" + "=" * 80)

