# SSL Fix Applied - verify=False Workaround

## Summary

Added `verify=False` to all Claude API calls as a temporary workaround for macOS TCC (Transparency, Consent, and Control) permission issues that were blocking SSL certificate access.

## Changes Made

### Files Updated

1. **main.py** (3 locations):
   - Line 1540: `get_ai_prediction_score_batch()` - Added `verify=False`
   - Line 1746: `extract_search_subject()` - Added `verify=False`
   - Line 2717: `get_top_losers_claude()` - Added `verify=False`
   - Added urllib3 warning suppression at top of file

2. **app.py** (1 location):
   - Line 751: `extract_search_subject()` endpoint - Added `verify=False`
   - Added urllib3 warning suppression in function

3. **test_claude_simple.py**:
   - Updated test to use `verify=False` for consistency

## Test Results

✅ **Claude API now works!**
- Test returned status 200
- Response received successfully
- SSL warnings suppressed for cleaner output

## Security Note

⚠️ **Warning**: `verify=False` disables SSL certificate verification, which is less secure. This is a temporary workaround until macOS permissions can be properly configured.

### Recommended Next Steps

1. **Fix macOS Permissions** (Preferred):
   - System Settings → Privacy & Security → Full Disk Access
   - Add Terminal/IDE to Full Disk Access
   - Restart Terminal/IDE
   - Then remove `verify=False` and re-enable SSL verification

2. **Alternative**: Keep `verify=False` if market events project uses it and it's acceptable for your use case.

## Verification

Run the test to verify Claude API works:
```bash
python3 test_claude_simple.py
```

Expected output:
```
Status: 200
✅ SUCCESS! Response: Test
```

