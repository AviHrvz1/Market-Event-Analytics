#!/usr/bin/env python3
"""
Unit test to compare Prixe.io direct API results vs project results
for Nov 3, 2025 with >= -5% drop threshold
"""

import sys
import os
import json
import requests
from datetime import datetime, timezone, timedelta
from main import LayoffTracker
from config import PRIXE_API_KEY

def get_prixe_direct_results(bearish_date, tickers_list):
    """Get drop percentages using project's get_top_losers_prixe method"""
    tracker = LayoffTracker()
    
    print(f"Fetching Prixe.io data for {len(tickers_list)} tickers using project method...")
    print()
    
    # Use the project's method to get losers from Prixe.io
    try:
        losers = tracker.get_top_losers_prixe(bearish_date, industry=None)
        
        # Convert to dictionary format
        results = {}
        for ticker, pct_change, company_info in losers:
            results[ticker] = {
                'pct_change': pct_change,
                'company_info': company_info
            }
        
        print(f"  Prixe.io returned {len(results)} stocks with drops")
        return results
    except Exception as e:
        print(f"❌ Error getting Prixe.io results: {e}")
        import traceback
        traceback.print_exc()
        return {}

def test_prixe_vs_project():
    """Compare Prixe.io direct results vs project results"""
    print("=" * 80)
    print("PRIXE.IO vs PROJECT COMPARISON TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    bearish_date = datetime(2025, 11, 3, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 22, tzinfo=timezone.utc)
    pct_threshold = -5.0
    
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"Threshold: >= {pct_threshold}% drop")
    print()
    
    # Step 1: Get list of all large-cap companies from project
    print("Step 1: Getting list of large-cap companies from project...")
    companies = tracker._get_large_cap_companies_with_options()
    tickers_list = [info.get('ticker') for info in companies.values() if info.get('ticker')]
    print(f"  Found {len(tickers_list)} tickers")
    print()
    
    # Step 2: Get direct Prixe.io results for all tickers
    print("Step 2: Fetching direct Prixe.io data...")
    prixe_results = get_prixe_direct_results(bearish_date, tickers_list)
    
    # Show all Prixe.io results (before filtering)
    print(f"\nPrixe.io returned {len(prixe_results)} stocks total")
    
    # Show distribution of drops
    drops_by_range = {
        '<= -10%': [],
        '-10% to -5%': [],
        '-5% to -3%': [],
        '-3% to 0%': [],
        '> 0%': [],
        'No data': []
    }
    
    for ticker, data in prixe_results.items():
        pct_change = data.get('pct_change')
        if pct_change is None:
            drops_by_range['No data'].append(ticker)
        elif pct_change <= -10:
            drops_by_range['<= -10%'].append((ticker, pct_change))
        elif pct_change <= -5:
            drops_by_range['-10% to -5%'].append((ticker, pct_change))
        elif pct_change <= -3:
            drops_by_range['-5% to -3%'].append((ticker, pct_change))
        elif pct_change <= 0:
            drops_by_range['-3% to 0%'].append((ticker, pct_change))
        else:
            drops_by_range['> 0%'].append((ticker, pct_change))
    
    print("\nDrop distribution from Prixe.io:")
    for range_name, stocks in drops_by_range.items():
        if stocks:
            print(f"  {range_name}: {len(stocks)} stocks")
            if range_name in ['<= -10%', '-10% to -5%'] and len(stocks) <= 20:
                # Show all stocks in these ranges
                for item in stocks:
                    if isinstance(item, tuple):
                        print(f"    {item[0]}: {item[1]:.2f}%")
                    else:
                        print(f"    {item}")
    print()
    
    # Filter Prixe.io results by threshold
    prixe_filtered = {}
    for ticker, data in prixe_results.items():
        pct_change = data.get('pct_change')
        if pct_change is not None and pct_change <= pct_threshold:
            prixe_filtered[ticker] = data
    
    print(f"  Prixe.io found {len(prixe_filtered)} stocks with drop <= {pct_threshold}%")
    if len(prixe_filtered) > 0:
        print("  Stocks:")
        for ticker in sorted(prixe_filtered.keys()):
            pct = prixe_filtered[ticker]['pct_change']
            print(f"    {ticker}: {pct:.2f}%")
    print()
    
    # Step 3: Get project results
    print("Step 3: Getting project results...")
    project_results, logs = tracker.get_bearish_analytics(
        bearish_date=bearish_date,
        target_date=target_date,
        industry=None,
        filter_type='bearish',
        pct_threshold=pct_threshold
    )
    
    project_tickers = {stock.get('ticker') for stock in project_results}
    print(f"  Project found {len(project_tickers)} stocks with drop <= {pct_threshold}%")
    print()
    
    # Step 4: Compare results
    print("=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)
    print()
    
    # Stocks found by Prixe.io but not by project
    prixe_only = set(prixe_filtered.keys()) - project_tickers
    
    # Stocks found by project but not by Prixe.io
    project_only = project_tickers - set(prixe_filtered.keys())
    
    # Stocks found by both
    both_found = set(prixe_filtered.keys()) & project_tickers
    
    print(f"✅ Stocks found by BOTH: {len(both_found)}")
    if len(both_found) > 0:
        print("  Examples (first 10):")
        for ticker in list(both_found)[:10]:
            prixe_pct = prixe_filtered[ticker]['pct_change']
            project_stock = next((s for s in project_results if s.get('ticker') == ticker), None)
            project_pct = project_stock.get('pct_change') if project_stock else None
            print(f"    {ticker}: Prixe={prixe_pct:.2f}%, Project={project_pct:.2f}%")
    print()
    
    print(f"⚠️  Stocks found by PRIXE.IO ONLY: {len(prixe_only)}")
    if len(prixe_only) > 0:
        print("  These stocks should be in project results but are missing:")
        for ticker in sorted(prixe_only):
            prixe_pct = prixe_filtered[ticker]['pct_change']
            prixe_price = prixe_filtered[ticker].get('price_on_date')
            print(f"    {ticker}: {prixe_pct:.2f}% drop, Price=${prixe_price:.2f}" if prixe_price else f"    {ticker}: {prixe_pct:.2f}% drop")
    print()
    
    print(f"❓ Stocks found by PROJECT ONLY: {len(project_only)}")
    if len(project_only) > 0:
        print("  These stocks are in project but Prixe.io didn't find them:")
        for ticker in sorted(project_only):
            project_stock = next((s for s in project_results if s.get('ticker') == ticker), None)
            project_pct = project_stock.get('pct_change') if project_stock else None
            project_price = project_stock.get('bearish_price') if project_stock else None
            print(f"    {ticker}: {project_pct:.2f}% drop, Price=${project_price:.2f}" if project_price else f"    {ticker}: {project_pct:.2f}% drop")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Prixe.io found: {len(prixe_filtered)} stocks")
    print(f"Project found: {len(project_tickers)} stocks")
    print(f"Both found: {len(both_found)} stocks")
    print(f"Missing from project: {len(prixe_only)} stocks")
    print(f"Extra in project: {len(project_only)} stocks")
    print()
    
    if len(prixe_only) > 0:
        print("⚠️  GAP DETECTED: Some stocks found by Prixe.io are missing from project results!")
        print("   This could indicate:")
        print("   1. Date adjustment issues (weekends/holidays)")
        print("   2. Price history calculation differences")
        print("   3. Filtering logic issues")
        return False
    elif len(project_only) > 0:
        print("ℹ️  Project found some stocks that Prixe.io didn't (might be due to date adjustments)")
        return True
    else:
        print("✅ PERFECT MATCH: All stocks match between Prixe.io and project!")
        return True

if __name__ == "__main__":
    success = test_prixe_vs_project()
    sys.exit(0 if success else 1)

