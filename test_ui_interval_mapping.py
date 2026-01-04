#!/usr/bin/env python3
"""Test to verify UI interval mapping matches backend data"""

# Simulate what the UI receives and how it should display it
selectedIntervals = ['5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr', '3hr']

# Backend data (what we calculated)
backend_data = {
    'price_5min': 57.84,
    'change_5min': 3.51,
    'volume_change_5min': 0.00,
    'datetime_5min': '2025-12-03T14:35:00+00:00',
    
    'price_10min': 57.86,
    'change_10min': 3.54,
    'volume_change_10min': 87.37,
    'datetime_10min': '2025-12-03T14:40:00+00:00',
    
    'price_30min': 58.00,
    'change_30min': 3.79,
    'volume_change_30min': -79.22,
    'datetime_30min': '2025-12-03T15:00:00+00:00',
}

print("=" * 80)
print("UI Interval Mapping Test")
print("=" * 80)

print(f"\nSelected Intervals (UI order): {selectedIntervals}")
print(f"\nBackend Data:")
for interval in selectedIntervals[:3]:  # Show first 3
    if f'price_{interval}' in backend_data:
        print(f"  {interval}: ${backend_data[f'price_{interval}']:.2f} ({backend_data[f'change_{interval}']:+.2f}%)")

print(f"\nHow UI should display:")
print("  Column headers: +5 Min, +10 Min, +30 Min, ...")
print("  Row data:")
for i, interval in enumerate(selectedIntervals[:3]):
    if f'price_{interval}' in backend_data:
        price = backend_data[f'price_{interval}']
        change = backend_data[f'change_{interval}']
        vol = backend_data.get(f'volume_change_{interval}', 0)
        dt = backend_data.get(f'datetime_{interval}', '')
        print(f"    Column {i+1} ({interval}): ${price:.2f} ({change:+.2f}%), Vol: {vol:+.2f}%")

print(f"\nWhat user sees:")
print("  'Article time': $57.84 (+3.51%)")
print("  '5min': $57.86 (+3.54%)")
print("  '10min': $58.00 (+3.79%)")

print(f"\nAnalysis:")
print("  User's 'Article time' = Backend's 5min ✅")
print("  User's '5min' = Backend's 10min ❌ (should be 5min)")
print("  User's '10min' = Backend's 30min ❌ (should be 10min)")

print(f"\nConclusion:")
print("  Intervals are shifted: UI is showing interval[i+1] in column[i]")
print("  This suggests the first interval (5min) is being displayed")
print("  as 'article time', then intervals are shifted by one position")

print("\n" + "=" * 80)

