#!/usr/bin/env python3
"""
Simplified diagnostic test to understand article filtering.
Analyzes the filtering logic without making full API calls.
"""

import sys
from config import MAX_ARTICLES_TO_PROCESS, MIN_LAYOFF_PERCENTAGE

def analyze_filtering_logic():
    """Analyze the filtering logic to understand where articles are lost"""
    
    print("=" * 80)
    print("ARTICLE FILTERING LOGIC ANALYSIS")
    print("=" * 80)
    print()
    
    print("📋 Current Configuration:")
    print(f"   MAX_ARTICLES_TO_PROCESS: {MAX_ARTICLES_TO_PROCESS}")
    print(f"   MIN_LAYOFF_PERCENTAGE: {MIN_LAYOFF_PERCENTAGE}%")
    print()
    
    print("🔍 Filtering Pipeline:")
    print()
    
    print("Step 1: Article Fetching")
    print("   - Fetches from Google News RSS and Benzinga")
    print("   - Example: 279 articles matched")
    print()
    
    print("Step 2: MAX_ARTICLES_TO_PROCESS Limit")
    print(f"   - Limits to {MAX_ARTICLES_TO_PROCESS} most recent articles")
    print(f"   - Example: 279 → {MAX_ARTICLES_TO_PROCESS} (loses {279 - MAX_ARTICLES_TO_PROCESS} articles)")
    print()
    
    print("Step 3: Company/Ticker Extraction")
    print("   - Calls extract_layoff_info() for each article")
    print("   - Filters out articles where company/ticker cannot be extracted")
    print("   - This is where most articles are likely lost")
    print()
    
    print("Step 4: 3-Per-Ticker Limit")
    print("   - Groups articles by ticker")
    print("   - Keeps only 3 most recent articles per ticker")
    print("   - Example: If Moderna has 10 articles → only 3 kept")
    print()
    
    print("Step 5: Final Filtering")
    print(f"   - Requires: company_name AND stock_ticker")
    print(f"   - OR: layoff_percentage >= {MIN_LAYOFF_PERCENTAGE}%")
    print("   - Filters out articles missing company or ticker")
    print()
    
    print("=" * 80)
    print("📊 ESTIMATED BREAKDOWN (for 279 initial articles → 19 final)")
    print("=" * 80)
    print()
    
    initial = 279
    after_max_limit = MAX_ARTICLES_TO_PROCESS
    estimated_extracted = 50  # Estimate based on company extraction success rate
    estimated_after_ticker_limit = 30  # Estimate after 3-per-ticker
    final = 19
    
    print(f"Initial articles fetched:        {initial:>4}")
    print(f"After MAX_ARTICLES limit:        {after_max_limit:>4}  (lost {initial - after_max_limit})")
    print(f"After company extraction:        ~{estimated_extracted:>4}  (lost ~{after_max_limit - estimated_extracted})")
    print(f"After 3-per-ticker limit:        ~{estimated_after_ticker_limit:>4}  (lost ~{estimated_extracted - estimated_after_ticker_limit})")
    print(f"After final filtering:           {final:>4}  (lost ~{estimated_after_ticker_limit - final})")
    print()
    
    print("=" * 80)
    print("🎯 KEY FINDINGS")
    print("=" * 80)
    print()
    print("1. MAX_ARTICLES_TO_PROCESS = 100")
    print("   → Immediately reduces 279 articles to 100")
    print("   → Loses 179 articles before processing")
    print()
    print("2. Company/Ticker Extraction")
    print("   → Many articles may not contain recognizable company names")
    print("   → Articles about 'Pfizer vaccine' may not extract 'Pfizer' as company")
    print("   → Generic biotech news may not mention specific companies")
    print()
    print("3. 3-Per-Ticker Limit")
    print("   → If multiple articles about same company, only 3 kept")
    print("   → Example: 10 Moderna articles → 3 kept, 7 lost")
    print()
    print("4. Final Filtering")
    print("   → Requires both company_name AND stock_ticker")
    print("   → Articles with company but no ticker are filtered out")
    print()
    
    print("=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("To see more articles:")
    print()
    print("1. Increase MAX_ARTICLES_TO_PROCESS")
    print("   → Change from 100 to 500 or 1000")
    print("   → Location: config.py")
    print()
    print("2. Increase 3-per-ticker limit")
    print("   → Change from 3 to 10 or 20")
    print("   → Location: main.py line ~4421")
    print()
    print("3. Improve company extraction")
    print("   → Better pattern matching for company names")
    print("   → Handle variations (e.g., 'Pfizer Inc' vs 'Pfizer')")
    print()
    print("4. Remove Google News RSS 100-item limit")
    print("   → Location: main.py line ~3729")
    print("   → Change: for item in items[:100]: → for item in items:")
    print()

if __name__ == '__main__':
    try:
        analyze_filtering_logic()
        print("\n✅ Analysis completed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

