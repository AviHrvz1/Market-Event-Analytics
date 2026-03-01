#!/usr/bin/env python3
"""
Unit test: Verify Recovery History 180-day lookback for WDAY (Workday).
User reported possible bug: during 180 days before bearish date Nov 26, 2025,
there should be no other -5% drops (or we verify the count matches recovery_history items).

Run: python test_wday_recovery_history_180_days.py
      python -m unittest test_wday_recovery_history_180_days
Requires network (fetches WDAY price history).
"""
import unittest
from datetime import datetime, timedelta, timezone
from main import LayoffTracker


def find_drops_in_window(price_history, pct_threshold, before_date_str):
    """
    Manually find all day-over-day drops <= pct_threshold where drop date < before_date_str.
    Mirrors analyze_recovery_history logic (drops only, no recovery).
    Returns list of (date, drop_pct).
    """
    if not price_history or len(price_history) < 2:
        return []
    sorted_history = sorted(price_history, key=lambda x: x.get('date', ''))
    drops = []
    for i in range(1, len(sorted_history)):
        current = sorted_history[i]
        prev = sorted_history[i - 1]
        current_date = current.get('date', '')
        current_price = current.get('price')
        prev_price = prev.get('price')
        if not current_date or current_date >= before_date_str or not current_price or not prev_price:
            continue
        drop_pct = ((current_price - prev_price) / prev_price) * 100
        if drop_pct <= pct_threshold:
            drops.append((current_date, round(drop_pct, 2)))
    return drops


class TestWDAYRecoveryHistory180Days(unittest.TestCase):
    """Verify 180-day recovery history: manual drop count matches analyze_recovery_history items."""

    def test_wday_180_days_no_other_minus_5_drops(self):
        ticker = "WDAY"
        bearish_date = datetime(2025, 11, 26, tzinfo=timezone.utc)
        target_date = datetime(2026, 1, 6, tzinfo=timezone.utc)
        bearish_date_str = bearish_date.strftime('%Y-%m-%d')
        pct_threshold = -5.0  # -5% drop
        recovery_threshold = 3.0  # 3% recovery (from UI default)

        tracker = LayoffTracker()
        graph_start_date = bearish_date - timedelta(days=180)
        price_history_end_date = target_date + timedelta(days=1)
        price_history = tracker.get_stock_price_history(ticker, graph_start_date, price_history_end_date)

        self.assertIsNotNone(price_history, "Price history should not be None")
        self.assertGreater(len(price_history), 0, "Price history should not be empty (check network/API)")

        # Manual count: all -5% drops before bearish date (within 180-day window)
        drops_before_bearish = find_drops_in_window(price_history, pct_threshold, bearish_date_str)

        # What analyze_recovery_history returns (same window; only dates before bearish_date)
        rh_result = tracker.analyze_recovery_history(
            price_history, pct_threshold, bearish_date_str, None, recovery_threshold=recovery_threshold
        )
        items = rh_result.get('items', []) if isinstance(rh_result, dict) else rh_result

        # Assert: manual drop count must equal recovery history item count
        self.assertEqual(
            len(drops_before_bearish),
            len(items),
            f"Count mismatch: manual drops (date < bearish) = {len(drops_before_bearish)}, "
            f"recovery_history items = {len(items)}",
        )

        # For WDAY with bearish 2025-11-26: expect no -5% drops in 180 days before
        self.assertEqual(
            len(drops_before_bearish),
            0,
            f"WDAY: expected 0 -5% drops in 180 days before {bearish_date_str}; found {len(drops_before_bearish)}: {drops_before_bearish}",
        )


class TestAPHRecoveryHistory180Days(unittest.TestCase):
    """Verify 180-day recovery history for APH (Amphenol): manual drop count matches analyze_recovery_history."""

    def test_aph_180_days_minus_5_drops_count(self):
        ticker = "APH"
        bearish_date = datetime(2025, 12, 12, tzinfo=timezone.utc)
        target_date = datetime(2026, 1, 6, tzinfo=timezone.utc)
        bearish_date_str = bearish_date.strftime('%Y-%m-%d')
        pct_threshold = -5.0  # -5% drop
        recovery_threshold = 3.0  # 3% recovery (from UI default)

        tracker = LayoffTracker()
        graph_start_date = bearish_date - timedelta(days=180)
        price_history_end_date = target_date + timedelta(days=1)
        price_history = tracker.get_stock_price_history(ticker, graph_start_date, price_history_end_date)

        self.assertIsNotNone(price_history, "Price history should not be None")
        self.assertGreater(len(price_history), 0, "Price history should not be empty (check network/API)")

        # Manual count: all -5% drops before bearish date (within 180-day window)
        drops_before_bearish = find_drops_in_window(price_history, pct_threshold, bearish_date_str)

        # What analyze_recovery_history returns (same window; only dates before bearish_date)
        rh_result = tracker.analyze_recovery_history(
            price_history, pct_threshold, bearish_date_str, None, recovery_threshold=recovery_threshold
        )
        items = rh_result.get('items', []) if isinstance(rh_result, dict) else rh_result

        # Assert: manual drop count must equal recovery history item count
        self.assertEqual(
            len(drops_before_bearish),
            len(items),
            f"Count mismatch: manual drops (date < bearish) = {len(drops_before_bearish)}, "
            f"recovery_history items = {len(items)}",
        )

        # Log how many -5% drops were found (for user visibility when run with -v)
        print(f"  APH: {len(drops_before_bearish)} -5% drops in 180 days before {bearish_date_str}")
        for d, pct in drops_before_bearish:
            print(f"    - {d}: {pct}%")
            self.assertLessEqual(pct, pct_threshold, f"Drop on {d}: {pct}%")


if __name__ == "__main__":
    unittest.main(verbosity=2)
