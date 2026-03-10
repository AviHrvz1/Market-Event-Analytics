#!/usr/bin/env python3
"""
Test: PANW Butterfly Arbitrage should show DIFFERENT expirations in col3 vs col4.
Expected: Col3 = 17 Apr 26 (38 DTE), Col4 = 15 May 26 or next monthly.
Bug: Both show MAY 26 (66 DTE) when Apr/May monthlies are filtered as weekly.

Run: python test_butterfly_panw_expirations.py
     python -m unittest test_butterfly_panw_expirations -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _has_schwab_token():
    try:
        from app import _get_schwab_refresh_token
        from config import SCHWAB_TOS_API_KEY
        return bool(_get_schwab_refresh_token() and SCHWAB_TOS_API_KEY)
    except Exception:
        return False


@unittest.skipUnless(_has_schwab_token(), "Schwab token not configured")
class TestButterflyPanwExpirations(unittest.TestCase):
    """Verify PANW returns two distinct expirations for col3 vs col4."""

    def test_panw_exp30_and_exp40_are_different(self):
        """exp30 (col3) and exp40 (col4) must be different dates."""
        from app import _get_butterfly_expirations_both

        (exp30_date, exp30_days), (exp40_date, exp40_days) = _get_butterfly_expirations_both("PANW")

        self.assertIsNotNone(exp30_date)
        self.assertIsNotNone(exp40_date)
        self.assertNotEqual(exp30_date, exp40_date,
            msg="BUG: Both col3 and col4 show same expiration. "
                "Expected col3=Apr 17 (38 DTE), col4=May 15 or next monthly.")

    def test_panw_col3_near_term_col4_far_term(self):
        """Col3 should be nearer-term (e.g. Apr 17 ~38 DTE), Col4 farther (e.g. May 15+)."""
        from app import _get_butterfly_expirations_both

        (exp30_date, exp30_days), (exp40_date, exp40_days) = _get_butterfly_expirations_both("PANW")

        if exp30_date and exp40_date:
            self.assertLess(exp30_days, exp40_days,
                msg="Col3 DTE should be less than Col4 DTE (col3=nearer term)")

    def test_panw_raw_expiration_chain_debug(self):
        """Print raw expiration chain to diagnose weekly filter."""
        from app import _schwab_api_get

        r = _schwab_api_get("/expirationchain", {"symbol": "PANW"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        exp_list = data.get("expirationList") or data.get("ExpirationList") or []

        # Show first 15 with exp_type and standard
        for i, item in enumerate(exp_list[:15]):
            if isinstance(item, dict):
                exp_date = item.get("expirationDate") or item.get("expiration")
                days = item.get("daysToExpiration") or item.get("DaysToExpiration")
                exp_type = item.get("expirationType") or item.get("ExpirationType")
                standard = item.get("standard")
                is_weekly = (exp_type == "W") or (standard is False)
                print(f"  {exp_date} DTE={days} type={exp_type} standard={standard} -> {'WEEKLY' if is_weekly else 'MONTHLY'}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
