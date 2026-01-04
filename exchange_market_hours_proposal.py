#!/usr/bin/env python3
"""
Proposal: Exchange Detection and Market Hours System

This file demonstrates how to address the root cause of foreign stock trading hours.
"""

from datetime import datetime, time, timezone, timedelta
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo  # Python 3.9+

# Exchange to Market Hours Mapping
EXCHANGE_MARKET_HOURS = {
    # US Exchanges (NYSE, NASDAQ)
    'US': {
        'open': time(9, 30),  # 9:30 AM
        'close': time(16, 0),  # 4:00 PM
        'timezone': 'America/New_York',  # ET (EST/EDT)
        'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
    },
    # Hong Kong Stock Exchange
    'HK': {
        'open': time(9, 30),  # 9:30 AM
        'close': time(16, 0),  # 4:00 PM
        'timezone': 'Asia/Hong_Kong',  # HKT (UTC+8)
        'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
    },
    # London Stock Exchange
    'L': {
        'open': time(8, 0),  # 8:00 AM
        'close': time(16, 30),  # 4:30 PM
        'timezone': 'Europe/London',  # GMT/BST
        'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
    },
    # Tokyo Stock Exchange
    'T': {
        'open': time(9, 0),  # 9:00 AM
        'close': time(15, 0),  # 3:00 PM
        'timezone': 'Asia/Tokyo',  # JST (UTC+9)
        'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
    },
    # Paris Stock Exchange (Euronext Paris)
    'PA': {
        'open': time(9, 0),  # 9:00 AM
        'close': time(17, 30),  # 5:30 PM
        'timezone': 'Europe/Paris',  # CET/CEST
        'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
    },
    # Frankfurt Stock Exchange
    'DE': {
        'open': time(9, 0),  # 9:00 AM
        'close': time(17, 30),  # 5:30 PM
        'timezone': 'Europe/Berlin',  # CET/CEST
        'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
    },
    # Toronto Stock Exchange
    'TO': {
        'open': time(9, 30),  # 9:30 AM
        'close': time(16, 0),  # 4:00 PM
        'timezone': 'America/Toronto',  # EST/EDT
        'trading_days': [0, 1, 2, 3, 4],  # Monday-Friday
    },
    # Australian Stock Exchange
    'AX': {
        'open': time(10, 0),  # 10:00 AM
        'close': time(16, 0),  # 4:00 PM
        'timezone': 'Australia/Sydney',  # AEST/AEDT
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
    '.TO': 'TO',  # Toronto
    '.AX': 'AX',  # Australia
    # US stocks typically have no suffix or are on NYSE/NASDAQ
    # Default to US if no suffix found
}

def detect_exchange_from_ticker(ticker: str) -> str:
    """
    Detect the exchange from a ticker symbol.
    
    Examples:
        'AAPL' -> 'US'
        '1211.HK' -> 'HK'
        'TSLA' -> 'US'
        'AIR.PA' -> 'PA'
    """
    if not ticker:
        return 'US'  # Default to US
    
    ticker_upper = ticker.upper()
    
    # Check for exchange suffix
    for suffix, exchange in TICKER_EXCHANGE_MAP.items():
        if ticker_upper.endswith(suffix):
            return exchange
    
    # Default to US exchange (NYSE/NASDAQ)
    return 'US'

def get_market_hours(exchange: str) -> Optional[Dict]:
    """Get market hours configuration for an exchange."""
    return EXCHANGE_MARKET_HOURS.get(exchange)

def is_market_open_for_exchange(dt: datetime, ticker: str) -> bool:
    """
    Check if market is open for a specific ticker at given datetime.
    Uses exchange-specific market hours.
    """
    exchange = detect_exchange_from_ticker(ticker)
    market_config = get_market_hours(exchange)
    
    if not market_config:
        # Fallback to US market hours
        market_config = EXCHANGE_MARKET_HOURS['US']
    
    # Convert datetime to exchange timezone
    exchange_tz = ZoneInfo(market_config['timezone'])
    
    if dt.tzinfo is None:
        dt_utc = dt.replace(tzinfo=timezone.utc)
    else:
        dt_utc = dt.astimezone(timezone.utc)
    
    # Convert to exchange local time
    dt_local = dt_utc.astimezone(exchange_tz)
    
    # Check if it's a trading day
    weekday = dt_local.weekday()  # 0=Monday, 6=Sunday
    if weekday not in market_config['trading_days']:
        return False
    
    # Check if within market hours
    local_time = dt_local.time()
    market_open = market_config['open']
    market_close = market_config['close']
    
    return market_open <= local_time <= market_close

def get_market_open_time(date: datetime, ticker: str) -> Optional[datetime]:
    """
    Get the market open time for a specific date and ticker.
    Returns datetime in UTC.
    """
    exchange = detect_exchange_from_ticker(ticker)
    market_config = get_market_hours(exchange)
    
    if not market_config:
        market_config = EXCHANGE_MARKET_HOURS['US']
    
    exchange_tz = ZoneInfo(market_config['timezone'])
    
    # Get date in exchange timezone
    if date.tzinfo is None:
        date_local = date.replace(tzinfo=exchange_tz)
    else:
        date_local = date.astimezone(exchange_tz)
    
    # Combine date with market open time
    market_open_dt = datetime.combine(
        date_local.date(),
        market_config['open'],
        exchange_tz
    )
    
    # Convert to UTC
    return market_open_dt.astimezone(timezone.utc)

def get_market_close_time(date: datetime, ticker: str) -> Optional[datetime]:
    """
    Get the market close time for a specific date and ticker.
    Returns datetime in UTC.
    """
    exchange = detect_exchange_from_ticker(ticker)
    market_config = get_market_hours(exchange)
    
    if not market_config:
        market_config = EXCHANGE_MARKET_HOURS['US']
    
    exchange_tz = ZoneInfo(market_config['timezone'])
    
    # Get date in exchange timezone
    if date.tzinfo is None:
        date_local = date.replace(tzinfo=exchange_tz)
    else:
        date_local = date.astimezone(exchange_tz)
    
    # Combine date with market close time
    market_close_dt = datetime.combine(
        date_local.date(),
        market_config['close'],
        exchange_tz
    )
    
    # Convert to UTC
    return market_close_dt.astimezone(timezone.utc)

# Example usage
if __name__ == '__main__':
    print("Exchange Detection Examples:")
    print(f"AAPL -> {detect_exchange_from_ticker('AAPL')}")
    print(f"1211.HK -> {detect_exchange_from_ticker('1211.HK')}")
    print(f"AIR.PA -> {detect_exchange_from_ticker('AIR.PA')}")
    print(f"TSLA -> {detect_exchange_from_ticker('TSLA')}")
    
    print("\nMarket Hours Test:")
    test_dt = datetime(2025, 12, 1, 14, 30, tzinfo=timezone.utc)  # 2:30 PM UTC
    print(f"Test datetime: {test_dt}")
    print(f"US market open (AAPL): {is_market_open_for_exchange(test_dt, 'AAPL')}")
    print(f"HK market open (1211.HK): {is_market_open_for_exchange(test_dt, '1211.HK')}")
    
    # Test market open times
    test_date = datetime(2025, 12, 1, 0, 0, tzinfo=timezone.utc)
    us_open = get_market_open_time(test_date, 'AAPL')
    hk_open = get_market_open_time(test_date, '1211.HK')
    print(f"\nMarket Open Times (Dec 1, 2025):")
    print(f"US (AAPL): {us_open}")
    print(f"HK (1211.HK): {hk_open}")

