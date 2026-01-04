#!/usr/bin/env python3
"""
Unit test to verify if JNJ stock price data is real
Tests Prixe.io and yfinance for Johnson & Johnson (JNJ) on Mar 11, 2025
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import PRIXE_API_KEY, PRIXE_BASE_URL, PRIXE_PRICE_ENDPOINT

# Test data from UI
TEST_DATA = {
    'company': 'Johnson & Johnson',
    'ticker': 'JNJ',
    'article_date': '2025-03-10 03:00:00',  # Mon, Mar 10, 2025 03:00
    'expected_close_date': '2025-03-11',  # Tue, Mar 11, 2025
    'expected_close_price': 162.22,
    'expected_change_pct': -1.10
}

def test_prixe_jnj(ticker, date_str):
    """Test Prixe.io for JNJ on specific date"""
    print(f"Testing Prixe.io for {ticker} on {date_str}")
    print("-" * 80)
    
    try:
        tracker = LayoffTracker()
        
        # Parse date
        target_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        start_date = target_date - timedelta(days=1)
        end_date = target_date + timedelta(days=1)
        
        # Try to get daily data
        payload = {
            'ticker': ticker,
            'start_date': date_str,
            'end_date': date_str,
            'interval': '1d'
        }
        
        print(f"  Endpoint: {PRIXE_BASE_URL}{PRIXE_PRICE_ENDPOINT}")
        print(f"  Payload: {payload}")
        
        response = tracker._prixe_api_request('/api/price', payload)
        
        if response:
            if response.get('success') and 'data' in response:
                data = response['data']
                print(f"  ✅ SUCCESS: Got data from Prixe.io")
                print(f"  Data structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                
                # Try to extract close price
                if isinstance(data, dict):
                    if 'close' in data:
                        closes = data['close']
                        if closes and len(closes) > 0:
                            close_price = float(closes[-1]) if isinstance(closes, list) else float(closes)
                            print(f"  Close price: ${close_price:.2f}")
                            return True, close_price, data
                    elif 'data' in data:
                        # Nested data structure
                        nested = data['data']
                        if isinstance(nested, list) and len(nested) > 0:
                            last = nested[-1]
                            if isinstance(last, dict) and 'close' in last:
                                close_price = float(last['close'])
                                print(f"  Close price: ${close_price:.2f}")
                                return True, close_price, data
                elif isinstance(data, list) and len(data) > 0:
                    last = data[-1]
                    if isinstance(last, dict) and 'close' in last:
                        close_price = float(last['close'])
                        print(f"  Close price: ${close_price:.2f}")
                        return True, close_price, data
                
                print(f"  ⚠️  Got data but couldn't extract close price")
                print(f"  Full response: {str(response)[:500]}")
                return True, None, data
            else:
                print(f"  ❌ Response indicates failure: {response}")
                return False, None, response
        else:
            print(f"  ❌ No response from Prixe.io (likely 404 or error)")
            return False, None, None
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False, None, None

def test_yfinance_jnj(ticker, date_str):
    """Test yfinance for JNJ on specific date"""
    print(f"Testing yfinance for {ticker} on {date_str}")
    print("-" * 80)
    
    try:
        import yfinance as yf
        
        stock = yf.Ticker(ticker)
        
        # Get info to verify ticker exists
        info = stock.info
        if not info or len(info) == 0:
            print(f"  ❌ Ticker {ticker} not found in yfinance")
            return False, None, None
        
        company_name = info.get('longName') or info.get('shortName', 'N/A')
        print(f"  ✅ Ticker found: {company_name}")
        
        # Get historical data for the date
        # yfinance needs date range
        from datetime import datetime as dt
        target_date = dt.strptime(date_str, '%Y-%m-%d')
        start_date = target_date - timedelta(days=5)
        end_date = target_date + timedelta(days=2)
        
        hist = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        
        if hist is None or len(hist) == 0:
            print(f"  ❌ No historical data for {date_str}")
            return False, None, None
        
        # Find data for the target date
        target_date_only = target_date.date()
        matching_dates = hist[hist.index.date == target_date_only]
        
        if len(matching_dates) > 0:
            close_price = float(matching_dates['Close'].iloc[-1])
            open_price = float(matching_dates['Open'].iloc[0])
            change_pct = ((close_price - open_price) / open_price) * 100
            
            print(f"  ✅ Found data for {date_str}")
            print(f"  Close price: ${close_price:.2f}")
            print(f"  Open price: ${open_price:.2f}")
            print(f"  Change: {change_pct:.2f}%")
            
            return True, close_price, {
                'close': close_price,
                'open': open_price,
                'change_pct': change_pct,
                'company': company_name
            }
        else:
            # Try to get closest date
            print(f"  ⚠️  No exact match for {date_str}, checking nearby dates...")
            print(f"  Available dates: {[str(d.date()) for d in hist.index[:5]]}")
            
            # Get closest date
            closest_idx = hist.index.get_indexer([target_date], method='nearest')[0]
            closest_date = hist.index[closest_idx]
            close_price = float(hist['Close'].iloc[closest_idx])
            
            print(f"  Closest date: {closest_date.date()}")
            print(f"  Close price: ${close_price:.2f}")
            
            return True, close_price, {
                'close': close_price,
                'date': closest_date.date(),
                'company': company_name
            }
            
    except ImportError:
        print(f"  ❌ yfinance not installed")
        return False, None, None
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False, None, None

def test_jnj_verification():
    """Verify JNJ price data"""
    
    print("=" * 80)
    print("JNJ STOCK PRICE VERIFICATION")
    print("=" * 80)
    print()
    
    ticker = TEST_DATA['ticker']
    date_str = TEST_DATA['expected_close_date']
    expected_price = TEST_DATA['expected_close_price']
    expected_change = TEST_DATA['expected_change_pct']
    
    print(f"Company: {TEST_DATA['company']}")
    print(f"Ticker: {ticker}")
    print(f"Article Date: {TEST_DATA['article_date']}")
    print(f"Expected Close Date: {date_str}")
    print(f"Expected Close Price: ${expected_price:.2f}")
    print(f"Expected Change: {expected_change:.2f}%")
    print()
    
    # Test Prixe.io
    print("=" * 80)
    print("TEST 1: Prixe.io")
    print("=" * 80)
    print()
    
    prixe_ok, prixe_price, prixe_data = test_prixe_jnj(ticker, date_str)
    print()
    
    # Test yfinance
    print("=" * 80)
    print("TEST 2: yfinance")
    print("=" * 80)
    print()
    
    yf_ok, yf_price, yf_data = test_yfinance_jnj(ticker, date_str)
    print()
    
    # Verification
    print("=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print()
    
    print(f"Expected Price: ${expected_price:.2f}")
    print()
    
    if prixe_ok and prixe_price:
        diff = abs(prixe_price - expected_price)
        match = diff < 0.01  # Allow small rounding differences
        status = "✅ MATCH" if match else f"❌ MISMATCH (diff: ${diff:.2f})"
        print(f"Prixe.io: {status}")
        print(f"  Price: ${prixe_price:.2f}")
        if not match:
            print(f"  Difference: ${diff:.2f}")
    elif prixe_ok:
        print(f"Prixe.io: ⚠️  Got data but couldn't extract price")
    else:
        print(f"Prixe.io: ❌ No data available (404 or error)")
    
    print()
    
    if yf_ok and yf_price:
        diff = abs(yf_price - expected_price)
        match = diff < 0.01
        status = "✅ MATCH" if match else f"❌ MISMATCH (diff: ${diff:.2f})"
        print(f"yfinance: {status}")
        print(f"  Price: ${yf_price:.2f}")
        if not match:
            print(f"  Difference: ${diff:.2f}")
        if yf_data and 'change_pct' in yf_data:
            print(f"  Change: {yf_data['change_pct']:.2f}%")
    else:
        print(f"yfinance: ❌ No data available")
    
    print()
    
    # Final verdict
    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    print()
    
    if prixe_ok and prixe_price:
        if abs(prixe_price - expected_price) < 0.01:
            print("✅ VERIFIED: Price data is REAL (matches Prixe.io)")
        else:
            print("⚠️  PRICE MISMATCH: Prixe.io shows different price")
    elif yf_ok and yf_price:
        if abs(yf_price - expected_price) < 0.01:
            print("✅ VERIFIED: Price data is REAL (matches yfinance)")
        else:
            print("⚠️  PRICE MISMATCH: yfinance shows different price")
    else:
        print("❌ CANNOT VERIFY: Neither Prixe.io nor yfinance returned data")
        print("   This could mean:")
        print("   - Ticker doesn't exist")
        print("   - Date is in the future (Mar 11, 2025)")
        print("   - API errors")
    
    print()
    
    # Date verification
    print("=" * 80)
    print("DATE VERIFICATION")
    print("=" * 80)
    print()
    
    article_date = datetime.strptime(TEST_DATA['article_date'], '%Y-%m-%d %H:%M:%S')
    close_date = datetime.strptime(date_str, '%Y-%m-%d')
    
    print(f"Article published: {article_date.strftime('%A, %b %d, %Y %H:%M')}")
    print(f"Expected close: {close_date.strftime('%A, %b %d, %Y')}")
    
    # Check if article was published when market was closed
    if article_date.hour < 9 or article_date.hour >= 16:
        print(f"  ✅ Market was CLOSED when article published")
        print(f"  ✅ Next trading day close is correct: {close_date.strftime('%A, %b %d, %Y')}")
    else:
        print(f"  ⚠️  Market was OPEN when article published")
        print(f"  ⚠️  Close date should be same day or next day")
    
    # Check if date is in future
    now = datetime.now(timezone.utc)
    today = now.date()
    close_date_only = close_date.date()
    
    print(f"  Today's date: {today.strftime('%Y-%m-%d')}")
    print(f"  Close date: {close_date_only.strftime('%Y-%m-%d')}")
    
    if close_date_only > today:
        days_ahead = (close_date_only - today).days
        print(f"  ❌ CRITICAL: Close date is {days_ahead} days in the FUTURE")
        print(f"  ❌ Cannot verify future prices - this data is NOT REAL")
        print(f"  ❌ Price ${expected_price:.2f} for {date_str} cannot be verified (date hasn't happened yet)")
        print()
        print("  Possible explanations:")
        print("    1. System date is incorrect")
        print("    2. Data is simulated/projected")
        print("    3. Date parsing error in article")
        print("    4. Historical data shown for wrong date")
    elif close_date_only == today:
        print(f"  ⚠️  Close date is TODAY - may not have closing price yet")
    else:
        days_ago = (today - close_date_only).days
        print(f"  ✅ Close date is {days_ago} days in the PAST - can verify")
    
    return True

if __name__ == '__main__':
    success = test_jnj_verification()
    sys.exit(0 if success else 1)

