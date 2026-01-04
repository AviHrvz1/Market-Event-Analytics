# FDA Approval Ticker N/A Issue - Exact Diagnosis

## Test Results Summary

### ✅ API Endpoint Status
- **Endpoint `/api/price` is WORKING** (returns 200 for valid tickers)
- **NOT an endpoint issue** - the endpoint exists and functions correctly

### ❌ Ticker-Specific Issues

| Ticker | Company | API Response | Root Cause |
|--------|---------|--------------|------------|
| **AAPL** | Apple (test) | ✅ 200 OK | Valid ticker - works |
| **BAYRY** | Bayer AG | ✅ 200 OK | Valid ticker - has data |
| **NOVN** | Novan | ❌ 404 | Ticker not in Prixe.io |
| **AVZO** | Avertex Biotherapeutics | ❌ 404 | Ticker not in Prixe.io |
| **MRTX** | Mirati Therapeutics | ❌ 404 | Ticker not in Prixe.io |
| **HGEN** | Humanigen | ❌ 404 | Ticker not in Prixe.io |

### Exact API Response for Failed Tickers
```json
{
  "error": "No data available for the specified parameters"
}
```

## Root Cause Analysis

### 1. **PRIMARY ISSUE: Tickers Not in Prixe.io Database**

The 404 errors are **NOT endpoint errors** - they are **ticker-not-found errors**.

- Prixe.io returns 404 with message: `"No data available for the specified parameters"`
- This means the ticker doesn't exist in Prixe.io's database
- **NOT a code bug** - the API is working correctly

### 2. **SECONDARY ISSUE: Error Message Misinterpretation**

**Location:** `main.py` lines 1757-1766

The error handling code tries to distinguish between:
- Endpoint not found (404 on endpoint)
- Ticker not found (404 on ticker)

**Problem:** The error message `"No data available for the specified parameters"` doesn't contain the word "ticker", so the code incorrectly reports it as an endpoint issue.

**Current behavior:**
```python
# Line 1761: Checks if 'ticker' is in error text
if 'ticker' in error_text or ticker_upper in error_text:
    error_msg = f"Ticker '{ticker}' not found..."
else:
    error_msg = f"Prixe.io API endpoint not found..."  # ❌ WRONG - this is selected
```

**Actual error text:** `"No data available for the specified parameters"` (no "ticker" word)

### 3. **Ticker Validation Issues**

All failed tickers are **NOT in SEC EDGAR**:
- NOVN: Not in SEC EDGAR (likely OTC or delisted)
- AVZO: Not in SEC EDGAR (likely OTC or invalid)
- MRTX: Not in SEC EDGAR (acquired/delisted)
- HGEN: Not in SEC EDGAR (likely OTC or delisted)

**BAYRY** (Bayer AG):
- Not in SEC EDGAR (foreign ticker - German exchange)
- BUT Prixe.io has data for it
- Shows partial data (next_close works, intraday fails)

## Exact Failure Points in Code

### Failure Point 1: API Returns 404
**Location:** `main.py` line 1749
```python
if response.status_code == 404:
    # Returns None
    return None
```

### Failure Point 2: Batch Data is None
**Location:** `main.py` line 2752-2754
```python
if not daily_price_data:
    # PERFORMANCE: Removed verbose debug logging (only log errors, not every missing data case)
    return empty_results  # ← ALL N/A VALUES RETURNED HERE
```

### Failure Point 3: Base Price is None
**Location:** `main.py` line 2774-2775
```python
if not base_price:
    return empty_results  # ← FALLBACK IF BASE PRICE NOT FOUND
```

## Why BAYRY Shows Partial Data

BAYRY (Bayer AG) shows `next_close` price but all intraday intervals are N/A:

1. **Daily data works:** Prixe.io has daily (1d interval) data for BAYRY
2. **Intraday data fails:** When trying to fetch intraday data (1m interval), it returns 404
3. **Result:** Base price and next_close work (use daily data), but intraday intervals fail

## Diagnosis Summary

### ✅ What's Working
- API endpoint `/api/price` is valid and functional
- Error handling code structure is correct
- Code flow is working as designed

### ❌ What's Not Working
- **Tickers don't exist in Prixe.io:** NOVN, AVZO, MRTX, HGEN
- **Error message is misleading:** Reports "endpoint not found" when it's "ticker not found"
- **Tickers not in SEC EDGAR:** All failed tickers are invalid/OTC/delisted

### 🔍 Exact Issue Location

**File:** `main.py`  
**Function:** `_prixe_api_request()`  
**Lines:** 1757-1766  
**Issue:** Error message parsing incorrectly identifies ticker-not-found as endpoint-not-found

**File:** `main.py`  
**Function:** `calculate_stock_changes()`  
**Lines:** 2752-2754  
**Issue:** Returns empty_results when API returns None (correct behavior, but triggered by ticker-not-found)

## Conclusion

**NOT a code bug** - the code is working correctly.

**IS a data availability issue:**
- Tickers NOVN, AVZO, MRTX, HGEN don't exist in Prixe.io database
- These are likely OTC stocks, delisted companies, or not supported by Prixe.io
- The error message is misleading but doesn't affect functionality

**Recommendation:**
1. Update error message parsing to correctly identify ticker-not-found (line 1761)
2. For unsupported tickers, show "Ticker not available" instead of "API endpoint not found"
3. Consider alternative data sources for OTC/delisted tickers

