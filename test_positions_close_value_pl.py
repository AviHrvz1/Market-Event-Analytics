#!/usr/bin/env python3
"""
Unit test: Net profit if close (mid-price) — real net cash in your pocket.

We value each leg at mid = (bid+ask)/2. P/L is real net profit: for BOT (opened_with_bot)
we use close_credit_debit + cost (cost is negative when paid); for SOLD we use
close_credit_debit - cost. All legs in each vertical (2 legs) and butterfly (3 legs)
are summed; total_pl_if_close is the sum of per-strategy pl_if_close.

Why a small gap vs TOS (~$3,050–$3,150) can still appear:
- Timing: our chain is from the API at request time; TOS is real-time.
- Mark: we use (bid+ask)/2; TOS may use last or a different mark.
- Missing legs: if a strike/exp isn’t in the chain response, we value that leg at 0.

Run: python test_positions_close_value_pl.py -v
     python -m unittest test_positions_close_value_pl -v
"""
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import _compute_pl_if_close_from_chain


def _make_chain(exp_date: str, puts: dict, calls: dict = None):
    """
    puts: { strike: (bid, ask), ... }
    calls: optional { strike: (bid, ask), ... }
    Schwab format: putExpDateMap[exp_key][strike] = [ { "bid": x, "ask": y } ]
    """
    exp_key = exp_date + ":1"
    put_map = {}
    if puts:
        strike_map = {str(float(s)): [{"bid": b, "ask": a}] for s, (b, a) in puts.items()}
        put_map = {exp_key: strike_map}
    call_map = {}
    if calls:
        strike_map = {str(float(s)): [{"bid": b, "ask": a}] for s, (b, a) in calls.items()}
        call_map = {exp_key: strike_map}
    return {"callExpDateMap": call_map, "putExpDateMap": put_map}


