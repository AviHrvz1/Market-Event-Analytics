#!/usr/bin/env python3
"""
Unit test to verify BKNG (Booking Holdings Inc) data in Bearish Analytics
Tests the specific data shown in UI:
- Company: Booking Holdings Inc
- Ticker: BKNG
- Industry: Consumer
- Bearish Date Price: $4948.93
- % Drop: -7.90%
- Target Date Price: $5038.37
- Recovery %: +1.81%
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_bkng_data_verification():
    """Verify BKNG data matches expected values from UI"""
    print("=" * 80)
    print("BKNG DATA VERIFICATION TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # IMPORTANT: Update these dates to match the dates you used in the UI query!
    # You can find the dates in the UI by looking at the "Bearish Date" and "Target Date" fields
    # Format: datetime(year, month, day, tzinfo=timezone.utc)
    
    # Example: If you used Dec 8, 2025 as bearish date and Dec 22, 2025 as target date:
    # bearish_date = datetime(2025, 12, 8, tzinfo=timezone.utc)
    # target_date = datetime(2025, 12, 22, tzinfo=timezone.utc)
    
    # For now, using default dates (update these to match your UI query):
    today = datetime.now(timezone.utc)
    bearish_date = today - timedelta(days=30)
    target_date = today - timedelta(days=14)
    
    # Alternative: Uncomment and set specific dates if you know them:
    # bearish_date = datetime(2025, 12, 8, tzinfo=timezone.utc)  # Update to your bearish date
    # target_date = datetime(2025, 12, 22, tzinfo=timezone.utc)  # Update to your target date
    
    print(f"Testing with dates:")
    print(f"  Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"  Target Date:  {target_date.strftime('%Y-%m-%d')}")
    print()
    print("⚠️  NOTE: If these dates don't match your UI query, please update them in the test")
    print()
    
    # Expected values from UI
    expected_data = {
        'company_name': 'Booking Holdings Inc',
        'ticker': 'BKNG',
        'industry': 'Consumer',
        'bearish_price': 4948.93,
        'pct_drop': -7.90,
        'target_price': 5038.37,
        'recovery_pct': 1.81
    }
    
    print("Expected values from UI:")
    print(f"  Company: {expected_data['company_name']}")
    print(f"  Ticker: {expected_data['ticker']}")
    print(f"  Industry: {expected_data['industry']}")
    print(f"  Bearish Date Price: ${expected_data['bearish_price']:.2f}")
    print(f"  % Drop: {expected_data['pct_drop']:.2f}%")
    print(f"  Target Date Price: ${expected_data['target_price']:.2f}")
    print(f"  Recovery %: {expected_data['recovery_pct']:.2f}%")
    print()
    
    print("Fetching bearish analytics data...")
    print()
    
    try:
        # Get bearish analytics
        results, logs = tracker.get_bearish_analytics(bearish_date, target_date, industry=None)
        
        # Find BKNG in results
        bkng_result = None
        for result in results:
            if result.get('ticker') == 'BKNG':
                bkng_result = result
                break
        
        if not bkng_result:
            print("❌ BKNG not found in results")
            print(f"   Found {len(results)} stocks total")
            if len(results) > 0:
                print("   Available tickers:", [r.get('ticker') for r in results[:10]])
            return False
        
        print("✅ BKNG found in results")
        print()
        
        # Verify each field
        print("=" * 80)
        print("DATA VERIFICATION")
        print("=" * 80)
        print()
        
        all_match = True
        tolerance = 0.01  # Allow 1 cent tolerance for prices, 0.01% for percentages
        
        # Check company name
        actual_company = bkng_result.get('company_name', '')
        expected_company = expected_data['company_name']
        if actual_company == expected_company:
            print(f"✅ Company Name: {actual_company}")
        else:
            print(f"❌ Company Name: Expected '{expected_company}', got '{actual_company}'")
            all_match = False
        
        # Check ticker
        actual_ticker = bkng_result.get('ticker', '')
        expected_ticker = expected_data['ticker']
        if actual_ticker == expected_ticker:
            print(f"✅ Ticker: {actual_ticker}")
        else:
            print(f"❌ Ticker: Expected '{expected_ticker}', got '{actual_ticker}'")
            all_match = False
        
        # Check industry
        actual_industry = bkng_result.get('industry', '')
        expected_industry = expected_data['industry']
        if actual_industry == expected_industry:
            print(f"✅ Industry: {actual_industry}")
        else:
            print(f"❌ Industry: Expected '{expected_industry}', got '{actual_industry}'")
            all_match = False
        
        # Check bearish price
        actual_bearish_price = bkng_result.get('bearish_price', 0)
        expected_bearish_price = expected_data['bearish_price']
        diff_bearish = abs(actual_bearish_price - expected_bearish_price)
        if diff_bearish <= tolerance:
            print(f"✅ Bearish Date Price: ${actual_bearish_price:.2f} (expected ${expected_bearish_price:.2f})")
        else:
            print(f"❌ Bearish Date Price: ${actual_bearish_price:.2f} (expected ${expected_bearish_price:.2f}, diff: ${diff_bearish:.2f})")
            all_match = False
        
        # Check % drop
        actual_pct_drop = bkng_result.get('pct_drop', 0)
        expected_pct_drop = expected_data['pct_drop']
        diff_pct_drop = abs(actual_pct_drop - expected_pct_drop)
        if diff_pct_drop <= tolerance:
            print(f"✅ % Drop: {actual_pct_drop:.2f}% (expected {expected_pct_drop:.2f}%)")
        else:
            print(f"❌ % Drop: {actual_pct_drop:.2f}% (expected {expected_pct_drop:.2f}%, diff: {diff_pct_drop:.2f}%)")
            all_match = False
        
        # Check target price
        actual_target_price = bkng_result.get('target_price', 0)
        expected_target_price = expected_data['target_price']
        diff_target = abs(actual_target_price - expected_target_price)
        if diff_target <= tolerance:
            print(f"✅ Target Date Price: ${actual_target_price:.2f} (expected ${expected_target_price:.2f})")
        else:
            print(f"❌ Target Date Price: ${actual_target_price:.2f} (expected ${expected_target_price:.2f}, diff: ${diff_target:.2f})")
            all_match = False
        
        # Check recovery %
        actual_recovery_pct = bkng_result.get('recovery_pct', 0)
        expected_recovery_pct = expected_data['recovery_pct']
        diff_recovery = abs(actual_recovery_pct - expected_recovery_pct)
        if diff_recovery <= tolerance:
            print(f"✅ Recovery %: {actual_recovery_pct:.2f}% (expected {expected_recovery_pct:.2f}%)")
        else:
            print(f"❌ Recovery %: {actual_recovery_pct:.2f}% (expected {expected_recovery_pct:.2f}%, diff: {diff_recovery:.2f}%)")
            all_match = False
        
        print()
        print("=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)
        print()
        
        if all_match:
            print("✅ ALL DATA MATCHES EXPECTED VALUES!")
            print()
            print("The BKNG data in the UI is correct.")
        else:
            print("❌ SOME DATA DOES NOT MATCH")
            print()
            print("Please check the differences above.")
            print("This could be due to:")
            print("  1. Different dates used in the test vs UI")
            print("  2. Data updates/changes")
            print("  3. Calculation differences")
        
        print()
        
        # Show full result for debugging
        print("=" * 80)
        print("FULL BKNG RESULT DATA")
        print("=" * 80)
        print()
        import json
        print(json.dumps(bkng_result, indent=2, default=str))
        print()
        
        return all_match
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify BKNG data from Bearish Analytics')
    parser.add_argument('--bearish-date', type=str, help='Bearish date in YYYY-MM-DD format (e.g., 2025-12-08)')
    parser.add_argument('--target-date', type=str, help='Target date in YYYY-MM-DD format (e.g., 2025-12-22)')
    args = parser.parse_args()
    
    # Override dates if provided via command line
    if args.bearish_date and args.target_date:
        try:
            bearish_date = datetime.strptime(args.bearish_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            target_date = datetime.strptime(args.target_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            print()
            print("🔍 BKNG Data Verification Test")
            print()
            print(f"Using provided dates:")
            print(f"  Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
            print(f"  Target Date:  {target_date.strftime('%Y-%m-%d')}")
            print()
            
            # Modify the function to accept dates
            tracker = LayoffTracker()
            results, logs = tracker.get_bearish_analytics(bearish_date, target_date, industry=None)
            
            bkng_result = None
            for result in results:
                if result.get('ticker') == 'BKNG':
                    bkng_result = result
                    break
            
            if not bkng_result:
                print("❌ BKNG not found in results")
                sys.exit(1)
            
            print("✅ BKNG found!")
            print()
            print("Actual values:")
            print(f"  Bearish Price: ${bkng_result.get('bearish_price', 0):.2f}")
            print(f"  % Drop: {bkng_result.get('pct_drop', 0):.2f}%")
            print(f"  Target Price: ${bkng_result.get('target_price', 0):.2f}")
            print(f"  Recovery %: {bkng_result.get('recovery_pct', 0):.2f}%")
            print()
            print("Expected values (from UI):")
            print(f"  Bearish Price: $4948.93")
            print(f"  % Drop: -7.90%")
            print(f"  Target Price: $5038.37")
            print(f"  Recovery %: +1.81%")
            print()
            
            # Verify
            tolerance = 0.01
            all_match = True
            
            if abs(bkng_result.get('bearish_price', 0) - 4948.93) > tolerance:
                print(f"❌ Bearish Price mismatch: ${bkng_result.get('bearish_price', 0):.2f} vs $4948.93")
                all_match = False
            else:
                print("✅ Bearish Price matches")
            
            if abs(bkng_result.get('pct_drop', 0) - (-7.90)) > tolerance:
                print(f"❌ % Drop mismatch: {bkng_result.get('pct_drop', 0):.2f}% vs -7.90%")
                all_match = False
            else:
                print("✅ % Drop matches")
            
            if abs(bkng_result.get('target_price', 0) - 5038.37) > tolerance:
                print(f"❌ Target Price mismatch: ${bkng_result.get('target_price', 0):.2f} vs $5038.37")
                all_match = False
            else:
                print("✅ Target Price matches")
            
            if abs(bkng_result.get('recovery_pct', 0) - 1.81) > tolerance:
                print(f"❌ Recovery % mismatch: {bkng_result.get('recovery_pct', 0):.2f}% vs +1.81%")
                all_match = False
            else:
                print("✅ Recovery % matches")
            
            sys.exit(0 if all_match else 1)
        except ValueError as e:
            print(f"❌ Invalid date format: {e}")
            print("   Use YYYY-MM-DD format (e.g., 2025-12-08)")
            sys.exit(1)
    
    print()
    print("🔍 BKNG Data Verification Test")
    print()
    print("This test verifies that the BKNG data shown in the UI matches")
    print("the calculated values from the backend.")
    print()
    print("⚠️  IMPORTANT: You need to provide the dates you used in the UI!")
    print()
    print("Usage:")
    print("  python3 test_bkng_data_verification.py --bearish-date 2025-12-08 --target-date 2025-12-22")
    print()
    print("Or update the dates in the test file directly.")
    print()
    
    success = test_bkng_data_verification()
    sys.exit(0 if success else 1)

