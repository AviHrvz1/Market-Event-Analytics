#!/usr/bin/env python3
"""
Unit test: Verify LRCX butterfly selection matches TOS expectation.

TOS at LRCX ~$217: Left = butterfly whose HIGH is nearest price, Right = LOW nearest price.
Schwab LRCX chain has strikes 190,195,200,210,220,230,240 (no 205,215,225).
Best achievable: Left 200/210/220 (high=220), Right 220/230/240 (low=220).

Current bug: Both show 190/195/200 due to early break in _find_butterflies_for_price.

Run: python test_butterfly_lrcx_tos.py
     python -m unittest test_butterfly_lrcx_tos -v

Requires: Schwab token. Skips if not configured.
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
class TestButterflyLrcxTos(unittest.TestCase):
    """Verify LRCX butterfly left/right selection vs TOS."""

    def test_lrcx_left_right_strikes_vs_tos(self):
        """Left should be 205/210/215, Right should be 215/220/225 at ~$217."""
        from app import _process_butterfly_ticker

        widths = [1, 5, 10]
        row = _process_butterfly_ticker("LRCX", widths)

        self.assertIsNone(row.get("error"), msg=f"LRCX failed: {row.get('error')}")
        price = row.get("current_price")
        self.assertIsNotNone(price, msg="No current price")
        print(f"\n[LRCX] Price: ${price:.2f}")

        # Check dte30 (first column)
        d30 = row.get("dte30")
        if d30:
            left = d30.get("left_butterfly")
            right = d30.get("right_butterfly")
            print(f"  dte30 Left:  {left['strikes'] if left else None}  Right: {right['strikes'] if right else None}")
            if left and right:
                self.assertNotEqual(left["strikes"], right["strikes"], msg="Left and Right must be different butterflies")
                self.assertEqual(left["strikes"], "200/210/220", msg="Left should be 200/210/220")
                self.assertEqual(right["strikes"], "220/230/240", msg="Right should be 220/230/240")

        # Check dte40 (second column)
        d40 = row.get("dte40")
        if d40:
            left = d40.get("left_butterfly")
            right = d40.get("right_butterfly")
            print(f"  dte40 Left:  {left['strikes'] if left else None}  Right: {right['strikes'] if right else None}")
            if left and right:
                self.assertNotEqual(left["strikes"], right["strikes"], msg="Left and Right must be different butterflies")
                self.assertEqual(left["strikes"], "200/210/220", msg="Left should be 200/210/220")
                self.assertEqual(right["strikes"], "220/230/240", msg="Right should be 220/230/240")

    def test_lrcx_chain_debug_exp_key_and_strikes(self):
        """Print exp keys and strikes to diagnose wrong selection."""
        from app import _get_butterfly_expirations_both, _schwab_api_get
        from datetime import datetime

        (exp30_date, _), (exp40_date, _) = _get_butterfly_expirations_both("LRCX")
        exp_dates = [d for d in [exp30_date, exp40_date] if d]
        self.assertTrue(len(exp_dates) >= 1, msg="No expirations for LRCX")

        for exp_date in exp_dates[:2]:
            exp_month = datetime.strptime(exp_date, "%Y-%m-%d").strftime("%b").upper()
            params = {
                "symbol": "LRCX",
                "contractType": "ALL",
                "strikeCount": 100,
                "includeUnderlyingQuote": "true",
                "strategy": "SINGLE",
                "range": "ALL",
                "expMonth": exp_month,
                "fromDate": exp_date,
                "toDate": exp_date,
            }
            r = _schwab_api_get("/chains", params)
            self.assertEqual(r.status_code, 200)
            data = r.json()

            call_map = data.get("callExpDateMap") or {}
            put_map = data.get("putExpDateMap") or {}

            price = data.get("underlyingPrice") or 0
            print(f"\n[LRCX {exp_date}] Price: ${price:.2f}")

            # All exp keys that contain this date
            call_keys = [k for k in call_map.keys() if exp_date in k]
            put_keys = [k for k in put_map.keys() if exp_date in k]
            print(f"  callExpDateMap keys containing '{exp_date}': {call_keys}")
            print(f"  putExpDateMap keys containing '{exp_date}': {put_keys}")

            # First match (what find_exp_key returns)
            exp_key = None
            for k in call_map.keys():
                if exp_date in k:
                    exp_key = k
                    break
            if not exp_key:
                for k in put_map.keys():
                    if exp_date in k:
                        exp_key = k
                        break

            if exp_key:
                s1 = [float(k) for k in call_map.get(exp_key, {}).keys()]
                s2 = [float(k) for k in put_map.get(exp_key, {}).keys()]
                strikes = sorted(set(s1 + s2))
                print(f"  Selected exp_key: {exp_key}")
                print(f"  Strike count: {len(strikes)}")
                # Strikes around price (200-230)
                near = [s for s in strikes if 195 <= s <= 235]
                print(f"  Strikes near price (195-235): {near}")
                print(f"  Full strikes: {strikes}")

                # What _find_butterflies would pick
                from app import _find_butterflies_for_price
                widths = [1, 5, 10]
                left_bf, right_bf = _find_butterflies_for_price(strikes, price, widths)
                print(f"  _find_butterflies result: left={left_bf} right={right_bf}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
