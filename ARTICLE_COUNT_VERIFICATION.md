# Article Count Verification - UI Shows 114 Articles

## Test Created

I've created two unit tests to verify if the UI showing 114 articles is correct:

1. **`test_article_count_verification.py`** - Comprehensive test that checks each stage
2. **`test_ui_count_verification.py`** - Simplified test that runs full pipeline and compares counts

## What the Tests Check

### Pipeline Stages:

1. **Initial Fetch**: Articles fetched from Google News RSS
   - Expected: 300+ articles (limited by MAX_ARTICLES_TO_PROCESS = 300)

2. **Company/Ticker Extraction**: 
   - Articles that successfully extract company name and ticker
   - Pre-tagged articles (from search query) should pass easily
   - Non-pre-tagged articles need Claude extraction

3. **3-Per-Ticker Limit**:
   - Maximum 3 articles per unique ticker
   - If 50 unique tickers → max 150 articles
   - If 38 unique tickers → max 114 articles ✅

4. **Final Filtering**:
   - Date range validation
   - Ticker availability check
   - Private company filter (no ticker)
   - Invalid ticker filter

## Expected Count Calculation

If UI shows **114 articles**, this suggests:
- **38 unique tickers** × 3 articles per ticker = 114 articles

OR

- **Fewer tickers** with some having fewer than 3 articles

## Potential Issues to Check

### 1. 3-Per-Ticker Limit
```python
# Line ~5078: Keep only top 3 per ticker
layoffs_list.sort(key=lambda x: x.get('datetime') or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
extracted_layoffs.extend(layoffs_list[:3])
```

### 2. Ticker Validation
```python
# Line ~745: Filter invalid tickers
if not self._is_ticker_available(ticker):
    return None
```

### 3. Private Company Filter
```python
# Line ~740: Filter private companies
if not ticker or ticker == 'N/A':
    return None
```

### 4. Date Range Filter
- Google News RSS uses `when:120d` parameter
- Articles outside 120 days are filtered

## Running the Test

The test is currently running in the background. It will:
1. Fetch articles from Google News RSS
2. Extract company/ticker info
3. Apply all filters
4. Count final articles
5. Compare with UI count (114)

## Expected Results

- **If count = 114**: ✅ UI is correct, no articles omitted
- **If count > 114**: ⚠️ Some articles are being filtered by UI (client-side filtering)
- **If count < 114**: ⚠️ Some articles are being omitted in the pipeline (server-side issue)

## Next Steps

Wait for test to complete, then check:
- Final count vs 114
- Breakdown by ticker
- Any filtering issues identified

