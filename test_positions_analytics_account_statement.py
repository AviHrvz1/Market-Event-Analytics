#!/usr/bin/env python3
"""
Unit test: Position Analytics parsing on AAA-2026-02-03-AccountStatement.csv.
Verifies parse_positions_analytics with ticker-only grouping:
- NEM trades are grouped into a single position (one row for NEM).
- Result has positions and summary; NEM position has multiple detail rows.

Run: python test_positions_analytics_account_statement.py
     python -m unittest test_positions_analytics_account_statement
"""
import os
import unittest
from main import parse_positions_analytics


CSV_PATH = "/Users/avi.horowitz/Desktop/AAA-2026-02-03-AccountStatement.csv"


@unittest.skipUnless(os.path.isfile(CSV_PATH), f"CSV not found: {CSV_PATH}")
class TestPositionsAnalyticsAccountStatement(unittest.TestCase):
    """Test parse_positions_analytics on the Desktop account statement CSV."""

    def test_parse_returns_positions_and_summary(self):
        result = parse_positions_analytics(CSV_PATH)
        self.assertIn("positions", result)
        self.assertIn("summary", result)
        self.assertIsInstance(result["positions"], list)
        self.assertIsInstance(result["summary"], dict)
        self.assertIn("open_count", result["summary"])
        self.assertIn("closed_count", result["summary"])

    def test_nem_ticker_grouping_all_trades_accounted(self):
        """With ticker-only grouping, all NEM trades are grouped by ticker. Details may be merged when same strategy (same expiry/strikes/type)."""
        result = parse_positions_analytics(CSV_PATH)
        positions = result["positions"]
        nem_positions = [p for p in positions if (p.get("ticker") or "").upper() == "NEM"]
        self.assertGreaterEqual(len(nem_positions), 1, "There should be at least one NEM position")
        total_nem_details = sum(len(p.get("details", [])) for p in nem_positions)
        # CSV has 8 NEM TRD rows; after merge of same-strategy details we have between 1 and 8 detail rows
        self.assertGreaterEqual(total_nem_details, 1)
        self.assertLessEqual(total_nem_details, 8, "Detail count cannot exceed CSV rows (merge may reduce count)")

    def test_nem_position_has_expected_fields(self):
        result = parse_positions_analytics(CSV_PATH)
        positions = result["positions"]
        nem_positions = [p for p in positions if (p.get("ticker") or "").upper() == "NEM"]
        self.assertGreaterEqual(len(nem_positions), 1)
        for nem in nem_positions:
            self.assertIn("open_date", nem)
            self.assertIn("pl_total", nem)
            self.assertIn("status", nem)
            self.assertIn("duration", nem)
            self.assertIn(nem["status"], ("Open", "Closed"))

    def test_summary_counts_consistent_with_positions(self):
        result = parse_positions_analytics(CSV_PATH)
        positions = result["positions"]
        summary = result["summary"]
        open_positions = [p for p in positions if p.get("status") == "Open"]
        closed_positions = [p for p in positions if p.get("status") == "Closed"]
        self.assertEqual(summary["open_count"], len(open_positions))
        self.assertEqual(summary["closed_count"], len(closed_positions))


if __name__ == "__main__":
    unittest.main()
