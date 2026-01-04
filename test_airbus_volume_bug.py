#!/usr/bin/env python3
"""Investigate volume calculation bug for Airbus EADSY"""

from main import LayoffTracker
from datetime import datetime, timezone, timedelta

print("=" * 80)
print("Airbus EADSY Volume Calculation Bug Investigation")
print("=" * 80)

tracker = LayoffTracker()
article_datetime = datetime(2025, 12, 2, 5, 33, tzinfo=timezone.utc)

mock_layoff = {
    'company_name': 'Airbus',
    'stock_ticker': 'EADSY',
    'datetime': article_datetime,
    'date': article_datetime.strftime('%Y-%m-%d'),
    'time': article_datetime.strftime('%H:%M:%S'),
    'url': 'https://test.com/airbus',
    'title': 'Airbus test article'
}

print(f"\n📰 Article: Dec 2, 2025 05:33 UTC (Market Closed)")
print(f"   Next trading day: Dec 3, 2025")

# Get intraday data for Dec 3
next_trading_day = datetime(2025, 12, 3, 0, 0, tzinfo=timezone.utc)
intraday_data = tracker._fetch_intraday_data_for_day('EADSY', next_trading_day, interval='5min')

if intraday_data:
    data = intraday_data.get('data', {})
    timestamps = data.get('timestamp', [])
    volumes = data.get('volume', [])
    closes = data.get('close', [])
    
    print(f"\n📊 Prixe.io Intraday Data for Dec 3, 2025:")
    print(f"   Total data points: {len(timestamps)}")
    
    if timestamps and volumes:
        print(f"\n   First 10 data points:")
        for i in range(min(10, len(timestamps))):
            ts = timestamps[i]
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            et = dt - timedelta(hours=5)  # EST
            vol = volumes[i] if i < len(volumes) else None
            price = closes[i] if i < len(closes) else None
            print(f"     {i}: {dt.strftime('%H:%M')} UTC ({et.strftime('%H:%M')} ET) - Price: ${price:.2f}, Volume: {vol:,.0f}" if vol and price else f"     {i}: {dt.strftime('%H:%M')} UTC ({et.strftime('%H:%M')} ET) - Price: ${price:.2f}, Volume: None")
        
        # Check market open time
        market_open_utc = tracker._get_market_open_time(next_trading_day, 'EADSY')
        print(f"\n   Market open: {market_open_utc.strftime('%H:%M')} UTC ({(market_open_utc - timedelta(hours=5)).strftime('%H:%M')} ET)")
        
        # Find volume at market open
        market_open_ts = int(market_open_utc.timestamp())
        base_volume = None
        base_volume_idx = None
        
        for i, ts in enumerate(timestamps):
            if abs(ts - market_open_ts) < 300:  # Within 5 minutes
                base_volume = volumes[i] if i < len(volumes) else None
                base_volume_idx = i
                break
        
        if base_volume is None:
            # Try to find first non-zero volume within 30 minutes
            market_open_plus_30min_ts = market_open_ts + (30 * 60)
            for i, ts in enumerate(timestamps):
                if market_open_ts <= ts <= market_open_plus_30min_ts and i < len(volumes):
                    vol = volumes[i]
                    if vol and vol > 0:
                        base_volume = float(vol)
                        base_volume_idx = i
                        break
        
        print(f"\n   Base volume (at market open): {base_volume:,.0f}" if base_volume else "   Base volume: None")
        if base_volume_idx is not None:
            dt_base = datetime.fromtimestamp(timestamps[base_volume_idx], tz=timezone.utc)
            print(f"   Base volume time: {dt_base.strftime('%H:%M')} UTC (index {base_volume_idx})")
        
        # Check volumes at interval times
        print(f"\n   Volumes at interval times:")
        intervals = {
            '5min': market_open_utc + timedelta(minutes=5),
            '10min': market_open_utc + timedelta(minutes=10),
            '30min': market_open_utc + timedelta(minutes=30),
            '1hr': market_open_utc + timedelta(hours=1),
        }
        
        for interval_name, target_time in intervals.items():
            target_ts = int(target_time.timestamp())
            target_volume = None
            target_idx = None
            
            # Find closest timestamp
            closest_idx = 0
            min_diff = abs(timestamps[0] - target_ts)
            for i, ts in enumerate(timestamps):
                diff = abs(ts - target_ts)
                if diff < min_diff:
                    min_diff = diff
                    closest_idx = i
            
            if min_diff < 300:  # Within 5 minutes
                target_volume = volumes[closest_idx] if closest_idx < len(volumes) else None
                target_idx = closest_idx
            
            if target_volume and base_volume:
                vol_change = ((target_volume - base_volume) / base_volume) * 100
                dt_target = datetime.fromtimestamp(timestamps[target_idx], tz=timezone.utc)
                print(f"     {interval_name} ({dt_target.strftime('%H:%M')} UTC): Volume {target_volume:,.0f}, Change: {vol_change:+.2f}%")
            elif target_volume:
                print(f"     {interval_name}: Volume {target_volume:,.0f}, Base volume missing")
            else:
                print(f"     {interval_name}: No volume data")

# Now test the actual calculation
print(f"\n🔍 Testing calculate_stock_changes...")
stock_changes = tracker.calculate_stock_changes(mock_layoff)

print(f"\n📊 System Results:")
print(f"   Base price: ${stock_changes.get('base_price'):.2f}")

for interval in ['5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr']:
    price = stock_changes.get(f'price_{interval}')
    change = stock_changes.get(f'change_{interval}')
    vol_change = stock_changes.get(f'volume_change_{interval}')
    datetime_str = stock_changes.get(f'datetime_{interval}')
    
    if price:
        print(f"   {interval}: ${price:.2f} ({change:+.2f}%), Vol: {vol_change:+.2f}%" if vol_change is not None else f"   {interval}: ${price:.2f} ({change:+.2f}%), Vol: None")
        if datetime_str:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            et = dt - timedelta(hours=5)
            print(f"      Time: {et.strftime('%H:%M')} ET")

print("\n" + "=" * 80)

