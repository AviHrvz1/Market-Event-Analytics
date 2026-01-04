#!/usr/bin/env python3
"""
Test to check Prixe.io API endpoints and see if yfinance can be used as fallback
Tests the actual endpoint being used and alternative endpoints
"""

import sys
from main import LayoffTracker
from config import PRIXE_API_KEY, PRIXE_BASE_URL

# Test tickers that are failing
TEST_TICKERS = ['GILD', 'NCOX', 'PLTN', 'IMMU', 'NMTR']

def test_prixe_via_tracker(ticker):
    """Test Prixe.io using the tracker's method"""
    try:
        tracker = LayoffTracker()
        
        # Check if ticker is available (this uses Prixe.io)
        is_available = tracker._is_ticker_available(ticker)
        
        if is_available:
            # Try to get actual price data
            from datetime import datetime, timedelta, timezone
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=5)
            
            # Use the tracker's method to get price
            try:
                price_data = tracker._get_prixe_price_data(ticker, start_date, end_date, '1d')
                if price_data:
                    return True, "Success via tracker", price_data
                else:
                    return False, "No data returned", None
            except Exception as e:
                return False, f"Error getting price: {str(e)[:80]}", None
        else:
            return False, "Ticker not available (404 or other error)", None
            
    except Exception as e:
        return False, f"Error: {str(e)[:80]}", None

def test_yfinance_simple(ticker):
    """Simple yfinance test"""
    try:
        import yfinance as yf
        
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if info and len(info) > 0:
            # Try to get recent price
            hist = stock.history(period="2d")
            if hist is not None and len(hist) > 0:
                last_price = float(hist['Close'].iloc[-1])
                return True, f"Success - Last price: ${last_price:.2f}", {
                    'price': last_price,
                    'company': info.get('longName') or info.get('shortName', 'N/A')
                }
            else:
                return True, "Info available but no history", {'info': info}
        else:
            return False, "No info available", None
            
    except ImportError:
        return False, "yfinance not installed", None
    except Exception as e:
        error_msg = str(e)
        if "No data found" in error_msg or "symbol" in error_msg.lower():
            return False, "Ticker not found", None
        return False, f"Error: {error_msg[:80]}", None

def test_prixe_endpoints():
    """Test different Prixe.io endpoints"""
    print("=" * 80)
    print("PRIXE.IO ENDPOINT & YFINANCE FALLBACK TEST")
    print("=" * 80)
    print()
    print(f"Testing tickers: {', '.join(TEST_TICKERS)}")
    print()
    
    results = []
    
    for ticker in TEST_TICKERS:
        print(f"Testing: {ticker}")
        print("-" * 80)
        
        # Test via tracker (uses actual Prixe.io integration)
        print("  Prixe.io (via tracker):")
        prixe_success, prixe_msg, prixe_data = test_prixe_via_tracker(ticker)
        if prixe_success:
            print(f"    ✅ {prixe_msg}")
        else:
            print(f"    ❌ {prixe_msg}")
        
        # Test yfinance
        print("  yfinance:")
        yf_success, yf_msg, yf_data = test_yfinance_simple(ticker)
        if yf_success:
            print(f"    ✅ {yf_msg}")
            if yf_data and 'company' in yf_data:
                print(f"    Company: {yf_data['company']}")
        else:
            print(f"    ❌ {yf_msg}")
        
        results.append({
            'ticker': ticker,
            'prixe_success': prixe_success,
            'prixe_msg': prixe_msg,
            'yfinance_success': yf_success,
            'yfinance_msg': yf_msg,
            'yfinance_data': yf_data
        })
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    prixe_count = sum(1 for r in results if r['prixe_success'])
    yfinance_count = sum(1 for r in results if r['yfinance_success'])
    
    print(f"Prixe.io available: {prixe_count}/{len(TEST_TICKERS)}")
    print(f"yfinance available: {yfinance_count}/{len(TEST_TICKERS)}")
    print()
    
    # Detailed results
    print("Detailed Results:")
    print()
    
    yfinance_fallback = []
    both_fail = []
    both_work = []
    
    for result in results:
        ticker = result['ticker']
        prixe_ok = result['prixe_success']
        yf_ok = result['yfinance_success']
        
        status = ""
        if prixe_ok and yf_ok:
            status = "✅ Both work"
            both_work.append(ticker)
        elif not prixe_ok and yf_ok:
            status = "✅ yfinance fallback available"
            yfinance_fallback.append(result)
        elif prixe_ok and not yf_ok:
            status = "✅ Prixe.io only"
        else:
            status = "❌ Neither works"
            both_fail.append(ticker)
        
        print(f"{ticker}: {status}")
        if not prixe_ok:
            print(f"  Prixe.io: {result['prixe_msg']}")
        if yf_ok:
            print(f"  yfinance: {result['yfinance_msg']}")
        print()
    
    # Recommendations
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    if yfinance_fallback:
        print(f"✅ {len(yfinance_fallback)} tickers can use yfinance as fallback:")
        for r in yfinance_fallback:
            print(f"   - {r['ticker']}: {r['yfinance_msg']}")
            if r['yfinance_data'] and 'company' in r['yfinance_data']:
                print(f"     Company: {r['yfinance_data']['company']}")
        print()
        print("💡 Recommendation: Add yfinance fallback for Prixe.io 404 errors")
    else:
        print("⚠️  No tickers available in yfinance that Prixe.io cannot find")
    
    if both_fail:
        print(f"❌ {len(both_fail)} tickers not available in either service:")
        for ticker in both_fail:
            print(f"   - {ticker}")
        print()
        print("💡 These tickers may be:")
        print("   - Delisted or merged")
        print("   - Private companies")
        print("   - Invalid ticker symbols")
    
    if both_work:
        print(f"✅ {len(both_work)} tickers work in both services:")
        for ticker in both_work:
            print(f"   - {ticker}")
    
    return True

if __name__ == '__main__':
    success = test_prixe_endpoints()
    sys.exit(0 if success else 1)

