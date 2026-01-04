# Real Estate Event Types - Expected Results

## Test Results Summary

Based on unittest analysis, here are the expected number of results for each real estate event type:

### Real Estate Good News
- **Total articles found by search**: ~1,700 articles
- **Articles with pre-matched company**: ~1,627 articles (95.7%)
- **Articles without pre-matched company**: ~73 articles (4.3%)

### Real Estate Bad News
- **Total articles found by search**: ~1,700 articles
- **Articles with pre-matched company**: ~1,627 articles (95.7%)
- **Articles without pre-matched company**: ~73 articles (4.3%)

## Important Note: Processing Limit

⚠️ **MAX_ARTICLES_TO_PROCESS is set to 300** (in `config.py`)

This means:
- Even though ~1,700 articles are found by search
- Only the **300 most recent articles** will be processed
- The remaining ~1,400 articles will be skipped

## Expected Final Results in UI

### Real Estate Good News
- **Expected articles in table**: **300 articles** (limited by MAX_ARTICLES_TO_PROCESS)
- **With company name**: ~287 articles (95% of 300)
- **Without company name**: ~13 articles (will show "Didn't find")
- **With ticker**: ~287 articles (most should have tickers)
- **Without ticker**: ~13 articles (will show "Didn't find")

### Real Estate Bad News
- **Expected articles in table**: **300 articles** (limited by MAX_ARTICLES_TO_PROCESS)
- **With company name**: ~287 articles (95% of 300)
- **Without company name**: ~13 articles (will show "Didn't find")
- **With ticker**: ~287 articles (most should have tickers)
- **Without ticker**: ~13 articles (will show "Didn't find")

## How It Works

1. **Search Phase**: 
   - Searches Google News using 85 real estate company names
   - Creates 17 search queries (5 companies per query)
   - Each query returns up to 100 articles
   - Total: ~1,700 articles found

2. **Processing Phase**:
   - Articles are sorted by date (most recent first)
   - Limited to 300 most recent articles (MAX_ARTICLES_TO_PROCESS)
   - Each article goes through extraction

3. **Extraction Phase**:
   - ~95% of articles are pre-tagged with company names from search
   - ~5% need company extraction (Claude API or fallback)
   - Ticker lookup for all companies found

4. **Display Phase**:
   - All 300 articles are shown in the UI
   - Articles without company/ticker show "Didn't find" in red italic text

## To See More Articles

If you want to see more than 300 articles, you can increase `MAX_ARTICLES_TO_PROCESS` in `config.py`:

```python
MAX_ARTICLES_TO_PROCESS = int(os.getenv('MAX_ARTICLES_TO_PROCESS', '1700'))  # Increased from 300
```

Note: Processing 1,700 articles will take significantly longer (several minutes) due to:
- Batch Claude API calls (rate limited)
- Ticker lookups
- Stock price fetching

## Test File

Run the test yourself:
```bash
python3 test_real_estate_final_count.py
```


