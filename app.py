#!/usr/bin/env python3
"""
Flask Web Application for Layoff Tracker
"""

from flask import Flask, render_template, jsonify, Response, stream_with_context, request
from main import LayoffTracker
from datetime import datetime, timezone, timedelta
import sys
import io
import json
import time
from contextlib import redirect_stdout, redirect_stderr
from threading import Lock, Thread
import queue

app = Flask(__name__)

# In-memory cache for AI opinions
# Key: (ticker, bearish_date, target_date) -> {score, explanation, timestamp}
_ai_opinion_cache = {}
_cache_lock = Lock()
CACHE_EXPIRY_SECONDS = 3600  # 1 hour

def get_cached_ai_opinion(ticker, bearish_date, target_date):
    """Get cached AI opinion if available and not expired"""
    cache_key = (ticker, bearish_date, target_date)
    with _cache_lock:
        if cache_key in _ai_opinion_cache:
            cached = _ai_opinion_cache[cache_key]
            # Check if cache is still valid (not expired)
            if time.time() - cached['timestamp'] < CACHE_EXPIRY_SECONDS:
                return cached
            else:
                # Remove expired cache entry
                del _ai_opinion_cache[cache_key]
    return None

def cache_ai_opinion(ticker, bearish_date, target_date, score, explanation):
    """Cache AI opinion result"""
    cache_key = (ticker, bearish_date, target_date)
    with _cache_lock:
        _ai_opinion_cache[cache_key] = {
            'score': score,
            'explanation': explanation,
            'timestamp': time.time()
        }

class LogCapture:
    """Capture stdout/stderr for logging with real-time streaming"""
    def __init__(self, stream_callback=None, file_handle=None):
        self.logs = []
        self.stream_callback = stream_callback
        self.file_handle = file_handle  # Optional file handle to also write to
        self.lock = Lock()
    
    def write(self, message):
        if message and message.strip():  # Only log non-empty messages
            with self.lock:
                # Keep original message (with newlines) for file
                self.logs.append(message.strip())
                # Also write to file if provided (write original message to preserve formatting)
                if self.file_handle:
                    try:
                        self.file_handle.write(message)
                        self.file_handle.flush()
                    except Exception as e:
                        # If file write fails, try to write to original stderr
                        try:
                            import sys
                            sys.__stderr__.write(f"[LogCapture file write error: {e}]\n")
                            sys.__stderr__.write(message)
                        except:
                            pass
            # Stream in real-time if callback is provided
            if self.stream_callback:
                try:
                    self.stream_callback(message.strip())
                except:
                    pass
    
    def flush(self):
        if self.file_handle:
            try:
                self.file_handle.flush()
            except:
                pass
    
    def get_logs(self):
        with self.lock:
            return self.logs.copy()
    
    def clear(self):
        with self.lock:
            self.logs = []

@app.route('/')
def index():
    """Main page with layoff data table"""
    return render_template('index.html')

