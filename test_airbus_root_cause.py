#!/usr/bin/env python3
"""Unit test to find the exact root cause of why 2 Airbus articles are filtered out"""

from main import LayoffTracker
from datetime import datetime, timezone

print("=" * 80)
print("Airbus Articles Root Cause Analysis")
print("=" * 80)

tracker = LayoffTracker()

# The 3 Airbus articles we know about
airbus_articles = [
    {
        'title': "Airbus to inspect some planes over 'quality issue' with panels - BBC",
        'description': "Airbus SE has announced it will inspect some of its aircraft over quality issues with panels. The European aerospace company said the inspections would affect a number of planes.",
        'url': 'https://www.bbc.com/news/business-123456',
        'publishedAt': '2025-12-01T10:00:00Z',
        'source': {'name': 'BBC'}
    },
    {
        'title': "Airbus News Today: Recall of 6,000 Jets Clears Safety Hurdle, Shares Tumble - Meyka",
        'description': "Airbus SE announced a recall of 6,000 jets that clears a major safety hurdle. The company's shares tumbled following the announcement.",
        'url': 'https://meyka.com/airbus-recall',
        'publishedAt': '2025-12-02T10:33:21Z',
        'source': {'name': 'Meyka'}
    },
    {
        'title': "Airbus Software: Which Companies Withdrew A320s for Inspection – What Happened",
        'description': "Several airlines have withdrawn Airbus A320 aircraft for inspection following software issues. Here's what happened and which companies are affected.",
        'url': 'https://example.com/airbus-software',
        'publishedAt': '2025-12-01T14:00:00Z',
        'source': {'name': 'Example'}
    }
]

print(f"\n📰 Testing {len(airbus_articles)} Airbus articles through extract_layoff_info()...")
print()

results = []

