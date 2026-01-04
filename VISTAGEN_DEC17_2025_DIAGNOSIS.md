# Vistagen Phase 3 Trial Article - December 17, 2025 Diagnosis

## Article Details
- **Title**: "Vistagen announced that its Phase 3 trial failed"
- **Source**: MSN / VistaGen update
- **Date**: December 17, 2025 (9 days ago)
- **Company**: Vistagen Therapeutics (VTGN)

## Test Results Summary

### ✅ Test 1: Company in List
- **Result**: ✅ **PASS**
- Vistagen IS in the bio companies list:
  - ✅ Found in `bio_companies` (all) list
  - ✅ Found in `bio_companies_small_cap` list
  - ❌ NOT in `bio_companies_mid_cap` list (expected - it's small-cap)

### ✅ Test 2: Google News Search
- **Result**: ✅ **PASS**
- Google News CAN find the article with multiple search queries:
  - ✅ "Vistagen Phase 3 trial failed" - Found articles on Dec 17, 2025
  - ✅ "Vistagen Phase 3" - Found articles on Dec 17, 2025
  - ✅ "VTGN Phase 3" - Found articles on Dec 17, 2025
  - ✅ "VistaGen Phase 3" - Found articles on Dec 17, 2025

**Sample articles found:**
- "Vistagen phase 3 study sees placebo surprise, putting future of social anxiety..." (Dec 17, 2025 19:44:03 GMT)
- "Jefferies downgrades VistaGen stock rating to Hold on failed Phase III trial" (Dec 17, 2025 08:00:00 GMT)
- "Vistagen Announces Topline Results from PALISADE-3 Phase 3 Public Speaking Chall..." (Dec 17, 2025 13:30:00 GMT)

### ✅ Test 3: Date Range
- **Result**: ✅ **PASS**
- **Target Date**: December 17, 2025
- **Today**: December 26, 2025
- **Days Ago**: 9 days
- **LOOKBACK_DAYS**: 120 days
- **Status**: ✅ **Date is WITHIN the 120-day lookback period**

### ✅ Test 4: Event Type Matching
- **Result**: ✅ **PASS**
- Article WOULD match all bio event types:
  - ✅ `bio_companies`
  - ✅ `bio_companies_small_cap`
  - ✅ `bio_companies_mid_cap`

### ⚠️ Test 5: Full Search Simulation
- **Result**: ⚠️ **PARTIAL**
- **Search Status**: ✅ Search is working - found 169 total articles
- **Vistagen Articles Found**: ✅ Found 5 Vistagen articles
- **Issue**: Articles don't have dates in the parsed results
  - This suggests the date parsing from Google News RSS might be failing
  - Or dates are being lost during article processing

**Articles found:**
1. "Vistagen Therapeutics: Intranasal Pherines And A Make-Or-Break 2026 (NASDAQ:VTGN" - No date
2. "Vistagen Therapeutics, Inc. (VTGN) Eyes Breakthrough with Phase 3 Social Anxiety" - No date
3. "VTGN News Today | Why did VistaGen Therapeutics stock go up today? - MarketBeat" - No date
4. "VistaGen Therapeutics (VTGN) Stock Price, News & Analysis - MarketBeat" - No date
5. "VistaGen Therapeutics (NASDAQ:VTGN) Rating Lowered to "Sell" at Wall Street Zen" - No date

### ✅ Test 6: Google News RSS Date Filtering
- **Result**: ✅ **PASS**
- Google News RSS uses `when:120d` parameter
- Article is 9 days old → ✅ **Within Google News RSS 120 day limit**
- ✅ Date is within config LOOKBACK_DAYS (120)

## Root Cause Analysis

### What's Working ✅
1. ✅ Vistagen is in the company list
2. ✅ Google News can find the articles
3. ✅ Date is within range (9 days < 120 days)
4. ✅ Event type matching works
5. ✅ Search queries are being executed

### Potential Issues ⚠️

**Issue 1: Date Parsing**
- Articles are being found but dates aren't being extracted properly
- Google News RSS returns dates in `pubDate` field
- The parsing might be failing, causing articles to be filtered out later

**Issue 2: Article Processing Pipeline**
- Articles might be filtered out during:
  - Company/ticker extraction
  - Date validation
  - Event type matching (though test shows it should match)

**Issue 3: Search Query Construction**
- The search uses `"VISTAGEN THERAPEUTICS"` in the query
- But the article might use "VistaGen" (capital G) or "Vistagen" (lowercase)
- Google News should handle this, but exact matching might be stricter

## Recommendations

### 1. Check Date Parsing
- Verify that Google News RSS `pubDate` fields are being parsed correctly
- Check if dates are being lost during article processing

### 2. Check Article Filtering Pipeline
- Run the full `fetch_layoffs()` with `bio_companies_small_cap` event type
- Check logs to see where articles are being filtered out
- Verify company/ticker extraction is working for Vistagen

### 3. Verify Search Query
- The search query includes `"VISTAGEN THERAPEUTICS"` which should match
- But verify that Google News is actually returning articles with this exact phrase

### 4. Check for Duplicate Filtering
- Articles might be filtered as duplicates
- Or limited by the 3-per-ticker limit

## Next Steps

1. Run the actual `fetch_layoffs()` function with `bio_companies_small_cap` event type
2. Check the logs to see where Vistagen articles are being filtered
3. Verify date parsing is working correctly
4. Check if company/ticker extraction is finding "Vistagen Therapeutics" and "VTGN"

## Conclusion

The article **should** be found because:
- ✅ Company is in the list
- ✅ Date is within range (9 days < 120 days)
- ✅ Google News can find it
- ✅ Event type matching works

The issue is likely in the **article processing pipeline** - articles are being found but filtered out during:
- Date parsing/extraction
- Company/ticker extraction
- Or duplicate filtering

