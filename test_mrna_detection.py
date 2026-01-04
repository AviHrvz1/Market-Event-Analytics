#!/usr/bin/env python3
"""
Unit test to check if MRNA (Moderna) is correctly detected for -5% drop
between 3/1/2025 to 22/12/2025
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker

def test_mrna_detection():
    """Test if MRNA is detected for -5% drop in the specified date range"""
    print("=" * 80)
    print("MRNA DETECTION TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Test dates from user's query
    # User said: "dates between 3/1/2025 to 22/12/2025"
    # This likely means: bearish_date = 3/1/2025, target_date = 22/12/2025
    # But wait, that doesn't make sense - bearish date should be before target date
    # Let me interpret: they're looking for drops between Jan 3, 2025 and Dec 22, 2025
    # So bearish_date could be any date in that range, target_date = Dec 22, 2025
    
    # Based on the user's example showing Nov 3, 2025 as bearish date and Dec 22, 2025 as target date
    bearish_date = datetime(2025, 11, 3, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 22, tzinfo=timezone.utc)
    pct_threshold = -5.0  # -5% drop
    
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"Percentage Threshold: {pct_threshold}%")
    print()
    
    try:
        # Get bearish analytics
        results, logs = tracker.get_bearish_analytics(
            bearish_date=bearish_date,
            target_date=target_date,
            industry=None,  # All industries
            filter_type='bearish',
            pct_threshold=pct_threshold
        )
        
        print("=" * 80)
        print("SEARCH RESULTS")
        print("=" * 80)
        print()
        
            # Check if MRNA is in results
            mrna_found = False
            mrna_result = None
            
            # Check all stocks and their pct_change values
            print(f"\nTotal stocks in results: {len(results)}")
            print(f"Filter threshold: {pct_threshold}%")
            print()
            
            # Find MRNA and show all stocks with pct_change values
            mrna_in_results = False
            stocks_below_threshold = []
            stocks_above_threshold = []
            
            for stock in results:
                ticker = stock.get('ticker', 'N/A')
                pct_change = stock.get('pct_change', None)
                pct_drop = stock.get('pct_drop', None)
                
                if ticker == 'MRNA':
                    mrna_in_results = True
                    mrna_found = True
                    mrna_result = stock
                    print(f"*** MRNA FOUND in results ***")
                    print(f"  pct_change: {pct_change}")
                    print(f"  pct_drop: {pct_drop}")
                    print(f"  bearish_date: {stock.get('bearish_date', 'N/A')}")
                    print(f"  bearish_price: ${stock.get('bearish_price', 0):.2f}")
                    print(f"  Filter check: {pct_change} <= {pct_threshold} = {pct_change <= pct_threshold if pct_change is not None else 'N/A'}")
                    print()
                
                # Track stocks above/below threshold
                if pct_change is not None:
                    if pct_change <= pct_threshold:
                        stocks_below_threshold.append((ticker, pct_change))
                    else:
                        stocks_above_threshold.append((ticker, pct_change))
            
            if not mrna_in_results:
                print("❌ MRNA NOT in results")
                print()
                print(f"Stocks below threshold ({pct_threshold}%): {len(stocks_below_threshold)}")
                if len(stocks_below_threshold) > 0:
                    print("  First 5:")
                    for ticker, pct in stocks_below_threshold[:5]:
                        print(f"    {ticker}: {pct:.2f}%")
                print()
                print(f"Stocks above threshold ({pct_threshold}%): {len(stocks_above_threshold)}")
                if len(stocks_above_threshold) > 0:
                    print("  First 5:")
                    for ticker, pct in stocks_above_threshold[:5]:
                        print(f"    {ticker}: {pct:.2f}%")
                print()
            
            # Check again after filtering (results should already be filtered)
            for stock in results:
                if stock.get('ticker') == 'MRNA':
                    mrna_found = True
                    mrna_result = stock
                    break
        
        if mrna_found:
            print("✅ MRNA FOUND in results")
            print()
            print("MRNA Details:")
            print(f"  Company: {mrna_result.get('company_name', 'N/A')}")
            print(f"  Ticker: {mrna_result.get('ticker', 'N/A')}")
            print(f"  Industry: {mrna_result.get('industry', 'N/A')}")
            print(f"  Market Cap: ${mrna_result.get('market_cap', 0):,.2f}")
            print(f"  Bearish Date: {mrna_result.get('bearish_date', 'N/A')}")
            print(f"  Bearish Price: ${mrna_result.get('bearish_price', 0):.2f}")
            print(f"  PCT Drop: {mrna_result.get('pct_drop', 0):.2f}%")
            print(f"  Target Date: {mrna_result.get('target_date', 'N/A')}")
            print(f"  Target Price: ${mrna_result.get('target_price', 0):.2f}")
            print(f"  Recovery PCT: {mrna_result.get('recovery_pct', 0):.2f}%")
            print()
            
            # Check if it matches expected values
            expected_bearish_price = 24.91
            expected_target_price = 34.90
            expected_pct_drop = -8.28
            expected_recovery_pct = 40.10
            
            bearish_price = mrna_result.get('bearish_price', 0)
            target_price = mrna_result.get('target_price', 0)
            pct_drop = mrna_result.get('pct_drop', 0)
            recovery_pct = mrna_result.get('recovery_pct', 0)
            
            print("Expected vs Actual:")
            print(f"  Bearish Price: Expected ${expected_bearish_price:.2f}, Got ${bearish_price:.2f}")
            print(f"  Target Price: Expected ${expected_target_price:.2f}, Got ${target_price:.2f}")
            print(f"  PCT Drop: Expected {expected_pct_drop:.2f}%, Got {pct_drop:.2f}%")
            print(f"  Recovery PCT: Expected {expected_recovery_pct:.2f}%, Got {recovery_pct:.2f}%")
            print()
            
            # Check if values match (within tolerance)
            tolerance = 0.1
            price_match = abs(bearish_price - expected_bearish_price) < tolerance
            target_match = abs(target_price - expected_target_price) < tolerance
            drop_match = abs(pct_drop - expected_pct_drop) < tolerance
            recovery_match = abs(recovery_pct - expected_recovery_pct) < tolerance
            
            if price_match and target_match and drop_match and recovery_match:
                print("✅ All values match expected results!")
                return True
            else:
                print("⚠️  Some values don't match expected results")
                if not price_match:
                    print(f"   ❌ Bearish price mismatch")
                if not target_match:
                    print(f"   ❌ Target price mismatch")
                if not drop_match:
                    print(f"   ❌ Drop percentage mismatch")
                if not recovery_match:
                    print(f"   ❌ Recovery percentage mismatch")
                return True  # Still found, just values differ
        else:
            print("❌ MRNA NOT FOUND in results")
            print()
            print(f"Total stocks found: {len(results)}")
            print()
            
            # Show first few results for debugging
            if len(results) > 0:
                print("First 5 results:")
                for i, stock in enumerate(results[:5], 1):
                    print(f"  {i}. {stock.get('ticker', 'N/A')} - {stock.get('company_name', 'N/A')} - Drop: {stock.get('pct_drop', 0):.2f}%")
                print()
            
            # Check if MRNA is in the initial losers list (before filtering)
            print("Checking Prixe.io API directly...")
            try:
                losers = tracker.get_top_losers_prixe(bearish_date, industry=None)
                mrna_in_losers = any(l[0] == 'MRNA' for l in losers)
                
                if mrna_in_losers:
                    print("✅ MRNA found in Prixe.io losers list")
                    # Find MRNA in losers
                    for ticker, pct_change, company_info in losers:
                        if ticker == 'MRNA':
                            print(f"  MRNA PCT Change from Prixe.io: {pct_change:.2f}%")
                            print(f"  Company Info: {company_info}")
                            break
                else:
                    print("❌ MRNA NOT found in Prixe.io losers list")
                    print(f"  Total losers from Prixe.io: {len(losers)}")
                    if len(losers) > 0:
                        print("  First 5 losers:")
                        for i, (ticker, pct_change, _) in enumerate(losers[:5], 1):
                            print(f"    {i}. {ticker}: {pct_change:.2f}%")
            except Exception as e:
                print(f"⚠️  Error checking Prixe.io: {e}")
            
            return False
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mrna_detection()
    sys.exit(0 if success else 1)

