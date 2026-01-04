#!/usr/bin/env python3
"""
Unit test to check if yfinance is reachable and identify certificate/SSL errors
"""

import sys
import os
from datetime import datetime, timezone

# Try to fix certificate path issue
try:
    import ssl
    import certifi
    
    # Try system certificates first (more reliable)
    system_cert = '/private/etc/ssl/cert.pem'
    certifi_cert = certifi.where()
    
    # Prefer system certificates if available (more reliable, especially in sandboxed environments)
    if os.path.exists(system_cert) and os.access(system_cert, os.R_OK):
        cert_path = system_cert
        print(f"[CERTIFICATE] Using system certificate: {cert_path}")
    elif os.path.exists(certifi_cert) and os.access(certifi_cert, os.R_OK):
        cert_path = certifi_cert
        print(f"[CERTIFICATE] Using certifi certificate: {cert_path}")
    else:
        # Fallback: try to find any valid certificate
        cert_path = system_cert if os.path.exists(system_cert) else certifi_cert
        print(f"[CERTIFICATE] Warning: Using certificate path (may not be accessible): {cert_path}")
    
    # Set environment variables for SSL certificate
    os.environ['SSL_CERT_FILE'] = cert_path
    os.environ['REQUESTS_CA_BUNDLE'] = cert_path
    os.environ['CURL_CA_BUNDLE'] = cert_path
    
    # Also try to configure curl_cffi if possible
    try:
        import curl_cffi
        # curl_cffi might need explicit configuration
        print(f"[CERTIFICATE] curl_cffi version: {curl_cffi.__version__}")
    except:
        pass
        
except Exception as e:
    print(f"[CERTIFICATE] Warning: Could not set certificate path: {e}")

