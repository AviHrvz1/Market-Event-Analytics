#!/usr/bin/env python3
"""
Test to check why intraday data is missing for certain tickers
Testing: VRTX, BLTE, PTGX, DYNE, CLRB, VRDN, RDHL, DNLI, VIR, TNXP, NVS
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_missing_intraday_data():
    """Check why intraday data is missing for these tickers"""
    print("=" * 80)
    print("MISSING INTRADAY DATA ANALYSIS")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test cases from user's data
    test_cases = [
        {'ticker': 'VRTX', 'company': 'Vertex Pharmaceuticals Incorporated', 'date': '2025-11-10', 'time': '03:00'},
        {'ticker': 'BLTE', 'company': 'Belite Bio, Inc.', 'date': '2025-10-15', 'time': '03:00'},
        {'ticker': 'PTGX', 'company': 'Protagonist Therapeutics, Inc.', 'date': '2025-08-25', 'time': '03:00'},
        {'ticker': 'DYNE', 'company': 'Dyne Therapeutics', 'date': '2025-06-17', 'time': '03:00'},
        {'ticker': 'CLRB', 'company': 'Cellectar Biosciences, Inc.', 'date': '2025-06-04', 'time': '03:00'},
        {'ticker': 'VRDN', 'company': 'Viridian Therapeutics, Inc.', 'date': '2025-05-07', 'time': '03:00'},
        {'ticker': 'RDHL', 'company': 'RedHill Biopharma Ltd.', 'date': '2025-03-12', 'time': '03:00'},
        {'ticker': 'DNLI', 'company': 'Denali Therapeutics Inc.', 'date': '2025-02-27', 'time': '03:00'},
        {'ticker': 'VIR', 'company': 'Vir Biotechnology', 'date': '2024-12-12', 'time': '03:00'},
        {'ticker': 'TNXP', 'company': 'Tonix Pharmaceuticals', 'date': '2024-11-18', 'time': '03:00'},
        {'ticker': 'NVS', 'company': 'Novartis', 'date': '2024-07-29', 'time': '03:00'},
    ]
    
    print(f"Testing {len(test_cases)} tickers...")
    print()
    
    results = []
    
    for i, case in enumerate(test_cases[:3], 1):  # Test first 3 to avoid too many API calls
        ticker = case['ticker']
        company = case['company']
        date_str = case['date']
        time_str = case['time']
        
        print(f"{i}. {ticker} - {company}")
        print(f"   Article Date: {date_str} {time_str}")
        print()
        
        # Parse datetime (assuming ET timezone, 03:00 = 08:00 UTC)
        article_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        # Convert to UTC (ET is UTC-5 in these months)
        article_datetime = article_datetime.replace(tzinfo=timezone(timedelta(hours=-5)))
        article_datetime_utc = article_datetime.astimezone(timezone.utc)
        
        print(f"   Article DateTime (UTC): {article_datetime_utc.isoformat()}")
        
        # Create mock layoff
        mock_layoff = {
            'company_name': company,
            'stock_ticker': ticker,
            'datetime': article_datetime_utc,
            'date': date_str,
            'time': time_str,
            'url': f'https://test.com/{ticker}',
            'title': f'{company} test article'
        }
        
        # Calculate stock changes
        print(f"   Fetching stock data...")
        stock_changes = tracker.calculate_stock_changes(mock_layoff)
        
        # Check which intervals have data
        intervals = ['1min', '2min', '3min', '4min', '5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr', '3hr']
        
        has_data = []
        no_data = []
        
        for interval in intervals:
            price_key = f'price_{interval}'
            price = stock_changes.get(price_key)
            if price is not None:
                change = stock_changes.get(f'change_{interval}')
                datetime_key = f'datetime_{interval}'
                dt_str = stock_changes.get(datetime_key)
                has_data.append({
                    'interval': interval,
                    'price': price,
                    'change': change,
                    'datetime': dt_str
                })
            else:
                no_data.append(interval)
        
        print(f"   ✅ Intervals with data: {len(has_data)}")
        for data in has_data:
            print(f"      {data['interval']:8s}: ${data['price']:.2f} ({data['change']:+.2f}%)" if data['change'] else f"      {data['interval']:8s}: ${data['price']:.2f}")
        
        print(f"   ❌ Intervals without data: {len(no_data)}")
        if no_data:
            print(f"      {', '.join(no_data)}")
        
        # Check if intraday data was fetched
        print()
        print(f"   Checking intraday data availability...")
        
        # Get next trading day
        from datetime import time as dt_time
        next_trading_day = article_datetime_utc
        # Skip to next day if article is on weekend
        while next_trading_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
            next_trading_day += timedelta(days=1)
        if next_trading_day.date() == article_datetime_utc.date():
            next_trading_day += timedelta(days=1)
            while next_trading_day.weekday() >= 5:
                next_trading_day += timedelta(days=1)
        
        # Market open is 9:30 AM ET = 14:30 UTC (in standard time) or 13:30 UTC (in daylight time)
        # For simplicity, let's use 14:30 UTC
        market_open_utc = next_trading_day.replace(hour=14, minute=30, second=0, microsecond=0)
        
        # Try to get intraday data
        try:
            intraday_data = tracker._get_intraday_batch_data(
                ticker,
                market_open_utc.date(),
                market_open_utc.date()
            )
            
            if intraday_data and 'data' in intraday_data:
                data = intraday_data['data']
                timestamps = data.get('timestamp', [])
                prices = data.get('close', [])
                volumes = data.get('volume', [])
                
                print(f"   📊 Intraday data points: {len(timestamps)}")
                if timestamps:
                    print(f"      First timestamp: {datetime.fromtimestamp(timestamps[0], tz=timezone.utc).isoformat()}")
                    print(f"      Last timestamp: {datetime.fromtimestamp(timestamps[-1], tz=timezone.utc).isoformat()}")
                    print(f"      Price points: {len(prices)}")
                    print(f"      Volume points: {len(volumes)}")
                    
                    # Check interval
                    if len(timestamps) > 1:
                        interval_seconds = timestamps[1] - timestamps[0]
                        if interval_seconds == 60:
                            interval = '1min'
                        elif interval_seconds == 300:
                            interval = '5min'
                        elif interval_seconds == 600:
                            interval = '10min'
                        elif interval_seconds == 1800:
                            interval = '30min'
                        elif interval_seconds == 3600:
                            interval = '1hr'
                        else:
                            interval = f'{interval_seconds}s'
                        print(f"      Data interval: {interval}")
                else:
                    print(f"      ⚠️  No timestamps in data")
            else:
                print(f"      ❌ No intraday data returned")
        except Exception as e:
            print(f"      ❌ Error fetching intraday data: {e}")
        
        results.append({
            'ticker': ticker,
            'has_data_count': len(has_data),
            'no_data_count': len(no_data),
            'has_data': has_data,
            'no_data': no_data
        })
        
        print()
        print("-" * 80)
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    for result in results:
        print(f"{result['ticker']}: {result['has_data_count']} intervals with data, {result['no_data_count']} without")
        if result['no_data_count'] > result['has_data_count']:
            print(f"  ⚠️  Most intervals missing data")
    
    return results

if __name__ == "__main__":
    test_missing_intraday_data()

