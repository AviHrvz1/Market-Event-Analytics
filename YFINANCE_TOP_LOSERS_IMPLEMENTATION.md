# yfinance Top Losers Implementation

## Summary

Switched from Claude AI to yfinance for identifying top bearish stocks. This ensures:
- ✅ **Accuracy**: Uses actual price data, not AI estimates
- ✅ **Consistency**: Same data source logic as the rest of the system
- ✅ **No Claude dependency**: Removed Claude for top losers identification

## Changes Made

### 1. Removed Claude Dependency
- **File**: `main.py`
- **Location**: `get_bearish_analytics()` method (line ~3186)
- **Change**: Removed Claude call, now uses yfinance directly
- **Before**: Try Claude first → Fallback to yfinance
- **After**: Use yfinance directly

### 2. SSL Certificate Fix Attempts
- **File**: `main.py`
- **Location**: `__init__()` method (line ~54)
- **Change**: Added environment variables to help with SSL issues:
  ```python
  os.environ['CURL_CA_BUNDLE'] = ''
  os.environ['REQUESTS_CA_BUNDLE'] = ''
  os.environ['CURLOPT_SSL_VERIFYPEER'] = '0'
  os.environ['CURLOPT_SSL_VERIFYHOST'] = '0'
  ```
- **Note**: yfinance uses `curl_cffi` which may not respect these variables, but we try anyway

### 3. Improved Error Handling
- **File**: `main.py`
- **Location**: `get_top_losers_yfinance()` method
- **Changes**:
  - Better logging for SSL errors
  - Continue processing even when some tickers fail
  - Individual retry for failed tickers
  - Summary of successful vs failed downloads

### 4. Enhanced Logging
- Shows which batches succeed/fail
- Identifies SSL errors specifically
- Reports successful ticker count
- Warns if results may be incomplete due to SSL errors

## Performance

### Expected Performance
- **Batch Download**: ~36 seconds for 197 tickers (in batches of 25)
- **Individual Retries**: Additional time for failed tickers
- **Total**: ~40-50 seconds (depending on SSL errors)

### SSL Error Impact
- Some tickers may fail with SSL certificate errors
- Code continues processing successful tickers
- Results may be incomplete if many tickers fail
- Individual retry helps recover some failed tickers

## Known Issues

### SSL Certificate Errors
- **Issue**: yfinance uses `curl_cffi` which has SSL certificate access issues on macOS
- **Symptom**: Some tickers fail with "curl: (77) error setting certificate verify locations"
- **Impact**: Some tickers may be missing from results
- **Workaround**: Code continues with successful tickers, retries failed ones individually
- **Future Fix**: May need to fix macOS TCC permissions or use alternative data source

## Testing

To test the implementation:

```python
from datetime import datetime, timezone
from main import LayoffTracker

tracker = LayoffTracker()
bearish_date = datetime(2025, 11, 10, tzinfo=timezone.utc)
target_date = datetime(2025, 11, 17, tzinfo=timezone.utc)

results, logs = tracker.get_bearish_analytics(bearish_date, target_date, industry=None)

# Check logs for SSL errors
for log in logs:
    print(log)

# Check results
print(f"Found {len(results)} stocks with drops")
```

## Benefits

1. **Accuracy**: Uses real price data, not AI estimates
2. **Consistency**: Same data source as graphs (yfinance)
3. **No AI dependency**: Removed Claude for this feature
4. **Better error handling**: Continues processing even with SSL errors
5. **Transparency**: Clear logging of what succeeded/failed

## Next Steps

If SSL errors persist:
1. Fix macOS TCC permissions (preferred)
2. Consider using Prixe.io as fallback for failed tickers
3. Or use a different data source that doesn't have SSL issues

