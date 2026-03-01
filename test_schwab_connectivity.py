#!/usr/bin/env python3
"""
Unittest: check if we can connect to api.schwabapi.com.
Useful to see if the failure is proxy/tunnel (403) vs network vs auth.

Run from project root:
  python3 test_schwab_connectivity.py

If test_schwab_reachable_without_proxy fails with ProxyError, run with proxy unset:
  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy python3 test_schwab_connectivity.py

Interpretation:
- test_schwab_reachable_without_proxy PASS = we can reach Schwab when proxy is disabled.
- test_schwab_reachable_without_proxy FAIL (ProxyError) = proxy still in use; run Flask with run_local_no_proxy.sh.
- test_schwab_token_refresh_if_configured = real refresh (200=ok, 400/401=reached Schwab, token/params issue).
"""
import os
import sys
import unittest
import requests

# Schwab token URL - reaching it (even 400/401) means we're not blocked by proxy
SCHWAB_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"


def _no_proxy_request(method, url, timeout=15, **kwargs):
    """Same idea as app._schwab_no_proxy_request: no proxy for this request."""
    proxy_vars = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy")
    saved = {k: os.environ.pop(k, None) for k in proxy_vars}
    kwargs.setdefault("proxies", {"http": None, "https": None})
    try:
        session = requests.Session()
        session.trust_env = False
        return session.request(method, url, timeout=timeout, **kwargs)
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def _default_request(method, url, timeout=15, **kwargs):
    """Normal request (uses env proxy if set)."""
    return requests.request(method, url, timeout=timeout, **kwargs)


class TestSchwabConnectivity(unittest.TestCase):
    """Check connectivity to api.schwabapi.com with and without proxy."""

    def test_schwab_reachable_without_proxy(self):
        """
        Call Schwab token endpoint with no proxy. We expect to reach the server.
        - 400/401 = we reached Schwab (auth/params issue, not proxy).
        - ProxyError / 403 from proxy = we did not bypass proxy or tunnel is in the path.
        """
        try:
            # POST with minimal body; Schwab will return 400 (missing params) or 401 if we reached them
            r = _no_proxy_request(
                "post",
                SCHWAB_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            )
            # Reaching the server gives 400 (bad request) or 401 (unauthorized), not ProxyError
            self.assertIn(
                r.status_code,
                (400, 401, 403),
                f"Expected 400/401/403 from Schwab when we reach them; got {r.status_code}",
            )
        except requests.exceptions.ProxyError as e:
            self.fail(
                f"ProxyError when using NO-proxy request: {e}. "
                "So proxy is still in use (e.g. system proxy). Run with: env -u HTTP_PROXY -u HTTPS_PROXY python test_schwab_connectivity.py"
            )
        except requests.exceptions.SSLError as e:
            self.fail(f"SSL error reaching Schwab (no proxy): {e}")
        except requests.exceptions.ConnectTimeout:
            self.fail("Timeout reaching api.schwabapi.com (no proxy). Check network/firewall.")
        except requests.exceptions.ConnectionError as e:
            self.fail(f"Connection error (no proxy): {e}")

    def test_schwab_with_default_request_shows_proxy_or_ok(self):
        """
        Call with default requests (env proxy used if set). Documents what happens
        when proxy is in use: often ProxyError / 403. Skip assertion so we only report.
        """
        try:
            r = _default_request(
                "post",
                SCHWAB_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            )
            # If we get here, no proxy or proxy allowed the request
            print(f"  [info] Default request to Schwab: status {r.status_code} (no ProxyError)")
        except requests.exceptions.ProxyError as e:
            print(f"  [info] Default request hit ProxyError (expected if tunnel/proxy is set): {type(e).__name__}")
        except Exception as e:
            print(f"  [info] Default request: {type(e).__name__}: {e}")

    def test_schwab_token_refresh_if_configured(self):
        """
        If SCHWAB_TOS_API_KEY, SCHWAB_TOS_API_SECRET, and refresh token are set,
        try a real token refresh (no proxy). Success or clear auth error = we can reach Schwab.
        """
        try:
            from config import (
                SCHWAB_TOS_API_KEY,
                SCHWAB_TOS_API_SECRET,
                SCHWAB_TOS_REFRESH_TOKEN,
            )
        except ImportError:
            self.skipTest("config not available")

        refresh = (SCHWAB_TOS_REFRESH_TOKEN or "").strip()
        if not SCHWAB_TOS_API_KEY or not SCHWAB_TOS_API_SECRET or not refresh:
            self.skipTest("Schwab credentials not configured (key, secret, or refresh token missing)")

        try:
            r = _no_proxy_request(
                "post",
                SCHWAB_TOKEN_URL,
                data={"grant_type": "refresh_token", "refresh_token": refresh},
                auth=(SCHWAB_TOS_API_KEY, SCHWAB_TOS_API_SECRET),
                headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            if r.status_code == 200:
                print("  [info] Token refresh succeeded (Schwab reachable, no proxy issue).")
                return
            # 400/401 = we reached Schwab (token expired etc.)
            self.assertIn(
                r.status_code,
                (400, 401),
                f"Token refresh returned {r.status_code}; expected 200 or 400/401",
            )
            print(f"  [info] Token refresh returned {r.status_code} (reached Schwab; check token/credentials).")
        except requests.exceptions.ProxyError as e:
            self.fail(
                f"ProxyError during token refresh (no-proxy path): {e}. "
                "Run with: env -u HTTP_PROXY -u HTTPS_PROXY python test_schwab_connectivity.py"
            )


if __name__ == "__main__":
    # Load .env if present so config/app can see credentials
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    unittest.main(verbosity=2, exit=True)
