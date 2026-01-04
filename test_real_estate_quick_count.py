#!/usr/bin/env python3
"""
Quick test to count real estate results
"""

import sys
from main import LayoffTracker

print("=" * 80)
print("REAL ESTATE RESULTS COUNT")
print("=" * 80)
print()

tracker = LayoffTracker()

# Test both event types
for event_type in ['real_estate_good_news', 'real_estate_bad_news']:
    print(f"\n{'='*80}")
    print(f"Testing: {event_type}")
    print(f"{'='*80}\n")
    
    # Reset
    tracker.layoffs = []
    
    try:
        # Run full fetch
        layoffs = tracker.fetch_layoffs(
            event_types=[event_type],
            selected_sources=['google_news'],
            fetch_full_content=False
        )
        
        total = len(layoffs)
        with_company = sum(1 for l in layoffs if l.get('company_name'))
        with_ticker = sum(1 for l in layoffs if l.get('stock_ticker'))
        
        print(f"RESULTS FOR {event_type.upper()}:")
        print(f"  Total articles: {total}")
        print(f"  With company name: {with_company}")
        print(f"  Without company name: {total - with_company}")
        print(f"  With ticker: {with_ticker}")
        print(f"  Without ticker: {total - with_ticker}")
        
        if layoffs:
            print(f"\n  First 3 articles:")
            for i, l in enumerate(layoffs[:3], 1):
                print(f"    {i}. {l.get('title', '')[:60]}...")
                print(f"       Company: {l.get('company_name') or 'Didn\'t find'}")
                print(f"       Ticker: {l.get('stock_ticker') or 'Didn\'t find'}")
        
    except Exception as e:
        print(f"ERROR: {str(e)[:200]}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("TEST COMPLETE")
print(f"{'='*80}")


