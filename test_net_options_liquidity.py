#!/usr/bin/env python3
"""Unit-style check for NET option liquidity (bid/ask + OI)."""

import sys
from statistics import median

import yfinance as yf


def _summarize_spreads(df):
    if df.empty:
        return {
            "count": 0,
            "median_spread": None,
            "median_oi": None,
            "total_oi": 0,
        }

    spreads = (df["ask"] - df["bid"]).tolist()
    ois = df["openInterest"].tolist()
    return {
        "count": len(df),
        "median_spread": median(spreads) if spreads else None,
        "median_oi": median(ois) if ois else None,
        "total_oi": sum(ois),
    }


def test_net_option_liquidity():
    symbol = "NET"
    ticker = yf.Ticker(symbol)

    expirations = ticker.options
    assert expirations, "No options expirations found"

    # Use nearest expiration by default (screening)
    exp = expirations[0]
    chain = ticker.option_chain(exp)

    # Get spot price for ATM band
    hist = ticker.history(period="1d")
    assert not hist.empty, "No price history returned"
    spot = float(hist["Close"].iloc[-1])

    # Near-ATM band (±2%)
    lower = spot * 0.98
    upper = spot * 1.02

    near_calls = chain.calls[(chain.calls["strike"] >= lower) & (chain.calls["strike"] <= upper)]
    near_puts = chain.puts[(chain.puts["strike"] >= lower) & (chain.puts["strike"] <= upper)]

    calls_stats = _summarize_spreads(near_calls)
    puts_stats = _summarize_spreads(near_puts)

    # Basic sanity checks
    assert calls_stats["count"] > 0, "No near-ATM call strikes found"
    assert puts_stats["count"] > 0, "No near-ATM put strikes found"

    print(f"Symbol: {symbol}")
    print(f"Expiry: {exp}")
    print(f"Spot: {spot:.2f}")
    print(f"Calls: {calls_stats}")
    print(f"Puts: {puts_stats}")


if __name__ == "__main__":
    try:
        test_net_option_liquidity()
        print("✅ NET option liquidity check completed")
        sys.exit(0)
    except AssertionError as exc:
        print(f"❌ Test failed: {exc}")
        sys.exit(1)