class TestPLIfCloseMidPrice(unittest.TestCase):
    """Net profit if close using mid price should match hand-computed real net."""

    def test_single_vertical_known_pl(self):
        # One vertical: SOLD 10 @ 0.60 → we received $600 credit → cost_basis = -600.
        # Legs: 114 PUT -10, 113 PUT +10. Exp 2026-02-06.
        # Mock chain: 114 PUT mid=1.04, 113 PUT mid=0.44.
        # close_credit_debit = -10*1.04*100 + 10*0.44*100 = -600 (we'd pay 600 to close).
        # SOLD: pl_if_close = close_credit_debit - cost = -600 - (-600) = 0.
        strategies = [
            {
                "detail_index": 0,
                "type": "VERTICAL",
                "cost": -600.0,
                "legs": [
                    {"expiration_date": "2026-02-06", "strike": 114.0, "put_call": "PUT", "qty": -10},
                    {"expiration_date": "2026-02-06", "strike": 113.0, "put_call": "PUT", "qty": 10},
                ],
                "opened_with_bot": False,
            }
        ]
        chain = _make_chain("2026-02-06", {114.0: (1.04, 1.04), 113.0: (0.44, 0.44)})
        results, total_pl, per_detail = _compute_pl_if_close_from_chain(strategies, chain, 1)
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0]["close_credit_debit"], -600.0, places=2)
        self.assertAlmostEqual(results[0]["pl_if_close"], 0.0, places=2)
        self.assertAlmostEqual(total_pl, 0.0, places=2)
        self.assertIsNotNone(per_detail[0])
        self.assertAlmostEqual(per_detail[0]["pl_if_close"], 0.0, places=2)

    def test_mid_price_equals_tos_mark_positive_pl(self):
        # BOT: we paid 600 (cost stored as -600). close_credit_debit = 8500.
        # Real net = close + cost = 8500 + (-600) = 7900.
        # One long leg 111 CALL +40: need 40 * mid * 100 = 8500 → mid = 2.125.
        strategies = [
            {
                "detail_index": 0,
                "type": "CALL",
                "cost": -600.0,
                "legs": [
                    {"expiration_date": "2026-02-06", "strike": 111.0, "put_call": "CALL", "qty": 40},
                ],
                "opened_with_bot": True,
            }
        ]
        # Long leg: we use bid when closing (we sell). bid=2.10 → 40*2.10*100 = 8400. Real net = 8400 + (-600) = 7800.
        chain = {
            "callExpDateMap": {"2026-02-06:1": {"111.0": [{"bid": 2.10, "ask": 2.15}]}},
            "putExpDateMap": {},
        }
        results, total_pl, per_detail = _compute_pl_if_close_from_chain(strategies, chain, 1)
        self.assertAlmostEqual(total_pl, 7800.0, places=2, msg="Net profit if close at bid should be +7800")
        self.assertAlmostEqual(results[0]["pl_if_close"], 7800.0, places=2)
        self.assertAlmostEqual(per_detail[0]["pl_if_close"], 7800.0, places=2)

    def test_two_strategies_sum_correct(self):
        # Two SOLD verticals: cost_basis negative (we received credit).
        strategies = [
            {"detail_index": 0, "type": "VERTICAL", "cost": -600.0, "opened_with_bot": False, "legs": [
                {"expiration_date": "2026-02-06", "strike": 114.0, "put_call": "PUT", "qty": -10},
                {"expiration_date": "2026-02-06", "strike": 113.0, "put_call": "PUT", "qty": 10},
            ]},
            {"detail_index": 1, "type": "VERTICAL", "cost": -450.0, "opened_with_bot": False, "legs": [
                {"expiration_date": "2026-02-06", "strike": 116.0, "put_call": "CALL", "qty": -10},
                {"expiration_date": "2026-02-06", "strike": 115.0, "put_call": "CALL", "qty": 10},
            ]},
        ]
        chain = _make_chain("2026-02-06", {114.0: (1.04, 1.04), 113.0: (0.44, 0.44)})
        chain["callExpDateMap"] = {"2026-02-06:1": {"116.0": [{"bid": 0.55, "ask": 0.55}], "115.0": [{"bid": 0.10, "ask": 0.10}]}}
        results, total_pl, per_detail = _compute_pl_if_close_from_chain(strategies, chain, 2)
        # Strategy 0: close = -600, pl = -600 - (-600) = 0.
        # Strategy 1: close = -450, pl = -450 - (-450) = 0.
        self.assertAlmostEqual(results[0]["pl_if_close"], 0.0, places=2)
        self.assertAlmostEqual(results[1]["pl_if_close"], 0.0, places=2)
        self.assertAlmostEqual(total_pl, 0.0, places=2)
        self.assertAlmostEqual(per_detail[0]["pl_if_close"], 0.0, places=2)
        self.assertAlmostEqual(per_detail[1]["pl_if_close"], 0.0, places=2)

    def test_all_legs_summed_per_strategy_total_pl_near_tos(self):
        """
        Verify all legs in each vertical/butterfly are summed correctly and total P/L
        can reach ~TOS P/L Open (+$3,150). Each strategy's close_credit_debit is the sum
        of (qty * mid * 100) over all its legs; total_pl_if_close is sum of pl_if_close.
        """
        exp = "2026-02-06"
        # One chain: PUTs 114/113, CALLs 111/112/113. Mid 111 = 0.7875 → 40*0.7875*100 = 3150.
        chain = _make_chain(
            exp,
            puts={114.0: (1.04, 1.04), 113.0: (0.44, 0.44)},
            calls={111.0: (0.78, 0.795), 112.0: (0.48, 0.48), 113.0: (0.46, 0.48)},
        )
        # Strategy 1: SOLD vertical 114/113 PUT, cost_basis -600. close = -600. pl = 0.
        # Strategy 2: BOT single long 111 CALL +40, cost 0. close = 40*0.7875*100 = 3150. pl = 3150.
        strategies = [
            {"detail_index": 0, "type": "VERTICAL", "cost": -600.0, "opened_with_bot": False, "legs": [
                {"expiration_date": exp, "strike": 114.0, "put_call": "PUT", "qty": -10},
                {"expiration_date": exp, "strike": 113.0, "put_call": "PUT", "qty": 10},
            ]},
            {"detail_index": 1, "type": "CALL", "cost": 0.0, "opened_with_bot": True, "legs": [
                {"expiration_date": exp, "strike": 111.0, "put_call": "CALL", "qty": 40},
            ]},
        ]
        results, total_pl, per_detail = _compute_pl_if_close_from_chain(strategies, chain, 2)
        self.assertEqual(len(results), 2)
        self.assertAlmostEqual(results[0]["close_credit_debit"], -600.0, places=2)
        self.assertAlmostEqual(results[0]["pl_if_close"], 0.0, places=2)
        # Strategy 2: long 40 calls, we use bid when closing. bid=0.78 → 40*0.78*100 = 3120.
        self.assertAlmostEqual(results[1]["close_credit_debit"], 3120.0, places=0)
        self.assertAlmostEqual(results[1]["pl_if_close"], 3120.0, places=0)
        self.assertAlmostEqual(total_pl, 3120.0, places=0, msg="Total net profit should be +$3,120")
        for i in range(2):
            self.assertIsNotNone(per_detail[i])
            self.assertAlmostEqual(per_detail[i]["pl_if_close"], results[i]["pl_if_close"], places=2)

    def test_vertical_and_butterfly_leg_count(self):
        """Ensure each strategy contributes all its legs (2 for vertical, 3 for butterfly)."""
        exp = "2026-02-06"
        chain = _make_chain(exp, puts={114.0: (1.0, 1.0), 113.0: (0.5, 0.5)}, calls={111.0: (0.3, 0.3), 112.0: (0.2, 0.2), 113.0: (0.1, 0.1)})
        # Vertical: 2 legs (SOLD). Butterfly: 3 legs (BOT, we paid 50 → cost -50).
        strategies = [
            {"detail_index": 0, "type": "VERTICAL", "cost": -500.0, "opened_with_bot": False, "legs": [
                {"expiration_date": exp, "strike": 114.0, "put_call": "PUT", "qty": -10},
                {"expiration_date": exp, "strike": 113.0, "put_call": "PUT", "qty": 10},
            ]},
            {"detail_index": 1, "type": "BUTTERFLY", "cost": -50.0, "opened_with_bot": True, "legs": [
                {"expiration_date": exp, "strike": 111.0, "put_call": "CALL", "qty": 10},
                {"expiration_date": exp, "strike": 112.0, "put_call": "CALL", "qty": -20},
                {"expiration_date": exp, "strike": 113.0, "put_call": "CALL", "qty": 10},
            ]},
        ]
        results, total_pl, _ = _compute_pl_if_close_from_chain(strategies, chain, 2)
        # Vertical close = -500. SOLD: pl = -500 - (-500) = 0.
        # Butterfly close = 0. BOT cost -50: pl = 0 + (-50) = -50.
        self.assertAlmostEqual(results[0]["close_credit_debit"], -500.0, places=2)
        self.assertAlmostEqual(results[0]["pl_if_close"], 0.0, places=2)
        self.assertAlmostEqual(results[1]["close_credit_debit"], 0.0, places=2)
        self.assertAlmostEqual(results[1]["pl_if_close"], -50.0, places=2)
        self.assertAlmostEqual(total_pl, -50.0, places=2)


