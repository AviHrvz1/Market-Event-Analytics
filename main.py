#!/usr/bin/env python3
"""
Layoff Tracker - Tracks layoff announcements from publicly traded companies
"""

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # Suppress SSL warning for verify=False
import re
import urllib.parse
import sys
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
import time as time_module
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None
from config import (
    NEWS_API_KEY, NEWS_API_EVERYTHING_URL, NEWS_API_HEADLINES_URL,
    LAYOFF_KEYWORDS, MIN_LAYOFF_PERCENTAGE, LOOKBACK_DAYS,
    PRIXE_API_KEY, PRIXE_BASE_URL, PRIXE_PRICE_ENDPOINT,
    SEC_EDGAR_BASE_URL, SEC_EDGAR_SEARCH_URL, SEC_EDGAR_COMPANY_API, SEC_USER_AGENT,
    EVENT_TYPES, MAX_ARTICLES_TO_PROCESS, DEDUPLICATE_BY_COMPANY,
    CLAUDE_API_KEY
)

NEWSAPI_MAX_LOOKBACK_DAYS = 30  # NewsAPI free/business tiers limit historical access


class LayoffTracker:
    def __init__(self):
        self.layoffs = []
        self.debug_log_file = 'events_filter_debug.log'
        
        # Fix yfinance SSL issues by using system certificates
        if YFINANCE_AVAILABLE:
            try:
                import os
                import ssl
                import certifi
                
                # Prefer system certificates (more reliable, especially in sandboxed environments)
                system_cert = '/private/etc/ssl/cert.pem'
                certifi_cert = certifi.where()
                
                if os.path.exists(system_cert) and os.access(system_cert, os.R_OK):
                    cert_path = system_cert
                elif os.path.exists(certifi_cert) and os.access(certifi_cert, os.R_OK):
                    cert_path = certifi_cert
                else:
                    cert_path = system_cert if os.path.exists(system_cert) else certifi_cert
                
                # Set environment variables for SSL certificate
                os.environ['SSL_CERT_FILE'] = cert_path
                os.environ['REQUESTS_CA_BUNDLE'] = cert_path
                os.environ['CURL_CA_BUNDLE'] = cert_path
                
                # Patch yfinance's data fetcher to use verify=False
                # yfinance uses curl_cffi, so we need to patch at the curl_cffi level
                try:
                    import yfinance.data as yf_data
                    # Patch the _get_cookie_and_crumb_basic method which makes requests
                    if hasattr(yf_data, 'YfData'):
                        original_get = yf_data.YfData.get
                        def patched_get(self, *args, **kwargs):
                            # Try to pass verify=False if the underlying library supports it
                            kwargs['verify'] = False
                            try:
                                return original_get(self, *args, **kwargs)
                            except TypeError:
                                # If verify is not supported, try without it
                                kwargs.pop('verify', None)
                                return original_get(self, *args, **kwargs)
                        yf_data.YfData.get = patched_get
                        
                        # Also patch get_raw_json
                        if hasattr(yf_data.YfData, 'get_raw_json'):
                            original_get_raw_json = yf_data.YfData.get_raw_json
                            def patched_get_raw_json(self, *args, **kwargs):
                                kwargs['verify'] = False
                                try:
                                    return original_get_raw_json(self, *args, **kwargs)
                                except TypeError:
                                    kwargs.pop('verify', None)
                                    return original_get_raw_json(self, *args, **kwargs)
                            yf_data.YfData.get_raw_json = patched_get_raw_json
                except Exception as patch_error:
                    # If patching fails, try to patch curl_cffi directly
                    try:
                        import curl_cffi.requests as curl_requests
                        # Patch curl_cffi Session to use verify=False by default
                        original_request = curl_requests.Session.request
                        def patched_request(self, *args, **kwargs):
                            kwargs['verify'] = False
                            return original_request(self, *args, **kwargs)
                        curl_requests.Session.request = patched_request
                    except:
                        pass  # If all patching fails, continue anyway
            except:
                pass  # If configuration fails, continue anyway
        self.company_ticker_cache = {}
        self.stock_price_cache = {}
        self.companies_list = None  # Will be populated dynamically
        self.company_to_ticker_map = {}  # Will be populated dynamically
        self.api_errors = []  # Track API errors for alerting
        self.ticker_to_cik_cache = {}  # Cache for ticker to CIK mapping
        self.api_call_count = 0  # Track API calls for optimization
        self.total_api_calls_estimated = 0  # Estimated total API calls needed (calculated before API calls start)
        self.batch_data_cache = {}  # Cache batch data per ticker
        self.sec_filings_cache = {}  # Cache for SEC filings by ticker
        self.price_history_cache = {}  # Cache price history per ticker to avoid recalculating
        self.source_stats = {}  # Track statistics per news source
        self.sec_companies_loaded = False  # Track if SEC companies have been loaded
        self.sorted_companies = []  # Pre-sorted list of companies (by length, longest first) for fast lookup
        self.failed_tickers = set()  # Cache tickers that returned 404s to avoid retrying
        # Hardcoded list of tickers known to not exist in Prixe.io (404 errors)
        self.invalid_tickers = {'CPSS', 'EPDU', 'MITI'}
        # Claude API configuration - use hardcoded value from config.py
        self.claude_api_key = CLAUDE_API_KEY
        self.claude_api_url = 'https://api.anthropic.com/v1/messages'
        self.ai_prediction_cache = {}  # Cache AI predictions by article URL
        
        # Fix yfinance SSL issues by setting environment variables
        if YFINANCE_AVAILABLE:
            try:
                import os
                # Set environment variables to help with SSL certificate issues
                # curl_cffi (used by yfinance) may respect these
                os.environ['CURL_CA_BUNDLE'] = ''
                os.environ['REQUESTS_CA_BUNDLE'] = ''
                # Try to disable SSL verification at the curl level
                os.environ['CURLOPT_SSL_VERIFYPEER'] = '0'
                os.environ['CURLOPT_SSL_VERIFYHOST'] = '0'
            except:
                pass  # If setting env vars fails, continue anyway
        
        # Clear stale intraday cache entries on initialization (dates >60 days old)
        self._clear_stale_intraday_cache()
        # Load SEC EDGAR company list on initialization
        self._load_sec_companies()
    
    def _write_debug_log(self, message):
        """Write debug message to log file"""
        try:
            import os
            # Use absolute path to ensure we can write
            log_path = os.path.join(os.getcwd(), self.debug_log_file)
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(message)
                f.flush()  # Ensure it's written immediately
        except Exception as e:
            # Log the error to stderr so we can see it
            import sys
            print(f"[DEBUG LOG ERROR] Failed to write to {self.debug_log_file}: {e}", file=sys.stderr)
    
    def _clear_stale_intraday_cache(self):
        """Clear intraday cache entries for dates >60 days old"""
        now = datetime.now(timezone.utc)
        keys_to_remove = []
        
        for cache_key in self.stock_price_cache.keys():
            # Check if this is an intraday cache key
            if 'prixe_intraday' in cache_key:
                # Try to extract date from cache key
                # Format: prixe_intraday_day_{ticker}_{date}_{interval}
                # or: prixe_intraday_batch_{ticker}_{start_date}_{end_date}_{interval}
                try:
                    if 'prixe_intraday_day_' in cache_key:
                        # Extract date from day cache key
                        parts = cache_key.replace('prixe_intraday_day_', '').split('_')
                        if len(parts) >= 2:
                            date_str = parts[1]  # Format: YYYY-MM-DD
                            cache_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                            days_ago = (now - cache_date).days
                            if days_ago > 60:
                                keys_to_remove.append(cache_key)
                    elif 'prixe_intraday_batch_' in cache_key:
                        # Extract end date from batch cache key
                        parts = cache_key.replace('prixe_intraday_batch_', '').split('_')
                        if len(parts) >= 3:
                            end_date_str = parts[2]  # Format: YYYY-MM-DD
                            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                            days_ago = (now - end_date).days
                            if days_ago > 60:
                                keys_to_remove.append(cache_key)
                except (ValueError, IndexError):
                    # If we can't parse the date, keep the cache entry (safer)
                    pass
        
        # Remove stale cache entries
        for key in keys_to_remove:
            del self.stock_price_cache[key]
        
        if keys_to_remove:
            print(f"[CACHE] Cleared {len(keys_to_remove)} stale intraday cache entries (>60 days old)")
    
    # Exchange to Market Hours Mapping
    EXCHANGE_MARKET_HOURS = {
        'US': {
            'open': (9, 30),  # (hour, minute) in local time
            'close': (16, 0),
            'timezone_offset': -5,  # EST base (will adjust for DST)
            'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
        },
        'HK': {
            'open': (9, 30),  # 9:30 AM HKT
            'close': (16, 0),  # 4:00 PM HKT
            'timezone_offset': 8,  # HKT (UTC+8)
            'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
        },
        'L': {
            'open': (8, 0),  # 8:00 AM GMT
            'close': (16, 30),  # 4:30 PM GMT
            'timezone_offset': 0,  # GMT (will adjust for BST)
            'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
        },
        'T': {
            'open': (9, 0),  # 9:00 AM JST
            'close': (15, 0),  # 3:00 PM JST
            'timezone_offset': 9,  # JST (UTC+9)
            'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
        },
        'PA': {
            'open': (9, 0),  # 9:00 AM CET
            'close': (17, 30),  # 5:30 PM CET
            'timezone_offset': 1,  # CET (will adjust for CEST)
            'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
        },
        'DE': {
            'open': (9, 0),  # 9:00 AM CET
            'close': (17, 30),  # 5:30 PM CET
            'timezone_offset': 1,  # CET (will adjust for CEST)
            'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
        },
    }
    
    # Ticker suffix to exchange mapping
    TICKER_EXCHANGE_MAP = {
        '.HK': 'HK',  # Hong Kong
        '.L': 'L',    # London
        '.T': 'T',    # Tokyo
        '.PA': 'PA',  # Paris
        '.DE': 'DE',  # Frankfurt
    }
    
    def _detect_exchange_from_ticker(self, ticker: str) -> str:
        """Detect the exchange from a ticker symbol. Returns 'US' by default."""
        if not ticker:
            return 'US'
        
        ticker_upper = ticker.upper()
        
        # Check for exchange suffix
        for suffix, exchange in self.TICKER_EXCHANGE_MAP.items():
            if ticker_upper.endswith(suffix):
                return exchange
        
        # Default to US exchange (NYSE/NASDAQ)
        return 'US'
    
    def _get_market_hours(self, exchange: str) -> Dict:
        """Get market hours configuration for an exchange. Returns US config as fallback."""
        return self.EXCHANGE_MARKET_HOURS.get(exchange, self.EXCHANGE_MARKET_HOURS['US'])
    
    def _get_market_open_time(self, date: datetime, ticker: str) -> Optional[datetime]:
        """Get the market open time for a specific date and ticker. Returns datetime in UTC."""
        exchange = self._detect_exchange_from_ticker(ticker)
        market_config = self._get_market_hours(exchange)
        
        # Get timezone offset (with DST adjustment)
        base_offset = market_config['timezone_offset']
        month = date.month
        
        if exchange == 'US':
            offset_hours = -4 if (month >= 3 and month <= 10) else -5
        elif exchange == 'L':
            offset_hours = 1 if (month >= 3 and month <= 10) else 0
        elif exchange in ['PA', 'DE']:
            offset_hours = 2 if (month >= 3 and month <= 10) else 1
        else:
            offset_hours = base_offset
        
        # Get the date (use the original date, not after timezone conversion)
        # This ensures we use the correct calendar date
        target_date = date.date() if hasattr(date, 'date') else date
        
        # Get market open time
        market_open_hour, market_open_minute = market_config['open']
        
        # Create datetime at market open in local time on the target date
        from datetime import time as dt_time
        market_open_local = datetime.combine(
            target_date,
            dt_time(market_open_hour, market_open_minute)
        )
        
        # Convert local time to UTC by subtracting the offset
        local_timedelta = timedelta(hours=offset_hours)
        market_open_utc = market_open_local - local_timedelta
        return market_open_utc.replace(tzinfo=timezone.utc)
    
    def _get_market_close_time(self, date: datetime, ticker: str) -> Optional[datetime]:
        """Get the market close time for a specific date and ticker. Returns datetime in UTC."""
        exchange = self._detect_exchange_from_ticker(ticker)
        market_config = self._get_market_hours(exchange)
        
        # Get timezone offset (with DST adjustment)
        base_offset = market_config['timezone_offset']
        month = date.month
        
        if exchange == 'US':
            offset_hours = -4 if (month >= 3 and month <= 10) else -5
        elif exchange == 'L':
            offset_hours = 1 if (month >= 3 and month <= 10) else 0
        elif exchange in ['PA', 'DE']:
            offset_hours = 2 if (month >= 3 and month <= 10) else 1
        else:
            offset_hours = base_offset
        
        # Get the date (use the original date, not after timezone conversion)
        # This ensures we use the correct calendar date
        target_date = date.date() if hasattr(date, 'date') else date
        
        # Get market close time
        market_close_hour, market_close_minute = market_config['close']
        
        # Create datetime at market close in local time on the target date
        from datetime import time as dt_time
        market_close_local = datetime.combine(
            target_date,
            dt_time(market_close_hour, market_close_minute)
        )
        
        # Convert local time to UTC by subtracting the offset
        local_timedelta = timedelta(hours=offset_hours)
        market_close_utc = market_close_local - local_timedelta
        return market_close_utc.replace(tzinfo=timezone.utc)
    
    def get_date_range(self) -> tuple:
        """Get date range for the last LOOKBACK_DAYS days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=LOOKBACK_DAYS)
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def matches_event_type(self, article: Dict, event_type: str) -> bool:
        """Check if article matches a specific event type"""
        if event_type not in EVENT_TYPES:
            return False
        
        event_config = EVENT_TYPES[event_type]
        
        # Special handling for event types that query by company names: if query_by_company_names is True and keywords are empty,
        # trust that Google News RSS already filtered by company names
        if event_type and (event_type.startswith('bio_companies') or event_type.startswith('real_estate')) and event_config.get('query_by_company_names', False) and len(event_config.get('keywords', [])) == 0:
            return True
        
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        full_text = f"{title} {description}"

        # Check for basic keywords
        keywords = event_config.get('keywords', [])
        if not keywords:
            return False  # No keywords defined and not a special case
        
        has_keyword = any(keyword in full_text for keyword in keywords)
        
        if not has_keyword:
            return False
        
        # CEO departure now works like other event types - just check keywords
        # No special validation needed since we removed the "no successor" requirement
        return True
    
    def search_news_api(self, event_types: List[str] = None) -> List[Dict]:
        """Search for news using NewsAPI with specified event types"""
        if not NEWS_API_KEY:
            print("Warning: NEWS_API_KEY not set. Skipping NewsAPI search.")
            return []
        
        if event_types is None:
            event_types = ['real_estate_good_news']  # Default
        
        # Collect all keywords from selected event types
        all_keywords = []
        for event_type in event_types:
            if event_type in EVENT_TYPES:
                all_keywords.extend(EVENT_TYPES[event_type]['keywords'])
        
        # Remove duplicates
        all_keywords = list(set(all_keywords))
        
        if not all_keywords:
            all_keywords = LAYOFF_KEYWORDS  # Fallback
        
        end_dt = datetime.now()
        lookback_days = min(LOOKBACK_DAYS, NEWSAPI_MAX_LOOKBACK_DAYS)
        start_dt = end_dt - timedelta(days=lookback_days)
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = end_dt.strftime('%Y-%m-%d')
        articles = []
        
        query = ' OR '.join(all_keywords)
        
        # Try everything endpoint first
        try:
            params = {
                'q': query,
                'from': start_date,
                'to': end_date,
                'sortBy': 'publishedAt',
                'language': 'en',
                'pageSize': 100,
                'apiKey': NEWS_API_KEY
            }
            
            full_url = f"{NEWS_API_EVERYTHING_URL}?q={query}&from={start_date}&to={end_date}&sortBy=publishedAt&language=en&pageSize=100&apiKey={NEWS_API_KEY}"
            print(f"[API REQUEST] NewsAPI")
            print(f"  Full URL: {full_url}")
            
            response = requests.get(NEWS_API_EVERYTHING_URL, params=params, timeout=10)
            
            # Check for rate limiting and other errors
            if response.status_code == 429:
                error_msg = "NewsAPI rate limit exceeded. Please wait before making more requests."
                self.api_errors.append({
                    'service': 'NewsAPI',
                    'type': 'rate_limit',
                    'message': error_msg,
                    'status_code': 429
                })
            elif response.status_code == 401:
                error_msg = "NewsAPI authentication failed. Invalid API key."
                self.api_errors.append({
                    'service': 'NewsAPI',
                    'type': 'authentication',
                    'message': error_msg,
                    'status_code': 401
                })
            elif response.status_code == 403:
                error_msg = "NewsAPI access forbidden. Check API key permissions."
                self.api_errors.append({
                    'service': 'NewsAPI',
                    'type': 'forbidden',
                    'message': error_msg,
                    'status_code': 403
                })
            elif response.status_code == 503:
                error_msg = "NewsAPI service unavailable. The service may be down."
                self.api_errors.append({
                    'service': 'NewsAPI',
                    'type': 'service_unavailable',
                    'message': error_msg,
                    'status_code': 503
                })
            
            if response.status_code == 200:
                data = response.json()
                if 'articles' in data:
                    articles = data['articles']
                    print(f"[API RESPONSE] NewsAPI: {len(articles)} articles found")
                    return articles
            
        except requests.exceptions.HTTPError as e:
            if e.response:
                status_code = e.response.status_code
                
                if status_code == 429:
                    error_msg = "NewsAPI rate limit exceeded. Please wait before making more requests."
                    self.api_errors.append({
                        'service': 'NewsAPI',
                        'type': 'rate_limit',
                        'message': error_msg,
                        'status_code': 429
                    })
                elif status_code == 426:
                    print("Everything endpoint requires upgrade. Trying headlines endpoint...")
                else:
                    error_msg = f"NewsAPI HTTP error: {status_code}"
                    self.api_errors.append({
                        'service': 'NewsAPI',
                        'type': 'http_error',
                        'message': error_msg,
                        'status_code': status_code
                    })
            else:
                print(f"Error fetching from NewsAPI everything endpoint: {e}")
        except requests.exceptions.Timeout:
            error_msg = "NewsAPI request timed out. The service may be slow or unavailable."
            self.api_errors.append({
                'service': 'NewsAPI',
                'type': 'timeout',
                'message': error_msg
            })
        except requests.exceptions.ConnectionError:
            error_msg = "NewsAPI connection error. Check your internet connection."
            self.api_errors.append({
                'service': 'NewsAPI',
                'type': 'connection_error',
                'message': error_msg
            })
        except Exception as e:
            error_msg = f"NewsAPI unexpected error: {str(e)}"
            self.api_errors.append({
                'service': 'NewsAPI',
                'type': 'unknown_error',
                'message': error_msg
            })
            import traceback
        
        # Fallback to headlines endpoint (free tier compatible)
        try:
            # Search in business category
            params = {
                'category': 'business',
                'country': 'us',
                'pageSize': 100,
                'apiKey': NEWS_API_KEY
            }
            
            full_url = f"{NEWS_API_HEADLINES_URL}?category=business&country=us&pageSize=100&apiKey={NEWS_API_KEY}"
            print(f"[API REQUEST] NewsAPI Headlines")
            print(f"  Full URL: {full_url}")
            
            response = requests.get(NEWS_API_HEADLINES_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'articles' in data:
                    articles = data['articles']
                    print(f"[API RESPONSE] NewsAPI Headlines: {len(articles)} articles found")
            
            # Check for rate limiting and other errors
            if response.status_code == 429:
                error_msg = "NewsAPI rate limit exceeded. Please wait before making more requests."
                self.api_errors.append({
                    'service': 'NewsAPI (Headlines)',
                    'type': 'rate_limit',
                    'message': error_msg,
                    'status_code': 429
                })
            elif response.status_code in [401, 403, 503]:
                error_msg = f"NewsAPI error: Status {response.status_code}"
                self.api_errors.append({
                    'service': 'NewsAPI (Headlines)',
                    'type': 'http_error',
                    'message': error_msg,
                    'status_code': response.status_code
                })
            
            if response.status_code == 200:
                data = response.json()
                if 'articles' in data:
                    all_articles = data['articles']
                    # Filter articles that contain layoff keywords
                    filtered_articles = []
                    for article in all_articles:
                        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
                        if any(keyword in text for keyword in LAYOFF_KEYWORDS):
                            filtered_articles.append(article)
                    
                    articles = filtered_articles
        except requests.exceptions.Timeout:
            error_msg = "NewsAPI headlines request timed out."
            self.api_errors.append({
                'service': 'NewsAPI (Headlines)',
                'type': 'timeout',
                'message': error_msg
            })
        except requests.exceptions.ConnectionError:
            error_msg = "NewsAPI headlines connection error."
            self.api_errors.append({
                'service': 'NewsAPI (Headlines)',
                'type': 'connection_error',
                'message': error_msg
            })
        except Exception as e:
            error_msg = f"NewsAPI headlines error: {str(e)}"
            self.api_errors.append({
                'service': 'NewsAPI (Headlines)',
                'type': 'unknown_error',
                'message': error_msg
            })
            import traceback
        
        return articles
    
    def fetch_article_metadata(self, url: str) -> Optional[str]:
        """Fetch only HTML head/metadata for fast date extraction
        Returns: publication_date or None
        """
        if not url:
            return None
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Range': 'bytes=0-50000'  # Only fetch first 50KB (usually contains head/metadata)
            }
            timeout = 0.3  # Slightly longer for metadata fetch
            
            # Handle Google News redirect URLs
            if 'news.google.com' in url:
                response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            else:
                response = requests.get(url, headers=headers, timeout=timeout)
            
            if response.status_code in [200, 206]:  # 206 = Partial Content
                soup = BeautifulSoup(response.content, 'html.parser')
                return self._extract_publication_date_from_html(soup)
        except:
            pass
        return None
    
    def fetch_article_content(self, url: str) -> tuple[str, Optional[str]]:
        """Fetch full article content from URL with shorter timeout
        Returns: (content_text, publication_date)
        """
        if not url:
            return '', None
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            # Use shorter timeout to avoid hanging
            timeout = 0.2  # Reduced to 0.2 seconds for faster processing
            
            print(f"  URL: {url[:80]}...")
            print(f"  Timeout: {timeout}s")
            
            # Handle Google News redirect URLs
            if 'news.google.com' in url:
                # Follow redirects but with timeout
                response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            else:
                response = requests.get(url, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract publication date from HTML before removing meta tags
                publication_date = self._extract_publication_date_from_html(soup)
                
                # Remove script and style elements (but keep meta for date extraction)
                for script in soup(["script", "style", "link"]):
                    script.decompose()
                
                # Try multiple strategies to find content
                content_text = ''
                
                # Strategy 1: Look for article tags
                article = soup.find('article')
                if article:
                    content_text = article.get_text(separator=' ', strip=True)
                
                # Strategy 2: Look for main content divs
                if not content_text or len(content_text) < 100:
                    for selector in ['main', '[role="main"]', '.article-body', '.content', '.post-content', '.entry-content']:
                        main = soup.select_one(selector)
                        if main:
                            content_text = main.get_text(separator=' ', strip=True)
                            if len(content_text) > 100:
                                break
                
                # Strategy 3: Get all paragraph text
                if not content_text or len(content_text) < 100:
                    paragraphs = soup.find_all('p')
                    if paragraphs:
                        content_text = ' '.join([p.get_text(strip=True) for p in paragraphs[:20]])
                
                # Clean and return
                if content_text:
                    # Remove extra whitespace
                    content_text = ' '.join(content_text.split())
                    return content_text[:3000], publication_date  # Limit to first 3000 chars
                return '', publication_date
        except requests.exceptions.Timeout:
            return '', None
        except Exception:
            return '', None
        return '', None
    
    def _extract_publication_date_from_html(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date from HTML using common meta tags and patterns"""
        try:
            # Strategy 1: Look for Open Graph meta tags
            og_published = soup.find('meta', property='article:published_time')
            if og_published and og_published.get('content'):
                return og_published.get('content')
            
            # Strategy 2: Look for schema.org datePublished
            date_published = soup.find('meta', {'itemprop': 'datePublished'})
            if date_published and date_published.get('content'):
                return date_published.get('content')
            
            # Strategy 3: Look for time tag with datetime attribute
            time_tag = soup.find('time', {'datetime': True})
            if time_tag and time_tag.get('datetime'):
                return time_tag.get('datetime')
            
            # Strategy 4: Look for meta name="publishdate" or "pubdate"
            for meta_name in ['publishdate', 'pubdate', 'publication-date', 'date']:
                meta = soup.find('meta', {'name': meta_name})
                if meta and meta.get('content'):
                    return meta.get('content')
            
            # Strategy 5: Look for JSON-LD structured data
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        date_published = data.get('datePublished') or data.get('datePublished')
                        if date_published:
                            return date_published
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                date_published = item.get('datePublished') or item.get('datePublished')
                                if date_published:
                                    return date_published
                except:
                    continue
            
            # Strategy 6: Look for common class names with dates
            for selector in ['.published-date', '.article-date', '.post-date', '.date-published', '[class*="date"]']:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    if date_text:
                        # Try to parse it
                        try:
                            from dateutil import parser
                            parser.parse(date_text)  # Validate it's a date
                            return date_text
                        except:
                            pass
        except Exception:
            pass
        
        return None
    
    def extract_layoff_info(self, article: Dict, fetch_content: bool = False, event_types: List[str] = None, pre_fetched_ai_result: Optional[Dict] = None, fetch_metadata: bool = False) -> Optional[Dict]:
        """Extract information from an article based on event types"""
        title = article.get('title', '')
        description = article.get('description', '')
        content = article.get('content', '')
        published_at = article.get('publishedAt', '')
        url = article.get('url', '')
        
        # Combine title and description first
        full_text = f"{title} {description}".lower()
        
        if event_types is None:
            event_types = ['real_estate_good_news']  # Default
        
        # EFFICIENCY: Trust Google News RSS pre-filtered articles
        # If Google News RSS already matched this article with a query, trust it
        # This avoids double-filtering that can miss valid articles (e.g., when title doesn't have keyword but URL/body does)
        matches_any = False
        matched_event_type = None
        
        if article.get('event_type') in event_types and article.get('source', {}).get('name') == 'Google News':
            # Google News RSS already filtered this article with the query - trust it
            matched_event_type = article.get('event_type')
            matches_any = True
        else:
            # Only do keyword matching for non-Google News sources or articles without event_type tag
            for event_type in event_types:
                if self.matches_event_type(article, event_type):
                    matches_any = True
                    matched_event_type = event_type
                    break
        
        if not matches_any:
            # Log why article was filtered
            print(f"[FILTER] Article filtered: No event type match - '{article.get('title', '')[:60]}...'")
            return None
        
        # REMOVED: Date filtering - show all articles regardless of age
        # Google News RSS already filters by date, and we want to show all matched articles
        # Log date info for debugging but don't filter
        days_ago = None
        if published_at:
            try:
                from dateutil import parser
                article_date = parser.parse(published_at)
                if article_date.tzinfo is None:
                    article_date = article_date.replace(tzinfo=timezone.utc)
                else:
                    article_date = article_date.astimezone(timezone.utc)
                
                now = datetime.now(timezone.utc)
                days_ago = (now - article_date).days
                
                # Log but don't filter - show all articles
                if days_ago > (LOOKBACK_DAYS + 5):
                    print(f"[FILTER] Article is {days_ago} days old (>{LOOKBACK_DAYS + 5}), but allowing through: '{article.get('title', '')[:60]}...'")
            except Exception as e:
                # If date parsing fails, allow article through (don't filter on parse errors)
                print(f"[FILTER] Date parsing failed for article, allowing through: '{article.get('title', '')[:60]}...' (error: {str(e)[:50]})")
                pass
        
        # OPTIMIZATION: Check if article was pre-tagged with company from search query
        pre_tagged_company = article.get('matched_company')
        if pre_tagged_company:
            # Article was pre-tagged with company from search query - skip Claude extraction AND ticker lookup
            company_name = pre_tagged_company
            
            # OPTIMIZATION: Use hardcoded ticker mapping if available (much faster than SEC EDGAR lookup)
            ticker = None
            if matched_event_type and matched_event_type.startswith('bio_companies'):
                event_config = EVENT_TYPES.get(matched_event_type, {})
                category = event_config.get('category', 'all')
                ticker_map = self._get_bio_pharma_tickers(category=category)
                company_upper = company_name.upper().strip()
                ticker = ticker_map.get(company_upper)
            
            # Fallback to SEC EDGAR lookup if not in hardcoded map
            if not ticker:
                ticker = self.get_stock_ticker(company_name)
            
            # Still get AI prediction for score/direction, but skip company extraction
            if pre_fetched_ai_result is not None:
                ai_result = pre_fetched_ai_result
            else:
                ai_result = self.get_ai_prediction_score(
                    title=title,
                    description=description,
                    url=url
                )
            if ai_result and ai_result.get('company_name'):
                # Use Claude's prediction but keep our pre-tagged company name
                ai_prediction = {
                    'score': ai_result.get('score'),
                    'direction': ai_result.get('direction')
                }
            else:
                # No AI prediction available, but we have company name
                ai_prediction = None
        else:
            # No pre-tagging - use normal extraction flow
            # Use pre-fetched AI result if available (from batch call), otherwise call Claude API
            if pre_fetched_ai_result is not None:
                ai_result = pre_fetched_ai_result
            else:
                # Call Claude first to extract company name, ticker, and get AI prediction
                ai_result = self.get_ai_prediction_score(
                    title=title,
                    description=description,
                    url=url
                )
            
            # If Claude succeeds, use its extracted company name and ticker directly
            if ai_result and ai_result.get('company_name'):
                company_name = ai_result.get('company_name')
                ticker = ai_result.get('ticker')  # Can be None for private companies
                # Use Claude's ticker directly - let Prixe.io validate if it's valid
                ai_prediction = {
                    'score': ai_result.get('score'),
                    'direction': ai_result.get('direction')
                }
            else:
                # Fallback to current extraction method if Claude fails
                # OPTIMIZATION: For event types that query by company names, use the search query companies as candidates
                candidate_companies = None
                if matched_event_type and matched_event_type.startswith('bio_companies'):
                    # Get the category from event config
                    event_config = EVENT_TYPES.get(matched_event_type, {})
                    category = event_config.get('category', 'all')
                    # Get the list of bio companies we searched for (with appropriate category)
                    candidate_companies = self._get_bio_pharma_companies(category=category)
                elif matched_event_type and matched_event_type.startswith('real_estate'):
                    # Get the list of real estate companies we searched for
                    candidate_companies = self._get_real_estate_companies()
                elif matched_event_type in ['bio_positive_news', 'bio_negative_news']:
                    # For bio positive/negative news, use all bio companies as candidates
                    # This helps extraction when articles mention companies but not in standard format
                    candidate_companies = self._get_bio_pharma_companies('all')
                    # Also include small-cap and mid-cap for broader coverage
                    small_cap = self._get_bio_pharma_companies('small_cap')
                    mid_cap = self._get_bio_pharma_companies('mid_cap')
                    if candidate_companies:
                        candidate_companies = list(set(candidate_companies + small_cap + mid_cap))
                    else:
                        candidate_companies = list(set(small_cap + mid_cap))
                
                # Try extraction with candidates first
                company_name = self.extract_company_name(title, description, candidate_companies=candidate_companies)
                
                # If extraction failed and we have candidates, try with full content if available
                if not company_name and candidate_companies and content:
                    company_name = self.extract_company_name(title, f"{description} {content}", candidate_companies=candidate_companies)
                
                # If still no company name, try without candidates (broader search)
                if not company_name:
                    company_name = self.extract_company_name(title, description, candidate_companies=None)
                
                # If still no company name, try with content
                if not company_name and content:
                    company_name = self.extract_company_name(title, f"{description} {content}", candidate_companies=None)
                
                # If extraction still fails, company_name will be None (UI will show "Didn't find")
                # This ensures we don't lose valuable news articles
                
                # Only try to get ticker if we have a real company name (not None)
                ticker = None
                if company_name:
                    ticker = self.get_stock_ticker(company_name)
                
                # If fallback method doesn't find ticker, still try to get AI prediction
                ai_prediction = None
                if company_name and ticker:
                    # Try to get AI prediction with fallback company/ticker
                    ai_prediction_result = self.get_ai_prediction_score(
                        title=title,
                        description=description,
                        url=url
                    )
                    if ai_prediction_result:
                        ai_prediction = {
                            'score': ai_prediction_result.get('score'),
                            'direction': ai_prediction_result.get('direction')
                        }
        
        # Allow articles without company names/tickers - show them with "Didn't find" in UI
        # This ensures we don't lose valuable news articles just because extraction failed
        # Keep company_name as None if extraction failed (UI will display "Didn't find")
        # Don't set to "Unknown Company" - let UI handle the display
        
        # Allow articles without tickers - they'll show "Didn't find" for ticker and stock prices
        # This includes private companies and cases where ticker lookup failed
        if not ticker or ticker == 'N/A':
            ticker = None  # Set to None (will be displayed as "Didn't find" in UI)
        
        # Don't filter out articles for invalid/failed tickers - show them anyway
        # Stock price fetching will handle None tickers gracefully
        # Only check ticker availability if we have a ticker (for optimization)
        if ticker and not self._is_ticker_available(ticker):
            # Ticker is invalid or not available - set to None but still show article
            ticker = None
        
        layoff_pct = self.extract_layoff_percentage(full_text)
        layoff_employees = self.extract_layoff_employees(full_text)
        
        # Extract additional insights
        layoff_reason = self.extract_layoff_reason(full_text)
        expected_savings = self.extract_expected_savings(full_text)
        financial_context = self.extract_financial_context(full_text)
        affected_departments = self.extract_affected_departments(full_text)
        guidance_change = self.extract_guidance_change(full_text)
        
        # OPTIMIZATION: Only fetch article metadata if explicitly requested (skip during batch processing)
        # Metadata fetch makes HTTP request to article URL (~0.5-2s per article) - too slow for batch processing
        # RSS feed date is usually accurate enough for our purposes
        extracted_publication_date = None
        if fetch_metadata and url:
            try:
                extracted_publication_date = self.fetch_article_metadata(url)
            except:
                pass  # Silently skip metadata fetch errors
        
        # Use extracted publication date if available (more accurate than RSS feed date)
        if extracted_publication_date:
            try:
                from dateutil import parser
                parsed_date = parser.parse(extracted_publication_date)
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                else:
                    parsed_date = parsed_date.astimezone(timezone.utc)
                # Update published_at with the more accurate date
                published_at = parsed_date.isoformat()
            except:
                pass  # Fall back to RSS feed date if parsing fails
        
        # Only fetch full content if we don't have percentage or employees AND fetch_content is True
        # This significantly speeds up processing
        fetched_content = None
        if fetch_content and (not layoff_pct or not layoff_employees) and url:
            try:
                fetched_content, _ = self.fetch_article_content(url)  # Date already extracted above
                if fetched_content:
                    full_text_with_content = f"{full_text} {fetched_content}".lower()
                    # Re-extract with full content
                    if not layoff_pct:
                        layoff_pct = self.extract_layoff_percentage(full_text_with_content)
                    if not layoff_employees:
                        layoff_employees = self.extract_layoff_employees(full_text_with_content)
            except Exception as e:
                pass  # Silently skip content fetch errors
        
        # Re-extract insights with full content if available
        if fetched_content:
            full_text_with_content = f"{full_text} {fetched_content}".lower()
            if not layoff_reason:
                layoff_reason = self.extract_layoff_reason(full_text_with_content)
            if not expected_savings:
                expected_savings = self.extract_expected_savings(full_text_with_content)
            if not financial_context:
                financial_context = self.extract_financial_context(full_text_with_content)
            if not affected_departments:
                affected_departments = self.extract_affected_departments(full_text_with_content)
            if not guidance_change:
                guidance_change = self.extract_guidance_change(full_text_with_content)
        
        # AI prediction is already set above (either from Claude's initial call or from fallback)
        
        # Parse date and time
        dt = None
        try:
            # Try ISO format first
            dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            # Ensure timezone is UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%H:%M:%S')
        except:
            try:
                # Try RSS format (e.g., "Mon, 23 Nov 2025 18:00:00 GMT")
                from dateutil import parser
                dt = parser.parse(published_at)
                # Ensure timezone is UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                date_str = dt.strftime('%Y-%m-%d')
                time_str = dt.strftime('%H:%M:%S')
            except:
                # Fallback to string extraction
                date_str = published_at[:10] if len(published_at) >= 10 else ''
                time_str = published_at[11:19] if len(published_at) >= 19 else ''
        
        # Extract AI prediction values
        ai_prediction_score = ai_prediction.get('score') if ai_prediction else None
        ai_prediction_direction = ai_prediction.get('direction') if ai_prediction else None
        
        # Log extraction result for debugging
        extraction_status = "SUCCESS"
        if not company_name:
            extraction_status = "NO_COMPANY"
        elif not ticker:
            extraction_status = "NO_TICKER"
        
        if days_ago is not None:
            print(f"[EXTRACT] {extraction_status}: '{title[:60]}...' - Company: {company_name or 'None'}, Ticker: {ticker or 'None'}, Days ago: {days_ago}")
        else:
            print(f"[EXTRACT] {extraction_status}: '{title[:60]}...' - Company: {company_name or 'None'}, Ticker: {ticker or 'None'}")
        
        return {
            'company_name': company_name,  # Can be None if extraction failed (UI will show "Didn't find")
            'stock_ticker': ticker,  # Can be None for private companies or failed lookup (UI will show "Didn't find")
            'event_type': matched_event_type,
            'layoff_percentage': layoff_pct,
            'layoff_employees': layoff_employees,
            'date': date_str,
            'time': time_str,
            'datetime': dt,
            'url': url,
            'title': title,
            # New insight fields
            'layoff_reason': layoff_reason,
            'expected_savings': expected_savings,
            'financial_context': financial_context,
            'affected_departments': affected_departments,
            'guidance_change': guidance_change,
            'ai_prediction_score': ai_prediction_score,
            'ai_prediction_direction': ai_prediction_direction,
        }
    
    def extract_company_name(self, title: str, description: str, candidate_companies: Optional[List[str]] = None) -> Optional[str]:
        """Extract company name from title/description using SEC EDGAR dynamic lookup
        
        Args:
            title: Article title
            description: Article description
            candidate_companies: Optional list of candidate company names to try first (much faster than searching all SEC EDGAR)
        """
        text = f"{title} {description}"
        text_lower = text.lower()
        text_upper = text.upper()
        
        # OPTIMIZATION: If candidate companies provided (e.g., from search query), try them first
        # This is MUCH faster than searching through all 10,499 SEC EDGAR companies
        if candidate_companies:
            # Normalize candidate companies to uppercase for matching
            candidate_upper = [c.upper().strip() for c in candidate_companies if c]
            
            # Try exact matches first (case-insensitive)
            for candidate in candidate_upper:
                # Use word boundary to avoid partial matches
                pattern = r'\b' + re.escape(candidate) + r'\b'
                if re.search(pattern, text_upper):
                    # Found a match! Verify it has a ticker in SEC database
                    ticker = self._find_ticker_by_company_name(candidate)
                    if ticker:
                        return candidate.title()  # Return with proper case
            
            # Try fuzzy matching (company name might have variations like "Inc", "Corp", etc.)
            for candidate in candidate_upper:
                # Remove common suffixes for matching
                candidate_base = candidate.replace(' INC', '').replace(' CORP', '').replace(' CORPORATION', '').replace(' LLC', '').replace(' LTD', '').strip()
                if candidate_base and len(candidate_base) > 3:
                    pattern = r'\b' + re.escape(candidate_base) + r'\b'
                    if re.search(pattern, text_upper):
                        # Found a match! Verify it has a ticker
                        ticker = self._find_ticker_by_company_name(candidate)
                        if ticker:
                            return candidate.title()
        
        # Ensure SEC companies are loaded (only if we need to fall back)
        if not self.sec_companies_loaded:
            self._load_sec_companies()
        
        # Strategy 1: Try pattern matching first (faster for common cases)
        # Look for company names before action verbs (including recall verbs)
        action_verbs = [
            'announces', 'to cut', 'plans', 'will cut', 'cuts', 'layoffs',
            'recalls', 'recalling', 'recalled', 'recall',  # Added recall verbs
            'issues', 'warns', 'discloses', 'reports', 'says', 'states'
        ]
        
        # Pattern: "Company Name" + action verb
        pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:' + '|'.join(action_verbs) + r')'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            potential_company = match.group(1).strip()
            # Check if this company exists in SEC database
            ticker = self._find_ticker_by_company_name(potential_company)
            if ticker:
                return potential_company
        
        # Pattern: Company with suffix (Inc, Corp, etc.)
        suffix_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc|Corp|Corporation|LLC|Ltd|Company|Co)'
        match = re.search(suffix_pattern, text, re.IGNORECASE)
        if match:
            potential_company = match.group(1).strip()
            ticker = self._find_ticker_by_company_name(potential_company)
            if ticker:
                return potential_company
        
        # Strategy 2: Search through SEC EDGAR company names (prioritize longer matches)
        # This is slower but more comprehensive
        text_upper = text.upper()
        
        # Blacklist of common words that also happen to be company names (to prevent false positives)
        blacklisted_companies = {
            'THE', 'AND', 'FOR', 'INC', 'CORP', 'COMPANY', 'NEWS', 'MARKET', 'POWER', 'MACHINES',
            'BICYCLE', 'BUSINESS', 'CALIFORNIA', 'CHICAGO', 'COLUMBUS', 'CONSUMER', 'FEDERAL',
            'FORMULA', 'GAMBLE', 'INDEPENDENT', 'INTERNATIONAL', 'PACIFIC', 'PRODUCT', 'PRODUCTS',
            'RESOURCES', 'SAFETY', 'STANLEY', 'TARGET', 'TESCO', 'VORNADO', 'WASHINGTON', 'WILLIAMS',
            'CARE', 'GATES', 'GENERAL', 'MOTORS', 'HILTON', 'NAUTILUS', 'BLENDJET', 'SHARKNINJA',
            'MIDEA', 'JUST', 'BATTERY', 'RECALL', 'RECALLS', 'RECALLING', 'RECALLED', 'EMPLOYERS'
        }
        
        # Use pre-sorted list (sorted once during load, not on every call)
        # This avoids sorting 15,444+ items on every extract_company_name() call
        sorted_companies = self.sorted_companies if self.sorted_companies else sorted(self.company_to_ticker_map.items(), key=lambda x: len(x[0]), reverse=True)
        
        # Try exact matches first (case-insensitive), starting with longest names
        for company_name, ticker in sorted_companies:
            # Use word boundary to avoid partial matches
            pattern = r'\b' + re.escape(company_name) + r'\b'
            if re.search(pattern, text_upper):
                # Exclude "GOOGLE NEWS" as a company name
                if company_name == 'GOOGLE' and 'GOOGLE NEWS' in text_upper:
                    continue
                
                # Skip blacklisted companies (common words that also happen to be company names)
                if company_name in blacklisted_companies:
                    # For blacklisted single-word companies, require stronger context signals
                    if len(company_name.split()) == 1:
                        # Check if it appears before an action verb (stronger signal it's actually the company)
                        action_context = r'\b' + re.escape(company_name) + r'\s+(?:' + '|'.join(action_verbs) + r')'
                        if not re.search(action_context, text_lower, re.IGNORECASE):
                            # Also check for company indicators (Inc, Corp, etc.)
                            company_indicator = r'\b' + re.escape(company_name) + r'\s+(?:Inc|Corp|Corporation|LLC|Ltd|Company|Co)'
                            if not re.search(company_indicator, text_upper):
                                continue  # Skip this match - not strong enough context
                    else:
                        # For multi-word blacklisted companies, skip entirely (very unlikely to be correct)
                        continue
                
                # Return the original case version if possible
                return company_name.title()
        
        # Strategy 3: Look for multi-word company names (2-4 words) - prioritize these
        # Pattern: "Word1 Word2" or "Word1 Word2 Word3" that might be a company
        multi_word_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
        matches = re.findall(multi_word_pattern, text)
        # Sort matches by length (longest first)
        matches = sorted(matches, key=len, reverse=True)
        for match in matches:
            if len(match.split()) >= 2:  # At least 2 words
                ticker = self._find_ticker_by_company_name(match)
                if ticker:
                    return match
        
        # Strategy 4: Try single-word company names (only if no multi-word match found)
        # Look for capitalized words that might be company names
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        # Filter out common words that are unlikely to be company names
        common_words = {
            'THE', 'AND', 'FOR', 'INC', 'CORP', 'COMPANY', 'NEWS', 'MARKET', 'POWER', 'MACHINES',
            'BICYCLE', 'BUSINESS', 'CALIFORNIA', 'CHICAGO', 'COLUMBUS', 'CONSUMER', 'FEDERAL',
            'FORMULA', 'GAMBLE', 'INDEPENDENT', 'INTERNATIONAL', 'PACIFIC', 'PRODUCT', 'PRODUCTS',
            'RESOURCES', 'SAFETY', 'STANLEY', 'TARGET', 'TESCO', 'VORNADO', 'WASHINGTON', 'WILLIAMS',
            'CARE', 'GATES', 'GENERAL', 'MOTORS', 'HILTON', 'NAUTILUS', 'BLENDJET', 'SHARKNINJA',
            'MIDEA', 'JUST', 'BATTERY', 'RECALL', 'RECALLS', 'RECALLING', 'RECALLED'
        }
        for word in words:
            if len(word) > 3 and word.upper() not in common_words:  # Skip short words and common words
                # Check if word matches a company name in SEC database
                ticker = self._find_ticker_by_company_name(word)
                if ticker:
                    # Only return if it's a strong match (exact or very close)
                    company_upper = word.upper()
                    if company_upper in self.company_to_ticker_map:
                        # Additional check: make sure it's not a common word that happens to be a company name
                        # Only return if it appears before an action verb or in a company-like context
                        word_pattern = r'\b' + re.escape(word) + r'\b'
                        # Check if word appears before action verbs (stronger signal it's a company)
                        action_context = r'\b' + re.escape(word) + r'\s+(?:' + '|'.join(action_verbs) + r')'
                        if re.search(action_context, text_lower, re.IGNORECASE):
                            return word
                        # Or if it's a well-known company (check if it's in our fallback map)
                        well_known_companies = {'AMAZON', 'MICROSOFT', 'GOOGLE', 'APPLE', 'META', 'TESLA', 
                                                'NETFLIX', 'WALMART', 'TARGET', 'COSTCO', 'BOEING', 'AIRBUS'}
                        if company_upper in well_known_companies:
                            return word
        
        return None
    
    def _find_ticker_by_company_name(self, company_name: str) -> Optional[str]:
        """Find ticker for a company name using SEC EDGAR map (with fuzzy matching)"""
        if not company_name:
            return None
        
        company_upper = company_name.upper().strip()
        
        # Try exact match first
        if company_upper in self.company_to_ticker_map:
            return self.company_to_ticker_map[company_upper]
        
        # Try with common suffixes removed
        suffixes = [' INC', ' CORP', ' CORPORATION', ' CO', ' COMPANY', ' LLC', ' LTD', ' LP', ' GROUP', ' HOLDINGS', ' HOLDING']
        for suffix in suffixes:
            if company_upper.endswith(suffix):
                short_name = company_upper[:-len(suffix)].strip()
                if short_name in self.company_to_ticker_map:
                    return self.company_to_ticker_map[short_name]
        
        # Try partial match (company name contains or is contained in SEC name)
        # But only if the match is substantial (at least 4 characters and 50% of shorter name)
        best_match = None
        best_match_length = 0
        
        for sec_name, ticker in self.company_to_ticker_map.items():
            # Check if company name is part of SEC name or vice versa
            if company_upper in sec_name:
                # Company name is contained in SEC name - prefer this
                if len(company_upper) >= 4 and len(company_upper) > best_match_length:
                    best_match = ticker
                    best_match_length = len(company_upper)
            elif sec_name in company_upper:
                # SEC name is contained in company name - only if substantial match
                if len(sec_name) >= 4 and len(sec_name) >= len(company_upper) * 0.5:
                    if len(sec_name) > best_match_length:
                        best_match = ticker
                        best_match_length = len(sec_name)
        
        return best_match
    
    def get_stock_ticker(self, company_name: str) -> Optional[str]:
        """Get stock ticker for a company using SEC EDGAR dynamic lookup"""
        if company_name in self.company_ticker_cache:
            return self.company_ticker_cache[company_name]
        
        # Ensure SEC companies are loaded
        if not self.sec_companies_loaded:
            self._load_sec_companies()
        
        # Try to find ticker using SEC EDGAR map
        ticker = self._find_ticker_by_company_name(company_name)
        
        # Fallback: Handle special cases (companies not in SEC or foreign companies)
        if not ticker:
            fallback_map = {
                'Airbus': 'EADSY',  # Airbus Group (traded as EADSY on US exchanges, may not be in SEC)
                'Nestle': 'NSRGY',  # Foreign company
                'Lufthansa Group': 'DLAKY',  # Foreign company
            }
            ticker = fallback_map.get(company_name)
        
        # Cache the result
        if ticker:
            self.company_ticker_cache[company_name] = ticker
        
        return ticker
    
    def extract_layoff_percentage(self, text: str) -> Optional[float]:
        """Extract layoff percentage from text"""
        # Normalize text - replace common variations
        text = text.replace('%', ' percent ')
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        # Patterns to match percentages - more comprehensive
        patterns = [
            # Direct percentage patterns
            r'(\d+(?:\.\d+)?)\s*(?:percent|%)\s*(?:of|workforce|employees|staff|jobs|workers|team)',
            r'(\d+(?:\.\d+)?)\s*(?:percent|%)\s*(?:cut|reduction|layoff|downsizing)',
            r'(?:cut|reduc|layoff|downsiz).{0,50}?\s*(\d+(?:\.\d+)?)\s*(?:percent|%)',
            r'(\d+(?:\.\d+)?)\s*(?:percent|%)\s*(?:workforce|staff|employees|jobs)',
            # Context-based patterns
            r'(\d+(?:\.\d+)?)\s*(?:percent|%)[^.]{0,80}(?:layoff|cut|reduction|downsizing|job)',
            r'(?:layoff|cut|reduction|downsizing|job.{0,10}cut)[^.]{0,80}(\d+(?:\.\d+)?)\s*(?:percent|%)',
            # Percentage in quotes or parentheses
            r'[("](\d+(?:\.\d+)?)\s*(?:percent|%)[^)]{0,50}(?:layoff|cut|reduction)',
            r'(?:layoff|cut|reduction)[^)]{0,50}[("](\d+(?:\.\d+)?)\s*(?:percent|%)',
        ]
        
        all_matches = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    pct = float(match)
                    if 0.1 < pct <= 100:  # Reasonable percentage range
                        all_matches.append(pct)
                except ValueError:
                    continue
        
        # Return the highest percentage found (most likely to be accurate)
        if all_matches:
            return max(all_matches)
        
        return None
    
    def extract_layoff_employees(self, text: str) -> Optional[int]:
        """Extract number of employees laid off from text"""
        # Normalize text
        text = re.sub(r'\s+', ' ', text)
        
        # Patterns to match employee counts - more comprehensive
        # IMPORTANT: Check K/M notation FIRST before regular numbers
        patterns = [
            # K/M notation (e.g., "14K employees", "1.5M workers") - CHECK FIRST
            r'(\d+(?:\.\d+)?)\s*(?:k|thousand|m|million)\s*(?:employees|workers|staff|jobs|people|positions)\s*(?:laid off|cut|eliminated)?',
            r'cut(?:ting|s)?\s*(?:about|around|approximately|up to|nearly|over|more than)?\s*(\d+(?:\.\d+)?)\s*(?:k|thousand|m|million)\s*(?:employees|workers|staff|jobs|people|positions)?',
            r'(?:lay|laid)\s+off\s+(?:about|around|approximately|up to|nearly|over|more than)?\s*(\d+(?:\.\d+)?)\s*(?:k|thousand|m|million)\s*(?:employees|workers|staff|jobs|people|positions)?',
            # Direct patterns with numbers before keywords - handle "lay off" as phrase (check simple pattern first)
            r'(?:to\s+)?lay\s+off\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:employees|workers|staff|jobs|people|positions)',
            r'(?:to\s+)?(?:lay|laid)\s+off\s+(?:about|around|approximately|up to|nearly|over|more than)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:employees|workers|staff|jobs|people|positions)',
            r'lay(?:ing|s)?\s*(?:off|of)?\s*(?:about|around|approximately|up to|nearly|over|more than)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:employees|workers|staff|jobs|people|positions)',
            r'cut(?:ting|s)?\s*(?:about|around|approximately|up to|nearly|over|more than)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:employees|workers|staff|jobs|people|positions)',
            r'reduc(?:ing|e|tion|s)?\s*(?:of\s*)?(?:about|around|approximately|up to|nearly|over|more than)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:employees|workers|staff|jobs|people|positions)',
            r'eliminat(?:ing|e|ion)?\s*(?:about|around|approximately|up to|nearly|over|more than)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:employees|workers|staff|jobs|people|positions)',
            # Patterns with numbers after keywords
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:employees|workers|staff|jobs|people|positions)\s*(?:will be|to be|are being|were|are)?\s*(?:laid off|cut|let go|terminated|eliminated|removed)',
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:job|position)s?\s*(?:will be|to be|are being|were|are)?\s*(?:cut|eliminated|removed|lost)',
            # Patterns with "X workers" or "X staff"
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:workers|staff)\s*(?:laid off|cut|let go)',
            # Patterns in quotes or parentheses
            r'[("](\d+(?:,\d+)*(?:\.\d+)?)\s*(?:employees|workers|staff|jobs|people)[^)]{0,30}(?:laid off|cut|eliminated)',
        ]
        
        all_matches = []
        for pattern_idx, pattern in enumerate(patterns):
            # Use finditer to get full match context
            for match_obj in re.finditer(pattern, text, re.IGNORECASE):
                match = match_obj.group(1)  # Get the captured number
                full_match = match_obj.group(0).lower()  # Get full matched text
                try:
                    # Handle K/M notation - check full match text, not just captured number
                    num_str = str(match).lower().replace(',', '')
                    if 'k' in full_match or 'thousand' in full_match:
                        num = float(num_str)
                        num = int(num * 1000)
                    elif 'm' in full_match or 'million' in full_match:
                        num = float(num_str)
                        num = int(num * 1000000)
                    else:
                        num = int(float(num_str))
                    
                    if 1 <= num <= 1000000:  # Reasonable range
                        all_matches.append(num)
                except (ValueError, IndexError) as e:
                    # Silently continue on conversion errors
                    continue
        
        # Return the largest number found (most likely to be the total)
        if all_matches:
            return max(all_matches)
        
        return None
    
    def extract_layoff_reason(self, text: str) -> Optional[Dict]:
        """Extract reason/context for layoffs"""
        text_lower = text.lower()
        
        # Bad signs (red)
        bad_patterns = {
            'revenue decline': r'revenue\s+(?:declin|drop|fall|decreas|down)',
            'losses': r'(?:loss|losin|negative|deficit)',
            'financial trouble': r'(?:financial\s+(?:trouble|difficult|struggle|crisis|distress)|bankruptcy|insolven)',
            'market downturn': r'(?:market\s+(?:downturn|crash|decline|recession)|economic\s+(?:recession|downturn|crisis))',
            'competition': r'(?:competition|competitor|market\s+share\s+loss)',
            'demand decline': r'(?:demand\s+(?:declin|drop|fall)|sales\s+(?:declin|drop|fall))',
        }
        
        # Good/neutral signs (green/yellow)
        good_patterns = {
            'cost optimization': r'(?:cost\s+(?:optimization|efficiency|saving|reduction)|efficiency|streamlin)',
            'strategic pivot': r'(?:strategic\s+(?:pivot|shift|focus|restructuring|transformation)|refocus|reposition)',
            'restructuring': r'(?:restructur(?:ing|e)|reorganiz(?:ation|ing)|realign)',
            'automation': r'(?:automation|ai\s+integration|technology\s+upgrade)',
            'post-merger': r'(?:post[\s-]?merger|after\s+acquisition|integration)',
        }
        
        reasons = []
        sentiment = 'neutral'
        
        for reason, pattern in bad_patterns.items():
            if re.search(pattern, text_lower):
                reasons.append(reason)
                sentiment = 'bad'
        
        for reason, pattern in good_patterns.items():
            if re.search(pattern, text_lower):
                reasons.append(reason)
                if sentiment != 'bad':
                    sentiment = 'good'
        
        if reasons:
            return {
                'reasons': ', '.join(reasons[:3]),  # Limit to 3 reasons
                'sentiment': sentiment
            }
        return None
    
    def extract_expected_savings(self, text: str) -> Optional[Dict]:
        """Extract expected cost savings from layoffs"""
        patterns = [
            r'(?:save|saving|savings|cut\s+costs?)\s+(?:of\s+)?\$?(\d+(?:\.\d+)?)\s*(?:billion|million|b|m)',
            r'\$(\d+(?:\.\d+)?)\s*(?:billion|million|b|m)\s+(?:in\s+)?(?:save|saving|savings|cost\s+reduction)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                unit = match.group(0).lower()
                if 'billion' in unit or 'b' in unit:
                    amount = amount * 1000000000
                elif 'million' in unit or 'm' in unit:
                    amount = amount * 1000000
                
                return {
                    'amount': int(amount),
                    'formatted': f"${amount/1000000:.1f}M" if amount >= 1000000 else f"${amount/1000:.0f}K"
                }
        return None
    
    def extract_financial_context(self, text: str) -> Optional[Dict]:
        """Extract financial context (revenue decline, losses, etc.)"""
        text_lower = text.lower()
        context = {}
        sentiment = 'neutral'
        
        # Revenue decline - allow text between verb and percentage
        revenue_pattern = r'revenue\s+(?:declin|drop|fall|decreas|down)(?:ed|ing|s)?(?:\s+(?:of|by))?\s+(\d+(?:\.\d+)?)\s*(?:percent|%)'
        match = re.search(revenue_pattern, text_lower)
        if match:
            pct = float(match.group(1))
            context['revenue_decline'] = pct
            sentiment = 'bad'
        
        # Losses mentioned
        if re.search(r'(?:loss|losin|negative|deficit)', text_lower):
            context['losses_mentioned'] = True
            sentiment = 'bad'
        
        # Profit warning
        if re.search(r'(?:profit\s+warning|earnings\s+warning|guidance\s+cut)', text_lower):
            context['profit_warning'] = True
            sentiment = 'bad'
        
        # Cost savings (positive)
        savings = self.extract_expected_savings(text)
        if savings:
            context['expected_savings'] = savings
            if sentiment != 'bad':
                sentiment = 'good'
        
        if context:
            return {
                'details': context,
                'sentiment': sentiment
            }
        return None
    
    def extract_affected_departments(self, text: str) -> Optional[List[str]]:
        """Extract which departments/divisions are affected"""
        departments = []
        text_lower = text.lower()
        
        department_keywords = [
            'sales', 'marketing', 'engineering', 'hr', 'human resources',
            'operations', 'manufacturing', 'retail', 'cloud', 'ai',
            'research', 'r&d', 'customer service', 'support', 'it',
            'finance', 'legal', 'product', 'design', 'content'
        ]
        
        for dept in department_keywords:
            pattern = r'\b' + re.escape(dept) + r'\b'
            if re.search(pattern, text_lower):
                # Check if it's in context of layoffs - expand context window
                dept_pos = text_lower.find(dept)
                context = text_lower[max(0, dept_pos-80):dept_pos+80]
                # More flexible keyword matching
                if any(kw in context for kw in ['layoff', 'cut', 'reduce', 'eliminate', 'close', 'team', 'department', 'division', '%']):
                    departments.append(dept.title())
        
        return departments[:5] if departments else None  # Limit to 5
    
    def extract_guidance_change(self, text: str) -> Optional[Dict]:
        """Extract guidance/outlook changes"""
        text_lower = text.lower()
        sentiment = 'neutral'
        change_type = None
        
        # Negative guidance
        if re.search(r'(?:lower|reduc|cut|revise\s+down|downgrad).{0,30}(?:guidance|outlook|forecast|expectation)', text_lower):
            change_type = 'negative'
            sentiment = 'bad'
        # Positive guidance
        elif re.search(r'(?:raise|increas|upgrad|improve).{0,30}(?:guidance|outlook|forecast|expectation)', text_lower):
            change_type = 'positive'
            sentiment = 'good'
        # Guidance mentioned
        elif re.search(r'(?:guidance|outlook|forecast)', text_lower):
            change_type = 'mentioned'
        
        if change_type:
            return {
                'type': change_type,
                'sentiment': sentiment
            }
        return None
    
    def get_ai_prediction_score_batch(self, articles: List[Dict]) -> Dict[int, Optional[Dict]]:
        """Get AI prediction scores for multiple articles in one API call (much faster)
        
        Args:
            articles: List of dicts with 'title', 'description', 'url', and 'index' keys
            
        Returns:
            Dict mapping article index to result dict (same format as get_ai_prediction_score)
        """
        if not articles:
            return {}
        
        # Check cache first for all articles
        results = {}
        uncached_articles = []
        
        for article in articles:
            cache_key = article.get('url') if article.get('url') else f"{article.get('title')}_{article.get('description')}"
            if cache_key in self.ai_prediction_cache:
                results[article['index']] = self.ai_prediction_cache[cache_key]
            else:
                uncached_articles.append(article)
        
        if not uncached_articles:
            return results
        
        # Build batch prompt (URL removed - Claude doesn't read URLs, saves tokens)
        # OPTIMIZATION: Truncate descriptions to 150 chars to reduce tokens while keeping key context for scoring
        articles_text = ""
        for i, article in enumerate(uncached_articles, 1):
            title = article.get('title', '')
            description = article.get('description', '')
            # Truncate description to first 150 chars (usually contains key info for scoring)
            # This reduces tokens by ~50-60% while keeping important context
            if len(description) > 150:
                description = description[:150] + "..."
            articles_text += f"\n\nArticle {i}:\nTitle: {title}\nDescription: {description}\n"
        
        prompt = f"""Analyze the following {len(uncached_articles)} news articles and extract company information and predict stock impact for each.

{articles_text}

For EACH article, provide:
1. Company Name: The full official name of the company mentioned (e.g., "Tesla Inc", "Microsoft Corporation")
2. Stock Ticker: The stock ticker symbol if publicly traded (e.g., "TSLA", "MSFT"), or "N/A" if private
3. Stock price impact score (1-10): 1-3=Low, 4-6=Moderate, 7-10=High
4. Direction: "bullish" or "bearish"

IMPORTANT: Respond with ONE LINE PER ARTICLE in this exact format:
Article 1: [company name], [ticker or N/A], [score 1-10], [bullish or bearish]
Article 2: [company name], [ticker or N/A], [score 1-10], [bullish or bearish]
...

Examples:
Article 1: Tesla Inc, TSLA, 7, bearish
Article 2: Rad Power Bikes, N/A, 5, bearish
Article 3: Microsoft Corporation, MSFT, 3, bullish

Do not include any explanation. Just the numbered lines with the four values separated by commas."""

        try:
            headers = {
                'x-api-key': self.claude_api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            }
            
            payload = {
                'model': 'çclaude-3-haiku-20240307',
                'max_tokens': min(len(uncached_articles) * 100, 4096),  # Cap at Claude Haiku's limit (4096)
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            }
            
            response = requests.post(self.claude_api_url, headers=headers, json=payload, timeout=60, verify=False)
            
            # Handle rate limit errors and service overload errors
            if response.status_code == 429:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', 'Rate limit exceeded')
                raise Exception(f"Rate limit error (429): {error_msg}")
            elif response.status_code == 529:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', 'Service overloaded')
                raise Exception(f"Service overloaded (529): {error_msg}")
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('content', [])
                if content and len(content) > 0:
                    text = content[0].get('text', '').strip()
                    
                    # Parse each line - improved parsing to handle various formats
                    lines = text.split('\n')
                    parsed_count = 0
                    parsed_indices = set()  # Track which articles we've successfully parsed
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Try multiple patterns to match article lines
                        # Pattern 1: "Article 1: Company, TICKER, score, direction"
                        match = re.match(r'Article\s+(\d+)[:\.]\s*(.+)', line, re.IGNORECASE)
                        if not match:
                            # Pattern 2: "1. Company, TICKER, score, direction"
                            match = re.match(r'(\d+)[:\.]\s*(.+)', line)
                        if not match:
                            continue
                        
                        try:
                            article_num = int(match.group(1))
                            if article_num < 1 or article_num > len(uncached_articles):
                                continue
                            
                            # Skip if already parsed
                            if article_num - 1 in parsed_indices:
                                continue
                            
                            article = uncached_articles[article_num - 1]
                            data_str = match.group(2).strip()
                            
                            # Parse: "Company Name, TICKER or N/A, score, direction"
                            # Handle company names with commas by parsing from the end backwards
                            # Direction, score, and ticker are always single values
                            parts = [p.strip() for p in data_str.split(',')]
                            
                            if len(parts) >= 4:
                                # Parse from the end: direction, score, ticker are always last 3
                                direction = parts[-1].strip().lower()
                                score_str = parts[-2].strip()
                                ticker_str = parts[-3].strip().upper()
                                
                                # Company name is everything before the last 3 parts
                                company_name = ', '.join(parts[:-3]).strip()
                                
                                # Validate and convert
                                ticker = None if ticker_str == 'N/A' or ticker_str == '' or ticker_str == 'NA' else ticker_str
                                
                                # Try to parse score (handle non-numeric gracefully)
                                try:
                                    score = int(score_str)
                                except ValueError:
                                    # Try to extract number from string like "score: 7" or "7/10"
                                    score_match = re.search(r'(\d+)', score_str)
                                    if score_match:
                                        score = int(score_match.group(1))
                                    else:
                                        continue  # Skip if can't parse score
                                
                                # Accept "neutral" direction by mapping to "bullish" (neutral = no strong direction)
                                if direction in ['neutral', 'none', 'n/a', 'na']:
                                    direction = 'bullish'  # Default to bullish for neutral
                                
                                # Normalize direction
                                if 'bull' in direction:
                                    direction = 'bullish'
                                elif 'bear' in direction:
                                    direction = 'bearish'
                                
                                if 1 <= score <= 10 and direction in ['bullish', 'bearish']:
                                    result = {
                                        'company_name': company_name,
                                        'ticker': ticker,
                                        'score': score,
                                        'direction': direction
                                    }
                                    
                                    # Cache the result
                                    cache_key = article.get('url') if article.get('url') else f"{article.get('title')}_{article.get('description')}"
                                    self.ai_prediction_cache[cache_key] = result
                                    results[article['index']] = result
                                    parsed_count += 1
                                    parsed_indices.add(article_num - 1)
                        except (ValueError, IndexError, AttributeError) as e:
                            # Log parsing failures for debugging (only for small batches to avoid spam)
                            if len(uncached_articles) <= 10:
                                print(f"[BATCH PARSE WARNING] Failed to parse line: {line[:100]}... Error: {e}")
                            pass
                    
                    # Log parsing success rate
                    if len(uncached_articles) > 10:
                        success_rate = (parsed_count / len(uncached_articles)) * 100 if uncached_articles else 0
                        if success_rate < 50:
                            print(f"[BATCH PARSE WARNING] Low success rate: {parsed_count}/{len(uncached_articles)} ({success_rate:.1f}%) parsed successfully")
            
            else:
                # Log API errors
                print(f"[BATCH API ERROR] Claude API returned status {response.status_code}: {response.text[:200]}")
            
            # Fill in None for articles that failed
            for article in uncached_articles:
                if article['index'] not in results:
                    results[article['index']] = None
                    
        except Exception as e:
            # If batch fails, log the error and mark all as None
            print(f"[BATCH API ERROR] Exception during batch API call: {e}")
            import traceback
            if len(uncached_articles) <= 10:  # Only print full traceback for small batches
                traceback.print_exc()
            for article in uncached_articles:
                results[article['index']] = None
        
        return results
    
    def get_ai_prediction_score(self, title: str, description: str, url: str) -> Optional[Dict]:
        """Get AI prediction score (1-10), direction (bullish/bearish), company name, and ticker from Claude API
        
        Args:
            title: Article title
            description: Article description
            url: Article URL
            
        Returns:
            Dict with 'company_name', 'ticker' (or None if private), 'score' (1-10), and 'direction' ('bullish' or 'bearish'), or None if API call fails
        """
        # Check cache first
        cache_key = url if url else f"{title}_{description}"
        if cache_key in self.ai_prediction_cache:
            return self.ai_prediction_cache[cache_key]
        
        try:
            # Build prompt for Claude to extract company info and predict stock impact
            # Note: URL removed - Claude doesn't read URLs, saves tokens
            prompt = f"""Analyze the following news article and extract the company information, then predict stock impact.

Article Title: {title}
Article Description: {description}

Please provide:
1. Company Name: The full official name of the company mentioned in the article (e.g., "Tesla Inc", "Microsoft Corporation")
2. Stock Ticker: The stock ticker symbol if the company is publicly traded (e.g., "TSLA", "MSFT"), or "N/A" if the company is private or not publicly traded
3. Stock price impact score on a scale of 1-10:
   - 1-3: Low impact (minimal effect)
   - 4-6: Moderate impact (some effect expected)
   - 7-10: High impact (significant effect expected)
4. Direction: Will the stock price go UP (bullish) or DOWN (bearish)?

Consider factors such as:
- Severity of the event (layoffs, recalls, violations, etc.)
- Financial implications
- Regulatory or legal consequences
- Market sentiment indicators
- Company size and resilience
- Whether the news is positive or negative for the company

IMPORTANT: Respond with ONLY four values separated by commas:
- First value: Company name (e.g., "Tesla Inc")
- Second value: Stock ticker symbol or "N/A" if private (e.g., "TSLA" or "N/A")
- Third value: An integer between 1 and 10 (the impact score)
- Fourth value: Either "bullish" or "bearish" (the direction)

Format: [company name], [ticker or N/A], [number], [bullish or bearish]

Examples:
- "Tesla Inc, TSLA, 7, bearish"
- "Rad Power Bikes, N/A, 5, bearish"
- "Microsoft Corporation, MSFT, 3, bullish"

Do not include any explanation, additional text, or formatting. Just the four values separated by commas."""

            headers = {
                'x-api-key': self.claude_api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            }
            
            payload = {
                'model': 'claude-3-haiku-20240307',
                'max_tokens': 50,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            }
            
            response = requests.post(self.claude_api_url, headers=headers, json=payload, timeout=30, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('content', [])
                if content and len(content) > 0:
                    text = content[0].get('text', '').strip()
                    # Expected format: "Company Name, TICKER or N/A, score, direction"
                    # Example: "Tesla Inc, TSLA, 7, bearish" or "Rad Power Bikes, N/A, 5, bearish"
                    # Try to parse the full format first
                    parts = [p.strip() for p in text.split(',')]
                    if len(parts) >= 4:
                        company_name = parts[0].strip()
                        ticker_str = parts[1].strip().upper()
                        ticker = None if ticker_str == 'N/A' or ticker_str == '' else ticker_str
                        try:
                            score = int(parts[2].strip())
                            direction = parts[3].strip().lower()
                            
                            if 1 <= score <= 10 and direction in ['bullish', 'bearish']:
                                result = {
                                    'company_name': company_name,
                                    'ticker': ticker,
                                    'score': score,
                                    'direction': direction
                                }
                                # Cache the result
                                self.ai_prediction_cache[cache_key] = result
                                return result
                        except (ValueError, IndexError):
                            pass
                    
                    # Fallback: Try to extract components separately
                    # Extract company name (look for capitalized words before ticker/score)
                    company_match = re.search(r'^([A-Z][^,]+?)(?:,\s*(?:[A-Z]{1,5}|N/A))', text)
                    ticker_match = re.search(r',\s*([A-Z]{1,5}|N/A)\s*,', text, re.IGNORECASE)
                    score_match = re.search(r'\b([1-9]|10)\b', text)
                    direction_match = re.search(r'\b(bullish|bearish)\b', text, re.IGNORECASE)
                    
                    if company_match and ticker_match and score_match and direction_match:
                        company_name = company_match.group(1).strip()
                        ticker_str = ticker_match.group(1).strip().upper()
                        ticker = None if ticker_str == 'N/A' or ticker_str == '' else ticker_str
                        score = int(score_match.group(1))
                        direction = direction_match.group(1).lower()
                        
                        if 1 <= score <= 10 and direction in ['bullish', 'bearish']:
                            result = {
                                'company_name': company_name,
                                'ticker': ticker,
                                'score': score,
                                'direction': direction
                            }
                            self.ai_prediction_cache[cache_key] = result
                            return result
            else:
                # API call failed - return None silently
                pass
            
            # If we get here, API call failed or couldn't parse response
            return None
            
        except Exception as e:
            print(f"[AI PREDICTION ERROR] Failed to get AI prediction: {e}")
            return None
    
    def extract_market_sentiment(self, text: str) -> Optional[Dict]:
        """Extract market sentiment with comprehensive keyword patterns"""
        text_lower = text.lower()
        sentiment = 'neutral'
        indicators = []
        confidence = 0
        
        # Check for analyst/expert presence
        analyst_patterns = [
            r'(?:analyst|analysts|expert|experts|strategist|strategists|economist|economists|trader|traders|investor|investors)',
            r'(?:wall street|street analyst|research analyst|equity analyst|fund manager|portfolio manager)',
            r'(?:jpmorgan|goldman sachs|morgan stanley|bank of america|citi|wells fargo|barclays|deutsche bank|credit suisse|ubs|bernstein|jefferies|mizuho|nomura)',
        ]
        has_analyst = any(re.search(pattern, text_lower) for pattern in analyst_patterns)
        
        # Positive patterns (with context)
        positive_patterns = [
            # Ratings
            r'(?:upgrade|upgraded|upgrading).{0,50}(?:rating|target|price|recommendation)',
            r'(?:buy|strong buy|outperform|overweight|positive|bullish|bull|optimistic|favorable|excellent|outstanding|exceptional|stellar|remarkable)',
            
            # Market reaction positive (strong terms)
            r'(?:well[\s-]?received|well[\s-]?received|positive\s+reaction|positive\s+response|enthusiastic|ecstatic|euphoric|celebrated)',
            r'(?:market|investor|trading).{0,30}(?:react.{0,30}positive|cheered|welcomed|embraced|applauded|praised|celebrated)',
            r'(?:shares|stock|price).{0,30}(?:rose|jumped|rallied|surged|gained|soared|climbed|exploded|rocketed|skyrocketed|spiked|leaped|mounted|ascended|ballooned)',
            
            # Analyst opinions positive (strong terms)
            r'(?:seen as|viewed as|considered).{0,50}(?:positive|good|favorable|constructive|encouraging|excellent|outstanding|exceptional|stellar|remarkable|impressive|compelling|attractive|promising)',
            r'(?:good|smart|strategic|necessary|prudent|constructive|brilliant|excellent|outstanding|exceptional|stellar|remarkable|impressive|compelling|masterful).{0,30}(?:move|decision|action|step)',
            
            # Price targets positive (strong terms)
            r'(?:raised|increased|higher|boosted|hiked|lifted|elevated).{0,50}(?:target|price target|forecast|estimate|projection)',
            r'(?:upside|attractive|room to grow|better than expected|exceeded expectations|crushed expectations|blew past|surpassed|outperformed|beat estimates|topped forecasts|outstripped)',
            
            # Strong positive action words
            r'(?:breakthrough|game[\s-]?changer|transformative|revolutionary|groundbreaking|innovative|disruptive|pioneering)',
            r'(?:record[\s-]?breaking|all[\s-]?time high|historic|unprecedented|extraordinary|phenomenal|spectacular|magnificent)',
            r'(?:massive|huge|enormous|tremendous|substantial|significant|major|considerable).{0,30}(?:gain|increase|growth|surge|rally|jump|boost)',
            r'(?:strong|robust|solid|healthy|vigorous|thriving|flourishing|prospering).{0,30}(?:performance|results|growth|demand|sales|revenue|earnings)',
        ]
        
        # Negative patterns (with context)
        negative_patterns = [
            # Ratings
            r'(?:downgrade|downgraded|downgrading).{0,50}(?:rating|target|price|recommendation)',
            r'(?:sell|strong sell|underperform|underweight|negative|bearish|bear|pessimistic|unfavorable|dismal|terrible|awful|catastrophic|devastating)',
            
            # Market reaction negative (strong terms)
            r'(?:concern|worr|fear|uncertain|caution|warning|risk|troubl|alarm|panic|dread|anxiety|distress|turmoil|crisis|disaster)',
            r'(?:market|investor|trading).{0,30}(?:react.{0,30}negative|worried|concerned|panicked|frightened|alarmed|distressed|shocked|stunned)',
            r'(?:shares|stock|price).{0,30}(?:fell|dropped|plunged|tumbled|declined|sank|slumped|collapsed|cratered|crashed|nosedived|freefall|imploded|eroded|evaporated|melted|crumbled)',
            
            # Analyst opinions negative (strong terms)
            r'(?:seen as|viewed as|considered).{0,50}(?:negative|bad|unfavorable|worrisome|troubling|dismal|terrible|awful|catastrophic|devastating|disastrous|alarming|disturbing|shocking)',
            r'(?:bad|poor|concerning|worrisome|alarming|disappointing|troubling|dismal|terrible|awful|catastrophic|devastating|disastrous|shocking|disturbing|dire|bleak).{0,30}(?:move|decision|action|step|news|development)',
            
            # Price targets negative (strong terms)
            r'(?:lowered|cut|reduced|lower|slashed|chopped|trimmed|lowered|downgraded).{0,50}(?:target|price target|forecast|estimate|projection)',
            r'(?:downside|overvalued|expensive|worse than expected|missed expectations|fell short|disappointed|underperformed|failed to meet|disappointing results|weak performance)',
            
            # Strong negative action words
            r'(?:failure|collapse|breakdown|breakdown|meltdown|crash|disaster|catastrophe|calamity|debacle|fiasco)',
            r'(?:record[\s-]?low|all[\s-]?time low|historic low|unprecedented|catastrophic|devastating|disastrous|dire|bleak|grim)',
            r'(?:massive|huge|enormous|tremendous|substantial|significant|major|considerable|severe|drastic).{0,30}(?:loss|decline|drop|fall|plunge|crash|collapse|decrease|reduction|cutback)',
            r'(?:weak|poor|dismal|terrible|awful|pathetic|lousy|abysmal|atrocious).{0,30}(?:performance|results|growth|demand|sales|revenue|earnings|outlook|guidance)',
            r'(?:bleeding|hemorrhaging|crumbling|imploding|collapsing|failing|struggling|suffering|deteriorating|worsening)',
        ]
        
        # Count matches
        positive_matches = sum(1 for pattern in positive_patterns if re.search(pattern, text_lower))
        negative_matches = sum(1 for pattern in negative_patterns if re.search(pattern, text_lower))
        
        # Determine sentiment
        if positive_matches > negative_matches and positive_matches > 0:
            sentiment = 'good'
            if has_analyst:
                indicators.append('Analyst positive')
            else:
                indicators.append('Market positive')
            confidence = positive_matches
            
        elif negative_matches > positive_matches and negative_matches > 0:
            sentiment = 'bad'
            if has_analyst:
                indicators.append('Analyst negative')
            else:
                indicators.append('Market concern')
            confidence = negative_matches
            
        elif has_analyst:
            # Analyst mentioned but no clear sentiment
            sentiment = 'neutral'
            indicators.append('Analysis available')
        
        # Add specific indicators if found
        if re.search(r'upgrade', text_lower):
            indicators.append('Upgrade mentioned')
        if re.search(r'downgrade', text_lower):
            indicators.append('Downgrade mentioned')
        if re.search(r'(?:price|target).{0,30}(?:raised|increased|higher)', text_lower):
            indicators.append('Target raised')
        if re.search(r'(?:price|target).{0,30}(?:lowered|cut|reduced)', text_lower):
            indicators.append('Target cut')
        
        if indicators:
            return {
                'indicators': ', '.join(indicators),
                'sentiment': sentiment
            }
        
        return None
    
    def is_market_open(self, dt: datetime, ticker: str = None) -> bool:
        """Check if stock market is open at given datetime for a specific ticker.
        
        Args:
            dt: Datetime to check
            ticker: Optional ticker symbol to use exchange-specific hours. If None, uses US hours.
        
        Returns:
            True if market is open, False otherwise
        """
        # Market is closed for future dates
        if self.is_future_date(dt):
            return False
        
        # Detect exchange if ticker provided
        if ticker:
            exchange = self._detect_exchange_from_ticker(ticker)
            market_config = self._get_market_hours(exchange)
        else:
            # Default to US for backward compatibility
            exchange = 'US'
            market_config = self.EXCHANGE_MARKET_HOURS['US']
        
        # Handle timezone-aware and timezone-naive datetimes
        if dt.tzinfo is None:
            dt_utc = dt.replace(tzinfo=timezone.utc)
        else:
            dt_utc = dt.astimezone(timezone.utc)
        
        # Get timezone offset for the exchange
        base_offset = market_config['timezone_offset']
        
        # Adjust for DST if needed (simplified - can be enhanced later)
        # For US: EST (UTC-5) in winter, EDT (UTC-4) in summer
        # For others: Assume no DST for simplicity (can be enhanced)
        month = dt_utc.month
        if exchange == 'US':
            if month >= 3 and month <= 10:  # Rough DST period
                offset_hours = -4  # EDT
            else:
                offset_hours = -5  # EST
        elif exchange == 'L':  # London: GMT in winter, BST (UTC+1) in summer
            if month >= 3 and month <= 10:
                offset_hours = 1  # BST
            else:
                offset_hours = 0  # GMT
        elif exchange in ['PA', 'DE']:  # Paris/Frankfurt: CET (UTC+1) in winter, CEST (UTC+2) in summer
            if month >= 3 and month <= 10:
                offset_hours = 2  # CEST
            else:
                offset_hours = 1  # CET
        else:
            # No DST adjustment for other exchanges
            offset_hours = base_offset
        
        # Calculate local time
        local_timedelta = timedelta(hours=offset_hours)
        dt_local = dt_utc + local_timedelta
        
        local_hour = dt_local.hour
        local_minute = dt_local.minute
        weekday = dt_local.weekday()  # 0=Monday, 6=Sunday
        
        # Market is closed on weekends
        if weekday not in market_config['trading_days']:
            return False
        
        # Check if within market hours
        market_open_hour, market_open_minute = market_config['open']
        market_close_hour, market_close_minute = market_config['close']
        
        # Market opens at specified time
        if local_hour == market_open_hour and local_minute >= market_open_minute:
            return True
        # Market is open between open+1 hour and close-1 hour
        if market_open_hour + 1 <= local_hour < market_close_hour:
            return True
        # Market closes at exactly specified time
        if local_hour == market_close_hour and local_minute == market_close_minute:
            return True
        
        return False
    
    def hours_until_market_close(self, dt: datetime) -> Optional[float]:
        """Calculate hours until market close (4:00 PM ET) from given datetime
        Returns None if market is closed or it's a weekend"""
        if not self.is_market_open(dt):
            return None
        
        # Handle timezone-aware and timezone-naive datetimes
        if dt.tzinfo is None:
            dt_utc = dt.replace(tzinfo=timezone.utc)
        else:
            dt_utc = dt.astimezone(timezone.utc)
        
        # Convert UTC to ET (EST is UTC-5, EDT is UTC-4)
        month = dt_utc.month
        if month >= 3 and month <= 10:  # Rough DST period
            et_offset_hours = -4  # EDT
        else:
            et_offset_hours = -5  # EST
        
        et_timedelta = timedelta(hours=et_offset_hours)
        dt_et = dt_utc + et_timedelta
        
        et_hour = dt_et.hour
        et_minute = dt_et.minute
        
        # Market closes at 4:00 PM ET (16:00)
        market_close_hour = 16
        market_close_minute = 0
        
        # Calculate hours until close
        hours_until_close = (market_close_hour - et_hour) + (market_close_minute - et_minute) / 60.0
        
        return max(0, hours_until_close)  # Return 0 if already past close
    
    def is_future_date(self, dt: datetime) -> bool:
        """Check if date is in the future"""
        from datetime import timezone
        # Handle both timezone-aware and timezone-naive datetimes
        if dt.tzinfo is not None:
            # dt is timezone-aware, compare with timezone-aware now
            now = datetime.now(timezone.utc)
        else:
            # dt is timezone-naive, compare with timezone-naive now
            now = datetime.now()
        return dt > now
    
    def _is_valid_ticker(self, ticker: str) -> bool:
        """Check if ticker exists in SEC EDGAR data (loaded on init)
        
        Args:
            ticker: Stock ticker symbol to validate
        
        Returns:
            True if ticker exists in SEC EDGAR, False otherwise
        """
        if not ticker:
            return False
        # Check if ticker exists in our loaded SEC EDGAR data
        return ticker.upper() in self.ticker_to_cik_cache
    
    def _is_ticker_available(self, ticker: str) -> bool:
        """Check if ticker is available for API calls (not invalid or failed)
        
        Args:
            ticker: Stock ticker symbol to check
        
        Returns:
            True if ticker is available for API calls, False if it should be skipped
        """
        if not ticker:
            return False
        
        ticker_upper = ticker.upper()
        
        # Skip hardcoded invalid tickers (known to not exist in Prixe.io)
        if ticker_upper in self.invalid_tickers:
            return False
        
        # Skip previously failed tickers (Prixe.io returned 404 for these)
        if ticker_upper in self.failed_tickers:
            return False
        
        # Don't validate against SEC EDGAR - let Prixe.io validate by attempting API call
        # This allows foreign tickers and other tickers not in SEC EDGAR to work
        return True
    
    def _prixe_api_request(self, endpoint: str, payload: Dict) -> Optional[Dict]:
        """Make a request to Prixe.io API
        
        Args:
            endpoint: API endpoint (e.g., '/api/last_sold', '/api/historical')
            payload: Request payload as dict
        
        Returns:
            Response JSON as dict, or None if error
        """
        import json
        import time
        
        # Extract ticker from payload for validation
        ticker = payload.get('ticker', '')
        ticker_upper = ticker.upper() if ticker else ''
        
        # PERFORMANCE: Skip hardcoded invalid tickers (known 404s)
        if ticker_upper in self.invalid_tickers:
            return None  # Fast-fail without making API call
        
        # PERFORMANCE: Skip API call if this ticker previously returned 404
        if ticker_upper in self.failed_tickers:
            return None  # Fast-fail without making API call
        
        # Don't pre-validate against SEC EDGAR - let Prixe.io validate the ticker
        # This allows foreign tickers and other tickers not in SEC EDGAR to work
        # If Prixe.io returns 404, we'll mark it as failed below
        import sys
        
        url = f"{PRIXE_BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {PRIXE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Also write directly to stderr (which goes to log file) to bypass any stdout redirection
        log_msg = f"""
{'='*80}
[PRIXE.IO API REQUEST]
  URL: {url}
  Method: POST
  Headers: {json.dumps(headers, indent=2)}
  Payload: {json.dumps(payload, indent=2)}
  Timestamp: {datetime.now().isoformat()}
{'='*80}
"""
        print(log_msg, flush=True)
        sys.stderr.write(log_msg)
        sys.stderr.flush()
        
        start_time = time.time()
        
        # Retry logic for rate limit errors (429)
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        response = None
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Increment API call counter
                self.api_call_count += 1
                call_num = self.api_call_count
                
                # Show progress with total estimate if available
                total_str = f"/{self.total_api_calls_estimated}" if self.total_api_calls_estimated > 0 else ""
                retry_str = f" (attempt {attempt + 1}/{max_retries})" if attempt > 0 else ""
                print(f"[API CALL #{call_num}{total_str}] Making request to {url}{retry_str}...", flush=True)
                sys.stderr.write(f"[API CALL #{call_num}{total_str}] Making request to {url}{retry_str}...\n")
                sys.stderr.flush()
                
                # PERFORMANCE: Reduced timeout from 30s to 5s for faster failure on errors
                # Also fail fast on 404s to avoid waiting for timeout
                response = requests.post(url, headers=headers, json=payload, timeout=5, verify=False)
                elapsed_time = time.time() - start_time
                
                # Check for 429 rate limit error - retry with exponential backoff
                if response.status_code == 429:
                    if attempt < max_retries - 1:  # Not the last attempt
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                        ticker_info = f" (Ticker: {ticker})" if ticker else ""
                        print(f"[RATE LIMIT 429] Retrying in {wait_time}s{ticker_info}... (attempt {attempt + 1}/{max_retries})", flush=True)
                        sys.stderr.write(f"[RATE LIMIT 429] Retrying in {wait_time}s{ticker_info}... (attempt {attempt + 1}/{max_retries})\n")
                        sys.stderr.flush()
                        time.sleep(wait_time)
                        continue  # Retry the request
                    else:
                        # Last attempt failed - log and return None
                        ticker_info = f" (Ticker: {ticker})" if ticker else ""
                        error_msg = f"Prixe.io API rate limit exceeded (429) after {max_retries} attempts{ticker_info}"
                        log_msg = f"\n[PRIXE.IO API ERROR - RATE LIMIT]\n  Error: {error_msg}\n  Ticker: {ticker if ticker else 'N/A'}\n  Endpoint: {endpoint}\n  Payload: {json.dumps(payload, indent=2)}\n  URL: {url}\n  Response Time: {elapsed_time:.3f} seconds\n{'='*80}\n"
                        print(log_msg, flush=True)
                        sys.stderr.write(log_msg)
                        sys.stderr.flush()
                        
                        self.api_errors.append({
                            'service': 'Prixe.io',
                            'type': 'rate_limit',
                            'message': error_msg,
                            'endpoint': endpoint,
                            'ticker': ticker,
                        })
                        return None
                
                # If not 429, break out of retry loop and continue with normal processing
                break
                
            except requests.exceptions.HTTPError as e:
                # Check if it's a 429 error in the exception
                if e.response and e.response.status_code == 429:
                    if attempt < max_retries - 1:  # Not the last attempt
                        wait_time = retry_delay * (2 ** attempt)
                        ticker_info = f" (Ticker: {ticker})" if ticker else ""
                        print(f"[RATE LIMIT 429] Retrying in {wait_time}s{ticker_info}... (attempt {attempt + 1}/{max_retries})", flush=True)
                        sys.stderr.write(f"[RATE LIMIT 429] Retrying in {wait_time}s{ticker_info}... (attempt {attempt + 1}/{max_retries})\n")
                        sys.stderr.flush()
                        time.sleep(wait_time)
                        last_exception = e
                        continue  # Retry the request
                    else:
                        # Last attempt failed - will be handled below
                        last_exception = e
                        break
                else:
                    # Not a 429 error - don't retry, break and handle normally
                    last_exception = e
                    break
            except Exception as e:
                # Other exceptions - don't retry, break and handle normally
                last_exception = e
                break
        
        # If we had a 429 error on the last attempt, handle it
        if last_exception and isinstance(last_exception, requests.exceptions.HTTPError):
            if last_exception.response and last_exception.response.status_code == 429:
                elapsed_time = time.time() - start_time
                ticker_info = f" (Ticker: {ticker})" if ticker else ""
                error_msg = f"Prixe.io API rate limit exceeded (429) after {max_retries} attempts{ticker_info}"
                log_msg = f"\n[PRIXE.IO API ERROR - RATE LIMIT]\n  Error: {error_msg}\n  Ticker: {ticker if ticker else 'N/A'}\n  Endpoint: {endpoint}\n  Payload: {json.dumps(payload, indent=2)}\n  URL: {url}\n  Response Time: {elapsed_time:.3f} seconds\n{'='*80}\n"
                print(log_msg, flush=True)
                sys.stderr.write(log_msg)
                sys.stderr.flush()
                
                self.api_errors.append({
                    'service': 'Prixe.io',
                    'type': 'rate_limit',
                    'message': error_msg,
                    'endpoint': endpoint,
                    'ticker': ticker,
                })
                return None
        
        # Continue with normal error handling if we have an exception
        if last_exception:
            raise last_exception
        
        try:
            # PERFORMANCE: Fail fast on 404 errors (ticker not found in Prixe.io)
            if response.status_code == 404:
                # Cache failed ticker to avoid future API calls
                if ticker:
                    self.failed_tickers.add(ticker.upper())
                
                # Only log error if it's not a known invalid ticker (to reduce noise)
                if ticker_upper not in self.invalid_tickers:
                    # Check if it's an endpoint issue or ticker issue
                    try:
                        error_data = response.json()
                        error_text = str(error_data).lower()
                        # If error mentions ticker, it's a ticker issue, not endpoint issue
                        if 'ticker' in error_text or ticker_upper in error_text:
                            error_msg = f"Ticker '{ticker}' not found in Prixe.io (404). This ticker may not be available."
                        else:
                            error_msg = f"Prixe.io API endpoint not found: {endpoint} (404). Ticker: {ticker}. This endpoint may not exist or may have changed."
                    except:
                        error_msg = f"Ticker '{ticker}' not found in Prixe.io (404). This ticker may not be available."
                    
                    # Only add to errors if it's not a known invalid ticker
                    if ticker_upper not in self.invalid_tickers:
                        log_msg = f"\n[PRIXE.IO API ERROR - 404]\n  Error: {error_msg}\n  Ticker: {ticker}\n  Endpoint: {endpoint}\n  Payload: {json.dumps(payload, indent=2)}\n  URL: {url}\n  Response Time: {elapsed_time:.3f} seconds\n{'='*80}\n"
                        print(log_msg, flush=True)
                        sys.stderr.write(log_msg)
                        sys.stderr.flush()
                        
                        self.api_errors.append({
                            'service': 'Prixe.io',
                            'type': 'ticker_not_found',
                            'message': error_msg,
                            'endpoint': endpoint,
                            'ticker': ticker,
                        })
                return None
            
            # PERFORMANCE: Fast-fail on 400 errors (invalid parameters, e.g., date too old)
            # This avoids logging overhead and waiting for error processing
            if response.status_code == 400:
                # Check if it's a date-related error (most common 400 for intraday data >60 days)
                try:
                    error_data = response.json()
                    if 'error' in error_data and '60 days' in str(error_data.get('error', '')).lower():
                        # Skip logging - this is expected for old dates
                        return None
                except:
                    pass
                # Other 400 errors - return None without logging (saves time)
                return None
            
            # Parse response JSON (needed for return value)
            try:
                response_json = response.json()
            except Exception as json_err:
                response_json = None
            
            # Only log API responses if there's an error or unusually slow response
            # Successful fast responses don't need verbose logging (too much output)
            if response.status_code != 200 or elapsed_time > 2.0:
                # Only show response body for errors
                if response.status_code != 200:
                    try:
                        response_body_str = json.dumps(response_json, indent=2)[:500] if response_json else "No response body"
                    except:
                        response_body_str = response.text[:200] if response.text else "No response body"
                else:
                    response_body_str = "Success (body omitted for brevity)"
                
                log_msg = f"""
[PRIXE.IO API RESPONSE]
  Status Code: {response.status_code}
  Response Time: {elapsed_time:.3f} seconds
  Response Body: {response_body_str}
{'='*80}
"""
                print(log_msg, flush=True)
                sys.stderr.write(log_msg)
                sys.stderr.flush()
            # For successful fast responses (< 2 seconds), don't log anything (too verbose)
            
            response.raise_for_status()
            
            if response_json:
                return response_json
            else:
                return response.json()
            
        except requests.exceptions.HTTPError as e:
            elapsed_time = time.time() - start_time
            ticker_info = f" (Ticker: {ticker})" if ticker else ""
            error_msg = f"Prixe.io API HTTP error for {endpoint}{ticker_info}: {e}"
            
            error_details = f"  Error: {error_msg}\n  Ticker: {ticker if ticker else 'N/A'}\n  Endpoint: {endpoint}\n  Payload: {json.dumps(payload, indent=2)}\n  Response Time: {elapsed_time:.3f} seconds\n"
            if e.response:
                error_details += f"  Status Code: {e.response.status_code}\n"
                try:
                    error_data = e.response.json()
                    error_details += f"  Error Response: {json.dumps(error_data, indent=2)}\n"
                    error_msg += f" - {error_data}"
                except:
                    error_details += f"  Error Response (raw): {e.response.text[:500]}\n"
                    error_msg += f" - Status: {e.response.status_code}"
            
            log_msg = f"\n[PRIXE.IO API ERROR - HTTP]\n{error_details}{'='*80}\n"
            print(log_msg, flush=True)
            sys.stderr.write(log_msg)
            sys.stderr.flush()
            
            self.api_errors.append({
                'service': 'Prixe.io',
                'type': 'http_error',
                'message': error_msg,
                'ticker': payload.get('ticker', 'unknown'),
                'endpoint': endpoint,
                'payload': payload
            })
            return None
        except requests.exceptions.RequestException as e:
            elapsed_time = time.time() - start_time
            # Include ticker in error message for better debugging
            ticker_info = f" (Ticker: {ticker})" if ticker else ""
            error_msg = f"Prixe.io API request error for {endpoint}{ticker_info}: {e}"
            
            log_msg = f"""
[PRIXE.IO API ERROR - REQUEST]
  Error: {error_msg}
  Ticker: {ticker if ticker else 'N/A'}
  Endpoint: {endpoint}
  Payload: {json.dumps(payload, indent=2)}
  Response Time: {elapsed_time:.3f} seconds
  Exception Type: {type(e).__name__}
{'='*80}
"""
            print(log_msg, flush=True)
            sys.stderr.write(log_msg)
            sys.stderr.flush()
            
            self.api_errors.append({
                'service': 'Prixe.io',
                'type': 'request_error',
                'message': error_msg,
                'ticker': payload.get('ticker', 'unknown'),
                'endpoint': endpoint,
                'payload': payload
            })
            return None
        except Exception as e:
            elapsed_time = time.time() - start_time
            ticker_info = f" (Ticker: {ticker})" if ticker else ""
            error_msg = f"Prixe.io API unexpected error for {endpoint}{ticker_info}: {e}"
            
            import traceback
            log_msg = f"""
[PRIXE.IO API ERROR - UNEXPECTED]
  Error: {error_msg}
  Ticker: {ticker if ticker else 'N/A'}
  Endpoint: {endpoint}
  Payload: {json.dumps(payload, indent=2)}
  Response Time: {elapsed_time:.3f} seconds
  Exception Type: {type(e).__name__}
  Traceback: {traceback.format_exc()}
{'='*80}
"""
            print(log_msg, flush=True)
            sys.stderr.write(log_msg)
            sys.stderr.flush()
            
            self.api_errors.append({
                'service': 'Prixe.io',
                'type': 'unexpected_error',
                'message': error_msg,
                'ticker': payload.get('ticker', 'unknown'),
                'endpoint': endpoint,
                'payload': payload
            })
            return None
    
    def get_stock_price_history(self, ticker: str, start_date: datetime, end_date: datetime = None) -> List[Dict]:
        """Get historical stock prices from start_date to end_date (or now if end_date is None) using Prixe.io
        
        OPTIMIZED: Uses pre-fetched batch data if available instead of making new API calls.
        Also caches filtered results to avoid re-filtering the same data.
        
        Returns:
            List of dicts with 'date', 'price', and 'timestamp' keys
        """
        if not ticker:
            return []
        
        if end_date is None:
            # Ensure end_date is timezone-aware
            end_date = datetime.now(timezone.utc)
        elif end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        # Ensure start_date is timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        
        # Check cache for this specific date range
        cache_key = f"price_history_filtered_{ticker}_{start_date.date()}_{end_date.date()}"
        if cache_key in self.price_history_cache:
            return self.price_history_cache[cache_key]
        
        # OPTIMIZATION: Use pre-fetched batch data if available
        if ticker in self.batch_data_cache:
            batch_data = self.batch_data_cache[ticker]
            data = batch_data.get('data', {})
            timestamps = data.get('timestamp', [])
            closes = data.get('close', [])
            
            if timestamps and closes:
                price_history = []
                start_timestamp = int(start_date.timestamp())
                end_timestamp = int(end_date.timestamp())
                
                for i, ts in enumerate(timestamps):
                    # Filter to only include dates in the requested range
                    if start_timestamp <= ts <= end_timestamp:
                        if i < len(closes):
                            try:
                                date_dt = datetime.fromtimestamp(ts)
                                price_history.append({
                                    'date': date_dt.strftime('%Y-%m-%d'),
                                    'price': float(closes[i]),
                                    'timestamp': int(ts * 1000)  # Convert to milliseconds
                                })
                            except:
                                continue
                
                # Sort by timestamp to ensure chronological order
                price_history.sort(key=lambda x: x['timestamp'])
                
                # No limit on data points - show all available data for complete charts
                
                # Cache the filtered result
                self.price_history_cache[cache_key] = price_history
                
                # PERFORMANCE: Removed verbose logging (called for every layoff)
                return price_history
        
        # Fallback: make API call if batch data not available (should rarely happen)
        price_history = []  # Initialize to avoid "referenced before assignment" error
        try:
            payload = {
                'ticker': ticker,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'interval': '1d'
            }
            
            response = self._prixe_api_request(PRIXE_PRICE_ENDPOINT, payload)
            
            if response and response.get('success') and 'data' in response:
                data = response['data']
                timestamps = data.get('timestamp', [])
                closes = data.get('close', [])
                
                price_history = []
                for i, ts in enumerate(timestamps):
                    if i < len(closes):
                        try:
                            date_dt = datetime.fromtimestamp(ts)
                            price_history.append({
                                'date': date_dt.strftime('%Y-%m-%d'),
                                'price': float(closes[i]),
                                'timestamp': int(ts * 1000)  # Convert to milliseconds
                            })
                        except:
                            continue
                # Sort by timestamp to ensure chronological order
                price_history.sort(key=lambda x: x['timestamp'])
                
                # No limit on data points - show all available data for complete charts
                
                # Cache the result
                self.price_history_cache[cache_key] = price_history
            
            # Return price_history (will be empty list if API call failed or returned no data)
            return price_history
            
        except Exception as e:
            print(f"Error fetching price history for {ticker}: {e}")
            return []
    
    def get_stock_price_at_time(self, ticker: str, target_datetime: datetime, price_type: str = 'close', require_exact_match: bool = False) -> tuple[Optional[float], bool]:
        """Get stock price at a specific datetime using Prixe.io API
        
        Args:
            ticker: Stock ticker symbol
            target_datetime: Target date/time
            price_type: 'open', 'close', 'high', 'low' - defaults to 'close'
            require_exact_match: If True, only return price if it's from the exact target date (no fallback)
        
        Returns:
            Tuple of (price, is_exact_match). If require_exact_match=True and no exact match, returns (None, False)
        """
        return self._get_stock_price_at_time_impl(ticker, target_datetime, price_type, require_exact_match)
    
    def _get_stock_price_at_time_impl(self, ticker: str, target_datetime: datetime, price_type: str = 'close', require_exact_match: bool = False) -> tuple[Optional[float], bool]:
        """Internal implementation of get_stock_price_at_time using Prixe.io
        
        Returns:
            Tuple of (price, is_exact_match)
        """
        try:
            # Format date for API
            date_str = target_datetime.strftime('%Y-%m-%d')
            
            # Check cache first (include price_type in cache key for open/close distinction)
            # Note: Cache doesn't track if it was an exact match, so skip cache when require_exact_match=True
            cache_key = f"{ticker}_{date_str}_{price_type}"
            if cache_key in self.stock_price_cache and not require_exact_match:
                # If not requiring exact match, we can use cached value
                # But we can't verify if it was exact, so return False for is_exact
                cached_price = self.stock_price_cache[cache_key]
                return cached_price, False  # Can't verify if cached was exact
            
            # Use Prixe.io to get historical price for the specific date
            # Prixe.io /api/price requires start_date, end_date, and interval
            # For a specific date, use that date as both start and end with 1d interval
            payload = {
                'ticker': ticker,
                'start_date': date_str,
                'end_date': date_str,
                'interval': '1d'
            }
            
            response = self._prixe_api_request(PRIXE_PRICE_ENDPOINT, payload)
            
            if response and response.get('success') and 'data' in response:
                # Prixe.io /api/price returns: { "data": { "open": [...], "close": [...], "high": [...], "low": [...], "price": number, "ticker": "...", "timestamp": [...] }, "success": true }
                data = response['data']
                timestamps = data.get('timestamp', [])
                target_timestamp = int(target_datetime.timestamp())
                
                # Find the closest timestamp match
                price = None
                response_date = date_str
                
                if timestamps:
                    # Find the index of the closest timestamp
                    closest_idx = 0
                    min_diff = abs(timestamps[0] - target_timestamp)
                    for i, ts in enumerate(timestamps):
                        diff = abs(ts - target_timestamp)
                        if diff < min_diff:
                            min_diff = diff
                            closest_idx = i
                    
                    # Get price based on price_type
                    if price_type == 'open' and 'open' in data:
                        prices = data['open']
                        if closest_idx < len(prices):
                            price = prices[closest_idx]
                    elif price_type == 'high' and 'high' in data:
                        prices = data['high']
                        if closest_idx < len(prices):
                            price = prices[closest_idx]
                    elif price_type == 'low' and 'low' in data:
                        prices = data['low']
                        if closest_idx < len(prices):
                            price = prices[closest_idx]
                    else:  # default to close
                        if 'close' in data:
                            prices = data['close']
                            if closest_idx < len(prices):
                                price = prices[closest_idx]
                        elif 'price' in data:
                            price = data['price']  # Current price
                    
                    # Check if we have an exact timestamp match
                    if timestamps[closest_idx] == target_timestamp:
                        response_date = date_str
                    else:
                        # Convert timestamp to date for comparison
                        from datetime import datetime as dt
                        response_timestamp = timestamps[closest_idx]
                        response_date_obj = dt.fromtimestamp(response_timestamp)
                        response_date = response_date_obj.strftime('%Y-%m-%d')
                
                if price is not None:
                    price_float = float(price)
                    is_exact = (response_date == date_str)
                    
                    # If exact match required and we don't have exact match, return None
                    if require_exact_match and not is_exact:
                        return None, False
                    
                    # Cache the result
                    self.stock_price_cache[cache_key] = price_float
                    return price_float, is_exact
            
            # If no data found and exact match required, return None
            if require_exact_match:
                        return None, False
            
            # Try to get current/last sold price as fallback (only if not requiring exact match)
            if not require_exact_match:
                payload_current = {'ticker': ticker}
                response_current = self._prixe_api_request('/api/last_sold', payload_current)
                
                if response_current:
                    current_price = None
                    current_price = None
                    if 'price' in response_current:
                        current_price = response_current.get('price')
                    elif 'data' in response_current:
                        data = response_current['data']
                        if isinstance(data, dict):
                            current_price = data.get('price')
                    
                if current_price:
                        price_float = float(current_price)
                    # Current price is never an exact match for historical dates
                        return price_float, False
        
        except Exception as e:
            import traceback
            traceback.print_exc()
        
        return None, False
    
    def get_stock_price_on_date(self, ticker: str, date: datetime) -> Optional[float]:
        """Get stock closing price on a specific date
        Handles market holidays by using previous trading day if needed
        
        Args:
            ticker: Stock ticker symbol
            date: Target date (datetime object)
            
        Returns:
            Closing price on that date, or None if not available
        """
        try:
            # Get price history for a few days around the target date to handle holidays
            start_date = date - timedelta(days=5)
            end_date = date + timedelta(days=1)
            
            price_history = self.get_stock_price_history(ticker, start_date, end_date)
            
            if not price_history:
                return None
            
            # Find the closest date to target date
            target_date_str = date.strftime('%Y-%m-%d')
            target_timestamp = int(date.timestamp())
            
            closest_price = None
            min_diff = float('inf')
            
            for entry in price_history:
                entry_date = entry.get('date')
                entry_timestamp = entry.get('timestamp', 0) / 1000  # Convert from ms
                price = entry.get('price')
                
                if price is None:
                    continue
                
                # Prefer exact date match
                if entry_date == target_date_str:
                    return float(price)
                
                # Otherwise find closest date (for holidays)
                diff = abs(entry_timestamp - target_timestamp)
                if diff < min_diff:
                    min_diff = diff
                    closest_price = float(price)
            
            return closest_price
            
        except Exception as e:
            print(f"Error getting stock price on date for {ticker}: {e}")
            return None
    
    def get_top_losers_prixe(
        self,
        bearish_date: datetime,
        industry: Optional[str] = None,
        logs: Optional[List[str]] = None,
        find_gainers: bool = False,
        flexible_days: int = 0,
        ticker_filter: Optional[List[str]] = None
    ) -> List[tuple[str, float, Dict, str]]:
        """Identify top losing or gaining stocks using Prixe.io data (reliable, works with SSL issues)
        
        Args:
            bearish_date: Date to check for price changes
            industry: Optional industry filter
            logs: Optional list to append log messages to
            find_gainers: If True, find stocks that increased (bullish), if False, find stocks that dropped (bearish)
            flexible_days: Number of days to check before/after bearish_date (0 = exact date only)
            
        Returns:
            List of tuples: (ticker, pct_change, company_info, actual_date)
            For bearish: Sorted by percentage drop (most negative first)
            For bullish: Sorted by percentage gain (most positive first)
            actual_date: The actual date when the best change occurred (YYYY-MM-DD format)
        """
        try:
            # Get all large-cap companies
            companies = self._get_large_cap_companies_with_options()
            
            # Filter by industry if specified
            if industry and industry != "All Industries":
                companies = {
                    ticker: info
                    for ticker, info in companies.items()
                    if info.get('industry') == industry
                }
            
            # Filter by ticker list if provided
            missing_tickers_info = {}  # Store Claude-fetched info for missing tickers
            if ticker_filter:
                tickers_set = {t.strip().upper() for t in ticker_filter if t.strip()}
                if tickers_set:
                    original_count = len(companies)
                    companies = {
                        ticker: info
                        for ticker, info in companies.items()
                        if ticker in tickers_set
                    }
                    if logs is not None:
                        missing = tickers_set.difference(set(companies.keys()))
                        initial_matched = len(companies)
                        logs.append(f"   🎯 Ticker filter applied: {', '.join(sorted(tickers_set))} (matched {initial_matched}/{len(tickers_set)})")
                        if missing:
                            logs.append(f"   ⚠️ Unknown or unsupported tickers: {', '.join(sorted(missing))}")
                            logs.append(f"   🔍 Attempting to fetch company info from Claude API for missing tickers...")
                            # Fetch info from Claude for missing tickers
                            fetched_count = 0
                            failed_tickers = []
                            for missing_ticker in sorted(missing):
                                if logs is not None:
                                    logs.append(f"   🔍 Fetching company info for {missing_ticker} from Claude API...")
                                ticker_info = self._fetch_ticker_info_from_claude(missing_ticker)
                                if ticker_info:
                                    # Add to companies dict temporarily for processing
                                    companies[missing_ticker] = {
                                        'name': ticker_info['name'],
                                        'industry': ticker_info['industry'],
                                        'market_cap': ticker_info['market_cap']
                                    }
                                    # Store info with flag for frontend
                                    missing_tickers_info[missing_ticker] = {
                                        'name': ticker_info['name'],
                                        'industry': ticker_info['industry'],
                                        'market_cap': ticker_info['market_cap'],
                                        'size_category': ticker_info.get('size_category', 'Unknown'),
                                        'is_missing_from_list': True
                                    }
                                    fetched_count += 1
                                    if logs is not None:
                                        logs.append(f"   ✅ Fetched info for {missing_ticker}: {ticker_info['name']} ({ticker_info['industry']}, {ticker_info.get('size_category', 'Unknown')})")
                                else:
                                    failed_tickers.append(missing_ticker)
                                    if logs is not None:
                                        logs.append(f"   ❌ Failed to fetch info for {missing_ticker} from Claude API (network error or ticker not found)")
                            
                            # Update the matched count in the log if we fetched any
                            if fetched_count > 0:
                                final_matched = len(companies)
                                logs.append(f"   📊 Updated: {final_matched}/{len(tickers_set)} tickers available for analysis ({fetched_count} fetched from Claude)")
                            
                            if failed_tickers:
                                logs.append(f"   ⚠️ Could not process {len(failed_tickers)} ticker(s): {', '.join(failed_tickers)} (Claude API unavailable or ticker not found)")
            
            # Helper function to append and print logs (for real-time streaming)
            def add_log_prixe(message):
                if logs is not None:
                    logs.append(message)
                print(message)  # Print to stdout for real-time streaming
            
            # Check if we have any companies to process
            if len(companies) == 0:
                if logs is not None:
                    if ticker_filter:
                        add_log_prixe(f"   ❌ No valid tickers to process. All tickers in filter were not found in stocks.json and Claude API failed to fetch their info.")
                    else:
                        add_log_prixe(f"   ❌ No companies found matching the criteria.")
                return []
            
            if logs is not None:
                if find_gainers:
                    add_log_prixe(f"   📊 Using Prixe.io to calculate gains for {len(companies)} stocks...")
                else:
                    add_log_prixe(f"   📊 Using Prixe.io to calculate drops for {len(companies)} stocks...")
                add_log_prixe(f"   📅 Date: {bearish_date.strftime('%Y-%m-%d')}")
                # Check if date is in the future
                now = datetime.now(timezone.utc)
                if bearish_date > now:
                    add_log_prixe(f"   ⚠️  Warning: Date is in the future. Prixe.io only has historical data up to today.")
            
            stocks = []  # Changed from 'losers' to 'stocks' to handle both gainers and losers
            processed = 0
            failed = 0
            # Force reload - stocks is initialized here
            
            # Process in parallel for better performance
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def process_ticker(ticker):
                """Process a single ticker to calculate drop - optimized to use 1 API call
                Supports flexible date lookup to find best change within date range
                """
                try:
                    # Check if date is in the future
                    now = datetime.now(timezone.utc)
                    if bearish_date > now:
                        # Date is in the future - Prixe.io only has historical data
                        if logs is not None and ticker == tickers[0]:  # Only log once for first ticker
                            add_log_prixe(f"   ⚠️  Warning: Date {bearish_date.strftime('%Y-%m-%d')} is in the future. Prixe.io only has historical data.")
                        return None
                    
                    # Calculate date range for flexible lookup
                    if flexible_days > 0:
                        # Use trading days (weekdays) for the ±N window
                        min_check_date = self.get_nth_trading_day_before(bearish_date, flexible_days)
                        max_check_date = self.get_nth_trading_day_after(bearish_date, flexible_days)
                        # Fetch wider range to ensure we have previous day data (also in trading days)
                        start_date = self.get_nth_trading_day_before(min_check_date, 5)
                        end_date = self.get_nth_trading_day_after(max_check_date, 1)
                    else:
                        # Exact date only (original behavior)
                        min_check_date = bearish_date
                        max_check_date = bearish_date
                        start_date = bearish_date - timedelta(days=5)
                        end_date = bearish_date + timedelta(days=1)
                    
                    price_history = self.get_stock_price_history(ticker, start_date, end_date)
                    
                    if not price_history:
                        return None
                    
                    # Sort by date
                    sorted_history = sorted(price_history, key=lambda x: x.get('date', ''))
                    
                    def find_best_change_in_range():
                        """Find the best (most negative for bearish, most positive for bullish) change within flexible date range"""
                        best_pct_change = None
                        best_date = None
                        best_price = None
                        best_prev_price = None
                        
                        # Convert dates to strings for comparison
                        min_date_str = min_check_date.strftime('%Y-%m-%d')
                        max_date_str = max_check_date.strftime('%Y-%m-%d')
                        
                        # Iterate through all dates in the flexible range
                        for i, entry in enumerate(sorted_history):
                            entry_date = entry.get('date', '')
                            price = entry.get('price')
                            
                            if not entry_date or price is None:
                                continue
                            
                            # Check if this date is within the flexible range
                            if entry_date < min_date_str or entry_date > max_date_str:
                                continue
                            
                            # Find previous trading day (before this entry)
                            prev_price = None
                            for j in range(i - 1, -1, -1):
                                prev_entry = sorted_history[j]
                                prev_entry_date = prev_entry.get('date', '')
                                prev_entry_price = prev_entry.get('price')
                                if prev_entry_date and prev_entry_price is not None and prev_entry_date < entry_date:
                                    prev_price = prev_entry_price
                                    break
                            
                            if prev_price is None or prev_price == 0:
                                continue
                            
                            # Calculate percentage change
                            pct_change = ((price - prev_price) / prev_price) * 100
                            
                            # Check if this is the best change so far
                            if best_pct_change is None:
                                best_pct_change = pct_change
                                best_date = entry_date
                                best_price = price
                                best_prev_price = prev_price
                            else:
                                if find_gainers:
                                    # For bullish: want most positive change
                                    if pct_change > best_pct_change:
                                        best_pct_change = pct_change
                                        best_date = entry_date
                                        best_price = price
                                        best_prev_price = prev_price
                                else:
                                    # For bearish: want most negative change
                                    if pct_change < best_pct_change:
                                        best_pct_change = pct_change
                                        best_date = entry_date
                                        best_price = price
                                        best_prev_price = prev_price
                        
                        return best_pct_change, best_date, best_price, best_prev_price
                    
                    # Find best change in range
                    best_pct_change, best_date, best_price, best_prev_price = find_best_change_in_range()
                    
                    if best_pct_change is None or best_price is None or best_prev_price is None or best_prev_price == 0:
                        return None
                    
                    # Get company info and add missing ticker flag if applicable
                    company_info = companies[ticker].copy()
                    if ticker in missing_tickers_info:
                        company_info['is_missing_from_list'] = True
                        company_info['size_category'] = missing_tickers_info[ticker].get('size_category', 'Unknown')
                    
                    # Return stocks based on find_gainers flag
                    if find_gainers:
                        # Only return stocks that increased (bullish)
                        if best_pct_change > 0:
                            return (ticker, best_pct_change, company_info, best_date)
                    else:
                        # Only return stocks that dropped (bearish)
                        if best_pct_change < 0:
                            return (ticker, best_pct_change, company_info, best_date)
                    return None
                except Exception as e:
                    return None
            
            # Process in parallel (limit to 10 workers to avoid Prixe.io rate limits)
            tickers = list(companies.keys())
            
            # Guard against empty tickers list (should not happen due to check above, but double-check for safety)
            if len(tickers) == 0:
                if logs is not None:
                    if ticker_filter:
                        add_log_prixe(f"   ❌ No valid tickers to process. All tickers in filter were not found in stocks.json and Claude API failed to fetch their info.")
                    else:
                        add_log_prixe(f"   ❌ No companies found matching the criteria.")
                return []
            
            max_workers = min(len(tickers), 10)  # Reduced from 20 to avoid 429 rate limit errors
            
            if logs is not None:
                add_log_prixe(f"   🚀 Processing {len(tickers)} tickers in parallel ({max_workers} workers)...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_ticker = {executor.submit(process_ticker, ticker): ticker for ticker in tickers}
                
                for future in as_completed(future_to_ticker):
                    ticker = future_to_ticker[future]
                    processed += 1
                    
                    try:
                        result = future.result()
                        if result:
                            stocks.append(result)
                    except Exception as e:
                        failed += 1
                        continue
                    
                    # Progress update every 50 tickers
                    if processed % 50 == 0 and logs is not None:
                        if find_gainers:
                            add_log_prixe(f"   ⏳ Processed {processed}/{len(tickers)} tickers... ({len(stocks)} gainers found)")
                        else:
                            add_log_prixe(f"   ⏳ Processed {processed}/{len(tickers)} tickers... ({len(stocks)} losers found)")
            
            # Sort by percentage change
            if find_gainers:
                # Sort by percentage gain (most positive first)
                stocks.sort(key=lambda x: x[1], reverse=True)
            else:
                # Sort by percentage drop (most negative first)
                stocks.sort(key=lambda x: x[1])
            
            if logs is not None:
                if find_gainers:
                    add_log_prixe(f"   ✓ Found {len(stocks)} stocks with gains using Prixe.io")
                else:
                    add_log_prixe(f"   ✓ Found {len(stocks)} stocks with drops using Prixe.io")
                if failed > 0:
                    add_log_prixe(f"   ⚠️  {failed} tickers failed to process")
            
            return stocks
            
        except Exception as e:
            error_msg = f"   ❌ Error in get_top_losers_prixe: {str(e)}"
            if logs is not None:
                logs.append(error_msg)
            print(error_msg)  # Print to stdout for real-time streaming
            import traceback
            traceback.print_exc()
            return []
    
    def get_top_losers_claude(self, bearish_date: datetime, industry: Optional[str] = None, logs: Optional[List[str]] = None) -> List[tuple[str, float, Dict]]:
        """Ask Claude AI to identify top bearish large-cap stocks for a specific date
        This is much faster than downloading data for all 197 companies
        
        Args:
            bearish_date: Date to check for drops
            industry: Optional industry filter
            logs: Optional list to append log messages to
            
        Returns:
            List of tuples: (ticker, pct_drop, company_info)
            Sorted by percentage drop (most negative first)
        """
        try:
            # Get all large-cap companies for reference
            companies = self._get_large_cap_companies_with_options()
            
            # Filter by industry if specified
            if industry and industry != "All Industries":
                companies = {ticker: info for ticker, info in companies.items() 
                           if info.get('industry') == industry}
            
            if logs is not None:
                logs.append(f"   🤖 Asking Claude AI to identify top bearish stocks...")
                logs.append(f"   📅 Date: {bearish_date.strftime('%Y-%m-%d')}")
                if industry and industry != "All Industries":
                    logs.append(f"   🏭 Industry: {industry}")
            
            # Create list of tickers for Claude
            ticker_list = ", ".join(sorted(companies.keys()))
            industry_filter = f" in the {industry} industry" if industry and industry != "All Industries" else ""
            
            # Format date nicely
            date_str = bearish_date.strftime('%B %d, %Y')
            day_of_week = bearish_date.strftime('%A')
            
            prompt = f"""You are a financial analyst. Identify the top bearish (biggest losing) large-cap stocks with active options trading on {day_of_week}, {date_str}{industry_filter}.

Based on historical stock market data, which large-cap stocks had the biggest percentage drops on this date?

Available tickers to consider (these are all large-cap stocks with active options):
{ticker_list}

For each stock that dropped on {date_str}, provide:
1. Stock ticker symbol (must be from the list above)
2. Percentage drop as a negative number (e.g., -5.2 means 5.2% drop)

CRITICAL: Respond with ONLY the ticker and percentage, ONE LINE PER STOCK, in this exact format:
TICKER, PERCENTAGE_DROP

Examples of correct format:
AAPL, -3.5
MSFT, -2.8
TSLA, -7.2
NVDA, -4.1

Requirements:
- Only include stocks that dropped (negative percentages)
- Only use tickers from the provided list
- Sort by most negative first (biggest drops first)
- Include at least the top 20-30 biggest losers, or all losers if fewer than 30
- Use your knowledge of historical stock market movements

Do not include any explanation, headers, or other text. Just the ticker and percentage separated by a comma, one per line."""

            headers = {
                'x-api-key': self.claude_api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            }
            
            payload = {
                'model': 'claude-3-haiku-20240307',
                'max_tokens': 2048,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            }
            
            response = requests.post(self.claude_api_url, headers=headers, json=payload, timeout=30, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('content', [])
                if content and len(content) > 0:
                    text = content[0].get('text', '').strip()
                    
                    if logs is not None:
                        logs.append(f"   ✓ Claude response received ({len(text)} characters)")
                        # Debug: show first 200 chars of response
                        preview = text[:200].replace('\n', ' ')
                        logs.append(f"   📝 Response preview: {preview}...")
                    
                    # Parse the response
                    losers = []
                    parsed_lines = 0
                    for line in text.split('\n'):
                        line = line.strip()
                        if not line or ',' not in line:
                            continue
                        
                        try:
                            parts = [p.strip() for p in line.split(',')]
                            if len(parts) >= 2:
                                ticker = parts[0].upper()
                                pct_str = parts[1].replace('%', '').strip()
                                pct_drop = float(pct_str)
                                
                                # Only include if it's a valid ticker and negative drop
                                if ticker in companies and pct_drop < 0:
                                    losers.append((ticker, pct_drop, companies[ticker]))
                                    parsed_lines += 1
                        except (ValueError, IndexError) as e:
                            # Skip invalid lines
                            continue
                    
                    # Sort by percentage drop (most negative first)
                    losers.sort(key=lambda x: x[1])
                    
                    if logs is not None:
                        if len(losers) > 0:
                            logs.append(f"   ✓ Found {len(losers)} bearish stocks from Claude")
                        else:
                            logs.append(f"   ⚠️  Claude response received but no valid stocks parsed")
                            logs.append(f"   💡 Tip: Date might be in the future or Claude couldn't find data")
                    
                    return losers
                else:
                    if logs is not None:
                        logs.append(f"   ⚠️  Claude returned empty response")
                    return []
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', f'Claude API error {response.status_code}')
                if logs is not None:
                    logs.append(f"   ⚠️  Claude API error: {error_msg}")
                return []
                
        except Exception as e:
            if logs is not None:
                logs.append(f"   ⚠️  Error asking Claude: {str(e)[:50]}...")
            return []
    
    def get_top_losers_yfinance(self, bearish_date: datetime, industry: Optional[str] = None, logs: Optional[List[str]] = None) -> List[tuple[str, float, Dict]]:
        """Quickly identify all losing stocks on bearish date using yfinance
        This is much faster than checking each stock individually
        
        Args:
            bearish_date: Date to check for drops
            industry: Optional industry filter
            logs: Optional list to append log messages to
            
        Returns:
            List of tuples: (ticker, pct_drop, company_info)
            Sorted by percentage drop (most negative first)
        """
        if not YFINANCE_AVAILABLE:
            if logs is not None:
                logs.append("   ⚠️  yfinance not available")
            return []
        
        try:
            # Get all large-cap companies
            companies = self._get_large_cap_companies_with_options()
            total_companies = len(companies)
            
            if logs is not None:
                logs.append(f"   📋 Loaded {total_companies} large-cap companies")
            
            # Filter by industry if specified
            if industry and industry != "All Industries":
                companies = {ticker: info for ticker, info in companies.items() 
                           if info.get('industry') == industry}
                if logs is not None:
                    logs.append(f"   🔍 Filtered to {len(companies)} companies in {industry}")
            
            if not companies:
                return []
            
            # Get previous trading day (look back up to 5 days)
            prev_date = bearish_date - timedelta(days=5)
            
            # Prepare date range for yfinance
            start_date = prev_date.date()
            end_date = (bearish_date + timedelta(days=1)).date()
            
            # Get all tickers
            tickers = list(companies.keys())
            
            if logs is not None:
                logs.append(f"   📥 Downloading price data for {len(tickers)} tickers using yfinance...")
            
            # Use yfinance to download data for all tickers at once (much faster!)
            # yfinance can handle multiple tickers in one call, but may have limits
            # Process in batches of 25 to reduce timeout risk and improve error handling
            batch_size = 25
            all_data = {}
            failed_tickers = []
            successful_tickers = []
            
            if len(tickers) > batch_size:
                if logs is not None:
                    logs.append(f"   📦 Processing in batches of {batch_size} (total: {len(tickers)} tickers)...")
                
                for i in range(0, len(tickers), batch_size):
                    batch_tickers = tickers[i:i+batch_size]
                    batch_num = (i // batch_size) + 1
                    total_batches = (len(tickers) + batch_size - 1) // batch_size
                    
                    if logs is not None:
                        logs.append(f"   ⏳ Batch {batch_num}/{total_batches}: Processing {len(batch_tickers)} tickers...")
                    
                    batch_success_count = 0
                    batch_failed_tickers = []
                    
                    try:
                        # Try to configure yfinance to handle SSL issues
                        # Note: yfinance uses curl_cffi which may have SSL certificate issues
                        # We'll catch errors and continue with successful tickers
                        batch_data = yf.download(
                            batch_tickers,
                            start=start_date.strftime('%Y-%m-%d'),
                            end=end_date.strftime('%Y-%m-%d'),
                            progress=False,
                            group_by='ticker',
                            threads=True,
                            # Try to suppress SSL warnings (may not work with curl_cffi)
                            show_errors=False
                        )
                        
                        # Store batch data
                        if batch_data is not None and not batch_data.empty:
                            for ticker in batch_tickers:
                                try:
                                    ticker_data = None
                                    if len(batch_tickers) > 1:
                                        if hasattr(batch_data.columns, 'get_level_values') and ticker in batch_data.columns.get_level_values(1):
                                            ticker_data = batch_data.xs(ticker, level=1, axis=1)
                                        else:
                                            try:
                                                ticker_data = batch_data[ticker]
                                            except:
                                                pass
                                    else:
                                        ticker_data = batch_data
                                    
                                    if ticker_data is not None and not ticker_data.empty:
                                        all_data[ticker] = ticker_data
                                        successful_tickers.append(ticker)
                                        batch_success_count += 1
                                    else:
                                        batch_failed_tickers.append(ticker)
                                        failed_tickers.append(ticker)
                                except Exception as ticker_error:
                                    batch_failed_tickers.append(ticker)
                                    failed_tickers.append(ticker)
                        
                        if logs is not None:
                            if batch_success_count > 0:
                                logs.append(f"   ✓ Batch {batch_num}: {batch_success_count}/{len(batch_tickers)} tickers succeeded")
                            if len(batch_failed_tickers) > 0:
                                logs.append(f"   ⚠️  Batch {batch_num}: {len(batch_failed_tickers)} tickers failed (will retry individually)")
                                
                    except Exception as e:
                        # Batch failed completely - mark all tickers for individual retry
                        batch_failed_tickers = batch_tickers
                        failed_tickers.extend(batch_tickers)
                        if logs is not None:
                            error_msg = str(e)[:80]
                            # Check if it's an SSL error
                            is_ssl_error = 'SSL' in str(e) or 'certificate' in str(e).lower() or 'curl' in str(e).lower()
                            if is_ssl_error:
                                logs.append(f"   ⚠️  Batch {batch_num} SSL error: {error_msg}... (will retry individually)")
                            else:
                                logs.append(f"   ⚠️  Batch {batch_num} failed: {error_msg}... (will retry individually)")
                    
                    # Retry failed tickers individually (more reliable but slower)
                    if len(batch_failed_tickers) > 0:
                        if logs is not None:
                            logs.append(f"   🔄 Retrying {len(batch_failed_tickers)} failed tickers individually...")
                        
                        for ticker in batch_failed_tickers:
                            try:
                                # Try individual download (sometimes works better for SSL issues)
                                stock = yf.Ticker(ticker)
                                hist = stock.history(start=start_date.strftime('%Y-%m-%d'), 
                                                   end=end_date.strftime('%Y-%m-%d'))
                                
                                if hist is not None and not hist.empty:
                                    all_data[ticker] = hist
                                    successful_tickers.append(ticker)
                                    if ticker in failed_tickers:
                                        failed_tickers.remove(ticker)
                            except Exception as individual_error:
                                # Individual retry also failed - skip this ticker
                                continue
                
                # Convert all_data dict to a structure we can process
                data = all_data if all_data else None
            else:
                # Small enough to do in one batch
                successful_tickers = []
                failed_tickers = []
                try:
                    data = yf.download(
                        tickers,
                        start=start_date.strftime('%Y-%m-%d'),
                        end=end_date.strftime('%Y-%m-%d'),
                        progress=False,
                        group_by='ticker',
                        threads=True
                    )
                    if logs is not None:
                        logs.append(f"   ✓ Successfully downloaded batch data")
                    # Track successful tickers
                    if data is not None and not data.empty:
                        for ticker in tickers:
                            try:
                                if hasattr(data.columns, 'get_level_values') and ticker in data.columns.get_level_values(1):
                                    successful_tickers.append(ticker)
                                elif ticker in data.columns:
                                    successful_tickers.append(ticker)
                                else:
                                    failed_tickers.append(ticker)
                            except:
                                failed_tickers.append(ticker)
                except Exception as e:
                    # If batch download fails, fall back to individual requests
                    if logs is not None:
                        logs.append(f"   ⚠️  Batch download failed, using individual requests (slower)...")
                    print(f"[YFINANCE BATCH] Batch download failed: {e}, falling back to individual requests")
                    data = None
                    failed_tickers = tickers.copy()
            
            losers = []
            bearish_date_only = bearish_date.date()
            
            # Ensure variables are initialized
            if 'successful_tickers' not in locals():
                successful_tickers = []
            if 'failed_tickers' not in locals():
                failed_tickers = []
            
            if logs is not None:
                logs.append(f"   🔍 Analyzing price changes for {bearish_date.strftime('%Y-%m-%d')}...")
                if len(successful_tickers) > 0:
                    logs.append(f"   ✓ Successfully retrieved data for {len(successful_tickers)} tickers")
                if len(failed_tickers) > 0:
                    logs.append(f"   ⚠️  Failed to retrieve data for {len(failed_tickers)} tickers (likely certificate/network issues)")
            
            # Check if data is a dict (from batched processing) or DataFrame
            if isinstance(data, dict) and len(data) > 0:
                # Process batched data (dict of DataFrames)
                for ticker in tickers:
                    try:
                        if ticker not in companies or ticker not in data:
                            continue
                        
                        ticker_data = data[ticker]
                        
                        if ticker_data.empty:
                            continue
                        
                        # Find bearish date and previous day
                        bearish_close = None
                        prev_close = None
                        
                        for date_idx, row in ticker_data.iterrows():
                            # Handle different date index types
                            if hasattr(date_idx, 'date'):
                                date_only = date_idx.date()
                            elif hasattr(date_idx, 'to_pydatetime'):
                                date_only = date_idx.to_pydatetime().date()
                            else:
                                try:
                                    date_only = datetime.fromtimestamp(date_idx).date()
                                except:
                                    continue
                            
                            # Get Close price
                            close_col = 'Close'
                            if close_col not in row.index:
                                # Try to find close column (case insensitive)
                                close_col = next((col for col in row.index if 'close' in str(col).lower()), None)
                                if close_col is None:
                                    continue
                            
                            close_price = float(row[close_col])
                            
                            if date_only == bearish_date_only:
                                bearish_close = close_price
                            elif date_only < bearish_date_only:
                                # This is a previous trading day (use the most recent one)
                                if prev_close is None:
                                    prev_close = close_price
                        
                        if bearish_close is None or prev_close is None or prev_close == 0:
                            continue
                        
                        # Calculate percentage drop
                        pct_drop = ((bearish_close - prev_close) / prev_close) * 100
                        
                        # Only include stocks that dropped
                        if pct_drop < 0:
                            losers.append((ticker, pct_drop, companies[ticker]))
                    
                    except Exception as e:
                        # Skip this ticker if there's an error
                        continue
            
            elif data is not None and not data.empty:
                # Process single batch DataFrame
                # When group_by='ticker', yfinance returns a MultiIndex DataFrame
                # Structure: (Date, Ticker) -> (Open, High, Low, Close, Volume, etc.)
                
                for ticker in tickers:
                    try:
                        if ticker not in companies:
                            continue
                        
                        # Get data for this ticker
                        if len(tickers) > 1:
                            # MultiIndex structure: data.loc[:, (slice(None), ticker)]
                            # Or simpler: check if ticker is in columns
                            if hasattr(data.columns, 'get_level_values') and ticker in data.columns.get_level_values(1):
                                ticker_data = data.xs(ticker, level=1, axis=1)
                            else:
                                # Try direct access
                                try:
                                    ticker_data = data[ticker]
                                except:
                                    continue
                        else:
                            ticker_data = data
                        
                        if ticker_data.empty:
                            continue
                        
                        # Find bearish date and previous day
                        bearish_close = None
                        prev_close = None
                        
                        for date_idx, row in ticker_data.iterrows():
                            # Handle different date index types
                            if hasattr(date_idx, 'date'):
                                date_only = date_idx.date()
                            elif hasattr(date_idx, 'to_pydatetime'):
                                date_only = date_idx.to_pydatetime().date()
                            else:
                                try:
                                    date_only = datetime.fromtimestamp(date_idx).date()
                                except:
                                    continue
                            
                            # Get Close price
                            close_col = 'Close'
                            if close_col not in row.index:
                                # Try to find close column (case insensitive)
                                close_col = next((col for col in row.index if 'close' in str(col).lower()), None)
                                if close_col is None:
                                    continue
                            
                            close_price = float(row[close_col])
                            
                            if date_only == bearish_date_only:
                                bearish_close = close_price
                            elif date_only < bearish_date_only:
                                # This is a previous trading day (use the most recent one)
                                if prev_close is None:
                                    prev_close = close_price
                        
                        if bearish_close is None or prev_close is None or prev_close == 0:
                            continue
                        
                        # Calculate percentage drop
                        pct_drop = ((bearish_close - prev_close) / prev_close) * 100
                        
                        # Only include stocks that dropped
                        if pct_drop < 0:
                            losers.append((ticker, pct_drop, companies[ticker]))
                    
                    except Exception as e:
                        # Skip this ticker if there's an error
                        continue
            else:
                # Fallback: individual requests (slower but more reliable)
                for ticker in tickers:
                    try:
                        stock = yf.Ticker(ticker)
                        hist = stock.history(start=start_date.strftime('%Y-%m-%d'), 
                                           end=end_date.strftime('%Y-%m-%d'))
                        
                        if hist.empty:
                            continue
                        
                        # Find bearish date and previous day
                        bearish_close = None
                        prev_close = None
                        
                        for date_idx, row in hist.iterrows():
                            date_only = date_idx.date() if hasattr(date_idx, 'date') else date_idx
                            
                            if date_only == bearish_date_only:
                                bearish_close = float(row['Close'])
                            elif date_only < bearish_date_only:
                                if prev_close is None:
                                    prev_close = float(row['Close'])
                        
                        if bearish_close is None or prev_close is None or prev_close == 0:
                            continue
                        
                        pct_drop = ((bearish_close - prev_close) / prev_close) * 100
                        
                        if pct_drop < 0:
                            losers.append((ticker, pct_drop, companies[ticker]))
                    
                    except Exception as e:
                        continue
            
            # Sort by percentage drop (most negative first)
            losers.sort(key=lambda x: x[1])
            
            if logs is not None:
                logs.append(f"   ✓ Found {len(losers)} stocks with drops")
                if len(failed_tickers) > 0:
                    ssl_error_count = len(failed_tickers)
                    if len(losers) == 0:
                        logs.append(f"   ⚠️  All {ssl_error_count} tickers failed with SSL errors")
                        logs.append(f"   🔄 Falling back to Prixe.io for failed tickers...")
                        # Fallback to Prixe.io for failed tickers
                        try:
                            prixe_losers = self._get_top_losers_prixe_fallback(failed_tickers, bearish_date, companies, logs)
                            if prixe_losers:
                                losers.extend(prixe_losers)
                                logs.append(f"   ✓ Prixe.io fallback found {len(prixe_losers)} additional stocks with drops")
                        except Exception as e:
                            logs.append(f"   ⚠️  Prixe.io fallback also failed: {str(e)[:50]}...")
                    else:
                        logs.append(f"   ℹ️  Note: {ssl_error_count} tickers failed to download (SSL errors), but {len(successful_tickers)} succeeded")
                else:
                    logs.append(f"   ✅ Successfully downloaded data for {len(successful_tickers)} tickers")
            
            # Re-sort after adding Prixe.io fallback results
            if losers:
                losers.sort(key=lambda x: x[1])
            
            return losers
            
        except Exception as e:
            error_msg = f"Error in get_top_losers_yfinance: {e}"
            if logs is not None:
                logs.append(f"   ❌ {error_msg}")
            print(error_msg)
            import traceback
            traceback.print_exc()
            return []
    
    def _count_trading_days_between(self, start_date: datetime, end_date: datetime) -> int:
        """Count trading days (weekdays) between start_date (exclusive) and end_date (inclusive)."""
        if not start_date or not end_date or end_date <= start_date:
            return 0
        
        current = start_date + timedelta(days=1)
        count = 0
        while current <= end_date:
            if current.weekday() < 5:  # Monday–Friday
                count += 1
            current += timedelta(days=1)
        return count
    
    def analyze_recovery_history(self, price_history: List[Dict], pct_threshold: float, bearish_date_str: str, events: List[Dict] = None) -> List[Dict]:
        """Analyze 120 days of price history to find similar drops and recovery times
        
        Args:
            price_history: List of price data points (sorted by date)
            pct_threshold: Minimum drop percentage (e.g., -5.0 for -5%)
            bearish_date_str: Current bearish date (exclude this from analysis)
            events: List of events (earnings/dividends) from 120 days before bearish_date to bearish_date
        
        Returns:
            Dict with:
              - 'items': list of per-drop dicts (drop_date, drop_pct, recovery_days, recovery_trading_days, recovery_date, recovery_pct, event_info)
              - 'summary': aggregated metrics for 7 trading days and 40 calendar days
        """
        recovery_items: List[Dict] = []
        
        if not price_history or len(price_history) < 2:
            return {
                'items': [],
                'summary': {
                    'within_7_trading_days': {
                        'count_recovered': 0,
                        'total_events': 0,
                        'percentage': 0.0,
                    },
                    'within_40_days': {
                        'count_recovered': 0,
                        'total_events': 0,
                        'percentage': 0.0,
                        'avg_recovery_pct': 0.0,
                        'avg_days_to_recover': 0.0,
                    },
                },
            }
        
        # Threshold range: ±1% (e.g., if -5%, find -4% and above/worse)
        # For negative thresholds, "above" means more negative (worse drops)
        # So if threshold is -5%, we find drops <= -4% (i.e., -4% or worse)
        max_threshold = pct_threshold + 1.0  # e.g., -4% for threshold of -5%
        
        # Only analyze dates BEFORE the current bearish date
        sorted_history = sorted(price_history, key=lambda x: x.get('date', ''))
        
        for i in range(1, len(sorted_history)):
            current = sorted_history[i]
            prev = sorted_history[i-1]
            
            current_date = current.get('date', '')
            current_price = current.get('price')
            prev_price = prev.get('price')
            
            # Skip if at or after bearish date or missing data
            if not current_date or current_date >= bearish_date_str or not current_price or not prev_price:
                continue
            
            # Calculate drop percentage (day-over-day)
            drop_pct = ((current_price - prev_price) / prev_price) * 100
            
                # Check if drop matches threshold: drop_pct <= (threshold + 1%)
            # For -5% threshold, this means drop_pct <= -4% (finds -4% and worse)
            if drop_pct <= max_threshold:
                # Find recovery (2% bounce from drop price)
                drop_price = current_price
                recovery_target = drop_price * 1.02  # 2% recovery from drop price
                
                recovery_date = None
                recovery_days = None
                recovery_pct = None  # Initialize recovery_pct
                
                # Look forward from drop date to find recovery
                for j in range(i + 1, len(sorted_history)):
                    future_entry = sorted_history[j]
                    future_date = future_entry.get('date', '')
                    future_price = future_entry.get('price')
                    
                    if not future_date or not future_price:
                        continue
                    
                    # Stop if we reach current bearish date
                    if future_date >= bearish_date_str:
                        break
                    
                    # Check if recovered by 2% (price >= drop_price * 1.02)
                    if future_price >= recovery_target:
                        # Calculate days between drop and recovery
                        try:
                            drop_dt = datetime.strptime(current_date, '%Y-%m-%d')
                            recovery_dt = datetime.strptime(future_date, '%Y-%m-%d')
                            recovery_days = (recovery_dt - drop_dt).days
                            recovery_date = future_date
                            # Calculate recovery percentage (total recovery from drop price)
                            recovery_pct = ((future_price - drop_price) / drop_price) * 100
                        except ValueError:
                            recovery_pct = None
                        break
                
                # Compute trading days to recover if we have both dates
                recovery_trading_days = None
                if recovery_days is not None and recovery_date is not None:
                    try:
                        drop_dt_td = datetime.strptime(current_date, '%Y-%m-%d')
                        recovery_dt_td = datetime.strptime(recovery_date, '%Y-%m-%d')
                        recovery_trading_days = self._count_trading_days_between(drop_dt_td, recovery_dt_td)
                    except ValueError:
                        recovery_trading_days = None
                
                # Event matching is now done in frontend - no longer needed here
                recovery_item = {
                    'drop_date': current_date,
                    'drop_pct': round(drop_pct, 2),
                    'recovery_days': recovery_days,
                    'recovery_trading_days': recovery_trading_days,
                    'recovery_date': recovery_date,
                    'recovery_pct': round(recovery_pct, 2) if recovery_pct is not None else None
                }
                recovery_items.append(recovery_item)
        
        # Sort by drop_date (most recent first)
        recovery_items.sort(key=lambda x: x.get('drop_date', ''), reverse=True)
        
        total_drops = len(recovery_items)
        
        # Debug: Count how many drops recovered within 7 trading days vs didn't
        recovered_within_7 = sum(1 for item in recovery_items 
                                 if item.get('recovery_trading_days') is not None 
                                 and item.get('recovery_trading_days') <= 7)
        didnt_recover_within_7 = total_drops - recovered_within_7
        items_with_events = sum(1 for item in recovery_items if item.get('event_info') is not None)
        print(f"[RECOVERY HISTORY SUMMARY] Total drops: {total_drops}, Recovered within 7 trading days: {recovered_within_7}, Didn't recover within 7: {didnt_recover_within_7}, Items with events: {items_with_events}")
        
        # 7-trading-day metric
        recovered_within_7_trading = [
            item for item in recovery_items
            if item.get('recovery_pct') is not None
            and item.get('recovery_trading_days') is not None
            and item['recovery_trading_days'] <= 7
        ]
        
        # 40-calendar-day metric (existing behavior)
        recovered_within_40_days = [
            item for item in recovery_items
            if item.get('recovery_pct') is not None
            and item.get('recovery_days') is not None
            and item['recovery_days'] <= 40
        ]
        
        all_recovered_calendar = [
            item for item in recovery_items
            if item.get('recovery_pct') is not None
            and item.get('recovery_days') is not None
        ]
        
        # Aggregate stats
        count_7 = len(recovered_within_7_trading)
        count_40 = len(recovered_within_40_days)
        
        pct_7 = (count_7 / total_drops * 100.0) if total_drops > 0 else 0.0
        pct_40 = (count_40 / total_drops * 100.0) if total_drops > 0 else 0.0
        
        avg_recovery_pct_40 = (
            sum(item['recovery_pct'] for item in recovered_within_40_days) / count_40
            if count_40 > 0 else 0.0
        )
        
        avg_days_to_recover = (
            sum(item['recovery_days'] for item in all_recovered_calendar) / len(all_recovered_calendar)
            if all_recovered_calendar else 0.0
        )
        
        summary = {
            'within_7_trading_days': {
                'count_recovered': count_7,
                'total_events': total_drops,
                'percentage': round(pct_7, 1),
            },
            'within_40_days': {
                'count_recovered': count_40,
                'total_events': total_drops,
                'percentage': round(pct_40, 1),
                'avg_recovery_pct': round(avg_recovery_pct_40, 1),
                'avg_days_to_recover': round(avg_days_to_recover, 1),
            },
        }
        
        return {
            'items': recovery_items,
            'summary': summary,
        }
    
    def _calculate_technical_indicators(self, price_history: List[Dict], current_price: float, bearish_price: float) -> Dict[str, any]:
        """Calculate technical indicators from price history
        
        Args:
            price_history: List of price data points
            current_price: Current/target price
            bearish_price: Price on bearish date
            
        Returns:
            Dictionary with technical indicators
        """
        if not price_history or len(price_history) < 5:
            return {}
        
        prices = [p['price'] for p in price_history if p.get('price') is not None]
        if len(prices) < 5:
            return {}
        
        indicators = {}
        
        # 1. RSI (14-period) - Wilder's Smoothing Method (Industry Standard)
        def calculate_rsi(prices_list, period=14):
            """Calculate RSI using Wilder's smoothing method (industry standard)
            
            Wilder's RSI uses exponential smoothing:
            - First period: Simple average of first 14 periods
            - Subsequent periods: avg = (prev_avg × (period-1) + current_value) / period
            """
            if len(prices_list) < period + 1:
                return None
            
            # Calculate price changes (gains and losses)
            changes = []
            for i in range(1, len(prices_list)):
                change = prices_list[i] - prices_list[i-1]
                changes.append(change)
            
            if len(changes) < period:
                return None
            
            # Step 1: Calculate initial average gain and loss (first 14 periods)
            initial_gains = [max(0, change) for change in changes[:period]]
            initial_losses = [max(0, -change) for change in changes[:period]]
            
            avg_gain = sum(initial_gains) / period
            avg_loss = sum(initial_losses) / period
            
            # Step 2: Apply Wilder's smoothing for remaining periods
            # Formula: avg = (prev_avg × (period-1) + current_value) / period
            for i in range(period, len(changes)):
                current_gain = max(0, changes[i])
                current_loss = max(0, -changes[i])
                
                # Wilder's smoothing: (prev_avg × 13 + current) / 14
                avg_gain = (avg_gain * (period - 1) + current_gain) / period
                avg_loss = (avg_loss * (period - 1) + current_loss) / period
            
            # Step 3: Calculate RSI
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return round(rsi, 1)
        
        indicators['rsi'] = calculate_rsi(prices)
        
        # 2. Moving Averages
        def calculate_sma(prices_list, period):
            if len(prices_list) < period:
                return None
            return sum(prices_list[-period:]) / period
        
        indicators['sma_5'] = round(calculate_sma(prices, 5), 2) if len(prices) >= 5 else None
        indicators['sma_10'] = round(calculate_sma(prices, 10), 2) if len(prices) >= 10 else None
        indicators['sma_20'] = round(calculate_sma(prices, 20), 2) if len(prices) >= 20 else None
        
        # 3. Price vs Moving Average
        if indicators['sma_20']:
            price_vs_ma20 = ((current_price - indicators['sma_20']) / indicators['sma_20']) * 100
            indicators['price_vs_ma20_pct'] = round(price_vs_ma20, 2)
        else:
            indicators['price_vs_ma20_pct'] = None
        
        # 4. Support/Resistance Levels (Improved Algorithm with Clustering and Significance Scoring)
        # Based on industry standards: cluster nearby levels, score by significance, ensure minimum separation
        
        def find_local_extrema_with_data(prices_list, window=3, min_swing_pct=1.0):
            """Find significant local minima and maxima with touch counts and reversal magnitudes
            
            Args:
                prices_list: List of prices
                window: Number of periods on each side to check (default 3)
                min_swing_pct: Minimum percentage swing to consider significant (default 1.0%)
            
            Returns:
                Tuple of (local_lows_dict, local_highs_dict) where each dict contains:
                {price: {'touches': count, 'avg_reversal_magnitude': pct}}
            """
            local_lows = {}  # {price: {'touches': count, 'avg_reversal_magnitude': pct}}
            local_highs = {}  # {price: {'touches': count, 'avg_reversal_magnitude': pct}}
            
            if len(prices_list) < window * 2 + 1:
                window = 1
            
            # Find local minima and maxima with wider window
            for i in range(window, len(prices_list) - window):
                price = prices_list[i]
                
                # Check if it's a local low (lower than neighbors within window)
                is_local_low = True
                is_local_high = True
                
                for j in range(i - window, i + window + 1):
                    if j != i:
                        if prices_list[j] <= price:
                            is_local_low = False
                        if prices_list[j] >= price:
                            is_local_high = False
                
                # Calculate swing percentage for significance
                if is_local_low:
                    nearby_highs = [prices_list[j] for j in range(max(0, i - window * 2), min(len(prices_list), i + window * 2 + 1)) if j != i]
                    if nearby_highs:
                        avg_nearby_high = sum(nearby_highs) / len(nearby_highs)
                        swing_pct = ((avg_nearby_high - price) / price) * 100
                        if swing_pct >= min_swing_pct:
                            rounded_price = round(price, 2)
                            if rounded_price not in local_lows:
                                local_lows[rounded_price] = {'touches': 0, 'reversal_magnitudes': []}
                            local_lows[rounded_price]['touches'] += 1
                            local_lows[rounded_price]['reversal_magnitudes'].append(swing_pct)
                
                if is_local_high:
                    nearby_lows = [prices_list[j] for j in range(max(0, i - window * 2), min(len(prices_list), i + window * 2 + 1)) if j != i]
                    if nearby_lows:
                        avg_nearby_low = sum(nearby_lows) / len(nearby_lows)
                        swing_pct = ((price - avg_nearby_low) / avg_nearby_low) * 100
                        if swing_pct >= min_swing_pct:
                            rounded_price = round(price, 2)
                            if rounded_price not in local_highs:
                                local_highs[rounded_price] = {'touches': 0, 'reversal_magnitudes': []}
                            local_highs[rounded_price]['touches'] += 1
                            local_highs[rounded_price]['reversal_magnitudes'].append(swing_pct)
            
            # Also check first and last prices if they're significant
            if len(prices_list) >= 3:
                # First price
                if prices_list[0] < min(prices_list[1:min(4, len(prices_list))]):
                    nearby_highs = prices_list[1:min(4, len(prices_list))]
                    if nearby_highs:
                        avg_high = sum(nearby_highs) / len(nearby_highs)
                        swing_pct = ((avg_high - prices_list[0]) / prices_list[0]) * 100
                        if swing_pct >= min_swing_pct:
                            rounded_price = round(prices_list[0], 2)
                            if rounded_price not in local_lows:
                                local_lows[rounded_price] = {'touches': 0, 'reversal_magnitudes': []}
                            local_lows[rounded_price]['touches'] += 1
                            local_lows[rounded_price]['reversal_magnitudes'].append(swing_pct)
                
                if prices_list[0] > max(prices_list[1:min(4, len(prices_list))]):
                    nearby_lows = prices_list[1:min(4, len(prices_list))]
                    if nearby_lows:
                        avg_low = sum(nearby_lows) / len(nearby_lows)
                        swing_pct = ((prices_list[0] - avg_low) / avg_low) * 100
                        if swing_pct >= min_swing_pct:
                            rounded_price = round(prices_list[0], 2)
                            if rounded_price not in local_highs:
                                local_highs[rounded_price] = {'touches': 0, 'reversal_magnitudes': []}
                            local_highs[rounded_price]['touches'] += 1
                            local_highs[rounded_price]['reversal_magnitudes'].append(swing_pct)
                
                # Last price
                if prices_list[-1] < min(prices_list[max(0, len(prices_list)-4):-1]):
                    nearby_highs = prices_list[max(0, len(prices_list)-4):-1]
                    if nearby_highs:
                        avg_high = sum(nearby_highs) / len(nearby_highs)
                        swing_pct = ((avg_high - prices_list[-1]) / prices_list[-1]) * 100
                        if swing_pct >= min_swing_pct:
                            rounded_price = round(prices_list[-1], 2)
                            if rounded_price not in local_lows:
                                local_lows[rounded_price] = {'touches': 0, 'reversal_magnitudes': []}
                            local_lows[rounded_price]['touches'] += 1
                            local_lows[rounded_price]['reversal_magnitudes'].append(swing_pct)
                
                if prices_list[-1] > max(prices_list[max(0, len(prices_list)-4):-1]):
                    nearby_lows = prices_list[max(0, len(prices_list)-4):-1]
                    if nearby_lows:
                        avg_low = sum(nearby_lows) / len(nearby_lows)
                        swing_pct = ((prices_list[-1] - avg_low) / avg_low) * 100
                        if swing_pct >= min_swing_pct:
                            rounded_price = round(prices_list[-1], 2)
                            if rounded_price not in local_highs:
                                local_highs[rounded_price] = {'touches': 0, 'reversal_magnitudes': []}
                            local_highs[rounded_price]['touches'] += 1
                            local_highs[rounded_price]['reversal_magnitudes'].append(swing_pct)
            
            # Calculate average reversal magnitudes
            for price in local_lows:
                if local_lows[price]['reversal_magnitudes']:
                    local_lows[price]['avg_reversal_magnitude'] = sum(local_lows[price]['reversal_magnitudes']) / len(local_lows[price]['reversal_magnitudes'])
                else:
                    local_lows[price]['avg_reversal_magnitude'] = 0
            
            for price in local_highs:
                if local_highs[price]['reversal_magnitudes']:
                    local_highs[price]['avg_reversal_magnitude'] = sum(local_highs[price]['reversal_magnitudes']) / len(local_highs[price]['reversal_magnitudes'])
                else:
                    local_highs[price]['avg_reversal_magnitude'] = 0
            
            return local_lows, local_highs
        
        def cluster_levels(levels_dict, tolerance_pct=1.0):
            """Cluster nearby price levels within tolerance percentage
            
            Args:
                levels_dict: Dict of {price: data}
                tolerance_pct: Percentage tolerance for clustering (default 1.0%)
            
            Returns:
                List of clusters, each with {'price': avg_price, 'touches': sum, 'avg_reversal_magnitude': avg}
            """
            if not levels_dict:
                return []
            
            sorted_prices = sorted(levels_dict.keys())
            clusters = []
            
            for price in sorted_prices:
                # Check if this price belongs to an existing cluster
                clustered = False
                for cluster in clusters:
                    # Check if price is within tolerance of cluster center
                    cluster_center = cluster['price']
                    tolerance = cluster_center * (tolerance_pct / 100)
                    if abs(price - cluster_center) <= tolerance:
                        # Add to existing cluster
                        # Recalculate cluster center as weighted average
                        total_touches = cluster['touches'] + levels_dict[price]['touches']
                        cluster['price'] = (cluster['price'] * cluster['touches'] + price * levels_dict[price]['touches']) / total_touches
                        cluster['touches'] = total_touches
                        # Average reversal magnitudes
                        cluster['avg_reversal_magnitude'] = (
                            cluster['avg_reversal_magnitude'] * (cluster['touches'] - levels_dict[price]['touches']) +
                            levels_dict[price]['avg_reversal_magnitude'] * levels_dict[price]['touches']
                        ) / total_touches
                        clustered = True
                        break
                
                if not clustered:
                    # Create new cluster
                    clusters.append({
                        'price': price,
                        'touches': levels_dict[price]['touches'],
                        'avg_reversal_magnitude': levels_dict[price]['avg_reversal_magnitude']
                    })
            
            return clusters
        
        def score_clusters(clusters):
            """Score clusters by significance
            
            Score = (touches * 2) + (avg_reversal_magnitude / 10)
            Higher score = more significant level
            
            Args:
                clusters: List of cluster dicts
            
            Returns:
                List of clusters with added 'score' field, sorted by score (descending)
            """
            for cluster in clusters:
                # Score formula: touches are weighted 2x, reversal magnitude divided by 10
                cluster['score'] = (cluster['touches'] * 2) + (cluster['avg_reversal_magnitude'] / 10)
            
            # Sort by score descending
            clusters.sort(key=lambda x: x['score'], reverse=True)
            return clusters
        
        # Find local extrema with data
        local_lows_dict, local_highs_dict = find_local_extrema_with_data(prices, window=3, min_swing_pct=1.0)
        
        # Cluster nearby levels
        clustered_lows = cluster_levels(local_lows_dict, tolerance_pct=1.0)
        clustered_highs = cluster_levels(local_highs_dict, tolerance_pct=1.0)
        
        # Score clusters by significance
        scored_lows = score_clusters(clustered_lows)
        scored_highs = score_clusters(clustered_highs)
        
        # Find support (below current_price) - use MOST SIGNIFICANT, not nearest
        min_separation_pct = 3.0  # Minimum 3% separation between support and resistance
        support_candidates = [c for c in scored_lows if c['price'] < current_price]
        
        if support_candidates:
            # Use most significant support (highest score)
            nearest_support = support_candidates[0]['price']
        else:
            # Fallback: use 5% below current price
            price_range = max(prices) - min(prices)
            if price_range > 0:
                fallback_support = current_price * 0.95
                min_support = max(min(prices) * 0.99, current_price * 0.99)
                nearest_support = max(min_support, fallback_support)
                if nearest_support >= current_price:
                    nearest_support = current_price * 0.99
            else:
                nearest_support = current_price * 0.99 if prices else None
        
        # Find resistance (above current_price) - use MOST SIGNIFICANT, not nearest
        resistance_candidates = [c for c in scored_highs if c['price'] > current_price]
        
        if resistance_candidates:
            # Use most significant resistance (highest score)
            nearest_resistance = resistance_candidates[0]['price']
        else:
            # Fallback: use 5% above current price
            price_range = max(prices) - min(prices)
            if price_range > 0:
                fallback_resistance = current_price * 1.05
                max_resistance = min(max(prices) * 1.01, current_price * 1.01)
                nearest_resistance = min(max_resistance, fallback_resistance)
                if nearest_resistance <= current_price:
                    nearest_resistance = current_price * 1.01
            else:
                nearest_resistance = current_price * 1.01 if prices else None
        
        # Ensure minimum separation between support and resistance
        if nearest_support and nearest_resistance:
            separation_pct = ((nearest_resistance - nearest_support) / nearest_support) * 100
            
            if separation_pct < min_separation_pct:
                # If too close, try to find better levels
                # Try next most significant support (further down)
                if len(support_candidates) > 1:
                    for candidate in support_candidates[1:]:
                        new_separation = ((nearest_resistance - candidate['price']) / candidate['price']) * 100
                        if new_separation >= min_separation_pct:
                            nearest_support = candidate['price']
                            break
                
                # If still too close, try next most significant resistance (further up)
                separation_pct = ((nearest_resistance - nearest_support) / nearest_support) * 100
                if separation_pct < min_separation_pct and len(resistance_candidates) > 1:
                    for candidate in resistance_candidates[1:]:
                        new_separation = ((candidate['price'] - nearest_support) / nearest_support) * 100
                        if new_separation >= min_separation_pct:
                            nearest_resistance = candidate['price']
                            break
                
                # Final fallback: if still too close, use percentage-based separation
                separation_pct = ((nearest_resistance - nearest_support) / nearest_support) * 100
                if separation_pct < min_separation_pct:
                    # Adjust to ensure minimum separation
                    target_support = nearest_resistance / (1 + min_separation_pct / 100)
                    if target_support < current_price and target_support > min(prices) * 0.9:
                        nearest_support = target_support
                    else:
                        # Or adjust resistance
                        target_resistance = nearest_support * (1 + min_separation_pct / 100)
                        if target_resistance > current_price and target_resistance < max(prices) * 1.1:
                            nearest_resistance = target_resistance
        
        indicators['nearest_support'] = round(nearest_support, 2) if nearest_support else None
        indicators['nearest_resistance'] = round(nearest_resistance, 2) if nearest_resistance else None
        
        if nearest_support:
            support_distance = ((current_price - nearest_support) / nearest_support) * 100
            indicators['support_distance_pct'] = round(support_distance, 2)
        else:
            indicators['support_distance_pct'] = None
        
        if nearest_resistance:
            resistance_distance = ((nearest_resistance - current_price) / current_price) * 100
            indicators['resistance_distance_pct'] = round(resistance_distance, 2)
        else:
            indicators['resistance_distance_pct'] = None
        
        # 5. Trend (based on moving averages)
        if indicators['sma_5'] and indicators['sma_10'] and indicators['sma_20']:
            if indicators['sma_5'] > indicators['sma_10'] > indicators['sma_20']:
                indicators['trend'] = 'Bullish'
            elif indicators['sma_5'] < indicators['sma_10'] < indicators['sma_20']:
                indicators['trend'] = 'Bearish'
            else:
                indicators['trend'] = 'Neutral'
        else:
            indicators['trend'] = 'Unknown'
        
        # 6. MACD (simplified - using EMA approximation)
        def calculate_ema(prices_list, period):
            if len(prices_list) < period:
                return None
            multiplier = 2 / (period + 1)
            ema = sum(prices_list[:period]) / period
            for price in prices_list[period:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
            return ema
        
        ema_12 = calculate_ema(prices, 12) if len(prices) >= 12 else None
        ema_26 = calculate_ema(prices, 26) if len(prices) >= 26 else None
        
        if ema_12 and ema_26:
            macd_line = ema_12 - ema_26
            # Simplified signal line (9-period EMA of MACD)
            # For simplicity, we'll use a basic comparison
            if macd_line > 0:
                indicators['macd_signal'] = 'Bullish'
            else:
                indicators['macd_signal'] = 'Bearish'
            indicators['macd_value'] = round(macd_line, 2)
        else:
            indicators['macd_signal'] = 'Unknown'
            indicators['macd_value'] = None
        
        return indicators
    
    def extract_price_from_history(self, price_history: List[Dict], target_date: datetime) -> Tuple[Optional[float], Optional[str]]:
        """Extract price from history list for a specific date
        
        Returns: (price, actual_date_used)
        For target_date: Prefers exact match, then closest date ON or BEFORE target_date
        (not after, as we want the price as of the target date, not future prices)
        
        Uses date string comparison to avoid timezone issues.
        """
        if not price_history:
            return None, None
        
        target_date_str = target_date.strftime('%Y-%m-%d')
        
        # Try exact date match first
        for entry in price_history:
            entry_date = entry.get('date')
            if entry_date == target_date_str:
                return entry.get('price'), target_date_str
        
        # If no exact match, find closest date ON or BEFORE target_date (for market holidays/weekends)
        # Use date string comparison to avoid timezone issues
        closest_price = None
        closest_date = None
        closest_date_obj = None
        
        for entry in price_history:
            entry_date = entry.get('date')
            price = entry.get('price')
            if price is None or not entry_date:
                continue
            
            # Only consider dates on or before target_date (string comparison works for YYYY-MM-DD format)
            if entry_date <= target_date_str:
                # Parse the entry date to compare properly
                try:
                    entry_date_obj = datetime.strptime(entry_date, '%Y-%m-%d')
                    # If this is the first valid date, or it's closer to target_date
                    if closest_date_obj is None or entry_date_obj > closest_date_obj:
                        closest_date_obj = entry_date_obj
                        closest_price = float(price)
                        closest_date = entry_date
                except (ValueError, TypeError):
                    # Skip entries with invalid date format
                    continue
        
        # If we found a date, return it
        if closest_price is not None and closest_date is not None:
            return closest_price, closest_date
        
        # Fallback: if no date found on or before target_date, use the most recent date available
        # (This shouldn't happen if data is correct, but provides a safety net)
        if not price_history:
            return None, None
        
        # Find the most recent date in history
        latest_entry = None
        latest_date_obj = None
        for entry in price_history:
            entry_date = entry.get('date')
            price = entry.get('price')
            if price is None or not entry_date:
                continue
            try:
                entry_date_obj = datetime.strptime(entry_date, '%Y-%m-%d')
                if latest_date_obj is None or entry_date_obj > latest_date_obj:
                    latest_date_obj = entry_date_obj
                    latest_entry = entry
            except (ValueError, TypeError):
                continue
        
        if latest_entry:
            return latest_entry.get('price'), latest_entry.get('date')
        
        return None, None
    
    def _get_recovery_strength(self, industry: str) -> Dict[str, any]:
        """Get recovery strength rating for an industry
        
        Returns:
            Dictionary with 'stars' (str), 'rating' (int 1-4), and 'reason' (str)
        """
        recovery_map = {
            'Technology': {'stars': '⭐⭐⭐⭐', 'rating': 4, 'reason': 'High growth, innovation, investor optimism rebounds fast'},
            'Consumer': {'stars': '⭐⭐⭐⭐', 'rating': 4, 'reason': 'Spending rebounds as consumer confidence returns'},
            'Consumer Discretionary': {'stars': '⭐⭐⭐⭐', 'rating': 4, 'reason': 'Spending rebounds as consumer confidence returns'},
            'Industrial': {'stars': '⭐⭐⭐⭐', 'rating': 4, 'reason': 'Business reinvestment and infrastructure spending surge'},
            'Industrials': {'stars': '⭐⭐⭐⭐', 'rating': 4, 'reason': 'Business reinvestment and infrastructure spending surge'},
            'Materials': {'stars': '⭐⭐⭐', 'rating': 3, 'reason': 'Demand rises with economic activity'},
            'Communication': {'stars': '⭐⭐⭐', 'rating': 3, 'reason': 'Ad spending and media usage rebound'},
            'Communication Services': {'stars': '⭐⭐⭐', 'rating': 3, 'reason': 'Ad spending and media usage rebound'},
            'Healthcare': {'stars': '⭐⭐', 'rating': 2, 'reason': 'Stable, but not explosive — more defensive'},
            'Utilities': {'stars': '⭐⭐', 'rating': 2, 'reason': 'Defensive, steady — not a big rebound sector'},
            'Financials': {'stars': '⭐⭐', 'rating': 2, 'reason': 'Depends on interest rates and credit conditions'},
            'Energy': {'stars': '⭐⭐', 'rating': 2, 'reason': 'Volatile — tied to oil/gas prices, not always cyclical'},
            'Real Estate': {'stars': '⭐', 'rating': 1, 'reason': 'Sensitive to rates — slow to recover'},
            'Consumer Staples': {'stars': '⭐⭐', 'rating': 2, 'reason': 'Defensive, stable — limited recovery potential'},
        }
        
        # Default for unknown industries
        default = {'stars': '⭐⭐', 'rating': 2, 'reason': 'Moderate recovery potential'}
        
        return recovery_map.get(industry, default)
    
    def get_bearish_analytics(
        self,
        bearish_date: datetime,
        target_date: datetime,
        industry: Optional[str] = None,
        filter_type: str = 'bearish',
        pct_threshold: Optional[float] = None,
        flexible_days: int = 0,
        ticker_filter: Optional[str] = None
    ) -> tuple[List[Dict], List[str]]:
        """Get top losing large-cap stocks on bearish date and their recovery to target date
        
        Args:
            bearish_date: Date when stocks dropped (datetime)
            target_date: Date to check recovery (datetime)
            industry: Optional industry filter (e.g., "Technology", "Healthcare")
            filter_type: 'bearish' to filter by drop percentage, 'bullish' to filter by recovery percentage
            pct_threshold: Minimum percentage change to include (e.g., -5 for bearish drop > 5%, 5 for bullish recovery > 5%)
            
        Returns:
            Tuple of (results list, logs list)
        """
        logs = []
        try:
            # Helper function to append and print logs (for real-time streaming)
            def add_log(message):
                logs.append(message)
                print(message)  # Print to stdout for real-time streaming
            
            add_log("🚀 Starting Optimized Bearish Analytics Analysis")
            add_log(f"📅 Bearish Date: {bearish_date.strftime('%Y-%m-%d')}")
            add_log(f"📅 Target Date: {target_date.strftime('%Y-%m-%d')}")
            add_log(f"🏭 Industry Filter: {industry if industry and industry != 'All Industries' else 'All Industries'}")
            if ticker_filter:
                add_log(f"🎯 Ticker Filter: {ticker_filter}")
            if pct_threshold is not None:
                filter_desc = f"drop <= {pct_threshold}%" if filter_type == 'bearish' else f"recovery >= {pct_threshold}%"
                add_log(f"🔍 Percentage Filter: {filter_type.title()} - {filter_desc}")
            if flexible_days > 0:
                # Log using trading-day based window for clarity
                min_date = self.get_nth_trading_day_before(bearish_date, flexible_days).strftime('%Y-%m-%d')
                max_date = self.get_nth_trading_day_after(bearish_date, flexible_days).strftime('%Y-%m-%d')
                add_log(f"📅 Flexible Date Range: {min_date} to {max_date} (±{flexible_days} trading days)")
            add_log("")
            
            # Calculate total API calls estimate for progress tracking
            companies = self._get_large_cap_companies_with_options()
            if industry and industry != "All Industries":
                companies = {ticker: info for ticker, info in companies.items() 
                           if info.get('industry') == industry}
            
            # Estimate: Step 1 = len(companies), Step 2 = ~50-100 stocks (estimate 70)
            estimated_losers = 70
            self.total_api_calls_estimated = len(companies) + estimated_losers
            self.api_call_count = 0  # Reset counter
            add_log(f"📊 Estimated total API calls: {self.total_api_calls_estimated} (Step 1: {len(companies)}, Step 2: ~{estimated_losers})")
            add_log("")
            
            # Step 1: Use Prixe.io to identify top stocks (bearish or bullish)
            find_gainers = (filter_type == 'bullish')
            if find_gainers:
                add_log("📊 Step 1: Identifying top bullish stocks using Prixe.io...")
                add_log("   Calculating price gains for all large-cap companies...")
            else:
                add_log("📊 Step 1: Identifying top bearish stocks using Prixe.io...")
                add_log("   Calculating price drops for all large-cap companies...")
            
            stocks = []
            
            # Parse ticker_filter into list if provided
            ticker_list: Optional[List[str]] = None
            if ticker_filter:
                ticker_list = [t.strip().upper() for t in str(ticker_filter).split(',') if t.strip()]

            try:
                stocks = self.get_top_losers_prixe(
                    bearish_date,
                    industry,
                    logs=logs,
                    find_gainers=find_gainers,
                    flexible_days=flexible_days,
                    ticker_filter=ticker_list
                )
                
                # Update estimate with actual number of stocks found
                self.total_api_calls_estimated = len(companies) + len(stocks)
                add_log(f"📊 Updated total API calls estimate: {self.total_api_calls_estimated} (Step 1: {len(companies)}, Step 2: {len(stocks)})")
                
                if len(stocks) == 0:
                    if find_gainers:
                        add_log("   ℹ️  No stocks found with gains on the date")
                    else:
                        add_log("   ℹ️  No stocks found with drops on the date")
                    return [], logs
                
            except Exception as e:
                add_log(f"   ⚠️  Error in Prixe.io pre-filtering: {str(e)}")
                add_log("   Falling back to legacy method...")
                return self._get_bearish_analytics_legacy(bearish_date, target_date, industry)
            
            if len(stocks) == 0:
                if find_gainers:
                    add_log("   ℹ️  No stocks found with gains on the date")
                else:
                    add_log("   ℹ️  No stocks found with drops on the date")
                return [], logs
            
            # Rename for clarity (stocks can be losers or gainers)
            losers = stocks
            
            add_log("")
            if find_gainers:
                add_log("📈 Step 2: Fetching detailed price data for gaining stocks...")
            else:
                add_log("📈 Step 2: Fetching detailed price data for losing stocks...")
            add_log(f"   Processing {len(losers)} stocks in parallel (optimized: 1 API call per stock, parallel execution)...")
            
            results = []
            processed_count = 0
            skipped_no_target_price = 0
            
            # Use class method self.extract_price_from_history() to extract prices
            
            # Process stock function (for parallel execution)
            def process_stock(stock_data):
                """Process a single stock - optimized to use 1 API call instead of 3"""
                ticker, pct_change, company_info, actual_date_from_lookup, idx = stock_data
                try:
                    # OPTIMIZATION: Fetch price history once (covers both bearish_date and target_date)
                    # Start 90 days before bearish_date to ensure:
                    # 1. Previous trading day is visible (for graph)
                    # 2. Enough data for technical indicators (RSI 14, MACD 26, MA 20)
                    # 3. Sufficient historical data for meaningful support/resistance levels (3 months)
                    # This replaces 3 separate API calls:
                    # 1. get_stock_price_on_date(ticker, bearish_date)
                    # 2. get_stock_price_on_date(ticker, target_date)
                    # 3. get_stock_price_history(ticker, bearish_date, target_date)
                    graph_start_date = bearish_date - timedelta(days=120)  # Increased to 120 days for recovery history analysis
                    # Add 1 day to target_date to ensure we get data up to and including the target date
                    # (API might exclude the end_date, so adding 1 day ensures we get target_date)
                    price_history_end_date = target_date + timedelta(days=1)
                    price_history = self.get_stock_price_history(ticker, graph_start_date, price_history_end_date)
                    
                    if not price_history:
                        return None
                    
                    # Use the actual date from flexible lookup (or fallback to bearish_date)
                    # Parse the actual_date string to datetime for extract_price_from_history
                    if actual_date_from_lookup:
                        try:
                            actual_bearish_date_dt = datetime.strptime(actual_date_from_lookup, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                            base_price, actual_bearish_date = self.extract_price_from_history(price_history, actual_bearish_date_dt)
                        except:
                            # Fallback to original bearish_date if parsing fails
                            base_price, actual_bearish_date = self.extract_price_from_history(price_history, bearish_date)
                    else:
                        # Fallback to original bearish_date if no actual_date provided
                        base_price, actual_bearish_date = self.extract_price_from_history(price_history, bearish_date)
                    
                    if base_price is None:
                        return None
                    
                    # Use actual trading date from flexible lookup (or extracted date)
                    actual_bearish_date_str = actual_date_from_lookup if actual_date_from_lookup else (actual_bearish_date if actual_bearish_date else bearish_date.strftime('%Y-%m-%d'))
                    
                    # Find the most recent previous trading day to calculate pct_change
                    sorted_history = sorted(price_history, key=lambda x: x.get('date', ''))
                    prev_price_entry = None
                    for entry in sorted_history:
                        entry_date = entry.get('date', '')
                        if entry_date and entry_date < actual_bearish_date_str:
                            if prev_price_entry is None or entry_date > prev_price_entry.get('date', ''):
                                prev_price_entry = entry
                    
                    if prev_price_entry:
                        best_prev_price = prev_price_entry.get('price')
                        best_drop_pct = ((base_price - best_prev_price) / best_prev_price) * 100 if best_prev_price and best_prev_price > 0 else pct_change
                    else:
                        # If we can't find previous price, use the pct_change from get_top_losers_prixe
                        best_drop_pct = pct_change
                        best_prev_price = base_price / (1 + pct_change / 100) if pct_change != 0 else base_price
                    
                    target_price, actual_target_date = self.extract_price_from_history(price_history, target_date)
                    if target_price is None:
                        return ('skipped', ticker)
                    
                    # Use actual trading date if different from requested date
                    actual_target_date_str = actual_target_date if actual_target_date else target_date.strftime('%Y-%m-%d')
                    
                    # Use the calculated pct_change from the actual drop day
                    pct_change = best_drop_pct
                    
                    # Calculate recovery/change percentage from base_date to target_date
                    recovery_pct = ((target_price - base_price) / base_price) * 100
                    
                    # Use the pct_change from the actual drop day we found (or recalculated)
                    # Calculate prev_price from pct_change and base_price
                    # pct_change is the change from previous day to base_date
                    prev_price = best_prev_price if best_prev_price else (base_price / (1 + best_drop_pct / 100) if best_drop_pct != 0 else base_price)
                    
                    # Use the recalculated pct_change from the actual drop day
                    actual_pct_change = best_drop_pct if best_drop_pct is not None else pct_change
                    
                    # For consistency, use pct_drop for bearish (negative) and pct_gain for bullish (positive)
                    pct_drop = actual_pct_change if actual_pct_change < 0 else 0
                    pct_gain = actual_pct_change if actual_pct_change > 0 else 0
                    
                    # Get recovery strength for the industry
                    stock_industry = company_info.get('industry', 'Unknown')
                    recovery_strength = self._get_recovery_strength(stock_industry)
                    
                    # Analyze recovery history (similar drops in past 120 days)
                    # Note: Events are now fetched separately in add_events_during_to_stock and will be matched in frontend
                    recovery_history = []
                    recovery_history_summary = None
                    if pct_threshold is not None and filter_type == 'bearish':
                        # Only analyze for bearish drops, using the threshold
                        # No longer passing events - frontend will match events from earnings_dividends.events_during
                        print(f"[RECOVERY HISTORY] Calling analyze_recovery_history for {ticker} (events will be matched in frontend)")
                        rh_result = self.analyze_recovery_history(price_history, pct_threshold, actual_bearish_date_str, None)
                        if isinstance(rh_result, dict):
                            recovery_history = rh_result.get('items', [])
                            recovery_history_summary = rh_result.get('summary')
                        else:
                            # Backward compatibility in case analyze_recovery_history returns a list
                            recovery_history = rh_result
                        
                        # Event matching is now done in frontend - no post-processing needed
                        print(f"[RECOVERY HISTORY] {ticker}: {len(recovery_history)} recovery items (events will be matched in frontend)")
                    
                    # OPTIMIZATION: Skip technical indicators and earnings checks here - will be done after percentage filter
                    # This saves CPU time and API calls for stocks that will be filtered out
                    technical_indicators = {}
                    earnings_dividends = {
                        'events_during': [],
                        'next_events': [],
                        'has_events_during': False,
                        'has_next_events': False
                    }
                    
                    result = {
                        'ticker': ticker,
                        'company_name': company_info.get('name', ticker),
                        'industry': stock_industry,
                        'recovery_strength': recovery_strength['stars'],
                        'recovery_rating': recovery_strength['rating'],
                        'recovery_reason': recovery_strength['reason'],
                        'market_cap': company_info.get('market_cap', 0),
                        'bearish_date': actual_bearish_date_str,  # Use actual trading date (not requested date if it's a non-trading day)
                        'bearish_price': round(base_price, 2),
                        'prev_price': round(prev_price, 2),
                        'pct_drop': round(pct_drop, 2),
                        'pct_gain': round(pct_gain, 2),
                        'pct_change': round(actual_pct_change, 2),
                        'target_date': actual_target_date_str,  # Use actual trading date (not requested date if it's a non-trading day)
                        'target_price': round(target_price, 2),
                        'recovery_pct': round(recovery_pct, 2),
                        'price_history': price_history,  # Keep price_history for later indicator calculation
                        'base_price': base_price,  # Keep base_price for indicator calculation
                        'technical_indicators': technical_indicators,
                        'earnings_dividends': earnings_dividends,
                        'recovery_history': recovery_history,  # Historical similar drops and recovery times
                        'recovery_history_summary': recovery_history_summary
                    }
                    
                    # Preserve is_missing_from_list flag if present
                    if company_info.get('is_missing_from_list'):
                        result['is_missing_from_list'] = True
                        if 'size_category' in company_info:
                            result['size_category'] = company_info['size_category']
                    
                    return result
                except Exception as e:
                    return ('error', ticker, str(e))
            
            # OPTIMIZATION: Process stocks in parallel using ThreadPoolExecutor
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            total_losers = len(losers)
            max_workers = min(10, total_losers)  # Reduced to 10 workers to avoid Prixe.io rate limits (429 errors)
            
            # Prepare stock data with index for progress tracking
            stock_data_list = [(ticker, pct_change, company_info, actual_date, idx) 
                             for idx, (ticker, pct_change, company_info, actual_date) in enumerate(losers, 1)]
            
            add_log(f"   🚀 Using {max_workers} parallel workers for faster processing...")
            
            # Process stocks in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_stock = {executor.submit(process_stock, stock_data): stock_data 
                                  for stock_data in stock_data_list}
                
                # Process completed tasks as they finish
                completed = 0
                for future in as_completed(future_to_stock):
                    completed += 1
                    stock_data = future_to_stock[future]
                    ticker = stock_data[0]
                    idx = stock_data[4]
                    
                    # Show progress every 10% or every 5 stocks
                    progress_interval = max(5, total_losers // 10)
                    if completed % progress_interval == 0 or completed == 1:
                        pct = int((completed / total_losers) * 100)
                        add_log(f"   ⏳ Progress: {completed}/{total_losers} stocks ({pct}%)...")
                    
                    try:
                        result = future.result()
                        
                        if result is None:
                            continue
                        elif isinstance(result, tuple) and result[0] == 'skipped':
                            skipped_no_target_price += 1
                        elif isinstance(result, tuple) and result[0] == 'error':
                            add_log(f"   ⚠️  Error processing {result[1]}: {result[2]}")
                        else:
                            # Success
                            results.append(result)
                            processed_count += 1
                    except Exception as e:
                        add_log(f"   ⚠️  Error processing {ticker}: {str(e)}")
                        continue
            
            # Apply percentage threshold filter if specified
            if pct_threshold is not None:
                original_count = len(results)
                
                # Removed verbose logging of individual stock prices - API progress is enough
                
                if filter_type == 'bearish':
                    # Filter by bearish drop percentage (pct_change <= threshold, e.g., <= -5 means drop >= 5%)
                    # Note: pct_change is negative for drops, so <= -5 means drop of 5% or more
                    results = [r for r in results if r.get('pct_change', 0) <= pct_threshold]
                    add_log(f"   🔍 Filtered by bearish drop: {len(results)}/{original_count} stocks with drop <= {pct_threshold}%")
                elif filter_type == 'bullish':
                    # Filter by bullish gain percentage (pct_change >= threshold, e.g., >= 5 means gain >= 5%)
                    # Note: pct_change is positive for gains, so >= 5 means gain of 5% or more
                    results = [r for r in results if r.get('pct_change', 0) >= pct_threshold]
                    add_log(f"   🔍 Filtered by bullish gain: {len(results)}/{original_count} stocks with gain >= {pct_threshold}%")
            
            # OPTIMIZATION: Calculate technical indicators and check earnings ONLY for filtered stocks
            # This is done after filtering to save CPU time and API calls for stocks that will be filtered out
            if len(results) > 0:
                add_log(f"   📊 Calculating technical indicators for {len(results)} filtered stocks...")
                
                def add_indicators_to_stock(stock_result):
                    """Add technical indicators to a stock result"""
                    try:
                        price_history = stock_result.get('price_history', [])
                        target_price = stock_result.get('target_price')
                        base_price = stock_result.get('base_price')
                        
                        if not price_history or not target_price or not base_price:
                            return stock_result
                        
                        # Calculate technical indicators at BOTH bearish_date and target_date
                        bearish_date_str = stock_result.get('bearish_date')
                        target_date_str = stock_result.get('target_date')
                        
                        # Filter price_history for bearish_date indicators
                        filtered_price_history_bearish = []
                        if bearish_date_str:
                            bearish_date_obj = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                            bearish_timestamp = int(bearish_date_obj.timestamp())
                            filtered_price_history_bearish = [
                                entry for entry in price_history
                                if entry.get('date') <= bearish_date_str or 
                                (entry.get('timestamp', 0) / 1000) <= bearish_timestamp
                            ]
                        else:
                            filtered_price_history_bearish = price_history
                        
                        # Filter price_history for target_date indicators
                        filtered_price_history_target = []
                        if target_date_str:
                            target_date_obj = datetime.strptime(target_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                            target_timestamp = int(target_date_obj.timestamp())
                            filtered_price_history_target = [
                                entry for entry in price_history
                                if entry.get('date') <= target_date_str or 
                                (entry.get('timestamp', 0) / 1000) <= target_timestamp
                            ]
                        else:
                            filtered_price_history_target = price_history
                        
                        # Calculate technical indicators at bearish_date
                        technical_indicators_bearish = self._calculate_technical_indicators(
                            filtered_price_history_bearish, base_price, base_price
                        )
                        
                        # Calculate technical indicators at target_date
                        technical_indicators_target = self._calculate_technical_indicators(
                            filtered_price_history_target, target_price, base_price
                        )
                        
                        # Store both sets of indicators
                        stock_result['technical_indicators'] = technical_indicators_target  # Keep for backward compatibility
                        stock_result['technical_indicators_bearish'] = technical_indicators_bearish
                        stock_result['technical_indicators_target'] = technical_indicators_target
                        return stock_result
                    except Exception as e:
                        # If indicator calculation fails, just keep empty indicators
                        return stock_result
                
                # Calculate technical indicators in parallel for filtered stocks
                with ThreadPoolExecutor(max_workers=min(10, len(results))) as executor:
                    results = list(executor.map(add_indicators_to_stock, results))
                
                # Fetch events_during (historical events between bearish_date and target_date) - fast, always fetch
                # Skip next_events (future events) - requires 40 days of queries, fetch on-demand
                add_log(f"   📊 Checking events during period for {len(results)} filtered stocks...")
                
                def add_events_during_to_stock(stock_result):
                    """Add events_during data to a stock result (historical events only)
                    Extended to 120 days before bearish_date for recovery history analysis"""
                    ticker = stock_result.get('ticker')
                    # Get reference to self for logging
                    tracker_self = self
                    
                    # TEST: Verify function is being called
                    test_msg = f"[EVENTS FILTER] {ticker}: FUNCTION CALLED - Starting events filtering\n"
                    print(test_msg, end='', flush=True)
                    try:
                        tracker_self._write_debug_log(test_msg)
                    except:
                        pass
                    try:
                        tracker_self._write_debug_log(test_msg)
                    except Exception as e:
                        print(f"[DEBUG LOG ERROR] Failed to write test log: {e}", flush=True)
                    
                    try:
                        # Extend fetch to 120 days before bearish_date for recovery history
                        events_start_date = bearish_date - timedelta(days=120)
                        # Fetch all events from 120 days before bearish_date to target_date
                        earnings_dividends = self._check_earnings_dividends_sec(ticker, events_start_date, target_date, future_days=0)
                        
                        # Also check yfinance for events (replaces NASDAQ - much faster, finds more events)
                        try:
                            yfinance_result = self._check_earnings_dividends_yfinance(ticker, events_start_date, target_date, future_days=0)
                            if yfinance_result:
                                yfinance_events_during = yfinance_result.get('events_during', [])
                                if yfinance_events_during:
                                    earnings_dividends['events_during'].extend(yfinance_events_during)
                                    
                                    # Remove duplicates
                                    seen_events = set()
                                    unique_events = []
                                    for event in sorted(earnings_dividends['events_during'], key=lambda x: (x['date'], x.get('type', ''))):
                                        event_key = (event['date'], event.get('type', ''), event.get('name', ''))
                                        if event_key not in seen_events:
                                            seen_events.add(event_key)
                                            unique_events.append(event)
                                    earnings_dividends['events_during'] = unique_events
                        except Exception:
                            pass
                        
                        # Store full events list for recovery history matching (120 days before bearish_date)
                        all_events_for_recovery = earnings_dividends.get('events_during', []).copy()
                        
                        # Filter events_during to only show events between actual bearish_date and target_date (for "Events During Period" column)
                        # Use actual bearish_date from stock_result (may differ from parameter if flexible_days was used)
                        stock_bearish_date = stock_result.get('bearish_date')
                        parameter_bearish_date = bearish_date.strftime('%Y-%m-%d')
                        actual_bearish_date_str = stock_bearish_date if stock_bearish_date else parameter_bearish_date
                        target_date_str = target_date.strftime('%Y-%m-%d')
                        
                        # Get original events list before filtering (CRITICAL: copy the list to avoid modifying the original)
                        original_events = list(earnings_dividends.get('events_during', []))
                        total_events_before_filter = len(original_events)
                        
                        # Debug: Log what we're using for filtering (also write to file)
                        log_msg = f"[EVENTS FILTER] {ticker}: stock_result.bearish_date={stock_bearish_date}, parameter={parameter_bearish_date}, using={actual_bearish_date_str}, target={target_date_str}\n"
                        print(log_msg, end='', flush=True)
                        try:
                            tracker_self._write_debug_log(log_msg)
                        except Exception as e:
                            print(f"[DEBUG LOG ERROR] Failed to write log: {e}", flush=True)
                        
                        if original_events:
                            log_msg = f"[EVENTS FILTER] {ticker}: Original events ({total_events_before_filter}): {[e.get('date') for e in original_events]}\n"
                            print(log_msg, end='')
                            tracker_self._write_debug_log(log_msg)
                        
                        events_during_period = []
                        filtered_out_count = 0
                        for event in original_events:
                            event_date = event.get('date', '')
                            if event_date:
                                # String comparison for YYYY-MM-DD format
                                if actual_bearish_date_str <= event_date <= target_date_str:
                                    events_during_period.append(event)
                                else:
                                    filtered_out_count += 1
                                    log_msg = f"[EVENTS FILTER] {ticker}: Filtering out event {event_date} (not in range {actual_bearish_date_str} to {target_date_str})\n"
                                    print(log_msg, end='')
                                    tracker_self._write_debug_log(log_msg)
                            else:
                                # Skip events without dates
                                filtered_out_count += 1
                                log_msg = f"[EVENTS FILTER] {ticker}: Skipping event without date: {event}\n"
                                print(log_msg, end='')
                                tracker_self._write_debug_log(log_msg)
                        
                        # Set filtered events for display (CRITICAL: replace the list, don't modify in place)
                        earnings_dividends['events_during'] = events_during_period
                        earnings_dividends['has_events_during'] = len(events_during_period) > 0
                        
                        # Debug logging
                        log_msg = f"[EVENTS FILTER] {ticker}: ✅ FILTERED {total_events_before_filter} events → {len(events_during_period)} events (filtered out: {filtered_out_count})\n"
                        print(log_msg, end='')
                        tracker_self._write_debug_log(log_msg)
                        
                        if events_during_period:
                            log_msg = f"[EVENTS FILTER] {ticker}: Remaining events: {[e.get('date') for e in events_during_period]}\n"
                            print(log_msg, end='')
                            tracker_self._write_debug_log(log_msg)
                        else:
                            log_msg = f"[EVENTS FILTER] {ticker}: No events in range {actual_bearish_date_str} to {target_date_str}\n"
                            print(log_msg, end='')
                            tracker_self._write_debug_log(log_msg)
                        
                        # Store full events list for recovery history (separate field)
                        earnings_dividends['all_events_for_recovery'] = all_events_for_recovery
                        
                        # DEBUG: Add debug info to stock_result so we can see it in the response
                        stock_result['_debug_events_filter'] = {
                            'bearish_date_used': actual_bearish_date_str,
                            'target_date': target_date_str,
                            'events_before_filter': total_events_before_filter,
                            'events_after_filter': len(events_during_period),
                            'all_events_count': len(all_events_for_recovery),
                            'original_event_dates': [e.get('date') for e in original_events] if original_events else [],
                            'filtered_event_dates': [e.get('date') for e in events_during_period] if events_during_period else []
                        }
                        
                        # Initialize next_events as empty (will be loaded on-demand)
                        earnings_dividends['next_events'] = []
                        earnings_dividends['has_next_events'] = False
                        earnings_dividends['next_events_loaded'] = False  # Flag to track if next_events has been loaded
                        
                        stock_result['earnings_dividends'] = earnings_dividends
                        return stock_result
                    except Exception as e:
                        # If events check fails, log the error and use empty result
                        error_msg = f"[EVENTS FILTER] {ticker}: EXCEPTION in add_events_during_to_stock: {e}\n"
                        print(error_msg, end='', flush=True)
                        import traceback
                        traceback.print_exc()
                        try:
                            tracker_self._write_debug_log(error_msg)
                            tracker_self._write_debug_log(traceback.format_exc())
                        except:
                            pass
                        
                        # Set debug info even on error
                        stock_result['_debug_events_filter'] = {
                            'error': str(e),
                            'function_called': True,
                            'exception_occurred': True
                        }
                        
                        # If events check fails, use empty result
                        stock_result['earnings_dividends'] = {
                            'events_during': [],
                            'all_events_for_recovery': [],
                            'next_events': [],
                            'has_events_during': False,
                            'has_next_events': False,
                            'next_events_loaded': False
                        }
                        return stock_result
                
                # Process events_during checks in parallel for filtered stocks
                with ThreadPoolExecutor(max_workers=min(10, len(results))) as executor:
                    results = list(executor.map(add_events_during_to_stock, results))
            
            add_log("")
            add_log("✅ Analysis Complete!")
            add_log(f"   📊 Summary:")
            if find_gainers:
                add_log(f"      • Stocks with gains found: {len(losers)}")
            else:
                add_log(f"      • Stocks with drops found: {len(losers)}")
            add_log(f"      • Successfully processed: {processed_count}")
            add_log(f"      • Skipped (no target price): {skipped_no_target_price}")
            if pct_threshold is not None:
                if filter_type == 'bearish':
                    filter_desc = f"drop <= {pct_threshold}%"
                else:
                    filter_desc = f"gain >= {pct_threshold}%"
                add_log(f"      • After filtering ({filter_desc}): {len(results)} stocks")
            add_log(f"      • Final results: {len(results)} stocks")
            
            print(f"[BEARISH ANALYTICS] Found {len(results)} stocks with drops")
            return results, logs
            
        except Exception as e:
            error_msg = f"Error in get_bearish_analytics: {e}"
            add_log("")
            add_log(f"❌ Error: {error_msg}")
            print(error_msg)
            import traceback
            traceback.print_exc()
            return [], logs
    
    def _get_bearish_analytics_legacy(self, bearish_date: datetime, target_date: datetime, industry: Optional[str] = None) -> tuple[List[Dict], List[str]]:
        """Legacy method: Check all companies individually (slower but more reliable fallback)"""
        logs = []
        try:
            logs.append("📋 Loading large-cap companies list...")
            companies = self._get_large_cap_companies_with_options()
            
            if industry and industry != "All Industries":
                companies = {ticker: info for ticker, info in companies.items() 
                           if info.get('industry') == industry}
            
            results = []
            prev_date = bearish_date - timedelta(days=5)
            
            for ticker, company_info in companies.items():
                try:
                    bearish_price = self.get_stock_price_on_date(ticker, bearish_date)
                    if bearish_price is None:
                        continue
                    
                    prev_price = None
                    prev_date_history = self.get_stock_price_history(ticker, prev_date, bearish_date)
                    if prev_date_history:
                        for entry in reversed(prev_date_history):
                            entry_date_str = entry.get('date')
                            entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                            if entry_date < bearish_date:
                                prev_price = entry.get('price')
                                break
                    
                    if prev_price is None:
                        continue
                    
                    pct_drop = ((bearish_price - prev_price) / prev_price) * 100
                    if pct_drop >= 0:
                        continue
                    
                    target_price = self.get_stock_price_on_date(ticker, target_date)
                    if target_price is None:
                        continue
                    
                    recovery_pct = ((target_price - bearish_price) / bearish_price) * 100
                    price_history = self.get_stock_price_history(ticker, bearish_date, target_date)
                    
                    results.append({
                        'ticker': ticker,
                        'company_name': company_info.get('name', ticker),
                        'industry': company_info.get('industry', 'Unknown'),
                        'market_cap': company_info.get('market_cap', 0),
                        'bearish_date': bearish_date.strftime('%Y-%m-%d'),
                        'bearish_price': round(bearish_price, 2),
                        'prev_price': round(prev_price, 2),
                        'pct_drop': round(pct_drop, 2),
                        'target_date': target_date.strftime('%Y-%m-%d'),
                        'target_price': round(target_price, 2),
                        'recovery_pct': round(recovery_pct, 2),
                        'price_history': price_history
                    })
                except:
                    continue
            
            results.sort(key=lambda x: x['pct_drop'])
            return results, logs
        except:
            return [], logs
    
    def has_trading_data_for_date(self, ticker: str, target_date: datetime, batch_data: Dict = None) -> bool:
        """Check if Prixe.io has actual trading data for the exact date (no fallback)
        
        Args:
            ticker: Stock ticker symbol
            target_date: Target date to check (datetime object, time component ignored)
            batch_data: Optional batch data to use instead of making API call
        
        Returns:
            True if Prixe.io has trading data for the exact date, False otherwise
        """
        try:
            # First try to use batch data if provided
            if batch_data:
                data = batch_data.get('data', {})
                timestamps = data.get('timestamp', [])
                target_date_only = target_date.date()
                
                for ts in timestamps:
                    from datetime import datetime as dt
                    ts_date = dt.fromtimestamp(ts).date()
                    if ts_date == target_date_only:
                        return True
                return False
            
            # Try to use cached batch data for this ticker
            if ticker in self.batch_data_cache:
                batch_data = self.batch_data_cache[ticker]
                data = batch_data.get('data', {})
                timestamps = data.get('timestamp', [])
                target_date_only = target_date.date()
                
                for ts in timestamps:
                    from datetime import datetime as dt
                    ts_date = dt.fromtimestamp(ts).date()
                    if ts_date == target_date_only:
                        return True
                return False
            
            # PERFORMANCE: Skip API call if we know market is closed
            # Check if it's a weekend
            weekday = target_date.weekday()
            if weekday >= 5:  # Saturday or Sunday
                return False
            
            # Check if it's a future date
            if self.is_future_date(target_date):
                return False
            
            # Fallback: make API call (should rarely happen now)
            date_str = target_date.strftime('%Y-%m-%d')
            payload = {
                'ticker': ticker,
                'start_date': date_str,
                'end_date': date_str,
                'interval': '1d'
            }
            
            response = self._prixe_api_request(PRIXE_PRICE_ENDPOINT, payload)
            
            if response and response.get('success') and 'data' in response:
                data = response['data']
                timestamps = data.get('timestamp', [])
                
                # Check if we have any timestamps that match the target date
                for ts in timestamps:
                    from datetime import datetime as dt
                    ts_date = dt.fromtimestamp(ts).date()
                    if ts_date == target_date.date():
                        return True
            
            return False
        except Exception:
            return False
    
    def get_fmp_intraday_price(self, ticker: str, target_datetime: datetime, interval: str = '1min') -> Optional[float]:
        """
        Fetches intraday stock price from Prixe.io API for a specific ticker and datetime.
        Uses _fetch_intraday_data_for_day to leverage caching and batch fetching.
        Returns None if data is not available (future date, API error, etc.)
        """
        if not ticker or not target_datetime:
            return None
        
        # Check if date is in the future
        if self.is_future_date(target_datetime):
            return None
        
        # Get the date (normalize to start of day for caching)
        target_date = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Use _fetch_intraday_data_for_day which handles caching properly
        # This ensures we use the same cache as pre-fetching
        intraday_data = self._fetch_intraday_data_for_day(ticker, target_date, interval=interval)
        
        if not intraday_data:
            return None
        
        # Extract price for the specific datetime from the batch data
        price, is_exact, actual_ts = self._extract_intraday_price_from_batch(intraday_data, target_datetime)
        return price
    
    def get_next_trading_day(self, dt: datetime, ticker: str = None, batch_data: Dict = None) -> Optional[datetime]:
        """Get the next trading day (Monday-Friday) after the given datetime
        Optionally verify with a ticker to ensure it's actually a trading day
        
        Args:
            dt: Starting datetime
            ticker: Optional ticker to verify trading day
            batch_data: Optional batch data to use instead of making API calls
        """
        # Start from the day after the announcement
        next_day = dt + timedelta(days=1)
        
        # Find the next weekday (Monday=0, Sunday=6)
        # Skip weekends and check if we can get price data (indicates trading day)
        for attempt in range(10):
            weekday = next_day.weekday()  # 0=Monday, 6=Sunday
            if weekday < 5:  # Monday-Friday
                # If ticker provided, verify we can get price data for this day
                if ticker:
                    # Use batch data if available, otherwise make API call
                    if batch_data:
                        price, _, _ = self._extract_price_from_batch(batch_data, next_day, 'close')
                        if price:
                            return next_day
                    elif ticker in self.batch_data_cache:
                        price, _, _ = self._extract_price_from_batch(self.batch_data_cache[ticker], next_day, 'close')
                        if price:
                            return next_day
                    else:
                        # Fallback: make API call (should rarely happen)
                        test_price, _ = self.get_stock_price_at_time(ticker, next_day)
                        if test_price:
                            return next_day
                else:
                    # No ticker provided, just return the next weekday
                    return next_day
            next_day = next_day + timedelta(days=1)
        
        return None
    
    def get_nth_trading_day_before(self, dt: datetime, n: int) -> datetime:
        """Get the Nth trading day (weekday) before the given date.
        
        This function treats Monday–Friday as trading days and skips weekends.
        It does NOT apply an explicit holiday calendar – holidays that fall on
        weekdays are effectively handled later by the price-history lookup.
        """
        if n <= 0:
            return dt
        
        current = dt
        remaining = n
        
        while remaining > 0:
            current = current - timedelta(days=1)
            # 0 = Monday, 6 = Sunday; trading days are 0–4
            if current.weekday() < 5:
                remaining -= 1
        
        return current
    
    def get_nth_trading_day_after(self, dt: datetime, n: int) -> datetime:
        """Get the Nth trading day (weekday) after the given date.
        
        This function treats Monday–Friday as trading days and skips weekends.
        It does NOT apply an explicit holiday calendar – holidays that fall on
        weekdays are effectively handled later by the price-history lookup.
        """
        if n <= 0:
            return dt
        
        current = dt
        remaining = n
        
        while remaining > 0:
            current = current + timedelta(days=1)
            if current.weekday() < 5:
                remaining -= 1
        
        return current
    
    def _fetch_price_data_batch(self, ticker: str, start_date: datetime, end_date: datetime, interval: str = '1d') -> Optional[Dict]:
        """Fetch price data for a date range in a single API call
        
        Returns the full Prixe.io response with all price data for the range
        Falls back to Yahoo Finance if Prixe.io fails (for old dates or unavailable tickers)
        """
        cache_key = f"prixe_batch_{ticker}_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}_{interval}"
        if cache_key in self.stock_price_cache:
            # PERFORMANCE: Removed verbose debug logging
            return self.stock_price_cache[cache_key]
        
        payload = {
            'ticker': ticker,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'interval': interval
        }
        
        # PERFORMANCE: Removed verbose debug logging (this function is called frequently)
        
        response = self._prixe_api_request('/api/price', payload)
        
        # PERFORMANCE: Removed verbose debug logging
        
        if response:
            # PERFORMANCE: Removed verbose debug logging
            
            if response.get('success'):
                self.stock_price_cache[cache_key] = response
                # PERFORMANCE: Removed verbose debug logging
                return response
            # else: response exists but success is False - fall through to Yahoo Finance fallback
        # else: no response - fall through to Yahoo Finance fallback
        
        # FALLBACK: Try Yahoo Finance if Prixe.io failed (for old dates or unavailable tickers)
        if interval == '1d' and YFINANCE_AVAILABLE:
            try:
                # Convert datetime to date for yfinance
                start_date_only = start_date.date() if isinstance(start_date, datetime) else start_date
                end_date_only = end_date.date() if isinstance(end_date, datetime) else end_date
                
                stock = yf.Ticker(ticker)
                hist = stock.history(start=start_date_only, end=end_date_only)
                
                if not hist.empty:
                    # Convert Yahoo Finance format to Prixe.io format
                    timestamps = []
                    opens = []
                    highs = []
                    lows = []
                    closes = []
                    
                    for date_idx, row in hist.iterrows():
                        # Convert pandas Timestamp to Unix timestamp
                        ts = int(date_idx.timestamp())
                        timestamps.append(ts)
                        opens.append(float(row['Open']))
                        highs.append(float(row['High']))
                        lows.append(float(row['Low']))
                        closes.append(float(row['Close']))
                    
                    # Format response to match Prixe.io structure
                    yahoo_response = {
                        'success': True,
                        'data': {
                            'timestamp': timestamps,
                            'open': opens,
                            'high': highs,
                            'low': lows,
                            'close': closes,
                            'ticker': ticker
                        }
                    }
                    
                    # Cache the result
                    self.stock_price_cache[cache_key] = yahoo_response
                    return yahoo_response
            except Exception as e:
                # Yahoo Finance also failed - log but don't crash
                print(f"[YAHOO FALLBACK] Failed for {ticker}: {e}")
                pass
        
        return None
    
    def _fetch_intraday_data_batch(self, ticker: str, start_date: datetime, end_date: datetime, interval: str = '5min') -> Optional[Dict]:
        """Fetch intraday data for a date range in one API call and cache it
        
        This is more efficient than fetching individual days.
        Returns the full Prixe.io response with all intraday price data for the range.
        """
        # PERFORMANCE: Filter out weekends and future dates before making API call
        # For intraday data, only fetch weekdays within last 60 days
        now = datetime.now(timezone.utc)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        # Filter to only valid trading days (weekdays, not future, within 60 days)
        valid_dates = []
        current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current <= end:
            # Check if weekday (Monday=0, Sunday=6)
            if current.weekday() < 5:  # Monday-Friday
                # Check if not future
                if not self.is_future_date(current):
                    # Check if within 60 days (for intraday data)
                    days_ago = (now - current).days
                    if days_ago <= 60:
                        valid_dates.append(current)
            current += timedelta(days=1)
        
        # If no valid dates, skip API call
        if not valid_dates:
            return None
        
        # Use the filtered date range
        start_date = min(valid_dates)
        end_date = max(valid_dates)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        cache_key = f"prixe_intraday_batch_{ticker}_{start_str}_{end_str}_{interval}"
        
        if cache_key in self.stock_price_cache:
            return self.stock_price_cache[cache_key]
        
        # Map interval format
        interval_map = {
            '1min': '1m',
            '2min': '2m',
            '3min': '3m',
            '4min': '4m',
            '5min': '5m',
            '15min': '15m',
            '30min': '30m',
            '1hr': '1h',
            '1h': '1h'
        }
        prixe_interval = interval_map.get(interval, interval)
        
        payload = {
            'ticker': ticker,
            'start_date': start_str,
            'end_date': end_str,
            'interval': prixe_interval
        }
        
        # PERFORMANCE: Removed verbose logging (called for each day - too frequent)
        
        response = self._prixe_api_request('/api/price', payload)
        
        if response and response.get('success') and 'data' in response:
            self.stock_price_cache[cache_key] = response
            return response
        
        return None
            
    def _fetch_intraday_data_for_day(self, ticker: str, target_date: datetime, interval: str = '5min') -> Optional[Dict]:
        """Fetch intraday data for a specific day and cache it
        
        First checks if data is available in batch cache, otherwise makes individual API call.
        Returns the full Prixe.io response with all intraday price data for the day
        """
        # PERFORMANCE: Skip intraday data for dates >60 days ago (Prixe.io doesn't support it)
        now = datetime.now(timezone.utc)
        if target_date.tzinfo is None:
            target_date_utc = target_date.replace(tzinfo=timezone.utc)
        else:
            target_date_utc = target_date.astimezone(timezone.utc)
        
        days_ago = (now - target_date_utc).days
        if days_ago > 60:
            # Prixe.io doesn't support intraday data for dates >60 days ago
            return None
        
        date_str = target_date.strftime('%Y-%m-%d')
        cache_key = f"prixe_intraday_day_{ticker}_{date_str}_{interval}"
        
        # Check individual day cache first, but only if date is still within 60 days
        # (cached data from when it was fresh should not be used if date is now >60 days old)
        if cache_key in self.stock_price_cache:
            # Re-validate date before using cached data
            if days_ago <= 60:
                return self.stock_price_cache[cache_key]
            else:
                # Date is now >60 days old, don't use cached intraday data
                # Remove from cache to prevent future use
                del self.stock_price_cache[cache_key]
        
        # Check if data exists in batch cache (search through batch cache keys)
        # Format: prixe_intraday_batch_{ticker}_{start_date}_{end_date}_{interval}
        for batch_key in self.stock_price_cache.keys():
            if batch_key.startswith(f"prixe_intraday_batch_{ticker}_") and batch_key.endswith(f"_{interval}"):
                # Extract date range from batch key
                parts = batch_key.replace(f"prixe_intraday_batch_{ticker}_", "").replace(f"_{interval}", "").split("_")
                if len(parts) == 2:
                    try:
                        # Parse dates and ensure they're timezone-aware (UTC)
                        batch_start = datetime.strptime(parts[0], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                        batch_end = datetime.strptime(parts[1], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                        
                        # Ensure target_date is timezone-aware (UTC)
                        if target_date.tzinfo is None:
                            target_date_only = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
                        else:
                            target_date_only = target_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
                        
                        # Check if target_date is within batch range AND still within 60 days
                        if batch_start <= target_date_only <= batch_end:
                            # Re-validate date before using cached batch data
                            batch_days_ago = (now - target_date_only).days
                            if batch_days_ago > 60:
                                # Date is now >60 days old, skip this batch cache entry
                                continue
                            # Extract data for this specific day from batch
                            batch_data = self.stock_price_cache[batch_key]
                            day_data = self._extract_day_from_batch(batch_data, target_date_only)
                            if day_data:
                                # Cache individual day for faster future access
                                self.stock_price_cache[cache_key] = day_data
                                return day_data
                    except (ValueError, TypeError) as e:
                        continue
                
        # If not in batch cache, fetch individual day (fallback)
        # Map interval format
        interval_map = {
            '1min': '1m',
            '2min': '2m',
            '3min': '3m',
            '4min': '4m',
            '5min': '5m',
            '15min': '15m',
            '30min': '30m',
            '1hr': '1h',
            '1h': '1h'
        }
        prixe_interval = interval_map.get(interval, interval)
        
        payload = {
            'ticker': ticker,
            'start_date': date_str,
            'end_date': date_str,
            'interval': prixe_interval
        }
        
        response = self._prixe_api_request('/api/price', payload)
        
        if response and response.get('success') and 'data' in response:
            self.stock_price_cache[cache_key] = response
            return response
        
        return None
    
    def _extract_day_from_batch(self, batch_data: Dict, target_date: datetime) -> Optional[Dict]:
        """Extract data for a specific day from batch intraday data
        
        Prixe.io returns arrays of timestamps, closes, etc. We need to filter by date.
        """
        if not batch_data or 'data' not in batch_data:
            return None
        
        data = batch_data['data']
        timestamps = data.get('timestamp', [])
        
        if not timestamps:
            return None
        
        # Ensure target_date is timezone-aware (UTC)
        if target_date.tzinfo is None:
            target_date = target_date.replace(tzinfo=timezone.utc)
        else:
            target_date = target_date.astimezone(timezone.utc)
        
        # Get start and end of target day in UTC
        target_date_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        target_date_end = target_date_start + timedelta(days=1)
        
        # Convert to timestamps (Prixe.io timestamps are Unix timestamps in UTC)
        target_timestamp_start = int(target_date_start.timestamp())
        target_timestamp_end = int(target_date_end.timestamp())
        
        # Find indices for this day
        day_indices = []
        for i, ts in enumerate(timestamps):
            if target_timestamp_start <= ts < target_timestamp_end:
                day_indices.append(i)
        
        if not day_indices:
                return None
        
        # Extract data for this day
        day_data = {
            'success': True,
            'data': {}
        }
        
        # Extract arrays for this day
        for key in ['timestamp', 'close', 'open', 'high', 'low', 'volume']:
            if key in data:
                day_data['data'][key] = [data[key][i] for i in day_indices]
        
        return day_data
    
    def _extract_intraday_price_from_batch(self, intraday_data: Dict, target_datetime: datetime) -> tuple[Optional[float], bool, Optional[int]]:
        """Extract price for a specific datetime from intraday batch data
        
        Returns:
            Tuple of (price, is_exact_match, actual_timestamp)
            - price: The price found, or None if not found
            - is_exact_match: True if timestamp matches within 60 seconds, False otherwise
            - actual_timestamp: The actual timestamp found, or None if not found
        """
        if not intraday_data or 'data' not in intraday_data:
                return (None, False, None)
        
        data = intraday_data['data']
        timestamps = data.get('timestamp', [])
        closes = data.get('close', [])
        
        if not timestamps or not closes or len(timestamps) != len(closes):
            return (None, False, None)
        
        # Convert target_datetime to UTC timestamp
        # target_datetime is already in ET timezone, so convert to UTC and then to timestamp
        # Prixe.io timestamps are Unix timestamps (UTC), so we need UTC timestamp for matching
        if target_datetime.tzinfo is None:
            dt_utc = target_datetime.replace(tzinfo=timezone.utc)
        else:
            dt_utc = target_datetime.astimezone(timezone.utc)
        
        # Convert UTC datetime directly to timestamp (no need to add ET offset - already converted)
        target_timestamp = int(dt_utc.timestamp())
        
        # Find the closest timestamp match
        closest_idx = 0
        min_diff = abs(timestamps[0] - target_timestamp)
        for i, ts in enumerate(timestamps):
            diff = abs(ts - target_timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
        
        # If the closest match is more than 30 minutes away, the target time is outside trading hours
        # Return None instead of using a price from a different time period
        # This prevents matching to wrong prices for foreign stocks with different trading hours
        if min_diff > 30 * 60:  # 30 minutes in seconds
            return (None, False, None)
        
        # Check if match is exact (within 60 seconds threshold)
        is_exact_match = min_diff <= 60  # 60 seconds threshold
        
        actual_timestamp = timestamps[closest_idx] if closest_idx < len(timestamps) else None
        
        if closest_idx < len(closes):
            return (float(closes[closest_idx]), is_exact_match, actual_timestamp)
        
        return (None, False, None)
    
    def _extract_intraday_volume_from_batch(self, intraday_data: Dict, target_datetime: datetime) -> Optional[float]:
        """Extract volume for a specific datetime from intraday batch data"""
        if not intraday_data or 'data' not in intraday_data:
            return None
        
        data = intraday_data['data']
        timestamps = data.get('timestamp', [])
        volumes = data.get('volume', [])
        
        if not timestamps or not volumes or len(timestamps) != len(volumes):
            return None
        
        # Convert target_datetime to UTC timestamp
        if target_datetime.tzinfo is None:
            dt_utc = target_datetime.replace(tzinfo=timezone.utc)
        else:
            dt_utc = target_datetime.astimezone(timezone.utc)
        
        target_timestamp = int(dt_utc.timestamp())
        
        # Find the closest timestamp match
        closest_idx = 0
        min_diff = abs(timestamps[0] - target_timestamp)
        for i, ts in enumerate(timestamps):
            diff = abs(ts - target_timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
        
        if closest_idx < len(volumes):
            return float(volumes[closest_idx])
        
        return None
    
    def _extract_price_from_batch(self, price_data: Dict, target_datetime: datetime, price_type: str = 'close') -> tuple[Optional[float], bool, Optional[int]]:
        """Extract price for a specific datetime from batch price data
        
        Returns:
            Tuple of (price, is_exact_match, actual_timestamp)
            - price: The price found, or None if not found
            - is_exact_match: True if timestamp is from the same day, False otherwise
            - actual_timestamp: The actual timestamp found, or None if not found
        """
        if not price_data or 'data' not in price_data:
            return (None, False, None)
        
        data = price_data['data']
        timestamps = data.get('timestamp', [])
        target_timestamp = int(target_datetime.timestamp())
        
        if not timestamps:
            return (None, False, None)
    
        # Find closest timestamp
        closest_idx = 0
        min_diff = abs(timestamps[0] - target_timestamp)
        for i, ts in enumerate(timestamps):
            diff = abs(ts - target_timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
        
        # Check if match is exact (same day)
        # Convert timestamps to dates for comparison
        from datetime import datetime as dt
        target_date = dt.fromtimestamp(target_timestamp, tz=timezone.utc).date()
        actual_timestamp = timestamps[closest_idx] if closest_idx < len(timestamps) else None
        if actual_timestamp:
            actual_date = dt.fromtimestamp(actual_timestamp, tz=timezone.utc).date()
            is_exact_match = (target_date == actual_date)
        else:
            is_exact_match = False
        
        # Get price based on price_type
        if price_type == 'open' and 'open' in data:
            prices = data['open']
            if closest_idx < len(prices):
                return (float(prices[closest_idx]), is_exact_match, actual_timestamp)
        elif price_type == 'high' and 'high' in data:
            prices = data['high']
            if closest_idx < len(prices):
                return (float(prices[closest_idx]), is_exact_match, actual_timestamp)
        elif price_type == 'low' and 'low' in data:
            prices = data['low']
            if closest_idx < len(prices):
                return (float(prices[closest_idx]), is_exact_match, actual_timestamp)
        else:  # default to close
            if 'close' in data:
                prices = data['close']
                if closest_idx < len(prices):
                    return (float(prices[closest_idx]), is_exact_match, actual_timestamp)
            elif 'price' in data:
                return (float(data['price']), is_exact_match, actual_timestamp)
        
        return (None, False, None)
    
    def calculate_stock_changes(self, layoff: Dict) -> Dict:
        """Calculate stock price changes at different intervals after layoff announcement
        Optimized to use a single API call per ticker for all needed dates"""
        ticker = layoff.get('stock_ticker')
        announcement_dt = layoff.get('datetime')
        company_name = layoff.get('company_name', 'Unknown')
        
        # Initialize results
        empty_results = {
                'price_1min': None, 'change_1min': None, 'date_1min': None,
                'price_2min': None, 'change_2min': None, 'date_2min': None,
                'price_3min': None, 'change_3min': None, 'date_3min': None,
                'price_4min': None, 'change_4min': None, 'date_4min': None,
                'price_5min': None, 'change_5min': None, 'date_5min': None,
                'price_10min': None, 'change_10min': None, 'date_10min': None,
                'price_30min': None, 'change_30min': None, 'date_30min': None,
                'price_1hr': None, 'change_1hr': None, 'date_1hr': None,
                'price_1.5hr': None, 'change_1.5hr': None, 'date_1.5hr': None,
                'price_2hr': None, 'change_2hr': None, 'date_2hr': None,
                'price_2.5hr': None, 'change_2.5hr': None, 'date_2.5hr': None,
                'price_3hr': None, 'change_3hr': None, 'date_3hr': None,
                'price_1day': None, 'change_1day': None, 'date_1day': None,
                'price_2day': None, 'change_2day': None, 'date_2day': None,
                'price_3day': None, 'change_3day': None, 'date_3day': None,
                'price_next_close': None, 'change_next_close': None, 'date_next_close': None,
                # Approximate time tracking fields
                'is_approximate_1min': False, 'is_approximate_2min': False, 'is_approximate_3min': False,
                'is_approximate_4min': False, 'is_approximate_5min': False, 'is_approximate_10min': False,
                'is_approximate_30min': False, 'is_approximate_1hr': False, 'is_approximate_1.5hr': False,
                'is_approximate_2hr': False, 'is_approximate_2.5hr': False, 'is_approximate_3hr': False,
                'is_approximate_1day': False, 'is_approximate_2day': False, 'is_approximate_3day': False,
                'is_approximate_next_close': False,
                'actual_datetime_1min': None, 'actual_datetime_2min': None, 'actual_datetime_3min': None,
                'actual_datetime_4min': None, 'actual_datetime_5min': None, 'actual_datetime_10min': None,
                'actual_datetime_30min': None, 'actual_datetime_1hr': None, 'actual_datetime_1.5hr': None,
                'actual_datetime_2hr': None, 'actual_datetime_2.5hr': None, 'actual_datetime_3hr': None,
                'actual_datetime_1day': None, 'actual_datetime_2day': None, 'actual_datetime_3day': None,
                'actual_datetime_next_close': None,
            }
        
        if not ticker or not announcement_dt:
            return empty_results
        
        # Calculate date range: 5 days before announcement to 3 days after
        start_date = announcement_dt - timedelta(days=5)
        end_date = announcement_dt + timedelta(days=3)
        
        # Check if we already have batch data for this ticker (from pre-fetch)
        if ticker in self.batch_data_cache:
            daily_price_data = self.batch_data_cache[ticker]
            # PERFORMANCE: Removed verbose debug logging (called for every layoff)
        else:
            # Fallback: fetch if not pre-fetched (should rarely happen)
            daily_price_data = self._fetch_price_data_batch(ticker, start_date, end_date, '1d')
            
            # Store batch data for this ticker so other functions can use it without making new API calls
            if daily_price_data:
                self.batch_data_cache[ticker] = daily_price_data
        
        # PERFORMANCE: Removed verbose debug logging (called for every layoff)
        
        if not daily_price_data:
            # PERFORMANCE: Removed verbose debug logging (only log errors, not every missing data case)
            return empty_results
        
        # Extract base price (previous trading day's close)
        base_price = None
        prev_day = announcement_dt - timedelta(days=1)
        for attempt in range(5):
            price, is_exact, actual_ts = self._extract_price_from_batch(daily_price_data, prev_day, 'close')
            if price:
                base_price = price
                break
            prev_day = prev_day - timedelta(days=1)
        
        if not base_price:
            price, is_exact, actual_ts = self._extract_price_from_batch(daily_price_data, announcement_dt, 'close')
            base_price = price
        
        # Ensure base_price is a float, not a tuple (defensive check)
        if isinstance(base_price, tuple):
            base_price = base_price[0] if len(base_price) > 0 else None
        
        if not base_price:
            return empty_results
        
        # Check if market was open when article was published (needed for results and intraday logic)
        # Use ticker to determine exchange-specific market hours
        market_was_open = self.is_market_open(announcement_dt, ticker)
        
        # Extract prices for all needed dates from the batch data
        results = {
            'base_price': base_price,  # Store base price for chart reference
            'market_was_open': market_was_open,  # Market status when article was published
        }
        
        # For daily intervals (1day, 2day, 3day), extract from batch
        for day_offset in [1, 2, 3]:
            target_date = announcement_dt + timedelta(days=day_offset)
            price, is_exact, actual_ts = self._extract_price_from_batch(daily_price_data, target_date, 'close')
            # Ensure price is a float, not a tuple (defensive check)
            if isinstance(price, tuple):
                price = price[0] if len(price) > 0 else None
            if price:
                change_pct = ((price - base_price) / base_price) * 100 if base_price else None
                results[f'price_{day_offset}day'] = price
                results[f'change_{day_offset}day'] = change_pct
                results[f'date_{day_offset}day'] = target_date.date().isoformat()
                results[f'is_approximate_{day_offset}day'] = not is_exact
                # Convert actual timestamp to datetime if available
                if actual_ts:
                    actual_dt = datetime.fromtimestamp(actual_ts, tz=timezone.utc)
                    results[f'actual_datetime_{day_offset}day'] = actual_dt.isoformat()
                else:
                    results[f'actual_datetime_{day_offset}day'] = None
            else:
                results[f'price_{day_offset}day'] = None
                results[f'change_{day_offset}day'] = None
                results[f'date_{day_offset}day'] = target_date.date().isoformat()
                results[f'is_approximate_{day_offset}day'] = False
                results[f'actual_datetime_{day_offset}day'] = None
        
        # Next Trading Close: Always use the next trading day's close (even if article published during market hours)
        next_trading_day = self.get_next_trading_day(announcement_dt, ticker, daily_price_data)
        if next_trading_day:
            next_close_price, is_exact, actual_ts = self._extract_price_from_batch(daily_price_data, next_trading_day, 'close')
            # Ensure next_close_price is a float, not a tuple (defensive check)
            if isinstance(next_close_price, tuple):
                next_close_price = next_close_price[0] if len(next_close_price) > 0 else None
            if next_close_price:
                change_pct = ((next_close_price - base_price) / base_price) * 100 if base_price else None
                results['price_next_close'] = next_close_price
                results['change_next_close'] = change_pct
                results['date_next_close'] = next_trading_day.date().isoformat()
                results['is_approximate_next_close'] = not is_exact
                # Use actual timestamp if available and approximate, otherwise use calculated market close time
                if actual_ts and not is_exact:
                    actual_dt = datetime.fromtimestamp(actual_ts, tz=timezone.utc)
                    results['actual_datetime_next_close'] = actual_dt.isoformat()
                else:
                    # Calculate datetime at market close (4:00 PM ET) for this trading day
                    if next_trading_day.tzinfo is None:
                        next_close_dt_utc = next_trading_day.replace(tzinfo=timezone.utc)
                    else:
                        next_close_dt_utc = next_trading_day.astimezone(timezone.utc)
                    month = next_close_dt_utc.month
                    if month >= 3 and month <= 10:
                        et_offset_hours = -4  # EDT
                    else:
                        et_offset_hours = -5  # EST
                    et_time = next_close_dt_utc + timedelta(hours=et_offset_hours)
                    market_close_dt = et_time.replace(hour=16, minute=0, second=0, microsecond=0)
                    market_close_dt_utc = market_close_dt - timedelta(hours=et_offset_hours)
                    results['datetime_next_close'] = market_close_dt_utc.isoformat()
                    results['actual_datetime_next_close'] = market_close_dt_utc.isoformat()
                results['is_daily_close_next_close'] = True
            else:
                results['price_next_close'] = None
                results['change_next_close'] = None
                results['date_next_close'] = next_trading_day.date().isoformat() if next_trading_day else None
                results['is_approximate_next_close'] = False
                results['actual_datetime_next_close'] = None
        else:
            results['price_next_close'] = None
            results['change_next_close'] = None
            results['date_next_close'] = None
            results['is_approximate_next_close'] = False
            results['actual_datetime_next_close'] = None
        
        # For intraday intervals, we need intraday data (if market was open)
        
        if market_was_open:
            # Article published during trading hours
            article_day = announcement_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get open/close prices from batch data
            open_price, _, _ = self._extract_price_from_batch(daily_price_data, article_day, 'open')
            close_price, _, _ = self._extract_price_from_batch(daily_price_data, article_day, 'close')
            # Ensure prices are floats, not tuples (defensive check)
            if isinstance(open_price, tuple):
                open_price = open_price[0] if len(open_price) > 0 else None
            if isinstance(close_price, tuple):
                close_price = close_price[0] if len(close_price) > 0 else None
            
            # Get exchange-specific market open/close times
            market_open_utc = self._get_market_open_time(article_day, ticker)
            market_close_utc = self._get_market_close_time(article_day, ticker)
            
            if not market_open_utc or not market_close_utc:
                # Fallback to US hours if calculation fails
                market_open_utc = self._get_market_open_time(article_day, 'AAPL')
                market_close_utc = self._get_market_close_time(article_day, 'AAPL')
            
            # Calculate trading day length
            trading_day_length = (market_close_utc - market_open_utc).total_seconds() / 3600.0
            
            # Initialize time_from_open
            time_from_open = 0.0  # Default value
            
            # Calculate time from market open
            if announcement_dt.tzinfo is None:
                dt_utc = announcement_dt.replace(tzinfo=timezone.utc)
            else:
                dt_utc = announcement_dt.astimezone(timezone.utc)
            
            # Calculate time from market open
            time_diff = dt_utc - market_open_utc
            time_from_open = time_diff.total_seconds() / 3600.0  # Convert to hours
            # If before market open, time_from_open will be negative - clamp to 0
            if time_from_open < 0:
                time_from_open = 0.0
            
            # Fetch intraday data for the entire day once (batch fetch)
            # This avoids making multiple API calls for the same day
            # PERFORMANCE: Only fetch if date is within last 60 days (Prixe.io limit)
            now_utc = datetime.now(timezone.utc)
            if article_day.tzinfo is None:
                article_day_utc = article_day.replace(tzinfo=timezone.utc)
            else:
                article_day_utc = article_day.astimezone(timezone.utc)
            days_ago = (now_utc - article_day_utc).days
            intraday_data = None
            intraday_data_interval = None  # Track which interval we fetched
            if days_ago <= 60:
                # Try to fetch 1min data first (for 1min, 2min, 3min, 4min intervals)
                # 1min data has 30-day limit, so fall back to 5min if outside limit
                if days_ago <= 30:
                    intraday_data = self._fetch_intraday_data_for_day(ticker, article_day, interval='1min')
                    if intraday_data:
                        intraday_data_interval = '1min'
                # If 1min fetch failed or outside limit, use 5min data
                if not intraday_data:
                    intraday_data = self._fetch_intraday_data_for_day(ticker, article_day, interval='5min')
                    if intraday_data:
                        intraday_data_interval = '5min'
            
            # CRITICAL: If date is >60 days old, force intraday_data to None
            # This prevents using stale cached data that might have been valid when cached
            if days_ago > 60:
                intraday_data = None
                intraday_data_interval = None
            
            intervals = [
                ('1min', 1/60.0),    # 1 minute in hours
                ('2min', 2/60.0),    # 2 minutes in hours
                ('3min', 3/60.0),    # 3 minutes in hours
                ('4min', 4/60.0),    # 4 minutes in hours
                ('5min', 5/60.0),    # 5 minutes in hours
                ('10min', 10/60.0),  # 10 minutes in hours
                ('30min', 30/60.0),  # 30 minutes in hours
                ('1hr', 1.0),
                ('1.5hr', 1.5),
                ('2hr', 2.0),
                ('2.5hr', 2.5),
                ('3hr', 3.0),
            ]
            
            for interval_name, hours_after in intervals:
                target_time = time_from_open + hours_after
                
                # Calculate target datetime (announcement time + interval)
                if 'min' in interval_name:
                    minutes = int(interval_name.replace('min', ''))
                    target_datetime = announcement_dt + timedelta(minutes=minutes)
                elif 'hr' in interval_name:
                    if interval_name == '1hr':
                        target_datetime = announcement_dt + timedelta(hours=1)
                    else:
                        hours = float(interval_name.replace('hr', ''))
                        target_datetime = announcement_dt + timedelta(hours=hours)
                else:
                    target_datetime = announcement_dt + timedelta(hours=hours_after)
                
                # Convert target_datetime to UTC
                if target_datetime.tzinfo is None:
                    target_dt_utc = target_datetime.replace(tzinfo=timezone.utc)
                else:
                    target_dt_utc = target_datetime.astimezone(timezone.utc)
                
                # Check if target time is still within trading hours (using exchange-specific close time)
                is_after_market_close = target_dt_utc > market_close_utc
                is_before_market_open = target_dt_utc < market_open_utc
                
                if is_after_market_close or is_before_market_open:
                    # Target time is beyond market hours
                    results[f'price_{interval_name}'] = None
                    results[f'change_{interval_name}'] = None
                    results[f'date_{interval_name}'] = target_datetime.date().isoformat()
                    results[f'datetime_{interval_name}'] = target_datetime.isoformat()
                    results[f'market_closed_{interval_name}'] = True
                elif target_time <= trading_day_length:
                    # Target time is within trading hours - try to get intraday price
                    # Only use REAL intraday prices from API - NO interpolation
                    if intraday_data:
                        target_price, is_exact, actual_ts = self._extract_intraday_price_from_batch(intraday_data, target_datetime)
                        # Ensure target_price is a float, not a tuple (defensive check)
                        if isinstance(target_price, tuple):
                            target_price = target_price[0] if len(target_price) > 0 else None
                    else:
                        target_price = None
                        is_exact = False
                        actual_ts = None
                    
                    # Only set prices if we have real intraday data
                    # Also check: if we only have 5min data, skip 1min, 2min, 3min, 4min intervals
                    if target_price and intraday_data_interval:
                        # If we only have 5min data, we can't provide accurate 1min, 2min, 3min, 4min intervals
                        if intraday_data_interval == '5min' and interval_name in ['1min', '2min', '3min', '4min']:
                            # Skip these intervals - set to None
                            results[f'price_{interval_name}'] = None
                            results[f'change_{interval_name}'] = None
                            results[f'date_{interval_name}'] = target_datetime.date().isoformat()
                            results[f'datetime_{interval_name}'] = target_datetime.isoformat()
                            results[f'no_intraday_data_{interval_name}'] = True
                            results[f'is_approximate_{interval_name}'] = False
                            results[f'actual_datetime_{interval_name}'] = None
                            continue
                    
                    if target_price:
                        # Calculate change from base price
                        change_pct = ((target_price - base_price) / base_price) * 100 if base_price else None
                        
                        # Extract volume at interval time
                        target_volume = self._extract_intraday_volume_from_batch(intraday_data, target_datetime) if intraday_data else None
                        
                        # Calculate base volume (volume at announcement time)
                        base_volume = self._extract_intraday_volume_from_batch(intraday_data, announcement_dt) if intraday_data else None
                        
                        # If base volume is 0 or None, try to find first non-zero volume near announcement time
                        if (base_volume is None or base_volume == 0) and intraday_data:
                            data = intraday_data.get('data', {})
                            timestamps = data.get('timestamp', [])
                            volumes = data.get('volume', [])
                            
                            if timestamps and volumes:
                                # Find first non-zero volume within 30 minutes of announcement
                                announcement_ts = int(announcement_dt.astimezone(timezone.utc).timestamp())
                                announcement_plus_30min_ts = announcement_ts + (30 * 60)
                                
                                for i, ts in enumerate(timestamps):
                                    if announcement_ts <= ts <= announcement_plus_30min_ts and i < len(volumes):
                                        vol = volumes[i]
                                        if vol and vol > 0:
                                            base_volume = float(vol)
                                            break
                        
                        # Calculate volume change percentage
                        volume_change_pct = None
                        if target_volume and base_volume and base_volume > 0:
                            volume_change_pct = ((target_volume - base_volume) / base_volume) * 100
                        
                        results[f'price_{interval_name}'] = target_price
                        results[f'change_{interval_name}'] = change_pct
                        results[f'volume_change_{interval_name}'] = volume_change_pct
                        results[f'date_{interval_name}'] = target_datetime.date().isoformat()
                        results[f'is_approximate_{interval_name}'] = not is_exact
                        # Use actual timestamp if available and approximate, otherwise use target datetime
                        if actual_ts and not is_exact:
                            actual_dt = datetime.fromtimestamp(actual_ts, tz=timezone.utc)
                            results[f'datetime_{interval_name}'] = actual_dt.isoformat()
                            results[f'actual_datetime_{interval_name}'] = actual_dt.isoformat()
                        else:
                            results[f'datetime_{interval_name}'] = target_datetime.isoformat()
                            results[f'actual_datetime_{interval_name}'] = target_datetime.isoformat()
                        results[f'is_intraday_{interval_name}'] = True
                    else:
                        # No real intraday data available - use daily close as fallback
                        # This handles cases where:
                        # 1. Intraday data is not available (date >60 days old, Prixe.io limit)
                        # 2. Intraday data is sparse (< 5 data points)
                        # 3. Intraday data fetch failed
                        use_daily_close_fallback = False
                        if intraday_data:
                            data = intraday_data.get('data', {})
                            timestamps = data.get('timestamp', [])
                            if timestamps and len(timestamps) < 5:
                                # Intraday data is sparse - use daily close as fallback
                                use_daily_close_fallback = True
                        else:
                            # No intraday data at all - use daily close as fallback
                            use_daily_close_fallback = True
                        
                        if use_daily_close_fallback and close_price:
                            # Use daily close price as fallback when intraday data is unavailable
                            change_pct = ((close_price - base_price) / base_price) * 100 if base_price else None
                            results[f'price_{interval_name}'] = close_price
                            results[f'change_{interval_name}'] = change_pct
                            results[f'date_{interval_name}'] = target_datetime.date().isoformat()
                            results[f'datetime_{interval_name}'] = target_datetime.isoformat()
                            results[f'is_daily_close_{interval_name}'] = True
                            results[f'is_intraday_{interval_name}'] = False
                            results[f'is_approximate_{interval_name}'] = True  # Daily close is approximate for intraday intervals
                            results[f'actual_datetime_{interval_name}'] = target_datetime.isoformat()
                        else:
                            # No daily close price available either - don't show price
                            results[f'price_{interval_name}'] = None
                            results[f'change_{interval_name}'] = None
                            results[f'date_{interval_name}'] = target_datetime.date().isoformat()
                            results[f'datetime_{interval_name}'] = target_datetime.isoformat()
                            results[f'no_intraday_data_{interval_name}'] = True
                            results[f'is_approximate_{interval_name}'] = False
                            results[f'actual_datetime_{interval_name}'] = None
                else:
                    # Target time calculation suggests it's beyond trading day length
                    # But double-check with actual datetime - if still before market close, try to get price
                    if target_dt_utc <= market_close_utc:
                        # Still within market hours - try to get intraday price
                        if intraday_data:
                            target_price, is_exact, actual_ts = self._extract_intraday_price_from_batch(intraday_data, target_datetime)
                            # Ensure target_price is a float, not a tuple (defensive check)
                            if isinstance(target_price, tuple):
                                target_price = target_price[0] if len(target_price) > 0 else None
                        else:
                            target_price = None
                            is_exact = False
                            actual_ts = None
                        
                        if target_price:
                            change_pct = ((target_price - base_price) / base_price) * 100 if base_price else None
                            target_volume = self._extract_intraday_volume_from_batch(intraday_data, target_datetime) if intraday_data else None
                            base_volume = self._extract_intraday_volume_from_batch(intraday_data, announcement_dt) if intraday_data else None
                            
                            volume_change_pct = None
                            if target_volume and base_volume and base_volume > 0:
                                volume_change_pct = ((target_volume - base_volume) / base_volume) * 100
                            
                            results[f'price_{interval_name}'] = target_price
                            results[f'change_{interval_name}'] = change_pct
                            results[f'volume_change_{interval_name}'] = volume_change_pct
                            results[f'date_{interval_name}'] = target_datetime.date().isoformat()
                            results[f'is_approximate_{interval_name}'] = not is_exact
                            # Use actual timestamp if available and approximate, otherwise use target datetime
                            if actual_ts and not is_exact:
                                actual_dt = datetime.fromtimestamp(actual_ts, tz=timezone.utc)
                                results[f'datetime_{interval_name}'] = actual_dt.isoformat()
                                results[f'actual_datetime_{interval_name}'] = actual_dt.isoformat()
                            else:
                                results[f'datetime_{interval_name}'] = target_datetime.isoformat()
                                results[f'actual_datetime_{interval_name}'] = target_datetime.isoformat()
                            results[f'is_intraday_{interval_name}'] = True
                        else:
                            # No intraday data available - use daily close as fallback
                            if close_price:
                                change_pct = ((close_price - base_price) / base_price) * 100 if base_price else None
                                results[f'price_{interval_name}'] = close_price
                                results[f'change_{interval_name}'] = change_pct
                                results[f'date_{interval_name}'] = target_datetime.date().isoformat()
                                results[f'datetime_{interval_name}'] = target_datetime.isoformat()
                                results[f'is_daily_close_{interval_name}'] = True
                                results[f'is_intraday_{interval_name}'] = False
                                results[f'is_approximate_{interval_name}'] = True
                                results[f'actual_datetime_{interval_name}'] = target_datetime.isoformat()
                            else:
                                # No daily close price available either
                                results[f'price_{interval_name}'] = None
                                results[f'change_{interval_name}'] = None
                                results[f'date_{interval_name}'] = target_datetime.date().isoformat()
                                results[f'datetime_{interval_name}'] = target_datetime.isoformat()
                                results[f'no_intraday_data_{interval_name}'] = True
                                results[f'is_approximate_{interval_name}'] = False
                                results[f'actual_datetime_{interval_name}'] = None
                    else:
                        # Actually after market close
                        results[f'price_{interval_name}'] = None
                        results[f'change_{interval_name}'] = None
                        results[f'date_{interval_name}'] = target_datetime.date().isoformat()
                        results[f'datetime_{interval_name}'] = target_datetime.isoformat()
                        results[f'market_closed_{interval_name}'] = True
            
            # Daily intervals (1day, 2day) are already handled above in the batch extraction
            # No need to duplicate here
        
        else:
            # Article published when market was closed
            # Calculate +10min, +1hr, +3hr after market opens on next trading day using Prixe.io
            # Find next trading day and use batch data
            next_trading_day = self.get_next_trading_day(announcement_dt, ticker, daily_price_data)
            
            if not next_trading_day:
                # No next trading day found - mark all intervals as closed
                for interval_name in ['1min', '2min', '3min', '4min', '5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr', '3hr', '1day', '2day', '3day', 'next_close']:
                    results[f'price_{interval_name}'] = None
                    results[f'change_{interval_name}'] = None
                    results[f'date_{interval_name}'] = None
                    results[f'market_closed_{interval_name}'] = True
                return results
            
            if not self.is_future_date(next_trading_day):
                # Check if next trading day has actual trading data
                # Check if it's today - if so, allow it even if batch data doesn't have it yet
                now = datetime.now(timezone.utc)
                next_day_date = next_trading_day.date() if hasattr(next_trading_day, 'date') else next_trading_day.replace(hour=0, minute=0, second=0, microsecond=0).date()
                is_today = next_day_date == now.date()
                
                # Check if we have trading data
                has_data = self.has_trading_data_for_date(ticker, next_trading_day, daily_price_data)
                
                # If it's today and we don't have data in batch, try fetching fresh data
                if not has_data and is_today:
                    # Force a fresh check (this will make an API call if needed)
                    has_data = self.has_trading_data_for_date(ticker, next_trading_day, None)
                
                if not has_data and not is_today:
                    # Market was closed on next trading day (holiday) - mark all intervals as closed
                    for interval_name in ['1min', '2min', '3min', '4min', '5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr', '3hr']:
                        results[f'price_{interval_name}'] = None
                        results[f'change_{interval_name}'] = None
                        results[f'date_{interval_name}'] = next_trading_day.date().isoformat() if hasattr(next_trading_day, 'date') else str(next_trading_day)
                        results[f'market_closed_{interval_name}'] = True
                elif not has_data and is_today:
                    # Today but no data yet - mark as no data, not closed
                    for interval_name in ['1min', '2min', '3min', '4min', '5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr', '3hr']:
                        results[f'price_{interval_name}'] = None
                        results[f'change_{interval_name}'] = None
                        results[f'date_{interval_name}'] = next_trading_day.date().isoformat() if hasattr(next_trading_day, 'date') else str(next_trading_day)
                        results[f'market_closed_{interval_name}'] = False  # Not closed, just no data yet
                else:
                    # Get next trading day's open and close prices from batch data
                    open_price, _, _ = self._extract_price_from_batch(daily_price_data, next_trading_day, 'open')
                    close_price, _, _ = self._extract_price_from_batch(daily_price_data, next_trading_day, 'close')
                    # Ensure prices are floats, not tuples (defensive check)
                    if isinstance(open_price, tuple):
                        open_price = open_price[0] if len(open_price) > 0 else None
                    if isinstance(close_price, tuple):
                        close_price = close_price[0] if len(close_price) > 0 else None
                    
                    if open_price and close_price:
                        # Fetch intraday data for the next trading day once (batch fetch)
                        # This avoids making multiple API calls for the same day
                        # Try 1min data first (for 1min, 2min, 3min, 4min intervals)
                        # 1min data has 30-day limit, so fall back to 5min if outside limit
                        now_utc = datetime.now(timezone.utc)
                        next_day_utc = next_trading_day.replace(tzinfo=timezone.utc) if next_trading_day.tzinfo is None else next_trading_day.astimezone(timezone.utc)
                        days_ago = (now_utc - next_day_utc).days
                        intraday_data = None  # Initialize before use
                        intraday_data_interval = None  # Track which interval we fetched
                        if days_ago <= 30:
                            intraday_data = self._fetch_intraday_data_for_day(ticker, next_trading_day, interval='1min')
                            if intraday_data:
                                intraday_data_interval = '1min'
                        # If 1min fetch failed or outside limit, use 5min data
                        if not intraday_data and days_ago <= 60:
                            intraday_data = self._fetch_intraday_data_for_day(ticker, next_trading_day, interval='5min')
                            if intraday_data:
                                intraday_data_interval = '5min'
                        
                        # CRITICAL: If date is >60 days old, force intraday_data to None
                        # This prevents using stale cached data that might have been valid when cached
                        if days_ago > 60:
                            intraday_data = None
                            intraday_data_interval = None
                        
                        # Get exchange-specific market open time
                        market_open_utc = self._get_market_open_time(next_trading_day, ticker)
                        market_close_utc = self._get_market_close_time(next_trading_day, ticker)
                        
                        if not market_open_utc or not market_close_utc:
                            # Fallback to US hours if calculation fails
                            market_open_utc = self._get_market_open_time(next_trading_day, 'AAPL')
                            market_close_utc = self._get_market_close_time(next_trading_day, 'AAPL')
                        
                        # Calculate trading day length
                        trading_day_length = (market_close_utc - market_open_utc).total_seconds() / 3600.0
                        
                        # Calculate base volume ONCE before the loop (for consistency across all intervals)
                        base_volume = self._extract_intraday_volume_from_batch(intraday_data, market_open_utc) if intraday_data else None
                        
                        # If base volume is 0 or None, try to find first non-zero volume within first 30 minutes
                        if (base_volume is None or base_volume == 0) and intraday_data:
                            data = intraday_data.get('data', {})
                            timestamps = data.get('timestamp', [])
                            volumes = data.get('volume', [])
                            
                            if timestamps and volumes:
                                # Find first non-zero volume after market open (within 30 minutes)
                                market_open_ts = int(market_open_utc.timestamp())
                                market_open_plus_30min_ts = market_open_ts + (30 * 60)
                                
                                for i, ts in enumerate(timestamps):
                                    if market_open_ts <= ts <= market_open_plus_30min_ts and i < len(volumes):
                                        vol = volumes[i]
                                        if vol and vol > 0:
                                            base_volume = float(vol)
                                            break
                        
                        intervals = [
                            ('1min', 1/60.0),    # 1 minute = 1/60 hours after open
                            ('2min', 2/60.0),    # 2 minutes = 2/60 hours after open
                            ('3min', 3/60.0),    # 3 minutes = 3/60 hours after open
                            ('4min', 4/60.0),    # 4 minutes = 4/60 hours after open
                            ('5min', 5/60.0),    # 5 minutes = 5/60 hours after open
                            ('10min', 10/60.0),   # 10 minutes = 10/60 hours after open
                            ('30min', 30/60.0),   # 30 minutes = 30/60 hours after open
                            ('1hr', 1.0),          # 1 hour after open
                            ('1.5hr', 1.5),        # 1.5 hours after open
                            ('2hr', 2.0),          # 2 hours after open
                            ('2.5hr', 2.5),        # 2.5 hours after open
                            ('3hr', 3.0),         # 3 hours after open
                        ]
                        
                        for interval_name, hours_after_open in intervals:
                            # Calculate datetime: market open (exchange-specific) + hours_after_open
                            target_datetime_utc = market_open_utc + timedelta(hours=hours_after_open)
                            
                            # Interval is already added above when calculating target_datetime_utc
                            # No need to add again
                            
                            # Verify target datetime is actually a trading day with data
                            target_date_only = target_datetime_utc.replace(hour=0, minute=0, second=0, microsecond=0)
                            
                            # Check if it's today - if so, allow it even if batch data doesn't have it yet
                            now = datetime.now(timezone.utc)
                            is_today = target_date_only.date() == now.date()
                            
                            # Check if we have trading data
                            has_data = self.has_trading_data_for_date(ticker, target_date_only, daily_price_data)
                            
                            # If it's today and we don't have data in batch, try fetching fresh data
                            if not has_data and is_today:
                                # Force a fresh check (this will make an API call if needed)
                                has_data = self.has_trading_data_for_date(ticker, target_date_only, None)
                            
                            if not has_data and not is_today:
                                # Market was closed on this day - mark as closed
                                results[f'price_{interval_name}'] = None
                                results[f'change_{interval_name}'] = None
                                results[f'date_{interval_name}'] = target_datetime_utc.date().isoformat()
                                results[f'datetime_{interval_name}'] = target_datetime_utc.isoformat()
                                results[f'market_closed_{interval_name}'] = True
                                continue
                            elif not has_data and is_today:
                                # Today but no data yet - mark as no data, not closed
                                results[f'price_{interval_name}'] = None
                                results[f'change_{interval_name}'] = None
                                results[f'date_{interval_name}'] = target_datetime_utc.date().isoformat()
                                results[f'datetime_{interval_name}'] = target_datetime_utc.isoformat()
                                results[f'market_closed_{interval_name}'] = False  # Not closed, just no data yet
                                continue
                            
                            # Check if target time is within trading hours
                            if target_datetime_utc > market_close_utc:
                                # Target time is after market close
                                results[f'price_{interval_name}'] = None
                                results[f'change_{interval_name}'] = None
                                results[f'date_{interval_name}'] = target_datetime_utc.date().isoformat()
                                results[f'datetime_{interval_name}'] = target_datetime_utc.isoformat()
                                results[f'market_closed_{interval_name}'] = True
                                continue
                            
                            # Get actual intraday price at intervals after market open
                            # Only use REAL intraday prices from API - NO interpolation
                            if hours_after_open <= trading_day_length:
                                # Only use real intraday data from API
                                if intraday_data:
                                    target_price, is_exact, actual_ts = self._extract_intraday_price_from_batch(intraday_data, target_datetime_utc)
                                    # Ensure target_price is a float, not a tuple (defensive check)
                                    if isinstance(target_price, tuple):
                                        target_price = target_price[0] if len(target_price) > 0 else None
                                else:
                                    target_price = None
                                    is_exact = False
                                    actual_ts = None
                                
                                # Only set prices if we have real intraday data AND intraday_data is not None
                                # CRITICAL: If intraday_data is None (date >60 days old), never use target_price as intraday
                                # This prevents stale cached data from being treated as intraday data
                                if target_price and intraday_data is not None:
                                    # Calculate change from base price (not open price)
                                    change_pct = ((target_price - base_price) / base_price) * 100 if base_price else None
                                    
                                    # Extract volume at interval time
                                    target_volume = self._extract_intraday_volume_from_batch(intraday_data, target_datetime_utc) if intraday_data else None
                                    
                                    # Base volume already calculated before the loop (for consistency)
                                    
                                    # Calculate volume change percentage
                                    volume_change_pct = None
                                    if target_volume and base_volume and base_volume > 0:
                                        volume_change_pct = ((target_volume - base_volume) / base_volume) * 100
                                    
                                    # target_datetime_utc already calculated above
                                    
                                    results[f'price_{interval_name}'] = target_price
                                    results[f'change_{interval_name}'] = change_pct
                                    results[f'volume_change_{interval_name}'] = volume_change_pct
                                    results[f'date_{interval_name}'] = next_trading_day.date().isoformat()
                                    results[f'is_approximate_{interval_name}'] = not is_exact
                                    # Use actual timestamp if available and approximate, otherwise use target datetime
                                    if actual_ts and not is_exact:
                                        actual_dt = datetime.fromtimestamp(actual_ts, tz=timezone.utc)
                                        results[f'datetime_{interval_name}'] = actual_dt.isoformat()
                                        results[f'actual_datetime_{interval_name}'] = actual_dt.isoformat()
                                    else:
                                        results[f'datetime_{interval_name}'] = target_datetime_utc.isoformat()  # Store full datetime
                                        results[f'actual_datetime_{interval_name}'] = target_datetime_utc.isoformat()
                                    results[f'is_intraday_{interval_name}'] = True
                                else:
                                    # No real intraday data available - use daily close as fallback
                                    if close_price:
                                        change_pct = ((close_price - base_price) / base_price) * 100 if base_price else None
                                        results[f'price_{interval_name}'] = close_price
                                        results[f'change_{interval_name}'] = change_pct
                                        results[f'date_{interval_name}'] = next_trading_day.date().isoformat()
                                        results[f'datetime_{interval_name}'] = target_datetime_utc.isoformat()
                                        results[f'is_daily_close_{interval_name}'] = True
                                        results[f'is_intraday_{interval_name}'] = False
                                        results[f'is_approximate_{interval_name}'] = True
                                        results[f'actual_datetime_{interval_name}'] = target_datetime_utc.isoformat()
                                    else:
                                        # No daily close price available either
                                        results[f'price_{interval_name}'] = None
                                        results[f'change_{interval_name}'] = None
                                        results[f'date_{interval_name}'] = next_trading_day.date().isoformat()
                                        results[f'datetime_{interval_name}'] = target_datetime_utc.isoformat()
                                        results[f'no_intraday_data_{interval_name}'] = True
                                        results[f'is_approximate_{interval_name}'] = False
                                        results[f'actual_datetime_{interval_name}'] = None
                            else:
                                # Beyond trading hours - target_datetime_utc already calculated above
                                results[f'price_{interval_name}'] = None
                                results[f'change_{interval_name}'] = None
                                results[f'date_{interval_name}'] = next_trading_day.date().isoformat()
                                results[f'datetime_{interval_name}'] = target_datetime_utc.isoformat()
                                results[f'market_closed_{interval_name}'] = True
                    else:
                        # Prices not exact matches (likely from fallback) - mark as closed
                        for interval_name in ['1min', '2min', '3min', '4min', '5min', '10min', '30min', '1hr', '1.5hr', '2hr', '2.5hr', '3hr']:
                            results[f'price_{interval_name}'] = None
                            results[f'change_{interval_name}'] = None
                            results[f'date_{interval_name}'] = next_trading_day.date().isoformat() if hasattr(next_trading_day, 'date') else str(next_trading_day)
                            results[f'market_closed_{interval_name}'] = True
            else:
                # No price data or future date
                intervals = [
                        ('1min', 1/60.0),
                        ('2min', 2/60.0),
                        ('3min', 3/60.0),
                        ('4min', 4/60.0),
                        ('5min', 5/60.0),
                        ('10min', 10/60.0),
                        ('30min', 30/60.0),
                        ('1hr', 1.0),
                        ('1.5hr', 1.5),
                        ('2hr', 2.0),
                        ('2.5hr', 2.5),
                        ('3hr', 3.0),
                    ]
                for interval_name, hours_after_open in intervals:
                    # Calculate datetime: market open + hours_after_open
                    month = next_trading_day.month if isinstance(next_trading_day, datetime) else next_trading_day.month
                    if month >= 3 and month <= 10:
                        et_offset_hours = -4
                    else:
                        et_offset_hours = -5
                    
                    # Create ET timezone
                    et_tz = timezone(timedelta(hours=et_offset_hours))
                    
                    # Create datetime at 9:30 AM ET on next_trading_day's date, then add interval
                    if isinstance(next_trading_day, datetime):
                        next_trading_day_date = next_trading_day.date()
                    else:
                        next_trading_day_date = next_trading_day
                    
                    from datetime import time as dt_time
                    target_datetime_et = datetime.combine(next_trading_day_date, dt_time(9, 30, 0))
                    target_datetime_et = target_datetime_et.replace(tzinfo=et_tz)
                    
                    # Add the interval
                    if 'min' in interval_name:
                        minutes = int(interval_name.replace('min', ''))
                        target_datetime_et = target_datetime_et + timedelta(minutes=minutes)
                    elif 'hr' in interval_name:
                        if interval_name == '1hr':
                            target_datetime_et = target_datetime_et + timedelta(hours=1)
                        else:
                            hours = float(interval_name.replace('hr', ''))
                            target_datetime_et = target_datetime_et + timedelta(hours=hours)
                    else:
                        target_datetime_et = target_datetime_et + timedelta(hours=hours_after_open)
                    
                    # Convert back to UTC for storage
                    target_datetime_utc = target_datetime_et.astimezone(timezone.utc)
                    
                    results[f'price_{interval_name}'] = None
                    results[f'change_{interval_name}'] = None
                    results[f'date_{interval_name}'] = next_trading_day.date().isoformat()
                    results[f'datetime_{interval_name}'] = target_datetime_utc.isoformat()  # Store datetime
                    results[f'market_closed_{interval_name}'] = True
            
            # Daily intervals: +1day, +2days
            intervals = [
                ('1day', 0),   # Next trading day
                ('2day', 1),   # 2nd trading day after
            ]
            
            for interval_name, trading_days_offset in intervals:
                if trading_days_offset == 0:
                    target_dt = next_trading_day
                else:
                    target_dt = next_trading_day
                    for _ in range(trading_days_offset):
                        target_dt = self.get_next_trading_day(target_dt, ticker, daily_price_data)
                        if not target_dt:
                            break
                
                if not target_dt:
                    results[f'price_{interval_name}'] = None
                    results[f'change_{interval_name}'] = None
                    estimated_date = next_trading_day + timedelta(days=trading_days_offset + 1)
                    results[f'date_{interval_name}'] = estimated_date.date().isoformat() if not self.is_future_date(estimated_date) else None
                    results[f'market_closed_{interval_name}'] = True
                    continue
                
                if self.is_future_date(target_dt):
                    results[f'price_{interval_name}'] = None
                    results[f'change_{interval_name}'] = None
                    results[f'date_{interval_name}'] = target_dt.date().isoformat()
                    results[f'market_closed_{interval_name}'] = True
                    continue
                
                price, is_exact, actual_ts = self._extract_price_from_batch(daily_price_data, target_dt, 'close')
                # Ensure price is a float, not a tuple (defensive check)
                if isinstance(price, tuple):
                    price = price[0] if len(price) > 0 else None
                
                if price:
                    change_pct = ((price - base_price) / base_price) * 100
                    results[f'is_approximate_{interval_name}'] = not is_exact
                    # Convert actual timestamp to datetime if available
                    if actual_ts:
                        actual_dt = datetime.fromtimestamp(actual_ts, tz=timezone.utc)
                        results[f'actual_datetime_{interval_name}'] = actual_dt.isoformat()
                    else:
                        results[f'actual_datetime_{interval_name}'] = None
                    # Calculate datetime at market close (4:00 PM ET) for this trading day
                    if target_dt.tzinfo is None:
                        target_dt_utc = target_dt.replace(tzinfo=timezone.utc)
                    else:
                        target_dt_utc = target_dt.astimezone(timezone.utc)
                    
                    # Set to 4:00 PM ET (market close)
                    month = target_dt_utc.month
                    if month >= 3 and month <= 10:
                        et_offset_hours = -4  # EDT
                    else:
                        et_offset_hours = -5  # EST
                    
                    # Create datetime at 4:00 PM ET on target date
                    target_date_et = target_dt_utc + timedelta(hours=et_offset_hours)
                    target_datetime = target_date_et.replace(hour=16, minute=0, second=0, microsecond=0)
                    # Convert back to UTC
                    target_datetime_utc = target_datetime - timedelta(hours=et_offset_hours)
                    if target_datetime_utc.tzinfo is None:
                        target_datetime_utc = target_datetime_utc.replace(tzinfo=timezone.utc)
                    
                    results[f'price_{interval_name}'] = price
                    results[f'change_{interval_name}'] = change_pct
                    results[f'date_{interval_name}'] = target_dt.date().isoformat()
                    results[f'datetime_{interval_name}'] = target_datetime_utc.isoformat()  # Store full datetime at market close
                else:
                    # Calculate datetime at market close (4:00 PM ET) for this trading day
                    if target_dt.tzinfo is None:
                        target_dt_utc = target_dt.replace(tzinfo=timezone.utc)
                    else:
                        target_dt_utc = target_dt.astimezone(timezone.utc)
                    
                    month = target_dt_utc.month
                    if month >= 3 and month <= 10:
                        et_offset_hours = -4
                    else:
                        et_offset_hours = -5
                    
                    # Create datetime at 4:00 PM ET on target date (correct timezone conversion)
                    et_tz = timezone(timedelta(hours=et_offset_hours))
                    target_date = target_dt_utc.date() if hasattr(target_dt_utc, 'date') else target_dt_utc
                    if isinstance(target_date, datetime):
                        target_date = target_date.date()
                    
                    from datetime import time as dt_time
                    target_datetime_et = datetime.combine(target_date, dt_time(16, 0, 0))
                    target_datetime_et = target_datetime_et.replace(tzinfo=et_tz)
                    
                    # Convert back to UTC
                    target_datetime_utc = target_datetime_et.astimezone(timezone.utc)
                    
                    results[f'price_{interval_name}'] = None
                    results[f'change_{interval_name}'] = None
                    results[f'date_{interval_name}'] = target_dt.date().isoformat()
                    results[f'datetime_{interval_name}'] = target_datetime_utc.isoformat()  # Store datetime
                    results[f'market_closed_{interval_name}'] = True
            
            # Next Trading Close: For market-closed case, next_trading_day is already calculated above
            # Use its close price (this is the next trading day after the article was published)
            if next_trading_day:
                next_close_price, is_exact, actual_ts = self._extract_price_from_batch(daily_price_data, next_trading_day, 'close')
                # Ensure next_close_price is a float, not a tuple (defensive check)
                if isinstance(next_close_price, tuple):
                    next_close_price = next_close_price[0] if len(next_close_price) > 0 else None
                if next_close_price:
                    change_pct = ((next_close_price - base_price) / base_price) * 100 if base_price else None
                    results['price_next_close'] = next_close_price
                    results['change_next_close'] = change_pct
                    results['date_next_close'] = next_trading_day.date().isoformat()
                    results['is_approximate_next_close'] = not is_exact
                    # Convert actual timestamp to datetime if available
                    if actual_ts:
                        actual_dt = datetime.fromtimestamp(actual_ts, tz=timezone.utc)
                        results['actual_datetime_next_close'] = actual_dt.isoformat()
                    else:
                        results['actual_datetime_next_close'] = None
                    # Calculate datetime at market close (4:00 PM ET) for this trading day
                    if next_trading_day.tzinfo is None:
                        next_close_dt_utc = next_trading_day.replace(tzinfo=timezone.utc)
                    else:
                        next_close_dt_utc = next_trading_day.astimezone(timezone.utc)
                    month = next_close_dt_utc.month
                    if month >= 3 and month <= 10:
                        et_offset_hours = -4  # EDT
                    else:
                        et_offset_hours = -5  # EST
                    et_time = next_close_dt_utc + timedelta(hours=et_offset_hours)
                    market_close_dt = et_time.replace(hour=16, minute=0, second=0, microsecond=0)
                    market_close_dt_utc = market_close_dt - timedelta(hours=et_offset_hours)
                    results['datetime_next_close'] = market_close_dt_utc.isoformat()
                    results['is_daily_close_next_close'] = True
                else:
                    results['price_next_close'] = None
                    results['change_next_close'] = None
                    results['date_next_close'] = next_trading_day.date().isoformat() if next_trading_day else None
            else:
                results['price_next_close'] = None
                results['change_next_close'] = None
                results['date_next_close'] = None
        
        # Get price history from article date to now
        # OPTIMIZATION: Cache price history per ticker to avoid recalculating for each layoff
        cache_key = f"price_history_{ticker}"
        if cache_key not in self.price_history_cache:
            # Calculate once per ticker (from earliest announcement to now)
            # Limit to last 60 days to reduce data size
            history_start = announcement_dt - timedelta(days=60)
            price_history = self.get_stock_price_history(ticker, history_start)
            self.price_history_cache[cache_key] = price_history
        else:
            # Use cached price history, but filter to this layoff's date range
            cached_history = self.price_history_cache[cache_key]
            # Filter to dates from announcement_dt onwards
            announcement_timestamp = int(announcement_dt.timestamp() * 1000)  # Convert to milliseconds
            price_history = [p for p in cached_history if p.get('timestamp', 0) >= announcement_timestamp]
        
        results['price_history'] = price_history
        
        # PERFORMANCE: Removed API summary logging (called for every layoff - too verbose)
        # API call count is logged once at the end of fetch_layoffs instead
        
        return results
    
    def _get_bio_pharma_tickers(self, category: str = 'all') -> Dict[str, str]:
        """Get hardcoded company name -> ticker mapping for bio/pharma companies
        
        Args:
            category: 'small_cap_with_options', 'small_cap', 'mid_cap', or 'all' (default)
        
        Returns:
            Dictionary mapping company name (uppercase) to ticker symbol
        """
        if category == 'small_cap_with_options':
            # Hardcoded ticker mapping for small-cap biotech with options (verified)
            return {
                'ADAPTIMMUNE': 'ADAPY',
                'AGENUS': 'AGEN',
                'APELLIS PHARMACEUTICALS': 'APLS',
                'ARCTURUS THERAPEUTICS': 'ARCT',
                'ARVINAS': 'ARVN',
                'ATHIRA PHARMA': 'ATHA',
                'AUTOLUS THERAPEUTICS': 'AUTL',
                'BEAM THERAPEUTICS': 'BEAM',
                'BIOXCEL THERAPEUTICS': 'BTAI',
                'BRIDGEBIO PHARMA': 'BBIO',
                'CARA THERAPEUTICS': 'BCAX',
                'CARTESIAN THERAPEUTICS': 'RNAC',
                'CASSAVA SCIENCES': 'SAVA',
                'CENTURY THERAPEUTICS': 'IPSC',
                'CORMEDIX': 'CRMD',
                'CRISPR THERAPEUTICS': 'CRSP',
                'CUMBERLAND PHARMACEUTICALS': 'CPIX',
                'CYTOMX THERAPEUTICS': 'CTMX',
                'ESPERION THERAPEUTICS': 'ESPR',
                'FATE THERAPEUTICS': 'FATE',
                'FIBROGEN': 'FGEN',
                'GOSSAMER BIO': 'GOSS',
                'IMMUNOCORE': 'IMCR',
                'IMMUNOMEDICS': 'IMNM',
                'IMMUNOVANT': 'IMVT',
                'INOVIO PHARMACEUTICALS': 'INO',
                'INSPIREMD': 'NSPR',
                'INTELLIA THERAPEUTICS': 'NTLA',
                'IOVANCE BIOTHERAPEUTICS': 'IOVA',
                'JAZZ PHARMACEUTICALS': 'JAZZ',
                'KINIKSA PHARMACEUTICALS': 'KNSA',
                'KURA ONCOLOGY': 'KURA',
                'KYMERA THERAPEUTICS': 'KYMR',
                'NEUROCRINE BIOSCIENCES': 'NBIX',
                'NOVOCURE': 'NVCR',
                'ORIC PHARMACEUTICS': 'ORIC',
                'PERSONALIS': 'PSNL',
                'PRECISION BIOSCIENCES': 'DTIL',
                'PTC THERAPEUTICS': 'PTCT',
                'PYXIS ONCOLOGY': 'PYXS',
                'RAPT THERAPEUTICS': 'RAPT',
                'REPLIMUNE': 'REPL',
                'RIGEL PHARMACEUTICS': 'RIGL',
                'SANGAMO THERAPEUTICS': 'SGMO',
                'SERES THERAPEUTICS': 'MCRB',
                'SOLID BIOSCIENCES': 'SLDB',
                'TELA BIO': 'TELA',
                'THERAVANCE BIOPHARMA': 'TBPH',
                'VERICEL': 'VCEL',
                'VIKING THERAPEUTICS': 'VKTX',
                'VISTAGEN THERAPEUTICS': 'VTGN',
                'VIVEVE MEDICAL': 'MPW',
                'WAVE LIFE SCIENCES': 'WVE',
                'XENCOR': 'XNCR',
                # Recently added missing companies
                'EQUILLIUM': 'EQ',
                'ABIVAX': 'ABVX',
                'QUANTUM BIOPHARMA': 'QNTM',
                'AMYLYX PHARMACEUTICALS': 'AMLX',
                'THARIMMUNE': 'THAR',
            }
        # For other categories, also return ticker mappings (fall back to SEC EDGAR if not found)
        # Add common ticker mappings that work across all categories
        common_tickers = {
            'EQUILLIUM': 'EQ',
            'ABIVAX': 'ABVX',
            'QUANTUM BIOPHARMA': 'QNTM',
            'AMYLYX PHARMACEUTICALS': 'AMLX',
            'THARIMMUNE': 'THAR',
            'CORCEPT THERAPEUTICS': 'CORT',
        }
        return common_tickers
    
    def _get_bio_pharma_companies(self, category: str = 'all') -> List[str]:
        """Get list of liquid biotech/pharma company names for Google News search
        Filtered for high liquidity and options availability
        
        Args:
            category: 'small_cap', 'small_cap_with_options', 'mid_cap', or 'all' (default)
        """
        if category == 'small_cap_with_options':
            # Small-cap biotech with verified options trading (54 companies)
            # Only includes companies that have options with volume > 0
            small_cap_bio_with_options = [
                'ADAPTIMMUNE', 'AGENUS', 'APELLIS PHARMACEUTICALS', 'ARCTURUS THERAPEUTICS',
                'ARVINAS', 'ATHIRA PHARMA', 'AUTOLUS THERAPEUTICS', 'BEAM THERAPEUTICS',
                'BIOXCEL THERAPEUTICS', 'BRIDGEBIO PHARMA', 'CARA THERAPEUTICS',
                'CARTESIAN THERAPEUTICS', 'CASSAVA SCIENCES', 'CENTURY THERAPEUTICS',
                'CORMEDIX', 'CRISPR THERAPEUTICS', 'CUMBERLAND PHARMACEUTICALS',
                'CYTOMX THERAPEUTICS', 'ESPERION THERAPEUTICS', 'FATE THERAPEUTICS',
                'FIBROGEN', 'GOSSAMER BIO', 'IMMUNOCORE', 'IMMUNOMEDICS', 'IMMUNOVANT',
                'INOVIO PHARMACEUTICALS', 'INSPIREMD', 'INTELLIA THERAPEUTICS',
                'IOVANCE BIOTHERAPEUTICS', 'JAZZ PHARMACEUTICALS', 'KINIKSA PHARMACEUTICALS',
                'KURA ONCOLOGY', 'KYMERA THERAPEUTICS', 'NEUROCRINE BIOSCIENCES',
                'NOVOCURE', 'ORIC PHARMACEUTICS', 'PERSONALIS', 'PRECISION BIOSCIENCES',
                'PTC THERAPEUTICS', 'PYXIS ONCOLOGY', 'RAPT THERAPEUTICS', 'REPLIMUNE',
                'RIGEL PHARMACEUTICS', 'SANGAMO THERAPEUTICS', 'SERES THERAPEUTICS',
                'SOLID BIOSCIENCES', 'TELA BIO', 'THERAVANCE BIOPHARMA', 'VERICEL',
                'VIKING THERAPEUTICS', 'VISTAGEN THERAPEUTICS', 'VIVEVE MEDICAL',
                'WAVE LIFE SCIENCES', 'XENCOR',
                # Recently added missing companies
                'EQUILLIUM', 'ABIVAX', 'QUANTUM BIOPHARMA', 'AMYLYX PHARMACEUTICALS',
                'THARIMMUNE'
            ]
            bio_companies = [c.upper().strip() for c in small_cap_bio_with_options if c]
            print(f"[SMALL-CAP BIO WITH OPTIONS] Using {len(bio_companies)} small-cap biotech companies (verified options with volume) for search")
            return bio_companies
        
        elif category == 'small_cap':
            # Small-cap biotech (market cap ~$300M-$2B, high volume ≥500K ADV)
            # Focus on liquid small-caps with active trading and options
            small_cap_bio = [
                # High-volume small-cap biotech (500K-2M+ ADV)
                'ATHIRA PHARMA', 'CENTURY THERAPEUTICS', 'VISTAGEN THERAPEUTICS',
                'PYXIS ONCOLOGY', 'GEOVAX LABS', 'NOVABAY PHARMACEUTICALS',
                'CUMBERLAND PHARMACEUTICALS', 'AMC ROBOTICS CORPORATION',
                'FATE THERAPEUTICS', 'FIBROGEN', 'GOSSAMER BIO', 'IMMUNOGEN',
                'INOVIO PHARMACEUTICALS', 'KURA ONCOLOGY', 'PORTOLA PHARMACEUTICALS',
                'PRECISION BIOSCIENCES', 'RUBIUS THERAPEUTICS', 'SERES THERAPEUTICS',
                'SYNERGY PHARMACEUTICALS', 'SYROS PHARMACEUTICS', 'THERAVANCE BIOPHARMA',
                'TRACON PHARMACEUTICALS', 'ADAPTIMMUNE', 'AGENUS', 'ALLOZYME',
                'ALPHATECHNOLOGIES', 'APELLIS PHARMACEUTICALS', 'ARCTURUS THERAPEUTICS',
                # Recently added missing companies
                'EQUILLIUM', 'ABIVAX', 'QUANTUM BIOPHARMA', 'AMYLYX PHARMACEUTICALS',
                'THARIMMUNE',
                'ARIDIS PHARMACEUTICALS', 'ARVINAS', 'ASLAN PHARMACEUTICALS',
                'AUTOLUS THERAPEUTICS', 'BEAM THERAPEUTICS', 'BELLICUM PHARMACEUTICALS',
                'BIOXCEL THERAPEUTICS', 'BLUEBIRD BIO', 'BRIDGEBIO PHARMA',
                'CARA THERAPEUTICS', 'CARTESIAN THERAPEUTICS', 'CASSAVA SCIENCES',
                'CEREVEL THERAPEUTICS', 'CORMEDIX', 'CRISPR THERAPEUTICS',
                'CURIS', 'CUTERA', 'CYTOMX THERAPEUTICS', 'DICERNA PHARMACEUTICALS',
                'DYNATRONICS', 'EIDOS THERAPEUTICS', 'EPIZYME', 'ESPERION THERAPEUTICS',
                'FREELINE THERAPEUTICS', 'GEMINI THERAPEUTICS', 'GOSSAMER BIO',
                'HARPOON THERAPEUTICS', 'HOMOLOGY MEDICINES', 'IMMUNOCORE',
                'IMMUNOMEDICS', 'IMMUNOVANT', 'INSPIREMD', 'INTELLIA THERAPEUTICS',
                'IOVANCE BIOTHERAPEUTICS', 'JAZZ PHARMACEUTICALS', 'KINIKSA PHARMACEUTICALS',
                'KINNATE BIOPHARMA', 'KITE PHARMA', 'KURA ONCOLOGY', 'KYMERA THERAPEUTICS',
                'MAGENTA THERAPEUTICS', 'MIRATI THERAPEUTICS', 'MOLECULAR TEMPLATES',
                'NANTK WEST', 'NANTKWEST', 'NEUROCRINE BIOSCIENCES', 'NEXTECH BIOMATERIALS',
                'NOVOCURE', 'NUVATION BIO', 'ONCOCYTE', 'ONCOMED PHARMACEUTICALS',
                'ORIC PHARMACEUTICALS', 'PELOTON THERAPEUTICS', 'PERSONALIS',
                'PHASEBIO PHARMACEUTICALS', 'PTC THERAPEUTICS', 'RA PHARMACEUTICALS',
                'RAPT THERAPEUTICS', 'REPLIMUNE', 'REVANCE THERAPEUTICS',
                'RIGEL PHARMACEUTICALS', 'RUBIUS THERAPEUTICS', 'SAGE THERAPEUTICS',
                'SANGAMO THERAPEUTICS', 'SERES THERAPEUTICS', 'SERONO',
                'SIGILON THERAPEUTICS', 'SILENCE THERAPEUTICS', 'SOLID BIOSCIENCES',
                'SPARK THERAPEUTICS', 'SYNERGY PHARMACEUTICALS', 'SYROS PHARMACEUTICS',
                'TARONIS THERAPEUTICS', 'TCR2 THERAPEUTICS', 'TELA BIO',
                'TENAX THERAPEUTICS', 'THERAVANCE BIOPHARMA', 'TRACON PHARMACEUTICALS',
                'TURNSTONE BIOLOGICS', 'UNITY BIOTECHNOLOGY', 'VERASTEM ONCOLOGY',
                'VERICEL', 'VIELA BIO', 'VIKING THERAPEUTICS', 'VISTAGEN THERAPEUTICS',
                'VIVEVE MEDICAL', 'WAVE LIFE SCIENCES', 'XENCOR', 'ZIOPHARM ONCOLOGY'
            ]
            bio_companies = [c.upper().strip() for c in small_cap_bio if c]
            print(f"[SMALL-CAP BIO] Using {len(bio_companies)} small-cap biotech companies (≥500K ADV, high volume) for search")
            return bio_companies
        
        elif category == 'mid_cap':
            # Mid-cap biotech (market cap ~$2B-$10B, high volume ≥1M ADV)
            # Focus on established mid-caps with strong liquidity and options
            mid_cap_bio = [
                # Mid-cap biotech with high volume (1M-5M+ ADV) - Actively traded
                'MODERNA', 'BIONTECH', 'NOVAVAX', 'ILLUMINA', 'VERTEX PHARMACEUTICALS',
                'ALNYLAM', 'EXELIXIS', 'INCYTE', 'SEATTLE GENETICS',
                'CLOVIS ONCOLOGY', 'HORIZON THERAPEUTICS', 'INTERCEPT PHARMACEUTICALS',
                'KARYOPHARM THERAPEUTICS', 'MIRATI THERAPEUTICS', 'NOVOCURE',
                'RIGEL PHARMACEUTICALS', 'SANGAMO THERAPEUTICS', 'ZOETIS',
                # From web research - actively traded mid-caps
                'ULTRAGENYX PHARMACEUTICAL', 'AMICUS THERAPEUTICS', 'ADMA BIOLOGICS',
                'VIKING THERAPEUTICS', 'VERVE THERAPEUTICS', 'BIO-TECHNE',
                'PENUMBRA', 'ALEXION PHARMACEUTICALS', 'ALKERMES', 'AMARIN',
                'ARENA PHARMACEUTICALS', 'BIOGEN', 'BLUEBIRD BIO', 'CARA THERAPEUTICS',
                'CEREVEL THERAPEUTICS', 'CRISPR THERAPEUTICS', 'EPIZYME',
                'ESPERION THERAPEUTICS', 'FATE THERAPEUTICS', 'FIBROGEN',
                'GOSSAMER BIO', 'IMMUNOGEN', 'INTELLIA THERAPEUTICS',
                'IOVANCE BIOTHERAPEUTICS', 'JAZZ PHARMACEUTICALS', 'KITE PHARMA',
                'KURA ONCOLOGY', 'NEUROCRINE BIOSCIENCES', 'PTC THERAPEUTICS',
                'SAGE THERAPEUTICS', 'SPARK THERAPEUTICS', 'SYNERGY PHARMACEUTICS',
                'SYROS PHARMACEUTICS', 'THERAVANCE BIOPHARMA', 'TRACON PHARMACEUTICALS',
                'XENCOR', 'ACADIA PHARMACEUTICALS', 'ARQULE', 'AUTOLUS THERAPEUTICS',
                'DICERNA PHARMACEUTICS', 'CORCEPT THERAPEUTICS'
            ]
            # Remove duplicates while preserving order
            seen = set()
            unique_mid_cap = []
            for c in mid_cap_bio:
                c_upper = c.upper().strip()
                if c_upper and c_upper not in seen:
                    seen.add(c_upper)
                    unique_mid_cap.append(c_upper)
            print(f"[MID-CAP BIO] Using {len(unique_mid_cap)} mid-cap biotech companies (≥1M ADV, high volume) for search")
            return unique_mid_cap
        
        else:
            # Default: All liquid biotech/pharma (backwards compatibility)
            # Curated list of liquid biotech/pharma stocks with options trading
            # Criteria: Average Daily Volume ≥ 1M shares, active options markets
            liquid_bio_companies = [
                # Large-cap pharma (very liquid, high volume)
                'PFIZER', 'MERCK', 'JOHNSON & JOHNSON', 'ABBVIE', 'BRISTOL-MYERS SQUIBB',
                'AMGEN', 'GILEAD SCIENCES', 'BIOGEN', 'REGENERON',
                'NOVARTIS', 'ROCHE', 'GLAXOSMITHKLINE', 'SANOFI', 'ASTRAZENECA',
                
                # Mid-to-large cap biotech (liquid, active options)
                'MODERNA', 'BIONTECH', 'NOVAVAX', 'ILLUMINA', 'VERTEX PHARMACEUTICALS',
                'ALNYLAM', 'SAGE THERAPEUTICS', 'BLUEBIRD BIO', 'SPARK THERAPEUTICS',
                'NEUROCRINE BIOSCIENCES', 'EXELIXIS', 'INCYTE', 'SEATTLE GENETICS',
                'CLOVIS ONCOLOGY', 'ACADIA PHARMACEUTICALS', 'HORIZON THERAPEUTICS',
                'INTERCEPT PHARMACEUTICALS', 'KARYOPHARM THERAPEUTICS', 'MIRATI THERAPEUTICS',
                'NOVOCURE', 'RIGEL PHARMACEUTICALS', 'SANGAMO THERAPEUTICS',                 'ZOETIS',
                'CORCEPT THERAPEUTICS',
                
                # Smaller but still liquid (500K-1M+ ADV, options available)
                'ATHIRA PHARMA', 'CENTURY THERAPEUTICS', 'VISTAGEN THERAPEUTICS',
                'PYXIS ONCOLOGY', 'GEOVAX LABS', 'NOVABAY PHARMACEUTICALS',
                'CUMBERLAND PHARMACEUTICALS', 'AMC ROBOTICS CORPORATION',
                'FATE THERAPEUTICS', 'FIBROGEN', 'GOSSAMER BIO', 'IMMUNOGEN',
                'INOVIO PHARMACEUTICALS', 'KURA ONCOLOGY', 'PORTOLA PHARMACEUTICALS',
                'PRECISION BIOSCIENCES', 'RUBIUS THERAPEUTICS', 'SERES THERAPEUTICS',
                'SYNERGY PHARMACEUTICALS', 'SYROS PHARMACEUTICS', 'THERAVANCE BIOPHARMA',
                'TRACON PHARMACEUTICALS'
            ]
            bio_companies = [c.upper().strip() for c in liquid_bio_companies if c]
            print(f"[BIO COMPANIES] Using {len(bio_companies)} liquid companies (≥1M ADV, options available) for search")
            return bio_companies
    
    def _get_real_estate_companies(self) -> List[str]:
        """Get list of liquid real estate company names (REITs, developers, etc.) for Google News search
        Focused on high liquidity and options availability
        
        Returns:
            List of company names in uppercase
        """
        # Major REITs and real estate companies with high liquidity (≥1M ADV, options available)
        # Includes major REITs across sectors: residential, commercial, healthcare, retail, industrial
        liquid_real_estate_companies = [
            # Major REITs - Residential
            'AMERICAN HOMES 4 RENT', 'AVALONBAY COMMUNITIES', 'EQUITY RESIDENTIAL',
            'MID-AMERICA APARTMENT COMMUNITIES', 'UDR', 'ESSENTIAL PROPERTIES REALTY TRUST',
            'SUN COMMUNITIES', 'EQUITY LIFESTYLE PROPERTIES', 'INVITATION HOMES',
            
            # Major REITs - Commercial/Office
            'BOSTON PROPERTIES', 'SL GREEN REALTY', 'VORNADO REALTY TRUST',
            'ALEXANDRIA REAL ESTATE EQUITIES', 'KILROY REALTY', 'COUSINS PROPERTIES',
            'DOUGLAS EMMETT', 'HUDSON PACIFIC PROPERTIES', 'BRANDYWINE REALTY TRUST',
            
            # Major REITs - Retail
            'SIMON PROPERTY GROUP', 'MACERICH', 'TAUBMAN CENTERS',
            'KIMCO REALTY', 'REGENCY CENTERS', 'FEDERAL REALTY INVESTMENT TRUST',
            'REALTY INCOME', 'NATIONAL RETAIL PROPERTIES', 'STORE CAPITAL',
            
            # Major REITs - Industrial
            'PROLOGIS', 'DUKE REALTY', 'FIRST INDUSTRIAL REALTY TRUST',
            'EASTGROUP PROPERTIES', 'STAG INDUSTRIAL', 'TERRENO REALTY',
            
            # Major REITs - Healthcare
            'WELLTOWER', 'VENTAS', 'HEALTHCARE REALTY TRUST',
            'MEDICAL PROPERTIES TRUST', 'HCP', 'SABRA HEALTHCARE REIT',
            
            # Major REITs - Data Centers
            'EQUINIX', 'DIGITAL REALTY TRUST', 'CORE SITE',
            
            # Major REITs - Cell Towers
            'AMERICAN TOWER', 'CROWN CASTLE', 'SBA COMMUNICATIONS',
            
            # Major REITs - Self Storage
            'PUBLIC STORAGE', 'EXTRA SPACE STORAGE', 'CUBESMART',
            'LIFESTORAGE', 'NATIONAL STORAGE AFFILIATES',
            
            # Major REITs - Hotels
            'HOST HOTELS & RESORTS', 'PARK HOTELS & RESORTS', 'RLJ LODGING TRUST',
            'PEBBLEBROOK HOTEL TRUST', 'XENIA HOTELS & RESORTS',
            
            # Major REITs - Diversified
            'W.P. CAREY', 'REALTY INCOME', 'AGNC INVESTMENT',
            'STARWOOD PROPERTY TRUST', 'BLACKSTONE MORTGAGE TRUST',
            
            # Real Estate Developers
            'LENNAR', 'D.R. HORTON', 'PULTEGROUP', 'NVR',
            'TOLL BROTHERS', 'KB HOME', 'MERITAGE HOMES',
            'HOVNANIAN ENTERPRISES', 'BEAZER HOMES', 'MDC HOLDINGS',
            
            # Real Estate Services
            'CBRE GROUP', 'JONES LANG LASALLE', 'COLLIERS INTERNATIONAL',
            'COLDWELL BANKER', 'RE/MAX HOLDINGS', 'REDFIN',
            'ZILLOW GROUP', 'COMPASS', 'OPENDOOR TECHNOLOGIES',
            
            # Real Estate Investment/Finance
            'BLACKSTONE', 'BROOKFIELD ASSET MANAGEMENT', 'APOLLO GLOBAL MANAGEMENT',
            'KKR', 'CARLYLE GROUP', 'TISHMAN SPEYER',
        ]
        
        real_estate_companies = [c.upper().strip() for c in liquid_real_estate_companies if c]
        print(f"[REAL ESTATE COMPANIES] Using {len(real_estate_companies)} liquid real estate companies (REITs, developers, services) for search")
        return real_estate_companies
    
    def _fetch_ticker_info_from_claude(self, ticker: str) -> Optional[Dict[str, any]]:
        """Fetch company information from Claude API for tickers not in stocks.json
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            Dict with keys: 'name', 'industry', 'market_cap', 'size_category' (Large-Cap/Mid-Cap)
            Returns None if API call fails
        """
        if not self.claude_api_key:
            print(f"[FETCH TICKER INFO] No API key configured")
            return None
        
        # Check if API key is still placeholder
        if self.claude_api_key == 'sk-ant-api03-YourActualClaudeAPIKeyHere-ReplaceThisWithYourRealKey':
            print(f"[FETCH TICKER INFO] API key is still using placeholder value.")
            return None
        
        try:
            prompt = f"""For the stock ticker symbol {ticker}, provide the following information:

1. Company name (full official name)
2. Industry (must be one of these exact categories: Technology, Healthcare, Financials, Energy, Consumer, Industrial, Communication, Utilities, Real Estate, Materials, ETFs)
3. Market cap in millions (e.g., 50000 for $50 billion)
4. Size category (Large-Cap if market cap >= $10 billion, Mid-Cap if between $2-10 billion, Small-Cap if < $2 billion)

Return ONLY valid JSON in this exact format (no markdown, no code blocks, just pure JSON):
{{
  "name": "<company name>",
  "industry": "<industry category>",
  "market_cap": <number in millions>,
  "size_category": "<Large-Cap or Mid-Cap or Small-Cap>"
}}

If you cannot find information for this ticker, return:
{{
  "error": "Ticker not found"
}}"""

            headers = {
                'x-api-key': self.claude_api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            }
            
            payload = {
                'model': 'claude-3-5-haiku-20241022',
                'max_tokens': 500,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            }
            
            response = requests.post(self.claude_api_url, headers=headers, json=payload, timeout=30, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('content', [])
                if content and len(content) > 0:
                    text = content[0].get('text', '').strip()
                    
                    # Remove markdown code blocks if present
                    if text.startswith('```'):
                        lines = text.split('\n')
                        text = '\n'.join(lines[1:-1]) if len(lines) > 2 else text
                    if text.startswith('```json'):
                        lines = text.split('\n')
                        text = '\n'.join(lines[1:-1]) if len(lines) > 2 else text
                    
                    # Parse JSON
                    import json
                    try:
                        result = json.loads(text)
                        
                        # Check for error
                        if 'error' in result:
                            print(f"[FETCH TICKER INFO] Claude returned error for {ticker}: {result['error']}")
                            return None
                        
                        # Validate required fields
                        if 'name' not in result or 'industry' not in result or 'market_cap' not in result:
                            print(f"[FETCH TICKER INFO] Claude response missing required fields for {ticker}")
                            return None
                        
                        # Ensure market_cap is a number
                        try:
                            market_cap = float(result['market_cap'])
                        except (ValueError, TypeError):
                            print(f"[FETCH TICKER INFO] Invalid market_cap value for {ticker}: {result.get('market_cap')}")
                            return None
                        
                        # Determine size_category if not provided
                        if 'size_category' not in result:
                            if market_cap >= 10000:  # $10B+
                                result['size_category'] = 'Large-Cap'
                            elif market_cap >= 2000:  # $2B-$10B
                                result['size_category'] = 'Mid-Cap'
                            else:
                                result['size_category'] = 'Small-Cap'
                        
                        # Ensure market_cap is stored as number
                        result['market_cap'] = int(market_cap)
                        
                        print(f"[FETCH TICKER INFO] Successfully fetched info for {ticker}: {result['name']} ({result['industry']}, {result['size_category']})")
                        return result
                        
                    except json.JSONDecodeError as e:
                        print(f"[FETCH TICKER INFO] Failed to parse Claude JSON response for {ticker}: {e}")
                        print(f"[FETCH TICKER INFO] Response text: {text[:200]}")
                        return None
            else:
                print(f"[FETCH TICKER INFO] Claude API error for {ticker}: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"[FETCH TICKER INFO] Exception fetching info for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_large_cap_companies_with_options(self) -> Dict[str, Dict[str, any]]:
        """Get large-cap companies list from JSON file (auto-reloads on change)
        
        The JSON file is required. If it's missing or invalid, raises an error.
        The Python hardcoded list is kept commented out as a backup reference only.
        
        Returns:
            Dictionary mapping ticker to {'name': str, 'industry': str, 'market_cap': float}
        """
        import json
        import os
        from pathlib import Path
        
        json_path = Path(__file__).parent / 'stocks.json'
        cache_key = '_stocks_json_cache'
        cache_mtime_key = '_stocks_json_mtime'
        
        # Check if JSON file exists
        if not json_path.exists():
            raise FileNotFoundError(f"stocks.json not found at {json_path}. Please create the file with stock data.")
        
        # Get current file modification time
        current_mtime = os.path.getmtime(json_path)
        cached_mtime = getattr(self, cache_mtime_key, None)
        
        # Reload if file changed or not cached
        if cached_mtime != current_mtime or not hasattr(self, cache_key):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    companies = json.load(f)
                
                # Validate structure
                if not isinstance(companies, dict):
                    raise ValueError(f"stocks.json must contain a JSON object (dict), got {type(companies)}")
                
                if len(companies) == 0:
                    raise ValueError("stocks.json is empty")
                
                # Validate each entry has required fields
                for ticker, data in companies.items():
                    if not isinstance(data, dict):
                        raise ValueError(f"Entry for {ticker} must be an object, got {type(data)}")
                    if 'name' not in data or 'industry' not in data or 'market_cap' not in data:
                        raise ValueError(f"Entry for {ticker} missing required fields (name, industry, market_cap)")
                
                # Cache the loaded data
                setattr(self, cache_key, companies)
                setattr(self, cache_mtime_key, current_mtime)
                return companies
                
            except json.JSONDecodeError as e:
                raise ValueError(f"stocks.json contains invalid JSON: {e}")
            except IOError as e:
                raise IOError(f"Error reading stocks.json: {e}")
        
        # Return cached data
        return getattr(self, cache_key)
    
    # BACKUP REFERENCE ONLY - NOT USED IN CODE
    # If stocks.json is ever damaged, you can ask to restore from this commented list:
    # 
    # companies_backup = {
    #     # Technology
    #     'AAPL': {'name': 'Apple Inc', 'industry': 'Technology', 'market_cap': 3000000},
            # 'MSFT': {'name': 'Microsoft Corporation', 'industry': 'Technology', 'market_cap': 3000000},
            # 'GOOGL': {'name': 'Alphabet Inc', 'industry': 'Technology', 'market_cap': 2000000},
            # 'AMZN': {'name': 'Amazon.com Inc', 'industry': 'Technology', 'market_cap': 1500000},
            # 'META': {'name': 'Meta Platforms Inc', 'industry': 'Technology', 'market_cap': 1200000},
            # 'NVDA': {'name': 'NVIDIA Corporation', 'industry': 'Technology', 'market_cap': 2000000},
            # 'TSLA': {'name': 'Tesla Inc', 'industry': 'Technology', 'market_cap': 800000},
            # 'AVGO': {'name': 'Broadcom Inc', 'industry': 'Technology', 'market_cap': 600000},
            # 'ORCL': {'name': 'Oracle Corporation', 'industry': 'Technology', 'market_cap': 400000},
            # 'CRM': {'name': 'Salesforce Inc', 'industry': 'Technology', 'market_cap': 250000},
            # 'INTC': {'name': 'Intel Corporation', 'industry': 'Technology', 'market_cap': 200000},
            # 'AMD': {'name': 'Advanced Micro Devices', 'industry': 'Technology', 'market_cap': 250000},
            # 'QCOM': {'name': 'QUALCOMM Incorporated', 'industry': 'Technology', 'market_cap': 200000},
            # 'CSCO': {'name': 'Cisco Systems Inc', 'industry': 'Technology', 'market_cap': 200000},
            # 'NOW': {'name': 'ServiceNow Inc', 'industry': 'Technology', 'market_cap': 150000},
            # 'ADBE': {'name': 'Adobe Inc', 'industry': 'Technology', 'market_cap': 250000},
            # 'INTU': {'name': 'Intuit Inc', 'industry': 'Technology', 'market_cap': 180000},
            # 'MU': {'name': 'Micron Technology Inc', 'industry': 'Technology', 'market_cap': 150000},
            # 'TXN': {'name': 'Texas Instruments Incorporated', 'industry': 'Technology', 'market_cap': 170000},
            # 'AMAT': {'name': 'Applied Materials Inc', 'industry': 'Technology', 'market_cap': 150000},
            # 'LRCX': {'name': 'Lam Research Corporation', 'industry': 'Technology', 'market_cap': 120000},
            # 'KLAC': {'name': 'KLA Corporation', 'industry': 'Technology', 'market_cap': 100000},
            # 'SNPS': {'name': 'Synopsys Inc', 'industry': 'Technology', 'market_cap': 85000},
            # 'CDNS': {'name': 'Cadence Design Systems Inc', 'industry': 'Technology', 'market_cap': 80000},
            # 'FTNT': {'name': 'Fortinet Inc', 'industry': 'Technology', 'market_cap': 50000},
            # 'PANW': {'name': 'Palo Alto Networks Inc', 'industry': 'Technology', 'market_cap': 100000},
            # 'CRWD': {'name': 'CrowdStrike Holdings Inc', 'industry': 'Technology', 'market_cap': 80000},
            # 'ZS': {'name': 'Zscaler Inc', 'industry': 'Technology', 'market_cap': 30000},
            # 'NET': {'name': 'Cloudflare Inc', 'industry': 'Technology', 'market_cap': 30000},
            # 'DDOG': {'name': 'Datadog Inc', 'industry': 'Technology', 'market_cap': 40000},
            # 'TEAM': {'name': 'Atlassian Corporation', 'industry': 'Technology', 'market_cap': 60000},
            # 'ZM': {'name': 'Zoom Video Communications Inc', 'industry': 'Technology', 'market_cap': 25000},
            # 'DOCN': {'name': 'DigitalOcean Holdings Inc', 'industry': 'Technology', 'market_cap': 3000},
            # 'ESTC': {'name': 'Elastic N.V.', 'industry': 'Technology', 'market_cap': 10000},
            # 'MDB': {'name': 'MongoDB Inc', 'industry': 'Technology', 'market_cap': 30000},
            # 'OKTA': {'name': 'Okta Inc', 'industry': 'Technology', 'market_cap': 15000},
            # 'VRSN': {'name': 'VeriSign Inc', 'industry': 'Technology', 'market_cap': 25000},
            # 'AKAM': {'name': 'Akamai Technologies Inc', 'industry': 'Technology', 'market_cap': 15000},
            # 'FFIV': {'name': 'F5 Inc', 'industry': 'Technology', 'market_cap': 12000},
            # 'NTNX': {'name': 'Nutanix Inc', 'industry': 'Technology', 'market_cap': 15000},
            # 'GTLB': {'name': 'GitLab Inc', 'industry': 'Technology', 'market_cap': 10000},
            # 'ASAN': {'name': 'Asana Inc', 'industry': 'Technology', 'market_cap': 5000},
            # 'FROG': {'name': 'JFrog Ltd', 'industry': 'Technology', 'market_cap': 3000},
            # 'PD': {'name': 'PagerDuty Inc', 'industry': 'Technology', 'market_cap': 2000},
            # 'ALRM': {'name': 'Alarm.com Holdings Inc', 'industry': 'Technology', 'market_cap': 3000},
            # 'QLYS': {'name': 'Qualys Inc', 'industry': 'Technology', 'market_cap': 5000},
            # 'QLYS': {'name': 'Qualys Inc', 'industry': 'Technology', 'market_cap': 5000},
            # 'ALRM': {'name': 'Alarm.com Holdings Inc', 'industry': 'Technology', 'market_cap': 3000},
            # 'RIVN': {'name': 'Rivian Automotive Inc', 'industry': 'Technology', 'market_cap': 25600},
            # 'APP': {'name': 'AppLovin Corp', 'industry': 'Technology', 'market_cap': 23500},
            # 'KRMN': {'name': 'Karman Holdings', 'industry': 'Technology', 'market_cap': 10270},
            # 'PD': {'name': 'PagerDuty Inc', 'industry': 'Technology', 'market_cap': 2000},
            # 'FROG': {'name': 'JFrog Ltd', 'industry': 'Technology', 'market_cap': 3000},
            # 'ASAN': {'name': 'Asana Inc', 'industry': 'Technology', 'market_cap': 5000},
            # 'GTLB': {'name': 'GitLab Inc', 'industry': 'Technology', 'market_cap': 10000},
            # 'NTNX': {'name': 'Nutanix Inc', 'industry': 'Technology', 'market_cap': 15000},
            # 'FFIV': {'name': 'F5 Inc', 'industry': 'Technology', 'market_cap': 12000},
            # 'AKAM': {'name': 'Akamai Technologies Inc', 'industry': 'Technology', 'market_cap': 15000},
            # 'VRSN': {'name': 'VeriSign Inc', 'industry': 'Technology', 'market_cap': 25000},
            # 'OKTA': {'name': 'Okta Inc', 'industry': 'Technology', 'market_cap': 15000},
            # 'MDB': {'name': 'MongoDB Inc', 'industry': 'Technology', 'market_cap': 30000},
            # 'ESTC': {'name': 'Elastic N.V.', 'industry': 'Technology', 'market_cap': 10000},
            # 'DOCN': {'name': 'DigitalOcean Holdings Inc', 'industry': 'Technology', 'market_cap': 3000},
            # 'ZM': {'name': 'Zoom Video Communications Inc', 'industry': 'Technology', 'market_cap': 25000},
            # 'TEAM': {'name': 'Atlassian Corporation', 'industry': 'Technology', 'market_cap': 60000},
            # 'DDOG': {'name': 'Datadog Inc', 'industry': 'Technology', 'market_cap': 40000},
            # 'NET': {'name': 'Cloudflare Inc', 'industry': 'Technology', 'market_cap': 30000},
            # 'ZS': {'name': 'Zscaler Inc', 'industry': 'Technology', 'market_cap': 30000},
            # 'CRWD': {'name': 'CrowdStrike Holdings Inc', 'industry': 'Technology', 'market_cap': 80000},
            # 'PANW': {'name': 'Palo Alto Networks Inc', 'industry': 'Technology', 'market_cap': 100000},
            # 'FTNT': {'name': 'Fortinet Inc', 'industry': 'Technology', 'market_cap': 50000},
            # 'CDNS': {'name': 'Cadence Design Systems Inc', 'industry': 'Technology', 'market_cap': 80000},
            # 'SNPS': {'name': 'Synopsys Inc', 'industry': 'Technology', 'market_cap': 85000},
            # 'KLAC': {'name': 'KLA Corporation', 'industry': 'Technology', 'market_cap': 100000},
            # 'LRCX': {'name': 'Lam Research Corporation', 'industry': 'Technology', 'market_cap': 120000},
            # 'AMAT': {'name': 'Applied Materials Inc', 'industry': 'Technology', 'market_cap': 150000},
            # 'TXN': {'name': 'Texas Instruments Incorporated', 'industry': 'Technology', 'market_cap': 170000},
            # 'MU': {'name': 'Micron Technology Inc', 'industry': 'Technology', 'market_cap': 150000},
            # 'INTU': {'name': 'Intuit Inc', 'industry': 'Technology', 'market_cap': 180000},
            # 'ADBE': {'name': 'Adobe Inc', 'industry': 'Technology', 'market_cap': 250000},
            # 'NOW': {'name': 'ServiceNow Inc', 'industry': 'Technology', 'market_cap': 150000},
            # 'CSCO': {'name': 'Cisco Systems Inc', 'industry': 'Technology', 'market_cap': 200000},
            # 'QCOM': {'name': 'QUALCOMM Incorporated', 'industry': 'Technology', 'market_cap': 200000},
            # 'AMD': {'name': 'Advanced Micro Devices', 'industry': 'Technology', 'market_cap': 250000},
            # 'INTC': {'name': 'Intel Corporation', 'industry': 'Technology', 'market_cap': 200000},
            # 'CRM': {'name': 'Salesforce Inc', 'industry': 'Technology', 'market_cap': 250000},
            # 'ORCL': {'name': 'Oracle Corporation', 'industry': 'Technology', 'market_cap': 400000},
            # 'AVGO': {'name': 'Broadcom Inc', 'industry': 'Technology', 'market_cap': 600000},
            # 'TSLA': {'name': 'Tesla Inc', 'industry': 'Technology', 'market_cap': 800000},
            # 'NVDA': {'name': 'NVIDIA Corporation', 'industry': 'Technology', 'market_cap': 2000000},
            # 'META': {'name': 'Meta Platforms Inc', 'industry': 'Technology', 'market_cap': 1200000},
            # 'AMZN': {'name': 'Amazon.com Inc', 'industry': 'Technology', 'market_cap': 1500000},
            # 'GOOGL': {'name': 'Alphabet Inc', 'industry': 'Technology', 'market_cap': 2000000},
            # 'MSFT': {'name': 'Microsoft Corporation', 'industry': 'Technology', 'market_cap': 3000000},
            # 'AAPL': {'name': 'Apple Inc', 'industry': 'Technology', 'market_cap': 3000000},
            # Healthcare
            # 'JNJ': {'name': 'Johnson & Johnson', 'industry': 'Healthcare', 'market_cap': 400000},
            # 'UNH': {'name': 'UnitedHealth Group Inc', 'industry': 'Healthcare', 'market_cap': 500000},
            # 'PFE': {'name': 'Pfizer Inc', 'industry': 'Healthcare', 'market_cap': 200000},
            # 'ABBV': {'name': 'AbbVie Inc', 'industry': 'Healthcare', 'market_cap': 300000},
            # 'TMO': {'name': 'Thermo Fisher Scientific Inc', 'industry': 'Healthcare', 'market_cap': 200000},
            # 'ABT': {'name': 'Abbott Laboratories', 'industry': 'Healthcare', 'market_cap': 200000},
            # 'DHR': {'name': 'Danaher Corporation', 'industry': 'Healthcare', 'market_cap': 200000},
            # 'BMY': {'name': 'Bristol-Myers Squibb Company', 'industry': 'Healthcare', 'market_cap': 150000},
            # 'AMGN': {'name': 'Amgen Inc', 'industry': 'Healthcare', 'market_cap': 150000},
            # 'GILD': {'name': 'Gilead Sciences Inc', 'industry': 'Healthcare', 'market_cap': 100000},
            # 'CVS': {'name': 'CVS Health Corporation', 'industry': 'Healthcare', 'market_cap': 100000},
            # 'CI': {'name': 'Cigna Corporation', 'industry': 'Healthcare', 'market_cap': 80000},
            # 'HUM': {'name': 'Humana Inc', 'industry': 'Healthcare', 'market_cap': 60000},
            # 'ELV': {'name': 'Elevance Health Inc', 'industry': 'Healthcare', 'market_cap': 120000},
            # 'CNC': {'name': 'Centene Corporation', 'industry': 'Healthcare', 'market_cap': 40000},
            # 'MRNA': {'name': 'Moderna Inc', 'industry': 'Healthcare', 'market_cap': 50000},
            # 'REGN': {'name': 'Regeneron Pharmaceuticals Inc', 'industry': 'Healthcare', 'market_cap': 100000},
            # 'VRTX': {'name': 'Vertex Pharmaceuticals Incorporated', 'industry': 'Healthcare', 'market_cap': 120000},
            # 'BIIB': {'name': 'Biogen Inc', 'industry': 'Healthcare', 'market_cap': 40000},
            # 'ILMN': {'name': 'Illumina Inc', 'industry': 'Healthcare', 'market_cap': 25000},
            # 'ALNY': {'name': 'Alnylam Pharmaceuticals Inc', 'industry': 'Healthcare', 'market_cap': 25000},
            # 'EXAS': {'name': 'Exact Sciences Corporation', 'industry': 'Healthcare', 'market_cap': 15000},
            # 'TECH': {'name': 'Bio-Techne Corporation', 'industry': 'Healthcare', 'market_cap': 12000},
            # 'ICLR': {'name': 'ICON plc', 'industry': 'Healthcare', 'market_cap': 25000},
            # 'CRL': {'name': 'Charles River Laboratories International Inc', 'industry': 'Healthcare', 'market_cap': 12000},
            # 'WAT': {'name': 'Waters Corporation', 'industry': 'Healthcare', 'market_cap': 15000},
            # 'A': {'name': 'Agilent Technologies Inc', 'industry': 'Healthcare', 'market_cap': 40000},
            # 'BRKR': {'name': 'Bruker Corporation', 'industry': 'Healthcare', 'market_cap': 12000},
            # 'QGEN': {'name': 'Qiagen N.V.', 'industry': 'Healthcare', 'market_cap': 10000},
            # 'PACB': {'name': 'Pacific Biosciences of California Inc', 'industry': 'Healthcare', 'market_cap': 2000},
            # 'OMCL': {'name': 'Omnicell Inc', 'industry': 'Healthcare', 'market_cap': 2000},
            # 'OMCL': {'name': 'Omnicell Inc', 'industry': 'Healthcare', 'market_cap': 2000},
            # 'PACB': {'name': 'Pacific Biosciences of California Inc', 'industry': 'Healthcare', 'market_cap': 2000},
            # 'QGEN': {'name': 'Qiagen N.V.', 'industry': 'Healthcare', 'market_cap': 10000},
            # 'BRKR': {'name': 'Bruker Corporation', 'industry': 'Healthcare', 'market_cap': 12000},
            # 'A': {'name': 'Agilent Technologies Inc', 'industry': 'Healthcare', 'market_cap': 40000},
            # 'WAT': {'name': 'Waters Corporation', 'industry': 'Healthcare', 'market_cap': 15000},
            # 'CRL': {'name': 'Charles River Laboratories International Inc', 'industry': 'Healthcare', 'market_cap': 12000},
            # 'ICLR': {'name': 'ICON plc', 'industry': 'Healthcare', 'market_cap': 25000},
            # 'TECH': {'name': 'Bio-Techne Corporation', 'industry': 'Healthcare', 'market_cap': 12000},
            # 'EXAS': {'name': 'Exact Sciences Corporation', 'industry': 'Healthcare', 'market_cap': 15000},
            # 'ALNY': {'name': 'Alnylam Pharmaceuticals Inc', 'industry': 'Healthcare', 'market_cap': 25000},
            # 'ILMN': {'name': 'Illumina Inc', 'industry': 'Healthcare', 'market_cap': 25000},
            # 'BIIB': {'name': 'Biogen Inc', 'industry': 'Healthcare', 'market_cap': 40000},
            # 'VRTX': {'name': 'Vertex Pharmaceuticals Incorporated', 'industry': 'Healthcare', 'market_cap': 120000},
            # 'REGN': {'name': 'Regeneron Pharmaceuticals Inc', 'industry': 'Healthcare', 'market_cap': 100000},
            # 'MRNA': {'name': 'Moderna Inc', 'industry': 'Healthcare', 'market_cap': 50000},
            # 'CNC': {'name': 'Centene Corporation', 'industry': 'Healthcare', 'market_cap': 40000},
            # 'ELV': {'name': 'Elevance Health Inc', 'industry': 'Healthcare', 'market_cap': 120000},
            # 'HUM': {'name': 'Humana Inc', 'industry': 'Healthcare', 'market_cap': 60000},
            # 'CI': {'name': 'Cigna Corporation', 'industry': 'Healthcare', 'market_cap': 80000},
            # 'CVS': {'name': 'CVS Health Corporation', 'industry': 'Healthcare', 'market_cap': 100000},
            # 'GILD': {'name': 'Gilead Sciences Inc', 'industry': 'Healthcare', 'market_cap': 100000},
            # 'AMGN': {'name': 'Amgen Inc', 'industry': 'Healthcare', 'market_cap': 150000},
            # 'BMY': {'name': 'Bristol-Myers Squibb Company', 'industry': 'Healthcare', 'market_cap': 150000},
            # 'DHR': {'name': 'Danaher Corporation', 'industry': 'Healthcare', 'market_cap': 200000},
            # 'ABT': {'name': 'Abbott Laboratories', 'industry': 'Healthcare', 'market_cap': 200000},
            # 'TMO': {'name': 'Thermo Fisher Scientific Inc', 'industry': 'Healthcare', 'market_cap': 200000},
            # 'ABBV': {'name': 'AbbVie Inc', 'industry': 'Healthcare', 'market_cap': 300000},
            # 'PFE': {'name': 'Pfizer Inc', 'industry': 'Healthcare', 'market_cap': 200000},
            # 'UNH': {'name': 'UnitedHealth Group Inc', 'industry': 'Healthcare', 'market_cap': 500000},
            # 'JNJ': {'name': 'Johnson & Johnson', 'industry': 'Healthcare', 'market_cap': 400000},
            # 'MRK': {'name': 'Merck & Co. Inc', 'industry': 'Healthcare', 'market_cap': 200000},
            # 'NVO': {'name': 'Novo Nordisk A/S', 'industry': 'Healthcare', 'market_cap': 361000},
            # 'AZN': {'name': 'AstraZeneca PLC', 'industry': 'Healthcare', 'market_cap': 222000},
            # 'ISRG': {'name': 'Intuitive Surgical Inc', 'industry': 'Healthcare', 'market_cap': 100000},
            # 'ZBH': {'name': 'Zimmer Biomet Holdings Inc', 'industry': 'Healthcare', 'market_cap': 28000},
            # 'BSX': {'name': 'Boston Scientific Corp', 'industry': 'Healthcare', 'market_cap': 75000},
            # 'EW': {'name': 'Edwards Lifesciences Corp', 'industry': 'Healthcare', 'market_cap': 28000},
            # 'DXCM': {'name': 'DexCom Inc', 'industry': 'Healthcare', 'market_cap': 55000},
            # 'GMAB': {'name': 'Genmab A/S', 'industry': 'Healthcare', 'market_cap': 31500},
            # 'HCM': {'name': 'HUTCHMED Limited', 'industry': 'Healthcare', 'market_cap': 13200},
            # 'BMRN': {'name': 'BioMarin Pharmaceutical Inc', 'industry': 'Healthcare', 'market_cap': 16500},
            # 'NBIX': {'name': 'Neurocrine Biosciences Inc', 'industry': 'Healthcare', 'market_cap': 13500},
            # Financials
            # 'JPM': {'name': 'JPMorgan Chase & Co', 'industry': 'Financials', 'market_cap': 500000},
            # 'AIG': {'name': 'American International Group Inc', 'industry': 'Financials', 'market_cap': 46000},
            # 'BAC': {'name': 'Bank of America Corp', 'industry': 'Financials', 'market_cap': 300000},
            # 'WFC': {'name': 'Wells Fargo & Company', 'industry': 'Financials', 'market_cap': 200000},
            # 'GS': {'name': 'Goldman Sachs Group Inc', 'industry': 'Financials', 'market_cap': 150000},
            # 'MS': {'name': 'Morgan Stanley', 'industry': 'Financials', 'market_cap': 150000},
            # 'C': {'name': 'Citigroup Inc', 'industry': 'Financials', 'market_cap': 100000},
            # 'BLK': {'name': 'BlackRock Inc', 'industry': 'Financials', 'market_cap': 120000},
            # 'SCHW': {'name': 'Charles Schwab Corporation', 'industry': 'Financials', 'market_cap': 150000},
            # 'AXP': {'name': 'American Express Company', 'industry': 'Financials', 'market_cap': 150000},
            # 'COF': {'name': 'Capital One Financial Corporation', 'industry': 'Financials', 'market_cap': 50000},
            # 'USB': {'name': 'U.S. Bancorp', 'industry': 'Financials', 'market_cap': 60000},
            # 'PNC': {'name': 'PNC Financial Services Group Inc', 'industry': 'Financials', 'market_cap': 70000},
            # 'TFC': {'name': 'Truist Financial Corporation', 'industry': 'Financials', 'market_cap': 50000},
            # 'BK': {'name': 'Bank of New York Mellon Corporation', 'industry': 'Financials', 'market_cap': 40000},
            # 'STT': {'name': 'State Street Corporation', 'industry': 'Financials', 'market_cap': 25000},
            # 'MTB': {'name': 'M&T Bank Corporation', 'industry': 'Financials', 'market_cap': 25000},
            # 'CFG': {'name': 'Citizens Financial Group Inc', 'industry': 'Financials', 'market_cap': 20000},
            # 'HBAN': {'name': 'Huntington Bancshares Incorporated', 'industry': 'Financials', 'market_cap': 20000},
            # 'ZION': {'name': 'Zions Bancorporation N.A.', 'industry': 'Financials', 'market_cap': 10000},
            # 'KEY': {'name': 'KeyCorp', 'industry': 'Financials', 'market_cap': 15000},
            # 'RF': {'name': 'Regions Financial Corporation', 'industry': 'Financials', 'market_cap': 20000},
            # 'FITB': {'name': 'Fifth Third Bancorp', 'industry': 'Financials', 'market_cap': 25000},
            # 'CMA': {'name': 'Comerica Incorporated', 'industry': 'Financials', 'market_cap': 8000},
            # 'WTFC': {'name': 'Wintrust Financial Corporation', 'industry': 'Financials', 'market_cap': 6000},
            # 'ONB': {'name': 'Old National Bancorp', 'industry': 'Financials', 'market_cap': 6000},
            # 'HOMB': {'name': 'Home BancShares Inc', 'industry': 'Financials', 'market_cap': 6000},
            # 'HOMB': {'name': 'Home BancShares Inc', 'industry': 'Financials', 'market_cap': 6000},
            # 'ONB': {'name': 'Old National Bancorp', 'industry': 'Financials', 'market_cap': 6000},
            # 'WTFC': {'name': 'Wintrust Financial Corporation', 'industry': 'Financials', 'market_cap': 6000},
            # 'CMA': {'name': 'Comerica Incorporated', 'industry': 'Financials', 'market_cap': 8000},
            # 'FITB': {'name': 'Fifth Third Bancorp', 'industry': 'Financials', 'market_cap': 25000},
            # 'RF': {'name': 'Regions Financial Corporation', 'industry': 'Financials', 'market_cap': 20000},
            # 'KEY': {'name': 'KeyCorp', 'industry': 'Financials', 'market_cap': 15000},
            # 'ZION': {'name': 'Zions Bancorporation N.A.', 'industry': 'Financials', 'market_cap': 10000},
            # 'HBAN': {'name': 'Huntington Bancshares Incorporated', 'industry': 'Financials', 'market_cap': 20000},
            # 'CFG': {'name': 'Citizens Financial Group Inc', 'industry': 'Financials', 'market_cap': 20000},
            # 'MTB': {'name': 'M&T Bank Corporation', 'industry': 'Financials', 'market_cap': 25000},
            # 'STT': {'name': 'State Street Corporation', 'industry': 'Financials', 'market_cap': 25000},
            # 'BK': {'name': 'Bank of New York Mellon Corporation', 'industry': 'Financials', 'market_cap': 40000},
            # 'TFC': {'name': 'Truist Financial Corporation', 'industry': 'Financials', 'market_cap': 50000},
            # 'PNC': {'name': 'PNC Financial Services Group Inc', 'industry': 'Financials', 'market_cap': 70000},
            # 'USB': {'name': 'U.S. Bancorp', 'industry': 'Financials', 'market_cap': 60000},
            # 'COF': {'name': 'Capital One Financial Corporation', 'industry': 'Financials', 'market_cap': 50000},
            # 'AXP': {'name': 'American Express Company', 'industry': 'Financials', 'market_cap': 150000},
            # 'SCHW': {'name': 'Charles Schwab Corporation', 'industry': 'Financials', 'market_cap': 150000},
            # 'BLK': {'name': 'BlackRock Inc', 'industry': 'Financials', 'market_cap': 120000},
            # 'C': {'name': 'Citigroup Inc', 'industry': 'Financials', 'market_cap': 100000},
            # 'MS': {'name': 'Morgan Stanley', 'industry': 'Financials', 'market_cap': 150000},
            # 'GS': {'name': 'Goldman Sachs Group Inc', 'industry': 'Financials', 'market_cap': 150000},
            # 'AIG': {'name': 'American International Group Inc', 'industry': 'Financials', 'market_cap': 46000},
            # 'WFC': {'name': 'Wells Fargo & Company', 'industry': 'Financials', 'market_cap': 200000},
            # 'BAC': {'name': 'Bank of America Corp', 'industry': 'Financials', 'market_cap': 300000},
            # 'JPM': {'name': 'JPMorgan Chase & Co', 'industry': 'Financials', 'market_cap': 500000},
            # Energy
            # 'XOM': {'name': 'Exxon Mobil Corporation', 'industry': 'Energy', 'market_cap': 400000},
            # 'CVX': {'name': 'Chevron Corporation', 'industry': 'Energy', 'market_cap': 300000},
            # 'SLB': {'name': 'Schlumberger Limited', 'industry': 'Energy', 'market_cap': 80000},
            # 'COP': {'name': 'ConocoPhillips', 'industry': 'Energy', 'market_cap': 150000},
            # 'CNQ': {'name': 'Canadian Natural Resources Limited', 'industry': 'Energy', 'market_cap': 70000},
            # 'EOG': {'name': 'EOG Resources Inc', 'industry': 'Energy', 'market_cap': 70000},
            # 'MPC': {'name': 'Marathon Petroleum Corporation', 'industry': 'Energy', 'market_cap': 60000},
            # 'VLO': {'name': 'Valero Energy Corporation', 'industry': 'Energy', 'market_cap': 50000},
            # 'PSX': {'name': 'Phillips 66', 'industry': 'Energy', 'market_cap': 50000},
            # 'HAL': {'name': 'Halliburton Company', 'industry': 'Energy', 'market_cap': 35000},
            # 'BKR': {'name': 'Baker Hughes Company', 'industry': 'Energy', 'market_cap': 30000},
            # 'FANG': {'name': 'Diamondback Energy Inc', 'industry': 'Energy', 'market_cap': 30000},
            # 'CTRA': {'name': 'Coterra Energy Inc', 'industry': 'Energy', 'market_cap': 20000},
            # 'OVV': {'name': 'Ovintiv Inc', 'industry': 'Energy', 'market_cap': 15000},
            # 'DVN': {'name': 'Devon Energy Corporation', 'industry': 'Energy', 'market_cap': 30000},
            # 'PR': {'name': 'Permian Resources Corporation', 'industry': 'Energy', 'market_cap': 10000},
            # 'PR': {'name': 'Permian Resources Corporation', 'industry': 'Energy', 'market_cap': 10000},
            # 'DVN': {'name': 'Devon Energy Corporation', 'industry': 'Energy', 'market_cap': 30000},
            # 'OVV': {'name': 'Ovintiv Inc', 'industry': 'Energy', 'market_cap': 15000},
            # 'CTRA': {'name': 'Coterra Energy Inc', 'industry': 'Energy', 'market_cap': 20000},
            # 'FANG': {'name': 'Diamondback Energy Inc', 'industry': 'Energy', 'market_cap': 30000},
            # 'BKR': {'name': 'Baker Hughes Company', 'industry': 'Energy', 'market_cap': 30000},
            # 'HAL': {'name': 'Halliburton Company', 'industry': 'Energy', 'market_cap': 35000},
            # 'PSX': {'name': 'Phillips 66', 'industry': 'Energy', 'market_cap': 50000},
            # 'VLO': {'name': 'Valero Energy Corporation', 'industry': 'Energy', 'market_cap': 50000},
            # 'MPC': {'name': 'Marathon Petroleum Corporation', 'industry': 'Energy', 'market_cap': 60000},
            # 'EOG': {'name': 'EOG Resources Inc', 'industry': 'Energy', 'market_cap': 70000},
            # 'CNQ': {'name': 'Canadian Natural Resources Limited', 'industry': 'Energy', 'market_cap': 70000},
            # 'COP': {'name': 'ConocoPhillips', 'industry': 'Energy', 'market_cap': 150000},
            # 'SLB': {'name': 'Schlumberger Limited', 'industry': 'Energy', 'market_cap': 80000},
            # 'CVX': {'name': 'Chevron Corporation', 'industry': 'Energy', 'market_cap': 300000},
            # 'XOM': {'name': 'Exxon Mobil Corporation', 'industry': 'Energy', 'market_cap': 400000},
            # Consumer
            # 'WMT': {'name': 'Walmart Inc', 'industry': 'Consumer', 'market_cap': 400000},
            # 'HD': {'name': 'Home Depot Inc', 'industry': 'Consumer', 'market_cap': 350000},
            # 'MCD': {'name': 'McDonald\'s Corporation', 'industry': 'Consumer', 'market_cap': 200000},
            # 'SBUX': {'name': 'Starbucks Corporation', 'industry': 'Consumer', 'market_cap': 100000},
            # 'NKE': {'name': 'Nike Inc', 'industry': 'Consumer', 'market_cap': 150000},
            # 'TGT': {'name': 'Target Corporation', 'industry': 'Consumer', 'market_cap': 70000},
            # 'LOW': {'name': 'Lowe\'s Companies Inc', 'industry': 'Consumer', 'market_cap': 150000},
            # 'COST': {'name': 'Costco Wholesale Corporation', 'industry': 'Consumer', 'market_cap': 250000},
            # 'BKNG': {'name': 'Booking Holdings Inc', 'industry': 'Consumer', 'market_cap': 100000},
            # 'MAR': {'name': 'Marriott International Inc', 'industry': 'Consumer', 'market_cap': 60000},
            # 'HLT': {'name': 'Hilton Worldwide Holdings Inc', 'industry': 'Consumer', 'market_cap': 50000},
            # 'ABNB': {'name': 'Airbnb Inc', 'industry': 'Consumer', 'market_cap': 80000},
            # 'EXPE': {'name': 'Expedia Group Inc', 'industry': 'Consumer', 'market_cap': 20000},
            # 'TRIP': {'name': 'Tripadvisor Inc', 'industry': 'Consumer', 'market_cap': 3000},
            # 'TRIP': {'name': 'Tripadvisor Inc', 'industry': 'Consumer', 'market_cap': 3000},
            # 'EXPE': {'name': 'Expedia Group Inc', 'industry': 'Consumer', 'market_cap': 20000},
            # 'ABNB': {'name': 'Airbnb Inc', 'industry': 'Consumer', 'market_cap': 80000},
            # 'HLT': {'name': 'Hilton Worldwide Holdings Inc', 'industry': 'Consumer', 'market_cap': 50000},
            # 'MAR': {'name': 'Marriott International Inc', 'industry': 'Consumer', 'market_cap': 60000},
            # 'BKNG': {'name': 'Booking Holdings Inc', 'industry': 'Consumer', 'market_cap': 100000},
            # 'COST': {'name': 'Costco Wholesale Corporation', 'industry': 'Consumer', 'market_cap': 250000},
            # 'LOW': {'name': 'Lowe\'s Companies Inc', 'industry': 'Consumer', 'market_cap': 150000},
            # 'TGT': {'name': 'Target Corporation', 'industry': 'Consumer', 'market_cap': 70000},
            # 'NKE': {'name': 'Nike Inc', 'industry': 'Consumer', 'market_cap': 150000},
            # 'SBUX': {'name': 'Starbucks Corporation', 'industry': 'Consumer', 'market_cap': 100000},
            # 'MCD': {'name': 'McDonald\'s Corporation', 'industry': 'Consumer', 'market_cap': 200000},
            # 'HD': {'name': 'Home Depot Inc', 'industry': 'Consumer', 'market_cap': 350000},
            # 'WMT': {'name': 'Walmart Inc', 'industry': 'Consumer', 'market_cap': 400000},
            # 'LVS': {'name': 'Las Vegas Sands Corp', 'industry': 'Consumer', 'market_cap': 65000},
            # 'MGM': {'name': 'MGM Resorts International', 'industry': 'Consumer', 'market_cap': 37000},
            # 'WYNN': {'name': 'Wynn Resorts Limited', 'industry': 'Consumer', 'market_cap': 12000},
            # 'CZR': {'name': 'Caesars Entertainment Inc', 'industry': 'Consumer', 'market_cap': 10000},
            # 'PENN': {'name': 'PENN Entertainment Inc', 'industry': 'Consumer', 'market_cap': 5000},
            # Industrial
            # 'BA': {'name': 'Boeing Company', 'industry': 'Industrial', 'market_cap': 150000},
            # 'CAT': {'name': 'Caterpillar Inc', 'industry': 'Industrial', 'market_cap': 150000},
            # 'GE': {'name': 'General Electric Company', 'industry': 'Industrial', 'market_cap': 150000},
            # 'HON': {'name': 'Honeywell International Inc', 'industry': 'Industrial', 'market_cap': 150000},
            # 'RTX': {'name': 'Raytheon Technologies Corporation', 'industry': 'Industrial', 'market_cap': 150000},
            # 'LMT': {'name': 'Lockheed Martin Corporation', 'industry': 'Industrial', 'market_cap': 120000},
            # 'NOC': {'name': 'Northrop Grumman Corporation', 'industry': 'Industrial', 'market_cap': 70000},
            # 'GD': {'name': 'General Dynamics Corporation', 'industry': 'Industrial', 'market_cap': 80000},
            # 'DE': {'name': 'Deere & Company', 'industry': 'Industrial', 'market_cap': 120000},
            # 'EMR': {'name': 'Emerson Electric Co', 'industry': 'Industrial', 'market_cap': 60000},
            # 'ETN': {'name': 'Eaton Corporation plc', 'industry': 'Industrial', 'market_cap': 80000},
            # 'ITW': {'name': 'Illinois Tool Works Inc', 'industry': 'Industrial', 'market_cap': 80000},
            # 'JCI': {'name': 'Johnson Controls International plc', 'industry': 'Industrial', 'market_cap': 73000},
            # 'EFX': {'name': 'Equifax Inc', 'industry': 'Industrial', 'market_cap': 26000},
            # 'PH': {'name': 'Parker-Hannifin Corporation', 'industry': 'Industrial', 'market_cap': 60000},
            # 'ROK': {'name': 'Rockwell Automation Inc', 'industry': 'Industrial', 'market_cap': 35000},
            # 'AME': {'name': 'AMETEK Inc', 'industry': 'Industrial', 'market_cap': 35000},
            # 'FTV': {'name': 'Fortive Corporation', 'industry': 'Industrial', 'market_cap': 30000},
            # 'DOV': {'name': 'Dover Corporation', 'industry': 'Industrial', 'market_cap': 25000},
            # 'GGG': {'name': 'Graco Inc', 'industry': 'Industrial', 'market_cap': 15000},
            # 'GGG': {'name': 'Graco Inc', 'industry': 'Industrial', 'market_cap': 15000},
            # 'DOV': {'name': 'Dover Corporation', 'industry': 'Industrial', 'market_cap': 25000},
            # 'FTV': {'name': 'Fortive Corporation', 'industry': 'Industrial', 'market_cap': 30000},
            # 'AME': {'name': 'AMETEK Inc', 'industry': 'Industrial', 'market_cap': 35000},
            # 'ROK': {'name': 'Rockwell Automation Inc', 'industry': 'Industrial', 'market_cap': 35000},
            # 'PH': {'name': 'Parker-Hannifin Corporation', 'industry': 'Industrial', 'market_cap': 60000},
            # 'ITW': {'name': 'Illinois Tool Works Inc', 'industry': 'Industrial', 'market_cap': 80000},
            # 'ETN': {'name': 'Eaton Corporation plc', 'industry': 'Industrial', 'market_cap': 80000},
            # 'EMR': {'name': 'Emerson Electric Co', 'industry': 'Industrial', 'market_cap': 60000},
            # 'DE': {'name': 'Deere & Company', 'industry': 'Industrial', 'market_cap': 120000},
            # 'GD': {'name': 'General Dynamics Corporation', 'industry': 'Industrial', 'market_cap': 80000},
            # 'NOC': {'name': 'Northrop Grumman Corporation', 'industry': 'Industrial', 'market_cap': 70000},
            # 'LMT': {'name': 'Lockheed Martin Corporation', 'industry': 'Industrial', 'market_cap': 120000},
            # 'RTX': {'name': 'Raytheon Technologies Corporation', 'industry': 'Industrial', 'market_cap': 150000},
            # 'HON': {'name': 'Honeywell International Inc', 'industry': 'Industrial', 'market_cap': 150000},
            # 'GE': {'name': 'General Electric Company', 'industry': 'Industrial', 'market_cap': 150000},
            # 'CAT': {'name': 'Caterpillar Inc', 'industry': 'Industrial', 'market_cap': 150000},
            # 'BA': {'name': 'Boeing Company', 'industry': 'Industrial', 'market_cap': 150000},
            # 'JCI': {'name': 'Johnson Controls International plc', 'industry': 'Industrial', 'market_cap': 73000},
            # 'EFX': {'name': 'Equifax Inc', 'industry': 'Industrial', 'market_cap': 26000},
            # Communication
            # 'VZ': {'name': 'Verizon Communications Inc', 'industry': 'Communication', 'market_cap': 200000},
            # 'T': {'name': 'AT&T Inc', 'industry': 'Communication', 'market_cap': 150000},
            # 'CMCSA': {'name': 'Comcast Corporation', 'industry': 'Communication', 'market_cap': 200000},
            # 'DIS': {'name': 'Walt Disney Company', 'industry': 'Communication', 'market_cap': 200000},
            # 'NFLX': {'name': 'Netflix Inc', 'industry': 'Communication', 'market_cap': 250000},
            # 'WBD': {'name': 'Warner Bros. Discovery Inc', 'industry': 'Communication', 'market_cap': 30000},
            # 'FOXA': {'name': 'Fox Corporation', 'industry': 'Communication', 'market_cap': 15000},
            # 'FOXA': {'name': 'Fox Corporation', 'industry': 'Communication', 'market_cap': 15000},
            # 'WBD': {'name': 'Warner Bros. Discovery Inc', 'industry': 'Communication', 'market_cap': 30000},
            # 'NFLX': {'name': 'Netflix Inc', 'industry': 'Communication', 'market_cap': 250000},
            # 'DIS': {'name': 'Walt Disney Company', 'industry': 'Communication', 'market_cap': 200000},
            # 'CMCSA': {'name': 'Comcast Corporation', 'industry': 'Communication', 'market_cap': 200000},
            # 'T': {'name': 'AT&T Inc', 'industry': 'Communication', 'market_cap': 150000},
            # 'VZ': {'name': 'Verizon Communications Inc', 'industry': 'Communication', 'market_cap': 200000},
            # Utilities
            # 'NEE': {'name': 'NextEra Energy Inc', 'industry': 'Utilities', 'market_cap': 150000},
            # 'DUK': {'name': 'Duke Energy Corporation', 'industry': 'Utilities', 'market_cap': 80000},
            # 'SO': {'name': 'Southern Company', 'industry': 'Utilities', 'market_cap': 80000},
            # 'AEP': {'name': 'American Electric Power Company Inc', 'industry': 'Utilities', 'market_cap': 50000},
            # 'EXC': {'name': 'Exelon Corporation', 'industry': 'Utilities', 'market_cap': 40000},
            # 'SRE': {'name': 'Sempra Energy', 'industry': 'Utilities', 'market_cap': 50000},
            # 'XEL': {'name': 'Xcel Energy Inc', 'industry': 'Utilities', 'market_cap': 35000},
            # 'WEC': {'name': 'WEC Energy Group Inc', 'industry': 'Utilities', 'market_cap': 30000},
            # 'ES': {'name': 'Eversource Energy', 'industry': 'Utilities', 'market_cap': 25000},
            # 'PEG': {'name': 'Public Service Enterprise Group Incorporated', 'industry': 'Utilities', 'market_cap': 35000},
            # 'PEG': {'name': 'Public Service Enterprise Group Incorporated', 'industry': 'Utilities', 'market_cap': 35000},
            # 'ES': {'name': 'Eversource Energy', 'industry': 'Utilities', 'market_cap': 25000},
            # 'WEC': {'name': 'WEC Energy Group Inc', 'industry': 'Utilities', 'market_cap': 30000},
            # 'XEL': {'name': 'Xcel Energy Inc', 'industry': 'Utilities', 'market_cap': 35000},
            # 'SRE': {'name': 'Sempra Energy', 'industry': 'Utilities', 'market_cap': 50000},
            # 'EXC': {'name': 'Exelon Corporation', 'industry': 'Utilities', 'market_cap': 40000},
            # 'AEP': {'name': 'American Electric Power Company Inc', 'industry': 'Utilities', 'market_cap': 50000},
            # 'SO': {'name': 'Southern Company', 'industry': 'Utilities', 'market_cap': 80000},
            # 'DUK': {'name': 'Duke Energy Corporation', 'industry': 'Utilities', 'market_cap': 80000},
            # 'NEE': {'name': 'NextEra Energy Inc', 'industry': 'Utilities', 'market_cap': 150000},
            # Real Estate
            # 'AMT': {'name': 'American Tower Corporation', 'industry': 'Real Estate', 'market_cap': 100000},
            # 'PLD': {'name': 'Prologis Inc', 'industry': 'Real Estate', 'market_cap': 120000},
            # 'EQIX': {'name': 'Equinix Inc', 'industry': 'Real Estate', 'market_cap': 80000},
            # 'PSA': {'name': 'Public Storage', 'industry': 'Real Estate', 'market_cap': 60000},
            # 'WELL': {'name': 'Welltower Inc', 'industry': 'Real Estate', 'market_cap': 50000},
            # 'VICI': {'name': 'VICI Properties Inc', 'industry': 'Real Estate', 'market_cap': 30000},
            # 'SPG': {'name': 'Simon Property Group Inc', 'industry': 'Real Estate', 'market_cap': 50000},
            # 'O': {'name': 'Realty Income Corporation', 'industry': 'Real Estate', 'market_cap': 50000},
            # 'DLR': {'name': 'Digital Realty Trust Inc', 'industry': 'Real Estate', 'market_cap': 40000},
            # 'EXPI': {'name': 'eXp World Holdings Inc', 'industry': 'Real Estate', 'market_cap': 2000},
            # 'EXPI': {'name': 'eXp World Holdings Inc', 'industry': 'Real Estate', 'market_cap': 2000},
            # 'DLR': {'name': 'Digital Realty Trust Inc', 'industry': 'Real Estate', 'market_cap': 40000},
            # 'O': {'name': 'Realty Income Corporation', 'industry': 'Real Estate', 'market_cap': 50000},
            # 'SPG': {'name': 'Simon Property Group Inc', 'industry': 'Real Estate', 'market_cap': 50000},
            # 'VICI': {'name': 'VICI Properties Inc', 'industry': 'Real Estate', 'market_cap': 30000},
            # 'WELL': {'name': 'Welltower Inc', 'industry': 'Real Estate', 'market_cap': 50000},
            # 'PSA': {'name': 'Public Storage', 'industry': 'Real Estate', 'market_cap': 60000},
            # 'EQIX': {'name': 'Equinix Inc', 'industry': 'Real Estate', 'market_cap': 80000},
            # 'PLD': {'name': 'Prologis Inc', 'industry': 'Real Estate', 'market_cap': 120000},
            # 'AMT': {'name': 'American Tower Corporation', 'industry': 'Real Estate', 'market_cap': 100000},
            # Materials
            # 'LIN': {'name': 'Linde plc', 'industry': 'Materials', 'market_cap': 200000},
            # 'APD': {'name': 'Air Products and Chemicals Inc', 'industry': 'Materials', 'market_cap': 60000},
            # 'ECL': {'name': 'Ecolab Inc', 'industry': 'Materials', 'market_cap': 60000},
            # 'SHW': {'name': 'Sherwin-Williams Company', 'industry': 'Materials', 'market_cap': 80000},
            # 'PPG': {'name': 'PPG Industries Inc', 'industry': 'Materials', 'market_cap': 35000},
            # 'DD': {'name': 'DuPont de Nemours Inc', 'industry': 'Materials', 'market_cap': 35000},
            # 'FCX': {'name': 'Freeport-McMoRan Inc', 'industry': 'Materials', 'market_cap': 60000},
            # 'NEM': {'name': 'Newmont Corporation', 'industry': 'Materials', 'market_cap': 50000},
            # 'VALE': {'name': 'Vale S.A.', 'industry': 'Materials', 'market_cap': 60000},
            # 'RIO': {'name': 'Rio Tinto Group', 'industry': 'Materials', 'market_cap': 120000},
            # 'BHP': {'name': 'BHP Group Limited', 'industry': 'Materials', 'market_cap': 150000},
            # 'BHP': {'name': 'BHP Group Limited', 'industry': 'Materials', 'market_cap': 150000},
            # 'RIO': {'name': 'Rio Tinto Group', 'industry': 'Materials', 'market_cap': 120000},
            # 'VALE': {'name': 'Vale S.A.', 'industry': 'Materials', 'market_cap': 60000},
            # 'NEM': {'name': 'Newmont Corporation', 'industry': 'Materials', 'market_cap': 50000},
            # 'FCX': {'name': 'Freeport-McMoRan Inc', 'industry': 'Materials', 'market_cap': 60000},
            # 'DD': {'name': 'DuPont de Nemours Inc', 'industry': 'Materials', 'market_cap': 35000},
            # 'PPG': {'name': 'PPG Industries Inc', 'industry': 'Materials', 'market_cap': 35000},
            # 'SHW': {'name': 'Sherwin-Williams Company', 'industry': 'Materials', 'market_cap': 80000},
            # 'ECL': {'name': 'Ecolab Inc', 'industry': 'Materials', 'market_cap': 60000},
            # 'APD': {'name': 'Air Products and Chemicals Inc', 'industry': 'Materials', 'market_cap': 60000},
            # 'LIN': {'name': 'Linde plc', 'industry': 'Materials', 'market_cap': 200000},
            # ETFs & Indices
            # 'SPY': {'name': 'SPDR S&P 500 ETF Trust', 'industry': 'ETFs', 'market_cap': 500000},
            # 'QQQ': {'name': 'Invesco QQQ Trust', 'industry': 'ETFs', 'market_cap': 250000},
            # 'DIA': {'name': 'SPDR Dow Jones Industrial Average ETF', 'industry': 'ETFs', 'market_cap': 30000},
            # 'IWM': {'name': 'iShares Russell 2000 ETF', 'industry': 'ETFs', 'market_cap': 60000},
            # 'VTI': {'name': 'Vanguard Total Stock Market ETF', 'industry': 'ETFs', 'market_cap': 400000},
            # 'VOO': {'name': 'Vanguard S&P 500 ETF', 'industry': 'ETFs', 'market_cap': 400000},
            # 'IVV': {'name': 'iShares Core S&P 500 ETF', 'industry': 'ETFs', 'market_cap': 400000},
            # 'EEM': {'name': 'iShares MSCI Emerging Markets ETF', 'industry': 'ETFs', 'market_cap': 20000},
            # 'EFA': {'name': 'iShares MSCI EAFE ETF', 'industry': 'ETFs', 'market_cap': 50000},
            # 'GLD': {'name': 'SPDR Gold Shares', 'industry': 'ETFs', 'market_cap': 60000},
            # 'SLV': {'name': 'iShares Silver Trust', 'industry': 'ETFs', 'market_cap': 15000},
            # 'TLT': {'name': 'iShares 20+ Year Treasury Bond ETF', 'industry': 'ETFs', 'market_cap': 40000},
            # 'HYG': {'name': 'iShares iBoxx $ High Yield Corporate Bond ETF', 'industry': 'ETFs', 'market_cap': 20000},
            # 'LQD': {'name': 'iShares iBoxx $ Investment Grade Corporate Bond ETF', 'industry': 'ETFs', 'market_cap': 30000},
            # 'XLF': {'name': 'Financial Select Sector SPDR Fund', 'industry': 'ETFs', 'market_cap': 40000},
            # 'XLE': {'name': 'Energy Select Sector SPDR Fund', 'industry': 'ETFs', 'market_cap': 40000},
            # 'XLK': {'name': 'Technology Select Sector SPDR Fund', 'industry': 'ETFs', 'market_cap': 50000},
            # 'XLV': {'name': 'Health Care Select Sector SPDR Fund', 'industry': 'ETFs', 'market_cap': 40000},
            # 'XLI': {'name': 'Industrial Select Sector SPDR Fund', 'industry': 'ETFs', 'market_cap': 15000},
            # 'XLP': {'name': 'Consumer Staples Select Sector SPDR Fund', 'industry': 'ETFs', 'market_cap': 20000},
            # 'XLY': {'name': 'Consumer Discretionary Select Sector SPDR Fund', 'industry': 'ETFs', 'market_cap': 20000},
            # 'XLB': {'name': 'Materials Select Sector SPDR Fund', 'industry': 'ETFs', 'market_cap': 10000},
            # 'XLU': {'name': 'Utilities Select Sector SPDR Fund', 'industry': 'ETFs', 'market_cap': 12000},
            # 'XLC': {'name': 'Communication Services Select Sector SPDR Fund', 'industry': 'ETFs', 'market_cap': 15000},
            # 'XLRE': {'name': 'Real Estate Select Sector SPDR Fund', 'industry': 'ETFs', 'market_cap': 5000},
            # 'SMH': {'name': 'VanEck Semiconductor ETF', 'industry': 'ETFs', 'market_cap': 12000},
            # 'ARKK': {'name': 'ARK Innovation ETF', 'industry': 'ETFs', 'market_cap': 8000},
            # 'TQQQ': {'name': 'ProShares UltraPro QQQ', 'industry': 'ETFs', 'market_cap': 20000},
            # 'SPXL': {'name': 'Direxion Daily S&P 500 Bull 3X Shares', 'industry': 'ETFs', 'market_cap': 5000},
        # }
        # return companies
    
    def search_google_news_rss(self, event_types: List[str] = None) -> List[Dict]:
        """
        Primary news source: Google News RSS (free, real-time, no delay)
        
        Args:
            event_types: List of event types to search for
            
        Returns:
            List of article dictionaries
        """
        if event_types is None:
            event_types = ['real_estate_good_news']  # Default
        
        articles = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Build search queries for each event type
        all_queries = []
        for event_type in event_types:
            if event_type in EVENT_TYPES:
                event_config = EVENT_TYPES[event_type]
                
                # Special handling for event types that query by company names (bio_companies, real_estate)
                if event_config.get('query_by_company_names', False):
                    companies = []
                    
                    # Get companies based on event type
                    if event_type.startswith('bio_companies'):
                        # Get category from event config (default to 'all' for backwards compatibility)
                        category = event_config.get('category', 'all')
                        companies = self._get_bio_pharma_companies(category=category)
                        category_label = category.replace('_', '-').upper() if category != 'all' else 'ALL'
                    elif event_type.startswith('real_estate'):
                        companies = self._get_real_estate_companies()
                        category_label = 'REAL ESTATE'
                    else:
                        # Generic fallback - could be extended for other event types
                        companies = []
                        category_label = 'UNKNOWN'
                    
                    if companies:
                        company_queries = []
                        for company in companies[:150]:
                            company_clean = company.replace('"', '').replace("'", '').strip()
                            if company_clean and len(company_clean) > 2:
                                company_queries.append(f'"{company_clean}"')
                        if company_queries:
                            # Reduced batch size from 25 to 5 to avoid Google News RSS query limits
                            # Google News RSS can return 0 results with too many OR terms in a single query
                            # Testing shows batches of 5-10 companies work reliably
                            batch_size = 5
                            for i in range(0, len(company_queries), batch_size):
                                batch = company_queries[i:i + batch_size]
                                search_query = ' OR '.join(batch)
                                # Store the actual company names (without quotes) for this batch for pre-tagging
                                batch_companies = []
                                for query in batch:
                                    # Extract company name from "COMPANY NAME" format
                                    company_name = query.strip('"').strip()
                                    batch_companies.append(company_name)
                                all_queries.append((event_type, search_query, batch_companies))
                        print(f"[{category_label}] Created {len([q for q in all_queries if len(q) == 3])} search queries")
                    continue
                
                keywords = event_config.get('keywords', [])
                # Create search query from keywords (use OR logic)
                # Google News RSS supports: "term1 OR term2 OR term3"
                query_terms = []
                # For bio_positive_news, prioritize high-impact keywords (FDA approval, Phase 3 success, etc.)
                # Limit to most important keywords to avoid query length limits
                if event_type == 'bio_positive_news':
                    # Prioritize: FDA approval, Phase 3 success, Breakthrough Therapy, Fast Track, Priority Review
                    priority_keywords = [
                        'FDA approval', 'FDA approved', 'phase 3 trial success', 'phase 3 meets primary endpoint',
                        'breakthrough therapy designation', 'fast track designation', 'priority review',
                        'positive topline results', 'acquisition offer', 'buyout offer', 'partnership with',
                        'licensing deal', 'orphan drug designation'
                    ]
                    # Use priority keywords first, then fill remaining slots with other keywords
                    used_keywords = set()
                    for kw in priority_keywords:
                        if kw in keywords and kw not in used_keywords:
                            query_terms.append(kw.replace(' ', '+'))
                            used_keywords.add(kw)
                            if len(query_terms) >= 15:
                                break
                    # Fill remaining slots with other keywords
                    for keyword in keywords:
                        if len(query_terms) >= 15:
                            break
                        if keyword not in used_keywords:
                            query_terms.append(keyword.replace(' ', '+'))
                            used_keywords.add(keyword)
                else:
                    # For other event types, use first 15 keywords
                    for keyword in keywords[:15]:
                        # Replace spaces with + for URL encoding
                        query_terms.append(keyword.replace(' ', '+'))
                
                if query_terms:
                    # Use OR for multiple terms
                    search_query = ' OR '.join(query_terms)
                    all_queries.append((event_type, search_query))
        
        # If no queries, nothing to search
        if not all_queries:
            print("[INFO] No valid event types provided for Google News RSS search.")
            return []
        
        # Search for each event type
        for query_info in all_queries:
            # Handle both old format (event_type, search_query) and new format (event_type, search_query, batch_companies)
            if len(query_info) == 3:
                event_type, search_query, batch_companies = query_info
            else:
                event_type, search_query = query_info
                batch_companies = None
            try:
                # Google News RSS with LOOKBACK_DAYS lookback
                # Note: Google News RSS format: q=query+when:Xd (where X is LOOKBACK_DAYS)
                # URL encode the query properly
                encoded_query = urllib.parse.quote_plus(f"{search_query} when:{LOOKBACK_DAYS}d")
                url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en&num=100"
                
                print(f"[API REQUEST] Google News RSS")
                print(f"  Full URL: {url}")
                
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'xml')
                    items = soup.find_all('item')
                    print(f"[API RESPONSE] Google News RSS: {len(items)} articles found")
                    
                    for item in items[:100]:  # Limit to 100 most recent per event type
                        title_elem = item.find('title')
                        pub_date_elem = item.find('pubDate')
                        link_elem = item.find('link')
                        description_elem = item.find('description')
                        
                        if title_elem and title_elem.text:
                            # Clean up title (remove HTML entities)
                            title = title_elem.text.strip()
                            
                            # Get description if available
                            description = ''
                            if description_elem and description_elem.text:
                                description = description_elem.text.strip()
                                # Remove HTML tags from description
                                desc_soup = BeautifulSoup(description, 'html.parser')
                                description = desc_soup.get_text()
                            
                            # Get publication date
                            published_at = ''
                            if pub_date_elem and pub_date_elem.text:
                                published_at = pub_date_elem.text.strip()
                            
                            # Get link
                            url_link = ''
                            if link_elem and link_elem.text:
                                url_link = link_elem.text.strip()
                            
                            # OPTIMIZATION: Pre-tag article with matched company if we can identify it from search query
                            matched_company = None
                            if batch_companies:
                                # Try to match article title/description against companies in this batch
                                article_text = f"{title} {description}".upper()
                                for company in batch_companies:
                                    company_upper = company.upper().strip()
                                    # Use word boundary to avoid partial matches
                                    import re
                                    pattern = r'\b' + re.escape(company_upper) + r'\b'
                                    if re.search(pattern, article_text):
                                        matched_company = company
                                        break  # Use first match found
                            
                            article_dict = {
                                'title': title,
                                'description': description,
                                'content': description,  # Use description as content for now
                                'publishedAt': published_at,
                                'url': url_link,
                                'source': {'name': 'Google News'},
                                'event_type': event_type,  # Tag with event type
                                'matched_company': matched_company  # Pre-tagged company from search query (if found)
                            }
                            articles.append(article_dict)
                    
                elif response.status_code == 429:
                    error_msg = "Google News RSS rate limit. Continuing with available results..."
                    self.api_errors.append({
                        'service': 'Google News RSS',
                        'type': 'rate_limit',
                        'message': error_msg,
                        'status_code': 429
                    })
                else:
                    error_msg = f"Google News RSS returned status {response.status_code}"
                    
            except requests.exceptions.Timeout:
                error_msg = "Google News RSS request timed out."
                self.api_errors.append({
                    'service': 'Google News RSS',
                    'type': 'timeout',
                    'message': error_msg
                })
            except Exception as e:
                error_msg = f"Error fetching from Google News RSS: {e}"
                import traceback
                self.api_errors.append({
                    'service': 'Google News RSS',
                    'type': 'error',
                    'message': error_msg
                })
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_articles = []
        for article in articles:
            title = article.get('title', '').lower().strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_articles.append(article)
        
        return unique_articles
    
    def scrape_layoffs_fyi(self) -> List[Dict]:
        """Legacy method - kept for backward compatibility, now calls search_google_news_rss"""
        return self.search_google_news_rss(event_types=['layoff_event'])
    
    def search_all_realtime_sources(self, event_types: List[str] = None, selected_sources: List[str] = None) -> tuple:
        """
        Search selected real-time RSS sources and return articles + source statistics
        
        Args:
            event_types: List of event types to search for
            selected_sources: List of source keys to search (if None or 'all', searches all)
            
        Returns:
            (articles, source_stats) where source_stats is:
            {
                'reuters': {'name': 'Reuters Business', 'total': 50, 'matched': 8},
                'marketwatch': {'name': 'MarketWatch', 'total': 30, 'matched': 12},
                ...
            }
        """
        if event_types is None:
            event_types = []
        
        if selected_sources is None:
            selected_sources = ['google_news']  # Default
        
        articles = []
        source_stats = {}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Build keywords from event types (skip special cases like bio_companies, real_estate)
        all_keywords = []
        has_special_event = False
        for event_type in event_types:
            if event_type in EVENT_TYPES:
                event_config = EVENT_TYPES[event_type]
                # Check if this is a special event type that doesn't use keywords (bio_companies, real_estate variants)
                if event_config.get('query_by_company_names', False):
                    # This includes bio_companies, real_estate_good_news, real_estate_bad_news
                    has_special_event = True
                else:
                    all_keywords.extend(event_config.get('keywords', []))
        
        # Only return early if no keywords AND no special events
        if not all_keywords and not has_special_event:
            return [], {}
        
        # Determine which sources to search
        all_source_keys = ['google_news', 'benzinga_news']
        if 'all' in selected_sources:
            sources_to_search = all_source_keys
        else:
            sources_to_search = selected_sources if selected_sources else ['google_news']
        
        # Define all RSS sources (real-time, no delay, no auth required)
        rss_sources = [
            {
                'name': 'Benzinga News',
                'url': 'https://www.benzinga.com/news/feed',
                'key': 'benzinga_news'
            },
        ]
        
        # Search Google News RSS if selected (with SSL workaround)
        if 'google_news' in sources_to_search:
            print(f"[SOURCE] Fetching from Google News RSS")
            try:
                google_articles, google_stats = self._try_google_news_rss(event_types, headers)
                articles.extend(google_articles)
                if google_stats:
                    source_stats['google_news'] = google_stats
            except Exception as e:
                print(f"[RESPONSE] Google News RSS: Error - {str(e)[:50]}")
                source_stats['google_news'] = {
                    'name': 'Google News',
                    'total': 0,
                    'matched': 0,
                    'error': str(e)[:50]
                }
        
        # Search selected RSS sources
        seen_titles = set()  # Deduplicate across sources
        
        for source in rss_sources:
            # Skip if source not selected
            if source['key'] not in sources_to_search:
                continue
            total_found = 0
            matched = 0
            
            try:
                print(f"[API REQUEST] {source['name']}")
                print(f"  URL: {source['url']}")
                print(f"  Event Types: {', '.join(event_types)}")
                print(f"  Keywords: {', '.join(all_keywords[:10])}{'...' if len(all_keywords) > 10 else ''}")
                
                response = requests.get(source['url'], headers=headers, timeout=10, verify=False)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'xml')
                    items = soup.find_all('item')
                    total_found = len(items)
                    print(f"[API RESPONSE] {source['name']}: {total_found} total articles retrieved")
                    
                    # Filter by keywords and deduplicate
                    matched_articles = []
                    for item in items:
                        title_elem = item.find('title')
                        if title_elem and title_elem.text:
                            title_text = title_elem.text.strip()
                            title_lower = title_text.lower()
                            
                            # Get description for keyword matching
                            description_elem = item.find('description')
                            description_text = description_elem.text.strip() if description_elem and description_elem.text else ''
                            description_lower = description_text.lower()
                            
                            # Check if matches keywords in both title and description
                            full_text = f"{title_lower} {description_lower}"
                            matches = any(keyword.lower() in full_text for keyword in all_keywords)
                            
                            if matches:
                                # Check for duplicates
                                if title_lower not in seen_titles:
                                    matched += 1
                                    seen_titles.add(title_lower)
                                    
                                    # Build article dict
                                    article_dict = {
                                        'title': title_text,
                                        'description': item.find('description').text.strip() if item.find('description') else '',
                                        'content': item.find('description').text.strip() if item.find('description') else '',
                                        'publishedAt': item.find('pubDate').text.strip() if item.find('pubDate') else '',
                                        'url': item.find('link').text.strip() if item.find('link') else '',
                                        'source': {'name': source['name']},
                                    }
                                    articles.append(article_dict)
                                    matched_articles.append(title_text)
                                else:
                                    # Still count as matched even if duplicate
                                    matched += 1
                    
                    # Log matched articles
                    if matched_articles:
                        print(f"[ARTICLES] {source['name']}: {matched} matched articles")
                        for i, article_title in enumerate(matched_articles[:10], 1):
                            print(f"  {i}. {article_title}")
                        if len(matched_articles) > 10:
                            print(f"  ... and {len(matched_articles) - 10} more")
                    
                    # Store stats for this source
                    source_stats[source['key']] = {
                        'name': source['name'],
                        'total': total_found,
                        'matched': matched
                    }
                    print(f"[SUMMARY] {source['name']}: {total_found} total articles, {matched} matched your event types")
                elif response.status_code == 429:
                    # Rate limit error
                    error_msg = f"Rate limit exceeded (HTTP 429). Too many requests."
                    print(f"[RESPONSE] {source['name']}: {error_msg}")
                    source_stats[source['key']] = {
                        'name': source['name'],
                        'total': 0,
                        'matched': 0,
                        'error': 'HTTP 429 (Rate Limited)'
                    }
                    # Add to API errors for UI display
                    self.api_errors.append({
                        'service': source['name'],
                        'type': 'rate_limit',
                        'message': error_msg,
                        'status_code': 429
                    })
                else:
                    error_msg = f'HTTP {response.status_code}'
                    print(f"[RESPONSE] {source['name']}: {error_msg}")
                    source_stats[source['key']] = {
                        'name': source['name'],
                        'total': 0,
                        'matched': 0,
                        'error': error_msg
                    }
                    
            except requests.exceptions.Timeout:
                print(f"[RESPONSE] {source['name']}: Timeout - No articles retrieved")
                source_stats[source['key']] = {
                    'name': source['name'],
                    'total': 0,
                    'matched': 0,
                    'error': 'Timeout'
                }
            except Exception as e:
                error_msg = str(e)[:50]
                print(f"[RESPONSE] {source['name']}: Error - {error_msg}")
                source_stats[source['key']] = {
                    'name': source['name'],
                    'total': 0,
                    'matched': 0,
                    'error': error_msg
                }
        
        return articles, source_stats
    
    def _try_google_news_rss(self, event_types: List[str], headers: Dict) -> tuple:
        """Try Google News RSS with SSL workarounds"""
        articles = []
        stats = {'name': 'Google News', 'total': 0, 'matched': 0}
        
        if not event_types:
            return articles, stats
        
        # Build query
        all_queries = []
        for event_type in event_types:
            if event_type in EVENT_TYPES:
                event_config = EVENT_TYPES[event_type]
                
                # Special handling for event types that query by company names (bio_companies, real_estate)
                if event_config.get('query_by_company_names', False):
                    companies = []
                    
                    # Get companies based on event type
                    if event_type.startswith('bio_companies'):
                        # Get category from event config (default to 'all' for backwards compatibility)
                        category = event_config.get('category', 'all')
                        companies = self._get_bio_pharma_companies(category=category)
                        category_label = category.replace('_', '-').upper() if category != 'all' else 'ALL'
                    elif event_type.startswith('real_estate'):
                        companies = self._get_real_estate_companies()
                        category_label = 'REAL ESTATE'
                    else:
                        # Generic fallback - could be extended for other event types
                        companies = []
                        category_label = 'UNKNOWN'
                    
                    if companies:
                        company_queries = []
                        for company in companies[:150]:
                            company_clean = company.replace('"', '').replace("'", '').strip()
                            if company_clean and len(company_clean) > 2:
                                company_queries.append(f'"{company_clean}"')
                        if company_queries:
                            # Reduced batch size from 25 to 5 to avoid Google News RSS query limits
                            # Google News RSS can return 0 results with too many OR terms in a single query
                            # Testing shows batches of 5-10 companies work reliably
                            batch_size = 5
                            for i in range(0, len(company_queries), batch_size):
                                batch = company_queries[i:i + batch_size]
                                search_query = ' OR '.join(batch)
                                # Store the actual company names (without quotes) for this batch for pre-tagging
                                batch_companies = []
                                for query in batch:
                                    # Extract company name from "COMPANY NAME" format
                                    company_name = query.strip('"').strip()
                                    batch_companies.append(company_name)
                                all_queries.append((event_type, search_query, batch_companies))
                        print(f"[{category_label}] Created {len([q for q in all_queries if len(q) == 3])} search queries")
                    continue
                
                keywords = event_config.get('keywords', [])
                query_terms = []
                # Increased from 5 to 15 keywords to catch more variations
                for keyword in keywords[:15]:
                    query_terms.append(keyword.replace(' ', '+'))
                if query_terms:
                    search_query = ' OR '.join(query_terms)
                    all_queries.append((event_type, search_query))
        
        if not all_queries:
            return articles, stats
        
        for query_info in all_queries:
            # Handle both old format (event_type, search_query) and new format (event_type, search_query, batch_companies)
            if len(query_info) == 3:
                event_type, search_query, batch_companies = query_info
            else:
                event_type, search_query = query_info
                batch_companies = None
            
            try:
                encoded_query = urllib.parse.quote_plus(f"{search_query} when:{LOOKBACK_DAYS}d")
                url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en&num=100"
                
                print(f"[API REQUEST] Google News RSS")
                print(f"  Event Type: {event_type}")
                print(f"  Query: {search_query}")
                print(f"  URL: {url}")
                
                # Try with SSL verification disabled
                try:
                    response = requests.get(url, headers=headers, timeout=15, verify=False)
                except:
                    # Try HTTP instead
                    url_http = url.replace('https://', 'http://')
                    print(f"[API REQUEST] Retrying Google News RSS with HTTP")
                    response = requests.get(url_http, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'xml')
                    items = soup.find_all('item')
                    items_count = len(items)
                    stats['total'] += items_count
                    stats['matched'] += items_count  # Google News RSS items are pre-filtered by query
                    print(f"[API RESPONSE] Google News RSS: {items_count} articles found")
                    
                    # Log article titles
                    article_titles = []
                    for item in items:
                        title_elem = item.find('title')
                        if title_elem and title_elem.text:
                            title = title_elem.text.strip()
                            description_elem = item.find('description')
                            description = description_elem.text.strip() if description_elem and description_elem.text else ''
                            article_titles.append(title)
                            
                            # OPTIMIZATION: Pre-tag article with matched company if we can identify it from search query
                            matched_company = None
                            if batch_companies:
                                # Try to match article title/description against companies in this batch
                                article_text = f"{title} {description}".upper()
                                for company in batch_companies:
                                    company_upper = company.upper().strip()
                                    # Use word boundary to avoid partial matches
                                    import re
                                    pattern = r'\b' + re.escape(company_upper) + r'\b'
                                    if re.search(pattern, article_text):
                                        matched_company = company
                                        break  # Use first match found
                            
                            article_dict = {
                                'title': title,
                                'description': description,
                                'content': description,
                                'publishedAt': item.find('pubDate').text.strip() if item.find('pubDate') else '',
                                'url': item.find('link').text.strip() if item.find('link') else '',
                                'source': {'name': 'Google News'},
                                'event_type': event_type,  # Tag with event type
                                'matched_company': matched_company  # Pre-tagged company from search query (if found)
                            }
                            articles.append(article_dict)
                            stats['matched'] += 1
                    
                    # Log matched articles
                    if article_titles:
                        print(f"[ARTICLES] Google News RSS: {len(article_titles)} articles")
                        for i, article_title in enumerate(article_titles[:10], 1):
                            print(f"  {i}. {article_title}")
                        if len(article_titles) > 10:
                            print(f"  ... and {len(article_titles) - 10} more")
                    
                    print(f"[SUMMARY] Google News RSS: {items_count} total articles, {items_count} matched your event types")
            except Exception:
                pass
        
        return articles, stats
    
    def _load_sec_companies(self):
        """Load all public companies from SEC EDGAR and build company name → ticker map"""
        if self.sec_companies_loaded:
            return
        
        try:
            # SEC EDGAR company tickers JSON file (updated daily)
            url = f"{SEC_EDGAR_BASE_URL}/files/company_tickers.json"
            headers = {
                'User-Agent': SEC_USER_AGENT,
                'Accept': 'application/json'
            }
            
            print("[SEC EDGAR] Loading public companies list...")
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                # The JSON structure is: {"0": {"cik_str": "0001018724", "ticker": "AMZN", "title": "AMAZON COM INC"}, ...}
                company_count = 0
                for entry in data.values():
                    ticker = entry.get('ticker', '').strip().upper()
                    company_name = entry.get('title', '').strip()
                    cik_str = str(entry.get('cik_str', '')).zfill(10)
                    
                    if ticker and company_name:
                        # Store ticker → CIK mapping
                        self.ticker_to_cik_cache[ticker] = cik_str
                        
                        # Build company name → ticker map with multiple variations
                        # 1. Full company name (e.g., "AMAZON COM INC" → "AMZN")
                        company_name_clean = company_name.upper()
                        self.company_to_ticker_map[company_name_clean] = ticker
                        
                        # 2. Remove common suffixes for better matching
                        suffixes = [' INC', ' CORP', ' CORPORATION', ' CO', ' COMPANY', ' LLC', ' LTD', ' LP', ' GROUP', ' HOLDINGS', ' HOLDING']
                        for suffix in suffixes:
                            if company_name_clean.endswith(suffix):
                                short_name = company_name_clean[:-len(suffix)].strip()
                                if short_name and len(short_name) > 2:
                                    # Only add if not already mapped (prefer longer names)
                                    if short_name not in self.company_to_ticker_map:
                                        self.company_to_ticker_map[short_name] = ticker
                        
                        # 3. Extract first significant word(s) for common company patterns
                        # e.g., "AMAZON COM INC" → "AMAZON"
                        words = company_name_clean.split()
                        if len(words) > 0:
                            first_word = words[0]
                            # Only use single-word if it's substantial (not "THE", "A", etc.)
                            if len(first_word) > 3 and first_word not in ['THE', 'AND', 'FOR', 'INC', 'CORP']:
                                if first_word not in self.company_to_ticker_map:
                                    self.company_to_ticker_map[first_word] = ticker
                        
                        company_count += 1
                
                # Sort companies by length (longest first) once for fast lookups
                # This avoids sorting 15,444+ items on every extract_company_name() call
                self.sorted_companies = sorted(self.company_to_ticker_map.items(), key=lambda x: len(x[0]), reverse=True)
                
                self.sec_companies_loaded = True
                print(f"[SEC EDGAR] Loaded {company_count} public companies")
            elif response.status_code == 429:
                error_msg = "SEC EDGAR rate limit exceeded. Using fallback hardcoded list."
                print(f"[WARNING] {error_msg}")
                self.api_errors.append({
                    'service': 'SEC EDGAR',
                    'type': 'rate_limit',
                    'message': error_msg,
                    'status_code': 429
                })
            else:
                error_msg = f"SEC EDGAR returned status {response.status_code}. Using fallback hardcoded list."
                print(f"[WARNING] {error_msg}")
        except requests.exceptions.Timeout:
            error_msg = "SEC EDGAR request timed out. Using fallback hardcoded list."
            print(f"[WARNING] {error_msg}")
            self.api_errors.append({
                'service': 'SEC EDGAR',
                'type': 'timeout',
                'message': error_msg
            })
        except Exception as e:
            error_msg = f"SEC EDGAR error: {str(e)}. Using fallback hardcoded list."
            print(f"[WARNING] {error_msg}")
            self.api_errors.append({
                'service': 'SEC EDGAR',
                'type': 'unknown_error',
                'message': error_msg
            })
    
    def get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """Get CIK (Central Index Key) from stock ticker using SEC EDGAR"""
        if ticker in self.ticker_to_cik_cache:
            return self.ticker_to_cik_cache[ticker]
        
        # If SEC companies not loaded yet, try loading
        if not self.sec_companies_loaded:
            self._load_sec_companies()
        
        # Check cache again after loading
        if ticker in self.ticker_to_cik_cache:
            return self.ticker_to_cik_cache[ticker]
        
        return None
    
    def fetch_sec_8k_filings(self, ticker: str, company_name: str) -> Optional[Dict]:
        """Fetch 8-K filings for a company from SEC EDGAR"""
        if ticker in self.sec_filings_cache:
            return self.sec_filings_cache[ticker]
        
        cik = self.get_cik_from_ticker(ticker)
        if not cik:
            return None
        
        try:
            # Get company submissions to find recent 8-K filings
            # SEC API requires CIK to be zero-padded to 10 digits in the URL
            url = f"{SEC_EDGAR_COMPANY_API}/CIK{cik}.json"
            headers = {
                'User-Agent': SEC_USER_AGENT,
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                filings = data.get('filings', {}).get('recent', {})
                
                if not filings:
                    return None
                
                # Get form types, filing dates, and accession numbers
                form_types = filings.get('form', [])
                filing_dates = filings.get('filingDate', [])
                accession_numbers = filings.get('accessionNumber', [])
                
                # Find 8-K filings in the last LOOKBACK_DAYS days
                start_date = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).date()
                layoff_8k = None
                
                for i, form_type in enumerate(form_types):
                    if form_type == '8-K':
                        try:
                            filing_date = datetime.strptime(filing_dates[i], '%Y-%m-%d').date()
                            if filing_date >= start_date:
                                accession = accession_numbers[i].replace('-', '')
                                
                                # Check if this 8-K might be about layoffs
                                filing_url = f"{SEC_EDGAR_BASE_URL}/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession_numbers[i]}&xbrl_type=v"
                                
                                # For now, include any 8-K in the date range
                                # In production, you'd want to fetch and parse the filing content
                                # to verify it's about layoffs
                                # SEC filings are typically filed at market open (9:30 AM ET) or after hours
                                # Default to 9:30 AM ET (market open) for better stock price tracking
                                # Note: SEC filings are in ET, but we'll use UTC for consistency
                                filing_dt_aware = datetime.combine(filing_date, datetime.min.time().replace(hour=9, minute=30))
                                filing_dt_aware = filing_dt_aware.replace(tzinfo=timezone.utc)
                                
                                layoff_8k = {
                                    'filing_date': filing_date.strftime('%Y-%m-%d'),
                                    'filing_datetime': filing_dt_aware,
                                    'filing_time': '09:30:00',  # Default to 9:30 AM ET (market open)
                                    'accession_number': accession_numbers[i],
                                    'filing_url': filing_url,
                                    'cik': cik
                                }
                                print(f"  Found 8-K filing: {filing_date}")
                                break
                        except (IndexError, ValueError) as e:
                            continue
                
                if layoff_8k:
                    self.sec_filings_cache[ticker] = layoff_8k
                    return layoff_8k
                else:
                    print(f"  No layoff-related 8-K filings found in last {LOOKBACK_DAYS} days")
                    
            elif response.status_code == 429:
                error_msg = "SEC EDGAR rate limit exceeded."
                self.api_errors.append({
                    'service': 'SEC EDGAR',
                    'type': 'rate_limit',
                    'message': error_msg,
                    'status_code': 429
                })
                
        except requests.exceptions.Timeout:
            error_msg = "SEC EDGAR request timed out."
            self.api_errors.append({
                'service': 'SEC EDGAR',
                'type': 'timeout',
                'message': error_msg
            })
        except Exception as e:
            error_msg = f"SEC EDGAR error: {str(e)}"
            self.api_errors.append({
                'service': 'SEC EDGAR',
                'type': 'unknown_error',
                'message': error_msg
            })
        
        return None
    
    def _check_earnings_dividends_yfinance(self, ticker: str, start_date: datetime, end_date: datetime, future_days: int = 60) -> Dict[str, any]:
        """Check for earnings and dividend events using yfinance
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date to check (typically bearish_date)
            end_date: End date to check (typically target_date)
            future_days: Number of days after end_date to check for next events
            
        Returns:
            Dictionary with:
            - 'events_during': List of events between start_date and end_date
            - 'next_events': List of events after end_date (within future_days)
            - 'has_events_during': Boolean
            - 'has_next_events': Boolean
        """
        result = {
            'events_during': [],
            'next_events': [],
            'has_events_during': False,
            'has_next_events': False
        }
        
        if not YFINANCE_AVAILABLE:
            return result
        
        try:
            import yfinance as yf
            # Ensure SSL verification is disabled (re-apply patch in case session was created before patching)
            try:
                import ssl
                import certifi
                import os
                
                # Re-apply certificate environment variables
                system_cert = '/private/etc/ssl/cert.pem'
                certifi_cert = certifi.where()
                if os.path.exists(system_cert) and os.access(system_cert, os.R_OK):
                    cert_path = system_cert
                else:
                    cert_path = certifi_cert
                os.environ['SSL_CERT_FILE'] = cert_path
                os.environ['REQUESTS_CA_BUNDLE'] = cert_path
                os.environ['CURL_CA_BUNDLE'] = cert_path
                
                # Re-patch curl_cffi to ensure verify=False (in case session was created before patching)
                import curl_cffi.requests as curl_requests
                if not hasattr(curl_requests.Session.request, '_patched_for_yfinance'):
                    original_request = curl_requests.Session.request
                    def patched_request(self, *args, **kwargs):
                        kwargs['verify'] = False
                        return original_request(self, *args, **kwargs)
                    patched_request._patched_for_yfinance = True
                    curl_requests.Session.request = patched_request
            except Exception as ssl_patch_error:
                # If SSL patching fails, continue anyway - the __init__ patch might still work
                pass
            
            ticker_obj = yf.Ticker(ticker)
            
            # Fetch earnings dates (includes both past and future)
            try:
                earnings_dates = ticker_obj.get_earnings_dates(limit=100)
                if earnings_dates is None or len(earnings_dates) == 0:
                    print(f"[EVENT FETCH] yfinance: No earnings dates found for {ticker}")
                else:
                    print(f"[EVENT FETCH] yfinance {ticker}: Found {len(earnings_dates)} total earnings dates")
                if earnings_dates is not None and len(earnings_dates) > 0:
                    # Handle timezone conversion
                    if earnings_dates.index.tz is not None:
                        start_dt = start_date.astimezone(earnings_dates.index.tz)
                        end_dt = end_date.astimezone(earnings_dates.index.tz)
                        future_end_dt = (end_date + timedelta(days=future_days)).astimezone(earnings_dates.index.tz)
                    else:
                        start_dt = start_date
                        end_dt = end_date
                        future_end_dt = end_date + timedelta(days=future_days)
                    
                    # Filter events during period
                    earnings_during = earnings_dates[
                        (earnings_dates.index >= start_dt) & 
                        (earnings_dates.index <= end_dt)
                    ]
                    # Ensure earnings_during is a DataFrame (not Series or list)
                    if not isinstance(earnings_during, type(earnings_dates)):
                        # If it's a Series or single row, convert to DataFrame
                        import pandas as pd
                        if isinstance(earnings_during, pd.Series):
                            earnings_during = earnings_during.to_frame().T
                        elif len(earnings_during) == 0:
                            earnings_during = pd.DataFrame()
                    
                    # Debug: Log filtering results
                    if len(earnings_during) == 0 and len(earnings_dates) > 0:
                        print(f"[EVENT FETCH] yfinance {ticker}: Found {len(earnings_dates)} total earnings dates, but 0 in range {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")
                        # Show first few dates for debugging
                        if len(earnings_dates) > 0:
                            first_dates = earnings_dates.index[:5] if len(earnings_dates) >= 5 else earnings_dates.index
                            print(f"[EVENT FETCH] yfinance {ticker}: Sample earnings dates: {[str(d.date()) for d in first_dates]}")
                    elif len(earnings_during) > 0:
                        print(f"[EVENT FETCH] yfinance {ticker}: Found {len(earnings_during)} earnings in range {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")
                    
                    # Filter next events (future)
                    if future_days > 0:
                        earnings_next = earnings_dates[
                            (earnings_dates.index > end_dt) & 
                            (earnings_dates.index <= future_end_dt)
                        ]
                        # Ensure earnings_next is a DataFrame
                        if not isinstance(earnings_next, type(earnings_dates)):
                            import pandas as pd
                            if isinstance(earnings_next, pd.Series):
                                earnings_next = earnings_next.to_frame().T
                            elif len(earnings_next) == 0:
                                earnings_next = pd.DataFrame()
                    else:
                        earnings_next = []
                    
                    # Convert to events_during format
                    if len(earnings_during) > 0:
                        for date_idx, row in earnings_during.iterrows():
                            event_date = date_idx
                            if event_date.tz is not None:
                                event_date_utc = event_date.astimezone(timezone.utc)
                            else:
                                event_date_utc = event_date.replace(tzinfo=timezone.utc)
                            
                            result['events_during'].append({
                                'date': event_date_utc.strftime('%Y-%m-%d'),
                                'type': 'earnings',
                                'name': 'Earnings',
                                'form': 'yfinance',
                                'description': f"Earnings - {row.get('EPS Estimate', 'N/A')} estimate" if 'EPS Estimate' in row else 'Earnings'
                            })
                            result['has_events_during'] = True
                    
                    # Convert to next_events format
                    if len(earnings_next) > 0:
                        for date_idx, row in earnings_next.iterrows():
                            event_date = date_idx
                            if event_date.tz is not None:
                                event_date_utc = event_date.astimezone(timezone.utc)
                            else:
                                event_date_utc = event_date.replace(tzinfo=timezone.utc)
                            
                            result['next_events'].append({
                                'date': event_date_utc.strftime('%Y-%m-%d'),
                                'type': 'earnings',
                                'name': 'Earnings',
                                'form': 'yfinance',
                                'description': f"Earnings - {row.get('EPS Estimate', 'N/A')} estimate" if 'EPS Estimate' in row else 'Earnings'
                            })
                            result['has_next_events'] = True
            except Exception as e:
                # Earnings fetch failed, continue with dividends
                error_msg = str(e)[:200]
                print(f"[EVENT FETCH] yfinance earnings error for {ticker}: {error_msg}")
                # If it's an SSL error, log it more prominently
                if 'SSL' in error_msg or 'certificate' in error_msg or 'curl' in error_msg:
                    print(f"[EVENT FETCH] ⚠️  yfinance SSL/certificate error for {ticker} - earnings dates cannot be fetched")
            
            # Fetch dividends
            try:
                dividends = ticker_obj.dividends
                if dividends is None or len(dividends) == 0:
                    print(f"[EVENT FETCH] yfinance: No dividends found for {ticker}")
                if dividends is not None and len(dividends) > 0:
                    # Handle timezone conversion
                    if dividends.index.tz is not None:
                        start_dt = start_date.astimezone(dividends.index.tz)
                        end_dt = end_date.astimezone(dividends.index.tz)
                        future_end_dt = (end_date + timedelta(days=future_days)).astimezone(dividends.index.tz)
                    else:
                        start_dt = start_date
                        end_dt = end_date
                        future_end_dt = end_date + timedelta(days=future_days)
                    
                    # Filter dividends during period
                    dividends_during = dividends[
                        (dividends.index >= start_dt) & 
                        (dividends.index <= end_dt)
                    ]
                    # Debug: Log filtering results
                    if len(dividends_during) == 0 and len(dividends) > 0:
                        print(f"[EVENT FETCH] yfinance {ticker}: Found {len(dividends)} total dividends, but 0 in range {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")
                    elif len(dividends_during) > 0:
                        print(f"[EVENT FETCH] yfinance {ticker}: Found {len(dividends_during)} dividends in range {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")
                    
                    # Filter next dividends (future)
                    if future_days > 0:
                        dividends_next = dividends[
                            (dividends.index > end_dt) & 
                            (dividends.index <= future_end_dt)
                        ]
                    else:
                        dividends_next = []
                    
                    # Convert to events_during format
                    for date_idx, dividend_amount in dividends_during.items():
                        event_date = date_idx
                        if event_date.tz is not None:
                            event_date_utc = event_date.astimezone(timezone.utc)
                        else:
                            event_date_utc = event_date.replace(tzinfo=timezone.utc)
                        
                        result['events_during'].append({
                            'date': event_date_utc.strftime('%Y-%m-%d'),
                            'type': 'dividend',
                            'name': f"Dividend ${dividend_amount:.4f}",
                            'form': 'yfinance',
                            'description': f"Dividend payment: ${dividend_amount:.4f} per share",
                            'dividend_rate': float(dividend_amount)
                        })
                        result['has_events_during'] = True
                    
                    # Convert to next_events format
                    for date_idx, dividend_amount in dividends_next.items():
                        event_date = date_idx
                        if event_date.tz is not None:
                            event_date_utc = event_date.astimezone(timezone.utc)
                        else:
                            event_date_utc = event_date.replace(tzinfo=timezone.utc)
                        
                        result['next_events'].append({
                            'date': event_date_utc.strftime('%Y-%m-%d'),
                            'type': 'dividend',
                            'name': f"Dividend ${dividend_amount:.4f}",
                            'form': 'yfinance',
                            'description': f"Dividend payment: ${dividend_amount:.4f} per share",
                            'dividend_rate': float(dividend_amount)
                        })
                        result['has_next_events'] = True
            except Exception as e:
                # Dividends fetch failed, continue
                print(f"[EVENT FETCH] yfinance dividends error for {ticker}: {str(e)[:100]}")
                
        except Exception as e:
            # yfinance not available or error occurred
            print(f"[EVENT FETCH] yfinance general error for {ticker}: {str(e)[:100]}")
        
        return result
    
    def _fetch_stock_news(self, ticker: str, company_name: str, bearish_date: datetime, limit: int = 20) -> List[Dict]:
        """Fetch news articles for a specific stock around the bearish date using yfinance
        
        Note: yfinance only returns the most recent ~10 news articles (no historical filtering).
        This method will return articles that fall within the 7-day window before bearish_date
        if they happen to be in yfinance's recent news feed.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name (not used, kept for compatibility)
            bearish_date: Date when stock dropped
            limit: Maximum number of articles to return
            
        Returns:
            List of news articles with title, description, and publication date
        """
        articles = []
        
        if not YFINANCE_AVAILABLE:
            return articles
        
        try:
            stock = yf.Ticker(ticker)
            news = stock.news
            
            if not news:
                return articles
            
            # Filter news around bearish_date (7 days before to bearish_date)
            start_date = bearish_date - timedelta(days=7)
            
            for item in news:
                # yfinance news structure: data is nested in 'content' key
                content = item.get('content', {})
                if not content:
                    continue
                
                # Get publication date from content.pubDate
                pub_date_str = content.get('pubDate', '')
                if not pub_date_str:
                    continue
                
                try:
                    # Parse ISO format date string (e.g., '2026-01-02T19:11:13Z')
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    continue
                
                # Include articles from 7 days before bearish_date up to and including bearish_date
                if start_date <= pub_date <= bearish_date:
                    # Get URL from canonicalUrl or clickThroughUrl
                    url = ''
                    canonical_url = item.get('canonicalUrl', {})
                    if canonical_url and isinstance(canonical_url, dict):
                        url = canonical_url.get('url', '')
                    if not url:
                        click_through = item.get('clickThroughUrl', {})
                        if click_through and isinstance(click_through, dict):
                            url = click_through.get('url', '')
                    
                    articles.append({
                        'title': content.get('title', ''),
                        'description': content.get('summary', '') or content.get('description', ''),
                        'publishedAt': pub_date.isoformat(),
                        'url': url,
                        'source': 'Yahoo Finance'
                    })
                    if len(articles) >= limit:
                        break
                
        except Exception as e:
            # Error fetching news - return empty list
            pass
        
        return articles
    
    def get_ai_recovery_score(self, ticker: str, company_name: str, stock_data: Dict) -> Dict[str, any]:
        """Get AI recovery score (1-10) only - fast version
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            stock_data: Dictionary containing stock information
            
        Returns:
            Dictionary with 'score' (1-10) or None if error
        """
        if not self.claude_api_key:
            return None
        
        try:
            # Parse bearish date for better formatting in prompt
            bearish_date_obj = datetime.strptime(stock_data['bearish_date'], '%Y-%m-%d')
            bearish_date_formatted = bearish_date_obj.strftime('%B %d, %Y')  # e.g., "December 16, 2025"
            
            # Prepare price history (last 30 days)
            price_history = stock_data.get('price_history', [])
            price_history_text = ""
            if price_history:
                # Format as date: price
                for entry in price_history[-30:]:  # Last 30 data points
                    date_str = entry.get('date', '')
                    price = entry.get('price', '')
                    if date_str and price:
                        price_history_text += f"{date_str}: ${price:.2f}\n"
            
            # Build prompt for score only (simplified, faster)
            # Claude will search the web to understand why the stock dropped
            prompt = f"""You are analyzing a stock drop for a vertical call options trading strategy.

STOCK INFORMATION:
- Ticker: {ticker}
- Company: {company_name}
- Industry: {stock_data.get('industry', 'Unknown')}
- Market Cap: ${stock_data.get('market_cap', 0):,.0f}

DROP DETAILS:
- Bearish Date: {stock_data['bearish_date']}
- Bearish Price: ${stock_data['bearish_price']:.2f}
- Previous Price: ${stock_data.get('prev_price', stock_data['bearish_price']):.2f}
- Drop Percentage: {stock_data['pct_drop']:.2f}%
- Target Date: {stock_data['target_date']}
- Target Price: ${stock_data['target_price']:.2f}
- Recovery Needed: {stock_data['recovery_pct']:.2f}%

PRICE HISTORY (last 30 data points):
{price_history_text}

UPCOMING EVENTS:
{self._format_events_for_ai(stock_data.get('earnings_dividends', {}))}

STRATEGY CONTEXT:
The trader uses vertical call options and hopes to sell if the stock bounces back up within 40 days. They don't necessarily wait for expiration.

TASK:
1. IMPORTANT: Search the web to find specific news about why {ticker} ({company_name}) dropped {stock_data['pct_drop']:.2f}% on {bearish_date_formatted} ({stock_data['bearish_date']}). 
   Search for: "{ticker} stock drop {bearish_date_formatted}" or "{company_name} news {bearish_date_formatted}" or "{ticker} analyst {bearish_date_formatted}"
   Look specifically for:
   - Analyst downgrades, price target cuts, or upgrades (check MarketBeat, Seeking Alpha, financial news)
   - Earnings reports, guidance changes, or financial announcements
   - Leadership changes, executive departures, CEO/CFO changes, or management announcements
   - Regulatory news, policy changes, FDA approvals/rejections, or sector-specific events
   - Company-specific news, press releases, or major announcements
   - Market-wide events that affected the sector
   If you cannot find specific news after searching, clearly state "I could not find specific news" rather than making assumptions.
2. Analyze the price history to identify support/resistance levels, trends, and patterns.
3. Based on your web search results, price history analysis, market conditions, and sector analysis, provide a recovery probability score.

Respond with ONLY a number from 1-10:
- 1-4: Low recovery probability (weak bounce expected)
- 5-7: Moderate recovery probability (some bounce possible)
- 8-10: High recovery probability (strong bounce likely)

Just the number, nothing else."""

            headers = {
                'x-api-key': self.claude_api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            }
            
            payload = {
                'model': 'claude-3-5-haiku-20241022',  # Updated to support web search
                'max_tokens': 200,  # Increased significantly to allow for web search + response
                'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}],  # Enable web search
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            }
            
            response = requests.post(self.claude_api_url, headers=headers, json=payload, timeout=60, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('content', [])
                stop_reason = data.get('stop_reason', '')
                
                # Handle web search response structure
                # Response may contain: server_tool_use, web_search_tool_result, and text
                text = None
                tool_used = False
                for item in content:
                    item_type = item.get('type', '')
                    if item_type == 'text':
                        # Concatenate all text items
                        item_text = item.get('text', '').strip()
                        if text:
                            text += " " + item_text
                        else:
                            text = item_text
                    elif item_type == 'server_tool_use' or item_type == 'tool_use':
                        tool_used = True
                    elif item_type == 'web_search_tool_result':
                        pass  # Tool results received
                
                # If we have text, extract score
                if text:
                    # Extract number from response
                    # Look for patterns like "score: 7", "score is 8", "7/10", or just a standalone number 1-10
                    import re
                    # Try to find explicit score mentions first (prioritize these)
                    score_patterns = [
                        r'score[:\s]+(\d+)',  # "score: 6" or "score is 6"
                        r'(\d+)/10',  # "6/10"
                        r'recovery[:\s]+(?:probability[:\s]+)?(\d+)',  # "recovery probability: 6"
                        r'probability[:\s]+(\d+)',  # "probability: 6"
                    ]
                    score = None
                    for pattern in score_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            score = int(match.group(1))
                            if 1 <= score <= 10:
                                break
                    
                    # If no explicit score found, look for standalone numbers 1-10
                    # But avoid numbers that are part of ranges like "1-4" or "8-10"
                    if score is None:
                        # First, try to find numbers at the end of the response (most likely to be the answer)
                        end_numbers = re.findall(r'\b([1-9]|10)\b', text[-50:])  # Last 50 chars
                        if end_numbers:
                            score = int(end_numbers[-1])  # Take the last number found
                        else:
                            # If no numbers at end, look for numbers not in ranges
                            # Avoid patterns like "1-4", "8-10", "1, 2, 3"
                            all_numbers = re.findall(r'\b([1-9]|10)\b', text)
                            for num_str in reversed(all_numbers):  # Start from end
                                num = int(num_str)
                                # Check if this number is part of a range pattern
                                num_pos = text.rfind(num_str)
                                if num_pos != -1:
                                    # Check context around the number
                                    context_start = max(0, num_pos - 10)
                                    context_end = min(len(text), num_pos + len(num_str) + 10)
                                    context = text[context_start:context_end]
                                    # Skip if it's part of a range like "1-4" or "8-10"
                                    if not re.search(rf'{num_str}\s*[-–]\s*\d+|\d+\s*[-–]\s*{num_str}', context):
                                        score = num
                                        break
                    
                    if score and 1 <= score <= 10:
                        return {'score': score}
                
                # If tool was used but no text yet, make follow-up calls until we get text
                if tool_used and not text:
                    # Build conversation history
                    conversation_messages = payload['messages'].copy()
                    conversation_messages.append({
                        'role': 'assistant',
                        'content': content
                    })
                    
                    # Make up to 3 follow-up calls (web search might need multiple rounds)
                    for follow_up_round in range(3):
                        follow_up_payload = {
                            'model': 'claude-3-5-haiku-20241022',
                            'max_tokens': 200,  # Increased for follow-up
                            'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}],
                            'messages': conversation_messages
                        }
                        
                        follow_up_response = requests.post(self.claude_api_url, headers=headers, json=follow_up_payload, timeout=60, verify=False)
                        if follow_up_response.status_code == 200:
                            follow_up_data = follow_up_response.json()
                            follow_up_content = follow_up_data.get('content', [])
                            follow_up_stop_reason = follow_up_data.get('stop_reason', '')
                            
                            # Collect all text from this response
                            follow_up_text = None
                            for item in follow_up_content:
                                item_type = item.get('type', '')
                                if item_type == 'text':
                                    item_text = item.get('text', '').strip()
                                    if follow_up_text:
                                        follow_up_text += " " + item_text
                                    else:
                                        follow_up_text = item_text
                            
                            if follow_up_text:
                                # Extract score using same improved logic as above
                                import re
                                score_patterns = [
                                    r'score[:\s]+(\d+)',  # "score: 6" or "score is 6"
                                    r'(\d+)/10',  # "6/10"
                                    r'recovery[:\s]+(?:probability[:\s]+)?(\d+)',  # "recovery probability: 6"
                                    r'probability[:\s]+(\d+)',  # "probability: 6"
                                ]
                                score = None
                                for pattern in score_patterns:
                                    match = re.search(pattern, follow_up_text, re.IGNORECASE)
                                    if match:
                                        score = int(match.group(1))
                                        if 1 <= score <= 10:
                                            break
                                
                                # If no explicit score found, look for standalone numbers 1-10
                                # But avoid numbers that are part of ranges like "1-4" or "8-10"
                                if score is None:
                                    # First, try to find numbers at the end of the response
                                    end_numbers = re.findall(r'\b([1-9]|10)\b', follow_up_text[-50:])
                                    if end_numbers:
                                        score = int(end_numbers[-1])
                                    else:
                                        # Look for numbers not in ranges
                                        all_numbers = re.findall(r'\b([1-9]|10)\b', follow_up_text)
                                        for num_str in reversed(all_numbers):
                                            num = int(num_str)
                                            num_pos = follow_up_text.rfind(num_str)
                                            if num_pos != -1:
                                                context_start = max(0, num_pos - 10)
                                                context_end = min(len(follow_up_text), num_pos + len(num_str) + 10)
                                                context = follow_up_text[context_start:context_end]
                                                if not re.search(rf'{num_str}\s*[-–]\s*\d+|\d+\s*[-–]\s*{num_str}', context):
                                                    score = num
                                                    break
                                
                                if score and 1 <= score <= 10:
                                    return {'score': score}
                                
                                # Add text to conversation for next round
                                text = follow_up_text
                            
                            # Add this response to conversation history for next round
                            conversation_messages.append({
                                'role': 'assistant',
                                'content': follow_up_content
                            })
                            
                            # If stop_reason is 'end_turn', we're done
                            if follow_up_stop_reason == 'end_turn':
                                break
                        else:
                            break
            else:
                # Log error for debugging
                print(f"[Claude API Error] Status: {response.status_code}, Response: {response.text[:500]}")
            
            return None
            
        except Exception as e:
            print(f"[Claude API Exception] {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_ai_recovery_opinion(self, ticker: str, company_name: str, stock_data: Dict) -> Dict[str, any]:
        """Get full AI recovery analysis with score and detailed explanation
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            stock_data: Dictionary containing stock information
            
        Returns:
            Dictionary with 'score' (1-10) and 'explanation' (detailed text) or None if error
        """
        if not self.claude_api_key:
            print(f"[AI OPINION] No API key configured")
            return None
        
        # Check if API key is still placeholder
        if self.claude_api_key == 'sk-ant-api03-YourActualClaudeAPIKeyHere-ReplaceThisWithYourRealKey':
            print(f"[AI OPINION] API key is still using placeholder value. Please update config.py with your actual API key.")
            return None
        
        try:
            # Parse bearish date for better formatting in prompt
            bearish_date_obj = datetime.strptime(stock_data['bearish_date'], '%Y-%m-%d')
            bearish_date_formatted = bearish_date_obj.strftime('%B %d, %Y')  # e.g., "December 16, 2025"
            
            # Prepare price history (last 50 days)
            price_history = stock_data.get('price_history', [])
            price_history_text = ""
            if price_history:
                # Format as date: price
                for entry in price_history[-50:]:  # Last 50 data points for full analysis
                    date_str = entry.get('date', '')
                    price = entry.get('price', '')
                    if date_str and price:
                        price_history_text += f"{date_str}: ${price:.2f}\n"
            
            # Build comprehensive prompt
            # Claude will search the web to understand why the stock dropped
            prompt = f"""You are analyzing a stock drop for a broken-wing butterfly options trading strategy.

STOCK INFORMATION:
- Ticker: {ticker}
- Company: {company_name}
- Industry: {stock_data.get('industry', 'Unknown')}
- Market Cap: ${stock_data.get('market_cap', 0):,.0f}

DROP DETAILS:
- Bearish Date: {stock_data['bearish_date']}
- Bearish Price: ${stock_data['bearish_price']:.2f}
- Previous Price: {stock_data.get('prev_price', stock_data['bearish_price']):.2f}
- Drop Percentage: {stock_data['pct_drop']:.2f}%
- Target Date: {stock_data['target_date']}
- Target Price: ${stock_data['target_price']:.2f}
- Recovery Needed: {stock_data['recovery_pct']:.2f}%

PRICE HISTORY (last 50 data points):
{price_history_text}

UPCOMING EVENTS:
{self._format_events_for_ai(stock_data.get('earnings_dividends', {}))}

STRATEGY CONTEXT:
The trader uses a broken-wing butterfly options strategy after a stock experiences a drop of around 5%. This strategy requires specific characteristics to be effective.

MY TRADING STRATEGY REQUIREMENTS (Broken-Wing Butterfly with 30-40 DTE):
You are evaluating stocks for bullish Broken Wing Butterfly (BWB) strategies with 30–40 DTE that rely on:
- Mean reversion after pullbacks
- Stable price behavior
- Liquid option chains
- Early exits (20–35% profit)

Ideal candidates must have:
- Very high options liquidity (tight spreads, high open interest, high daily volume)
- Frequent 3–5% moves with a tendency to stabilize or mean-revert afterward
- Moderate to high implied volatility, especially after a drop
- Deep option chains with many strikes, weekly expirations, and small strike increments
- Large-cap or highly traded stocks with predictable behavior and strong institutional participation

BWB SUITABILITY SCORING RULES:
Score 9–10 (Excellent):
- Large or mega-cap
- Very liquid options
- Mean-reverting behavior
- Business-driven price action
- No binary or overnight event risk

Score 6–8 (Acceptable):
- Generally stable but with some macro or sector sensitivity
- Requires caution (prefer 40 DTE)

Score 4–5 (Weak):
- Trend-prone or macro-driven
- Inconsistent mean reversion

Score 1–3 (Avoid):
- Biotechnology or FDA-driven
- Airlines, shipping, logistics
- Commodity-based (energy, materials)
- High gap or event risk

INDUSTRY BIAS:
Favor (higher scores):
- Information Technology
- Communication Services
- Consumer Discretionary (mega-caps)
- Pharmaceuticals
- Health Care Equipment & Services
- Life Sciences Tools & Services
- Industrial Conglomerates
- Machinery
- Electrical Equipment
- Professional & Commercial Services

Penalize (lower scores):
- Biotechnology
- Airlines & Transportation
- Energy
- Materials
- Utilities
- Real Estate

TASK:
1. IMPORTANT: Search the web to find specific news about why {ticker} ({company_name}) dropped {stock_data['pct_drop']:.2f}% on {bearish_date_formatted} ({stock_data['bearish_date']}). 
   Search for: "{ticker} stock drop {bearish_date_formatted}" or "{company_name} news {bearish_date_formatted}" or "{ticker} analyst {bearish_date_formatted}"
   Look specifically for:
   - Analyst downgrades, price target cuts, or upgrades (check MarketBeat, Seeking Alpha, financial news)
   - Earnings reports, guidance changes, or financial announcements
   - Leadership changes, executive departures, CEO/CFO changes, or management announcements
   - Regulatory news, policy changes, FDA approvals/rejections, or sector-specific events
   - Company-specific news, press releases, or major announcements
   - Market-wide events that affected the sector
   If you cannot find specific news after searching, clearly state "I could not find specific news" rather than making assumptions.

2. Analyze the price history to identify:
   - Support and resistance levels
   - Trend patterns (bullish/bearish/neutral)
   - RSI-like patterns (overbought/oversold conditions)
   - Historical recovery patterns

3. Evaluate whether this ticker fits my broken-wing butterfly options strategy:
   IMPORTANT: Evaluate based on the broken-wing butterfly strategy requirements and BWB Suitability Scoring Rules above. Consider all factors below.
   
   - Provide a strategy fit score (1-10) using the BWB Suitability Scoring Rules:
     * 9-10: Excellent (large/mega-cap, very liquid options, mean-reverting, business-driven, no binary risk)
     * 6-8: Acceptable (generally stable but some macro/sector sensitivity - prefer 40 DTE)
     * 4-5: Weak (trend-prone or macro-driven, inconsistent mean reversion)
     * 1-3: Avoid (biotech/FDA-driven, airlines/shipping/logistics, commodity-based, high gap/event risk)
   
   IMPORTANT: Apply industry bias when scoring:
   - Favor: Information Technology, Communication Services, Consumer Discretionary (mega-caps), Pharmaceuticals, Health Care Equipment & Services, Life Sciences Tools & Services, Industrial Conglomerates, Machinery, Electrical Equipment, Professional & Commercial Services
   - Penalize: Biotechnology, Airlines & Transportation, Energy, Materials, Utilities, Real Estate
   
   - Provide a short explanation (2-4 sentences) of the score
   
   - Liquidity Assessment: Evaluate options liquidity:
     * Tight spreads (narrow bid-ask spreads)
     * High open interest (active options trading)
     * High daily volume (liquid options market)
     * Assess whether liquidity is sufficient for broken-wing butterfly execution
   
   - IV Behavior Assessment: Evaluate implied volatility:
     * Current IV level (low/moderate/high)
     * IV behavior after drops (does IV spike appropriately?)
     * IV rank/percentile if available
     * Whether IV is suitable for the strategy
   
   - Mean-Reversion Tendencies: Analyze price behavior:
     * Frequency of 3-5% moves
     * Tendency to stabilize or mean-revert after drops
     * Historical patterns of recovery after similar drops
     * Whether price action shows mean-reverting characteristics
   
   - Red Flags: Identify any concerns:
     * Upcoming earnings (timing relative to the drop)
     * Significant news events
     * Volatility spikes (unusual or excessive)
     * Low float (limited shares available)
     * Low trading volume
     * Any other factors that could impact the strategy
   
   - Suitability: Provide a clear Yes/No on whether this ticker is suitable for a broken-wing butterfly after a 5% drop:
     * "Yes" if it meets the key requirements and has no major red flags
     * "No" if it lacks critical requirements or has significant red flags
     * Be specific about why it is or isn't suitable

4. Based on your research and analysis, provide:
   - A recovery probability score (1-10):
     * 1-4: Low recovery probability (weak bounce expected)
     * 5-7: Moderate recovery probability (some bounce possible)
     * 8-10: High recovery probability (strong bounce likely)
   
   - Explain why you gave this specific recovery score and whether you think it will recover or not
   - Briefly explain the reason the stock fell (based on your web search/knowledge)

CRITICAL: Respond ONLY with valid JSON. Do not include any text before or after the JSON. Do not wrap the JSON in markdown code blocks. Do not include explanatory text.

Respond in this exact JSON format (no additional text, no markdown, just pure JSON):
{{
  "score": <recovery probability score 1-10>,
  "explanation": "<structured explanation with the following sections:\\n\\n1. STRATEGY FIT EVALUATION:\\n   - Strategy Fit Score: <1-10 using scale: 1-3 poor fit, 4-6 moderate fit, 7-8 good fit, 9-10 excellent fit>\\n   - Short Explanation: <2-4 sentences explaining the score>\\n   - Liquidity Assessment: <Evaluation of options liquidity including spreads, open interest, daily volume, and whether liquidity is sufficient for broken-wing butterfly>\\n   - IV Behavior Assessment: <Evaluation of implied volatility including current level, behavior after drops, IV rank if available, and suitability for strategy>\\n   - Mean-Reversion Tendencies: <Analysis of price behavior including frequency of 3-5% moves, tendency to stabilize/mean-revert, historical recovery patterns, and mean-reverting characteristics>\\n   - Red Flags: <Any concerns including upcoming earnings, significant news, volatility spikes, low float, low trading volume, or other factors that could impact the strategy>\\n   - Suitable for Broken-Wing Butterfly: <Yes or No - clear answer on whether this ticker is suitable for a broken-wing butterfly after a 5% drop, with specific reasoning>\\n\\n2. RECOVERY SCORE EXPLANATION:\\n   - Why this recovery score: <explanation of why you gave this specific recovery score>\\n   - Will it recover: <Yes/No and brief reasoning>\\n\\n3. REASON FOR THE FALL:\\n   - <Brief explanation of why the stock fell, based on web search results>"
}}

The explanation should be plain text with proper line breaks. Use \\n for newlines within the JSON string. Do not include the JSON structure as part of the explanation text itself."""

            headers = {
                'x-api-key': self.claude_api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            }
            
            payload = {
                'model': 'claude-3-5-haiku-20241022',  # Updated to support web search
                'max_tokens': 2000,  # Enough for detailed explanation
                'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}],  # Enable web search
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            }
            
            # Retry logic for network issues
            max_retries = 3
            retry_delay = 2  # seconds
            last_exception = None
            response = None
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        self.claude_api_url, 
                        headers=headers, 
                        json=payload, 
                        timeout=90, 
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        break  # Success, exit retry loop
                    
                    # Handle non-200 status codes
                    print(f"[AI OPINION] API request failed with status {response.status_code} (attempt {attempt + 1}/{max_retries})")
                    try:
                        error_data = response.json()
                        print(f"[AI OPINION] Error response: {error_data}")
                        
                        # Don't retry on authentication errors (401) or bad requests (400)
                        if response.status_code in [400, 401, 403]:
                            return None
                    except:
                        print(f"[AI OPINION] Error response text: {response.text[:500]}")
                    
                    # Retry on server errors (5xx) or rate limits (429)
                    if response.status_code in [429, 500, 502, 503, 504] and attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        print(f"[AI OPINION] Retrying in {wait_time} seconds...")
                        time_module.sleep(wait_time)
                        continue
                    else:
                        return None
                        
                except requests.exceptions.Timeout:
                    last_exception = "Timeout"
                    print(f"[AI OPINION] Request timeout (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"[AI OPINION] Retrying in {wait_time} seconds...")
                        time_module.sleep(wait_time)
                    else:
                        print(f"[AI OPINION] Max retries reached. Timeout error.")
                        return None
                        
                except requests.exceptions.ConnectionError as e:
                    last_exception = f"ConnectionError: {str(e)[:100]}"
                    print(f"[AI OPINION] Connection error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"[AI OPINION] Retrying in {wait_time} seconds...")
                        time_module.sleep(wait_time)
                    else:
                        print(f"[AI OPINION] Max retries reached. Connection error: {str(e)[:200]}")
                        return None
                        
                except requests.exceptions.RequestException as e:
                    last_exception = f"RequestException: {str(e)[:100]}"
                    print(f"[AI OPINION] Request error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"[AI OPINION] Retrying in {wait_time} seconds...")
                        time_module.sleep(wait_time)
                    else:
                        print(f"[AI OPINION] Max retries reached. Request error: {str(e)[:200]}")
                        return None
                        
                except Exception as e:
                    last_exception = f"Unexpected error: {str(e)[:100]}"
                    print(f"[AI OPINION] Unexpected error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
                    import traceback
                    traceback.print_exc()
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"[AI OPINION] Retrying in {wait_time} seconds...")
                        time_module.sleep(wait_time)
                    else:
                        print(f"[AI OPINION] Max retries reached. Error: {str(e)[:200]}")
                        return None
            
            # Check if we got a successful response
            if response is None or response.status_code != 200:
                print(f"[AI OPINION] Failed after {max_retries} attempts. Last error: {last_exception}")
                return None
            
            # Process successful response
            if response.status_code == 200:
                data = response.json()
                content = data.get('content', [])
                stop_reason = data.get('stop_reason', '')
                
                # Handle web search response structure
                # Response may contain: server_tool_use, web_search_tool_result, and text
                text = None
                tool_used = False
                for item in content:
                    item_type = item.get('type', '')
                    if item_type == 'text':
                        # Concatenate all text items
                        item_text = item.get('text', '').strip()
                        if text:
                            text += " " + item_text
                        else:
                            text = item_text
                    elif item_type == 'server_tool_use' or item_type == 'tool_use':
                        tool_used = True
                
                if text:
                    # Try to parse JSON response
                    import json
                    import re
                    explanation = text
                    score = 5  # Default
                    
                    try:
                        # First, try to extract JSON from the text if it's embedded
                        # Remove markdown code blocks
                        text_clean = text.replace('```json', '').replace('```', '').strip()
                        
                        # Try to find JSON object in the text (even if there's text before it)
                        json_start = text_clean.find('{')
                        if json_start != -1:
                            # Find matching closing brace (handle nested objects)
                            brace_count = 0
                            json_end = json_start
                            in_string = False
                            escape_next = False
                            
                            for i in range(json_start, len(text_clean)):
                                char = text_clean[i]
                                
                                if escape_next:
                                    escape_next = False
                                    continue
                                
                                if char == '\\':
                                    escape_next = True
                                    continue
                                
                                if char == '"' and not escape_next:
                                    in_string = not in_string
                                    continue
                                
                                if not in_string:
                                    if char == '{':
                                        brace_count += 1
                                    elif char == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            json_end = i + 1
                                            break
                            
                            if json_end > json_start and brace_count == 0:
                                json_str = text_clean[json_start:json_end]
                                result = json.loads(json_str)
                                score = result.get('score', 5)
                                explanation = result.get('explanation', '')
                                # If explanation is empty, use the text before JSON as fallback
                                if not explanation and json_start > 0:
                                    explanation = text_clean[:json_start].strip()
                            else:
                                # Try parsing the entire cleaned text as JSON
                                result = json.loads(text_clean)
                                score = result.get('score', 5)
                                explanation = result.get('explanation', text_clean)
                        else:
                            # Try parsing the entire cleaned text as JSON
                            result = json.loads(text_clean)
                            score = result.get('score', 5)
                            explanation = result.get('explanation', text_clean)
                        
                        # Clamp score to 1-10
                        score = max(1, min(10, int(score)))
                        
                        # Clean up explanation - remove escaped newlines and format
                        if isinstance(explanation, str):
                            explanation = explanation.replace('\\n', '\n').replace('\\t', '\t')
                        
                        return {
                            'score': score,
                            'explanation': explanation
                        }
                    except (json.JSONDecodeError, ValueError, AttributeError) as parse_error:
                        # Log the parsing error for debugging
                        print(f"[AI OPINION] JSON parsing failed: {str(parse_error)}")
                        print(f"[AI OPINION] Text that failed to parse (first 500 chars): {text[:500]}")
                        
                        # If JSON parsing fails, try to extract score and use text as explanation
                        # Use same patterns as score-only method for consistency
                        score_patterns = [
                            r'"score"[:\s]+(\d+)',  # JSON format
                            r'score[:\s]+(\d+)',
                            r'(\d+)/10',
                            r'recovery[:\s]+(?:probability[:\s]+)?(\d+)',  # "recovery probability: 6"
                            r'probability[:\s]+(\d+)',  # "probability: 6"
                        ]
                        for pattern in score_patterns:
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                score = int(match.group(1))
                                if 1 <= score <= 10:
                                    break
                        
                        # Clean up explanation text
                        explanation = text.replace('\\n', '\n').replace('\\t', '\t')
                        
                        return {
                            'score': score,
                            'explanation': explanation
                        }
                
                # If tool was used but no text yet, make follow-up calls until we get text
                if tool_used and not text:
                    # Build conversation history
                    conversation_messages = payload['messages'].copy()
                    conversation_messages.append({
                        'role': 'assistant',
                        'content': content
                    })
                    
                    # Make up to 3 follow-up calls
                    for follow_up_round in range(3):
                        follow_up_payload = {
                            'model': 'claude-3-5-haiku-20241022',
                            'max_tokens': 2000,
                            'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}],
                            'messages': conversation_messages
                        }
                        
                        follow_up_response = requests.post(self.claude_api_url, headers=headers, json=follow_up_payload, timeout=90, verify=False)
                        if follow_up_response.status_code == 200:
                            follow_up_data = follow_up_response.json()
                            follow_up_content = follow_up_data.get('content', [])
                            follow_up_stop_reason = follow_up_data.get('stop_reason', '')
                            
                            # Collect all text from this response
                            follow_up_text = None
                            for item in follow_up_content:
                                item_type = item.get('type', '')
                                if item_type == 'text':
                                    item_text = item.get('text', '').strip()
                                    if follow_up_text:
                                        follow_up_text += " " + item_text
                                    else:
                                        follow_up_text = item_text
                            
                            if follow_up_text:
                                # Try to parse JSON
                                import json
                                import re
                                try:
                                    follow_up_text_clean = follow_up_text.replace('```json', '').replace('```', '').strip()
                                    
                                    # Try to find JSON object in the text (even if there's text before it)
                                    json_start = follow_up_text_clean.find('{')
                                    if json_start != -1:
                                        # Find matching closing brace (handle nested objects and strings)
                                        brace_count = 0
                                        json_end = json_start
                                        in_string = False
                                        escape_next = False
                                        
                                        for i in range(json_start, len(follow_up_text_clean)):
                                            char = follow_up_text_clean[i]
                                            
                                            if escape_next:
                                                escape_next = False
                                                continue
                                            
                                            if char == '\\':
                                                escape_next = True
                                                continue
                                            
                                            if char == '"' and not escape_next:
                                                in_string = not in_string
                                                continue
                                            
                                            if not in_string:
                                                if char == '{':
                                                    brace_count += 1
                                                elif char == '}':
                                                    brace_count -= 1
                                                    if brace_count == 0:
                                                        json_end = i + 1
                                                        break
                                        
                                        if json_end > json_start and brace_count == 0:
                                            json_str = follow_up_text_clean[json_start:json_end]
                                            result = json.loads(json_str)
                                            score = result.get('score', 5)
                                            explanation = result.get('explanation', '')
                                            # If explanation is empty, use the text before JSON as fallback
                                            if not explanation and json_start > 0:
                                                explanation = follow_up_text_clean[:json_start].strip()
                                        else:
                                            result = json.loads(follow_up_text_clean)
                                            score = result.get('score', 5)
                                            explanation = result.get('explanation', follow_up_text_clean)
                                    else:
                                        result = json.loads(follow_up_text_clean)
                                        score = result.get('score', 5)
                                        explanation = result.get('explanation', follow_up_text_clean)
                                    
                                    score = max(1, min(10, int(score)))
                                    
                                    # Clean up explanation
                                    if isinstance(explanation, str):
                                        explanation = explanation.replace('\\n', '\n').replace('\\t', '\t')
                                    
                                    return {
                                        'score': score,
                                        'explanation': explanation
                                    }
                                except (json.JSONDecodeError, ValueError, AttributeError):
                                    # Extract score from text
                                    # Use same patterns as score-only method for consistency
                                    score_patterns = [
                                        r'"score"[:\s]+(\d+)',  # JSON format
                                        r'score[:\s]+(\d+)',
                                        r'(\d+)/10',
                                        r'recovery[:\s]+(?:probability[:\s]+)?(\d+)',  # "recovery probability: 6"
                                        r'probability[:\s]+(\d+)',  # "probability: 6"
                                    ]
                                    score = 5
                                    for pattern in score_patterns:
                                        match = re.search(pattern, follow_up_text, re.IGNORECASE)
                                        if match:
                                            score = int(match.group(1))
                                            if 1 <= score <= 10:
                                                break
                                    
                                    # Clean up explanation
                                    explanation = follow_up_text.replace('\\n', '\n').replace('\\t', '\t')
                                    
                                    return {
                                        'score': score,
                                        'explanation': explanation
                                    }
                            
                            # Add this response to conversation history for next round
                            conversation_messages.append({
                                'role': 'assistant',
                                'content': follow_up_content
                            })
                            
                            # If stop_reason is 'end_turn', we're done
                            if follow_up_stop_reason == 'end_turn':
                                break
                        else:
                            break
            
            print(f"[AI OPINION] No text content in response")
            return None
            
        except Exception as e:
            print(f"[AI OPINION] Exception in get_ai_recovery_opinion: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _format_events_for_ai(self, earnings_dividends: Dict) -> str:
        """Format earnings/dividends events for AI prompt"""
        events_text = ""
        
        events_during = earnings_dividends.get('events_during', [])
        next_events = earnings_dividends.get('next_events', [])
        
        if events_during:
            events_text += "Events During Drop Period:\n"
            for event in events_during[:5]:
                events_text += f"  - {event.get('name', 'Event')} on {event.get('date', 'N/A')} ({event.get('type', 'unknown')})\n"
        
        if next_events:
            events_text += "\nUpcoming Events (next 40 days):\n"
            for event in next_events[:5]:
                events_text += f"  - {event.get('name', 'Event')} on {event.get('date', 'N/A')} ({event.get('type', 'unknown')})\n"
        
        if not events_text:
            events_text = "No significant events found."
        
        return events_text
    
    def _check_earnings_dividends_nasdaq(self, ticker: str, start_date: datetime, end_date: datetime, future_days: int = 60) -> Dict[str, any]:
        """Check for earnings and dividend events using NASDAQ public API
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date to check (typically bearish_date)
            end_date: End date to check (typically target_date)
            future_days: Number of days after end_date to check for next events
            
        Returns:
            Dictionary with:
            - 'events_during': List of events between start_date and end_date
            - 'next_events': List of events after end_date (within future_days)
            - 'has_events_during': Boolean
            - 'has_next_events': Boolean
        """
        result = {
            'events_during': [],
            'next_events': [],
            'has_events_during': False,
            'has_next_events': False
        }
        
        try:
            # NASDAQ earnings calendar endpoint (date-based, shows all earnings on that date)
            # Format: https://api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD
            # We need to query multiple dates and filter by ticker
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://www.nasdaq.com/'
            }
            
            start_date_only = start_date.date()
            end_date_only = end_date.date()
            future_end_date = end_date_only + timedelta(days=future_days)
            
            # Query dates during the period (between start_date and end_date) for events_during
            dates_during_period = []
            current_date = start_date_only
            while current_date <= end_date_only:
                dates_during_period.append(current_date)
                current_date += timedelta(days=1)
                # Safety limit
                if len(dates_during_period) >= 100:
                    break
            
            # Query dates in the future range (for "next events") - only if future_days > 0
            dates_to_query = []
            if future_days > 0:
                current_date = end_date_only + timedelta(days=1)  # Start day after target_date
                # Query every day to catch all earnings (no missed dates)
                while current_date <= future_end_date:
                    dates_to_query.append(current_date)
                    current_date += timedelta(days=1)  # Daily queries for accuracy
                    
                    # Safety limit: max 50 queries total (covers up to 50 days)
                    if len(dates_to_query) >= 50:
                        break
            
            # Query NASDAQ API for dates during period (for events_during)
            ticker_upper = ticker.upper()
            for query_date in dates_during_period:
                try:
                    nasdaq_url = f"https://api.nasdaq.com/api/calendar/earnings?date={query_date.strftime('%Y-%m-%d')}"
                    response = requests.get(nasdaq_url, headers=headers, timeout=5, verify=False)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                        except (ValueError, json.JSONDecodeError):
                            continue
                        
                        earnings_data = data.get('data', {})
                        if not isinstance(earnings_data, dict):
                            continue
                            
                        rows = earnings_data.get('rows', [])
                        if not isinstance(rows, list):
                            continue
                        
                        # Filter by ticker
                        for event in rows:
                            if not isinstance(event, dict):
                                continue
                                
                            event_ticker = event.get('symbol', '')
                            if event_ticker and event_ticker.upper() == ticker_upper:
                                fiscal_quarter = event.get('fiscalQuarterEnding', '')
                                company_name = event.get('name', '')
                                
                                event_info = {
                                    'date': query_date.strftime('%Y-%m-%d'),
                                    'type': 'earnings',
                                    'name': f"Earnings ({fiscal_quarter})" if fiscal_quarter else 'Earnings',
                                    'form': 'NASDAQ Calendar',
                                    'accession': None,
                                    'description': f"{company_name} - {fiscal_quarter}" if fiscal_quarter else company_name
                                }
                                
                                result['events_during'].append(event_info)
                                result['has_events_during'] = True
                                break
                except Exception:
                    continue
            
            # Query NASDAQ API for future dates (for next_events) - only if future_days > 0
            for idx, query_date in enumerate(dates_to_query):
                # Removed delay for faster processing (NASDAQ API is usually tolerant)
                # If rate limiting occurs, we can add it back
                
                try:
                    nasdaq_url = f"https://api.nasdaq.com/api/calendar/earnings?date={query_date.strftime('%Y-%m-%d')}"
                    response = requests.get(nasdaq_url, headers=headers, timeout=5, verify=False)  # Reduced timeout from 10s to 5s for faster failure
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                        except (ValueError, json.JSONDecodeError):
                            # Skip if JSON parsing fails
                            continue
                        
                        # Handle different response structures
                        if not isinstance(data, dict):
                            continue
                            
                        earnings_data = data.get('data', {})
                        if not isinstance(earnings_data, dict):
                            continue
                            
                        rows = earnings_data.get('rows', [])
                        if not isinstance(rows, list):
                            continue
                        
                        # Filter by ticker
                        for event in rows:
                            if not isinstance(event, dict):
                                continue
                                
                            event_ticker = event.get('symbol', '')
                            if not event_ticker:
                                continue
                                
                            if event_ticker.upper() == ticker_upper:
                                # Found earnings for this ticker on this date
                                fiscal_quarter = event.get('fiscalQuarterEnding', '')
                                company_name = event.get('name', '')
                                
                                event_info = {
                                    'date': query_date.strftime('%Y-%m-%d'),
                                    'type': 'earnings',
                                    'name': f"Earnings ({fiscal_quarter})" if fiscal_quarter else 'Earnings',
                                    'form': 'NASDAQ Calendar',
                                    'accession': None,
                                    'description': f"{company_name} - {fiscal_quarter}" if fiscal_quarter else company_name
                                }
                                
                                # This is a "next event" (after target_date)
                                result['next_events'].append(event_info)
                                result['has_next_events'] = True
                                
                                # Only need to find first occurrence per date
                                break
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException):
                    # Skip this date if API call fails
                    continue
                except Exception:
                    # Skip if any other error occurs
                    continue
            
            # Sort events by date
            result['events_during'].sort(key=lambda x: x['date'])
            result['next_events'].sort(key=lambda x: x['date'])
            
            # Also check for dividends during the period
            for query_date in dates_during_period:
                try:
                    dividends_url = f"https://api.nasdaq.com/api/calendar/dividends?date={query_date.strftime('%Y-%m-%d')}"
                    response = requests.get(dividends_url, headers=headers, timeout=5, verify=False)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                        except (ValueError, json.JSONDecodeError):
                            continue
                        
                        calendar_data = data.get('data', {}).get('calendar', {})
                        if not isinstance(calendar_data, dict):
                            continue
                            
                        rows = calendar_data.get('rows', [])
                        if not isinstance(rows, list):
                            continue
                        
                        # Filter by ticker
                        for event in rows:
                            if not isinstance(event, dict):
                                continue
                                
                            event_ticker = event.get('symbol', '')
                            if not event_ticker or event_ticker.upper() != ticker_upper:
                                continue
                            
                            ex_date_str = event.get('dividend_Ex_Date', '')
                            payment_date_str = event.get('payment_Date', '')
                            dividend_rate = event.get('dividend_Rate', 0)
                            company_name = event.get('companyName', '')
                            
                            # Parse dates
                            ex_date = None
                            if ex_date_str:
                                try:
                                    ex_date = datetime.strptime(ex_date_str, '%m/%d/%Y').date()
                                except:
                                    try:
                                        ex_date = datetime.strptime(ex_date_str, '%m/%d/%y').date()
                                    except:
                                        pass
                            
                            event_date = ex_date if ex_date else query_date
                            
                            if start_date_only <= event_date <= end_date_only:
                                dividend_info = {
                                    'date': event_date.strftime('%Y-%m-%d'),
                                    'type': 'dividend',
                                    'name': f"Dividend ${dividend_rate:.2f}" if dividend_rate else 'Dividend',
                                    'form': 'NASDAQ Calendar',
                                    'accession': None,
                                    'description': f"{company_name} - ${dividend_rate:.2f} per share" if dividend_rate else company_name,
                                    'dividend_rate': dividend_rate,
                                    'ex_date': ex_date_str,
                                    'payment_date': payment_date_str
                                }
                                
                                result['events_during'].append(dividend_info)
                                result['has_events_during'] = True
                                break
                except Exception:
                    continue
            
            # Also check for dividends in the future (for next_events) - only if future_days > 0
            for query_date in dates_to_query:
                try:
                    dividends_url = f"https://api.nasdaq.com/api/calendar/dividends?date={query_date.strftime('%Y-%m-%d')}"
                    response = requests.get(dividends_url, headers=headers, timeout=5, verify=False)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                        except (ValueError, json.JSONDecodeError):
                            continue
                        
                        # Dividends structure: data.calendar.rows (different from earnings)
                        calendar_data = data.get('data', {}).get('calendar', {})
                        if not isinstance(calendar_data, dict):
                            continue
                            
                        rows = calendar_data.get('rows', [])
                        if not isinstance(rows, list):
                            continue
                        
                        # Filter by ticker
                        for event in rows:
                            if not isinstance(event, dict):
                                continue
                                
                            event_ticker = event.get('symbol', '')
                            if not event_ticker or event_ticker.upper() != ticker_upper:
                                continue
                            
                            # Found dividend for this ticker
                            ex_date_str = event.get('dividend_Ex_Date', '')
                            payment_date_str = event.get('payment_Date', '')
                            dividend_rate = event.get('dividend_Rate', 0)
                            company_name = event.get('companyName', '')
                            
                            # Parse dates (format: "1/06/2026" or "01/06/2026")
                            ex_date = None
                            if ex_date_str:
                                try:
                                    ex_date = datetime.strptime(ex_date_str, '%m/%d/%Y').date()
                                except:
                                    try:
                                        ex_date = datetime.strptime(ex_date_str, '%m/%d/%y').date()
                                    except:
                                        pass
                            
                            # Use ex-date or query_date as the event date
                            event_date = ex_date if ex_date else query_date
                            
                            dividend_info = {
                                'date': event_date.strftime('%Y-%m-%d'),
                                'type': 'dividend',
                                'name': f"Dividend ${dividend_rate:.2f}" if dividend_rate else 'Dividend',
                                'form': 'NASDAQ Calendar',
                                'accession': None,
                                'description': f"{company_name} - ${dividend_rate:.2f} per share" if dividend_rate else company_name,
                                'dividend_rate': dividend_rate,
                                'ex_date': ex_date_str,
                                'payment_date': payment_date_str
                            }
                            
                            # Check if dividend is during the period or in the future
                            if start_date_only <= event_date <= end_date_only:
                                result['events_during'].append(dividend_info)
                                result['has_events_during'] = True
                            elif event_date > end_date_only:
                                result['next_events'].append(dividend_info)
                                result['has_next_events'] = True
                            
                            # Only need to find first occurrence per date
                            break
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException):
                    continue
                except Exception:
                    continue
            
            # Sort all events by date
            result['events_during'].sort(key=lambda x: x['date'])
            result['next_events'].sort(key=lambda x: x['date'])
            
        except Exception as e:
            # Silently fail - don't break the main flow
            pass
        
        return result
    
    def get_stock_next_events(self, ticker: str, bearish_date: datetime, target_date: datetime, future_days: int = 40) -> Dict[str, any]:
        """Get next events (future earnings/dividends) for a single stock (on-demand fetching)
        
        Args:
            ticker: Stock ticker symbol
            bearish_date: Bearish date
            target_date: Target date
            future_days: Number of days after target_date to check
            
        Returns:
            Dictionary with next_events data only
        """
        result = {
            'next_events': [],
            'has_next_events': False,
            'next_events_loaded': True
        }
        
        try:
            # Fetch next_events using SEC EDGAR (historical filings that might be in future range)
            sec_result = self._check_earnings_dividends_sec(ticker, bearish_date, target_date, future_days=future_days)
            if sec_result:
                result['next_events'].extend(sec_result.get('next_events', []))
            
            # Then try yfinance (future scheduled events and dividends) - replaces NASDAQ, much faster and finds more events
            try:
                yfinance_result = self._check_earnings_dividends_yfinance(ticker, bearish_date, target_date, future_days=future_days)
                if yfinance_result:
                    yfinance_next_events = yfinance_result.get('next_events', [])
                    if yfinance_next_events:
                        result['next_events'].extend(yfinance_next_events)
                    
                    # Remove duplicates and sort by date
                    seen_events = set()
                    unique_events = []
                    for event in sorted(result['next_events'], key=lambda x: (x['date'], x.get('type', ''))):
                        event_key = (event['date'], event.get('type', ''), event.get('name', ''))
                        if event_key not in seen_events:
                            seen_events.add(event_key)
                            unique_events.append(event)
                    result['next_events'] = unique_events
                    result['has_next_events'] = len(result['next_events']) > 0
            except Exception as yfinance_error:
                # If yfinance fails, just use SEC results
                pass
        except Exception as e:
            # If both fail, return empty result
            pass
        
        return result
    
    def _check_earnings_dividends_sec(self, ticker: str, start_date: datetime, end_date: datetime, future_days: int = 60) -> Dict[str, any]:
        """Check for earnings and dividend events using SEC EDGAR
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date to check (typically bearish_date)
            end_date: End date to check (typically target_date)
            future_days: Number of days after end_date to check for next events
            
        Returns:
            Dictionary with:
            - 'events_during': List of events between start_date and end_date
            - 'next_events': List of events after end_date (within future_days)
            - 'has_events_during': Boolean
            - 'has_next_events': Boolean
        """
        result = {
            'events_during': [],
            'next_events': [],
            'has_events_during': False,
            'has_next_events': False
        }
        
        try:
            # Get CIK from ticker (with timeout protection)
            cik = self.get_cik_from_ticker(ticker)
            if not cik:
                return result
            
            # Fetch company filings with shorter timeout to avoid blocking
            url = f"{SEC_EDGAR_COMPANY_API}/CIK{cik}.json"
            headers = {
                'User-Agent': SEC_USER_AGENT,
                'Accept': 'application/json'
            }
            
            # Use shorter timeout (3 seconds) to avoid blocking the main flow
            try:
                response = requests.get(url, headers=headers, timeout=3)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException):
                # If SEC EDGAR times out or fails, just return empty result
                return result
            
            if response.status_code != 200:
                return result
            
            try:
                data = response.json()
            except (ValueError, json.JSONDecodeError):
                return result
            
            filings = data.get('filings', {}).get('recent', {})
            if not filings:
                return result
            
            form_types = filings.get('form', [])
            filing_dates = filings.get('filingDate', [])
            accession_numbers = filings.get('accessionNumber', [])
            descriptions = filings.get('description', [])
            
            # Calculate date ranges
            start_date_only = start_date.date()
            end_date_only = end_date.date()
            future_end_date = end_date_only + timedelta(days=future_days)
            
            # Process each filing
            for i, form_type in enumerate(form_types):
                if i >= len(filing_dates) or i >= len(accession_numbers):
                    continue
                
                try:
                    filing_date_str = filing_dates[i]
                    filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d').date()
                    accession = accession_numbers[i]
                    desc = descriptions[i] if i < len(descriptions) else ''
                    
                    event_type = None
                    event_name = None
                    
                    # Check for earnings-related forms
                    if form_type in ['10-Q', '10-K']:
                        event_type = 'earnings'
                        event_name = f"{form_type} Earnings"
                    elif form_type == '8-K':
                        desc_lower = desc.lower()
                        # Item 2.02: Results of Operations and Financial Condition
                        if '2.02' in desc or 'results of operations' in desc_lower:
                            event_type = 'earnings'
                            event_name = '8-K Earnings'
                        # Item 8.01: Other Events (often used for dividends)
                        elif '8.01' in desc and any(kw in desc_lower for kw in ['dividend', 'cash dividend', 'quarterly dividend']):
                            event_type = 'dividend'
                            event_name = '8-K Dividend'
                    
                    if event_type:
                        event_info = {
                            'date': filing_date.strftime('%Y-%m-%d'),  # Convert date to string for JSON serialization
                            'type': event_type,
                            'name': event_name,
                            'form': form_type,
                            'accession': accession,
                            'description': desc
                        }
                        
                        # Check if event is during the period
                        if start_date_only <= filing_date <= end_date_only:
                            result['events_during'].append(event_info)
                            result['has_events_during'] = True
                        # Check if event is in the future (next events) - after target_date but within future_days
                        elif end_date_only < filing_date <= future_end_date:
                            result['next_events'].append(event_info)
                            result['has_next_events'] = True
                        # Note: If filing_date > future_end_date, it's beyond our search window (ignored)
                
                except (ValueError, IndexError, KeyError, AttributeError):
                    continue
            
            # Sort events by date
            result['events_during'].sort(key=lambda x: x['date'])
            result['next_events'].sort(key=lambda x: x['date'])
            
        except Exception as e:
            # Silently fail - don't break the main flow if SEC EDGAR fails
            # Log to debug if needed, but don't raise
            pass
        
        return result
    
    def fetch_layoffs(self, fetch_full_content: bool = True, event_types: List[str] = None, selected_sources: List[str] = None):
        """Fetch all layoff announcements
        
        Args:
            fetch_full_content: If True, will fetch full article content for missing data (slower but more accurate)
            event_types: List of event types to search for
            selected_sources: List of source keys to search (if None, searches all)
        """
        if event_types is None:
            event_types = ['real_estate_good_news']  # Default
        
        if selected_sources is None:
            selected_sources = ['google_news']  # Default
        
        # PRIMARY SOURCE: Search selected real-time RSS sources (no delay, free)
        articles, source_stats = self.search_all_realtime_sources(event_types=event_types, selected_sources=selected_sources)
        self.source_stats = source_stats
        
        print(f"[INFO] Total articles retrieved: {len(articles)}")
        print(f"[INFO] Source statistics:")
        for key, stats in source_stats.items():
            error_msg = f" ({stats.get('error', '')})" if stats.get('error') else ""
            print(f"  {stats['name']}: {stats['total']} total, {stats['matched']} matched{error_msg}")
        
        # OPTIMIZATION: Sort articles by date (most recent first) before processing
        def parse_date(date_str):
            """Parse various date formats from RSS feeds"""
            if not date_str:
                return datetime.min.replace(tzinfo=timezone.utc)
            try:
                # Try parsing common RSS date formats
                from dateutil import parser
                return parser.parse(date_str).replace(tzinfo=timezone.utc)
            except:
                return datetime.min.replace(tzinfo=timezone.utc)
        
        articles.sort(key=lambda x: parse_date(x.get('publishedAt', '')), reverse=True)
        print(f"[OPTIMIZATION] Sorted articles by date (most recent first)")
        
        # OPTIMIZATION: Limit total articles to process
        if len(articles) > MAX_ARTICLES_TO_PROCESS:
            print(f"[OPTIMIZATION] Limiting to {MAX_ARTICLES_TO_PROCESS} most recent articles (from {len(articles)} total)")
            articles = articles[:MAX_ARTICLES_TO_PROCESS]
        
        # First pass: Extract from titles/descriptions only (fast)
        # Process all articles - don't pre-filter by company name (extract_layoff_info can find companies via patterns)
        articles_processed = 0
        articles_with_companies = 0
        articles_without_companies = []
        articles_filtered_invalid_ticker = 0  # Track articles filtered due to invalid tickers
        companies_found = {}
        extracted_layoffs = []  # Store all extracted layoff info
        
        total_articles = len(articles)
        print(f"[INFO] Processing {total_articles} articles for company/ticker extraction...")
        print(f"[INFO] Using batched Claude API calls (much faster than individual calls)...")
        
        # OPTIMIZATION: Batch Claude API calls with rate limiting
        # Reduced batch size to avoid rate limits (50k tokens/min limit)
        # Smaller batches = fewer tokens per request = less likely to hit rate limit
        BATCH_SIZE = 20  # Reduced from 40 to reduce tokens per request and avoid rate limits
        batch_results = {}
        
        # Process articles in batches with rate limiting
        for batch_start in range(0, total_articles, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_articles)
            batch_articles = articles[batch_start:batch_end]
            
            print(f"ℹ️ [PROGRESS] Processing batch {batch_start//BATCH_SIZE + 1}/{(total_articles + BATCH_SIZE - 1)//BATCH_SIZE} "
                  f"(articles {batch_start + 1}-{batch_end}/{total_articles})...")
            
            # Prepare articles for batch API call
            batch_input = []
            for i, article in enumerate(batch_articles):
                batch_input.append({
                    'index': batch_start + i,
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'url': article.get('url', '')
                })
            
            # Get batch results from Claude with retry logic
            max_retries = 3
            retry_delay = 2  # Start with 2 seconds
            batch_ai_results = None
            
            for attempt in range(max_retries):
                try:
                    batch_ai_results = self.get_ai_prediction_score_batch(batch_input)
                    if batch_ai_results is not None:
                        break  # Success
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "529" in error_str or "rate_limit" in error_str.lower() or "overload" in error_str.lower():
                        # Rate limit or service overload error - wait longer before retry
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                        error_type = "rate limit" if "429" in error_str else "service overload"
                        print(f"[{error_type.upper()}] Hit {error_type}, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                        time_module.sleep(wait_time)
                    else:
                        # Other error - break and continue
                        print(f"[BATCH ERROR] Error in batch API call: {e}")
                        break
            
            if batch_ai_results:
                batch_results.update(batch_ai_results)
            else:
                # Mark all articles in this batch as failed
                for i in range(batch_start, batch_end):
                    batch_results[i] = None
            
            # Rate limiting: Add delay between batches to avoid hitting 50k tokens/min limit
            # Estimate: ~500 tokens per article (title + description + prompt overhead)
            # 20 articles = ~10k tokens per batch
            # To stay under 50k/min, we need max 5 batches per minute = 12 seconds between batches
            if batch_start + BATCH_SIZE < total_articles:  # Don't delay after last batch
                time_module.sleep(2)  # 2 second delay between batches
        
        print(f"[INFO] Batch API calls complete. Extracting company info...")
        
        # Now process each article with the batch results
        extraction_start_time = time_module.time()
        for i, article in enumerate(articles):
            articles_processed += 1
            
            # Show progress every 25 articles
            if (i + 1) % 25 == 0 or (i + 1) == total_articles:
                elapsed = time_module.time() - extraction_start_time
                avg_time = elapsed / (i + 1) if (i + 1) > 0 else 0
                remaining = avg_time * (total_articles - (i + 1)) if (i + 1) > 0 else 0
                print(f"[PROGRESS] Extracting company info: {i + 1}/{total_articles} ({((i + 1)/total_articles*100):.1f}%) - "
                      f"Elapsed: {elapsed:.1f}s, Avg: {avg_time:.3f}s/article, Est. remaining: {remaining:.1f}s")
            
            # Get pre-fetched AI result from batch
            ai_result = batch_results.get(i)
            
            # Use extract_layoff_info but skip Claude call (we already have the result)
            # Skip metadata fetch during batch processing (too slow - 300 HTTP requests would take 2-10 minutes)
            # RSS feed date is accurate enough for our purposes
            layoff_info = self.extract_layoff_info(article, fetch_content=False, event_types=event_types, pre_fetched_ai_result=ai_result, fetch_metadata=False)
            if layoff_info:
                articles_with_companies += 1
                company = layoff_info.get('company_name')
                # Track all companies found (including "Unknown Company")
                if company:
                    companies_found[company] = companies_found.get(company, 0) + 1
                # Always add to extracted_layoffs (even if company is None or "Unknown Company")
                extracted_layoffs.append(layoff_info)
        
        print(f"[INFO] Extraction complete: {articles_with_companies} articles with companies found")
        print(f"[INFO] Companies found: {', '.join(sorted(companies_found.keys())) if companies_found else 'None'}")
        print(f"[INFO] Total articles with companies extracted: {len(extracted_layoffs)}")
        
        # REMOVED: 3-per-ticker limiting - show all articles regardless of ticker
        # All articles are kept, no limiting applied
        print(f"[INFO] Keeping all {len(extracted_layoffs)} articles (no per-ticker limit)")
        
        # Add all extracted layoffs to self.layoffs (no filtering)
        # Allow articles with or without company names/tickers (UI will show "Didn't find")
        for layoff_info in extracted_layoffs:
            # Include ALL articles, regardless of percentage, company name, or ticker
            # This ensures we don't lose valuable news articles
            self.layoffs.append(layoff_info)
        
        # Second pass: Fetch full content for articles missing percentage data
        # This is important because percentages are rarely in titles
        if fetch_full_content:
            articles_to_fetch = []
            for layoff in self.layoffs:
                if not layoff.get('layoff_percentage') or layoff.get('layoff_percentage', 0) == 0:
                    articles_to_fetch.append(layoff)
            
            if articles_to_fetch:
                print(f"[INFO] Fetching full content for {min(15, len(articles_to_fetch))} articles to extract layoff percentages...")
            
            # Limit to 15 articles to balance speed vs completeness
            fetched = 0
            for layoff in articles_to_fetch[:15]:
                if fetched >= 15:
                    break
                # Find the original article by matching title
                for article in articles:
                    if article.get('title', '').lower() == layoff.get('title', '').lower():
                        try:
                            # Fetch and re-extract with full content
                            updated_info = self.extract_layoff_info(article, fetch_content=True, event_types=event_types)
                            if updated_info:
                                # Update with new data if found
                                if updated_info.get('layoff_percentage') and updated_info['layoff_percentage'] > 0:
                                    layoff['layoff_percentage'] = updated_info['layoff_percentage']
                                if updated_info.get('layoff_employees'):
                                    layoff['layoff_employees'] = updated_info['layoff_employees']
                        except:
                            pass
                        fetched += 1
                        break
        
        # Third pass: Fetch stock price changes for all layoffs (from article publication time)
        # OPTIMIZATION: Batch API calls by ticker to reduce API calls
        print(f"[OPTIMIZATION] Batching API calls by ticker...", flush=True)
        sys.stderr.write(f"[OPTIMIZATION] Batching API calls by ticker...\n")
        sys.stderr.flush()
        
        # Group layoffs by ticker
        ticker_groups = {}
        for layoff in self.layoffs:
            ticker = layoff.get('stock_ticker')
            if not ticker:
                continue
            if ticker not in ticker_groups:
                ticker_groups[ticker] = []
            ticker_groups[ticker].append(layoff)
        
        print(f"[OPTIMIZATION] Found {len(ticker_groups)} unique tickers across {len(self.layoffs)} layoffs", flush=True)
        sys.stderr.write(f"[OPTIMIZATION] Found {len(ticker_groups)} unique tickers across {len(self.layoffs)} layoffs\n")
        sys.stderr.flush()
        
        # Estimate total API calls needed:
        # - 1 daily batch call per ticker (for stock changes)
        # - 1 intraday batch call per ticker (if trading dates exist)
        # - 1 price history call per ticker
        estimated_calls_per_ticker = 3  # Daily + intraday + price history
        self.total_api_calls_estimated = len(ticker_groups) * estimated_calls_per_ticker
        print(f"[INFO] Estimated {self.total_api_calls_estimated} API calls needed for {len(ticker_groups)} unique tickers", flush=True)
        sys.stderr.write(f"[INFO] Estimated {self.total_api_calls_estimated} API calls needed for {len(ticker_groups)} unique tickers\n")
        sys.stderr.flush()
        
        # Pre-fetch batch data for each unique ticker
        for ticker, layoff_list in ticker_groups.items():
            # Calculate combined date range for all layoffs with this ticker
            # Include: (1) stock changes range (5 days before to 3 days after) and (2) price history (to now)
            min_start = None
            max_end = None
            earliest_announcement = None
            
            for layoff in layoff_list:
                announcement_dt = layoff.get('datetime')
                if not announcement_dt:
                    continue
                
                # Ensure announcement_dt is timezone-aware (UTC) for safe comparisons
                if announcement_dt.tzinfo is None:
                    announcement_dt = announcement_dt.replace(tzinfo=timezone.utc)
                else:
                    announcement_dt = announcement_dt.astimezone(timezone.utc)
                
                # Track earliest announcement for price history
                if earliest_announcement is None or announcement_dt < earliest_announcement:
                    earliest_announcement = announcement_dt
                
                # Stock changes range: 5 days before to 3 days after
                start_date = announcement_dt - timedelta(days=5)
                end_date = announcement_dt + timedelta(days=3)
                
                # Ensure timezone-aware for comparisons
                if min_start is None:
                    min_start = start_date
                elif start_date < min_start:
                    min_start = start_date
                    
                if max_end is None:
                    max_end = end_date
                elif end_date > max_end:
                    max_end = end_date
            
            # Extend max_end to "now" for price history (from earliest announcement to now)
            if earliest_announcement:
                # Make sure now is timezone-aware (UTC) to match layoff datetimes
                now = datetime.now(timezone.utc)
                # Ensure max_end is also timezone-aware for comparison
                if max_end is None:
                    max_end = now
                else:
                    # Ensure max_end is timezone-aware
                    if max_end.tzinfo is None:
                        max_end = max_end.replace(tzinfo=timezone.utc)
                    # Extend to now if now is later
                    if now > max_end:
                        max_end = now
            
            if min_start and max_end:
                # Make ONE API call for this ticker with combined date range (covers both stock changes AND price history)
                print(f"[OPTIMIZATION] Pre-fetching batch data for {ticker} from {min_start.date()} to {max_end.date()} ({len(layoff_list)} layoffs)", flush=True)
                sys.stderr.write(f"[OPTIMIZATION] Pre-fetching batch data for {ticker} from {min_start.date()} to {max_end.date()} ({len(layoff_list)} layoffs)\n")
                sys.stderr.flush()
                batch_data = self._fetch_price_data_batch(ticker, min_start, max_end, '1d')
                if batch_data:
                    self.batch_data_cache[ticker] = batch_data
                
                # Pre-fetch intraday data for all unique dates for this ticker
                # OPTIMIZATION: Batch fetch all dates in one API call instead of one per date
                unique_dates = set()
                for layoff in layoff_list:
                    announcement_dt = layoff.get('datetime')
                    if announcement_dt:
                        # Add announcement day
                        unique_dates.add(announcement_dt.replace(hour=0, minute=0, second=0, microsecond=0))
                        # Add next trading day (if market was closed)
                        next_trading_day = self.get_next_trading_day(announcement_dt, ticker, batch_data)
                        if next_trading_day:
                            unique_dates.add(next_trading_day.replace(hour=0, minute=0, second=0, microsecond=0))
                
                # Filter to only trading days (weekdays, not future, market open)
                trading_dates = []
                for date_dt in unique_dates:
                    if self.is_market_open(date_dt) or (date_dt.weekday() < 5 and not self.is_future_date(date_dt)):
                        trading_dates.append(date_dt)
                
                # Batch fetch all dates in ONE API call per ticker
                if trading_dates:
                    # Find min and max dates
                    min_date = min(trading_dates)
                    max_date = max(trading_dates)
                    
                    # Ensure dates are timezone-aware for comparison
                    if min_date.tzinfo is None:
                        min_date = min_date.replace(tzinfo=timezone.utc)
                    if max_date.tzinfo is None:
                        max_date = max_date.replace(tzinfo=timezone.utc)
                    
                    print(f"[OPTIMIZATION] Batching {len(trading_dates)} unique dates for {ticker} into 1 API call ({min_date.date()} to {max_date.date()})", flush=True)
                    sys.stderr.write(f"[OPTIMIZATION] Batching {len(trading_dates)} unique dates for {ticker} into 1 API call ({min_date.date()} to {max_date.date()})\n")
                    sys.stderr.flush()
                    
                    # Make ONE API call for all dates
                    self._fetch_intraday_data_batch(ticker, min_date, max_date, interval='5min')
        
        # OPTIMIZATION: Pre-calculate price history for each unique ticker once
        # This avoids calling get_stock_price_history 98 times (once per layoff)
        print(f"[OPTIMIZATION] Pre-calculating price history for {len(ticker_groups)} unique tickers...", flush=True)
        sys.stderr.write(f"[OPTIMIZATION] Pre-calculating price history for {len(ticker_groups)} unique tickers...\n")
        sys.stderr.flush()
        
        for ticker, layoff_list in ticker_groups.items():
            # Find earliest announcement date for this ticker
            earliest_date = None
            for layoff in layoff_list:
                announcement_dt = layoff.get('datetime')
                if announcement_dt:
                    if earliest_date is None or announcement_dt < earliest_date:
                        earliest_date = announcement_dt
            
            if earliest_date:
                # Calculate price history once per ticker (from 60 days before earliest to now)
                cache_key = f"price_history_{ticker}"
                if cache_key not in self.price_history_cache:
                    history_start = earliest_date - timedelta(days=60)
                    price_history = self.get_stock_price_history(ticker, history_start)
                    self.price_history_cache[cache_key] = price_history
                    print(f"[OPTIMIZATION] Pre-calculated price history for {ticker} ({len(price_history)} data points)", flush=True)
                    sys.stderr.write(f"[OPTIMIZATION] Pre-calculated price history for {ticker} ({len(price_history)} data points)\n")
                    sys.stderr.flush()
        
        # Now process each layoff (will use cached batch data, intraday data, and price history)
        for layoff in self.layoffs:
            try:
                # Only calculate stock changes if ticker exists (publicly traded company)
                ticker = layoff.get('stock_ticker')
                if ticker and ticker != 'N/A':
                    # Calculate stock changes from article publication time
                    stock_changes = self.calculate_stock_changes(layoff)
                    layoff.update(stock_changes)
                # If no ticker (private company), skip stock price calculation
            except Exception as e:
                error_msg = f"Error calculating stock changes for {layoff.get('company_name')}: {e}"
                self.api_errors.append({
                    'service': 'stock_changes',
                    'type': 'calculation_error',
                    'message': error_msg
                })
    
    def sort_layoffs(self):
        """Sort layoffs by date/time (most recent first)"""
        # Sort by datetime (most recent first)
        self.layoffs.sort(
            key=lambda x: x['datetime'] if x['datetime'] else datetime.min,
            reverse=True
        )
    
    def print_results(self):
        """Print formatted results"""
        if not self.layoffs:
            print(f"\nNo layoff announcements found in the last {LOOKBACK_DAYS} days.")
            return
        
        print("\n" + "="*100)
        print(f"LAYOFF ANNOUNCEMENTS - LAST {LOOKBACK_DAYS} DAYS")
        print("="*100)
        print(f"{'Company Name':<25} {'Stock Ticker':<15} {'Layoff %':<12} {'Date':<12} {'Time':<10}")
        print("-"*100)
        
        for layoff in self.layoffs:
            company = layoff['company_name'][:24]
            ticker = layoff['stock_ticker']
            pct = f"{layoff['layoff_percentage']:.2f}%" if layoff['layoff_percentage'] and layoff['layoff_percentage'] > 0 else "N/A"
            date = layoff['date']
            time = layoff['time']
            
            print(f"{company:<25} {ticker:<15} {pct:<12} {date:<12} {time:<10}")
        
        print("="*100)
        print(f"\nTotal announcements: {len(self.layoffs)}")


def main():
    tracker = LayoffTracker()
    tracker.fetch_layoffs()
    tracker.sort_layoffs()
    tracker.print_results()


if __name__ == '__main__':
    main()

