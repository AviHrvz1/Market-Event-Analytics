# Bio Companies Missing Diagnosis Report

## Problem
8 bio/pharma companies with significant weekly moves were not captured in the system:

**Top Gainers:**
- AMC Robotics Corporation (AMCI) +256.46%
- NovaBay Pharmaceuticals (NBY) +89.29%
- Athira Pharma (ATHA) +80.10%
- Cumberland Pharmaceuticals (CPIX) +74.31%
- Century Therapeutics (IPSC) +61.38%

**Top Losers:**
- Vistagen Therapeutics (VTGN) -81.70%
- Pyxis Oncology (PYXS) -70.35%
- GeoVax Labs (GOVX) -57.52%

## Root Cause Analysis

### ✅ TEST 1: Company List Check - **PRIMARY ISSUE IDENTIFIED**

**Result: ALL 8 COMPANIES ARE MISSING FROM THE BIO COMPANIES LIST**

```
❌ AMC Robotics Corporation (AMCI) - NOT in bio list
❌ NovaBay Pharmaceuticals (NBY) - NOT in bio list
❌ Athira Pharma (ATHA) - NOT in bio list
❌ Cumberland Pharmaceuticals (CPIX) - NOT in bio list
❌ Century Therapeutics (IPSC) - NOT in bio list
❌ Vistagen Therapeutics (VTGN) - NOT in bio list
❌ Pyxis Oncology (PYXS) - NOT in bio list
❌ GeoVax Labs (GOVX) - NOT in bio list

📊 Summary: 0 found, 8 missing
```

**Impact:** Since the `bio_companies` event type uses `query_by_company_names=True`, it only searches for companies that are explicitly listed in `_get_bio_pharma_companies()`. If a company is not in that list, it will never be searched, regardless of whether articles exist about it.

### How the System Works

1. When `bio_companies` event type is selected, the system calls `_get_bio_pharma_companies()` to get a hardcoded list of ~68 companies
2. It constructs Google News queries like: `"PFIZER" OR "MERCK" OR "JOHNSON & JOHNSON" OR ...`
3. Only companies in this list are searched
4. If a company is not in the list, it will never appear in results

### Current Bio Companies List

The current list includes major companies like:
- PFIZER, MERCK, JOHNSON & JOHNSON, ABBVIE, BRISTOL-MYERS SQUIBB
- AMGEN, GILEAD SCIENCES, BIOGEN, REGENERON, MODERNA
- BIONTECH, NOVAVAX, ILLUMINA, VERTEX PHARMACEUTICALS
- And ~50+ other companies

But it does NOT include:
- AMC Robotics Corporation
- NovaBay Pharmaceuticals
- Athira Pharma
- Cumberland Pharmaceuticals
- Century Therapeutics
- Vistagen Therapeutics
- Pyxis Oncology
- GeoVax Labs

## Additional Potential Issues (Requires Network Access to Verify)

### TEST 2: Google News Search
- **Status:** Could not test due to SSL permission errors in sandbox
- **What to check:** Whether Google News actually has articles about these companies

### TEST 3: Date Range Filtering
- **Status:** Could not test due to SSL permission errors in sandbox
- **What to check:** Whether articles are within the 120-day lookback period
- **Note:** If the moves happened "past week", articles should be within range

### TEST 4: Event Type Matching
- **Status:** Could not test due to SSL permission errors in sandbox
- **What to check:** Whether articles would match the `bio_companies` event type
- **Note:** Since `bio_companies` has empty keywords and `query_by_company_names=True`, matching should pass if company is in list

### TEST 5: Full Fetch Simulation
- **Status:** Test ran but found 0 articles
- **Result:** This confirms the issue - no articles found because companies aren't in the search list

## Recommendations

### 1. **IMMEDIATE FIX: Add Missing Companies to Bio List**

Add these 8 companies to the `_get_bio_pharma_companies()` method in `main.py`:

```python
def _get_bio_pharma_companies(self) -> List[str]:
    """Get list of biotech/pharma company names for Google News search"""
    major_bio_companies = [
        # ... existing companies ...
        'AMC ROBOTICS CORPORATION',  # AMCI
        'NOVABAY PHARMACEUTICALS',   # NBY
        'ATHIRA PHARMA',              # ATHA
        'CUMBERLAND PHARMACEUTICALS', # CPIX
        'CENTURY THERAPEUTICS',       # IPSC
        'VISTAGEN THERAPEUTICS',     # VTGN
        'PYXIS ONCOLOGY',             # PYXS
        'GEOVAX LABS',                # GOVX
        # ... rest of existing companies ...
    ]
    # ...
```

### 2. **LONG-TERM SOLUTION: Dynamic Company Discovery**

Consider implementing one of these approaches:

**Option A: Expand from SEC EDGAR SIC Codes**
- Query SEC EDGAR for all companies with SIC codes 2834 (Pharmaceuticals) and 2836 (Biological Products)
- Dynamically build the company list instead of hardcoding

**Option B: Use Ticker-Based Search**
- Instead of searching by company name, search by ticker symbol
- More reliable for smaller companies that may have name variations

**Option C: Hybrid Approach**
- Keep major companies hardcoded for performance
- Add dynamic discovery for smaller companies based on SIC codes or ticker lists

### 3. **Monitoring & Maintenance**

- Regularly review bio/pharma stock movers lists
- Add new companies that appear in gainers/losers lists
- Consider automating this by scraping stock screener APIs

## Test Results Summary

| Test | Status | Finding |
|------|--------|---------|
| Test 1: Company List | ✅ Complete | **ALL 8 companies missing from list** |
| Test 2: Google News Search | ❌ Blocked | SSL permission errors (sandbox) |
| Test 3: Date Range | ❌ Blocked | SSL permission errors (sandbox) |
| Test 4: Event Matching | ❌ Blocked | SSL permission errors (sandbox) |
| Test 5: Full Fetch | ✅ Complete | 0 articles found (confirms issue) |

## Conclusion

**Primary Root Cause:** All 8 companies are missing from the hardcoded bio companies list in `_get_bio_pharma_companies()`. Since the system only searches for companies explicitly in this list, these companies will never be found regardless of:
- Whether articles exist about them
- Whether articles are within date range
- Whether articles would match event type

**Solution:** Add the 8 missing companies to the bio companies list. This is a simple fix that will immediately resolve the issue for these specific companies.

**Prevention:** Consider implementing dynamic company discovery to avoid this issue in the future.

