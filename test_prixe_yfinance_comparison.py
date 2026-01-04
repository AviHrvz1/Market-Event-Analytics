#!/usr/bin/env python3
"""
Test to compare Prixe.io vs yfinance for tickers that return 404
Shows which endpoint Prixe.io uses and if yfinance can find the tickers
"""

import sys
from main import LayoffTracker
from config import PRIXE_API_KEY, PRIXE_BASE_URL, PRIXE_PRICE_ENDPOINT

# Test tickers that are failing in Prixe.io
TEST_TICKERS = ['GILD', 'NCOX', 'PLTN', 'IMMU', 'NMTR']

def test_prixe_via_tracker_method(ticker):
    """Test using tracker's actual methods"""
    try:
        tracker = LayoffTracker()
        
        # Check what endpoint is used
        print(f"  Prixe.io endpoint: {PRIXE_BASE_URL}{PRIXE_PRICE_ENDPOINT}")
        
        # Test _is_ticker_available (this checks cache, not API)
        is_available = tracker._is_ticker_available(ticker)
        
        if not is_available:
            # Check why it's not available
            if ticker.upper() in tracker.invalid_tickers:
                return False, "In invalid_tickers cache", None
            elif ticker.upper() in tracker.failed_tickers:
                return False, "In failed_tickers cache (previous 404)", None
            else:
                return False, "Not available (unknown reason)", None
        
        # Try to get price data using tracker's method
        from datetime import datetime, timedelta, timezone
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=5)
        
        # Use the actual method from tracker
        try:
            # Check what method is used to get price data
            price_data = tracker._get_prixe_price_data(ticker, start_date, end_date, '1d')
            if price_data:
                return True, "Success - got price data", price_data
            else:
                return False, "No price data returned", None
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                return False, "404 - Endpoint or ticker not found", None
            return False, f"Error: {error_msg[:80]}", None
            
    except Exception as e:
        return False, f"Exception: {str(e)[:80]}", None

def test_yfinance_detailed(ticker):
    """Detailed yfinance test"""
    try:
        import yfinance as yf
        
        stock = yf.Ticker(ticker)
        
        # Get info
        info = stock.info
        
        if not info or len(info) == 0:
            return False, "No info available", None
        
        # Get history
        hist = stock.history(period="5d")
        
        if hist is None or len(hist) == 0:
            return False, "No history available", {'info': info}
        
        # Extract data
        last_price = float(hist['Close'].iloc[-1])
        company_name = info.get('longName') or info.get('shortName') or 'N/A'
        market_cap = info.get('marketCap', 'N/A')
        exchange = info.get('exchange', 'N/A')
        
        return True, f"Success - Price: ${last_price:.2f}", {
            'price': last_price,
            'company': company_name,
            'market_cap': market_cap,
            'exchange': exchange,
            'data_points': len(hist)
        }
        
    except ImportError:
        return False, "yfinance not installed", None
    except Exception as e:
        error_msg = str(e)
        if "No data found" in error_msg or "symbol" in error_msg.lower():
            return False, "Ticker not found in yfinance", None
        return False, f"Error: {error_msg[:80]}", None

def test_comparison():
    """Compare Prixe.io vs yfinance"""
    
    print("=" * 80)
    print("PRIXE.IO vs YFINANCE COMPARISON")
    print("=" * 80)
    print()
    print(f"Prixe.io Endpoint: {PRIXE_BASE_URL}{PRIXE_PRICE_ENDPOINT}")
    print(f"Method: POST")
    print()
    print(f"Testing tickers: {', '.join(TEST_TICKERS)}")
    print()
    
    results = []
    
    for ticker in TEST_TICKERS:
        print(f"Ticker: {ticker}")
        print("-" * 80)
        
        # Test Prixe.io
        prixe_ok, prixe_msg, prixe_data = test_prixe_via_tracker_method(ticker)
        print(f"  Prixe.io: {'✅' if prixe_ok else '❌'} {prixe_msg}")
        
        # Test yfinance
        yf_ok, yf_msg, yf_data = test_yfinance_detailed(ticker)
        print(f"  yfinance: {'✅' if yf_ok else '❌'} {yf_msg}")
        if yf_ok and yf_data:
            print(f"    Company: {yf_data.get('company', 'N/A')}")
            if yf_data.get('price'):
                print(f"    Price: ${yf_data['price']:.2f}")
            if yf_data.get('exchange') != 'N/A':
                print(f"    Exchange: {yf_data['exchange']}")
        
        results.append({
            'ticker': ticker,
            'prixe_ok': prixe_ok,
            'prixe_msg': prixe_msg,
            'yfinance_ok': yf_ok,
            'yfinance_msg': yf_msg,
            'yfinance_data': yf_data
        })
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    prixe_count = sum(1 for r in results if r['prixe_ok'])
    yfinance_count = sum(1 for r in results if r['yfinance_ok'])
    
    print(f"Prixe.io: {prixe_count}/{len(TEST_TICKERS)} tickers available")
    print(f"yfinance: {yfinance_count}/{len(TEST_TICKERS)} tickers available")
    print()
    
    # Find tickers where yfinance works but Prixe.io doesn't
    yfinance_fallback = [r for r in results if not r['prixe_ok'] and r['yfinance_ok']]
    
    if yfinance_fallback:
        print(f"✅ {len(yfinance_fallback)} tickers available in yfinance (can use as fallback):")
        for r in yfinance_fallback:
            print(f"   {r['ticker']}: {r['yfinance_msg']}")
            if r['yfinance_data']:
                print(f"      Company: {r['yfinance_data'].get('company', 'N/A')}")
                if r['yfinance_data'].get('price'):
                    print(f"      Price: ${r['yfinance_data']['price']:.2f}")
        print()
        print("💡 RECOMMENDATION: Use yfinance as fallback when Prixe.io returns 404")
    else:
        print("⚠️  No tickers found in yfinance that Prixe.io cannot find")
        print()
        print("Possible reasons:")
        print("  - Tickers may be delisted/merged")
        print("  - Tickers may be invalid")
        print("  - Prixe.io endpoint may be incorrect")
        print("  - yfinance may also not have these tickers")
    
    # Show Prixe.io endpoint info
    print()
    print("=" * 80)
    print("PRIXE.IO ENDPOINT INFO")
    print("=" * 80)
    print()
    print(f"Base URL: {PRIXE_BASE_URL}")
    print(f"Endpoint: {PRIXE_PRICE_ENDPOINT}")
    print(f"Full URL: {PRIXE_BASE_URL}{PRIXE_PRICE_ENDPOINT}")
    print(f"Method: POST")
    print()
    print("If getting 404 errors, possible issues:")
    print("  1. Endpoint may have changed (check Prixe.io documentation)")
    print("  2. Tickers may not exist in Prixe.io database")
    print("  3. API key may not have access to these tickers")
    print()
    
    return True

if __name__ == '__main__':
    success = test_comparison()
    sys.exit(0 if success else 1)