for i, article in enumerate(airbus_articles, 1):
    print(f"{'='*80}")
    print(f"Article {i}: {article['title'][:70]}...")
    print(f"{'='*80}")
    
    result = {
        'title': article['title'],
        'steps': {}
    }
    
    # Step 1: Check if article matches event type
    print(f"\n[Step 1] Event Type Matching...")
    from main import EVENT_TYPES
    event_types = ['recall']
    all_keywords = []
    for event_type in event_types:
        if event_type in EVENT_TYPES:
            all_keywords.extend(EVENT_TYPES[event_type].get('keywords', []))
    
    title_lower = article['title'].lower()
    description_lower = article.get('description', '').lower()
    matches = any(keyword.lower() in title_lower or keyword.lower() in description_lower for keyword in all_keywords)
    result['steps']['event_type_match'] = matches
    print(f"   {'✅' if matches else '❌'} Matches event type: {matches}")
    
    if not matches:
        print(f"   ⚠️  Article filtered out at Step 1: Event type mismatch")
        results.append(result)
        continue
    
    # Step 2: Date filtering
    print(f"\n[Step 2] Date Filtering...")
    from config import LOOKBACK_DAYS
    from dateutil import parser
    try:
        article_date = parser.parse(article['publishedAt'])
        if article_date.tzinfo is None:
            article_date = article_date.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_ago = (now - article_date).days
        within_lookback = days_ago <= LOOKBACK_DAYS
        result['steps']['date_filter'] = within_lookback
        print(f"   {'✅' if within_lookback else '❌'} Within {LOOKBACK_DAYS} days: {within_lookback} (published {days_ago} days ago)")
    except Exception as e:
        result['steps']['date_filter'] = False
        print(f"   ❌ Date parsing failed: {e}")
        results.append(result)
        continue
    
    if not within_lookback:
        print(f"   ⚠️  Article filtered out at Step 2: Outside lookback period")
        results.append(result)
        continue
    
    # Step 3: Claude extraction
    print(f"\n[Step 3] Claude API Extraction...")
    try:
        ai_result = tracker.get_ai_prediction_score(
            title=article['title'],
            description=article.get('description', ''),
            url=article['url']
        )
        
        if ai_result:
            company_name = ai_result.get('company_name')
            ticker = ai_result.get('ticker')
            result['steps']['claude_extraction'] = {
                'success': True,
                'company_name': company_name,
                'ticker': ticker
            }
            print(f"   ✅ Claude extraction successful")
            print(f"      Company: {company_name}")
            print(f"      Ticker: {ticker}")
        else:
            result['steps']['claude_extraction'] = {'success': False, 'reason': 'AI result is None'}
            print(f"   ❌ Claude extraction failed: AI result is None")
    except Exception as e:
        result['steps']['claude_extraction'] = {'success': False, 'reason': str(e)}
        print(f"   ❌ Claude extraction failed: {e}")
    
    # Step 4: Fallback extraction (if Claude failed)
    if not result['steps'].get('claude_extraction', {}).get('success'):
        print(f"\n[Step 4] Fallback Company/Ticker Extraction...")
        try:
            company_name = tracker.extract_company_name(article['title'], article.get('description', ''))
            if company_name:
                ticker = tracker.get_stock_ticker(company_name)
                result['steps']['fallback_extraction'] = {
                    'success': True,
                    'company_name': company_name,
                    'ticker': ticker
                }
                print(f"   ✅ Fallback extraction successful")
                print(f"      Company: {company_name}")
                print(f"      Ticker: {ticker}")
            else:
                result['steps']['fallback_extraction'] = {'success': False, 'reason': 'No company name found'}
                print(f"   ❌ Fallback extraction failed: No company name found")
        except Exception as e:
            result['steps']['fallback_extraction'] = {'success': False, 'reason': str(e)}
            print(f"   ❌ Fallback extraction failed: {e}")
    
    # Step 5: Check if company name exists
    print(f"\n[Step 5] Company Name Validation...")
    final_company = None
    if result['steps'].get('claude_extraction', {}).get('success'):
        final_company = result['steps']['claude_extraction']['company_name']
    elif result['steps'].get('fallback_extraction', {}).get('success'):
        final_company = result['steps']['fallback_extraction']['company_name']
    
    if final_company:
        result['steps']['company_name_validation'] = True
        print(f"   ✅ Company name exists: {final_company}")
    else:
        result['steps']['company_name_validation'] = False
        print(f"   ❌ Company name validation failed: No company name")
        print(f"   ⚠️  Article filtered out at Step 5: No company name")
        results.append(result)
        continue
    
    # Step 6: Check if ticker exists
    print(f"\n[Step 6] Ticker Validation...")
    final_ticker = None
    if result['steps'].get('claude_extraction', {}).get('success'):
        final_ticker = result['steps']['claude_extraction']['ticker']
    elif result['steps'].get('fallback_extraction', {}).get('success'):
        final_ticker = result['steps']['fallback_extraction']['ticker']
    
    if not final_ticker or final_ticker == 'N/A':
        result['steps']['ticker_validation'] = False
        print(f"   ❌ Ticker validation failed: Ticker is None or 'N/A'")
        print(f"   ⚠️  Article filtered out at Step 6: No ticker (private company)")
        results.append(result)
        continue
    
    result['steps']['ticker_validation'] = True
    print(f"   ✅ Ticker exists: {final_ticker}")
    
    # Step 7: Check if ticker is available in Prixe.io
    print(f"\n[Step 7] Ticker Availability Check...")
    try:
        is_available = tracker._is_ticker_available(final_ticker)
        result['steps']['ticker_availability'] = is_available
        if is_available:
            print(f"   ✅ Ticker is available in Prixe.io: {final_ticker}")
        else:
            print(f"   ❌ Ticker is NOT available in Prixe.io: {final_ticker}")
            print(f"   ⚠️  Article filtered out at Step 7: Ticker not available")
            results.append(result)
            continue
    except Exception as e:
        result['steps']['ticker_availability'] = False
        print(f"   ❌ Ticker availability check failed: {e}")
        results.append(result)
        continue
    
    # If we get here, the article should pass
    result['steps']['final_status'] = 'PASSED'
    print(f"\n   ✅✅✅ Article PASSED all filters!")
    results.append(result)

# Summary
print(f"\n{'='*80}")
print("ROOT CAUSE ANALYSIS SUMMARY")
print(f"{'='*80}")

for i, result in enumerate(results, 1):
    print(f"\nArticle {i}: {result['title'][:60]}...")
    print(f"   Final Status: {result['steps'].get('final_status', 'FILTERED OUT')}")
    
    if result['steps'].get('final_status') != 'PASSED':
        # Find the first step that failed
        failed_step = None
        for step_name, step_result in result['steps'].items():
            if step_result is False or (isinstance(step_result, dict) and not step_result.get('success', True)):
                failed_step = step_name
                break
        
        if failed_step:
            print(f"   ❌ ROOT CAUSE: Failed at {failed_step}")
            if isinstance(result['steps'][failed_step], dict):
                print(f"      Reason: {result['steps'][failed_step].get('reason', 'Unknown')}")
        else:
            print(f"   ❌ ROOT CAUSE: Unknown (check steps above)")

print(f"\n{'='*80}")

