#!/usr/bin/env python3
"""
Quick unit-style check for Alpha Vantage key access.

This test:
- Calls a free endpoint (GLOBAL_QUOTE) to validate key works.
- Calls a premium endpoint (REALTIME_OPTIONS) and accepts either
  success data or a premium-access message.
"""

import json
import sys
import urllib.parse
import urllib.request


API_KEY = "DVWSJXY2WJMRPKSR"
BASE_URL = "https://www.alphavantage.co/query"


def _fetch(params):
    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}?{query}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise AssertionError(f"Non-JSON response: {raw[:200]}")


def test_global_quote_key():
    data = _fetch(
        {
            "function": "GLOBAL_QUOTE",
            "symbol": "IBM",
            "apikey": API_KEY,
        }
    )
    assert "Global Quote" in data, f"Unexpected response: {data}"
    assert data["Global Quote"].get("01. symbol") == "IBM", f"Bad quote: {data}"
    print("✅ GLOBAL_QUOTE ok")


def test_realtime_options_access():
    data = _fetch(
        {
            "function": "REALTIME_OPTIONS",
            "symbol": "AAPL",
            "apikey": API_KEY,
        }
    )

    if "optionChain" in data or "data" in data:
        print("✅ REALTIME_OPTIONS returned data (premium access)")
        return

    # Premium endpoints often return an info/error message.
    premium_message = (
        data.get("Information")
        or data.get("Error Message")
        or data.get("Note")
        or ""
    )
    assert premium_message, f"Unexpected response: {data}"
    print(f"ℹ️ REALTIME_OPTIONS blocked (expected): {premium_message}")


if __name__ == "__main__":
    try:
        test_global_quote_key()
        test_realtime_options_access()
        print("✅ Alpha Vantage checks completed")
        sys.exit(0)
    except AssertionError as exc:
        print(f"❌ Test failed: {exc}")
        sys.exit(1)
