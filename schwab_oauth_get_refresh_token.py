#!/usr/bin/env python3
"""
One-time script to get a new Schwab OAuth refresh token.

Run: python3 schwab_oauth_get_refresh_token.py

1. Script prints a URL — open it in your browser.
2. Log in at Schwab and approve the app.
3. You will be redirected. Either:
   - (Local server) The script catches the redirect and prints your new refresh_token, or
   - (Manual) Copy the FULL URL from your browser's address bar and paste it when prompted.
4. Add the printed refresh_token to your .env as SCHWAB_TOS_REFRESH_TOKEN and restart the app.

Requires: Your Schwab app's callback URL must match what this script uses.
  Default: https://127.0.0.1:8765 — add this exact URL to your app's callback URLs at
  https://developer.schwab.com (or https://beta-developer.schwab.com).
  Or set SCHWAB_TOS_REDIRECT_URI in .env to your existing callback (e.g. https://127.0.0.1:8182).
"""

import os
import sys
import urllib.parse
import webbrowser
import ssl
import socket
import tempfile
import subprocess

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Config from env or project config
try:
    from config import SCHWAB_TOS_API_KEY as _K, SCHWAB_TOS_API_SECRET as _S, SCHWAB_TOS_CALLBACK_URL as _CB, SCHWAB_TOS_AUTHORIZE_URL as _AUTH
    _default_key, _default_secret = _K, _S
    _default_redirect = _CB
    _default_auth_url = _AUTH
except Exception:
    _default_key = _default_secret = ''
    _default_redirect = 'https://127.0.0.1:8765'
    _default_auth_url = None

SCHWAB_TOS_API_KEY = os.getenv('SCHWAB_TOS_API_KEY', _default_key)
SCHWAB_TOS_API_SECRET = os.getenv('SCHWAB_TOS_API_SECRET', _default_secret)
SCHWAB_TOS_REDIRECT_URI = os.getenv('SCHWAB_TOS_REDIRECT_URI', _default_redirect)


if not SCHWAB_TOS_API_KEY or not SCHWAB_TOS_API_SECRET:
    print('Missing SCHWAB_TOS_API_KEY or SCHWAB_TOS_API_SECRET. Set them in .env or config.py.')
    sys.exit(1)

AUTH_URL = 'https://api.schwabapi.com/v1/oauth/authorize'
TOKEN_URL = 'https://api.schwabapi.com/v1/oauth/token'


def build_auth_url():
    if _default_auth_url and SCHWAB_TOS_REDIRECT_URI == _default_redirect:
        return _default_auth_url
    params = {
        'client_id': SCHWAB_TOS_API_KEY,
        'redirect_uri': SCHWAB_TOS_REDIRECT_URI,
        'response_type': 'code',
    }
    return AUTH_URL + '?' + urllib.parse.urlencode(params)


def exchange_code_for_tokens(code: str):
    import requests
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SCHWAB_TOS_REDIRECT_URI,
    }
    response = requests.post(
        TOKEN_URL,
        data=payload,
        auth=(SCHWAB_TOS_API_KEY, SCHWAB_TOS_API_SECRET),
        headers={'accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=30,
    )
    if response.status_code != 200:
        print(f'Token exchange failed: {response.status_code} {response.text}')
        return None
    return response.json()


def run_local_server():
    """Start a minimal HTTPS server to catch the redirect. Requires openssl for self-signed cert."""
    import http.server
    import threading

    code_holder = {'code': None, 'done': False}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            code_holder['code'] = (qs.get('code') or [None])[0]
            code_holder['done'] = True
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Success</h1><p>You can close this window and return to the script.</p></body></html>')

        def log_message(self, format, *args):
            pass

    cert_file = os.path.join(tempfile.gettempdir(), 'schwab_oauth_cert.pem')
    key_file = os.path.join(tempfile.gettempdir(), 'schwab_oauth_key.pem')
    host = '127.0.0.1'
    port = 8765

    # Generate self-signed cert if missing
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        try:
            subprocess.run([
                'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
                '-keyout', key_file, '-out', cert_file, '-days', '365',
                '-nodes', '-subj', '/CN=127.0.0.1',
                '-addext', 'subjectAltName=IP:127.0.0.1',
            ], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print('Could not generate HTTPS cert (openssl required for local server).')
            print('Falling back to manual paste flow.')
            return None

    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        server = http.server.HTTPServer((host, port), Handler)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    except Exception as e:
        print(f'Could not start HTTPS server: {e}')
        print('Falling back to manual paste flow.')
        return None

    def serve():
        server.handle_request()
        server.server_close()

    thread = threading.Thread(target=serve)
    thread.daemon = True
    thread.start()
    return code_holder


def main():
    print('Schwab OAuth — get new refresh token')
    print('-------------------------------------')
    print(f'Redirect URI: {SCHWAB_TOS_REDIRECT_URI}')
    print('(This must match exactly the callback URL in your Schwab app.)')
    print()

    auth_url = build_auth_url()

    # Try local HTTPS server if redirect is localhost 8765
    code_holder = None
    if SCHWAB_TOS_REDIRECT_URI.rstrip('/') == 'https://127.0.0.1:8765':
        code_holder = run_local_server()
        if code_holder is not None:
            print('Local server running. Opening browser...')
            webbrowser.open(auth_url)
            print('Waiting for you to log in at Schwab and approve (max 120s)...')
            import time
            for _ in range(600):
                time.sleep(0.2)
                if code_holder['done']:
                    break
            code = code_holder.get('code')
            if not code:
                print('No redirect received in time. Use manual paste flow (see URL above).')
        else:
            code = None
    else:
        code = None

    if code is None:
        print('Open this URL in your browser:')
        print()
        print(auth_url)
        print()
        print('After logging in, you will be redirected.')
        print('Copy the FULL URL from your browser (including ?code=...) and paste it below.')
        try:
            redirect_url = input('Paste redirect URL: ').strip()
        except EOFError:
            redirect_url = ''
        if not redirect_url:
            print('No URL entered. Exiting.')
            sys.exit(1)
        parsed = urllib.parse.urlparse(redirect_url)
        qs = urllib.parse.parse_qs(parsed.query)
        code = (qs.get('code') or [None])[0]
        if not code:
            print('Could not find "code" in the URL. Make sure you pasted the full URL.')
            sys.exit(1)

    try:
        import requests
    except ImportError:
        print('Install requests: pip install requests')
        sys.exit(1)

    data = exchange_code_for_tokens(code)
    if not data:
        sys.exit(1)

    refresh_token = data.get('refresh_token')
    access_token = data.get('access_token')
    if not refresh_token:
        print('No refresh_token in response:', data)
        sys.exit(1)

    print()
    print('Success. Add this to your .env file:')
    print()
    print(f'SCHWAB_TOS_REFRESH_TOKEN={refresh_token}')
    print()
    print('Then restart your app.')
    if access_token:
        print('(Access token also received; app will use refresh_token to get new access tokens.)')


if __name__ == '__main__':
    main()
