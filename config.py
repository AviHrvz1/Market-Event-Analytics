import os
import urllib.parse
from dotenv import load_dotenv

try:
    load_dotenv()
except PermissionError:
    # Some environments block reading .env (macOS TCC, etc.); rely on defaults/env vars
    pass

# Load keys from app_secrets.py (gitignored); fallback to env or placeholder if missing
try:
    from app_secrets import (
        NEWS_API_KEY as _NEWS_API_KEY,
        PRIXE_API_KEY as _PRIXE_API_KEY,
        CLAUDE_API_KEY as _CLAUDE_API_KEY,
        SCHWAB_TOS_API_KEY as _SCHWAB_TOS_API_KEY,
        SCHWAB_TOS_API_SECRET as _SCHWAB_TOS_API_SECRET,
    )
except ImportError:
    _NEWS_API_KEY = _PRIXE_API_KEY = _CLAUDE_API_KEY = _SCHWAB_TOS_API_KEY = _SCHWAB_TOS_API_SECRET = ''

# News API configuration (set NEWS_API_KEY in .env or app_secrets)
NEWS_API_KEY = os.getenv('NEWS_API_KEY') or _NEWS_API_KEY or ''
NEWS_API_EVERYTHING_URL = 'https://newsapi.org/v2/everything'
NEWS_API_HEADLINES_URL = 'https://newsapi.org/v2/top-headlines'
NEWSAPI_MAX_LOOKBACK_DAYS = 30  # NewsAPI historical cap on free/business plans

# Prixe.io Stock Price API configuration (set PRIXE_API_KEY in .env or app_secrets)
PRIXE_API_KEY = os.getenv('PRIXE_API_KEY') or _PRIXE_API_KEY or ''
PRIXE_BASE_URL = 'https://api.prixe.io'
# Prixe.io API endpoints - if /api/price doesn't work, try /api/historical or check Prixe.io documentation
PRIXE_PRICE_ENDPOINT = os.getenv('PRIXE_PRICE_ENDPOINT', '/api/price')

# Claude API configuration for AI opinion (set CLAUDE_API_KEY in .env or app_secrets)
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY') or _CLAUDE_API_KEY or ''

# Schwab (TOS) developer credentials - used for option chain / close-value (Think or Swim).
# If you see "refresh_token_authentication_error" or "unsupported_token_type", the refresh
# token has expired. Re-run the OAuth flow and paste the new token in data/schwab_refresh_token.txt
# (or set SCHWAB_TOS_REFRESH_TOKEN in .env).

# Callback URL: set SCHWAB_TOS_CALLBACK_URL in env for Beanstalk; default for local + tunnel
SCHWAB_TOS_CALLBACK_URL = os.getenv(
    'SCHWAB_TOS_CALLBACK_URL',
    'https://api.avi-marketdata.xyz/schwab/callback'
)

# Authorize URL - client_id and redirect_uri from config (env-driven)
_schwab_cid = os.getenv('SCHWAB_TOS_API_KEY') or _SCHWAB_TOS_API_KEY or ''
SCHWAB_TOS_AUTHORIZE_URL = (
    'https://api.schwabapi.com/v1/oauth/authorize'
    '?client_id=' + urllib.parse.quote(_schwab_cid, safe='')
    + '&redirect_uri=' + urllib.parse.quote(SCHWAB_TOS_CALLBACK_URL, safe='')
    + '&response_type=code'
)

# Schwab (TOS) credentials - set in .env or app_secrets
SCHWAB_TOS_API_KEY = os.getenv('SCHWAB_TOS_API_KEY') or _SCHWAB_TOS_API_KEY or ''
SCHWAB_TOS_API_SECRET = os.getenv('SCHWAB_TOS_API_SECRET') or _SCHWAB_TOS_API_SECRET or ''
SCHWAB_TOS_APP_MACHINE_NAME = os.getenv('SCHWAB_TOS_APP_MACHINE_NAME', '')

# Refresh token: from env, or from file data/schwab_refresh_token.txt (paste token there so you don't lose it)
def _read_schwab_refresh_token_from_file():
    path = os.path.join(os.path.dirname(__file__), 'data', 'schwab_refresh_token.txt')
    if os.path.isfile(path):
        try:
            with open(path, 'r') as f:
                line = f.read().strip().splitlines()
                if line and line[0].strip() and not line[0].strip().startswith('#'):
                    return line[0].strip()
        except Exception:
            pass
    return None

SCHWAB_TOS_REFRESH_TOKEN = os.getenv('SCHWAB_TOS_REFRESH_TOKEN') or _read_schwab_refresh_token_from_file() or ''

# Schwab heartbeat: run every N hours to keep refresh token active (default 24)
SCHWAB_HEARTBEAT_INTERVAL_HOURS = float(os.getenv('SCHWAB_HEARTBEAT_INTERVAL_HOURS', '24'))

# Performance optimization settings
MAX_ARTICLES_TO_PROCESS = int(os.getenv('MAX_ARTICLES_TO_PROCESS', '300'))  # Limit total articles processed (increased to 300 to find more articles)
DEDUPLICATE_BY_COMPANY = os.getenv('DEDUPLICATE_BY_COMPANY', 'false').lower() == 'true'  # Keep only most recent per company (set to false to show all articles)  # Alternative: '/api/historical', '/api/v1/price'

# SEC EDGAR configuration
SEC_EDGAR_BASE_URL = 'https://www.sec.gov'
SEC_EDGAR_SEARCH_URL = 'https://www.sec.gov/cgi-bin/browse-edgar'
SEC_EDGAR_COMPANY_API = 'https://data.sec.gov/submissions'
SEC_USER_AGENT = 'LayoffTracker/1.0 (contact@example.com)'

# Core thresholds
MIN_LAYOFF_PERCENTAGE = 1.0
LOOKBACK_DAYS = 120

# Event types for market-moving corporate events
EVENT_TYPES = {
    'real_estate_good_news': {
        'name': 'Real Estate Good News',
        'keywords': [],
        'requires_all': False,
        'query_by_company_names': True,
        'sic_codes': [6512, 6513, 6514, 6515, 6517, 6519, 6531, 6552, 6798]  # Real estate SIC codes
    },
    'real_estate_bad_news': {
        'name': 'Real Estate Bad News',
        'keywords': [],
        'requires_all': False,
        'query_by_company_names': True,
        'sic_codes': [6512, 6513, 6514, 6515, 6517, 6519, 6531, 6552, 6798]  # Real estate SIC codes
    },
}

# Backwards compatibility helper
LAYOFF_KEYWORDS = []
