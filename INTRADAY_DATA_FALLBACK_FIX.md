# Intraday Data Fallback Fix

## Problem
When articles were published on dates older than 60 days (Prixe.io intraday data limit), all intraday intervals (1min, 2min, 3min, 4min, 5min, 10min, 30min) showed "N/A" even though daily close data was available.

**Example from user:**
- VRTX (Nov 10, 2025) - All intervals showed N/A except 1hr (12:30) and daily close (16:00)
- BLTE (Oct 15, 2025) - All intervals showed N/A except 1hr and daily close
- PTGX (Aug 25, 2025) - All intervals showed N/A except 1hr and daily close

## Root Cause
The code only used daily close as a fallback when:
1. Intraday data existed but was sparse (< 5 data points)

But when `intraday_data` was `None` (because date was >60 days old), it didn't use the fallback, so all intervals showed N/A.

## Solution
Updated the fallback logic to use daily close price when:
1. Intraday data is not available (date >60 days old, Prixe.io limit)
2. Intraday data is sparse (< 5 data points)
3. Intraday data fetch failed

## Changes Made

### 1. Market Open Path (lines 3400-3430)
- Changed logic to use daily close fallback when `intraday_data` is `None`
- Previously only used fallback if intraday_data existed but was sparse

### 2. Market Closed Path (lines 3723-3731)
- Added daily close fallback when intraday data is not available
- Previously showed N/A when no intraday data

### 3. Edge Case Path (lines 3475-3483)
- Added daily close fallback for edge cases where target time is within market hours but no intraday data

## Result
✅ **All intervals now show data using daily close as fallback when intraday data is unavailable**

**Before:**
- 1min: N/A
- 2min: N/A
- 3min: N/A
- 4min: N/A
- 5min: N/A
- 10min: N/A
- 30min: N/A
- 1hr: $56.99 (+0.19%)
- Daily close: $56.99 (+0.19%)

**After:**
- 1min: $56.99 (+0.19%) [daily close fallback]
- 2min: $56.99 (+0.19%) [daily close fallback]
- 3min: $56.99 (+0.19%) [daily close fallback]
- 4min: $56.99 (+0.19%) [daily close fallback]
- 5min: $56.99 (+0.19%) [daily close fallback]
- 10min: $56.99 (+0.19%) [daily close fallback]
- 30min: $56.99 (+0.19%) [daily close fallback]
- 1hr: $56.99 (+0.19%) [daily close fallback]
- Daily close: $56.99 (+0.19%)

## Note
When daily close is used as fallback:
- `is_daily_close_{interval}` is set to `True`
- `is_intraday_{interval}` is set to `False`
- `is_approximate_{interval}` is set to `True`

This allows the UI to display these as approximate values (using daily close instead of actual intraday prices).

## Status
✅ **FIXED** - All intervals now show data when daily close is available, even if intraday data is not available due to date limits.

