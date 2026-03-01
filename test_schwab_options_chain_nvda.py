#!/usr/bin/env python3
"""Unit-style test for Schwab options chain API (NVDA)."""

import json
import sys

import requests


def _summarize_success(data):
    call_map = data.get("callExpDateMap", {})
    put_map = data.get("putExpDateMap", {})
    if not call_map and not put_map:
        raise AssertionError("No callExpDateMap or putExpDateMap returned")

    print("Underlying:", data.get("symbol"))
    print("Underlying price:", data.get("underlyingPrice"))
    print("Call exp dates:", len(call_map))
    print("Put exp dates:", len(put_map))
    print("Top-level keys:", sorted(list(data.keys()))[:20])


def _refresh_access_token():
    refresh_token = (
        "guHfgW1FiPoXIbbftpyA__oelSwzffwamLUnTgOjFa6xV8d4mkVGNaZeVdHTWMz9P0crHwAA8tvBwE-g8_-OwGYF5LK2us5_ntx8N8hVnNIgaf0W1CPg6KUqyI0iuD7xNEk9LGYuJg8@"
    )
    client_id = "jSGRcUly7Ao8i0gwE8A3bhUOGWQC6tAaXYWc8KJTBKShBgOP"
    client_secret = "Hi8NAKygbnvlHeR0YresMd8QHyoO6E2WspZpC7oGvx4uS5WLHNFrq9OH2UosJTUu"
    url = "https://api.schwabapi.com/v1/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    resp = requests.post(url, data=payload, auth=(client_id, client_secret), headers={"accept": "application/json"})
    if resp.status_code != 200:
        raise AssertionError(f"Refresh token failed: {resp.status_code} {resp.text[:500]}")
    data = resp.json()
    new_token = data.get("access_token")
    if not new_token:
        raise AssertionError("Refresh token response missing access_token")
    return new_token


def test_schwab_options_chain_nvda():
    token = "I0.b2F1dGgyLmJkYy5zY2h3YWIuY29t.j8R-fuqd4cgXh3FZhVICZVO7BHThKic5QRkKwJ0-yTM@"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    expiration_url = "https://api.schwabapi.com/marketdata/v1/expirationchain"
    target_expiration = "2026-02-20"
    print("=" * 80)
    print("Expiration chain lookup for NVDA")
    exp_response = requests.get(
        expiration_url,
        params={"symbol": "NVDA"},
        headers=headers,
        timeout=30,
    )
    if exp_response.status_code == 401:
        token = _refresh_access_token()
        headers["Authorization"] = f"Bearer {token}"
        exp_response = requests.get(
            expiration_url,
            params={"symbol": "NVDA"},
            headers=headers,
            timeout=30,
        )
    print("Expiration status:", exp_response.status_code)
    if exp_response.status_code != 200:
        print("Expiration response:", exp_response.text[:1000])
        exp_response.raise_for_status()

    exp_data = exp_response.json()
    expiration_list = exp_data.get("expirationList") or exp_data.get("ExpirationList") or []
    expirations = [
        item.get("expirationDate")
        or item.get("expiration")
        or item.get("ExpirationDate")
        or item.get("Expiration")
        for item in expiration_list
        if isinstance(item, dict)
    ]
    expirations = [exp for exp in expirations if exp]
    print("Expiration count:", len(expirations))
    print("First 10 expirations:", expirations[:10])
    has_target = target_expiration in expirations
    print(f"Has {target_expiration}:", has_target)

    url = "https://api.schwabapi.com/marketdata/v1/chains"
    base_params = {
        "symbol": "NVDA",
        "contractType": "ALL",
        "strikeCount": 14,
        "includeUnderlyingQuote": "true",
        "strategy": "SINGLE",
        "interval": 5,
        "range": "ITM",
        "fromDate": "2026-01-27",
        "toDate": "2026-01-27",
        "expMonth": "FEB",
    }

    variants = [
        ("requested_params", dict(base_params)),
        ("no_interval", {k: v for k, v in base_params.items() if k != "interval"}),
        ("range_all", {**base_params, "range": "ALL"}),
        ("no_expMonth", {k: v for k, v in base_params.items() if k != "expMonth"}),
        ("no_dates", {k: v for k, v in base_params.items() if k not in ("fromDate", "toDate")}),
        ("feb_2026_date", {**base_params, "fromDate": "2026-02-21", "toDate": "2026-02-21"}),
        ("feb_2026_trading_day", {**base_params, "fromDate": "2026-02-20", "toDate": "2026-02-20"}),
        ("feb_2026_thu", {**base_params, "fromDate": "2026-02-19", "toDate": "2026-02-19"}),
        ("feb_2026_no_interval", {
            **base_params,
            "range": "ALL",
            "interval": 5
        }),
        ("minimal_single", {
            "symbol": "NVDA",
            "contractType": "ALL",
            "strikeCount": 14,
            "includeUnderlyingQuote": "true",
            "strategy": "SINGLE",
        }),
    ]

    for label, params in variants:
        print("=" * 80)
        print("Variant:", label)
        print("Request URL:", url)
        print("Params:", json.dumps(params, indent=2))
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code == 401:
            token = _refresh_access_token()
            headers["Authorization"] = f"Bearer {token}"
            response = requests.get(url, params=params, headers=headers, timeout=30)
        print("Status:", response.status_code)
        if response.status_code == 200:
            data = response.json()
            if not isinstance(data, dict):
                raise AssertionError("Expected JSON object response")
            call_map = data.get("callExpDateMap", {})
            put_map = data.get("putExpDateMap", {})
            if call_map or put_map:
                _summarize_success(data)
                return
            print("Empty option maps returned; continuing.")
            print("Top-level keys:", sorted(list(data.keys()))[:20])
            continue
        print("Response:", response.text[:500])

    raise AssertionError("All parameter variants failed")


if __name__ == "__main__":
    try:
        test_schwab_options_chain_nvda()
        print("✅ Schwab options chain test completed")
        sys.exit(0)
    except Exception as exc:
        print(f"❌ Test failed: {exc}")
        sys.exit(1)
