# UI Interval Shift Investigation

## Problem
User reports seeing:
- "Article time": $57.84 (+3.51%) - This is backend's 5min interval
- "5min": $57.86 (+3.54%) - This is backend's 10min interval  
- "10min": $58.00 (+3.79%) - This is backend's 30min interval

Intervals appear to be shifted by one position.

## Code Analysis

### Backend Data Structure ✅
- Correctly calculates intervals: 5min, 10min, 30min, etc.
- Data structure: `price_5min`, `price_10min`, `price_30min`, etc.

### Frontend Code Analysis
1. **Interval Array**: `selectedIntervals = ['5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr', '3hr']` ✅
2. **Table Headers**: Created in order from `selectedIntervals` ✅
3. **Table Cells**: Created in order from `selectedIntervals` ✅
4. **Data Mapping**: Uses `layoff[`price_${interval}`]` for each interval ✅

### Code Flow
```javascript
// Line 2734: Iterate through intervals in order
selectedIntervals.forEach(interval => {
    const price = articlePrices[`price_${interval}`];
    // ... other fields
    intervalCells += `<td data-interval="${interval}">${formatStockChange(...)}</td>`;
});
```

**The code looks correct!** There's no shifting or skipping happening.

## Possible Causes

1. **Browser Cache**: Old version of the page with buggy code
2. **Data Mismatch**: Backend returning data in wrong order (unlikely)
3. **Visual Bug**: CSS causing columns to appear misaligned
4. **Special Display**: User viewing data in tooltip/expanded view I haven't found
5. **Off-by-one in data structure**: Backend returning `price_10min` when asked for `price_5min`

## Recommended Fix

Since I can't find the bug in the code, I'll add:
1. Console logging to verify data mapping
2. Verification that interval names match
3. Ensure data is displayed in correct order

## Next Steps

1. Add console.log to verify what data is being received
2. Verify interval names match between backend and frontend
3. Check if there's any code that modifies `selectedIntervals` array
4. Test with actual browser to see the issue

