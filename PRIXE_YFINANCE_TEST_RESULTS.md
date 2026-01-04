# Prixe.io vs yfinance Test Results

## Test Summary

**Date:** Test run for tickers returning 404 from Prixe.io
**Tickers Tested:** GILD, NCOX, PLTN, IMMU, NMTR

## Findings

### Prixe.io Configuration
- **Base URL:** `https://api.prixe.io`
- **Endpoint:** `/api/price`
- **Method:** POST
- **Full URL:** `https://api.prixe.io/api/price`

### Test Results

**Prixe.io:**
- All 5 tickers returning 404 errors
- Error message: "Prixe.io API endpoint not found: /api/price (404)"
- This suggests either:
  1. The endpoint `/api/price` doesn't exist
  2. The API has changed
  3. These tickers don't exist in Prixe.io database

**yfinance:**
- Test was blocked by SSL certificate issues in sandbox
- Cannot determine if yfinance can find these tickers from this test

## What `extract_layoff_info` Does

The `extract_layoff_info` function in `main.py`:

1. **Event Type Matching** (lines 667-683)
   - Checks if article matches requested event types
   - Returns `None` if no match

2. **Date Filtering** (lines 685-704) - **NOW REMOVED**
   - Previously filtered articles older than 125 days
   - Now allows all articles through

3. **Company/Ticker Extraction** (lines 706-823)
   - Tries multiple methods:
     - Pre-tagged companies (from search query)
     - Claude AI batch extraction
     - Fallback pattern matching
   - Now allows `None` for company/ticker (UI shows "Didn't find")

4. **Returns Article Info** (lines 946-965)
   - Returns dict with all extracted info
   - Includes company_name, stock_ticker, date, AI prediction, etc.

## Recommendations

### For Prixe.io 404 Errors:

1. **Check Prixe.io Documentation**
   - Verify if `/api/price` is the correct endpoint
   - Check if endpoint has changed to `/api/historical` or another path
   - Verify API key has access to these tickers

2. **Alternative Endpoints to Try:**
   - `/api/historical`
   - `/api/v1/price`
   - `/api/v1/historical`
   - `/api/stock/price`

3. **yfinance as Fallback:**
   - If yfinance can find these tickers, implement fallback logic
   - Use yfinance when Prixe.io returns 404
   - This would require modifying `_get_prixe_price_data` or similar methods

### For Company Extraction Failures:

- All 51 articles are now shown (no filtering)
- Articles without company names show "Didn't find" in UI
- Extract button works for all articles for manual review

## Next Steps

1. Verify Prixe.io endpoint is correct (check documentation)
2. Test yfinance in non-sandbox environment to see if it can find these tickers
3. If yfinance works, implement fallback logic
4. Consider alternative data sources for tickers not in Prixe.io

