#!/usr/bin/env python3
"""
Diagnostic test to understand why UI shows only 1 result
Checks the filtering logic and what should be returned
"""

import sys
from datetime import datetime, timezone, timedelta

def test_ui_results_diagnostic():
    """Diagnostic test for UI results"""
    print("=" * 80)
    print("UI RESULTS DIAGNOSTIC")
    print("=" * 80)
    print()
    
    print("Test Parameters:")
    print("  Analysis Date: 2025-12-11")
    print("  Target Date: 2025-12-31")
    print("  Industry: All Industries")
    print("  Filter Type: bearish")
    print("  Percentage Threshold: -5%")
    print("  Flexible Days: (not specified - need to check UI)")
    print()
    
    print("=" * 80)
    print("POSSIBLE REASONS FOR ONLY 1 RESULT")
    print("=" * 80)
    print()
    print("1. Network/API Issues:")
    print("   - DNS resolution failures for api.prixe.io")
    print("   - Many tickers failing to fetch data")
    print("   - Only 1 ticker successfully fetched and met criteria")
    print()
    print("2. Future Date Issues:")
    print("   - Dec 2025 is in the future - no real historical data")
    print("   - API may return empty or limited data")
    print()
    print("3. Flexible Date Range:")
    print("   - If flexible_days=0: Only checks exact date (2025-12-11)")
    print("   - If flexible_days=2: Checks 2025-12-09 to 2025-12-13")
    print("   - Need to verify what flexible_days value was used in UI")
    print()
    print("4. Filtering Logic:")
    print("   - Stocks must have pct_change <= -5.0 (drop of 5% or more)")
    print("   - Filter is applied after fetching all stocks")
    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("1. Check Server Logs:")
    print("   - Look for 'Filtered by bearish drop: X/Y stocks' message")
    print("   - This will show how many stocks were found before filtering")
    print()
    print("2. Check Flexible Days Value:")
    print("   - Verify what value was entered in the 'Flexible Date (± days)' field")
    print("   - If it's 0, try 1 or 2 to see if more stocks appear")
    print()
    print("3. Test with Past Dates:")
    print("   - Try dates in Nov 2024 or earlier where real data exists")
    print("   - This will verify if the issue is data availability")
    print()
    print("4. Check Browser Console:")
    print("   - Open browser DevTools (F12)")
    print("   - Check Console tab for any JavaScript errors")
    print("   - Check Network tab to see API responses")
    print()
    print("5. Verify API Response:")
    print("   - Check the streaming logs in the UI")
    print("   - Look for messages like:")
    print("     * 'Found X stocks with drops using Prixe.io'")
    print("     * 'Filtered by bearish drop: Y/X stocks'")
    print()
    
    return True

if __name__ == "__main__":
    success = test_ui_results_diagnostic()
    sys.exit(0 if success else 1)

