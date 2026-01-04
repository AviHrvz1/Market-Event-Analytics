#!/usr/bin/env python3
"""
Unit test to check how many results will be returned from 22/9/2025 till 29/10/2025
for all industries with min change -4%
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker

def test_results_count_sep_oct_2025():
    """Test results count for Sep 22 - Oct 29, 2025 with -4% filter"""
    print("=" * 80)
    print("RESULTS COUNT TEST: Sep 22 - Oct 29, 2025")
    print("=" * 80)
    print()
    
    # Test parameters
    bearish_date = datetime(2025, 9, 22, tzinfo=timezone.utc)  # Sep 22, 2025
    target_date = datetime(2025, 10, 29, tzinfo=timezone.utc)  # Oct 29, 2025
    filter_type = 'bearish'  # Looking for bearish stocks
    pct_threshold = -4.0  # Minimum -4% change
    
    print(f"Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"Filter Type: {filter_type}")
    print(f"Percentage Threshold: {pct_threshold}%")
    print()
    
    tracker = LayoffTracker()
    
    # Get all available industries
    companies = tracker._get_large_cap_companies_with_options()
    industries = set()
    for ticker, company_info in companies.items():
        industry = company_info.get('industry', 'Unknown')
        if industry:
            industries.add(industry)
    
    industries_list = sorted(list(industries))
    print(f"Total Industries: {len(industries_list)}")
    print(f"Industries: {', '.join(industries_list)}")
    print()
    print("=" * 80)
    print("RUNNING ANALYSIS FOR ALL INDUSTRIES")
    print("=" * 80)
    print()
    
    # Run analysis for all industries (None means all industries)
    print("Running analysis with industry=None (all industries)...")
    print()
    
    try:
        # Capture logs
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        log_capture = io.StringIO()
        
        # Run the analysis (this will take a few minutes)
        print("⏳ This may take 2-5 minutes depending on API response times...")
        print()
        
        results, analysis_logs = tracker.get_bearish_analytics(
            bearish_date=bearish_date,
            target_date=target_date,
            industry=None,  # All industries
            filter_type=filter_type,
            pct_threshold=pct_threshold
        )
        
        print("=" * 80)
        print("RESULTS SUMMARY")
        print("=" * 80)
        print()
        
        if results:
            print(f"✅ Total Results: {len(results)}")
            print()
            
            # Group by industry
            industry_counts = {}
            for stock in results:
                industry = stock.get('industry', 'Unknown')
                if industry not in industry_counts:
                    industry_counts[industry] = 0
                industry_counts[industry] += 1
            
            print("Results by Industry:")
            print("-" * 80)
            for industry in sorted(industry_counts.keys()):
                count = industry_counts[industry]
                print(f"  {industry}: {count} stock(s)")
            print()
            
            # Show sample results
            print("Sample Results (first 5):")
            print("-" * 80)
            for i, stock in enumerate(results[:5], 1):
                ticker = stock.get('ticker', 'N/A')
                company = stock.get('company', 'N/A')
                industry = stock.get('industry', 'N/A')
                pct_change = stock.get('pct_change', 0)
                bearish_date_str = stock.get('bearish_date', 'N/A')
                target_date_str = stock.get('target_date', 'N/A')
                
                print(f"{i}. {ticker} - {company}")
                print(f"   Industry: {industry}")
                print(f"   Change: {pct_change:.2f}%")
                print(f"   Bearish Date: {bearish_date_str}")
                print(f"   Target Date: {target_date_str}")
                print()
            
            if len(results) > 5:
                print(f"... and {len(results) - 5} more results")
                print()
            
            # Statistics
            pct_changes = [stock.get('pct_change', 0) for stock in results]
            if pct_changes:
                avg_change = sum(pct_changes) / len(pct_changes)
                min_change = min(pct_changes)
                max_change = max(pct_changes)
                
                print("Statistics:")
                print("-" * 80)
                print(f"  Average Change: {avg_change:.2f}%")
                print(f"  Minimum Change: {min_change:.2f}%")
                print(f"  Maximum Change: {max_change:.2f}%")
                print()
        else:
            print("❌ No results found")
            print()
            print("Possible reasons:")
            print("  1. No stocks met the -4% criteria on Sep 22, 2025")
            print("  2. Date range is in the future (2025) - may not have real data")
            print("  3. API limitations or errors")
            print()
        
        # Check for API errors
        if tracker.api_errors:
            print("=" * 80)
            print("API ERRORS")
            print("=" * 80)
            print()
            for error in tracker.api_errors:
                print(f"  {error.get('service', 'Unknown')}: {error.get('message', 'N/A')}")
            print()
        
        # API call statistics
        print("=" * 80)
        print("API CALL STATISTICS")
        print("=" * 80)
        print()
        print(f"Total API Calls: {tracker.api_call_count}")
        print()
        
        return len(results) if results else 0
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    import json
    
    result_count = test_results_count_sep_oct_2025()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()
    print(f"Total results returned: {result_count}")
    
    # Save summary to file
    summary_file = "test_results_sep_oct_2025_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("RESULTS COUNT TEST: Sep 22 - Oct 29, 2025\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Bearish Date: 2025-09-22\n")
        f.write(f"Target Date: 2025-10-29\n")
        f.write(f"Filter Type: bearish\n")
        f.write(f"Percentage Threshold: -4.0%\n")
        f.write(f"\nTotal Results: {result_count}\n")
    
    print(f"\nSummary saved to: {summary_file}")
    sys.exit(0)

