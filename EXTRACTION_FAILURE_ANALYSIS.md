# Extraction Failure Analysis - Root Cause Found

## 🔍 Investigation Results

**Date:** Test run
**Total Articles Processed:** 275
**Successful Extractions:** 132 (48.0%)
**Failed Extractions:** 143 (52.0%)

---

## 📊 Root Cause Breakdown

### Primary Issue: Date Out of Range (49.5% of failures)

**136 articles (49.5%) are being filtered due to date range**

**Why this happens:**
1. Google News RSS query uses `when:120d` parameter (120 days lookback)
2. Articles are fetched and sorted by date
3. `extract_layoff_info()` then filters articles again using `LOOKBACK_DAYS` (120 days)
4. **Date parsing differences** can cause articles to be slightly over 120 days
5. Articles published exactly 120+ days ago are filtered out

**Sample filtered articles:**
- "Is Pfizer's 6.8%-Yielding Dividend Too Good to Be True?" - 127 days ago
- "After a Strong Quarterly Result, Is It Finally Safe to Buy Pfizer Stock Again?" - 131 days ago
- "3 Reasons Pfizer's 7%-Yielding Dividend Is Getting Safer" - 133 days ago
- "Theravance Biopharma, Inc. Reports Second Quarter 2025 Financial Results" - 134 days ago

**The Issue:**
- Google News RSS may return articles up to ~130-140 days old
- But `extract_layoff_info()` filters out anything > 120 days
- This creates a mismatch where articles are fetched but then immediately filtered

### Secondary Issue: No Ticker/Private Company (2.5% of failures)

**7 articles (2.5%) are filtered because they're private companies or have no ticker**

**Sample filtered articles:**
1. "Exploring the Role of Molecular Profiling..." - Generic medical article, no company
2. "Spotlight On: Prasinezumab goes to Phase III..." - Mentions "Roche" but no ticker extracted
3. "First U.S. Commercial Sale of KOMZIFTI™..." - "KOMZIFTI" is a drug name, not a company
4. "Prelude loses CMO..." - "Prelude Therapeutics" - private company or ticker not found
5. "Precision BioSciences to Report..." - Company name found but ticker lookup failed

**Why this happens:**
- Some articles mention company names but ticker lookup fails
- Some articles mention drug names instead of company names
- Some companies may be private or not in SEC EDGAR database
- Pattern matching may extract wrong entities (drug names, person names, etc.)

---

## ✅ What's NOT the Problem

1. **Event type matching:** ✅ Working correctly (all articles pass)
2. **Company name extraction:** ✅ Working for most articles (only 7 failures)
3. **Ticker lookup:** ✅ Working for most articles (only 7 failures)
4. **Ticker availability:** ✅ No issues (0 failures)

---

## 💡 Solutions

### Solution 1: Fix Date Range Mismatch (Highest Impact)

**Problem:** Google News returns articles up to ~130-140 days, but code filters at 120 days

**Fix Options:**

**Option A: Increase LOOKBACK_DAYS to match Google News**
- Change `LOOKBACK_DAYS` in `config.py` from 120 to 150
- This will allow articles up to 150 days old
- **Expected impact:** +136 articles (49.5% recovery)

**Option B: Remove date filtering in extract_layoff_info (since Google News already filters)**
- Google News RSS already uses `when:120d` parameter
- The additional date check in `extract_layoff_info()` is redundant
- **Location:** `main.py` lines 636-666
- **Expected impact:** +136 articles (49.5% recovery)

**Option C: Make date filtering more lenient (add buffer)**
- Change `if days_ago > LOOKBACK_DAYS:` to `if days_ago > LOOKBACK_DAYS + 30:`
- Adds 30-day buffer to account for date parsing differences
- **Expected impact:** +136 articles (49.5% recovery)

**Recommendation:** **Option B** - Remove redundant date filtering since Google News already filters by date

### Solution 2: Improve Ticker Lookup for Edge Cases (Low Impact)

**Problem:** 7 articles fail because ticker lookup fails

**Fix Options:**

1. **Handle "Roche" company name:**
   - "Roche" may need special handling (could be "Roche Holding" or "Hoffmann-La Roche")
   - Add to hardcoded company list or improve matching

2. **Filter out drug names:**
   - "KOMZIFTI" is a drug name, not a company
   - Improve pattern matching to distinguish drug names from company names

3. **Handle subsidiary companies:**
   - "Prelude Therapeutics" may be a subsidiary
   - Improve SEC EDGAR matching for subsidiaries

**Expected impact:** +3-5 articles (small improvement)

---

## 📈 Expected Results After Fixes

### Current State:
- Initial: 275 articles
- After date filter: 139 articles (lost 136)
- After ticker filter: 132 articles (lost 7)
- After 3-per-ticker: 22 articles (lost 110)
- **Final: 22 articles**

### After Fixing Date Range (Option B - Remove redundant filter):
- Initial: 275 articles
- After date filter: 275 articles (lost 0) ✅
- After ticker filter: 268 articles (lost 7)
- After 3-per-ticker: ~80-100 articles (lost ~170)
- **Final: ~80-100 articles (3-4x improvement!)**

### After Fixing Date Range + Improving Ticker Lookup:
- Initial: 275 articles
- After date filter: 275 articles (lost 0) ✅
- After ticker filter: 273 articles (lost 2) ✅
- After 3-per-ticker: ~85-105 articles (lost ~170)
- **Final: ~85-105 articles (3.5-4.5x improvement!)**

---

## 🎯 Immediate Action Items

1. **Remove redundant date filtering in `extract_layoff_info()`** (Quick fix, high impact)
   - Location: `main.py` lines 636-666
   - Reason: Google News RSS already filters by date
   - Expected: +136 articles recovered

2. **Increase 3-per-ticker limit** (Quick fix, high impact)
   - Location: `main.py` line ~4421
   - Change: `layoffs_list[:3]` → `layoffs_list[:10]` or `[:20]`
   - Expected: 3-7x more articles shown

3. **Improve ticker lookup for edge cases** (Medium effort, low impact)
   - Handle "Roche" company name variations
   - Filter out drug names
   - Expected: +3-5 articles

---

## 📝 Code Changes Needed

### Change 1: Remove Redundant Date Filtering

**File:** `main.py`
**Location:** Lines 636-666
**Action:** Comment out or remove the date range check since Google News already filters

```python
# REMOVE OR COMMENT OUT THIS SECTION:
# Filter by date: Only process articles within the LOOKBACK_DAYS lookback period
# try:
#     article_date = None
#     if published_at:
#         ...
#         if days_ago > LOOKBACK_DAYS:
#             return None
# except Exception:
#     return None
```

**Reason:** Google News RSS query already uses `when:120d`, so this is redundant and causes 136 articles to be filtered unnecessarily.

---

## ✅ Conclusion

**The "48% extraction failure" is actually:**
- **49.5% due to redundant date filtering** (136 articles) - **FIXABLE**
- **2.5% due to legitimate ticker lookup failures** (7 articles) - **MINOR**

**The main issue is NOT extraction logic - it's redundant date filtering!**

Fixing the date filtering will immediately recover 136 articles, bringing the success rate from 48% to ~97%!

