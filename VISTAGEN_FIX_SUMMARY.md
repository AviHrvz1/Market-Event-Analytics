# Vistagen Article Fix - Summary

## Issue
The Vistagen Phase 3 trial failure article from December 17, 2025 was not being found in search results.

## Root Cause
**Google News RSS query batch size was too large (25 companies per batch)**

When searching with `bio_companies_small_cap`, the system creates batches of company names using OR queries. The batch containing "VISTAGEN THERAPEUTICS" had 17 companies, and Google News RSS returned **0 articles** for that batch query.

**Why this happened:**
- Google News RSS has limits on the number of OR terms in a single query
- Batches of 25 companies (or even 17 companies) can exceed these limits
- This caused the batch with Vistagen to return 0 results, even though individual searches work

## Fix Applied
**Reduced batch size from 25 to 5 companies per query**

**File:** `main.py`
**Lines:** 4015 and 4370 (two occurrences)

**Change:**
```python
# Before:
batch_size = 25

# After:
batch_size = 5  # Reduced to avoid Google News RSS query limits
```

**Impact:**
- More batches are created (24 batches instead of 5 for 117 companies)
- Each batch is smaller and more reliable
- Vistagen articles are now found (19 articles found, up from 5)

## Verification

### Before Fix:
- Batch with Vistagen: **0 articles** returned
- Total Vistagen articles found: **5 articles**
- December 17 articles: **0 found**

### After Fix:
- Batch with Vistagen: **100 articles** returned (first batch)
- Total Vistagen articles found: **19 articles** (up from 5)
- December 17 articles: **Need to verify in full pipeline**

## Testing
Direct Google News RSS search confirms December 17, 2025 articles exist:
- "Vistagen phase 3 study sees placebo surprise..." (Dec 17, 19:44)
- "Vistagen Announces Topline Results from PALISADE-3..." (Dec 17, 13:30)
- "Vistagen's anxiety treatment fails to meet primary endpoint" (Dec 17, 08:00)
- And 7 more articles from December 17

## Status
✅ **FIXED** - Batch size reduced, articles are now being found

⚠️ **VERIFICATION NEEDED** - Need to run full pipeline to confirm December 17 articles make it through all filtering steps

## Next Steps
1. Run full `fetch_layoffs()` with `bio_companies_small_cap` event type
2. Verify December 17 articles appear in final results
3. Check if any additional filtering is removing these articles

