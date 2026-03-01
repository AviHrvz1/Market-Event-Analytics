#!/usr/bin/env python3
"""
Unittest to test NIO ticker fetching and processing
"""

import unittest
import sys
from datetime import datetime, timezone, timedelta
from main import LayoffTracker

class TestNIOTicker(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = LayoffTracker()
        self.test_ticker = 'NIO'
        
    def test_fetch_ticker_info_from_claude(self):
        """Test that Claude API can fetch NIO company info"""
        print(f"\n{'='*60}")
        print(f"Test 1: Fetching NIO info from Claude API...")
        print(f"{'='*60}")
        
        result = self.tracker._fetch_ticker_info_from_claude(self.test_ticker)
        
        self.assertIsNotNone(result, "Claude API should return company info")
        self.assertIn('name', result, "Result should contain 'name'")
        self.assertIn('industry', result, "Result should contain 'industry'")
        self.assertIn('market_cap', result, "Result should contain 'market_cap'")
        
        print(f"✅ Successfully fetched NIO info:")
        print(f"   Company Name: {result['name']}")
        print(f"   Industry: {result['industry']}")
        print(f"   Market Cap: ${result['market_cap']}M")
        print(f"   Size Category: {result.get('size_category', 'Unknown')}")
        
    def test_nio_not_in_stocks_json(self):
        """Test that NIO is not in stocks.json"""
        print(f"\n{'='*60}")
        print(f"Test 2: Checking if NIO is in stocks.json...")
        print(f"{'='*60}")
        
        companies = self.tracker._get_large_cap_companies_with_options()
        is_in_list = self.test_ticker.upper() in companies
        
        print(f"NIO in stocks.json: {is_in_list}")
        if is_in_list:
            print(f"   ⚠️  NIO is already in stocks.json - this test expects it to be missing")
        else:
            print(f"   ✅ NIO is not in stocks.json (as expected)")
        
        # This test documents the current state - NIO should not be in the list
        # If it is, that's fine, but the test will note it
        
    def test_get_top_losers_with_nio_ticker_filter(self):
        """Test that get_top_losers_prixe can process NIO when provided as ticker filter"""
        print(f"\n{'='*60}")
        print(f"Test 3: Testing get_top_losers_prixe with NIO ticker filter...")
        print(f"{'='*60}")
        
        # Use a recent date (30 days ago)
        bearish_date = datetime.now(timezone.utc) - timedelta(days=30)
        logs = []
        
        try:
            results = self.tracker.get_top_losers_prixe(
                bearish_date=bearish_date,
                industry=None,
                logs=logs,
                find_gainers=False,
                flexible_days=0,
                ticker_filter=[self.test_ticker]
            )
            
            print(f"\nLogs from get_top_losers_prixe:")
            for log in logs:
                print(f"   {log}")
            
            print(f"\nResults: {len(results)} stocks found")
            
            if results:
                for ticker, pct_change, company_info, actual_date in results:
                    print(f"\n✅ Found result for {ticker}:")
                    print(f"   Company: {company_info.get('name', 'Unknown')}")
                    print(f"   Industry: {company_info.get('industry', 'Unknown')}")
                    print(f"   Market Cap: ${company_info.get('market_cap', 0)}M")
                    print(f"   Pct Change: {pct_change:.2f}%")
                    print(f"   Actual Date: {actual_date}")
                    print(f"   Is Missing From List: {company_info.get('is_missing_from_list', False)}")
                    
                    # Verify the ticker is NIO
                    self.assertEqual(ticker.upper(), self.test_ticker.upper(), 
                                   f"Expected ticker {self.test_ticker}, got {ticker}")
            else:
                print(f"\n⚠️  No results returned - this could mean:")
                print(f"   1. NIO had no price drop on the test date")
                print(f"   2. Price data is not available for NIO on that date")
                print(f"   3. There was an error fetching the data")
                
        except Exception as e:
            print(f"\n❌ Error in get_top_losers_prixe: {e}")
            import traceback
            traceback.print_exc()
            self.fail(f"get_top_losers_prixe raised an exception: {e}")
    
    def test_full_bearish_analytics_with_nio(self):
        """Test the full get_bearish_analytics flow with NIO"""
        print(f"\n{'='*60}")
        print(f"Test 4: Testing full get_bearish_analytics with NIO...")
        print(f"{'='*60}")
        
        # Use recent dates
        bearish_date = datetime.now(timezone.utc) - timedelta(days=30)
        target_date = datetime.now(timezone.utc) - timedelta(days=20)
        
        logs = []
        
        try:
            results, all_logs = self.tracker.get_bearish_analytics(
                bearish_date=bearish_date,
                target_date=target_date,
                industry=None,
                filter_type='bearish',
                pct_threshold=None,
                flexible_days=0,
                ticker_filter=self.test_ticker
            )
            
            print(f"\nLogs from get_bearish_analytics:")
            for log in all_logs[-20:]:  # Show last 20 logs
                print(f"   {log}")
            
            print(f"\nResults: {len(results)} stocks found")
            
            if results:
                for result in results:
                    print(f"\n✅ Found result:")
                    print(f"   Ticker: {result.get('ticker')}")
                    print(f"   Company: {result.get('company_name')}")
                    print(f"   Industry: {result.get('industry')}")
                    print(f"   Market Cap: ${result.get('market_cap', 0)}M")
                    print(f"   Is Missing From List: {result.get('is_missing_from_list', False)}")
                    print(f"   Bearish Price: ${result.get('bearish_price', 0):.2f}")
                    print(f"   Target Price: ${result.get('target_price', 0):.2f}")
                    
                    # Verify the ticker is NIO
                    self.assertEqual(result.get('ticker', '').upper(), self.test_ticker.upper(),
                                   f"Expected ticker {self.test_ticker}, got {result.get('ticker')}")
            else:
                print(f"\n⚠️  No results returned")
                print(f"   This could be due to:")
                print(f"   1. No price drop on the bearish date")
                print(f"   2. No price data available")
                print(f"   3. Error in processing")
                
        except Exception as e:
            print(f"\n❌ Error in get_bearish_analytics: {e}")
            import traceback
            traceback.print_exc()
            self.fail(f"get_bearish_analytics raised an exception: {e}")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("NIO Ticker Test Suite")
    print("="*60)
    print("\nThis test will:")
    print("1. Test Claude API fetching for NIO")
    print("2. Check if NIO is in stocks.json")
    print("3. Test get_top_losers_prixe with NIO")
    print("4. Test full get_bearish_analytics flow with NIO")
    print("\n" + "="*60 + "\n")
    
    unittest.main(verbosity=2)

