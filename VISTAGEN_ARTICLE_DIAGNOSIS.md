# Vistagen Phase 3 Trial Article - Diagnosis Results

## Article Details
- **Title**: "Vistagen announced that its Phase 3 trial failed"
- **Date**: December 17, 2024
- **Company**: Vistagen Therapeutics (VTGN)

## Test Results Summary

### ✅ Test 1: Company in List
- **Result**: ✅ **PASS**
- Vistagen IS in the bio companies list:
  - ✅ Found in `bio_companies` (all) list
  - ✅ Found in `bio_companies_small_cap` list
  - ❌ NOT in `bio_companies_mid_cap` list (expected - it's small-cap)

### ✅ Test 2: Event Type Matching
- **Result**: ✅ **PASS**
- Article WOULD match all bio event types:
  - ✅ `bio_companies`
  - ✅ `bio_companies_small_cap`
  - ✅ `bio_companies_mid_cap`

### ❌ Test 3: Date Range
- **Result**: ❌ **FAIL - ROOT CAUSE**
- **Target Date**: December 17, 2024
- **Today**: December 26, 2025
- **Days Ago**: 374 days
- **LOOKBACK_DAYS**: 120 days
- **Status**: ❌ **Article is OUTSIDE the 120-day lookback period**

### ❌ Test 4: Google News RSS Date Filtering
- **Result**: ❌ **FAIL**
- Google News RSS uses `when:120d` parameter
- Article is 374 days old → **Filtered out by Google News RSS**
- Even if fetched, would be filtered by `LOOKBACK_DAYS = 120`

## Root Cause

**The article is too old (374 days) to be included in the search results.**

The system has two date filters:
1. **Google News RSS**: Uses `when:120d` parameter (120 days lookback)
2. **Config LOOKBACK_DAYS**: 120 days (filters articles after fetching)

Since the article is 374 days old, it's excluded by both filters.

## Solutions

### Option 1: Increase LOOKBACK_DAYS (Quick Fix)
- Change `LOOKBACK_DAYS` in `config.py` from 120 to 400+ days
- **Pros**: Simple, will find older articles
- **Cons**: May fetch many more articles, slower processing

### Option 2: Make LOOKBACK_DAYS Configurable Per Event Type
- Allow different lookback periods for different event types
- **Pros**: More flexible, can have longer lookback for important events
- **Cons**: More complex configuration

### Option 3: Add Historical Article Search Mode
- Create a separate mode for searching historical articles (e.g., >120 days)
- **Pros**: Doesn't affect normal searches, can search specific date ranges
- **Cons**: Requires UI changes, more complex

## Recommendation

**Option 1** is the simplest solution. If you want to find articles from December 2024, increase `LOOKBACK_DAYS` to at least 400 days.

However, note that:
- Google News RSS may still limit results (though it can go back further than 120 days)
- Processing more articles will be slower
- Older articles may have less reliable stock price data (intraday data only works for last 60 days)

## Current Status

- ✅ Company is in the search list
- ✅ Article would match event type
- ❌ **Article is excluded due to date range (374 days > 120 days)**

