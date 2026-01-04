#!/usr/bin/env python3
"""
Unit test for CEO event types:
1. CEO Departs with No Successor
2. CEO/CFO Successor Named

This test tracks what happens during the full flow from article fetching to stock changes calculation.
"""

import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import EVENT_TYPES

print(f"\n{'='*80}")
print("Unit Test: CEO Event Types")
print(f"{'='*80}\n")

# Initialize tracker
tracker = LayoffTracker()

# Test event types
ceo_event_types = [
    'ceo_departure_no_successor',
    'successor_named',  # CEO/CFO Successor Named
]

print("Available CEO Event Types:")
for event_type in ceo_event_types:
    if event_type in EVENT_TYPES:
        print(f"  ✓ {event_type}: {EVENT_TYPES[event_type]['name']}")
        print(f"    Keywords: {len(EVENT_TYPES[event_type]['keywords'])} keywords")
    else:
        print(f"  ✗ {event_type}: NOT FOUND in EVENT_TYPES")

print(f"\n{'='*80}")
print("Test 1: Fetching Articles for CEO Event Types")
print(f"{'='*80}\n")

# Test fetching articles
event_types_to_test = ['ceo_departure_no_successor', 'successor_named']
sources = ['google_news', 'benzinga_news']

print(f"Fetching articles for:")
print(f"  Event types: {event_types_to_test}")
print(f"  Sources: {sources}")
print(f"  Lookback: 30 days")
print()

try:
    layoffs = tracker.fetch_layoffs(
        event_types=event_types_to_test,
        selected_sources=sources,
        fetch_full_content=False  # Faster for testing
    )
    
    print(f"\nResults:")
    print(f"  Total articles found: {len(layoffs)}")
    
    # Group by event type
    by_event_type = {}
    by_company = {}
    
    for layoff in layoffs:
        event_type = layoff.get('event_type', 'unknown')
        company = layoff.get('company_name', 'Unknown')
        ticker = layoff.get('stock_ticker', 'N/A')
        
        if event_type not in by_event_type:
            by_event_type[event_type] = []
        by_event_type[event_type].append(layoff)
        
        if company not in by_company:
            by_company[company] = []
        by_company[company].append({
            'ticker': ticker,
            'event_type': event_type,
            'datetime': layoff.get('datetime'),
            'title': layoff.get('title', '')[:60] + '...' if len(layoff.get('title', '')) > 60 else layoff.get('title', '')
        })
    
    print(f"\n  By Event Type:")
    for event_type, articles in by_event_type.items():
        print(f"    {event_type}: {len(articles)} articles")
    
    print(f"\n  By Company (first 10):")
    for i, (company, articles) in enumerate(list(by_company.items())[:10]):
        print(f"    {i+1}. {company}:")
        for article in articles:
            print(f"       - {article['ticker']} | {article['event_type']} | {article['datetime']}")
            print(f"         {article['title']}")
    
    # Test stock changes calculation for a few articles
    print(f"\n{'='*80}")
    print("Test 2: Calculating Stock Changes")
    print(f"{'='*80}\n")
    
    # Pick a few articles to test
    test_articles = layoffs[:5] if len(layoffs) >= 5 else layoffs
    
    print(f"Testing stock changes for {len(test_articles)} articles:\n")
    
    for i, layoff in enumerate(test_articles, 1):
        company = layoff.get('company_name', 'Unknown')
        ticker = layoff.get('stock_ticker', 'N/A')
        event_type = layoff.get('event_type', 'unknown')
        article_dt = layoff.get('datetime')
        
        print(f"{i}. {company} ({ticker})")
        print(f"   Event type: {event_type}")
        print(f"   Article datetime: {article_dt}")
        
        if not ticker or ticker == 'N/A':
            print(f"   ✗ No ticker - skipping stock changes calculation")
            continue
        
        # Calculate stock changes
        try:
            stock_changes = tracker.calculate_stock_changes(layoff)
            
            base_price = stock_changes.get('base_price')
            market_was_open = stock_changes.get('market_was_open')
            
            print(f"   Base price: {base_price}")
            print(f"   Market was open: {market_was_open}")
            
            # Check intervals
            intervals_with_data = []
            intervals_with_na = []
            intervals_closed = []
            
            for interval in ['5min', '10min', '30min', '1hr']:
                price = stock_changes.get(f'price_{interval}')
                change = stock_changes.get(f'change_{interval}')
                market_closed = stock_changes.get(f'market_closed_{interval}')
                no_data = stock_changes.get(f'no_intraday_data_{interval}')
                
                if price is not None:
                    intervals_with_data.append(interval)
                elif market_closed:
                    intervals_closed.append(interval)
                else:
                    intervals_with_na.append(interval)
            
            print(f"   Intervals with data: {intervals_with_data}")
            print(f"   Intervals closed: {intervals_closed}")
            print(f"   Intervals N/A: {intervals_with_na}")
            
            if not intervals_with_data and not intervals_closed:
                print(f"   ⚠️  All intervals show N/A - investigating...")
                
                # Check why
                if not base_price:
                    print(f"      - No base price found")
                if not market_was_open:
                    next_trading_day = tracker.get_next_trading_day(article_dt, ticker)
                    print(f"      - Market was closed, next trading day: {next_trading_day}")
                    if next_trading_day:
                        # Check if next trading day has data
                        article_day = article_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                        start_date = article_dt - timedelta(days=5)
                        end_date = article_dt + timedelta(days=3)
                        daily_data = tracker._fetch_price_data_batch(ticker, start_date, end_date, '1d')
                        has_data = tracker.has_trading_data_for_date(ticker, next_trading_day, daily_data)
                        print(f"      - Next trading day has data: {has_data}")
            
        except Exception as e:
            print(f"   ✗ Error calculating stock changes: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print(f"\n{'='*80}")
    print("Summary")
    print(f"{'='*80}\n")
    print(f"Total articles processed: {len(layoffs)}")
    print(f"Articles with tickers: {sum(1 for l in layoffs if l.get('stock_ticker') and l.get('stock_ticker') != 'N/A')}")
    print(f"Articles with stock data: {sum(1 for l in layoffs if tracker.calculate_stock_changes(l).get('base_price'))}")
    
except Exception as e:
    print(f"✗ Error during fetch: {e}")
    import traceback
    traceback.print_exc()

