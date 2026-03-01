#!/usr/bin/env python3
"""
Unit test: Verify 5% drop recovery history (180-day lookback) for IBM.
User reported: bearish date Feb 23, 2026, "show history" shows only 2 occurrences;
they expect more than 2 in 180 days. This test checks that the recovery history
item count matches the actual number of day-over-day -5% drops in the same window
(no drops are missed by the backend).
Requires network (fetches IBM price history).
Run: python test_ibm_recovery_history_180_days.py
     python -m unittest test_ibm_recovery_history_180_days -v
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


class TestIBMRecoveryHistory180Days(unittest.TestCase):
    """
    Verify IBM 5% drop recovery history: count of items matches actual -5% drops
    in 180 days before bearish date (Feb 23, 2026). If only 2 occurrences show
    in the UI, this test confirms whether that is the true number of -5% drops
    in the data or if the backend is undercounting.
    """

    def test_ibm_180_days_minus_5_drops_count_matches_recovery_history(self):
        ticker = "IBM"
        # Bearish date shown in UI as "Feb 23, 2026"
        bearish_date = datetime(2026, 2, 23, tzinfo=timezone.utc)
        target_date = bearish_date + timedelta(days=10)  # end of analysis window
        bearish_date_str = bearish_date.strftime('%Y-%m-%d')
        pct_threshold = -5.0  # -5% drop (same as UI "5% drop")
        recovery_threshold = 6.0  # 6% recovery (common UI default)

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

        # Assert: manual drop count must equal recovery history item count (no drops missed)
        self.assertEqual(
            len(drops_before_bearish),
            len(items),
            f"Count mismatch: manual -5% drops (date < {bearish_date_str}) = {len(drops_before_bearish)}, "
            f"recovery_history items = {len(items)}. If manual > items, backend may be undercounting.",
        )

        # Document the data: print drop dates so user can verify "only 2" vs expected more
        print(f"\n  IBM: {len(drops_before_bearish)} day-over-day -5% drops in 180 days before {bearish_date_str}")
        for d, pct in sorted(drops_before_bearish, key=lambda x: x[0], reverse=True):
            print(f"    - {d}: {pct}%")
            self.assertLessEqual(pct, pct_threshold, f"Drop on {d}: {pct}%")

    def test_ibm_recovery_history_items_have_expected_dates(self):
        """Sanity check: recovery history for IBM includes the two dates user sees (Feb 11 and Feb 3)."""
        ticker = "IBM"
        bearish_date = datetime(2026, 2, 23, tzinfo=timezone.utc)
        target_date = bearish_date + timedelta(days=10)
        bearish_date_str = bearish_date.strftime('%Y-%m-%d')
        pct_threshold = -5.0
        recovery_threshold = 6.0

        tracker = LayoffTracker()
        graph_start_date = bearish_date - timedelta(days=180)
        price_history_end_date = target_date + timedelta(days=1)
        price_history = tracker.get_stock_price_history(ticker, graph_start_date, price_history_end_date)
        if not price_history or len(price_history) < 2:
            self.skipTest("No price history for IBM (network or API)")

        rh_result = tracker.analyze_recovery_history(
            price_history, pct_threshold, bearish_date_str, None, recovery_threshold=recovery_threshold
        )
        items = rh_result.get('items', []) if isinstance(rh_result, dict) else rh_result

        drop_dates = [item.get('drop_date') for item in items if item.get('drop_date')]
        # User reported seeing Feb 11 and Feb 3; in YYYY-MM-DD that is 2026-02-11 and 2026-02-03
        user_visible_dates = {'2026-02-11', '2026-02-03'}
        for d in user_visible_dates:
            self.assertIn(
                d, drop_dates,
                f"User sees drop on {d} in UI; it should appear in recovery_history items: {drop_dates}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
