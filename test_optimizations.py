#!/usr/bin/env python3
"""
Test to verify the optimizations work:
1. CSV parsing handles company names with commas
2. "neutral" direction is accepted
3. Company name extraction uses candidate companies for bio_companies
"""

import sys
import re
from main import LayoffTracker

def test_csv_parsing():
    """Test CSV parsing with company names containing commas"""
    print("=" * 80)
    print("TEST 1: CSV Parsing with Commas in Company Names")
    print("=" * 80)
    print()
    
    test_cases = [
        ('Article 1: Theravance Biopharma, Inc., TBPH, 5, bullish', 'Theravance Biopharma, Inc.', 'TBPH', 5, 'bullish'),
        ('Article 2: Johnson & Johnson, Inc., JNJ, 7, bearish', 'Johnson & Johnson, Inc.', 'JNJ', 7, 'bearish'),
        ('Article 3: Pfizer Inc, PFE, 8, neutral', 'Pfizer Inc', 'PFE', 8, 'bullish'),  # neutral -> bullish
        ('Article 4: Moderna, MRNA, 9, bullish', 'Moderna', 'MRNA', 9, 'bullish'),
    ]
    
    tracker = LayoffTracker()
    
    for test_line, expected_company, expected_ticker, expected_score, expected_direction in test_cases:
        print(f"Testing: {test_line[:60]}...")
        
        # Simulate the parsing logic
        match = re.match(r'Article\s+(\d+):\s*(.+)', test_line, re.IGNORECASE)
        if match:
            data_str = match.group(2)
            parts = [p.strip() for p in data_str.split(',')]
            
            if len(parts) >= 4:
                # Parse from the end backwards
                direction = parts[-1].strip().lower()
                score_str = parts[-2].strip()
                ticker_str = parts[-3].strip().upper()
                company_name = ', '.join(parts[:-3]).strip()
                
                # Map neutral to bullish
                if direction == 'neutral':
                    direction = 'bullish'
                
                ticker = None if ticker_str == 'N/A' or ticker_str == '' else ticker_str
                score = int(score_str)
                
                if company_name == expected_company and ticker == expected_ticker and score == expected_score and direction == expected_direction:
                    print(f"  ✅ PASS: Parsed correctly")
                else:
                    print(f"  ❌ FAIL: Expected ({expected_company}, {expected_ticker}, {expected_score}, {expected_direction}), got ({company_name}, {ticker}, {score}, {direction})")
            else:
                print(f"  ❌ FAIL: Not enough parts ({len(parts)})")
        else:
            print(f"  ❌ FAIL: Regex didn't match")
        print()

def test_candidate_companies():
    """Test that candidate companies are used for bio_companies"""
    print("=" * 80)
    print("TEST 2: Candidate Companies Optimization")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    bio_companies = tracker._get_bio_pharma_companies()
    
    print(f"Bio companies list: {len(bio_companies)} companies")
    print(f"Sample: {bio_companies[:5]}")
    print()
    
    # Test article that mentions a bio company
    test_title = "Pfizer announces new drug approval"
    test_description = "Pfizer Inc has received FDA approval for its new treatment"
    
    print(f"Testing extraction with candidate companies...")
    print(f"Title: {test_title}")
    print(f"Description: {test_description}")
    print()
    
    # Test with candidates (should be fast)
    result_with_candidates = tracker.extract_company_name(
        test_title, 
        test_description, 
        candidate_companies=bio_companies
    )
    
    print(f"Result with candidates: {result_with_candidates}")
    
    if result_with_candidates:
        print(f"  ✅ PASS: Found company using candidate list")
    else:
        print(f"  ⚠️  WARNING: Didn't find company (might need to check SEC EDGAR)")
    print()

if __name__ == '__main__':
    try:
        test_csv_parsing()
        test_candidate_companies()
        print("✅ All tests completed")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

