# SEC Bio/Pharma Companies Test Results

## Test Status

**Test File Created:** `test_sec_bio_companies.py`

**Current Status:** Test structure is complete, but cannot run fully in sandbox due to SSL permission restrictions.

**Current Hardcoded List:** 76 companies

## How the Test Works

The test implements dynamic loading of bio/pharma companies from SEC EDGAR:

1. **Loads SEC Company Tickers**
   - Fetches: `https://www.sec.gov/files/company_tickers.json`
   - Contains all SEC-registered companies with CIK, ticker, and name

2. **Filters by SIC Codes**
   - Checks each company's SIC code via: `https://data.sec.gov/submissions/CIK{10-digit}.json`
   - Filters for:
     - **2834**: Pharmaceutical Preparations
     - **2836**: Biological Products

3. **Compares with Current List**
   - Shows how many companies would be added
   - Shows which companies are in current list but not in SEC (foreign companies, etc.)

## Expected Results

Based on SEC data, we expect to find:

- **~400-600 bio/pharma companies** registered with SEC
- This would be a **5-8x increase** from the current 76 companies
- Many small/mid-cap biotech companies that aren't in the current hardcoded list

## Why This Approach is Better

### Current Approach (Hardcoded List)
- ✅ Fast (no API calls)
- ❌ Limited to ~76 companies
- ❌ Missing many small/mid-cap companies
- ❌ Requires manual updates when new companies emerge

### Dynamic SEC Approach
- ✅ Comprehensive (all SEC-registered bio/pharma)
- ✅ Automatically includes new companies
- ✅ No manual maintenance needed
- ⚠️ Slower (requires API calls, but can be cached)
- ⚠️ Rate limiting (SEC allows 10 requests/second)

## Implementation Options

### Option 1: Full Dynamic (Recommended)
Load from SEC every time (with caching):
```python
def _get_bio_pharma_companies(self) -> List[str]:
    # Load from SEC, cache for 24 hours
    # Filter by SIC codes 2834, 2836
    # Return all company names
```

### Option 2: Hybrid Approach
Keep major companies hardcoded, add SEC companies:
```python
def _get_bio_pharma_companies(self) -> List[str]:
    major_companies = [hardcoded list]  # Fast lookup
    sec_companies = load_from_sec()     # Comprehensive
    return major_companies + sec_companies
```

### Option 3: Cached Dynamic
Load from SEC once per day, cache results:
```python
def _get_bio_pharma_companies(self) -> List[str]:
    cache_file = 'bio_companies_cache.json'
    if cache_expired(cache_file):
        companies = load_from_sec()
        save_cache(cache_file, companies)
    return load_cache(cache_file)
```

## Running the Test

To run the test and see actual results, execute outside the sandbox:

```bash
cd "/Users/avi.horowitz/Documents/LayoffTracker -10"
python3 test_sec_bio_companies.py
```

**Note:** The test will take 5-10 minutes to complete due to:
- ~10,000+ companies to check
- SEC rate limiting (10 requests/second)
- Need to check each company's SIC code individually

## Test Output Format

The test will show:
1. Current hardcoded list count (76 companies)
2. SEC bio/pharma companies found (expected: ~400-600)
3. New companies that would be added
4. Companies in current list but not in SEC (foreign companies, etc.)
5. Summary with recommendations

## Next Steps

1. **Run the test locally** (outside sandbox) to get actual numbers
2. **Review the results** to see how many companies would be added
3. **Decide on implementation approach** (full dynamic, hybrid, or cached)
4. **Implement the chosen approach** if results are favorable

## Estimated Impact

If we add ~400-500 more companies:
- **5-8x more coverage** of bio/pharma news
- Better chance of catching small/mid-cap movers
- More comprehensive market coverage
- Slightly slower initial load (but can be cached)

