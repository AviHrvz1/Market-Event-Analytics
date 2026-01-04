#!/usr/bin/env python3
"""Diagnostic script to track where articles are filtered out during processing"""

from main import LayoffTracker
from datetime import datetime, timezone, timedelta
from config import LOOKBACK_DAYS, MAX_ARTICLES_TO_PROCESS
from collections import defaultdict

print("=" * 80)
print("Article Filtering Diagnostic Tool")
print("=" * 80)
print()

# Initialize tracker
tracker = LayoffTracker()

# Statistics tracking
stats = {
    'initial_articles': 0,
    'after_event_matching': 0,
    'after_date_filtering': 0,
    'after_claude_extraction': 0,
    'after_fallback_extraction': 0,
    'after_company_validation': 0,
    'after_ticker_validation': 0,
    'after_prixe_check': 0,
    'after_deduplication': 0,
    'final_companies': 0
}

# Detailed tracking
filtered_articles = {
    'event_mismatch': [],
    'date_too_old': [],
    'date_parse_failed': [],
    'claude_failed': [],
    'fallback_no_company': [],
    'no_company_name': [],
    'no_ticker_private': [],
    'ticker_not_available': [],
    'deduplication': []
}

companies_at_stage = {
    'after_claude': set(),
    'after_fallback': set(),
    'after_ticker_validation': set(),
    'after_prixe_check': set(),
    'final': set()
}

# Fetch articles (same as main flow)
print("📰 Step 1: Fetching articles from sources...")
event_types = ['layoff_event']  # Default, can be changed
selected_sources = ['google_news']  # Default, can be changed

articles, source_stats = tracker.search_all_realtime_sources(
    event_types=event_types,
    selected_sources=selected_sources
)

stats['initial_articles'] = len(articles)
print(f"   ✅ Retrieved {len(articles)} articles")
print(f"   Source statistics:")
for key, stat in source_stats.items():
    print(f"      {stat['name']}: {stat['total']} total, {stat['matched']} matched")

# Sort by date
def parse_date(date_str):
    if not date_str:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        from dateutil import parser
        return parser.parse(date_str).replace(tzinfo=timezone.utc)
    except:
        return datetime.min.replace(tzinfo=timezone.utc)

articles.sort(key=lambda x: parse_date(x.get('publishedAt', '')), reverse=True)

# Limit to MAX_ARTICLES_TO_PROCESS
if len(articles) > MAX_ARTICLES_TO_PROCESS:
    print(f"\n   ⚠️  Limiting to {MAX_ARTICLES_TO_PROCESS} most recent articles")
    articles = articles[:MAX_ARTICLES_TO_PROCESS]

print(f"\n📊 Step 2: Processing articles through filtering pipeline...")
print(f"   Processing {len(articles)} articles...")
print()

# Process each article and track filtering
articles_after_event = []
articles_after_date = []
articles_after_claude = []
articles_after_fallback = []
articles_after_company = []
articles_after_ticker = []
articles_after_prixe = []
extracted_layoffs = []

