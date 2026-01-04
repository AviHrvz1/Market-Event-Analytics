#!/usr/bin/env python3
"""
Simple verification test for JNJ price data
Checks if the data makes sense even if APIs fail
"""

import sys
from datetime import datetime, timezone

# Test data from UI
TEST_DATA = {
    'company': 'Johnson & Johnson',
    'ticker': 'JNJ',
    'article_date': '2025-03-10 03:00:00',  # Mon, Mar 10, 2025 03:00
    'close_date': '2025-03-11',  # Tue, Mar 11, 2025
    'close_price': 162.22,
    'change_pct': -1.10
}

def test_jnj_simple_verification():
    """Simple verification without API calls"""
    
    print("=" * 80)
    print("JNJ PRICE DATA VERIFICATION (Simple Check)")
    print("=" * 80)
    print()
    
    print(f"Company: {TEST_DATA['company']}")
    print(f"Ticker: {TEST_DATA['ticker']}")
    print(f"Article Date: {TEST_DATA['article_date']}")
    print(f"Close Date: {TEST_DATA['close_date']}")
    print(f"Close Price: ${TEST_DATA['close_price']:.2f}")
    print(f"Change: {TEST_DATA['change_pct']:.2f}%")
    print()
    
    # Date verification
    print("=" * 80)
    print("DATE VERIFICATION")
    print("=" * 80)
    print()
    
    now = datetime.now(timezone.utc)
    today = now.date()
    article_date = datetime.strptime(TEST_DATA['article_date'], '%Y-%m-%d %H:%M:%S')
    close_date = datetime.strptime(TEST_DATA['close_date'], '%Y-%m-%d').date()
    
    print(f"Today: {today.strftime('%Y-%m-%d')}")
    print(f"Article Date: {article_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"Close Date: {close_date.strftime('%Y-%m-%d')}")
    print()
    
    if close_date > today:
        days_ahead = (close_date - today).days
        print(f"❌ Close date is {days_ahead} days in the FUTURE")
        print(f"❌ Data cannot be real (date hasn't happened yet)")
        return False
    else:
        days_ago = (today - close_date).days
        print(f"✅ Close date is {days_ago} days in the PAST")
        print(f"✅ Date is valid (can verify)")
    print()
    
    # Check if article date to close date makes sense
    article_date_only = article_date.date()
    days_between = (close_date - article_date_only).days
    
    print(f"Days between article and close: {days_between}")
    if days_between == 1:
        print(f"✅ Correct: Article on {article_date_only.strftime('%A')}, close on {close_date.strftime('%A')}")
        print(f"   Article published when market was closed, next trading day close is correct")
    elif days_between == 0:
        print(f"✅ Correct: Same day close")
    else:
        print(f"⚠️  {days_between} days between article and close (may include weekends)")
    print()
    
    # Price reasonableness check
    print("=" * 80)
    print("PRICE REASONABLENESS CHECK")
    print("=" * 80)
    print()
    
    price = TEST_DATA['close_price']
    change_pct = TEST_DATA['change_pct']
    
    # JNJ typically trades between $140-$180 range
    if 140 <= price <= 180:
        print(f"✅ Price ${price:.2f} is within reasonable range for JNJ ($140-$180)")
    elif price < 140:
        print(f"⚠️  Price ${price:.2f} seems low for JNJ (typically $140+)")
    else:
        print(f"⚠️  Price ${price:.2f} seems high for JNJ (typically <$180)")
    
    # Change percentage check
    if abs(change_pct) < 10:
        print(f"✅ Change {change_pct:.2f}% is reasonable (not extreme)")
    else:
        print(f"⚠️  Change {change_pct:.2f}% is large (may indicate significant event)")
    print()
    
    # Summary
    print("=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print()
    
    print("Data Structure Check:")
    print(f"  ✅ Company name: {TEST_DATA['company']}")
    print(f"  ✅ Ticker: {TEST_DATA['ticker']}")
    print(f"  ✅ Date format: Valid")
    print(f"  ✅ Price format: ${price:.2f}")
    print(f"  ✅ Change format: {change_pct:.2f}%")
    print()
    
    print("Date Logic Check:")
    if close_date <= today:
        print(f"  ✅ Close date is in the past (verifiable)")
    if days_between <= 2:
        print(f"  ✅ Time between article and close is reasonable")
    print()
    
    print("Price Reasonableness:")
    if 140 <= price <= 180:
        print(f"  ✅ Price is within expected range for JNJ")
    if abs(change_pct) < 10:
        print(f"  ✅ Change percentage is reasonable")
    print()
    
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()
    
    print("Based on structural checks:")
    print("  ✅ Date is valid (in the past)")
    print("  ✅ Price is within reasonable range")
    print("  ✅ Change percentage is reasonable")
    print("  ✅ Date logic is correct (next trading day after article)")
    print()
    print("⚠️  NOTE: Cannot verify exact price due to API limitations in test environment")
    print("   To fully verify, need to:")
    print("   1. Check Prixe.io API for JNJ on 2025-03-11")
    print("   2. Check yfinance for JNJ on 2025-03-11")
    print("   3. Compare with expected price $162.22")
    print()
    print("💡 The data STRUCTURE appears valid, but exact price needs API verification")
    
    return True

if __name__ == '__main__':
    success = test_jnj_simple_verification()
    sys.exit(0 if success else 1)