def _price_from_contract(contract):
    """
    Intended behavior when app supports mark/theoretical (Option B):
    Use mark (or theoreticalValue/theo) from chain when present and numeric; else use mid.
    Used only in tests until app code is updated to use mark.
    """
    if not contract:
        return 0.0
    for key in ('mark', 'theoreticalValue', 'theo', 'markPrice'):
        val = contract.get(key)
        if val is not None:
            try:
                f = float(val)
                if f == f:  # not NaN
                    return f
            except (TypeError, ValueError):
                pass
    bid = contract.get('bid')
    ask = contract.get('ask')
    try:
        bid = float(bid) if bid is not None else 0.0
        ask = float(ask) if ask is not None else 0.0
    except (TypeError, ValueError):
        return 0.0
    if bid is not None and ask is not None:
        return (bid + ask) / 2.0
    return bid if bid is not None else ask if ask is not None else 0.0


class TestPriceFromContractMarkOrMid(unittest.TestCase):
    """Tests for 'use mark when present, else mid' (no app code changed yet)."""

    def test_use_mark_when_present(self):
        c = {'bid': 1.0, 'ask': 1.2, 'mark': 1.05}
        self.assertAlmostEqual(_price_from_contract(c), 1.05, places=4)

    def test_use_mid_when_mark_absent(self):
        c = {'bid': 1.0, 'ask': 1.2}
        self.assertAlmostEqual(_price_from_contract(c), 1.1, places=4)

    def test_use_mid_when_mark_none(self):
        c = {'bid': 1.0, 'ask': 1.2, 'mark': None}
        self.assertAlmostEqual(_price_from_contract(c), 1.1, places=4)

    def test_use_theoretical_value_when_mark_absent(self):
        c = {'bid': 1.0, 'ask': 1.2, 'theoreticalValue': 1.07}
        self.assertAlmostEqual(_price_from_contract(c), 1.07, places=4)

    def test_mark_takes_precedence_over_theoretical(self):
        c = {'bid': 1.0, 'ask': 1.2, 'mark': 1.05, 'theoreticalValue': 1.07}
        self.assertAlmostEqual(_price_from_contract(c), 1.05, places=4)

    def test_empty_contract_returns_zero(self):
        self.assertAlmostEqual(_price_from_contract({}), 0.0, places=4)
        self.assertAlmostEqual(_price_from_contract(None), 0.0, places=4)


if __name__ == "__main__":
    unittest.main()
