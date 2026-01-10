import os
from dotenv import load_dotenv

try:
    load_dotenv()
except PermissionError:
    # Some environments block reading .env (macOS TCC, etc.); rely on defaults/env vars
    pass

# News API configuration
NEWS_API_KEY = os.getenv('NEWS_API_KEY', 'e876bac25bb346a1985dfdc6b582b122')
NEWS_API_EVERYTHING_URL = 'https://newsapi.org/v2/everything'
NEWS_API_HEADLINES_URL = 'https://newsapi.org/v2/top-headlines'
NEWSAPI_MAX_LOOKBACK_DAYS = 30  # NewsAPI historical cap on free/business plans

# Prixe.io Stock Price API configuration
PRIXE_API_KEY = os.getenv('PRIXE_API_KEY', 'pro_82da3ed00b82b730c5ce36826a555899703a7841ba96dab8fa9b2f094171447e')
PRIXE_BASE_URL = 'https://api.prixe.io'
# Prixe.io API endpoints - if /api/price doesn't work, try /api/historical or check Prixe.io documentation
PRIXE_PRICE_ENDPOINT = os.getenv('PRIXE_PRICE_ENDPOINT', '/api/price')

# Claude API configuration (for AI opinion feature)
# API key must be set via environment variable CLAUDE_API_KEY or in .env file
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')

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
