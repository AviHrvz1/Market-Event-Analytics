#!/bin/bash
# Run Flask with no proxy so Schwab API works (avoids Tunnel connection failed: 403 Forbidden)
export NO_PROXY='*'
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
cd "$(dirname "$0")"
exec env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy FLASK_APP=app.py python3 -m flask run --host=127.0.0.1 --port=8083
