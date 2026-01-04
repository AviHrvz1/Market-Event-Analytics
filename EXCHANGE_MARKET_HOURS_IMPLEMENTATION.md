# Exchange Detection and Market Hours Implementation Plan

## Problem
The system currently assumes all stocks trade during US market hours (9:30 AM - 4:00 PM ET). Foreign stocks like BYD (1211.HK) trade during different hours (Hong Kong: 9:30 AM - 4:00 PM HKT = 1:30 AM - 8:00 AM UTC), causing incorrect price extraction.

## Solution Overview
1. **Detect Exchange from Ticker**: Parse ticker suffix to identify the exchange (e.g., `.HK` = Hong Kong)
2. **Map Exchanges to Market Hours**: Create a configuration mapping exchanges to their trading hours and timezones
3. **Use Exchange-Specific Hours**: Modify market open/close checks and interval calculations to use the correct exchange

## Implementation Steps

### Step 1: Add Exchange Detection Functions to `main.py`

Add these functions to the `LayoffTracker` class:

```python
# Exchange to Market Hours Mapping
EXCHANGE_MARKET_HOURS = {
    'US': {
        'open': (9, 30),  # (hour, minute)
        'close': (16, 0),
        'timezone_offset': -5,  # EST (will adjust for DST)
        'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
    },
    'HK': {
        'open': (9, 30),
        'close': (16, 0),
        'timezone_offset': 8,  # HKT (UTC+8)
        'trading_days': [0, 1, 2, 3, 4],
    },
    # Add more exchanges as needed
}

TICKER_EXCHANGE_MAP = {
    '.HK': 'HK',
    '.L': 'L',
    '.T': 'T',
    '.PA': 'PA',
    # ... etc
}

def _detect_exchange_from_ticker(self, ticker: str) -> str:
    """Detect exchange from ticker suffix. Returns 'US' by default."""
    if not ticker:
        return 'US'
    
    ticker_upper = ticker.upper()
    for suffix, exchange in TICKER_EXCHANGE_MAP.items():
        if ticker_upper.endswith(suffix):
            return exchange
    return 'US'

def _get_market_hours(self, exchange: str) -> Dict:
    """Get market hours config for exchange. Returns US config as fallback."""
    return EXCHANGE_MARKET_HOURS.get(exchange, EXCHANGE_MARKET_HOURS['US'])
```

### Step 2: Modify `is_market_open()` to Accept Ticker

Change the function signature and logic:

```python
def is_market_open(self, dt: datetime, ticker: str = None) -> bool:
    """Check if market is open at given datetime for a specific ticker."""
    # Detect exchange if ticker provided
    if ticker:
        exchange = self._detect_exchange_from_ticker(ticker)
        market_config = self._get_market_hours(exchange)
    else:
        # Default to US for backward compatibility
        market_config = EXCHANGE_MARKET_HOURS['US']
    
    # Convert to exchange timezone
    # ... (use market_config['timezone_offset'] to calculate local time)
    # Check trading days and hours
```

### Step 3: Update `calculate_stock_changes()` to Use Exchange Hours

Modify the function to:
1. Detect exchange from ticker
2. Use exchange-specific market open/close times
3. Calculate intervals based on exchange hours

Key changes:
- Replace hardcoded `9:30 AM ET` with exchange-specific open time
- Replace hardcoded `4:00 PM ET` with exchange-specific close time
- Use exchange timezone for all time calculations

### Step 4: Update Interval Calculations

In `calculate_stock_changes()`, when calculating intervals:
- Use `get_market_open_time(ticker, date)` instead of hardcoded 9:30 AM ET
- Use `get_market_close_time(ticker, date)` instead of hardcoded 4:00 PM ET
- Convert all times to exchange timezone before calculations

## Alternative: Simpler Approach (Recommended for Quick Fix)

If full implementation is too complex, a simpler approach:

1. **Detect Exchange**: Keep the detection function
2. **Adjust Time Window**: When extracting intraday prices, check if the target time is within the actual data range
3. **Use Data-Driven Hours**: Instead of hardcoding hours, infer trading hours from the actual intraday data timestamps

This is what we already did with the 30-minute threshold fix, but we can make it smarter:

```python
def _get_trading_hours_from_data(self, intraday_data: Dict) -> Optional[Tuple[datetime, datetime]]:
    """Infer trading hours from actual intraday data timestamps."""
    if not intraday_data or 'data' not in intraday_data:
        return None
    
    timestamps = intraday_data['data'].get('timestamp', [])
    if not timestamps:
        return None
    
    # Find first and last timestamps (these represent trading hours)
    first_ts = min(timestamps)
    last_ts = max(timestamps)
    
    first_dt = datetime.fromtimestamp(first_ts, tz=timezone.utc)
    last_dt = datetime.fromtimestamp(last_ts, tz=timezone.utc)
    
    return (first_dt, last_dt)
```

Then use this in `_extract_intraday_price_from_batch()` to validate that target time is within actual trading hours.

## Recommended Implementation Order

1. **Phase 1 (Quick Win)**: Enhance the 30-minute threshold fix to use data-driven trading hours
2. **Phase 2 (Full Solution)**: Implement full exchange detection and market hours mapping

## Testing

Create unit tests for:
- Exchange detection from various ticker formats
- Market open/close time calculations for different exchanges
- Interval calculations for foreign stocks
- BYD (1211.HK) specific test case

## Notes

- **Timezone Handling**: Use `zoneinfo` (Python 3.9+) or `pytz` for proper timezone handling
- **DST**: Account for Daylight Saving Time changes
- **Holidays**: Consider adding exchange-specific holiday calendars (future enhancement)
- **Backward Compatibility**: Ensure existing US stock functionality continues to work

