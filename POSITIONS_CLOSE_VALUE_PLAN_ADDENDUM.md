# Positions Close Value – Plan Addendum: Refresh Button

## Requirement

Add a **Refresh** button on each ticker’s expanded details panel (Positions Analytics tab). When the user clicks it:

1. Re-fetch the latest option prices from Think or Swim (Schwab API).
2. Recompute and update in the UI:
   - **Close (Credit/Debit)** for each position line
   - **P/L if close** for each position line
   - **By strategy** block (each VERTICAL/BUTTERFLY P/L if close)
   - **Total P/L if close all**

## UI placement

- Show the Refresh button **inside the expanded details row**, only when:
  - The position **status is Open**, and
  - Close-value data is already loaded (so the Close / P/L if close section is visible).
- Place it near the top of the details panel (e.g. next to the “Details” heading or in a small toolbar row above the details table).
- Label: e.g. “Refresh prices” or “Refresh” with an icon if desired.

## Behavior

- **On click**: Call the same backend used for initial load: `GET /api/positions-analytics/close-value?ticker=<ticker>` (no change to API; reuse existing endpoint).
- **While refreshing**: Disable the button and show loading state (e.g. “Updating…” or spinner).
- **On success**: Replace the existing Close (Credit/Debit), P/L if close, By strategy, and Total P/L if close all with the new values from the response.
- **On error**: Show a short message in the panel (e.g. “Could not refresh. Try again.”); leave existing numbers as-is.

## Implementation note

- Reuse the same logic that populates the panel on first expand: after the refresh API returns, re-render the Close columns, By strategy block, and Total P/L if close all using the new payload (same structure as initial load).
