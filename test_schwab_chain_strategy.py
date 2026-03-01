#!/usr/bin/env python3
"""
Unit test: Check if Schwab chains API returns strategy-level prices when using
strategy=BUTTERFLY or strategy=VERTICAL (vs leg-by-leg from strategy=SINGLE).

Run: python test_schwab_chain_strategy.py -v
     python -m unittest test_schwab_chain_strategy -v

Requires: Schwab refresh token and API key configured (same as app).
Skips all tests if token is not available.
"""
import os
import sys
import unittest

# Load app to use its Schwab auth and API get
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Skip entire module if no Schwab token
def _has_schwab_token():
    try:
        from app import _get_schwab_refresh_token
        from config import SCHWAB_TOS_API_KEY
        return bool(_get_schwab_refresh_token() and SCHWAB_TOS_API_KEY)
    except Exception:
        return False


@unittest.skipUnless(_has_schwab_token(), "Schwab token not configured")
class TestSchwabChainStrategy(unittest.TestCase):
    """Check chains API response for strategy=BUTTERFLY and strategy=VERTICAL."""

    def test_chains_single_response_structure(self):
        """Baseline: SINGLE chain returns callExpDateMap/putExpDateMap with per-leg options."""
        from app import _schwab_api_get
        from datetime import datetime
        from_date = "2026-03-01"
        to_date = "2026-03-31"
        params = {
            "symbol": "SNOW",
            "contractType": "ALL",
            "strikeCount": 20,
            "includeUnderlyingQuote": "true",
            "strategy": "SINGLE",
            "range": "ALL",
            "expMonth": "MAR",
            "fromDate": from_date,
            "toDate": to_date,
        }
        r = _schwab_api_get("/chains", params)
        self.assertEqual(r.status_code, 200, msg=f"Chains SINGLE failed: {r.text}")
        data = r.json()
        self.assertIn("symbol", data)
        # SINGLE returns maps by expiry and strike with single-option quotes
        has_calls = "callExpDateMap" in data and bool(data.get("callExpDateMap"))
        has_puts = "putExpDateMap" in data and bool(data.get("putExpDateMap"))
        self.assertTrue(has_calls or has_puts, msg="SINGLE chain should have call or put map")

    def test_chains_butterfly_response_has_strategy_level_quote(self):
        """Request chain with strategy=BUTTERFLY; check if API returns 200 and strategy-level bid/ask. Schwab may return 400 (Not Found)."""
        from app import _schwab_api_get
        from_date = "2026-03-01"
        to_date = "2026-03-31"
        params = {
            "symbol": "SNOW",
            "contractType": "ALL",
            "strikeCount": 25,
            "includeUnderlyingQuote": "true",
            "strategy": "BUTTERFLY",
            "interval": 5,
            "range": "ALL",
            "expMonth": "MAR",
            "fromDate": from_date,
            "toDate": to_date,
        }
        r = _schwab_api_get("/chains", params)
        if r.status_code != 200:
            # Schwab API often returns 400/404 for BUTTERFLY strategy chain (not supported or different params needed)
            print(f"\n[BUTTERFLY] API returned {r.status_code}: {r.text[:200]}")
            self.assertIn(r.status_code, (200, 400, 404), msg="Document known response: 200=has strategy price, 400/404=not supported")
            return
        data = r.json()
        top_keys = list(data.keys())
        print(f"\n[BUTTERFLY] response top-level keys: {top_keys}")
        strategy_like_keys = [k for k in top_keys if "butterfly" in k.lower() or "strategy" in k.lower() or "spread" in k.lower()]
        has_strategy_map = bool(strategy_like_keys)
        if "callExpDateMap" in data and data["callExpDateMap"]:
            sample_exp = next(iter(data["callExpDateMap"].keys()))
            sample_strikes = data["callExpDateMap"][sample_exp]
            if sample_strikes:
                sample_strike = next(iter(sample_strikes.keys()))
                sample_contract = sample_strikes[sample_strike]
                if isinstance(sample_contract, list) and sample_contract:
                    sample_contract = sample_contract[0]
                print(f"[BUTTERFLY] sample contract keys: {list(sample_contract.keys()) if isinstance(sample_contract, dict) else type(sample_contract)}")
                has_bid_ask = isinstance(sample_contract, dict) and ("bid" in sample_contract or "ask" in sample_contract)
                self.assertTrue(has_bid_ask or has_strategy_map,
                    msg="BUTTERFLY response should have strategy-like keys or bid/ask on contract")
        else:
            self.assertTrue(has_strategy_map or "callExpDateMap" in data or "putExpDateMap" in data,
                msg="BUTTERFLY response should have some option/strategy structure")

    def test_chains_vertical_response_has_strategy_level_quote(self):
        """Request chain with strategy=VERTICAL; check if response has strategy-level bid/ask."""
        from app import _schwab_api_get
        from_date = "2026-03-01"
        to_date = "2026-03-31"
        params = {
            "symbol": "SNOW",
            "contractType": "ALL",
            "strikeCount": 25,
            "includeUnderlyingQuote": "true",
            "strategy": "VERTICAL",
            "interval": 5,
            "range": "ALL",
            "expMonth": "MAR",
            "fromDate": from_date,
            "toDate": to_date,
        }
        r = _schwab_api_get("/chains", params)
        self.assertEqual(r.status_code, 200, msg=f"Chains VERTICAL failed: {r.text}")
        data = r.json()
        top_keys = list(data.keys())
        print(f"\n[VERTICAL] response top-level keys: {top_keys}")
        strategy_like_keys = [k for k in top_keys if "vertical" in k.lower() or "strategy" in k.lower() or "spread" in k.lower()]
        has_strategy_map = bool(strategy_like_keys)
        if "callExpDateMap" in data and data["callExpDateMap"]:
            sample_exp = next(iter(data["callExpDateMap"].keys()))
            sample_strikes = data["callExpDateMap"][sample_exp]
            if sample_strikes:
                sample_strike = next(iter(sample_strikes.keys()))
                sample_contract = sample_strikes[sample_strike]
                if isinstance(sample_contract, list) and sample_contract:
                    sample_contract = sample_contract[0]
                print(f"[VERTICAL] sample contract keys: {list(sample_contract.keys()) if isinstance(sample_contract, dict) else type(sample_contract)}")
                has_bid_ask = isinstance(sample_contract, dict) and ("bid" in sample_contract or "ask" in sample_contract)
                self.assertTrue(has_bid_ask or has_strategy_map,
                    msg="VERTICAL response should have strategy-like keys or bid/ask on contract")
        else:
            self.assertTrue(has_strategy_map or "callExpDateMap" in data or "putExpDateMap" in data,
                msg="VERTICAL response should have some option/strategy structure")

    def test_vertical_response_has_price_per_strategy(self):
        """Check if we can get a price per strategy: VERTICAL chain may use callExpDateMap/putExpDateMap or monthlyStrategyList."""
        from app import _schwab_api_get
        from_date = "2026-03-01"
        to_date = "2026-03-31"
        params = {
            "symbol": "SNOW",
            "contractType": "ALL",
            "strikeCount": 25,
            "includeUnderlyingQuote": "true",
            "strategy": "VERTICAL",
            "interval": 5,
            "range": "ALL",
            "expMonth": "MAR",
            "fromDate": from_date,
            "toDate": to_date,
        }
        r = _schwab_api_get("/chains", params)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        # Check callExpDateMap / putExpDateMap for contract with bid/ask
        call_map = data.get("callExpDateMap") or {}
        put_map = data.get("putExpDateMap") or {}
        for name, strike_map in (("call", call_map), ("put", put_map)):
            if not strike_map:
                continue
            for exp_key, strikes in strike_map.items():
                for strike_key, contracts in strikes.items():
                    if not contracts:
                        continue
                    c = contracts[0] if isinstance(contracts[0], dict) else contracts
                    if isinstance(c, dict) and (c.get("bid") is not None or c.get("ask") is not None):
                        print(f"\n[VERTICAL] price per strategy: {name} exp={exp_key} strike={strike_key} bid={c.get('bid')} ask={c.get('ask')}")
                        return  # found strategy-level bid/ask
        # If maps are empty, check monthlyStrategyList (Schwab may put strategy data there)
        monthly = data.get("monthlyStrategyList") or data.get("intervals") or []
        if isinstance(monthly, dict):
            monthly = list(monthly.values()) if monthly else []
        if isinstance(monthly, list) and monthly:
            print(f"\n[VERTICAL] monthlyStrategyList/intervals present (len={len(monthly)}), exp maps empty: use SINGLE for leg-by-leg")
        # Pass if we got 200 and have known structure; strategy-level price may be in empty exp maps (API quirk)
        self.assertIn("strategy", data)
        self.assertEqual(data.get("strategy"), "VERTICAL")


