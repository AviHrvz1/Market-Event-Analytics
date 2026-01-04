#!/usr/bin/env python3
"""
Test script to fetch layoff events and extract all stock pricing data
for verification with AI (Claude/ChatGPT)
"""

import json
from datetime import datetime
from main import LayoffTracker

def format_stock_data_for_verification(layoff):
    """Format stock pricing data in a clear format for AI verification"""
    ticker = layoff.get('stock_ticker', 'N/A')
    company = layoff.get('company_name', 'N/A')
    announcement_dt = layoff.get('datetime')
    announcement_date = layoff.get('date', 'N/A')
    announcement_time = layoff.get('time', 'N/A')
    
    intervals = ['5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr', '3hr', '1day', '2day', '3day']
    
    data = {
        'company': company,
        'ticker': ticker,
        'announcement_datetime': announcement_dt.isoformat() if announcement_dt else f"{announcement_date} {announcement_time}",
        'announcement_date': announcement_date,
        'announcement_time': announcement_time,
        'intervals': []
    }
    
    for interval in intervals:
        price = layoff.get(f'price_{interval}')
        change = layoff.get(f'change_{interval}')
        date = layoff.get(f'date_{interval}')
        datetime_str = layoff.get(f'datetime_{interval}')
        market_closed = layoff.get(f'market_closed_{interval}', False)
        
        interval_data = {
            'interval': interval,
            'price': price,
            'change_percent': change,
            'date': date,
            'datetime': datetime_str,
            'market_closed': market_closed
        }
        
        data['intervals'].append(interval_data)
    
    return data

def main():
    print("=" * 80)
    print("LAYOFF EVENT STOCK PRICING VERIFICATION TEST")
    print("=" * 80)
    print()
    
    # Initialize tracker
    print("Fetching layoff events...")
    tracker = LayoffTracker()
    
    # Fetch layoff events only
    event_types = ['layoff_event']
    tracker.fetch_layoffs(fetch_full_content=True, event_types=event_types)
    tracker.sort_layoffs()
    
    print(f"\nFound {len(tracker.layoffs)} layoff events")
    print()
    
    if not tracker.layoffs:
        print("No layoff events found. Exiting.")
        return
    
    # Format all stock pricing data
    all_stock_data = []
    for layoff in tracker.layoffs:
        if layoff.get('stock_ticker'):
            stock_data = format_stock_data_for_verification(layoff)
            all_stock_data.append(stock_data)
    
    print(f"Found {len(all_stock_data)} events with stock tickers")
    print()
    
    # Display summary
    print("=" * 80)
    print("STOCK PRICING DATA SUMMARY")
    print("=" * 80)
    print()
    
    for i, data in enumerate(all_stock_data, 1):
        print(f"\n{i}. {data['company']} ({data['ticker']})")
        print(f"   Announcement: {data['announcement_datetime']}")
        print(f"   Intervals with data:")
        
        for interval in data['intervals']:
            if interval['price'] is not None:
                price_str = f"${interval['price']:.2f}" if interval['price'] else "N/A"
                change_str = f"{interval['change_percent']:+.2f}%" if interval['change_percent'] is not None else "N/A"
                date_str = interval['date'] or "N/A"
                datetime_str = interval['datetime'] or "N/A"
                closed_str = " (MARKET CLOSED)" if interval['market_closed'] else ""
                
                print(f"      {interval['interval']:>6}: {price_str:>10} ({change_str:>8}) on {date_str} at {datetime_str}{closed_str}")
            elif interval['market_closed']:
                print(f"      {interval['interval']:>6}: MARKET CLOSED on {interval['date']}")
    
    # Save to JSON file for easy sharing with AI
    output_file = 'stock_pricing_verification_data.json'
    with open(output_file, 'w') as f:
        json.dump(all_stock_data, f, indent=2, default=str)
    
    print()
    print("=" * 80)
    print(f"Data saved to: {output_file}")
    print("=" * 80)
    print()
    print("You can now share this data with Claude/ChatGPT for verification.")
    print("Ask the AI to:")
    print("  1. Verify if the prices are correct for each date/time")
    print("  2. Check if the dates are trading days (not holidays/weekends)")
    print("  3. Verify the percentage changes are calculated correctly")
    print("  4. Check if market-closed days are properly identified")
    print()
    
    # Also print a formatted version for direct copy-paste
    print("=" * 80)
    print("FORMATTED DATA FOR AI VERIFICATION")
    print("=" * 80)
    print()
    print("Please verify the following stock pricing data:")
    print()
    
    for data in all_stock_data:
        print(f"Company: {data['company']}")
        print(f"Ticker: {data['ticker']}")
        print(f"Announcement Date/Time: {data['announcement_datetime']}")
        print()
        print("Stock Price Data:")
        print("-" * 60)
        
        for interval in data['intervals']:
            if interval['price'] is not None:
                print(f"  {interval['interval']:>6}: Price ${interval['price']:.2f}, Change {interval['change_percent']:+.2f}%, Date: {interval['date']}, Time: {interval['datetime']}")
            elif interval['market_closed']:
                print(f"  {interval['interval']:>6}: MARKET CLOSED on {interval['date']}")
        
        print()
        print("=" * 60)
        print()

if __name__ == '__main__':
    main()