for i, article in enumerate(articles, 1):
    title = article.get('title', '')
    description = article.get('description', '')
    published_at = article.get('publishedAt', '')
    url = article.get('url', '')
    
    # Step 1: Event type matching
    matches_any = False
    if article.get('event_type') in event_types and article.get('source', {}).get('name') == 'Google News':
        matches_any = True
    else:
        for event_type in event_types:
            if tracker.matches_event_type(article, event_type):
                matches_any = True
                break
    
    if not matches_any:
        filtered_articles['event_mismatch'].append({
            'title': title[:60],
            'url': url
        })
        continue
    
    articles_after_event.append(article)
    
    # Step 2: Date filtering
    try:
        article_date = None
        if published_at:
            try:
                article_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except:
                try:
                    from dateutil import parser
                    article_date = parser.parse(published_at)
                except:
                    pass
        
        if article_date:
            if article_date.tzinfo is None:
                article_date = article_date.replace(tzinfo=timezone.utc)
            else:
                article_date = article_date.astimezone(timezone.utc)
            
            now = datetime.now(timezone.utc)
            days_ago = (now - article_date).days
            if days_ago > LOOKBACK_DAYS:
                filtered_articles['date_too_old'].append({
                    'title': title[:60],
                    'days_ago': days_ago,
                    'url': url
                })
                continue
        else:
            # Date parsing failed
            filtered_articles['date_parse_failed'].append({
                'title': title[:60],
                'published_at': published_at,
                'url': url
            })
            continue
    except Exception as e:
        filtered_articles['date_parse_failed'].append({
            'title': title[:60],
            'error': str(e),
            'url': url
        })
        continue
    
    articles_after_date.append(article)
    
    # Step 3: Claude extraction
    ai_result = tracker.get_ai_prediction_score(
        title=title,
        description=description,
        url=url
    )
    
    company_name = None
    ticker = None
    
    if ai_result and ai_result.get('company_name'):
        company_name = ai_result.get('company_name')
        ticker = ai_result.get('ticker')
        companies_at_stage['after_claude'].add(company_name)
        articles_after_claude.append({
            'article': article,
            'company': company_name,
            'ticker': ticker,
            'method': 'claude'
        })
    else:
        # Step 4: Fallback extraction
        company_name = tracker.extract_company_name(title, description)
        if company_name:
            ticker = tracker.get_stock_ticker(company_name)
            companies_at_stage['after_fallback'].add(company_name)
            articles_after_fallback.append({
                'article': article,
                'company': company_name,
                'ticker': ticker,
                'method': 'fallback'
            })
        else:
            filtered_articles['fallback_no_company'].append({
                'title': title[:60],
                'url': url
            })
            continue
    
    articles_after_company.append({
        'article': article,
        'company': company_name,
        'ticker': ticker
    })
    
    # Step 5: Company name validation
    if not company_name:
        filtered_articles['no_company_name'].append({
            'title': title[:60],
            'url': url
        })
        continue
    
    # Step 6: Ticker validation (private companies)
    if not ticker or ticker == 'N/A':
        filtered_articles['no_ticker_private'].append({
            'title': title[:60],
            'company': company_name,
            'url': url
        })
        continue
    
    companies_at_stage['after_ticker_validation'].add(company_name)
    articles_after_ticker.append({
        'article': article,
        'company': company_name,
        'ticker': ticker
    })
    
    # Step 7: Prixe.io availability check
    if not tracker._is_ticker_available(ticker):
        filtered_articles['ticker_not_available'].append({
            'title': title[:60],
            'company': company_name,
            'ticker': ticker,
            'url': url
        })
        continue
    
    companies_at_stage['after_prixe_check'].add(company_name)
    articles_after_prixe.append({
        'article': article,
        'company': company_name,
        'ticker': ticker
    })
    
    # Create layoff info structure (simplified)
    layoff_info = {
        'company_name': company_name,
        'stock_ticker': ticker,
        'title': title,
        'url': url,
        'datetime': article_date if article_date else datetime.now(timezone.utc),
        'publishedAt': published_at
    }
    extracted_layoffs.append(layoff_info)

# Step 8: Deduplication (keep up to 3 per ticker)
ticker_to_layoffs = {}
for layoff in extracted_layoffs:
    ticker = layoff.get('stock_ticker')
    if not ticker:
        continue
    
    if ticker not in ticker_to_layoffs:
        ticker_to_layoffs[ticker] = []
    
    ticker_to_layoffs[ticker].append(layoff)

