# Performance Optimization Summary

## Problem Identified

The app was taking **6.5 minutes** to process 278 articles, getting stuck at "Extracting company info..." after batch API calls completed.

### Root Causes

1. **CSV Parsing Failure (95% failure rate)**
   - Company names with commas (e.g., "Theravance Biopharma, Inc.") broke CSV parsing
   - Simple `split(',')` created 5 parts instead of 4, causing parsing errors
   - "neutral" direction was rejected (only "bullish"/"bearish" accepted)

2. **Slow Fallback Extraction**
   - When Claude failed (95% of articles), code fell back to `extract_company_name()`
   - This searched through **10,499 SEC EDGAR companies** sequentially
   - Average time: **1.4 seconds per article** = 389 seconds for 278 articles

## Solutions Implemented

### 1. Fixed CSV Parsing ✅

**Location:** `main.py` `get_ai_prediction_score_batch()` method

**Changes:**
- Parse from the **end backwards** (direction, score, ticker are always last 3 values)
- Company name is everything before the last 3 parts (handles commas correctly)
- Accept "neutral" direction by mapping it to "bullish" (neutral = no strong direction)

**Example:**
```python
# Before: "Theravance Biopharma, Inc., TBPH, 5, bullish"
# Split: ['Theravance Biopharma', 'Inc.', 'TBPH', '5', 'bullish'] ❌ (5 parts)

# After: Parse from end
# Direction: 'bullish' (last)
# Score: 5 (second to last)
# Ticker: 'TBPH' (third to last)
# Company: 'Theravance Biopharma, Inc.' (everything before) ✅
```

### 2. Optimized Company Name Extraction ✅

**Location:** `main.py` `extract_company_name()` method

**Changes:**
- Added `candidate_companies` parameter
- For `bio_companies` event type, use the search query companies as candidates
- Try matching against **59 bio companies** first (fast) before falling back to **10,499 SEC EDGAR companies** (slow)

**Performance Impact:**
- Before: Searched 10,499 companies for every article (~1.4s/article)
- After: Searches 59 bio companies first (~0.01s if found, ~1.4s only if not found)
- **Expected speedup: 10-100x for bio_companies articles**

### 3. Added Error Logging ✅

**Location:** `main.py` `get_ai_prediction_score_batch()` method

**Changes:**
- Log API errors (non-200 status codes)
- Log parsing failures (for debugging)
- Log success rates for batches > 10 articles
- Log exceptions with traceback (for small batches)

## Expected Performance Improvements

### Before Optimization
- Batch API calls: **6.37s** (fast ✅)
- Claude success rate: **5%** (14/278 articles)
- Fallback extraction: **389s** (264 articles × 1.4s)
- **Total: ~6.5 minutes**

### After Optimization
- Batch API calls: **6.37s** (unchanged)
- Claude success rate: **~80-90%** (expected, with fixed parsing)
- Fallback extraction: **~40-60s** (only 20-30% of articles, and faster for bio_companies)
- **Total: ~1-2 minutes** (3-6x faster)

## Testing

Created `test_optimizations.py` to verify:
1. ✅ CSV parsing handles company names with commas
2. ✅ "neutral" direction is accepted
3. ✅ Candidate companies optimization works for bio_companies

## Next Steps

1. **Monitor performance** in production to verify actual speedup
2. **Consider further optimizations:**
   - Cache company name → ticker mappings
   - Parallelize extraction for multiple articles
   - Skip Prixe.io availability checks if ticker is known valid

## Files Modified

- `main.py`: 
  - `get_ai_prediction_score_batch()`: Fixed CSV parsing, added error logging
  - `extract_company_name()`: Added candidate_companies parameter
  - `extract_layoff_info()`: Pass bio_companies list to extract_company_name()

