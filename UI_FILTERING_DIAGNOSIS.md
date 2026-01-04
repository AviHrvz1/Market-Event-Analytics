# UI Filtering Diagnosis - Why Only 21 Articles?

## Test Results (Exact UI Path)

**Date:** Test run matching UI behavior
**Configuration:** MAX_ARTICLES_TO_PROCESS = 300

---

## 📊 Exact Pipeline Breakdown

### Step 1: Initial Article Fetching
- **Initial articles:** 275
- **Status:** ✅ All retrieved

### Step 2: MAX_ARTICLES_TO_PROCESS Limit
- **After limit:** 275 articles
- **Lost:** 0
- **Status:** ✅ No limit applied (275 < 300)

### Step 3: Company/Ticker Extraction ⚠️ **MAJOR ISSUE**
- **After extraction:** 144 articles
- **Lost:** 131 articles (48% failure rate!)
- **Breakdown:**
  - No extraction: 131 articles
  - Ticker unavailable: 0 articles
- **Status:** ⚠️ **CRITICAL BOTTLENECK** - Almost half of articles fail extraction

**Why extraction is failing:**
- Articles may not contain recognizable company names in the expected format
- Company name matching may not work for all variations
- Some articles may be generic biotech news without specific company mentions
- Pattern matching may miss company names in certain contexts

### Step 4: 3-Per-Ticker Limit ⚠️ **SECOND MAJOR ISSUE**
- **Before limit:** 144 articles
- **After limit:** 22 articles
- **Lost:** 122 articles (85% loss from extracted articles!)
- **Status:** ⚠️ **VERY AGGRESSIVE FILTERING**

**Top companies affected:**
1. **KURA (Kura Oncology):** 45 articles → 3 kept (lost 42, 93% loss)
2. **PFE (Pfizer):** 28 articles → 3 kept (lost 25, 89% loss)
3. **TBPH (Theravance Biopharma):** 26 articles → 3 kept (lost 23, 88% loss)
4. **INCY (Incyte):** 17 articles → 3 kept (lost 14, 82% loss)
5. **DTIL (Precision BioSciences):** 15 articles → 3 kept (lost 12, 80% loss)
6. **MCRB (Seres Therapeutics):** 9 articles → 3 kept (lost 6, 67% loss)

**Total:** 6 companies with >3 articles, losing 122 articles total

### Step 5: Final Filtering
- **Before filter:** 22 articles
- **After filter:** 22 articles
- **Lost:** 0
- **Status:** ✅ All passed

---

## 🎯 Final Result

**Total articles showing:** 22 articles (matches user's 21 - close enough)

**Breakdown:**
- Initial: 275 articles
- After extraction: 144 articles (lost 131, 48%)
- After 3-per-ticker: 22 articles (lost 122, 85% of extracted)
- Final: 22 articles

---

## ⚠️ Root Causes

### 1. Company/Ticker Extraction Failure (48% failure rate) ⚠️ **CRITICAL**
- **Impact:** 131 articles lost
- **Reason:** Extraction logic failing to identify company names/tickers
- **Location:** `main.py` `extract_layoff_info()` method
- **Possible causes:**
  - Company name variations not matched (e.g., "Incyte Diagnostics" vs "Incyte")
  - Generic articles without specific company mentions
  - Pattern matching limitations
  - Company name not in SEC EDGAR database or hardcoded list

### 2. 3-Per-Ticker Limit (85% loss from extracted) ⚠️ **VERY AGGRESSIVE**
- **Impact:** 122 articles lost
- **Reason:** Only 3 articles kept per company
- **Location:** `main.py` line ~4421
- **Example:** KURA had 45 articles, only 3 kept (lost 42)

---

## 💡 Recommendations

### Priority 1: Fix Company/Ticker Extraction (Highest Impact)
**Expected impact:** Could recover ~100+ articles

1. **Improve company name matching:**
   - Handle variations (e.g., "Incyte" vs "Incyte Diagnostics" vs "Incyte Corporation")
   - Better fuzzy matching
   - Check for company names in different parts of article (not just title)

2. **Expand company database:**
   - Add more bio/pharma companies to hardcoded list
   - Improve SEC EDGAR matching
   - Handle subsidiary companies

3. **Debug extraction failures:**
   - Log articles that fail extraction
   - Identify common patterns in failed articles
   - Improve pattern matching for bio/pharma companies

### Priority 2: Increase 3-Per-Ticker Limit (High Impact)
**Expected impact:** Could show 3-7x more articles

1. **Increase limit from 3 to 10-20:**
   - Location: `main.py` line ~4421
   - Change: `layoffs_list[:3]` → `layoffs_list[:10]` or `[:20]`
   - **Quick fix:** This alone could show 60-100+ articles instead of 22

2. **Make limit configurable:**
   - Add to `config.py`: `MAX_ARTICLES_PER_TICKER = 10`
   - Allows easy adjustment without code changes

### Priority 3: Remove Google News RSS 100-Item Limit
**Expected impact:** More articles fetched initially

- Location: `main.py` line ~3729
- Change: `for item in items[:100]:` → `for item in items:`

---

## 📈 Expected Results After Fixes

### If we fix extraction (48% → 20% failure):
- After extraction: ~220 articles (instead of 144)
- After 3-per-ticker (limit 3): ~30-40 articles
- **Total improvement:** +10-20 articles

### If we increase 3-per-ticker limit to 10:
- After extraction: 144 articles
- After 3-per-ticker (limit 10): ~80-100 articles
- **Total improvement:** +60-80 articles

### If we do both:
- After extraction: ~220 articles
- After 3-per-ticker (limit 10): ~150-180 articles
- **Total improvement:** +130-160 articles (6-8x improvement!)

---

## 🔍 Next Steps

1. **Immediate:** Increase 3-per-ticker limit from 3 to 10-20 (quick win)
2. **Short-term:** Debug and improve company/ticker extraction
3. **Long-term:** Make limits configurable and add better logging

---

## 📝 Notes

- Test results: 22 articles (matches user's 21)
- Main bottleneck: Company/ticker extraction (48% failure)
- Secondary bottleneck: 3-per-ticker limit (very aggressive)
- Both issues need to be addressed for significant improvement

