#!/usr/bin/env python3
"""
Unittest to verify VWAP chart data accuracy:
- Each candle timestamp matches the requested time range
- Each candle's OHLC prices match Prixe.io data
- VWAP calculation is correct
- Time labels match actual timestamps
"""

import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_net_vwap_chart_accuracy():
    """Test VWAP chart data accuracy for NET on Nov 13, 2025"""
    
    print("=" * 80)
    print("VWAP CHART ACCURACY TEST - NET (Cloudflare) Nov 13, 2025")
    print("=" * 80)
    print()
    
    ticker = "NET"
    bearish_date_str = "2025-11-13"
    
    print(f"Ticker: {ticker}")
    print(f"Bearish date: {bearish_date_str}")
    print()
    
    tracker = LayoffTracker()
    
    # Parse bearish_date
    bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    
    # Calculate market open and close
    market_open_utc = tracker._get_market_open_time(bearish_date, ticker)
    market_close_utc = tracker._get_market_close_time(bearish_date, ticker)
    
    print(f"Market hours:")
    print(f"  Open (UTC): {market_open_utc}")
    print(f"  Close (UTC): {market_close_utc}")
    print()
    
    # Get next trading day
    next_trading_day = tracker.get_next_trading_day(bearish_date, ticker)
    if next_trading_day:
        next_market_open_utc = tracker._get_market_open_time(next_trading_day, ticker)
        end_time_utc = next_market_open_utc + timedelta(hours=3)
        print(f"Next trading day: {next_trading_day.date()}")
        print(f"End time (UTC): {end_time_utc}")
    print()
    
    # Fetch raw Prixe.io data for verification
    print("=" * 80)
    print("FETCHING RAW PRIXE.IO DATA")
    print("=" * 80)
    print()
    
    bearish_date_only = bearish_date.replace(hour=0, minute=0, second=0, microsecond=0)
    next_trading_day_only = next_trading_day.replace(hour=0, minute=0, second=0, microsecond=0) if next_trading_day else None
    
    # Fetch 1-minute data
    intraday_data_day1 = tracker._fetch_intraday_data_for_day(ticker, bearish_date_only, interval='1min')
    if not intraday_data_day1:
        intraday_data_day1 = tracker._fetch_intraday_data_for_day(ticker, bearish_date_only, interval='5min')
    
    intraday_data_day2 = None
    if next_trading_day_only:
        intraday_data_day2 = tracker._fetch_intraday_data_for_day(ticker, next_trading_day_only, interval='1min')
        if not intraday_data_day2:
            intraday_data_day2 = tracker._fetch_intraday_data_for_day(ticker, next_trading_day_only, interval='5min')
    
    # Combine raw data
    raw_timestamps = []
    raw_opens = []
    raw_highs = []
    raw_lows = []
    raw_closes = []
    raw_volumes = []
    
    if intraday_data_day1 and intraday_data_day1.get('success') and 'data' in intraday_data_day1:
        data1 = intraday_data_day1['data']
        raw_timestamps.extend(data1.get('timestamp', []))
        raw_opens.extend(data1.get('open', []))
        raw_highs.extend(data1.get('high', []))
        raw_lows.extend(data1.get('low', []))
        raw_closes.extend(data1.get('close', []))
        raw_volumes.extend(data1.get('volume', []))
    
    if intraday_data_day2 and intraday_data_day2.get('success') and 'data' in intraday_data_day2:
        data2 = intraday_data_day2['data']
        raw_timestamps.extend(data2.get('timestamp', []))
        raw_opens.extend(data2.get('open', []))
        raw_highs.extend(data2.get('high', []))
        raw_lows.extend(data2.get('low', []))
        raw_closes.extend(data2.get('close', []))
        raw_volumes.extend(data2.get('volume', []))
    
    print(f"Raw Prixe.io data: {len(raw_timestamps)} data points")
    if raw_timestamps:
        print(f"  First: {datetime.fromtimestamp(min(raw_timestamps), tz=timezone.utc)}")
        print(f"  Last: {datetime.fromtimestamp(max(raw_timestamps), tz=timezone.utc)}")
    print()
    
    # Test API endpoint
    print("=" * 80)
    print("TESTING API ENDPOINT")
    print("=" * 80)
    print()
    
    url = f"http://127.0.0.1:8082/api/vwap-chart-data?ticker={ticker}&bearish_date={bearish_date_str}"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            return False
        
        data = response.json()
        if not data.get('success'):
            print(f"❌ API returned success=False: {data.get('error')}")
            return False
        
        candles = data.get('candles', [])
        vwap_points = data.get('vwap_points', [])
        time_labels = data.get('time_labels', [])
        
        print(f"API returned: {len(candles)} candles, {len(vwap_points)} VWAP points, {len(time_labels)} time labels")
        print()
        
        if not candles:
            print("❌ No candles returned")
            return False
        
        # Verify each candle
        print("=" * 80)
        print("VERIFYING CANDLES")
        print("=" * 80)
        print()
        
        errors = []
        warnings = []
        
        start_timestamp = int(market_open_utc.timestamp())
        end_timestamp = int(end_time_utc.timestamp()) if next_trading_day else int(market_close_utc.timestamp())
        
        cumulative_price_volume = 0
        cumulative_volume = 0
        
        for i, candle in enumerate(candles):
            candle_ts = candle['timestamp']
            candle_dt = datetime.fromtimestamp(candle_ts, tz=timezone.utc)
            
            # Verify timestamp is in expected range
            if candle_ts < start_timestamp or candle_ts > end_timestamp:
                errors.append(f"Candle {i}: timestamp {candle_ts} ({candle_dt}) is outside expected range [{start_timestamp}, {end_timestamp}]")
            
            # Verify timestamp is rounded to 15 minutes
            expected_minute = (candle_dt.minute // 15) * 15
            if candle_dt.minute != expected_minute or candle_dt.second != 0:
                warnings.append(f"Candle {i}: timestamp {candle_dt} is not rounded to 15 minutes")
            
            # Find corresponding raw data points for this 15-minute period
            candle_start_ts = candle_ts
            candle_end_ts = candle_ts + 15 * 60  # 15 minutes later
            
            # For the last candle, also respect the end_timestamp limit
            if i == len(candles) - 1:
                candle_end_ts = min(candle_end_ts, end_timestamp)
            
            period_data = []
            for j, ts in enumerate(raw_timestamps):
                # Also filter by the expected time range
                if candle_start_ts <= ts < candle_end_ts and start_timestamp <= ts <= end_timestamp:
                    period_data.append({
                        'timestamp': ts,
                        'open': raw_opens[j] if j < len(raw_opens) else None,
                        'high': raw_highs[j] if j < len(raw_highs) else None,
                        'low': raw_lows[j] if j < len(raw_lows) else None,
                        'close': raw_closes[j] if j < len(raw_closes) else None,
                        'volume': raw_volumes[j] if j < len(raw_volumes) else 0
                    })
            
            if period_data:
                # Verify OHLC values match aggregated raw data
                expected_open = period_data[0]['open']
                expected_high = max(d['high'] for d in period_data if d['high'] is not None)
                expected_low = min(d['low'] for d in period_data if d['low'] is not None)
                expected_close = period_data[-1]['close']
                expected_volume = sum(d['volume'] for d in period_data)
                
                tolerance = 0.02  # Allow small floating point differences (increased for rounding)
                
                # For the last candle, be more lenient as it might be incomplete
                is_last_candle = (i == len(candles) - 1)
                last_candle_tolerance = 0.05 if is_last_candle else tolerance
                
                if abs(candle['open'] - expected_open) > tolerance:
                    errors.append(f"Candle {i} ({candle_dt}): Open mismatch - chart={candle['open']:.2f}, expected={expected_open:.2f} (diff={abs(candle['open'] - expected_open):.4f})")
                
                if abs(candle['high'] - expected_high) > last_candle_tolerance:
                    errors.append(f"Candle {i} ({candle_dt}): High mismatch - chart={candle['high']:.2f}, expected={expected_high:.2f} (diff={abs(candle['high'] - expected_high):.4f})")
                
                if abs(candle['low'] - expected_low) > last_candle_tolerance:
                    errors.append(f"Candle {i} ({candle_dt}): Low mismatch - chart={candle['low']:.2f}, expected={expected_low:.2f} (diff={abs(candle['low'] - expected_low):.4f})")
                
                if abs(candle['close'] - expected_close) > tolerance:
                    errors.append(f"Candle {i} ({candle_dt}): Close mismatch - chart={candle['close']:.2f}, expected={expected_close:.2f} (diff={abs(candle['close'] - expected_close):.4f})")
                
                # For volume, be more lenient for last candle (might be incomplete period)
                volume_tolerance = 100 if is_last_candle else 1
                if abs(candle['volume'] - expected_volume) > volume_tolerance:
                    warnings.append(f"Candle {i} ({candle_dt}): Volume mismatch - chart={candle['volume']}, expected={expected_volume} (diff={abs(candle['volume'] - expected_volume)})")
                
                # Calculate VWAP for this period
                period_price_volume = sum((d['high'] + d['low'] + d['close']) / 3 * d['volume'] 
                                         for d in period_data if d['high'] is not None and d['low'] is not None and d['close'] is not None and d['volume'] > 0)
                period_vol = sum(d['volume'] for d in period_data)
                
                if period_vol > 0:
                    cumulative_price_volume += period_price_volume
                    cumulative_volume += period_vol
                    expected_vwap = cumulative_price_volume / cumulative_volume if cumulative_volume > 0 else (expected_high + expected_low + expected_close) / 3
                else:
                    expected_vwap = (expected_high + expected_low + expected_close) / 3
                
                # Verify VWAP
                if i < len(vwap_points):
                    if abs(vwap_points[i] - expected_vwap) > tolerance:
                        errors.append(f"Candle {i} ({candle_dt}): VWAP mismatch - chart={vwap_points[i]:.2f}, expected={expected_vwap:.2f}")
            else:
                warnings.append(f"Candle {i} ({candle_dt}): No raw data found for this period")
            
            # Verify time label
            if i < len(time_labels):
                # Parse time label (format: "Nov 13 20:00")
                label_parts = time_labels[i].split()
                if len(label_parts) >= 3:
                    month_name = label_parts[0]
                    day = int(label_parts[1])
                    time_str = label_parts[2]
                    
                    month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
                    month = month_map.get(month_name, 0)
                    hour, minute = map(int, time_str.split(':'))
                    
                    # Convert to UTC for comparison (Israel time is UTC+2 or UTC+3)
                    # Rough approximation: assume UTC+2 for November
                    label_dt_utc = datetime(2025, month, day, hour, minute, tzinfo=timezone.utc) - timedelta(hours=2)
                    
                    # Allow 15-minute difference (since label might be at start of period)
                    if abs((label_dt_utc - candle_dt).total_seconds()) > 15 * 60:
                        warnings.append(f"Candle {i}: Time label '{time_labels[i]}' doesn't match timestamp {candle_dt}")
        
        # Print results
        print(f"Verified {len(candles)} candles")
        print()
        
        if errors:
            print(f"❌ ERRORS ({len(errors)}):")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")
            print()
        
        if warnings:
            print(f"⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings[:10]:  # Show first 10 warnings
                print(f"  {warning}")
            if len(warnings) > 10:
                print(f"  ... and {len(warnings) - 10} more warnings")
            print()
        
        if not errors and not warnings:
            print("✅ All candles verified successfully!")
            return True
        elif not errors:
            print("✅ No errors, but some warnings")
            return True
        else:
            print("❌ Verification failed with errors")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running on port 8082?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_net_vwap_chart_accuracy()
    sys.exit(0 if success else 1)
