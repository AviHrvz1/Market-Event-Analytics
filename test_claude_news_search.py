#!/usr/bin/env python3
"""
Unit test to verify Claude can find news about stock drops
Tests if Claude receives correct dates and can locate relevant news
"""

import sys
from datetime import datetime, timezone
from main import LayoffTracker
import json

def test_claude_news_search():
    """Test if Claude can find news about specific stock drops"""
    print("=" * 80)
    print("CLAUDE NEWS SEARCH TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    if not tracker.claude_api_key:
        print("❌ Claude API key not available")
        return False
    
    # Test case: HUM on Dec 16, 2025 (known to have news)
    test_cases = [
        {
            'ticker': 'HUM',
            'company_name': 'Humana Inc',
            'bearish_date': '2025-12-16',
            'pct_drop': -6.2,
            'expected_news': True,
            'expected_keywords': ['analyst', 'target', 'cut', 'leadership', 'president', 'retired']
        },
        {
            'ticker': 'AAPL',
            'company_name': 'Apple Inc',
            'bearish_date': '2025-12-20',
            'pct_drop': -4.5,
            'expected_news': True,
            'expected_keywords': ['earnings', 'analyst', 'downgrade', 'news']
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        ticker = test_case['ticker']
        company_name = test_case['company_name']
        bearish_date_str = test_case['bearish_date']
        pct_drop = test_case['pct_drop']
        
        print(f"Testing: {ticker} ({company_name})")
        print(f"  Bearish Date: {bearish_date_str}")
        print(f"  Drop: {pct_drop}%")
        print()
        
        # Prepare minimal stock_data
        stock_data = {
            'company_name': company_name,
            'industry': 'Healthcare',
            'market_cap': 50000000000,  # $50B
            'bearish_date': bearish_date_str,
            'bearish_price': 250.0,
            'prev_price': 266.5,
            'pct_drop': pct_drop,
            'target_date': '2025-12-29',
            'target_price': 258.0,
            'recovery_pct': 3.2,
            'price_history': [
                {'date': '2025-12-15', 'price': 266.5},
                {'date': '2025-12-16', 'price': 250.0},
                {'date': '2025-12-17', 'price': 252.0},
            ],
            'earnings_dividends': {}
        }
        
        # Test 1: Check what prompt is being sent
        print("  📝 Testing prompt construction...")
        try:
            # We'll manually construct the prompt to see what Claude receives
            price_history_text = ""
            for entry in stock_data.get('price_history', [])[-30:]:
                date_str = entry.get('date', '')
                price = entry.get('price', '')
                if date_str and price:
                    price_history_text += f"{date_str}: ${price:.2f}\n"
            
            prompt = f"""You are analyzing a stock drop for a vertical call options trading strategy.

STOCK INFORMATION:
- Ticker: {ticker}
- Company: {company_name}
- Industry: {stock_data.get('industry', 'Unknown')}
- Market Cap: ${stock_data.get('market_cap', 0):,.0f}

DROP DETAILS:
- Bearish Date: {stock_data['bearish_date']}
- Bearish Price: ${stock_data['bearish_price']:.2f}
- Previous Price: {stock_data.get('prev_price', stock_data['bearish_price']):.2f}
- Drop Percentage: {stock_data['pct_drop']:.2f}%
- Target Date: {stock_data['target_date']}
- Target Price: ${stock_data['target_price']:.2f}
- Recovery Needed: {stock_data['recovery_pct']:.2f}%

PRICE HISTORY (last 30 data points):
{price_history_text}

UPCOMING EVENTS:
No significant events found.

STRATEGY CONTEXT:
The trader uses vertical call options and hopes to sell if the stock bounces back up within 40 days. They don't necessarily wait for expiration.

TASK:
1. Search the web or use your knowledge to understand why {ticker} ({company_name}) dropped {stock_data['pct_drop']:.2f}% on {stock_data['bearish_date']}. Look for news, earnings reports, analyst actions, or market events.
2. Analyze the price history to identify support/resistance levels, trends, and patterns.
3. Based on your research, price history analysis, market conditions, and sector analysis, provide a recovery probability score.

Respond with ONLY a number from 1-10:
- 1-4: Low recovery probability (weak bounce expected)
- 5-7: Moderate recovery probability (some bounce possible)
- 8-10: High recovery probability (strong bounce likely)

Just the number, nothing else."""
            
            print(f"     ✅ Prompt constructed")
            print(f"     Date in prompt: {bearish_date_str} ✓")
            print(f"     Drop % in prompt: {pct_drop}% ✓")
            print(f"     Ticker in prompt: {ticker} ✓")
            print()
            
        except Exception as e:
            print(f"     ❌ Error constructing prompt: {e}")
            print()
        
        # Test 2: Actually call Claude API
        print("  🤖 Testing Claude API call...")
        try:
            result = tracker.get_ai_recovery_score(ticker, company_name, stock_data)
            
            if result:
                score = result.get('score')
                print(f"     ✅ Claude responded with score: {score}/10")
                print()
                
                # Test 3: Get full explanation to see if Claude found news
                print("  📰 Testing full explanation (to check if Claude found news)...")
                full_result = tracker.get_ai_recovery_opinion(ticker, company_name, stock_data)
                
                if full_result:
                    explanation = full_result.get('explanation', '')
                    score_full = full_result.get('score', 0)
                    
                    print(f"     ✅ Claude provided explanation")
                    print(f"     Score: {score_full}/10")
                    print()
                    print("     Explanation preview:")
                    print("     " + "-" * 70)
                    # Show first 500 chars of explanation
                    preview = explanation[:500]
                    for line in preview.split('\n'):
                        print(f"     {line}")
                    if len(explanation) > 500:
                        print(f"     ... ({len(explanation) - 500} more characters)")
                    print("     " + "-" * 70)
                    print()
                    
                    # Check if explanation mentions expected keywords
                    explanation_lower = explanation.lower()
                    found_keywords = []
                    missing_keywords = []
                    
                    for keyword in test_case.get('expected_keywords', []):
                        if keyword.lower() in explanation_lower:
                            found_keywords.append(keyword)
                        else:
                            missing_keywords.append(keyword)
                    
                    print(f"     Keyword Analysis:")
                    if found_keywords:
                        print(f"     ✅ Found keywords: {', '.join(found_keywords)}")
                    if missing_keywords:
                        print(f"     ⚠️  Missing keywords: {', '.join(missing_keywords)}")
                    
                    # Check if Claude says it couldn't find news
                    if 'could not find' in explanation_lower or 'no news' in explanation_lower or 'no significant news' in explanation_lower:
                        print(f"     ⚠️  WARNING: Claude says it couldn't find news!")
                    else:
                        print(f"     ✅ Claude appears to have found information")
                    
                    results.append({
                        'ticker': ticker,
                        'date': bearish_date_str,
                        'score': score_full,
                        'found_keywords': found_keywords,
                        'missing_keywords': missing_keywords,
                        'explanation_length': len(explanation),
                        'mentions_no_news': 'could not find' in explanation_lower or 'no news' in explanation_lower
                    })
                else:
                    print(f"     ❌ Claude did not provide explanation")
                    results.append({
                        'ticker': ticker,
                        'date': bearish_date_str,
                        'error': 'No explanation returned'
                    })
            else:
                print(f"     ❌ Claude did not respond")
                results.append({
                    'ticker': ticker,
                    'date': bearish_date_str,
                    'error': 'No response from Claude'
                })
                
        except Exception as e:
            print(f"     ❌ Error calling Claude: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'ticker': ticker,
                'date': bearish_date_str,
                'error': str(e)
            })
        
        print("-" * 80)
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    for result in results:
        ticker = result['ticker']
        date = result['date']
        if 'error' in result:
            print(f"❌ {ticker} ({date}): Error - {result['error']}")
        else:
            score = result.get('score', 'N/A')
            found = result.get('found_keywords', [])
            missing = result.get('missing_keywords', [])
            no_news = result.get('mentions_no_news', False)
            
            status = "✅" if not no_news and found else "⚠️"
            print(f"{status} {ticker} ({date}): Score {score}/10")
            if found:
                print(f"   Found keywords: {', '.join(found)}")
            if missing:
                print(f"   Missing keywords: {', '.join(missing)}")
            if no_news:
                print(f"   ⚠️  Claude reported it couldn't find news")
    
    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    # Check if dates are being sent correctly
    print("1. Date Format Check:")
    print("   - Bearish date should be in format: YYYY-MM-DD")
    print("   - Example: 2025-12-16")
    print()
    
    # Check if Claude is actually searching
    print("2. Claude Web Search:")
    print("   - Claude should search for: '[TICKER] stock drop [DATE]'")
    print("   - Example: 'HUM stock drop December 16 2025'")
    print("   - If Claude says 'could not find', it may not be searching the web")
    print()
    
    # Suggest improvements
    print("3. Potential Issues:")
    print("   - Claude API may not have web search enabled")
    print("   - Date format might need to be more explicit (e.g., 'December 16, 2025')")
    print("   - Prompt might need to be more explicit about web searching")
    print()
    
    return len([r for r in results if 'error' not in r]) > 0

if __name__ == "__main__":
    success = test_claude_news_search()
    sys.exit(0 if success else 1)