@app.route('/api/layoffs')
def get_layoffs():
    """API endpoint to get layoff data"""
    import time
    start_time = time.time()
    
    # Capture logs
    log_capture = LogCapture()
    
    # Redirect stdout to capture logs
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = log_capture
    sys.stderr = log_capture
    
    try:
        # Get event types from query parameters
        event_types = request.args.getlist('event_types')
        if not event_types:
            event_types = ['real_estate_good_news']  # Default
        
        selected_sources = request.args.getlist('sources')
        if not selected_sources:
            selected_sources = ['google_news', 'benzinga_news']  # Default
        
        tracker = LayoffTracker()
        # Fetch full content for articles missing percentage data (enabled for better data)
        # This will fetch content for up to 15 articles, which should take ~30-45 seconds
        tracker.fetch_layoffs(fetch_full_content=True, event_types=event_types, selected_sources=selected_sources)
        tracker.sort_layoffs()
        
        elapsed = time.time() - start_time
        print(f"Data fetched in {elapsed:.2f} seconds")
        
        # Get captured logs
        logs = log_capture.get_logs()
        
        # Format data for frontend
        layoffs_data = []
        for layoff in tracker.layoffs:
            layoffs_data.append({
            'company_name': layoff.get('company_name') or None,  # None will be displayed as "Didn't find"
            'stock_ticker': layoff.get('stock_ticker') or None,  # None will be displayed as "Didn't find"
            'date': layoff['date'],
            'time': layoff['time'],
            'datetime': layoff['datetime'].isoformat() if layoff.get('datetime') else None,
            'market_was_open': layoff.get('market_was_open'),  # Market status when article was published
            'layoff_percentage': layoff.get('layoff_percentage') if layoff.get('layoff_percentage') and layoff.get('layoff_percentage', 0) > 0 else None,
            'layoff_employees': layoff.get('layoff_employees'),
            'url': layoff.get('url', ''),
            'title': layoff.get('title', ''),
            # Stock price changes (from article publication time)
            'change_1min': layoff.get('change_1min'),
            'change_2min': layoff.get('change_2min'),
            'change_3min': layoff.get('change_3min'),
            'change_4min': layoff.get('change_4min'),
            'change_5min': layoff.get('change_5min'),
            'change_10min': layoff.get('change_10min'),
            'change_30min': layoff.get('change_30min'),
            'change_1hr': layoff.get('change_1hr'),
            'change_1.5hr': layoff.get('change_1.5hr'),
            'change_2hr': layoff.get('change_2hr'),
            'change_2.5hr': layoff.get('change_2.5hr'),
            'change_3hr': layoff.get('change_3hr'),
            # Volume changes for each interval
            'volume_change_1min': layoff.get('volume_change_1min'),
            'volume_change_2min': layoff.get('volume_change_2min'),
            'volume_change_3min': layoff.get('volume_change_3min'),
            'volume_change_4min': layoff.get('volume_change_4min'),
            'volume_change_5min': layoff.get('volume_change_5min'),
            'volume_change_10min': layoff.get('volume_change_10min'),
            'volume_change_30min': layoff.get('volume_change_30min'),
            'volume_change_1hr': layoff.get('volume_change_1hr'),
            'volume_change_1.5hr': layoff.get('volume_change_1.5hr'),
            'volume_change_2hr': layoff.get('volume_change_2hr'),
            'volume_change_2.5hr': layoff.get('volume_change_2.5hr'),
            'volume_change_3hr': layoff.get('volume_change_3hr'),
            'change_1day': layoff.get('change_1day'),
            'change_2day': layoff.get('change_2day'),
            'change_3day': layoff.get('change_3day'),
            'change_next_close': layoff.get('change_next_close'),
            # Price snapshots for each interval
            'price_1min': layoff.get('price_1min'),
            'price_2min': layoff.get('price_2min'),
            'price_3min': layoff.get('price_3min'),
            'price_4min': layoff.get('price_4min'),
            'price_5min': layoff.get('price_5min'),
            'price_10min': layoff.get('price_10min'),
            'price_30min': layoff.get('price_30min'),
            'price_1hr': layoff.get('price_1hr'),
            'price_1.5hr': layoff.get('price_1.5hr'),
            'price_2hr': layoff.get('price_2hr'),
            'price_2.5hr': layoff.get('price_2.5hr'),
            'price_3hr': layoff.get('price_3hr'),
            'price_1day': layoff.get('price_1day'),
            'price_2day': layoff.get('price_2day'),
            'price_3day': layoff.get('price_3day'),
            'price_next_close': layoff.get('price_next_close'),
            # Dates for each interval (for displaying day names)
            'date_1min': layoff.get('date_1min'),
            'date_2min': layoff.get('date_2min'),
            'date_3min': layoff.get('date_3min'),
            'date_4min': layoff.get('date_4min'),
            'date_5min': layoff.get('date_5min'),
            'date_10min': layoff.get('date_10min'),
            'date_30min': layoff.get('date_30min'),
            'date_1hr': layoff.get('date_1hr'),
            'date_1.5hr': layoff.get('date_1.5hr'),
            'date_2hr': layoff.get('date_2hr'),
            'date_2.5hr': layoff.get('date_2.5hr'),
            'date_3hr': layoff.get('date_3hr'),
            'date_1day': layoff.get('date_1day'),
            'date_2day': layoff.get('date_2day'),
            'date_3day': layoff.get('date_3day'),
            'date_next_close': layoff.get('date_next_close'),
            # Datetimes for each interval (for displaying full date and time)
            'datetime_1min': layoff.get('datetime_1min'),
            'datetime_2min': layoff.get('datetime_2min'),
            'datetime_3min': layoff.get('datetime_3min'),
            'datetime_4min': layoff.get('datetime_4min'),
            'datetime_5min': layoff.get('datetime_5min'),
            'datetime_10min': layoff.get('datetime_10min'),
            'datetime_30min': layoff.get('datetime_30min'),
            'datetime_1hr': layoff.get('datetime_1hr'),
            'datetime_1.5hr': layoff.get('datetime_1.5hr'),
            'datetime_2hr': layoff.get('datetime_2hr'),
            'datetime_2.5hr': layoff.get('datetime_2.5hr'),
            'datetime_3hr': layoff.get('datetime_3hr'),
            'datetime_1day': layoff.get('datetime_1day'),
            'datetime_2day': layoff.get('datetime_2day'),
            'datetime_3day': layoff.get('datetime_3day'),
            'datetime_next_close': layoff.get('datetime_next_close'),
            # Approximate time flags
            'is_approximate_1min': layoff.get('is_approximate_1min', False),
            'is_approximate_2min': layoff.get('is_approximate_2min', False),
            'is_approximate_3min': layoff.get('is_approximate_3min', False),
            'is_approximate_4min': layoff.get('is_approximate_4min', False),
            'is_approximate_5min': layoff.get('is_approximate_5min', False),
            'is_approximate_10min': layoff.get('is_approximate_10min', False),
            'is_approximate_30min': layoff.get('is_approximate_30min', False),
            'is_approximate_1hr': layoff.get('is_approximate_1hr', False),
            'is_approximate_1.5hr': layoff.get('is_approximate_1.5hr', False),
            'is_approximate_2hr': layoff.get('is_approximate_2hr', False),
            'is_approximate_2.5hr': layoff.get('is_approximate_2.5hr', False),
            'is_approximate_3hr': layoff.get('is_approximate_3hr', False),
            'is_approximate_1day': layoff.get('is_approximate_1day', False),
            'is_approximate_2day': layoff.get('is_approximate_2day', False),
            'is_approximate_3day': layoff.get('is_approximate_3day', False),
            'is_approximate_next_close': layoff.get('is_approximate_next_close', False),
            # Actual datetimes (when approximate)
            'actual_datetime_1min': layoff.get('actual_datetime_1min'),
            'actual_datetime_2min': layoff.get('actual_datetime_2min'),
            'actual_datetime_3min': layoff.get('actual_datetime_3min'),
            'actual_datetime_4min': layoff.get('actual_datetime_4min'),
            'actual_datetime_5min': layoff.get('actual_datetime_5min'),
            'actual_datetime_10min': layoff.get('actual_datetime_10min'),
            'actual_datetime_30min': layoff.get('actual_datetime_30min'),
            'actual_datetime_1hr': layoff.get('actual_datetime_1hr'),
            'actual_datetime_1.5hr': layoff.get('actual_datetime_1.5hr'),
            'actual_datetime_2hr': layoff.get('actual_datetime_2hr'),
            'actual_datetime_2.5hr': layoff.get('actual_datetime_2.5hr'),
            'actual_datetime_3hr': layoff.get('actual_datetime_3hr'),
            'actual_datetime_1day': layoff.get('actual_datetime_1day'),
            'actual_datetime_2day': layoff.get('actual_datetime_2day'),
            'actual_datetime_3day': layoff.get('actual_datetime_3day'),
            'actual_datetime_next_close': layoff.get('actual_datetime_next_close'),
            # Market closed flags
            'market_closed_1min': layoff.get('market_closed_1min'),
            'market_closed_2min': layoff.get('market_closed_2min'),
            'market_closed_3min': layoff.get('market_closed_3min'),
            'market_closed_4min': layoff.get('market_closed_4min'),
            'market_closed_5min': layoff.get('market_closed_5min'),
            'market_closed_10min': layoff.get('market_closed_10min'),
            'market_closed_30min': layoff.get('market_closed_30min'),
            'market_closed_1hr': layoff.get('market_closed_1hr'),
            'market_closed_1.5hr': layoff.get('market_closed_1.5hr'),
            'market_closed_2hr': layoff.get('market_closed_2hr'),
            'market_closed_2.5hr': layoff.get('market_closed_2.5hr'),
            'market_closed_3hr': layoff.get('market_closed_3hr'),
            'market_closed_1day': layoff.get('market_closed_1day'),
            'market_closed_2day': layoff.get('market_closed_2day'),
            # Daily close flags (for intraday intervals using daily data)
            'is_daily_close_1min': layoff.get('is_daily_close_1min'),
            'is_daily_close_2min': layoff.get('is_daily_close_2min'),
            'is_daily_close_3min': layoff.get('is_daily_close_3min'),
            'is_daily_close_4min': layoff.get('is_daily_close_4min'),
            'is_daily_close_5min': layoff.get('is_daily_close_5min'),
            'is_daily_close_10min': layoff.get('is_daily_close_10min'),
            'is_daily_close_30min': layoff.get('is_daily_close_30min'),
            'is_daily_close_1hr': layoff.get('is_daily_close_1hr'),
            'is_daily_close_1.5hr': layoff.get('is_daily_close_1.5hr'),
            'is_daily_close_2hr': layoff.get('is_daily_close_2hr'),
            'is_daily_close_2.5hr': layoff.get('is_daily_close_2.5hr'),
            'is_daily_close_3hr': layoff.get('is_daily_close_3hr'),
            'is_daily_close_next_close': layoff.get('is_daily_close_next_close'),
            # Intraday flags (indicates open-to-close movement)
            'is_intraday_1min': layoff.get('is_intraday_1min'),
            'is_intraday_2min': layoff.get('is_intraday_2min'),
            'is_intraday_3min': layoff.get('is_intraday_3min'),
            'is_intraday_4min': layoff.get('is_intraday_4min'),
            'is_intraday_5min': layoff.get('is_intraday_5min'),
            'is_intraday_10min': layoff.get('is_intraday_10min'),
            'is_intraday_30min': layoff.get('is_intraday_30min'),
            'is_intraday_1hr': layoff.get('is_intraday_1hr'),
            'is_intraday_1.5hr': layoff.get('is_intraday_1.5hr'),
            'is_intraday_2hr': layoff.get('is_intraday_2hr'),
            'is_intraday_2.5hr': layoff.get('is_intraday_2.5hr'),
            'is_intraday_3hr': layoff.get('is_intraday_3hr'),
            # New insight fields
            'layoff_reason': layoff.get('layoff_reason'),
            'expected_savings': layoff.get('expected_savings'),
            'financial_context': layoff.get('financial_context'),
            'affected_departments': layoff.get('affected_departments'),
            'guidance_change': layoff.get('guidance_change'),
            'ai_prediction_score': layoff.get('ai_prediction_score'),
            'ai_prediction_direction': layoff.get('ai_prediction_direction'),
        })
        
        return jsonify({
            'layoffs': layoffs_data,
            'total': len(layoffs_data),
            'last_updated': datetime.now().isoformat(),
            'note': 'Intraday intervals (10min, 1hr, 3hr) use daily close prices. Real intraday data requires paid API access.',
            'logs': logs,
            'api_errors': tracker.api_errors,  # Include API errors for frontend alerts
            'source_stats': getattr(tracker, 'source_stats', {})  # Include source statistics
        })
    finally:
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

