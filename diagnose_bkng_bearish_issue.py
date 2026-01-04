#!/usr/bin/env python3
"""
Diagnostic script to understand why BKNG appears as a "top loser" on Nov 10, 2025
when the price data shows it actually increased from previous days.
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def diagnose_bkng_issue():
    print("=" * 80)
    print("BKNG BEARISH ANALYTICS DIAGNOSIS")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    bearish_date = datetime(2025, 11, 10, tzinfo=timezone.utc)
    
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d (%A)')}")
    print()
    
    # Check Prixe.io data
    print("=" * 80)
    print("PRIXE.IO DATA (what we use for final prices)")
    print("=" * 80)
    print()
    
    price_history = tracker.get_stock_price_history('BKNG', bearish_date - timedelta(days=7), bearish_date)
    if price_history:
        print("Price History from Prixe.io:")
        for entry in price_history:
            date_str = entry.get('date')
            price = entry.get('price', 0)
            print(f"  {date_str}: ${price:.2f}")
        
        # Find Nov 10 price
        nov10_entry = next((e for e in price_history if e.get('date') == '2025-11-10'), None)
        if nov10_entry:
            nov10_price = nov10_entry.get('price')
            print()
            print(f"Nov 10 price: ${nov10_price:.2f}")
            
            # Compare to previous days
            print()
            print("Comparison to previous days:")
            for entry in price_history:
                date_str = entry.get('date')
                price = entry.get('price', 0)
                if date_str < '2025-11-10':
                    pct_change = ((nov10_price - price) / price) * 100
                    print(f"  {date_str}: ${price:.2f} → Nov 10: ${nov10_price:.2f} = {pct_change:+.2f}%")
    
    print()
    print("=" * 80)
    print("YFINANCE DATA (what we use to identify top losers)")
    print("=" * 80)
    print()
    
    try:
        import yfinance as yf
        
        # Get previous trading day (look back up to 5 days)
        prev_date = bearish_date - timedelta(days=5)
        start_date = prev_date.date()
        end_date = (bearish_date + timedelta(days=1)).date()
        
        print(f"Fetching yfinance data from {start_date} to {end_date}...")
        print()
        
        ticker = yf.Ticker('BKNG')
        data = ticker.history(start=start_date, end=end_date)
        
        if data is not None and not data.empty:
            print("yfinance Historical Data:")
            print(data[['Close']].to_string())
            print()
            
            # Find bearish date and previous day
            bearish_date_only = bearish_date.date()
            bearish_close = None
            prev_close = None
            
            for date_idx, row in data.iterrows():
                if hasattr(date_idx, 'date'):
                    date_only = date_idx.date()
                elif hasattr(date_idx, 'to_pydatetime'):
                    date_only = date_idx.to_pydatetime().date()
                else:
                    try:
                        date_only = datetime.fromtimestamp(date_idx).date()
                    except:
                        continue
                
                close_price = float(row['Close'])
                
                if date_only == bearish_date_only:
                    bearish_close = close_price
                    print(f"✅ Found bearish date ({date_only}): ${bearish_close:.2f}")
                elif date_only < bearish_date_only:
                    if prev_close is None:
                        prev_close = close_price
                        print(f"✅ Found previous trading day ({date_only}): ${prev_close:.2f}")
            
            if bearish_close is not None and prev_close is not None:
                pct_drop = ((bearish_close - prev_close) / prev_close) * 100
                print()
                print(f"Calculated % Drop: {pct_drop:.2f}%")
                print()
                print(f"Previous day ({prev_date.strftime('%Y-%m-%d')}): ${prev_close:.2f}")
                print(f"Bearish day (Nov 10): ${bearish_close:.2f}")
                print(f"Change: {pct_drop:+.2f}%")
                print()
                
                if pct_drop >= 0:
                    print("⚠️  ISSUE: yfinance shows a POSITIVE change, not a drop!")
                    print("   BKNG should NOT be in the top losers list.")
                else:
                    print(f"✅ yfinance shows a drop of {pct_drop:.2f}%")
                    print()
                    print("⚠️  DISCREPANCY: yfinance data differs from Prixe.io data!")
                    print(f"   Prixe.io Nov 10: ${nov10_price:.2f}")
                    print(f"   yfinance Nov 10: ${bearish_close:.2f}")
                    print(f"   Difference: ${abs(nov10_price - bearish_close):.2f}")
            else:
                print("❌ Could not find both dates in yfinance data")
                print(f"   Bearish close: {bearish_close}")
                print(f"   Previous close: {prev_close}")
        else:
            print("❌ No yfinance data returned")
            
    except ImportError:
        print("❌ yfinance not available")
    except Exception as e:
        print(f"❌ Error fetching yfinance data: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()
    print("The issue is that BKNG appears as a 'top loser' on Nov 10, 2025,")
    print("but the actual price data shows it INCREASED from previous days.")
    print()
    print("Possible causes:")
    print("1. yfinance data differs from Prixe.io data (data source mismatch)")
    print("2. The -7.90% drop is comparing to a much earlier date (not representative)")
    print("3. Date/timezone handling issues")
    print()
    print("Recommendation:")
    print("- Use Prixe.io data for BOTH identifying losers AND final prices")
    print("- OR verify yfinance data matches Prixe.io before including stocks")

if __name__ == "__main__":
    diagnose_bkng_issue()

