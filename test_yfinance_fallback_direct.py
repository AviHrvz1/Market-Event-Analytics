#!/usr/bin/env python3
"""
Direct test of yfinance fallback for missing VWAP chart data
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Fix yfinance SSL issues (same as main.py)
try:
    import ssl
    import certifi
    
    # Prefer system certificates (more reliable, especially in sandboxed environments)
    system_cert = '/private/etc/ssl/cert.pem'
    certifi_cert = certifi.where()
    
    if os.path.exists(system_cert) and os.access(system_cert, os.R_OK):
        cert_path = system_cert
    elif os.path.exists(certifi_cert) and os.access(certifi_cert, os.R_OK):
        cert_path = certifi_cert
    else:
        cert_path = system_cert if os.path.exists(system_cert) else certifi_cert
    
    # Set environment variables for SSL certificate
    os.environ['SSL_CERT_FILE'] = cert_path
    os.environ['REQUESTS_CA_BUNDLE'] = cert_path
    os.environ['CURL_CA_BUNDLE'] = cert_path
except:
    pass

try:
    import yfinance as yf
    import yfinance.data as yf_data
    import pytz
    YFINANCE_AVAILABLE = True
    
    # Disable SSL verification for yfinance (same approach as main.py and app.py)
    # Set environment variables to disable SSL verification
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    os.environ['SSL_CERT_FILE'] = ''
    # Try to disable SSL verification at the curl level
    os.environ['CURLOPT_SSL_VERIFYPEER'] = '0'
    os.environ['CURLOPT_SSL_VERIFYHOST'] = '0'
    
    # Patch yfinance to disable SSL verification
    try:
        # Patch the _get_cookie_and_crumb_basic method which makes requests
        if hasattr(yf_data, 'YfData'):
            original_get = yf_data.YfData.get
            def patched_get(self, *args, **kwargs):
                # Try to pass verify=False if the underlying library supports it
                kwargs['verify'] = False
                try:
                    return original_get(self, *args, **kwargs)
                except TypeError:
                    # If verify is not supported, try without it
                    kwargs.pop('verify', None)
                    return original_get(self, *args, **kwargs)
            yf_data.YfData.get = patched_get
            
            # Also patch get_raw_json
            if hasattr(yf_data.YfData, 'get_raw_json'):
                original_get_raw_json = yf_data.YfData.get_raw_json
                def patched_get_raw_json(self, *args, **kwargs):
                    kwargs['verify'] = False
                    try:
                        return original_get_raw_json(self, *args, **kwargs)
                    except TypeError:
                        kwargs.pop('verify', None)
                        return original_get_raw_json(self, *args, **kwargs)
                yf_data.YfData.get_raw_json = patched_get_raw_json
    except Exception as patch_error:
        # If patching fails, try to patch curl_cffi directly
        try:
            import curl_cffi.requests as curl_requests
            # Patch curl_cffi Session to use verify=False by default
            original_request = curl_requests.Session.request
            def patched_request(self, *args, **kwargs):
                kwargs['verify'] = False
                return original_request(self, *args, **kwargs)
            curl_requests.Session.request = patched_request
        except:
            pass  # If all patching fails, continue anyway
except ImportError as e:
    print(f"yfinance not available: {e}")
    YFINANCE_AVAILABLE = False
    sys.exit(1)

def test_yfinance_fallback():
    """Test yfinance fallback directly"""
    
    print("=" * 80)
    print("DIRECT YFINANCE FALLBACK TEST")
    print("=" * 80)
    print()
    
    ticker = "DOCN"
    bearish_date_str = "2025-11-13"
    
    # Parse bearish_date
    bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    
    # Market open time (9:30 AM ET = 14:30 UTC)
    market_open_utc = datetime(2025, 11, 13, 14, 30, 0, tzinfo=timezone.utc)
    start_timestamp = int(market_open_utc.timestamp())
    
    # First data point from Prixe.io (1:00 PM ET = 18:00 UTC)
    first_ts_raw = 1763056800  # 2025-11-13 18:00:00 UTC
    first_dt_raw = datetime.fromtimestamp(first_ts_raw, tz=timezone.utc)
    
    print(f"Ticker: {ticker}")
    print(f"Bearish date: {bearish_date_str}")
    print(f"Market open (UTC): {market_open_utc} (timestamp: {start_timestamp})")
    print(f"First Prixe.io data (UTC): {first_dt_raw} (timestamp: {first_ts_raw})")
    print()
    
    missing_seconds = first_ts_raw - start_timestamp
    missing_minutes = missing_seconds / 60
    print(f"Missing: {missing_minutes:.0f} minutes ({missing_seconds} seconds)")
    print()
    
    if not YFINANCE_AVAILABLE:
        print("❌ yfinance not available")
        return False
    
    # Test yfinance download
    print("=" * 80)
    print("TESTING YFINANCE DOWNLOAD")
    print("=" * 80)
    print()
    
    date_str = bearish_date.strftime('%Y-%m-%d')
    next_date_str = (bearish_date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"Fetching: {ticker} from {date_str} to {next_date_str}, interval=1m")
    
    try:
        yf_data = yf.download(
            ticker,
            start=date_str,
            end=next_date_str,
            interval='1m',
            progress=False,
            auto_adjust=False
        )
        
        print(f"Download completed. Empty: {yf_data.empty}")
        if not yf_data.empty:
            print(f"Shape: {yf_data.shape}")
            print(f"Columns: {list(yf_data.columns)}")
            print(f"Index type: {type(yf_data.index)}")
            print(f"First index: {yf_data.index[0]}")
            print(f"Last index: {yf_data.index[-1]}")
            print()
            
            # Process data
            print("=" * 80)
            print("PROCESSING YFINANCE DATA")
            print("=" * 80)
            print()
            
            yf_timestamps = []
            yf_opens = []
            yf_highs = []
            yf_lows = []
            yf_closes = []
            yf_volumes = []
            
            print(f"Filtering range: {start_timestamp} ({market_open_utc}) to {first_ts_raw} ({first_dt_raw})")
            print()
            
            processed_count = 0
            in_range_count = 0
            
            for idx, row in yf_data.iterrows():
                try:
                    # Convert pandas timestamp to UTC
                    if idx.tz is None:
                        # Assume ET timezone if not set
                        et_tz = pytz.timezone('America/New_York')
                        idx_et = et_tz.localize(idx)
                        idx_utc = idx_et.astimezone(timezone.utc)
                    else:
                        idx_utc = idx.tz_convert('UTC')
                    
                    ts_utc = int(idx_utc.timestamp())
                    processed_count += 1
                    
                    # Only include data in the missing range
                    if start_timestamp <= ts_utc < first_ts_raw:
                        yf_timestamps.append(ts_utc)
                        yf_opens.append(float(row['Open']))
                        yf_highs.append(float(row['High']))
                        yf_lows.append(float(row['Low']))
                        yf_closes.append(float(row['Close']))
                        yf_volumes.append(int(row['Volume']) if 'Volume' in row else 0)
                        in_range_count += 1
                        
                        if in_range_count <= 5:
                            print(f"  Row {processed_count}: {idx} -> {idx_utc} (UTC) -> timestamp {ts_utc} -> {datetime.fromtimestamp(ts_utc, tz=timezone.utc)}")
                except Exception as e:
                    print(f"  Error processing row {processed_count}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print()
            print(f"Processed {processed_count} rows")
            print(f"Found {in_range_count} rows in missing range")
            print()
            
            if yf_timestamps:
                print("✅ SUCCESS! Found data in missing range:")
                print(f"  First timestamp: {min(yf_timestamps)} ({datetime.fromtimestamp(min(yf_timestamps), tz=timezone.utc)})")
                print(f"  Last timestamp: {max(yf_timestamps)} ({datetime.fromtimestamp(max(yf_timestamps), tz=timezone.utc)})")
                print(f"  Total data points: {len(yf_timestamps)}")
                print()
                
                # Show first few prices
                print("First 5 data points:")
                for i in range(min(5, len(yf_timestamps))):
                    ts = yf_timestamps[i]
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    print(f"  {dt}: Open=${yf_opens[i]:.2f}, High=${yf_highs[i]:.2f}, Low=${yf_lows[i]:.2f}, Close=${yf_closes[i]:.2f}")
                
                return True
            else:
                print("❌ No data found in missing range")
                print(f"  Start timestamp: {start_timestamp} ({market_open_utc})")
                print(f"  End timestamp: {first_ts_raw} ({first_dt_raw})")
                return False
        else:
            print("❌ yfinance returned empty data")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_yfinance_fallback()
    sys.exit(0 if success else 1)
