# Recommendation: Addressing Root Cause of Foreign Stock Trading Hours

## Current Situation
- System assumes all stocks trade 9:30 AM - 4:00 PM ET (US market hours)
- Foreign stocks like BYD (1211.HK) trade during different hours
- Current fix: Returns `None` if target time is >30 minutes from data (prevents wrong prices)
- **Problem**: Intervals show `N/A` instead of actual prices

## Recommended Solution: Two-Phase Approach

### Phase 1: Data-Driven Trading Hours (Quick Win) ⭐ **RECOMMENDED**

**Idea**: Instead of assuming market hours, infer them from the actual intraday data.

**Benefits**:
- Works for any exchange automatically
- No need to maintain exchange mappings
- Minimal code changes
- Handles edge cases (half-days, special sessions)

**Implementation**:
1. Add function to extract trading hours from intraday data
2. Use these hours to validate target times
3. Calculate intervals based on actual trading window

**Code Changes**:
```python
def _get_trading_window_from_data(self, intraday_data: Dict) -> Optional[Tuple[datetime, datetime]]:
    """Extract actual trading hours from intraday data timestamps."""
    if not intraday_data or 'data' not in intraday_data:
        return None
    
    timestamps = intraday_data['data'].get('timestamp', [])
    if not timestamps or len(timestamps) < 2:
        return None
    
    # First and last timestamps represent trading window
    first_ts = min(timestamps)
    last_ts = max(timestamps)
    
    first_dt = datetime.fromtimestamp(first_ts, tz=timezone.utc)
    last_dt = datetime.fromtimestamp(last_ts, tz=timezone.utc)
    
    return (first_dt, last_dt)

def _extract_intraday_price_from_batch(self, intraday_data: Dict, target_datetime: datetime) -> Optional[float]:
    """Extract price - now validates against actual trading hours."""
    # ... existing code ...
    
    # Get actual trading window from data
    trading_window = self._get_trading_window_from_data(intraday_data)
    if trading_window:
        window_start, window_end = trading_window
        target_utc = target_datetime.astimezone(timezone.utc) if target_datetime.tzinfo else target_datetime.replace(tzinfo=timezone.utc)
        
        # Only extract if within actual trading hours (with 5-minute buffer)
        if target_utc < window_start - timedelta(minutes=5) or target_utc > window_end + timedelta(minutes=5):
            return None
    
    # ... rest of extraction logic ...
```

**In `calculate_stock_changes()`**:
- When article published on market-closed day, calculate intervals from actual market open (first timestamp) instead of hardcoded 9:30 AM ET
- Use actual trading window to determine valid intervals

### Phase 2: Full Exchange Detection (Future Enhancement)

**Idea**: Explicitly detect exchange and use known market hours.

**Benefits**:
- More accurate (handles pre-market, after-hours)
- Can validate data quality
- Better error messages

**When to implement**:
- If Phase 1 doesn't work well enough
- If you need to handle pre-market/after-hours
- If you want to support more exchanges with special rules

## My Recommendation

**Start with Phase 1** because:
1. ✅ Works immediately for all exchanges
2. ✅ Minimal code changes
3. ✅ No maintenance burden (no exchange mappings to update)
4. ✅ Handles edge cases automatically
5. ✅ Can be implemented in ~1-2 hours

**Then consider Phase 2** if:
- You need pre-market/after-hours data
- You want to validate data quality
- You need exchange-specific features

## Implementation Priority

1. **Now**: Enhance `_extract_intraday_price_from_batch()` to use data-driven trading window
2. **Now**: Update `calculate_stock_changes()` to calculate intervals from actual market open
3. **Later**: Add exchange detection if needed

## Example: How It Would Work for BYD

**Current (Broken)**:
- Article: Sun Nov 30, 4:48 AM UTC
- System calculates: Mon Dec 1, 9:35 AM ET (14:35 UTC) for +5min interval
- Prixe.io data: 01:15 - 08:05 UTC (Hong Kong hours)
- Result: No match → Returns `None` ✅ (but shows N/A in UI)

**With Phase 1 (Fixed)**:
- Article: Sun Nov 30, 4:48 AM UTC
- System detects: Actual trading window is 01:15 - 08:05 UTC
- System calculates: Mon Dec 1, 01:20 UTC (01:15 + 5min) for +5min interval
- Prixe.io data: Has price at 01:20 UTC
- Result: Returns actual price ✅

This would make BYD intervals show real prices instead of N/A!

