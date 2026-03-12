#!/usr/bin/env python3
"""
Unit test: Check IBM options chain for APR 26 (~36 DTE) and detect strike interval jumps.

Identifies where the TOS option chain has non-uniform strike spacing (gaps/jumps)
that would trigger the broken-chain icon in Butterfly Arbitrage.

Run: python test_ibm_chain_strike_jumps.py
     python -m unittest test_ibm_chain_strike_jumps -v

Requires: Schwab token. Skips if not configured.
"""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _has_schwab_token():
    try:
        from app import _get_schwab_refresh_token
        from config import SCHWAB_TOS_API_KEY
        return bool(_get_schwab_refresh_token() and SCHWAB_TOS_API_KEY)
    except Exception:
        return False


def _find_strike_jumps(strikes):
    """
    Compute gaps between consecutive strikes and return list of (idx, strike_low, strike_high, gap).
    Also returns unique_gaps and whether chain is unified.
    """
    if len(strikes) < 2:
        return [], set(), True
    gaps = [round(strikes[i + 1] - strikes[i], 2) for i in range(len(strikes) - 1)]
    unique_gaps = set(gaps)
    unified = len(unique_gaps) <= 1

    jumps = []
    for i, g in enumerate(gaps):
        jumps.append((i, strikes[i], strikes[i + 1], g))

    return jumps, unique_gaps, unified


@unittest.skipUnless(_has_schwab_token(), "Schwab token not configured")
class TestIBMChainStrikeJumps(unittest.TestCase):
    """Verify IBM APR 26 (~36 DTE) option chain strike spacing and locate any jumps."""

    def test_ibm_apr26_chain_strike_jumps(self):
        """Fetch IBM chain for APR 26 (~36 DTE), check for strike interval jumps, report where."""
        from app import _schwab_api_get

        ticker = "IBM"
        target_dte = 36
        dte_tolerance = 8  # Accept 28-44 DTE

        # 1. Fetch expiration chain
        r = _schwab_api_get("/expirationchain", {"symbol": ticker})
        self.assertEqual(r.status_code, 200, msg=f"Expiration chain failed: {r.text[:200]}")
        data = r.json()
        exp_list = data.get("expirationList") or data.get("ExpirationList") or []

        # 2. Find non-weekly expiration with DTE ~36 (APR 26)
        candidates = []
        for item in exp_list:
            if not isinstance(item, dict):
                continue
            exp_date = item.get("expirationDate") or item.get("expiration")
            days = item.get("daysToExpiration") or item.get("DaysToExpiration")
            exp_type = item.get("expirationType") or item.get("ExpirationType")
            if not exp_date or days is None:
                continue
            if exp_type == "W":
                continue
            if target_dte - dte_tolerance <= int(days) <= target_dte + dte_tolerance:
                candidates.append({
                    "expiration_date": exp_date,
                    "days_to_expiration": int(days),
                })

        self.assertTrue(candidates, msg=f"No IBM expirations with DTE ~{target_dte} found")
        # Pick closest to 36 DTE
        best = min(candidates, key=lambda c: abs(c["days_to_expiration"] - target_dte))
        exp_date = best["expiration_date"]
        exp_dte = best["days_to_expiration"]

        print(f"\n[IBM] Using expiration {exp_date} ({exp_dte} DTE) for APR 26")

        # 3. Fetch options chain
        exp_month = datetime.strptime(exp_date, "%Y-%m-%d").strftime("%b").upper()
        params = {
            "symbol": ticker,
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
        self.assertEqual(r.status_code, 200, msg=f"Chains failed: {r.text[:200]}")
        chain_data = r.json()

        # 4. Extract strikes (same logic as app.py compute_for_dte)
        call_map = chain_data.get("callExpDateMap") or {}
        put_map = chain_data.get("putExpDateMap") or {}

        def find_exp_key(side_map, ed):
            for k in side_map.keys():
                if ed in k:
                    return k
            return None

        exp_key = find_exp_key(call_map, exp_date) or find_exp_key(put_map, exp_date)
        self.assertIsNotNone(exp_key, msg=f"No exp key for {exp_date}")

        s1 = [float(k) for k in call_map.get(exp_key, {}).keys()]
        s2 = [float(k) for k in put_map.get(exp_key, {}).keys()]
        all_strikes = sorted(set(s1 + s2))
        self.assertGreater(len(all_strikes), 1, msg="Need at least 2 strikes")

        price = chain_data.get("underlyingPrice") or 0
        print(f"  Underlying: ${price:.2f}")
        print(f"  Full chain strike count: {len(all_strikes)}")

        # 5. Use only 14 strikes nearest the price (near the money)
        NUM_STRIKES = 14
        strikes_near_price = sorted(
            all_strikes,
            key=lambda s: abs(s - price)
        )[:NUM_STRIKES]
        strikes = sorted(strikes_near_price)
        print(f"  Checking {len(strikes)} strikes near price: {strikes}")

        # 6. Compute gaps and find jumps
        jumps, unique_gaps, unified = _find_strike_jumps(strikes)

        print(f"  Unique gaps: {sorted(unique_gaps)}")
        print(f"  Strikes unified: {unified}")

        if not unified:
            # Report each jump (where gap differs from the most common gap)
            gap_counts = {}
            for _, _, _, g in jumps:
                gap_counts[g] = gap_counts.get(g, 0) + 1
            most_common_gap = max(gap_counts.keys(), key=lambda k: gap_counts[k])

            print(f"\n  JUMPS (gap != {most_common_gap}):")
            for idx, strike_low, strike_high, gap in jumps:
                if gap != most_common_gap:
                    print(f"    Jump at index {idx}: {strike_low} -> {strike_high} (gap={gap})")
        else:
            print(f"\n  No jumps: all strikes have uniform spacing of {list(unique_gaps)[0]}")

        # Assert: document the result (test passes either way; we're verifying the chain)
        self.assertIsNotNone(exp_key, msg="Should have exp key")
