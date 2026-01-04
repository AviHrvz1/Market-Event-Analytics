#!/usr/bin/env python3
"""
Simplified test to verify UI article count (114) matches actual count
"""

import sys
from main import LayoffTracker

def test_ui_count():
    """Quick test to verify article count"""
    print("=" * 80)
    print("UI COUNT VERIFICATION")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    # Reset state
    tracker.layoffs = []
    tracker.api_call_count = 0
    tracker.total_api_calls_estimated = 0
    
    # Use the default event type
    event_types = ['bio_companies_small_cap_options']
    selected_sources = ['google_news']
    
    print(f"Event types: {event_types}")
    print(f"Sources: {selected_sources}")
    print()
    print("Running fetch_layoffs (this may take a few minutes)...")
    print()
    
    try:
        # Run full pipeline
        layoffs = tracker.fetch_layoffs(
            event_types=event_types,
            selected_sources=selected_sources,
            fetch_full_content=False
        )
        
        final_count = len(layoffs)
        print()
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        print(f"UI shows: 114 articles")
        print(f"Actual count: {final_count} articles")
        print()
        
        if final_count == 114:
            print("✅ VERIFICATION PASSED: UI count (114) matches actual count!")
        else:
            diff = abs(114 - final_count)
            print(f"⚠️  VERIFICATION FAILED: UI shows 114 but actual is {final_count}")
            print(f"   Difference: {diff} articles")
            
            if final_count > 114:
                print(f"   ⚠️  {diff} articles are missing from UI (may be filtered by UI)")
            else:
                print(f"   ⚠️  {diff} articles are shown in UI but not in actual results")
        
        # Show breakdown by ticker
        print()
        print("Breakdown by ticker:")
        ticker_counts = {}
        for layoff in layoffs:
            ticker = layoff.get('stock_ticker', 'N/A')
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        
        # Sort by count
        sorted_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)
        print(f"Total unique tickers: {len(ticker_counts)}")
        print(f"Max articles per ticker: {max(ticker_counts.values()) if ticker_counts else 0}")
        print(f"Total articles: {sum(ticker_counts.values())}")
        print()
        print("Top 10 tickers by article count:")
        for ticker, count in sorted_tickers[:10]:
            print(f"  {ticker}: {count} articles")
        
        return final_count
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    count = test_ui_count()
    sys.exit(0 if count == 114 else 1)