# Sort and keep top 3 per ticker
final_layoffs = []
deduplication_count = 0
for ticker, layoffs_list in ticker_to_layoffs.items():
    layoffs_list.sort(key=lambda x: x.get('datetime') or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    final_layoffs.extend(layoffs_list[:3])
    if len(layoffs_list) > 3:
        deduplication_count += len(layoffs_list) - 3
        filtered_articles['deduplication'].extend([
            {
                'title': l.get('title', '')[:60],
                'company': l.get('company_name'),
                'ticker': ticker
            }
            for l in layoffs_list[3:]
        ])

# Update stats
stats['after_event_matching'] = len(articles_after_event)
stats['after_date_filtering'] = len(articles_after_date)
stats['after_claude_extraction'] = len(articles_after_claude)
stats['after_fallback_extraction'] = len(articles_after_fallback)
stats['after_company_validation'] = len(articles_after_company)
stats['after_ticker_validation'] = len(articles_after_ticker)
stats['after_prixe_check'] = len(articles_after_prixe)
stats['after_deduplication'] = len(final_layoffs)
stats['final_companies'] = len(set(l.get('company_name') for l in final_layoffs))

# Print summary
print("=" * 80)
print("FILTERING SUMMARY")
print("=" * 80)
print()
print(f"Initial articles:                    {stats['initial_articles']:4d}")
print(f"After event type matching:            {stats['after_event_matching']:4d}  (filtered: {stats['initial_articles'] - stats['after_event_matching']:4d})")
print(f"After date filtering (≤{LOOKBACK_DAYS} days):    {stats['after_date_filtering']:4d}  (filtered: {stats['after_event_matching'] - stats['after_date_filtering']:4d})")
print(f"After Claude extraction:              {stats['after_claude_extraction']:4d}  (filtered: {stats['after_date_filtering'] - stats['after_claude_extraction']:4d})")
print(f"After fallback extraction:            {stats['after_fallback_extraction']:4d}  (filtered: {stats['after_date_filtering'] - stats['after_fallback_extraction']:4d})")
print(f"After company validation:              {stats['after_company_validation']:4d}  (filtered: {stats['after_date_filtering'] - stats['after_company_validation']:4d})")
print(f"After ticker validation:              {stats['after_ticker_validation']:4d}  (filtered: {stats['after_company_validation'] - stats['after_ticker_validation']:4d})")
print(f"After Prixe.io check:                 {stats['after_prixe_check']:4d}  (filtered: {stats['after_ticker_validation'] - stats['after_prixe_check']:4d})")
print(f"After deduplication (3 per ticker):   {stats['after_deduplication']:4d}  (filtered: {deduplication_count:4d})")
print()
print(f"Final companies found:                {stats['final_companies']:4d}")
print()

# Detailed breakdown
print("=" * 80)
print("DETAILED FILTERING BREAKDOWN")
print("=" * 80)
print()

filter_reasons = {
    'event_mismatch': 'Event type mismatch',
    'date_too_old': f'Date too old (> {LOOKBACK_DAYS} days)',
    'date_parse_failed': 'Date parsing failed',
    'claude_failed': 'Claude extraction failed (no company/ticker)',
    'fallback_no_company': 'Fallback extraction failed (no company)',
    'no_company_name': 'No company name found',
    'no_ticker_private': 'No ticker (private company)',
    'ticker_not_available': 'Ticker not available in Prixe.io',
    'deduplication': 'Deduplication (kept only 3 per ticker)'
}

for reason, label in filter_reasons.items():
    count = len(filtered_articles[reason])
    if count > 0:
        print(f"{label}: {count} articles")
        # Show first 3 examples
        for i, example in enumerate(filtered_articles[reason][:3], 1):
            print(f"   {i}. {example.get('title', 'N/A')[:70]}")
            if 'company' in example:
                print(f"      Company: {example['company']}")
            if 'ticker' in example:
                print(f"      Ticker: {example['ticker']}")
            if 'days_ago' in example:
                print(f"      Days ago: {example['days_ago']}")
        if count > 3:
            print(f"   ... and {count - 3} more")
        print()

# Companies at each stage
print("=" * 80)
print("COMPANIES FOUND AT EACH STAGE")
print("=" * 80)
print()

print(f"After Claude extraction:     {len(companies_at_stage['after_claude']):3d} companies")
if companies_at_stage['after_claude']:
    print(f"   {', '.join(sorted(list(companies_at_stage['after_claude']))[:10])}")
    if len(companies_at_stage['after_claude']) > 10:
        print(f"   ... and {len(companies_at_stage['after_claude']) - 10} more")
print()

print(f"After fallback extraction:  {len(companies_at_stage['after_fallback']):3d} companies")
if companies_at_stage['after_fallback']:
    print(f"   {', '.join(sorted(list(companies_at_stage['after_fallback']))[:10])}")
    if len(companies_at_stage['after_fallback']) > 10:
        print(f"   ... and {len(companies_at_stage['after_fallback']) - 10} more")
print()

print(f"After ticker validation:     {len(companies_at_stage['after_ticker_validation']):3d} companies")
if companies_at_stage['after_ticker_validation']:
    print(f"   {', '.join(sorted(list(companies_at_stage['after_ticker_validation']))[:10])}")
    if len(companies_at_stage['after_ticker_validation']) > 10:
        print(f"   ... and {len(companies_at_stage['after_ticker_validation']) - 10} more")
print()

print(f"After Prixe.io check:        {len(companies_at_stage['after_prixe_check']):3d} companies")
if companies_at_stage['after_prixe_check']:
    print(f"   {', '.join(sorted(list(companies_at_stage['after_prixe_check']))[:10])}")
    if len(companies_at_stage['after_prixe_check']) > 10:
        print(f"   ... and {len(companies_at_stage['after_prixe_check']) - 10} more")
print()

print(f"Final companies:            {stats['final_companies']:3d} companies")
final_companies_list = sorted(set(l.get('company_name') for l in final_layoffs))
if final_companies_list:
    print(f"   {', '.join(final_companies_list)}")
print()

# Final summary
print("=" * 80)
print("CONCLUSION")
print("=" * 80)
print()

total_filtered = stats['initial_articles'] - stats['after_deduplication']
filter_rate = (total_filtered / stats['initial_articles'] * 100) if stats['initial_articles'] > 0 else 0

print(f"Total articles filtered: {total_filtered} out of {stats['initial_articles']} ({filter_rate:.1f}%)")
print(f"Final articles kept: {stats['after_deduplication']} ({100 - filter_rate:.1f}%)")
print()

# Identify biggest bottlenecks
bottlenecks = []
if len(filtered_articles['claude_failed']) > 0:
    bottlenecks.append(('Claude extraction failures', len(filtered_articles['claude_failed'])))
if len(filtered_articles['no_ticker_private']) > 0:
    bottlenecks.append(('Private companies (no ticker)', len(filtered_articles['no_ticker_private'])))
if len(filtered_articles['ticker_not_available']) > 0:
    bottlenecks.append(('Ticker not in Prixe.io', len(filtered_articles['ticker_not_available'])))
if len(filtered_articles['date_too_old']) > 0:
    bottlenecks.append(('Date too old', len(filtered_articles['date_too_old'])))

if bottlenecks:
    bottlenecks.sort(key=lambda x: x[1], reverse=True)
    print("Top filtering bottlenecks:")
    for i, (reason, count) in enumerate(bottlenecks[:3], 1):
        print(f"   {i}. {reason}: {count} articles")

print()
print("=" * 80)