@app.route('/api/layoffs/stream')
def get_layoffs_stream():
    """Streaming endpoint for real-time logs using Server-Sent Events"""
    def generate():
        import time
        start_time = time.time()
        
        # Store logs for final response
        all_logs = []
        log_queue = queue.Queue()
        fetch_complete = False
        
        def log_callback(message):
            log_queue.put(message)
        
        # PERFORMANCE: Disable file logging during streaming (30-50% faster)
        # File I/O is slow - we only stream to UI, not to file during active fetch
        log_file = None  # Disabled for performance
        
        # Capture logs with callback only (no file handle)
        log_capture = LogCapture(stream_callback=log_callback, file_handle=log_file)
        
        # Redirect stdout to capture logs
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log_capture
        sys.stderr = log_capture
        
        # Get event types and sources from query parameters (before threading)
        # IMPORTANT: Capture all request parameters here, before background thread starts
        event_types = request.args.getlist('event_types')
        if not event_types:
            event_types = ['bio_companies']  # Default
        
        selected_sources = request.args.getlist('sources')
        if not selected_sources:
            selected_sources = ['google_news', 'benzinga_news']  # Default
        
        # Capture fetch_full_content parameter before threading (request context not available in thread)
        fetch_full = request.args.get('fetch_full_content', 'false').lower() == 'true'
        
        def fetch_data():
            nonlocal fetch_complete
            try:
                tracker = LayoffTracker()
                # Use captured fetch_full value (not request.args, which isn't available in thread)
                tracker.fetch_layoffs(fetch_full_content=fetch_full, event_types=event_types, selected_sources=selected_sources)
                fetch_complete = True
                return tracker
            except Exception as e:
                log_queue.put(f"Error during fetch: {e}")
                fetch_complete = True
                return None
        
        try:
            # Send initial message
            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting data fetch...'}, separators=(',', ':'))}\n\n"
            
            yield f"data: {json.dumps({'type': 'info', 'message': 'Fetching articles from all sources...'}, separators=(',', ':'))}\n\n"
            
            # Start fetch in background thread
            tracker_ref = [None]
            fetch_thread = Thread(target=lambda: tracker_ref.__setitem__(0, fetch_data()))
            fetch_thread.daemon = True
            fetch_thread.start()
            
            # Stream logs in real-time while fetch is running
            while not fetch_complete or not log_queue.empty():
                try:
                    # Check for new logs (with short timeout to avoid blocking)
                    try:
                        log_msg = log_queue.get(timeout=0.1)
                        all_logs.append(log_msg)
                        yield f"data: {json.dumps({'type': 'log', 'message': log_msg}, separators=(',', ':'))}\n\n"
                    except queue.Empty:
                        # No logs available, check if fetch is complete
                        if fetch_complete:
                            break
                        # Small sleep to avoid busy waiting
                        time.sleep(0.05)
                except:
                    if fetch_complete:
                        break
            
            # Wait for fetch thread to complete (increased timeout for large datasets)
            fetch_thread.join(timeout=300)  # 5 minutes should be enough
            tracker = tracker_ref[0]
            
            if tracker is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to fetch data'}, separators=(',', ':'))}\n\n"
                return
            
            # Stream any remaining logs
            while not log_queue.empty():
                try:
                    log_msg = log_queue.get_nowait()
                    all_logs.append(log_msg)
                    yield f"data: {json.dumps({'type': 'log', 'message': log_msg}, separators=(',', ':'))}\n\n"
                except queue.Empty:
                    break
            
            # Stock changes are already calculated in fetch_layoffs() - no need to recalculate!
            # This was causing duplicate work and slowing down the UI significantly.
            yield f"data: {json.dumps({'type': 'info', 'message': 'Stock price changes already calculated during fetch...'}, separators=(',', ':'))}\n\n"
            
            # Stream any remaining logs from stock calculation
            while not log_queue.empty():
                try:
                    log_msg = log_queue.get_nowait()
                    all_logs.append(log_msg)
                    yield f"data: {json.dumps({'type': 'log', 'message': log_msg}, separators=(',', ':'))}\n\n"
                except queue.Empty:
                    break
            
            tracker.sort_layoffs()
            
            elapsed = time.time() - start_time
            yield f"data: {json.dumps({'type': 'info', 'message': f'Data fetched in {elapsed:.2f} seconds'}, separators=(',', ':'))}\n\n"
            
            # Format final data
            yield f"data: {json.dumps({'type': 'info', 'message': f'Formatting data for {len(tracker.layoffs)} layoffs...'}, separators=(',', ':'))}\n\n"
            layoffs_data = []
            total_layoffs = len(tracker.layoffs)
            for idx, layoff in enumerate(tracker.layoffs):
                # Progress updates every 10 items (UX improvement)
                if idx > 0 and idx % 10 == 0:
                    progress_pct = int((idx / total_layoffs) * 100)
                    yield f"data: {json.dumps({'type': 'info', 'message': f'Formatting progress: {idx}/{total_layoffs} ({progress_pct}%)...'}, separators=(',', ':'))}\n\n"
                layoffs_data.append({
                    'company_name': layoff.get('company_name') or None,  # None will be displayed as "Didn't find"
                    'stock_ticker': layoff.get('stock_ticker') or None,  # None will be displayed as "Didn't find"
                    'date': layoff['date'],
                    'time': layoff['time'],
                    'datetime': layoff['datetime'].isoformat() if layoff.get('datetime') else None,
                    'market_was_open': layoff.get('market_was_open'),  # Market status when article was published
                    'layoff_percentage': layoff.get('layoff_percentage') if layoff.get('layoff_percentage') and layoff.get('layoff_percentage', 0) > 0 else None,
                    'layoff_employees': layoff.get('layoff_employees'),
                    'url': layoff.get('url', ''),
                    'title': layoff.get('title', ''),
                    # Stock price changes (from article publication time)
                    'change_1min': layoff.get('change_1min'),
                    'change_2min': layoff.get('change_2min'),
                    'change_3min': layoff.get('change_3min'),
                    'change_4min': layoff.get('change_4min'),
                    'change_5min': layoff.get('change_5min'),
                    'change_10min': layoff.get('change_10min'),
                    'change_30min': layoff.get('change_30min'),
                    'change_1hr': layoff.get('change_1hr'),
                    'change_1.5hr': layoff.get('change_1.5hr'),
                    'change_2hr': layoff.get('change_2hr'),
                    'change_2.5hr': layoff.get('change_2.5hr'),
                    'change_3hr': layoff.get('change_3hr'),
                    # Volume changes for each interval
                    'volume_change_1min': layoff.get('volume_change_1min'),
                    'volume_change_2min': layoff.get('volume_change_2min'),
                    'volume_change_3min': layoff.get('volume_change_3min'),
                    'volume_change_4min': layoff.get('volume_change_4min'),
                    'volume_change_5min': layoff.get('volume_change_5min'),
                    'volume_change_10min': layoff.get('volume_change_10min'),
                    'volume_change_30min': layoff.get('volume_change_30min'),
                    'volume_change_1hr': layoff.get('volume_change_1hr'),
                    'volume_change_1.5hr': layoff.get('volume_change_1.5hr'),
                    'volume_change_2hr': layoff.get('volume_change_2hr'),
                    'volume_change_2.5hr': layoff.get('volume_change_2.5hr'),
                    'volume_change_3hr': layoff.get('volume_change_3hr'),
                    'change_1day': layoff.get('change_1day'),
                    'change_2day': layoff.get('change_2day'),
                    'change_3day': layoff.get('change_3day'),
                    'change_next_close': layoff.get('change_next_close'),
                    'price_1min': layoff.get('price_1min'),
                    'price_2min': layoff.get('price_2min'),
                    'price_3min': layoff.get('price_3min'),
                    'price_4min': layoff.get('price_4min'),
                    'price_5min': layoff.get('price_5min'),
                    'price_10min': layoff.get('price_10min'),
                    'price_30min': layoff.get('price_30min'),
                    'price_1hr': layoff.get('price_1hr'),
                    'price_1.5hr': layoff.get('price_1.5hr'),
                    'price_2hr': layoff.get('price_2hr'),
                    'price_2.5hr': layoff.get('price_2.5hr'),
                    'price_3hr': layoff.get('price_3hr'),
                    'price_1day': layoff.get('price_1day'),
                    'price_2day': layoff.get('price_2day'),
                    'price_3day': layoff.get('price_3day'),
                    'price_next_close': layoff.get('price_next_close'),
                    # Dates for each interval (for displaying day names)
                    'date_1min': layoff.get('date_1min'),
                    'date_2min': layoff.get('date_2min'),
                    'date_3min': layoff.get('date_3min'),
                    'date_4min': layoff.get('date_4min'),
                    'date_5min': layoff.get('date_5min'),
                    'date_10min': layoff.get('date_10min'),
                    'date_30min': layoff.get('date_30min'),
                    'date_1hr': layoff.get('date_1hr'),
                    'date_1.5hr': layoff.get('date_1.5hr'),
                    'date_2hr': layoff.get('date_2hr'),
                    'date_2.5hr': layoff.get('date_2.5hr'),
                    'date_3hr': layoff.get('date_3hr'),
                    'date_1day': layoff.get('date_1day'),
                    'date_2day': layoff.get('date_2day'),
                    'date_3day': layoff.get('date_3day'),
                    'date_next_close': layoff.get('date_next_close'),
                    # Datetimes for each interval (for displaying full date and time)
                    'datetime_1min': layoff.get('datetime_1min'),
                    'datetime_2min': layoff.get('datetime_2min'),
                    'datetime_3min': layoff.get('datetime_3min'),
                    'datetime_4min': layoff.get('datetime_4min'),
                    'datetime_5min': layoff.get('datetime_5min'),
                    'datetime_10min': layoff.get('datetime_10min'),
                    'datetime_30min': layoff.get('datetime_30min'),
                    'datetime_1hr': layoff.get('datetime_1hr'),
                    'datetime_1.5hr': layoff.get('datetime_1.5hr'),
                    'datetime_2hr': layoff.get('datetime_2hr'),
                    'datetime_2.5hr': layoff.get('datetime_2.5hr'),
                    'datetime_3hr': layoff.get('datetime_3hr'),
                    'datetime_1day': layoff.get('datetime_1day'),
                    'datetime_2day': layoff.get('datetime_2day'),
                    'datetime_3day': layoff.get('datetime_3day'),
                    'datetime_next_close': layoff.get('datetime_next_close'),
                    # Approximate time flags
                    'is_approximate_1min': layoff.get('is_approximate_1min', False),
                    'is_approximate_2min': layoff.get('is_approximate_2min', False),
                    'is_approximate_3min': layoff.get('is_approximate_3min', False),
                    'is_approximate_4min': layoff.get('is_approximate_4min', False),
                    'is_approximate_5min': layoff.get('is_approximate_5min', False),
                    'is_approximate_10min': layoff.get('is_approximate_10min', False),
                    'is_approximate_30min': layoff.get('is_approximate_30min', False),
                    'is_approximate_1hr': layoff.get('is_approximate_1hr', False),
                    'is_approximate_1.5hr': layoff.get('is_approximate_1.5hr', False),
                    'is_approximate_2hr': layoff.get('is_approximate_2hr', False),
                    'is_approximate_2.5hr': layoff.get('is_approximate_2.5hr', False),
                    'is_approximate_3hr': layoff.get('is_approximate_3hr', False),
                    'is_approximate_1day': layoff.get('is_approximate_1day', False),
                    'is_approximate_2day': layoff.get('is_approximate_2day', False),
                    'is_approximate_3day': layoff.get('is_approximate_3day', False),
                    'is_approximate_next_close': layoff.get('is_approximate_next_close', False),
                    # Actual datetimes (when approximate)
                    'actual_datetime_1min': layoff.get('actual_datetime_1min'),
                    'actual_datetime_2min': layoff.get('actual_datetime_2min'),
                    'actual_datetime_3min': layoff.get('actual_datetime_3min'),
                    'actual_datetime_4min': layoff.get('actual_datetime_4min'),
                    'actual_datetime_5min': layoff.get('actual_datetime_5min'),
                    'actual_datetime_10min': layoff.get('actual_datetime_10min'),
                    'actual_datetime_30min': layoff.get('actual_datetime_30min'),
                    'actual_datetime_1hr': layoff.get('actual_datetime_1hr'),
                    'actual_datetime_1.5hr': layoff.get('actual_datetime_1.5hr'),
                    'actual_datetime_2hr': layoff.get('actual_datetime_2hr'),
                    'actual_datetime_2.5hr': layoff.get('actual_datetime_2.5hr'),
                    'actual_datetime_3hr': layoff.get('actual_datetime_3hr'),
                    'actual_datetime_1day': layoff.get('actual_datetime_1day'),
                    'actual_datetime_2day': layoff.get('actual_datetime_2day'),
                    'actual_datetime_3day': layoff.get('actual_datetime_3day'),
                    'actual_datetime_next_close': layoff.get('actual_datetime_next_close'),
                    # Market closed flags
                    'market_closed_1min': layoff.get('market_closed_1min'),
                    'market_closed_2min': layoff.get('market_closed_2min'),
                    'market_closed_3min': layoff.get('market_closed_3min'),
                    'market_closed_4min': layoff.get('market_closed_4min'),
                    'market_closed_5min': layoff.get('market_closed_5min'),
                    'market_closed_10min': layoff.get('market_closed_10min'),
                    'market_closed_30min': layoff.get('market_closed_30min'),
                    'market_closed_1hr': layoff.get('market_closed_1hr'),
                    'market_closed_1.5hr': layoff.get('market_closed_1.5hr'),
                    'market_closed_2hr': layoff.get('market_closed_2hr'),
                    'market_closed_2.5hr': layoff.get('market_closed_2.5hr'),
                    'market_closed_3hr': layoff.get('market_closed_3hr'),
                    'market_closed_1day': layoff.get('market_closed_1day'),
                    'market_closed_2day': layoff.get('market_closed_2day'),
                    # Daily close flags (for intraday intervals using daily data)
                    'is_daily_close_1min': layoff.get('is_daily_close_1min'),
                    'is_daily_close_2min': layoff.get('is_daily_close_2min'),
                    'is_daily_close_3min': layoff.get('is_daily_close_3min'),
                    'is_daily_close_4min': layoff.get('is_daily_close_4min'),
                    'is_daily_close_5min': layoff.get('is_daily_close_5min'),
                    'is_daily_close_10min': layoff.get('is_daily_close_10min'),
                    'is_daily_close_30min': layoff.get('is_daily_close_30min'),
                    'is_daily_close_1hr': layoff.get('is_daily_close_1hr'),
                    'is_daily_close_1.5hr': layoff.get('is_daily_close_1.5hr'),
                    'is_daily_close_2hr': layoff.get('is_daily_close_2hr'),
                    'is_daily_close_2.5hr': layoff.get('is_daily_close_2.5hr'),
                    'is_daily_close_3hr': layoff.get('is_daily_close_3hr'),
                    'is_daily_close_next_close': layoff.get('is_daily_close_next_close'),
                    # Intraday flags (indicates open-to-close movement)
                    'is_intraday_1min': layoff.get('is_intraday_1min'),
                    'is_intraday_2min': layoff.get('is_intraday_2min'),
                    'is_intraday_3min': layoff.get('is_intraday_3min'),
                    'is_intraday_4min': layoff.get('is_intraday_4min'),
                    'is_intraday_5min': layoff.get('is_intraday_5min'),
                    'is_intraday_10min': layoff.get('is_intraday_10min'),
                    'is_intraday_30min': layoff.get('is_intraday_30min'),
                    'is_intraday_1hr': layoff.get('is_intraday_1hr'),
                    'is_intraday_1.5hr': layoff.get('is_intraday_1.5hr'),
                    'is_intraday_2hr': layoff.get('is_intraday_2hr'),
                    'is_intraday_2.5hr': layoff.get('is_intraday_2.5hr'),
                    'is_intraday_3hr': layoff.get('is_intraday_3hr'),
                    # New insight fields
                    'layoff_reason': layoff.get('layoff_reason'),
                    'expected_savings': layoff.get('expected_savings'),
                    'financial_context': layoff.get('financial_context'),
                    'affected_departments': layoff.get('affected_departments'),
                    'guidance_change': layoff.get('guidance_change'),
                    'ai_prediction_score': layoff.get('ai_prediction_score'),
                    'ai_prediction_direction': layoff.get('ai_prediction_direction'),
                    'price_history': layoff.get('price_history', []),
                    'base_price': layoff.get('base_price'),
                })
            
            # Send final data with API errors and source stats (optimized JSON with compact separators)
            try:
                final_payload = {
                    'type': 'complete',
                    'data': {
                        'layoffs': layoffs_data,
                        'total': len(layoffs_data),
                        'logs': all_logs,
                        'api_errors': tracker.api_errors,
                        'source_stats': getattr(tracker, 'source_stats', {})
                    }
                }
                # Use ensure_ascii=False and handle encoding errors gracefully
                final_json = json.dumps(final_payload, separators=(',', ':'), ensure_ascii=False)
                yield f"data: {final_json}\n\n"
            except Exception as json_err:
                # If JSON serialization fails, send error message instead of crashing
                error_msg = f"Error serializing final data: {str(json_err)}"
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg, 'layoffs_count': len(layoffs_data)}, separators=(',', ':'))}\n\n"
                print(f"[ERROR] {error_msg}", file=sys.stderr)
            
        except Exception as e:
            # Catch any unhandled exceptions and send error message to client
            error_msg = f"Unexpected error during stream: {str(e)}"
            try:
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg}, separators=(',', ':'))}\n\n"
            except:
                # If even error message fails, try minimal message
                yield f"data: {json.dumps({'type': 'error', 'message': 'Stream error occurred'}, separators=(',', ':'))}\n\n"
            print(f"[ERROR] {error_msg}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        finally:
            # Always restore stdout/stderr and clean up
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            if 'log_file' in locals() and log_file is not None:
                try:
                    log_file.close()
                except:
                    pass
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/extract_search_subject', methods=['POST'])
def extract_search_subject():
    """Extract search subject and terms from article using Claude API"""
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # Suppress SSL warning for verify=False
    from bs4 import BeautifulSoup
    
    try:
        data = request.get_json(force=True) or {}
        title = data.get('title', '')
        url = data.get('url', '')
        full_text = data.get('full_text', '')
        
        if not title and not url:
            return jsonify({'error': 'No article title or URL provided'}), 400
        
        # If full_text not provided, try to fetch from URL
        if not full_text and url:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # Try to extract main article content
                    article_body = soup.find('article') or soup.find('main') or soup.find('div', class_='article-body')
                    if article_body:
                        full_text = article_body.get_text(separator=' ', strip=True)
                    else:
                        # Fallback: get all text but remove scripts/styles
                        for script in soup(['script', 'style', 'nav', 'header', 'footer']):
                            script.decompose()
                        full_text = soup.get_text(separator=' ', strip=True)
            except Exception as e:
                return jsonify({'error': f'Failed to fetch article content: {str(e)}'}), 500
        
        # Get Claude API key from LayoffTracker instance
        tracker = LayoffTracker()
        claude_api_key = tracker.claude_api_key
        claude_api_url = tracker.claude_api_url
        
        if not claude_api_key:
            return jsonify({'error': 'Claude API key not configured'}), 500
        
        # Build prompt for Claude
        prompt = f"""You are helping a quant researcher find repeatable patterns in news that cause rapid stock moves.

Given the article below (title + full text), extract ONLY from the article itself:

1. One concise **search subject** that captures the core scenario described in this article that is most likely to explain the stock move (e.g., "Biotech stock drops after Phase 2 trial failure", "Small-cap oncology stock surges on FDA fast-track designation").
2. 5–15 **search terms/phrases** that:
   - Are actually present in the article text (or very close paraphrases),
   - Are tightly related to the specific event that is likely moving the stock (e.g., trial result, FDA decision, guidance cut, major contract, layoff, etc.),
   - Are good candidates to reuse as search queries to find similar articles for other companies.
   Do NOT invent generic themes that are not clearly expressed in the article.
3. A very short explanation (1–2 sentences) of why this specific subject in the article is likely to cause a rapid move in the stock.

IMPORTANT CONSTRAINTS:
- **Use only terms and phrases that clearly come from this article** (title or body); do not invent new jargon or topics.
- Focus on the part of the article that is most material to the stock price (e.g., trial outcome, FDA action, large layoff, big contract, guidance change, major financing).
- The search terms should be usable directly in Google News / RSS queries.

Return JSON with this exact structure (no extra text, no markdown):

{{
  "search_subject": "...",
  "search_terms": ["term1", "term2", "term3", ...],
  "explanation": "..."
}}

TITLE:
{title}

FULL TEXT:
{full_text[:8000] if len(full_text) > 8000 else full_text}
"""

        headers = {
            'x-api-key': claude_api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        
        payload = {
            # Use the same model and style as the existing AI prediction flow
            # to avoid model-availability errors
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 512,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }
        
        response = requests.post(claude_api_url, headers=headers, json=payload, timeout=30, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('content', [])
            if content and len(content) > 0:
                text = content[0].get('text', '').strip()
                
                # Try to parse JSON from Claude's response
                try:
                    # Remove markdown code blocks if present
                    if '```json' in text:
                        text = text.split('```json')[1].split('```')[0].strip()
                    elif '```' in text:
                        text = text.split('```')[1].split('```')[0].strip()
                    
                    # If there's extra prose around the JSON, try to isolate the JSON object
                    if not text.lstrip().startswith('{'):
                        first_brace = text.find('{')
                        last_brace = text.rfind('}')
                        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                            text = text[first_brace:last_brace + 1].strip()
                    
                    result = json.loads(text)
                    return jsonify(result)
                except json.JSONDecodeError:
                    # Fallback: return raw response so user can see what Claude returned
                    return jsonify({
                        'search_subject': 'Could not parse Claude response',
                        'search_terms': [],
                        'explanation': 'Claude returned non-JSON format. Inspect raw_response for details.',
                        'raw_response': text
                    })
            else:
                return jsonify({'error': 'Claude API returned empty response'}), 500
        else:
            error_msg = f"Claude API returned status {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', error_msg)
            except:
                pass
            return jsonify({'error': error_msg}), response.status_code
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/api/bearish-analytics/stream')
def get_bearish_analytics_stream():
    """Streaming endpoint for real-time bearish analytics logs using Server-Sent Events"""
    def generate():
        import time
        start_time = time.time()
        
        # Store logs for final response
        all_logs = []
        log_queue = queue.Queue()
        fetch_complete = False
        results = []
        
        def log_callback(message):
            log_queue.put(message)
        
        # Capture logs with callback
        log_capture = LogCapture(stream_callback=log_callback, file_handle=None)
        
        # Redirect stdout to capture logs
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log_capture
        sys.stderr = log_capture
        
        # Get parameters from query string
        bearish_date_str = request.args.get('bearish_date')
        target_date_str = request.args.get('target_date')
        industry = request.args.get('industry', 'All Industries')
        filter_type = request.args.get('filter_type', 'bearish')  # 'bearish' or 'bullish'
        pct_threshold_str = request.args.get('pct_threshold')
        
        if not bearish_date_str or not target_date_str:
            yield f"data: {json.dumps({'type': 'error', 'message': 'bearish_date and target_date are required'})}\n\n"
            return
        
        # Parse percentage threshold
        pct_threshold = None
        if pct_threshold_str:
            try:
                pct_threshold = float(pct_threshold_str)
            except ValueError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid percentage threshold'})}\n\n"
                return
        
        # Parse dates
        try:
            bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'})}\n\n"
            return
        
        # Validate date range
        if target_date < bearish_date:
            yield f"data: {json.dumps({'type': 'error', 'message': 'target_date must be >= bearish_date'})}\n\n"
            return
        
        # Limit date range to 1 year
        max_range = timedelta(days=365)
        if target_date - bearish_date > max_range:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Date range cannot exceed 1 year'})}\n\n"
            return
        
        def fetch_data():
            nonlocal fetch_complete, results, all_logs
            try:
                tracker = LayoffTracker()
                results, logs = tracker.get_bearish_analytics(bearish_date, target_date, industry, filter_type=filter_type, pct_threshold=pct_threshold)
                all_logs = logs
                fetch_complete = True
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print(f"[BEARISH ANALYTICS FETCH ERROR] {str(e)}")
                print(f"[BEARISH ANALYTICS FETCH ERROR] Traceback: {error_trace}")
                log_queue.put(f"❌ Error occurred: {str(e)}")
                results = []  # Ensure results is set even on error
                all_logs = logs if 'logs' in locals() else []
                fetch_complete = True
        
        # Start fetch in background thread
        fetch_thread = Thread(target=fetch_data, daemon=True)
        fetch_thread.start()
        
        # Stream logs in real-time
        last_log_time = time.time()
        while not fetch_complete or not log_queue.empty():
            try:
                # Get log message (with timeout to allow checking fetch_complete)
                try:
                    message = log_queue.get(timeout=0.5)
                    all_logs.append(message)
                    yield f"data: {json.dumps({'type': 'log', 'message': message})}\n\n"
                    last_log_time = time.time()
                except queue.Empty:
                    # No new logs, but check if we should continue
                    if fetch_complete and log_queue.empty():
                        break
                    # Send heartbeat to keep connection alive
                    if time.time() - last_log_time > 5:
                        yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                        last_log_time = time.time()
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Stream error: {str(e)}'})}\n\n"
                break
        
        # Wait for thread to complete
        fetch_thread.join(timeout=1)
        
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Send final results
        elapsed_time = time.time() - start_time
        try:
            # Ensure all data is JSON serializable (convert any date objects, etc.)
            serializable_results = []
            for result in results:
                serializable_result = result.copy()
                # Ensure earnings_dividends dates are strings
                if 'earnings_dividends' in serializable_result and serializable_result['earnings_dividends']:
                    ed = serializable_result['earnings_dividends']
                    if 'events_during' in ed and ed['events_during']:
                        ed['events_during'] = [
                            {**event, 'date': str(event.get('date', ''))} if not isinstance(event.get('date'), str) else event
                            for event in ed['events_during']
                        ]
                    if 'next_events' in ed and ed['next_events']:
                        ed['next_events'] = [
                            {**event, 'date': str(event.get('date', ''))} if not isinstance(event.get('date'), str) else event
                            for event in ed['next_events']
                        ]
                serializable_results.append(serializable_result)
            
            response_data = {
                'type': 'complete',
                'results': serializable_results,
                'total': len(serializable_results),
                'logs': all_logs,
                'bearish_date': bearish_date_str,
                'target_date': target_date_str,
                'industry': industry,
                'elapsed_time': elapsed_time
            }
            yield f"data: {json.dumps(response_data)}\n\n"
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[BEARISH ANALYTICS STREAM ERROR] Serialization error: {str(e)}")
            print(f"[BEARISH ANALYTICS STREAM ERROR] Traceback: {error_trace}")
            # Try to send results without earnings_dividends if that's the issue
            try:
                simplified_results = []
                for result in results:
                    simplified_result = result.copy()
                    if 'earnings_dividends' in simplified_result:
                        simplified_result['earnings_dividends'] = {
                            'events_during': [],
                            'next_events': [],
                            'has_events_during': False,
                            'has_next_events': False
                        }
                    simplified_results.append(simplified_result)
                yield f"data: {json.dumps({'type': 'complete', 'results': simplified_results, 'total': len(simplified_results), 'logs': all_logs, 'bearish_date': bearish_date_str, 'target_date': target_date_str, 'industry': industry, 'elapsed_time': elapsed_time, 'warning': 'Earnings data excluded due to serialization error'})}\n\n"
            except Exception as e2:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error serializing results: {str(e)}'})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/bearish-analytics')
def get_bearish_analytics():
    """API endpoint to get bearish analytics data (non-streaming, for backwards compatibility)"""
    try:
        # Get parameters from query string
        bearish_date_str = request.args.get('bearish_date')
        target_date_str = request.args.get('target_date')
        industry = request.args.get('industry', 'All Industries')
        filter_type = request.args.get('filter_type', 'bearish')  # 'bearish' or 'bullish'
        pct_threshold_str = request.args.get('pct_threshold')
        
        if not bearish_date_str or not target_date_str:
            return jsonify({'error': 'bearish_date and target_date are required'}), 400
        
        # Parse percentage threshold
        pct_threshold = None
        if pct_threshold_str:
            try:
                pct_threshold = float(pct_threshold_str)
            except ValueError:
                return jsonify({'error': 'Invalid percentage threshold'}), 400
        
        # Parse dates
        try:
            bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Validate date range
        if target_date < bearish_date:
            return jsonify({'error': 'target_date must be >= bearish_date'}), 400
        
        # Limit date range to 1 year
        max_range = timedelta(days=365)
        if target_date - bearish_date > max_range:
            return jsonify({'error': 'Date range cannot exceed 1 year'}), 400
        
        # Get analytics
        try:
            print(f"[BEARISH ANALYTICS API] Starting analysis: bearish_date={bearish_date_str}, target_date={target_date_str}, industry={industry}, filter_type={filter_type}, pct_threshold={pct_threshold}")
            tracker = LayoffTracker()
            print(f"[BEARISH ANALYTICS API] Tracker initialized, calling get_bearish_analytics...")
            results, logs = tracker.get_bearish_analytics(bearish_date, target_date, industry, filter_type=filter_type, pct_threshold=pct_threshold)
            print(f"[BEARISH ANALYTICS API] Analysis complete: {len(results)} results, {len(logs)} log entries")
            
            return jsonify({
                'results': results,
                'total': len(results),
                'bearish_date': bearish_date_str,
                'target_date': target_date_str,
                'industry': industry,
                'logs': logs
            })
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[BEARISH ANALYTICS API ERROR] {error_trace}")
            return jsonify({
                'error': f'Error during analysis: {str(e)}',
                'logs': [f"❌ Error occurred: {str(e)}", f"Details: {error_trace[:500]}"]
            }), 500
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/api/stock-events')
def get_stock_events():
    """API endpoint to fetch next events (future earnings/dividends) for a single stock on-demand"""
    try:
        ticker = request.args.get('ticker')
        bearish_date_str = request.args.get('bearish_date')
        target_date_str = request.args.get('target_date')
        
        if not ticker or not bearish_date_str or not target_date_str:
            return jsonify({'error': 'Missing required parameters: ticker, bearish_date, target_date'}), 400
        
        # Parse dates
        try:
            bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError as e:
            return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
        
        # Fetch next_events only (future events after target_date)
        tracker = LayoffTracker()
        next_events_data = tracker.get_stock_next_events(ticker, bearish_date, target_date, future_days=40)
        
        return jsonify({
            'ticker': ticker,
            'next_events': next_events_data.get('next_events', []),
            'has_next_events': next_events_data.get('has_next_events', False)
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[STOCK EVENTS API ERROR] {error_trace}")
        return jsonify({
            'error': f'Error fetching events: {str(e)}'
        }), 500

@app.route('/api/ai-opinion', methods=['POST'])
def get_ai_opinion():
    """Unified API endpoint to fetch AI recovery analysis (score + explanation) with caching
    
    Returns both score and explanation. Results are cached in memory.
    Frontend can request score_only=true to get just the score for faster initial display.
    """
    try:
        data = request.get_json()
        ticker = data.get('ticker')
        bearish_date_str = data.get('bearish_date')
        target_date_str = data.get('target_date')
        score_only = data.get('score_only', False)  # If True, return only score (faster)
        stock_data = data.get('stock_data', {})
        
        if not ticker or not bearish_date_str or not target_date_str:
            return jsonify({'error': 'Missing required parameters: ticker, bearish_date, target_date'}), 400
        
        # Parse dates
        try:
            bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError as e:
            return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
        
        # Check cache first
        cached = get_cached_ai_opinion(ticker, bearish_date_str, target_date_str)
        if cached:
            if score_only:
                return jsonify({
                    'ticker': ticker,
                    'score': cached['score'],
                    'cached': True
                })
            else:
                return jsonify({
                    'ticker': ticker,
                    'score': cached['score'],
                    'explanation': cached['explanation'],
                    'cached': True
                })
        
        # If stock_data is incomplete, try to fetch required data
        if not stock_data.get('price_history') or not stock_data.get('bearish_price'):
            # Fetch data needed for AI analysis
            tracker = LayoffTracker()
            try:
                price_history = tracker.get_stock_price_history(ticker, bearish_date - timedelta(days=90), target_date)
                if not price_history:
                    return jsonify({'error': 'Could not fetch price history for analysis'}), 500
                
                bearish_price, actual_bearish_date = tracker.extract_price_from_history(price_history, bearish_date)
                target_price, actual_target_date = tracker.extract_price_from_history(price_history, target_date)
                
                if bearish_price is None or target_price is None:
                    return jsonify({'error': 'Could not extract prices from history'}), 500
                
                # Fetch earnings/dividends
                earnings_dividends = tracker._check_earnings_dividends_sec(ticker, bearish_date, target_date, future_days=0)
                yfinance_result = tracker._check_earnings_dividends_yfinance(ticker, bearish_date, target_date, future_days=0)
                if yfinance_result:
                    yfinance_events = yfinance_result.get('events_during', [])
                    if yfinance_events:
                        earnings_dividends['events_during'].extend(yfinance_events)
                        earnings_dividends['has_events_during'] = len(earnings_dividends['events_during']) > 0
                
                # Build stock_data
                stock_data = {
                    'company_name': stock_data.get('company_name', ticker),
                    'industry': stock_data.get('industry', 'Unknown'),
                    'market_cap': stock_data.get('market_cap', 0),
                    'bearish_date': actual_bearish_date or bearish_date_str,
                    'bearish_price': bearish_price,
                    'prev_price': stock_data.get('prev_price', bearish_price),
                    'pct_drop': stock_data.get('pct_drop', 0),
                    'target_date': actual_target_date or target_date_str,
                    'target_price': target_price,
                    'recovery_pct': stock_data.get('recovery_pct', 0),
                    'price_history': price_history,
                    'earnings_dividends': earnings_dividends
                }
            except Exception as fetch_error:
                return jsonify({'error': f'Failed to fetch stock data: {str(fetch_error)}'}), 500
        
        # Get full AI analysis (always use explanation API for consistency)
        tracker = LayoffTracker()
        company_name = stock_data.get('company_name', ticker)
        result = tracker.get_ai_recovery_opinion(ticker, company_name, stock_data)
        
        if result:
            score = result.get('score')
            explanation = result.get('explanation', '')
            
            # Cache the result
            cache_ai_opinion(ticker, bearish_date_str, target_date_str, score, explanation)
            
            if score_only:
                return jsonify({
                    'ticker': ticker,
                    'score': score,
                    'cached': False
                })
            else:
                return jsonify({
                    'ticker': ticker,
                    'score': score,
                    'explanation': explanation,
                    'cached': False
                })
        else:
            return jsonify({'error': 'Failed to get AI analysis'}), 500
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[AI OPINION API ERROR] {error_trace}")
        return jsonify({
            'error': f'Error fetching AI opinion: {str(e)}'
        }), 500

@app.route('/api/ai-opinion-score', methods=['POST'])
def get_ai_opinion_score():
    """Legacy endpoint - redirects to unified /api/ai-opinion with score_only=true"""
    data = request.get_json()
    if data:
        data['score_only'] = True
    # Create a new request context with updated data
    from flask import has_request_context
    if has_request_context():
        request.json = data
    return get_ai_opinion()

@app.route('/api/ai-opinion-explanation', methods=['POST'])
def get_ai_opinion_explanation():
    """Legacy endpoint - redirects to unified /api/ai-opinion (returns full explanation)"""
    data = request.get_json()
    if data:
        data['score_only'] = False
        request.json = data
    return get_ai_opinion()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8082)

