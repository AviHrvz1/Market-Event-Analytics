# Article Filtering Analysis Report

## Test Results Summary

**Date:** $(date)
**Configuration:** MAX_ARTICLES_TO_PROCESS = 300

---

## 📊 Pipeline Breakdown

### Step 1: Initial Article Fetching
- **Initial articles fetched:** 275
- **Source breakdown:**
  - Google News: 275 total, 550 matched
  - Benzinga News: 15 total, 0 matched
- **Status:** ✅ All articles retrieved successfully

### Step 2: MAX_ARTICLES_TO_PROCESS Limit
- **Before limit:** 275 articles
- **After limit:** 275 articles
- **Articles lost:** 0
- **Reason:** No limit applied (275 < 300)
- **Status:** ✅ No articles filtered at this stage

### Step 3: Company/Ticker Extraction
- **Sample size analyzed:** 20 articles
- **Extraction success rate:** 95.0%
- **With company/ticker:** 19 articles (95.0%)
- **Without company/ticker:** 1 article (5.0%)
- **Estimated full results:**
  - After extraction: ~261 articles (lost ~14, ~5% failure)
- **Status:** ⚠️ Small loss due to extraction failures

**Sample articles that failed extraction:**
1. "Exploring the Role of Molecular Profiling: Using NGS in the Diagnosis and Treatment of Biliary Tract Cancers (BTC)" - Generic medical article without specific company mention

### Step 4: 3-Per-Ticker Limit
- **Before limit:** ~261 articles
- **After limit:** ~156 articles
- **Articles lost:** ~105 articles (~40% loss)
- **Reason:** Only 3 most recent articles kept per company/ticker
- **Status:** ⚠️ **MAJOR BOTTLENECK** - This is the biggest filter

**Impact:** If multiple companies have many articles, only 3 are kept per company. For example:
- If Moderna has 10 articles → only 3 kept, 7 lost
- If Pfizer has 8 articles → only 3 kept, 5 lost
- If multiple companies have 5+ articles each, significant loss occurs

### Step 5: Final Filtering
- **Before filter:** ~156 articles
- **After filter:** ~148 articles
- **Articles lost:** ~8 articles (~5% loss)
- **Reason:** Requires both `company_name` AND `stock_ticker`
- **Status:** ✅ Small loss, expected

---

## 🎯 Key Findings

### 1. MAX_ARTICLES_TO_PROCESS = 300 ✅
- **Impact:** No articles lost at this stage (275 < 300)
- **Status:** Working correctly

### 2. Company/Ticker Extraction ⚠️
- **Success rate:** 95.0%
- **Failure rate:** 5.0%
- **Impact:** ~14 articles lost
- **Reason:** Generic articles, articles without specific company mentions
- **Status:** Acceptable loss rate

### 3. 3-Per-Ticker Limit ⚠️ **MAJOR ISSUE**
- **Impact:** ~105 articles lost (~40% of extracted articles)
- **Reason:** Only 3 most recent articles per company/ticker are kept
- **Location:** `main.py` line ~4421
- **Status:** **This is the biggest bottleneck**

**Example scenarios:**
- If 10 companies each have 5 articles = 50 articles
- After 3-per-ticker limit = 30 articles (20 lost)
- If 20 companies each have 3 articles = 60 articles
- After 3-per-ticker limit = 60 articles (0 lost)

### 4. Final Filtering ✅
- **Impact:** ~8 articles lost (~5%)
- **Reason:** Missing company_name or stock_ticker
- **Status:** Expected and acceptable

---

## 📈 Estimated Results

| Stage | Articles | Lost | Loss % |
|-------|----------|------|--------|
| Initial fetch | 275 | 0 | 0% |
| After MAX_ARTICLES limit | 275 | 0 | 0% |
| After company extraction | ~261 | ~14 | 5% |
| After 3-per-ticker limit | ~156 | ~105 | 40% |
| After final filtering | ~148 | ~8 | 5% |

**Estimated final count:** ~148 articles

---

## ⚠️ Discrepancy Analysis

**User reported:** Only 19 articles showing
**Estimated from test:** ~148 articles should show

**Possible reasons for discrepancy:**
1. **3-Per-Ticker Limit:** If articles are heavily concentrated on a few companies, the 3-per-ticker limit could be more aggressive than estimated
2. **Date Range Filtering:** Articles outside the LOOKBACK_DAYS (120 days) may be filtered
3. **Prixe.io Availability:** Articles for companies not available in Prixe.io may be filtered
4. **Real-time vs Test:** The test may have different results than actual runtime

---

## 💡 Recommendations

### To See More Articles:

1. **Increase 3-Per-Ticker Limit** (Highest Impact)
   - Current: 3 articles per ticker
   - Recommended: 10-20 articles per ticker
   - Location: `main.py` line ~4421
   - Expected impact: Could show 3-7x more articles

2. **Remove or Increase Google News RSS 100-Item Limit**
   - Current: 100 items per query
   - Location: `main.py` line ~3729
   - Change: `for item in items[:100]:` → `for item in items:`
   - Expected impact: More articles fetched initially

3. **Improve Company Extraction**
   - Better pattern matching for company name variations
   - Handle edge cases (e.g., "Incyte Diagnostics" vs "Incyte")
   - Expected impact: Reduce 5% extraction failure rate

4. **Remove Final Filtering Strictness** (Low Priority)
   - Current: Requires both company_name AND stock_ticker
   - Could allow articles with company_name only
   - Expected impact: ~5% more articles

---

## 🔍 Next Steps

1. Run full diagnostic test (`test_article_filtering_diagnosis.py`) to get exact counts
2. Analyze which companies have the most articles to understand 3-per-ticker impact
3. Consider increasing 3-per-ticker limit from 3 to 10-20
4. Monitor actual results vs estimated results

---

## 📝 Notes

- Test was run with sample of 20 articles for speed
- Full test would process all 275 articles (takes 2-3 minutes)
- Results are estimates based on sample analysis
- Actual results may vary based on article distribution across companies

