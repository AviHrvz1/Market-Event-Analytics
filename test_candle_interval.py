#!/usr/bin/env python3
"""Test to verify candle intervals for past dates"""

import requests
import json
from datetime import datetime

def test_candle_intervals():
    """Test that past dates use 1-hour candles"""
    
    ticker = "NET"
    bearish_date = "2025-11-13"  # Past date
    
    url = f"http://127.0.0.1:8082/api/vwap-chart-data?ticker={ticker}&bearish_date={bearish_date}"
    
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
        time_labels = data.get('time_labels', [])
        
        print(f"Total candles: {len(candles)}")
        print(f"First 10 time labels: {time_labels[:10]}")
        print()
        
        # Check intervals between consecutive labels
        print("Checking intervals between consecutive candles:")
        intervals = []
        for i in range(1, min(20, len(time_labels))):
            # Parse time labels (format: "Nov 13 20:00")
            parts1 = time_labels[i-1].split()
            parts2 = time_labels[i].split()
            
            if len(parts1) >= 3 and len(parts2) >= 3:
                time1 = parts1[2]  # "20:00"
                time2 = parts2[2]  # "20:15" or "21:00"
                
                h1, m1 = map(int, time1.split(':'))
                h2, m2 = map(int, time2.split(':'))
                
                # Calculate difference in minutes
                if parts1[0] == parts2[0] and parts1[1] == parts2[1]:  # Same day
                    diff_minutes = (h2 * 60 + m2) - (h1 * 60 + m1)
                else:
                    # Different day - assume next day
                    diff_minutes = (24 * 60) - (h1 * 60 + m1) + (h2 * 60 + m2)
                
                intervals.append(diff_minutes)
                print(f"  {time_labels[i-1]} -> {time_labels[i]}: {diff_minutes} minutes")
        
        print()
        if intervals:
            unique_intervals = set(intervals)
            print(f"Unique intervals found: {sorted(unique_intervals)} minutes")
            
            if 60 in unique_intervals and 15 not in unique_intervals:
                print("✅ PASS: Using 1-hour candles (60 minutes)")
                return True
            elif 15 in unique_intervals and 60 not in unique_intervals:
                print("❌ FAIL: Still using 15-minute candles (should be 60 minutes for past dates)")
                return False
            else:
                print(f"⚠️  Mixed intervals: {sorted(unique_intervals)}")
                return False
        else:
            print("❌ Could not determine intervals")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_candle_intervals()
