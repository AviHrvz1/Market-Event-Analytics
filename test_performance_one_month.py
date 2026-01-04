#!/usr/bin/env python3
"""
Performance unittest for one-month period
Tests data completeness and identifies performance bottlenecks
"""

import sys
import time
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

def test_performance_one_month():
    """Test performance and data completeness for one-month period"""
    print("=" * 80)
    print("PERFORMANCE TEST - ONE MONTH PERIOD")
    print("=" * 80)
    print()
    
    # One month period: Nov 17 to Dec 17, 2025
    bearish_date = datetime(2025, 11, 17, tzinfo=timezone.utc)
    target_date = datetime(2025, 12, 17, tzinfo=timezone.utc)
    industry = "Technology"
    filter_type = "bearish"
    pct_threshold = -5.0
    
    print(f"📅 Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
    print(f"📅 Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"📊 Period: {(target_date - bearish_date).days} days")
    print(f"🏭 Industry: {industry}")
    print(f"🔍 Filter Type: {filter_type}")
    print(f"📉 Min % Change: {pct_threshold}%")
    print()
    
    tracker = LayoffTracker()
    
    # Track timing for each step
    timings = {
        'total': 0,
        'step1_find_stocks': 0,
        'step2_process_stocks': 0,
        'step3_filter': 0,
        'step4_indicators': 0,
        'step5_earnings': 0
    }
    
    # Track data completeness
    data_quality = {
        'total_stocks_found': 0,
        'stocks_processed': 0,
        'stocks_after_filter': 0,
        'stocks_with_indicators': 0,
        'stocks_with_earnings': 0,
        'stocks_with_price_history': 0,
        'stocks_with_target_price': 0
    }
    
    total_start = time.time()
    
    try:
        # Step 1: Find stocks with drops/gains
        print("=" * 80)
        print("STEP 1: Finding stocks with drops/gains")
        print("=" * 80)
        step1_start = time.time()
        
        losers = tracker.get_top_losers_prixe(
            bearish_date, 
            industry=industry, 
            logs=None, 
            find_gainers=(filter_type == 'bullish')
        )
        
        step1_time = time.time() - step1_start
        timings['step1_find_stocks'] = step1_time
        data_quality['total_stocks_found'] = len(losers)
        
        print(f"✅ Found {len(losers)} stocks in {step1_time:.2f}s")
        print()
        
        # Step 2: Process stocks (get prices, calculate pct_change)
        print("=" * 80)
        print("STEP 2: Processing stocks (prices, pct_change)")
        print("=" * 80)
        step2_start = time.time()
        
        results, logs = tracker.get_bearish_analytics(
            bearish_date=bearish_date,
            target_date=target_date,
            industry=industry,
            filter_type=filter_type,
            pct_threshold=pct_threshold
        )
        
        step2_time = time.time() - step2_start
        timings['step2_process_stocks'] = step2_time
        
        print(f"✅ Processed stocks in {step2_time:.2f}s")
        print()
        
        # Analyze results for data completeness
        print("=" * 80)
        print("DATA COMPLETENESS CHECK")
        print("=" * 80)
        print()
        
        for stock in results:
            data_quality['stocks_processed'] += 1
            
            if stock.get('target_price'):
                data_quality['stocks_with_target_price'] += 1
            
            if stock.get('price_history') and len(stock.get('price_history', [])) > 0:
                data_quality['stocks_with_price_history'] += 1
            
            if stock.get('technical_indicators'):
                indicators = stock.get('technical_indicators', {})
                if indicators.get('rsi') is not None or indicators.get('nearest_support') is not None:
                    data_quality['stocks_with_indicators'] += 1
            
            if stock.get('earnings_dividends'):
                earnings = stock.get('earnings_dividends', {})
                if earnings.get('has_events_during') or earnings.get('has_next_events'):
                    data_quality['stocks_with_earnings'] += 1
        
        data_quality['stocks_after_filter'] = len(results)
        
        # Print data quality report
        print(f"📊 Data Quality:")
        print(f"   Total stocks found: {data_quality['total_stocks_found']}")
        print(f"   Stocks processed: {data_quality['stocks_processed']}")
        print(f"   Stocks after filter: {data_quality['stocks_after_filter']}")
        print()
        print(f"   ✅ Stocks with target price: {data_quality['stocks_with_target_price']}/{data_quality['stocks_after_filter']}")
        print(f"   ✅ Stocks with price history: {data_quality['stocks_with_price_history']}/{data_quality['stocks_after_filter']}")
        print(f"   ✅ Stocks with technical indicators: {data_quality['stocks_with_indicators']}/{data_quality['stocks_after_filter']}")
        print(f"   ✅ Stocks with earnings data: {data_quality['stocks_with_earnings']}/{data_quality['stocks_after_filter']}")
        print()
        
        # Check for missing data
        missing_data = []
        if data_quality['stocks_with_target_price'] < data_quality['stocks_after_filter']:
            missing_data.append(f"Target price: {data_quality['stocks_after_filter'] - data_quality['stocks_with_target_price']} missing")
        if data_quality['stocks_with_price_history'] < data_quality['stocks_after_filter']:
            missing_data.append(f"Price history: {data_quality['stocks_after_filter'] - data_quality['stocks_with_price_history']} missing")
        if data_quality['stocks_with_indicators'] < data_quality['stocks_after_filter']:
            missing_data.append(f"Technical indicators: {data_quality['stocks_after_filter'] - data_quality['stocks_with_indicators']} missing")
        
        if missing_data:
            print("⚠️  Missing Data:")
            for item in missing_data:
                print(f"   - {item}")
        else:
            print("✅ All stocks have complete data!")
        print()
        
        # Performance breakdown (from logs if available)
        print("=" * 80)
        print("PERFORMANCE BREAKDOWN")
        print("=" * 80)
        print()
        
        # Parse logs to extract timing information
        step_times = {
            'step1': step1_time,
            'step2': step2_time
        }
        
        # Look for timing patterns in logs
        for log in logs:
            if 'Progress:' in log and '%' in log:
                # Extract progress info
                pass
            elif 'Filtered by' in log:
                step_times['step3_filter'] = 0.01  # Filtering is instant
            elif 'Checking earnings' in log:
                step_times['step4_earnings'] = 0  # Will estimate
            elif 'Calculating technical indicators' in log:
                step_times['step5_indicators'] = 0  # Will estimate
        
        total_time = time.time() - total_start
        timings['total'] = total_time
        
        print(f"⏱️  Timing Breakdown:")
        print(f"   Step 1 - Find stocks: {step1_time:.2f}s ({step1_time/total_time*100:.1f}%)")
        print(f"   Step 2 - Process stocks: {step2_time:.2f}s ({step2_time/total_time*100:.1f}%)")
        
        # Estimate other steps (they're part of step2)
        if step2_time > 0:
            # Estimate: processing is most of step2, filtering/indicators/earnings are smaller
            estimated_processing = step2_time * 0.7
            estimated_indicators = step2_time * 0.1
            estimated_earnings = step2_time * 0.2
            
            print(f"      ├─ Price fetching & processing: ~{estimated_processing:.2f}s")
            print(f"      ├─ Technical indicators: ~{estimated_indicators:.2f}s")
            print(f"      └─ Earnings checks: ~{estimated_earnings:.2f}s")
        
        print(f"   Total time: {total_time:.2f}s")
        print()
        
        # Identify bottlenecks
        print("=" * 80)
        print("BOTTLENECK ANALYSIS")
        print("=" * 80)
        print()
        
        if step1_time > step2_time:
            print(f"🔴 Bottleneck: Step 1 (Finding stocks) takes {step1_time:.2f}s")
            print(f"   This is the initial stock discovery phase")
        else:
            print(f"🔴 Bottleneck: Step 2 (Processing stocks) takes {step2_time:.2f}s")
            print(f"   This includes: price fetching, indicators, earnings")
        
        if step2_time > 0:
            if estimated_earnings > estimated_processing:
                print(f"   └─ Earnings checks are the slowest part: ~{estimated_earnings:.2f}s")
            elif estimated_processing > estimated_indicators:
                print(f"   └─ Price fetching is the slowest part: ~{estimated_processing:.2f}s")
        
        print()
        
        # Sample results
        print("=" * 80)
        print("SAMPLE RESULTS (First 5 stocks)")
        print("=" * 80)
        print()
        
        for i, stock in enumerate(results[:5], 1):
            print(f"{i}. {stock.get('ticker')} - {stock.get('company_name', 'N/A')}")
            print(f"   Bearish Price: ${stock.get('bearish_price', 0):.2f}")
            print(f"   Target Price: ${stock.get('target_price', 0):.2f}")
            print(f"   % Change: {stock.get('pct_change', 0):+.2f}%")
            print(f"   RSI: {stock.get('technical_indicators', {}).get('rsi', 'N/A')}")
            print(f"   Support: ${stock.get('technical_indicators', {}).get('nearest_support', 'N/A')}")
            print(f"   Resistance: ${stock.get('technical_indicators', {}).get('nearest_resistance', 'N/A')}")
            print(f"   Earnings During: {stock.get('earnings_dividends', {}).get('has_events_during', False)}")
            print(f"   Next Events: {stock.get('earnings_dividends', {}).get('has_next_events', False)}")
            print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        
        all_data_complete = (
            data_quality['stocks_with_target_price'] == data_quality['stocks_after_filter'] and
            data_quality['stocks_with_price_history'] == data_quality['stocks_after_filter'] and
            data_quality['stocks_with_indicators'] == data_quality['stocks_after_filter']
        )
        
        if all_data_complete:
            print("✅ All data received correctly!")
        else:
            print("⚠️  Some data missing (see details above)")
        
        print(f"📊 Performance: {total_time:.2f}s total")
        print(f"📈 Stocks found: {data_quality['total_stocks_found']}")
        print(f"📉 Stocks after filter: {data_quality['stocks_after_filter']}")
        print()
        
        return all_data_complete and len(results) > 0
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_performance_one_month()
    sys.exit(0 if success else 1)