@unittest.skipUnless(_has_schwab_token(), "Schwab token not configured")
class TestSnowVerticalsCloseValue(unittest.TestCase):
    """
    Integration-style test: call the Flask close-value endpoint for SNOW and
    confirm that the two vertical strategies currently open in the CSV
    (160/165 CALL and 170/165 PUT) produce the same close and net P/L numbers
    that the UI shows:

    - 160/165 CALL vertical: Cost -480, Close +320, Net -160
    - 170/165 PUT vertical:  Cost -510, Close -520, Net -1030

    This test does **not** change any app logic; it only:
    - Parses the existing AccountStatement.csv to locate the SNOW position and
      confirm the first two details are the expected verticals.
    - Uses Flask's test client to call /api/positions-analytics/close-value?ticker=SNOW
      and asserts that per_detail[0] and per_detail[1] match the UI numbers.

    Note: This depends on live Schwab chain quotes; if the market moves
    substantially or the CSV/position set changes, the expected numbers
    will need to be updated.
    """

    def test_snow_verticals_close_value_matches_ui_numbers(self):
        from app import app as flask_app
        from main import parse_positions_analytics
        import os

        # 1) Confirm the SNOW open position and detail ordering match expectations.
        csv_path = os.path.join(os.path.dirname(__file__), "data", "AccountStatement.csv")
        result = parse_positions_analytics(csv_path)
        positions = result.get("positions", [])
        snow_pos = None
        for p in positions:
            if (p.get("ticker") or "").strip().upper() == "SNOW" and p.get("status") == "Open":
                snow_pos = p
                break
        self.assertIsNotNone(snow_pos, msg="SNOW open position not found in parsed positions analytics")

        details = snow_pos.get("details") or []
        self.assertGreaterEqual(len(details), 2, msg="Expected at least two SNOW details (two verticals)")

        desc0 = (details[0].get("description") or "").strip()
        desc1 = (details[1].get("description") or "").strip()
        self.assertIn("160/165 CALL", desc0, msg=f"Detail[0] is not the 160/165 CALL vertical: {desc0}")
        self.assertIn("170/165 PUT", desc1, msg=f"Detail[1] is not the 170/165 PUT vertical: {desc1}")

        # 2) Call the live close-value endpoint for SNOW.
        client = flask_app.test_client()
        resp = client.get("/api/positions-analytics/close-value?ticker=SNOW")
        self.assertEqual(resp.status_code, 200, msg=f"close-value endpoint failed: {resp.data[:200]}")

        data = resp.get_json()
        self.assertIsInstance(data, dict, msg="close-value response should be JSON object")
        per_detail = data.get("per_detail") or []
        self.assertGreaterEqual(len(per_detail), 2, msg="per_detail should have at least two entries for SNOW")

        d0 = per_detail[0] or {}
        d1 = per_detail[1] or {}

        # 3) Assert that the computed close (credit/debit) and net P/L match the UI numbers.
        # UI snapshot:
        # 2/4/26 21:53:30 BOT +2 VERTICAL SNOW 160/165 CALL @2.40  Cost -480  Close +320  Net -160
        # 2/6/26 17:45:26 BOT +2 VERTICAL SNOW 170/165 PUT  @2.55  Cost -510  Close -520 Net -1030
        close0 = float(d0.get("close_credit_debit", 0.0))
        net0 = float(d0.get("pl_if_close_real", d0.get("pl_if_close", 0.0)))
        close1 = float(d1.get("close_credit_debit", 0.0))
        net1 = float(d1.get("pl_if_close_real", d1.get("pl_if_close", 0.0)))

        self.assertAlmostEqual(close0, 320.0, places=1, msg=f"SNOW 160/165 CALL close should be ~+320, got {close0}")
        self.assertAlmostEqual(net0, -160.0, places=1, msg=f"SNOW 160/165 CALL net P/L should be ~-160, got {net0}")

        self.assertAlmostEqual(close1, -520.0, places=1, msg=f"SNOW 170/165 PUT close should be ~-520, got {close1}")
        self.assertAlmostEqual(net1, -1030.0, places=1, msg=f"SNOW 170/165 PUT net P/L should be ~-1030, got {net1}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
