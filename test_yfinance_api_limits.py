#!/usr/bin/env python3
"""
Test yfinance API limits for 1-minute and 5-minute interval data
Tests different date ranges to determine actual API limitations
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, timezone
import pytz

def test_yfinance_limit(ticker: str, days_ago: int, interval: str):
    """Test yfinance API with a specific date range and interval"""
    
    # Calculate test date
    now = datetime.now(timezone.utc)
    test_date = now - timedelta(days=days_ago)
    date_str = test_date.strftime('%Y-%m-%d')
    
    # Map interval
    interval_map = {
        '1min': '1m',
        '5min': '5m',
    }
    yf_interval = interval_map.get(interval, interval)
    
    # yfinance requires start and end to be different, so add 1 day
    start_date = date_str
    end_date_obj = test_date + timedelta(days=1)
    end_date = end_date_obj.strftime('%Y-%m-%d')
    
    print(f"\n{'='*80}")
    print(f"Testing: {ticker} | {interval} interval | {days_ago} days ago ({date_str})")
    print(f"{'='*80}")
    print(f"Interval: {yf_interval}")
    print(f"Date range: {start_date} to {end_date}")
    
    try:
        print(f"Downloading data from yfinance...")
        # Suppress yfinance warnings/errors temporarily
        import warnings
        import sys
        from io import StringIO
        
        # Capture stderr to parse error messages
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                data = yf.download(
                    ticker,
                    start=start_date,
                    end=end_date,
                    interval=yf_interval,
                    progress=False,
                    auto_adjust=False
                )
        finally:
            stderr_output = sys.stderr.getvalue()
            sys.stderr = old_stderr
            
            # Check for specific error messages about date limits
            if stderr_output:
                if '1m data not available' in stderr_output and 'last 30 days' in stderr_output:
                    print(f"❌ FAILED - yfinance error: 1m data only available for last 30 days")
                    return False
                elif '5m data not available' in stderr_output and 'last 60 days' in stderr_output:
                    print(f"❌ FAILED - yfinance error: 5m data only available for last 60 days")
                    return False
        
        if data.empty:
            print(f"❌ FAILED - No data returned (empty DataFrame)")
            print(f"   ⚠️  Likely date range limit or market closed")
            return False
        
        # Check if we got any data
        if len(data) == 0:
            print(f"❌ FAILED - DataFrame has 0 rows")
            print(f"   ⚠️  Likely date range limit or market closed")
            return False
        
        # Get timezone info
        if data.index.tz is None:
            # Try to infer timezone (yfinance usually returns ET for US stocks)
            try:
                data.index = data.index.tz_localize('America/New_York')
            except:
                pass
        
        print(f"✅ SUCCESS")
        print(f"   Data points returned: {len(data)}")
        
        if len(data) > 0:
            first_ts = data.index[0]
            last_ts = data.index[-1]
            print(f"   Time range: {first_ts} to {last_ts}")
            
            # Get close prices
            try:
                if 'Close' in data.columns:
                    closes = data['Close']
                    if len(closes) > 0:
                        first_price = float(closes.iloc[0]) if hasattr(closes.iloc[0], '__float__') else closes.iloc[0]
                        last_price = float(closes.iloc[-1]) if hasattr(closes.iloc[-1], '__float__') else closes.iloc[-1]
                        print(f"   First price: ${first_price:.2f}, Last price: ${last_price:.2f}")
                elif 'Adj Close' in data.columns:
                    closes = data['Adj Close']
                    if len(closes) > 0:
                        first_price = float(closes.iloc[0]) if hasattr(closes.iloc[0], '__float__') else closes.iloc[0]
                        last_price = float(closes.iloc[-1]) if hasattr(closes.iloc[-1], '__float__') else closes.iloc[-1]
                        print(f"   First price (Adj): ${first_price:.2f}, Last price (Adj): ${last_price:.2f}")
            except Exception as price_err:
                print(f"   (Could not format prices: {price_err})")
        
        return True
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        print(f"❌ EXCEPTION: {error_type}")
        print(f"   Error: {error_msg}")
        
        # Check for specific yfinance errors
        if 'YFPricesMissingError' in error_type or 'YFPricesMissingError' in error_msg:
            print(f"   ⚠️  yfinance cannot fetch prices for this date (likely too old or market closed)")
        elif 'Invalid' in error_msg or 'invalid' in error_msg.lower():
            print(f"   ⚠️  Invalid request - possibly date range limit")
        elif 'interval' in error_msg.lower():
            print(f"   ⚠️  Interval-related error")
        
        return False

def main():
    """Run comprehensive tests"""
    
    ticker = 'AAPL'  # Use a common, liquid stock
    test_ranges = [1, 7, 25, 30, 31, 35, 60, 61, 90, 180, 365]  # Test various date ranges
    intervals = ['1min', '5min']
    
    print(f"\n{'#'*80}")
    print(f"# yfinance API Limit Test")
    print(f"# Ticker: {ticker}")
    print(f"# Testing intervals: {', '.join(intervals)}")
    print(f"# Testing date ranges: {', '.join(map(str, test_ranges))} days ago")
    print(f"{'#'*80}")
    
    results = {}
    
    for interval in intervals:
        print(f"\n\n{'='*80}")
        print(f"INTERVAL: {interval}")
        print(f"{'='*80}")
        results[interval] = {}
        
        for days_ago in test_ranges:
            success = test_yfinance_limit(ticker, days_ago, interval)
            results[interval][days_ago] = success
    
    # Summary
    print(f"\n\n{'#'*80}")
    print(f"# SUMMARY")
    print(f"{'#'*80}")
    
    for interval in intervals:
        print(f"\n{interval.upper()} INTERVAL:")
        print(f"  Days Ago | Status")
        print(f"  {'-'*40}")
        
        working_days = []
        failing_days = []
        limit_error_days = []
        
        for days_ago in sorted(test_ranges):
            success = results[interval][days_ago]
            status = "✅ WORKS" if success else "❌ FAILS"
            print(f"  {days_ago:8d} | {status}")
            
            if success:
                working_days.append(days_ago)
            else:
                failing_days.append(days_ago)
                # Check if this was a limit error (we'd need to track this, but for now infer from pattern)
                if days_ago >= 30 and interval == '1min':
                    limit_error_days.append(days_ago)
                elif days_ago >= 60 and interval == '5min':
                    limit_error_days.append(days_ago)
        
        # Determine limit based on error messages and working days
        if interval == '1min':
            max_working = max(working_days) if working_days else 0
            if limit_error_days:
                print(f"  {' '*10} ⚠️  LIMIT: 1-minute data only available for last 30 days (yfinance)")
                print(f"  {' '*10}    Last successful: {max_working} days ago")
        elif interval == '5min':
            max_working = max(working_days) if working_days else 0
            if limit_error_days:
                print(f"  {' '*10} ⚠️  LIMIT: 5-minute data only available for last 60 days (yfinance)")
                print(f"  {' '*10}    Last successful: {max_working} days ago")
        
        if not working_days:
            print(f"  {' '*10} ❌ No successful tests - check ticker or network connection")

if __name__ == '__main__':
    main()