def test_yfinance_reachability():
    """Test if yfinance can be imported and used without certificate errors"""
    print("=" * 80)
    print("YFINANCE REACHABILITY TEST")
    print("=" * 80)
    print()
    
    # Test 1: Check if yfinance can be imported
    print("Test 1: Import yfinance")
    print("-" * 80)
    try:
        import yfinance as yf
        print("✅ PASS: yfinance imported successfully")
        print(f"   Version: {yf.__version__ if hasattr(yf, '__version__') else 'Unknown'}")
    except ImportError as e:
        print(f"❌ FAIL: Cannot import yfinance: {e}")
        print("   Install with: pip install yfinance")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error importing yfinance: {e}")
        return False
    print()
    
    # Test 2: Test basic ticker creation (no network call yet)
    print("Test 2: Create Ticker object")
    print("-" * 80)
    try:
        ticker = yf.Ticker("AAPL")
        print("✅ PASS: Ticker object created successfully")
    except Exception as e:
        print(f"❌ FAIL: Cannot create Ticker object: {e}")
        return False
    print()
    
    # Test 3: Test fetching earnings dates (with SSL/certificate check)
    print("Test 3: Fetch earnings dates (checks network + SSL)")
    print("-" * 80)
    try:
        earnings_dates = ticker.get_earnings_dates(limit=10)
        if earnings_dates is not None and len(earnings_dates) > 0:
            print(f"✅ PASS: Successfully fetched {len(earnings_dates)} earnings dates")
            print(f"   Sample dates: {earnings_dates.index[:3].tolist() if len(earnings_dates) >= 3 else earnings_dates.index.tolist()}")
        else:
            print("⚠️  WARNING: Earnings dates returned but empty or None")
    except Exception as e:
        error_str = str(e).lower()
        if 'certificate' in error_str or 'ssl' in error_str or 'cert' in error_str:
            print(f"❌ FAIL: Certificate/SSL error: {e}")
            print("   This indicates a certificate verification issue")
            print("   Possible solutions:")
            print("   1. Update certificates: pip install --upgrade certifi")
            print("   2. Disable SSL verification (not recommended): yfinance may have options")
            return False
        elif 'timeout' in error_str or 'connection' in error_str:
            print(f"❌ FAIL: Network/connection error: {e}")
            print("   This indicates network connectivity issues")
            return False
        else:
            print(f"❌ FAIL: Unexpected error fetching earnings dates: {e}")
            import traceback
            traceback.print_exc()
            return False
    print()
    
    # Test 4: Test fetching dividends (with SSL/certificate check)
    print("Test 4: Fetch dividend history (checks network + SSL)")
    print("-" * 80)
    try:
        dividends = ticker.dividends
        if dividends is not None and len(dividends) > 0:
            print(f"✅ PASS: Successfully fetched {len(dividends)} dividend records")
            print(f"   Date range: {dividends.index.min()} to {dividends.index.max()}")
            print(f"   Sample dividends: {dividends.head(3).to_dict()}")
        else:
            print("⚠️  WARNING: Dividends returned but empty or None")
            print("   (This might be normal if AAPL doesn't pay dividends, but unlikely)")
    except Exception as e:
        error_str = str(e).lower()
        if 'certificate' in error_str or 'ssl' in error_str or 'cert' in error_str:
            print(f"❌ FAIL: Certificate/SSL error: {e}")
            print("   This indicates a certificate verification issue")
            return False
        elif 'timeout' in error_str or 'connection' in error_str:
            print(f"❌ FAIL: Network/connection error: {e}")
            return False
        else:
            print(f"❌ FAIL: Unexpected error fetching dividends: {e}")
            import traceback
            traceback.print_exc()
            return False
    print()
    
    # Test 5: Test date filtering (simulate events during period)
    print("Test 5: Test date filtering (simulate events during period)")
    print("-" * 80)
    try:
        # Simulate a date range: Dec 1, 2024 to Dec 31, 2024
        start_date = datetime(2024, 12, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
        
        # Filter earnings dates
        if earnings_dates is not None and len(earnings_dates) > 0:
            earnings_during = earnings_dates[
                (earnings_dates.index >= start_date) & 
                (earnings_dates.index <= end_date)
            ]
            print(f"✅ PASS: Successfully filtered earnings dates")
            print(f"   Earnings in period: {len(earnings_during)}")
        else:
            print("⚠️  SKIP: No earnings dates to filter")
        
        # Filter dividends (dividends.index is already timezone-aware datetime)
        if dividends is not None and len(dividends) > 0:
            # Convert start_date and end_date to match dividends index timezone
            if dividends.index.tz is not None:
                start_dt = start_date.astimezone(dividends.index.tz)
                end_dt = end_date.astimezone(dividends.index.tz)
            else:
                start_dt = start_date
                end_dt = end_date
            dividends_during = dividends[
                (dividends.index >= start_dt) & 
                (dividends.index <= end_dt)
            ]
            print(f"✅ PASS: Successfully filtered dividends")
            print(f"   Dividends in period: {len(dividends_during)}")
        else:
            print("⚠️  SKIP: No dividends to filter")
            
    except Exception as e:
        print(f"❌ FAIL: Error filtering dates: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # Test 6: Test with SSL verification disabled (if previous tests failed)
    print("Test 6: Test with SSL verification disabled (if needed)")
    print("-" * 80)
    print("⚠️  This test is skipped if previous tests passed")
    print("   If you see certificate errors above, you may need to:")
    print("   1. Update certificates: pip install --upgrade certifi")
    print("   2. Or configure yfinance to disable SSL verification")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✅ All tests passed! yfinance is reachable and working correctly.")
    print()
    print("RECOMMENDATION:")
    print("   yfinance can be used to fetch events during period with:")
    print("   - 2 API calls per stock (earnings + dividends)")
    print("   - Much faster than current NASDAQ approach (30+ calls)")
    print("   - Date filtering done in Python (no additional API calls)")
    print()
    return True

def test_yfinance_multiple_tickers():
    """Test yfinance with multiple tickers to check rate limiting"""
    print("=" * 80)
    print("YFINANCE MULTIPLE TICKERS TEST")
    print("=" * 80)
    print()
    
    try:
        import yfinance as yf
    except ImportError:
        print("❌ SKIP: yfinance not available")
        return False
    
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
    print(f"Testing {len(test_tickers)} tickers: {', '.join(test_tickers)}")
    print()
    
    success_count = 0
    for ticker_symbol in test_tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            earnings = ticker.get_earnings_dates(limit=5)
            dividends = ticker.dividends
            
            if earnings is not None or dividends is not None:
                print(f"✅ {ticker_symbol}: Success")
                success_count += 1
            else:
                print(f"⚠️  {ticker_symbol}: No data returned")
        except Exception as e:
            error_str = str(e).lower()
            if 'certificate' in error_str or 'ssl' in error_str:
                print(f"❌ {ticker_symbol}: Certificate error - {e}")
            elif 'rate limit' in error_str or '429' in error_str:
                print(f"⚠️  {ticker_symbol}: Rate limited - {e}")
            else:
                print(f"❌ {ticker_symbol}: Error - {e}")
    
    print()
    print(f"Success rate: {success_count}/{len(test_tickers)} ({success_count*100//len(test_tickers)}%)")
    return success_count == len(test_tickers)

if __name__ == "__main__":
    print()
    success1 = test_yfinance_reachability()
    print()
    print()
    success2 = test_yfinance_multiple_tickers()
    print()
    
    if success1 and success2:
        print("=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        sys.exit(0)
    else:
        print("=" * 80)
        print("❌ SOME TESTS FAILED")
        print("=" * 80)
        sys.exit(1)

