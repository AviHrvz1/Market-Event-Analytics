#!/usr/bin/env python3
"""
Flask Web Application for Layoff Tracker
"""

import os
# Set SSL environment variables BEFORE importing yfinance (must be done early)
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''
# Try to disable SSL verification at the curl level
os.environ['CURLOPT_SSL_VERIFYPEER'] = '0'
os.environ['CURLOPT_SSL_VERIFYHOST'] = '0'

from flask import Flask, render_template, jsonify, Response, stream_with_context, request
from main import LayoffTracker
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None
import sys
import io
import json
import time
import copy
from contextlib import redirect_stdout, redirect_stderr
from threading import Lock, Thread
import queue

# Import yfinance for fallback data
try:
    import yfinance as yf
    import yfinance.data as yf_data
    YFINANCE_AVAILABLE = True
    
    # Patch yfinance to disable SSL verification
    try:
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
except ImportError:
    YFINANCE_AVAILABLE = False

app = Flask(__name__)

# Debug log file for events filtering
DEBUG_LOG_FILE = 'events_filter_debug.log'

def _write_debug_log_to_file(message):
    """Write debug message to log file"""
    try:
        import os
        # Use absolute path to ensure we can write
        log_path = os.path.join(os.getcwd(), DEBUG_LOG_FILE)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(message)
            f.flush()  # Ensure it's written immediately
    except Exception as e:
        # Log the error to stderr so we can see it
        import sys
        print(f"[DEBUG LOG ERROR] Failed to write to {DEBUG_LOG_FILE}: {e}", file=sys.stderr)

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

@app.route('/chart')
def chart():
    """Render TradingView chart page"""
    return render_template('chart.html')

@app.route('/api/pine-script/bearish-date')
def get_bearish_date_pine_script():
    """Generate Pine Script for drawing vertical line at bearish date"""
    bearish_date = request.args.get('date')
    if not bearish_date:
        return jsonify({'error': 'bearish_date parameter required'}), 400
    
    try:
        # Parse date (format: YYYY-MM-DD)
        date_parts = bearish_date.split('-')
        if len(date_parts) != 3:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        year = int(date_parts[0])
        month = int(date_parts[1])
        day = int(date_parts[2])
        
        # Generate Pine Script code
        pine_script = f"""//@version=5
indicator("Bearish Date Line - {bearish_date}", overlay=true, max_lines_count=500)

// Bearish date parameters (pre-filled)
year = {year}
month = {month}
day = {day}

// Line style and color
lineColor = input.color(color.red, title="Line Color")
lineWidth = input.int(2, title="Line Width", minval=1, maxval=5)

// Convert input date to timestamp
targetTime = timestamp(year, month, day, 0, 0)

// Draw vertical line on the bearish date
if time >= targetTime and time < targetTime + 86400000
    // Get the full price range for the line
    var float lineLow = low
    var float lineHigh = high
    
    // Update range to cover full visible area
    lineLow := math.min(lineLow, low)
    lineHigh := math.max(lineHigh, high)
    
    // Draw the line
    line.new(bar_index, lineLow, bar_index, lineHigh, color=lineColor, width=lineWidth, style=line.style_solid)
    
    // Add label at the top
    label.new(bar_index, lineHigh, "Bearish Date\\n{bearish_date}", 
              style=label.style_label_down, color=lineColor, textcolor=color.white, size=size.small)
"""
        
        # Return as plain text (Pine Script)
        from flask import Response
        return Response(pine_script, mimetype='text/plain')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        flexible_days = int(request.args.get('flexible_days', 0))
        ticker_filter_str = request.args.get('ticker_filter', '').strip()
        
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
                results, logs = tracker.get_bearish_analytics(
                    bearish_date,
                    target_date,
                    industry,
                    filter_type=filter_type,
                    pct_threshold=pct_threshold,
                    flexible_days=flexible_days,
                    ticker_filter=ticker_filter_str
                )
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
                # Use deepcopy to ensure nested structures (like recovery_history with event_info) are properly copied
                serializable_result = copy.deepcopy(result)
                
                # Ensure earnings_dividends dates are strings
                if 'earnings_dividends' in serializable_result and serializable_result['earnings_dividends']:
                    ed = serializable_result['earnings_dividends']
                    ticker_name = serializable_result.get('ticker', 'UNKNOWN')
                    bearish_date_str = serializable_result.get('bearish_date', 'UNKNOWN')
                    
                    # Debug: Log what we're serializing (also write to file)
                    events_during_count = len(ed.get('events_during', []))
                    all_events_count = len(ed.get('all_events_for_recovery', []))
                    log_msg = f"[SERIALIZATION] {ticker_name}: Serializing events - events_during={events_during_count}, all_events_for_recovery={all_events_count}, bearish_date={bearish_date_str}\n"
                    print(log_msg, end='')
                    _write_debug_log_to_file(log_msg)
                    
                    if events_during_count > 0:
                        events_during_dates = [e.get('date') for e in ed.get('events_during', []) if e.get('date')]
                        log_msg = f"[SERIALIZATION] {ticker_name}: events_during dates: {events_during_dates}\n"
                        print(log_msg, end='')
                        _write_debug_log_to_file(log_msg)
                        # Check if any are before bearish_date (BUG DETECTION)
                        events_before = [d for d in events_during_dates if d and d < bearish_date_str]
                        if events_before:
                            log_msg = f"[SERIALIZATION] ⚠️  {ticker_name}: BUG - {len(events_before)} events in events_during are BEFORE bearish_date: {events_before}\n"
                            print(log_msg, end='')
                            _write_debug_log_to_file(log_msg)
                    
                    if 'events_during' in ed and ed['events_during']:
                        ed['events_during'] = [
                            {**event, 'date': str(event.get('date', ''))} if not isinstance(event.get('date'), str) else event
                            for event in ed['events_during']
                        ]
                    if 'all_events_for_recovery' in ed and ed['all_events_for_recovery']:
                        ed['all_events_for_recovery'] = [
                            {**event, 'date': str(event.get('date', ''))} if not isinstance(event.get('date'), str) else event
                            for event in ed['all_events_for_recovery']
                        ]
                    if 'next_events' in ed and ed['next_events']:
                        ed['next_events'] = [
                            {**event, 'date': str(event.get('date', ''))} if not isinstance(event.get('date'), str) else event
                            for event in ed['next_events']
                        ]
                
                # Ensure recovery_history event_info is properly serialized
                if 'recovery_history' in serializable_result and serializable_result['recovery_history']:
                    rh = serializable_result['recovery_history']
                    if isinstance(rh, list):
                        ticker_name = result.get('ticker', 'UNKNOWN')
                        print(f"[SERIALIZATION] {ticker_name}: Processing {len(rh)} recovery_history items")
                        
                        events_found_count = 0
                        for idx, item in enumerate(rh):
                            # CRITICAL: Ensure event_info key ALWAYS exists (even if None)
                            # This is essential - JSON will include null values, but missing keys won't be in JSON
                            if 'event_info' not in item:
                                item['event_info'] = None
                                print(f"[SERIALIZATION] {ticker_name} recovery_history[{idx}]: Added missing 'event_info' key")
                            
                            # Explicitly ensure the key exists and is set (even if None)
                            # This prevents the key from being removed during JSON serialization
                            if 'event_info' not in item:
                                item['event_info'] = None
                            
                            # Only serialize if event_info is not None
                            if item.get('event_info') is not None:
                                event_info = item['event_info']
                                print(f"[SERIALIZATION] {ticker_name} recovery_history[{idx}]: Serializing event_info: {event_info}")
                                
                                # Ensure date is a string
                                if 'date' in event_info:
                                    if event_info['date'] is None:
                                        event_info['date'] = ''
                                    elif not isinstance(event_info['date'], str):
                                        event_info['date'] = str(event_info['date'])
                                
                                # Ensure all fields are JSON serializable
                                event_info['type'] = str(event_info.get('type', ''))
                                event_info['name'] = str(event_info.get('name', 'Event'))
                                
                                # Ensure days_after_drop is an integer
                                try:
                                    event_info['days_after_drop'] = int(event_info.get('days_after_drop', 0))
                                except (ValueError, TypeError):
                                    event_info['days_after_drop'] = 0
                                
                                event_info['icon'] = str(event_info.get('icon', '📅'))
                                
                                events_found_count += 1
                                
                                # Verify JSON serializability
                                try:
                                    json.dumps(event_info)
                                    print(f"[SERIALIZATION] {ticker_name} recovery_history[{idx}]: event_info is JSON serializable ✓")
                                except (TypeError, ValueError) as e:
                                    print(f"[SERIALIZATION] {ticker_name} recovery_history[{idx}]: ERROR - event_info is NOT JSON serializable: {e}")
                            
                            # Log structure for debugging (first item only)
                            if idx == 0:
                                item_keys = list(item.keys())
                                has_key = 'event_info' in item
                                key_value = item.get('event_info')
                                print(f"[SERIALIZATION] {ticker_name} recovery_history[0]: keys={item_keys}, event_info={'present' if has_key else 'MISSING'}, value={key_value}")
                                # CRITICAL: Force add the key if missing, then verify JSON
                                if not has_key:
                                    print(f"[SERIALIZATION] {ticker_name} recovery_history[0]: ⚠️ Key missing! Force adding 'event_info': None")
                                    item['event_info'] = None
                                    has_key = True
                                # Verify the key will be in JSON
                                try:
                                    test_json = json.dumps(item)
                                    if '"event_info"' in test_json:
                                        print(f"[SERIALIZATION] {ticker_name} recovery_history[0]: ✅ 'event_info' key WILL be in JSON")
                                    else:
                                        print(f"[SERIALIZATION] {ticker_name} recovery_history[0]: ❌ 'event_info' key will NOT be in JSON!")
                                        print(f"[SERIALIZATION] {ticker_name} recovery_history[0]: JSON preview: {test_json[:200]}")
                                        # Force add again and retest
                                        item['event_info'] = None
                                        test_json2 = json.dumps(item)
                                        if '"event_info"' in test_json2:
                                            print(f"[SERIALIZATION] {ticker_name} recovery_history[0]: ✅ After force-add, key IS in JSON")
                                        else:
                                            print(f"[SERIALIZATION] {ticker_name} recovery_history[0]: ❌ After force-add, key STILL NOT in JSON!")
                                except Exception as e:
                                    print(f"[SERIALIZATION] {ticker_name} recovery_history[0]: ERROR testing JSON: {e}")
                        
                        print(f"[SERIALIZATION] {ticker_name}: {len(rh)} items processed, {events_found_count} with non-None event_info")
                        
                        # CRITICAL: Verify event_info key exists in ALL items after processing
                        items_missing_key = [i for i, item in enumerate(rh) if 'event_info' not in item]
                        if items_missing_key:
                            print(f"[SERIALIZATION] {ticker_name}: ERROR - {len(items_missing_key)} items still missing 'event_info' key after processing: {items_missing_key}")
                            # Force add the key to all missing items
                            for missing_idx in items_missing_key:
                                rh[missing_idx]['event_info'] = None
                                print(f"[SERIALIZATION] {ticker_name}: Force-added 'event_info' key to item {missing_idx}")
                        else:
                            print(f"[SERIALIZATION] {ticker_name}: ✅ All {len(rh)} items have 'event_info' key")
                
                # Preserve debug info from main.py
                if '_debug_events_filter' in result:
                    serializable_result['_debug_events_filter'] = result['_debug_events_filter']
                    ticker_name = serializable_result.get('ticker', 'UNKNOWN')
                    print(f"[SERIALIZATION] {ticker_name}: Preserved _debug_events_filter: {serializable_result['_debug_events_filter']}")
                else:
                    ticker_name = serializable_result.get('ticker', 'UNKNOWN')
                    print(f"[SERIALIZATION] {ticker_name}: ⚠️  _debug_events_filter NOT FOUND in result - function may not have run")
                
                serializable_results.append(serializable_result)
            
            # Final verification: Check recovery_history event_info before sending
            for result in serializable_results:
                ticker = result.get('ticker', 'UNKNOWN')
                if 'recovery_history' in result and result['recovery_history']:
                    rh = result['recovery_history']
                    items_with_key = sum(1 for item in rh if 'event_info' in item)
                    items_with_events = sum(1 for item in rh if item.get('event_info') is not None)
                    
                    print(f"[FINAL CHECK] {ticker}: About to send {len(rh)} recovery_history items")
                    print(f"[FINAL CHECK] {ticker}: {items_with_key} items have 'event_info' key, {items_with_events} have non-None event_info")
                    
                    # Verify structure of first item
                    if len(rh) > 0:
                        first_item = rh[0]
                        first_item_keys = list(first_item.keys())
                        has_event_info_key = 'event_info' in first_item
                        event_info_value = first_item.get('event_info')
                        
                        print(f"[FINAL CHECK] {ticker}: First item keys: {first_item_keys}")
                        print(f"[FINAL CHECK] {ticker}: First item has 'event_info' key: {has_event_info_key}")
                        print(f"[FINAL CHECK] {ticker}: First item event_info value: {event_info_value}")
                        
                        # Verify JSON serializability of first item AND check if event_info is in JSON string
                        try:
                            test_json_str = json.dumps(first_item)
                            if '"event_info"' in test_json_str:
                                print(f"[FINAL CHECK] {ticker}: ✅ First item is JSON serializable AND 'event_info' key IS in JSON string")
                            else:
                                print(f"[FINAL CHECK] {ticker}: ❌ First item is JSON serializable BUT 'event_info' key is NOT in JSON string!")
                                print(f"[FINAL CHECK] {ticker}: JSON preview: {test_json_str[:300]}")
                                # Force add the key and retest
                                first_item['event_info'] = None
                                test_json_str2 = json.dumps(first_item)
                                if '"event_info"' in test_json_str2:
                                    print(f"[FINAL CHECK] {ticker}: ✅ After force-add, 'event_info' key IS in JSON string")
                                else:
                                    print(f"[FINAL CHECK] {ticker}: ❌ After force-add, 'event_info' key STILL NOT in JSON string!")
                        except (TypeError, ValueError) as e:
                            print(f"[FINAL CHECK] {ticker}: ERROR - First item is NOT JSON serializable: {e}")
            
            # FINAL SAFEGUARD: Force add event_info key to ALL recovery_history items right before JSON serialization
            for result in serializable_results:
                ticker = result.get('ticker', 'UNKNOWN')
                if 'recovery_history' in result and result['recovery_history']:
                    rh = result['recovery_history']
                    items_fixed = 0
                    for item in rh:
                        if 'event_info' not in item:
                            item['event_info'] = None
                            items_fixed += 1
                    if items_fixed > 0:
                        print(f"[FINAL SAFEGUARD] {ticker}: Force-added 'event_info' key to {items_fixed} items right before JSON serialization")
                    
                    # Verify first item has the key and it's in JSON
                    if len(rh) > 0:
                        first_item = rh[0]
                        if 'event_info' not in first_item:
                            first_item['event_info'] = None
                            print(f"[FINAL SAFEGUARD] {ticker}: ⚠️ First item still missing key after fix - force-added again")
                        
                        # Test JSON serialization
                        try:
                            test_json_str = json.dumps(first_item)
                            if '"event_info"' in test_json_str:
                                print(f"[FINAL SAFEGUARD] {ticker}: ✅ 'event_info' key IS in JSON string")
                            else:
                                print(f"[FINAL SAFEGUARD] {ticker}: ❌ 'event_info' key is NOT in JSON string!")
                                print(f"[FINAL SAFEGUARD] {ticker}: Keys in dict: {list(first_item.keys())}")
                                print(f"[FINAL SAFEGUARD] {ticker}: JSON preview: {test_json_str[:300]}")
                        except Exception as e:
                            print(f"[FINAL SAFEGUARD] {ticker}: ERROR testing JSON: {e}")
            
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
        flexible_days = int(request.args.get('flexible_days', 0))
        
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
            print(f"[BEARISH ANALYTICS API] Starting analysis: bearish_date={bearish_date_str}, target_date={target_date_str}, industry={industry}, filter_type={filter_type}, pct_threshold={pct_threshold}, flexible_days={flexible_days}")
            tracker = LayoffTracker()
            print(f"[BEARISH ANALYTICS API] Tracker initialized, calling get_bearish_analytics...")
            results, logs = tracker.get_bearish_analytics(bearish_date, target_date, industry, filter_type=filter_type, pct_threshold=pct_threshold, flexible_days=flexible_days)
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

def _utc_to_israel_time(utc_dt):
    """Convert UTC datetime to Israel time (IST/IDT)"""
    if ZoneInfo:
        # Use proper timezone handling if available
        israel_tz = ZoneInfo('Asia/Jerusalem')
        return utc_dt.astimezone(israel_tz)
    else:
        # Fallback: simple offset (not perfect but better than nothing)
        # DST in Israel: Last Sunday in March to last Sunday in October (roughly April-October)
        is_israel_dst = 4 <= utc_dt.month <= 10
        israel_offset_hours = 3 if is_israel_dst else 2
        return utc_dt + timedelta(hours=israel_offset_hours)

@app.route('/api/vwap-chart-data')
def get_vwap_chart_data():
    """API endpoint to fetch intraday data and calculate candles with VWAP for chart display
    
    Query parameters:
    - ticker: Stock ticker symbol (required)
    - bearish_date: Date in YYYY-MM-DD format (required)
    - interval: Candle interval - one of: 5m, 15m, 30m, 1h, 1d (default: 15m)
               Uses Prixe.io data directly - no aggregation on our side
    """
    try:
        ticker = request.args.get('ticker')
        bearish_date_str = request.args.get('bearish_date')
        interval_param = request.args.get('interval', '15m').lower()
        
        if not ticker or not bearish_date_str:
            return jsonify({'error': 'Missing required parameters: ticker, bearish_date'}), 400
        
        # Validate and map interval to Prixe.io format
        # Prixe.io supports: 5m, 15m, 30m, 1h, 1d
        valid_intervals = {
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '1d': '1d'
        }
        
        if interval_param not in valid_intervals:
            return jsonify({
                'success': False,
                'error': f'Invalid interval. Must be one of: {", ".join(valid_intervals.keys())}'
            }), 400
        
        prixe_interval = valid_intervals[interval_param]
        
        # Parse bearish_date
        try:
            bearish_date = datetime.strptime(bearish_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError as e:
            return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
        
        # Check if bearish_date is today
        now_utc = datetime.now(timezone.utc)
        is_today = bearish_date.date() == now_utc.date()
        
        print(f"[VWAP API DEBUG] bearish_date={bearish_date_str}, is_today={is_today}, now_utc.date()={now_utc.date()}")
        
        # Fetch intraday data for bearish_date only
        tracker = LayoffTracker()
        
        # Initialize warning variable (will be set if data is missing)
        missing_data_warning = None
        
        # Calculate market open time for bearish_date
        market_open_utc = tracker._get_market_open_time(bearish_date, ticker)
        if not market_open_utc:
            return jsonify({
                'success': False,
                'error': 'Could not determine market open time'
            }), 400
        
        # Calculate market close time for bearish_date
        market_close_utc = tracker._get_market_close_time(bearish_date, ticker)
        
        if is_today:
            print(f"[VWAP API DEBUG] Using TODAY path")
            # If today, show full trading day from market open to current time (or market close if after hours)
            start_time_utc = market_open_utc  # 9:30 AM ET
            end_time_utc = min(now_utc, market_close_utc) if market_close_utc else now_utc
            
            # Fetch intraday data for bearish_date only
            bearish_date_only = bearish_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Request data at the specified interval directly from Prixe.io (no aggregation)
            intraday_data = tracker._fetch_intraday_data_for_day(ticker, bearish_date_only, interval=prixe_interval)
            
            if not intraday_data or not intraday_data.get('success') or 'data' not in intraday_data:
                return jsonify({
                    'success': False,
                    'error': 'No intraday data available for the specified date'
                }), 200
            
            data = intraday_data['data']
            timestamps = data.get('timestamp', [])
            opens = data.get('open', [])
            highs = data.get('high', [])
            lows = data.get('low', [])
            closes = data.get('close', [])
            volumes = data.get('volume', [])
            
            if not timestamps:
                return jsonify({
                    'success': False,
                    'error': 'No intraday data available for the specified date'
                }), 200
            
            # Filter data to the time window
            start_timestamp = int(start_time_utc.timestamp())
            end_timestamp = int(end_time_utc.timestamp())
            
            filtered_data = []
            for i, ts in enumerate(timestamps):
                if start_timestamp <= ts <= end_timestamp:
                    filtered_data.append({
                        'timestamp': ts,
                        'open': opens[i] if i < len(opens) else None,
                        'high': highs[i] if i < len(highs) else None,
                        'low': lows[i] if i < len(lows) else None,
                        'close': closes[i] if i < len(closes) else None,
                        'volume': volumes[i] if i < len(volumes) else 0
                    })
            
            if not filtered_data:
                return jsonify({
                    'success': False,
                    'error': 'No data available in the specified time range'
                }), 200
        else:
            print(f"[VWAP API DEBUG] Using PAST DATE path - full trading day of {bearish_date_str} + full trading day of next day")
            # For past dates: show full trading day of bearish_date + full trading day of next trading day (only trading hours)
            if not market_close_utc:
                return jsonify({
                    'success': False,
                    'error': 'Could not determine market close time'
                }), 400
            
            # Start from beginning of bearish_date (market open, e.g., 9:30 AM ET)
            start_time_utc = market_open_utc
            print(f"[VWAP API DEBUG] market_open_utc: {market_open_utc}, market_close_utc: {market_close_utc}, start_time_utc: {start_time_utc}, timestamp: {int(start_time_utc.timestamp())}")
            
            # Get next trading day
            next_trading_day = tracker.get_next_trading_day(bearish_date, ticker)
            print(f"[VWAP API DEBUG] next_trading_day: {next_trading_day}")
            if not next_trading_day:
                return jsonify({
                    'success': False,
                    'error': 'Could not determine next trading day'
                }), 400
            
            # Get market open and close for next trading day
            next_market_open_utc = tracker._get_market_open_time(next_trading_day, ticker)
            next_market_close_utc = tracker._get_market_close_time(next_trading_day, ticker)
            print(f"[VWAP API DEBUG] next_market_open_utc: {next_market_open_utc}, next_market_close_utc: {next_market_close_utc}")
            if not next_market_open_utc or not next_market_close_utc:
                return jsonify({
                    'success': False,
                    'error': 'Could not determine next trading day market hours'
                }), 400
            
            # End at market close of next trading day (e.g., 4:00 PM ET)
            end_time_utc = next_market_close_utc
            print(f"[VWAP API DEBUG] end_time_utc: {end_time_utc}, timestamp: {int(end_time_utc.timestamp())}")
            
            # Fetch intraday data for both bearish_date and next trading day
            bearish_date_only = bearish_date.replace(hour=0, minute=0, second=0, microsecond=0)
            # Ensure next_trading_day has timezone info before using replace
            if next_trading_day.tzinfo is None:
                next_trading_day = next_trading_day.replace(tzinfo=timezone.utc)
            next_trading_day_only = next_trading_day.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Fetch data for bearish_date at specified interval (no fallback - use Prixe.io data directly)
            intraday_data_day1 = tracker._fetch_intraday_data_for_day(ticker, bearish_date_only, interval=prixe_interval)
            
            # Fetch data for next trading day at same interval
            intraday_data_day2 = tracker._fetch_intraday_data_for_day(ticker, next_trading_day_only, interval=prixe_interval)
            
            # Combine data from both days
            all_timestamps = []
            all_opens = []
            all_highs = []
            all_lows = []
            all_closes = []
            all_volumes = []
            
            # Initialize warning variable (will be set if data is missing)
            missing_data_warning = None
            
            if intraday_data_day1 and intraday_data_day1.get('success') and 'data' in intraday_data_day1:
                data1 = intraday_data_day1['data']
                all_timestamps.extend(data1.get('timestamp', []))
                all_opens.extend(data1.get('open', []))
                all_highs.extend(data1.get('high', []))
                all_lows.extend(data1.get('low', []))
                all_closes.extend(data1.get('close', []))
                all_volumes.extend(data1.get('volume', []))
            
            if intraday_data_day2 and intraday_data_day2.get('success') and 'data' in intraday_data_day2:
                data2 = intraday_data_day2['data']
                all_timestamps.extend(data2.get('timestamp', []))
                all_opens.extend(data2.get('open', []))
                all_highs.extend(data2.get('high', []))
                all_lows.extend(data2.get('low', []))
                all_closes.extend(data2.get('close', []))
                all_volumes.extend(data2.get('volume', []))
            
            if not all_timestamps:
                return jsonify({
                    'success': False,
                    'error': 'No intraday data available for the specified dates'
                }), 200
            
            # Filter data to the time window (full trading day of day 1 + first 3 hours of day 2)
            start_timestamp = int(start_time_utc.timestamp())
            end_timestamp = int(end_time_utc.timestamp())
            
            # Debug: Check data before filtering
            day1_count_before = sum(1 for ts in all_timestamps 
                                   if datetime.fromtimestamp(ts, tz=timezone.utc).date() == bearish_date.date())
            day2_count_before = sum(1 for ts in all_timestamps 
                                   if datetime.fromtimestamp(ts, tz=timezone.utc).date() == next_trading_day.date())
            print(f"[VWAP DEBUG] Before filtering: {len(all_timestamps)} total, {day1_count_before} from {bearish_date_str}, {day2_count_before} from {next_trading_day.date()}")
            
            # Debug: Show first and last timestamps in raw data
            if all_timestamps:
                first_ts_raw = min(all_timestamps)
                last_ts_raw = max(all_timestamps)
                first_dt_raw = datetime.fromtimestamp(first_ts_raw, tz=timezone.utc)
                last_dt_raw = datetime.fromtimestamp(last_ts_raw, tz=timezone.utc)
                print(f"[VWAP DEBUG] Raw data range: first={first_dt_raw} UTC (timestamp: {first_ts_raw}), last={last_dt_raw} UTC (timestamp: {last_ts_raw})")
                print(f"[VWAP DEBUG] Expected range: start={start_time_utc} UTC (timestamp: {start_timestamp}), end={end_time_utc} UTC (timestamp: {end_timestamp})")
                
                # Check if we're missing data from market open
                missing_data_warning = None
                if first_ts_raw > start_timestamp:
                    missing_seconds = first_ts_raw - start_timestamp
                    missing_minutes = missing_seconds / 60
                    print(f"[VWAP WARNING] ⚠️  Missing {missing_minutes:.0f} minutes ({missing_seconds} seconds) of data from market open!")
                    print(f"[VWAP WARNING]    Expected start: {start_time_utc} UTC")
                    print(f"[VWAP WARNING]    Actual first data point: {first_dt_raw} UTC")
                    
                    # Try to fetch missing data from yfinance
                    print(f"[VWAP FALLBACK DEBUG] YFINANCE_AVAILABLE={YFINANCE_AVAILABLE}, missing_minutes={missing_minutes:.0f}")
                    print(f"[VWAP FALLBACK DEBUG] Condition check: YFINANCE_AVAILABLE={YFINANCE_AVAILABLE}, missing_minutes > 30 = {missing_minutes > 30}")
                    if YFINANCE_AVAILABLE and missing_minutes > 30:  # Only try if missing more than 30 minutes
                        print(f"[VWAP FALLBACK] ✅ Condition met! Attempting to fetch missing data from yfinance...")
                        print(f"[VWAP FALLBACK] Ticker: {ticker}, Bearish date: {bearish_date_str}")
                        try:
                            # yfinance needs date strings
                            date_str = bearish_date.strftime('%Y-%m-%d')
                            next_date_str = (bearish_date + timedelta(days=1)).strftime('%Y-%m-%d')
                            print(f"[VWAP FALLBACK] Fetching yfinance data: {ticker} from {date_str} to {next_date_str}, interval=1m")
                            
                            # Download 1-minute data for the day
                            yf_data = yf.download(
                                ticker,
                                start=date_str,
                                end=next_date_str,
                                interval='1m',
                                progress=False,
                                auto_adjust=False
                            )
                            print(f"[VWAP FALLBACK] yfinance download completed. Data empty: {yf_data.empty}, Shape: {yf_data.shape if not yf_data.empty else 'N/A'}")
                            
                            if not yf_data.empty:
                                # Convert to UTC timestamps and filter to missing range
                                yf_timestamps = []
                                yf_opens = []
                                yf_highs = []
                                yf_lows = []
                                yf_closes = []
                                yf_volumes = []
                                
                                for idx, row in yf_data.iterrows():
                                    # Convert pandas timestamp to UTC
                                    try:
                                        import pytz
                                        if idx.tz is None:
                                            # Assume ET timezone if not set
                                            et_tz = pytz.timezone('America/New_York')
                                            idx_et = et_tz.localize(idx)
                                            idx_utc = idx_et.astimezone(timezone.utc)
                                        else:
                                            idx_utc = idx.tz_convert('UTC')
                                        
                                        ts_utc = int(idx_utc.timestamp())
                                    except Exception as e:
                                        print(f"[VWAP FALLBACK] Error processing yfinance row: {e}")
                                        continue
                                    
                                    # Only include data in the missing range
                                    if start_timestamp <= ts_utc < first_ts_raw:
                                        yf_timestamps.append(ts_utc)
                                        yf_opens.append(float(row['Open']))
                                        yf_highs.append(float(row['High']))
                                        yf_lows.append(float(row['Low']))
                                        yf_closes.append(float(row['Close']))
                                        yf_volumes.append(int(row['Volume']) if 'Volume' in row else 0)
                                
                                if yf_timestamps:
                                    print(f"[VWAP FALLBACK] ✅ Fetched {len(yf_timestamps)} data points from yfinance for missing period")
                                    # Prepend yfinance data to the arrays
                                    all_timestamps = yf_timestamps + all_timestamps
                                    all_opens = yf_opens + all_opens
                                    all_highs = yf_highs + all_highs
                                    all_lows = yf_lows + all_lows
                                    all_closes = yf_closes + all_closes
                                    all_volumes = yf_volumes + all_volumes
                                    
                                    # Update first timestamp
                                    first_ts_raw = min(all_timestamps)
                                    first_dt_raw = datetime.fromtimestamp(first_ts_raw, tz=timezone.utc)
                                    
                                    if first_ts_raw <= start_timestamp:
                                        print(f"[VWAP FALLBACK] ✅ Successfully filled missing data! Data now starts at {first_dt_raw} UTC")
                                    else:
                                        missing_data_warning = f"Missing {missing_minutes:.0f} minutes from market open (yfinance fallback partially filled)"
                                        print(f"[VWAP FALLBACK] ⚠️  Partially filled - still missing some data")
                                else:
                                    print(f"[VWAP FALLBACK] ❌ yfinance data available but not in missing time range")
                                    missing_data_warning = f"Missing {missing_minutes:.0f} minutes from market open (yfinance fallback unavailable)"
                            else:
                                print(f"[VWAP FALLBACK] ❌ No yfinance data available")
                                missing_data_warning = f"Missing {missing_minutes:.0f} minutes from market open (yfinance fallback unavailable)"
                        except Exception as e:
                            print(f"[VWAP FALLBACK] ❌ Error fetching from yfinance: {e}")
                            missing_data_warning = f"Missing {missing_minutes:.0f} minutes from market open (yfinance fallback failed: {str(e)})"
                    else:
                        missing_data_warning = f"Missing {missing_minutes:.0f} minutes from market open"
                else:
                    print(f"[VWAP DEBUG] ✅ Data starts at or before market open")
            
            filtered_data = []
            for i, ts in enumerate(all_timestamps):
                ts_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                ts_date = ts_dt.date()
                
                # Check if timestamp is within the overall range
                if start_timestamp <= ts <= end_timestamp:
                    # Also check if timestamp is during market hours for that day
                    is_valid_trading_hour = False
                    
                    if ts_date == bearish_date.date():
                        # For bearish_date: include full trading hours (9:30 AM - 4:00 PM ET)
                        if market_open_utc.timestamp() <= ts <= market_close_utc.timestamp():
                            is_valid_trading_hour = True
                    elif ts_date == next_trading_day.date():
                        # For next trading day: include full trading hours (9:30 AM - 4:00 PM ET)
                        if next_market_open_utc.timestamp() <= ts <= next_market_close_utc.timestamp():
                            is_valid_trading_hour = True
                    
                    if is_valid_trading_hour:
                        filtered_data.append({
                            'timestamp': ts,
                            'open': all_opens[i] if i < len(all_opens) else None,
                            'high': all_highs[i] if i < len(all_highs) else None,
                            'low': all_lows[i] if i < len(all_lows) else None,
                            'close': all_closes[i] if i < len(all_closes) else None,
                            'volume': all_volumes[i] if i < len(all_volumes) else 0
                        })
            
            # Debug: Check data after filtering
            day1_count_after = sum(1 for d in filtered_data 
                                  if datetime.fromtimestamp(d['timestamp'], tz=timezone.utc).date() == bearish_date.date())
            day2_count_after = sum(1 for d in filtered_data 
                                  if datetime.fromtimestamp(d['timestamp'], tz=timezone.utc).date() == next_trading_day.date())
            print(f"[VWAP DEBUG] After filtering: {len(filtered_data)} total, {day1_count_after} from {bearish_date_str}, {day2_count_after} from {next_trading_day.date()}")
            
            if not filtered_data:
                return jsonify({
                    'success': False,
                    'error': 'No data available in the specified time range'
                }), 200
        
        # Sort filtered data by timestamp
        filtered_data.sort(key=lambda x: x['timestamp'])
        
        # Debug: Check filtered data dates
        filtered_dates = set()
        for d in filtered_data:
            dt = datetime.fromtimestamp(d['timestamp'], tz=timezone.utc)
            filtered_dates.add(dt.date())
        print(f"[VWAP DEBUG] Filtered data dates: {sorted(filtered_dates)}")
        print(f"[VWAP DEBUG] Using Prixe.io interval: {prixe_interval}")
        
        # Initialize arrays for candles
        candles_15min = []
        vwap_points = []
        time_labels = []
        
        cumulative_price_volume = 0
        cumulative_volume = 0
        current_trading_day = None  # Track current trading day for VWAP reset
        
        # Use Prixe.io data directly - no aggregation
        # Prixe.io already provides candles at the requested interval
        print(f"[VWAP DEBUG] Using Prixe.io data directly at {prixe_interval} interval - no aggregation")
        
        # Map interval to minutes for time label formatting
        interval_to_minutes = {
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '1d': 1440  # Daily
        }
        interval_minutes = interval_to_minutes.get(prixe_interval, 15)
        
        # Process each data point from Prixe.io as a candle
        for data_point in filtered_data:
            close = data_point.get('close')
            if close is None:
                continue
            
            # Get timestamp and check if we've moved to a new trading day
            ts = data_point['timestamp']
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            candle_date = dt.date()
            
            # Reset VWAP calculation at the start of each new trading day
            if current_trading_day is None or candle_date != current_trading_day:
                # Reset VWAP for the new trading day
                cumulative_price_volume = 0
                cumulative_volume = 0
                current_trading_day = candle_date
                print(f"[VWAP DEBUG] Resetting VWAP for new trading day: {candle_date}")
            
            # Use OHLC from Prixe.io if available, otherwise calculate from close
            candle_open = data_point.get('open') or close
            candle_high = data_point.get('high') or close
            candle_low = data_point.get('low') or close
            candle_close = close
            candle_volume = data_point.get('volume', 0)
            
            # Calculate VWAP (resets each trading day)
            typical_price = (candle_high + candle_low + candle_close) / 3
            if candle_volume > 0:
                cumulative_price_volume += typical_price * candle_volume
                cumulative_volume += candle_volume
                candle_vwap = cumulative_price_volume / cumulative_volume if cumulative_volume > 0 else typical_price
            else:
                candle_vwap = typical_price
            
            # Format time label based on interval
            israel_dt = _utc_to_israel_time(dt)
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            month = month_names[israel_dt.month - 1]
            day = israel_dt.day
            hour = israel_dt.hour
            minute_val = israel_dt.minute
            
            if prixe_interval == '1h':
                time_label = f"{month} {day} {hour:02d}:00"
            elif prixe_interval == '30m':
                minute_display = 0 if minute_val < 30 else 30
                time_label = f"{month} {day} {hour:02d}:{minute_display:02d}"
            elif prixe_interval == '1d':
                time_label = f"{month} {day}"
            else:
                # 5m, 15m - show full time
                time_label = f"{month} {day} {hour:02d}:{minute_val:02d}"
            
            candles_15min.append({
                'timestamp': ts,
                'open': candle_open,
                'high': candle_high,
                'low': candle_low,
                'close': candle_close,
                'volume': candle_volume
            })
            vwap_points.append(candle_vwap)
            time_labels.append(time_label)
        
        # Calculate overall VWAP
        if cumulative_volume > 0:
            overall_vwap = cumulative_price_volume / cumulative_volume
        else:
            # Fallback: average of all closes
            overall_vwap = sum(c['close'] for c in candles_15min) / len(candles_15min) if candles_15min else 0
        
        # Debug: Check final candles
        print(f"[VWAP DEBUG] Processed {len(filtered_data)} data points into {len(candles_15min)} candles")
        if candles_15min:
            first_candle_dt = datetime.fromtimestamp(candles_15min[0]['timestamp'], tz=timezone.utc)
            last_candle_dt = datetime.fromtimestamp(candles_15min[-1]['timestamp'], tz=timezone.utc)
            unique_candle_dates = set()
            for c in candles_15min:
                dt = datetime.fromtimestamp(c['timestamp'], tz=timezone.utc)
                unique_candle_dates.add(dt.date())
            print(f"[VWAP DEBUG] Final candles: {len(candles_15min)} candles, dates: {sorted(unique_candle_dates)}, first: {first_candle_dt}, last: {last_candle_dt}")
        
        # Add debug info to response (only if candles exist)
        debug_info = None
        if candles_15min:
            try:
                debug_info = {
                    'is_today': is_today,
                    'bearish_date': bearish_date_str,
                    'first_candle_timestamp': candles_15min[0]['timestamp'],
                    'last_candle_timestamp': candles_15min[-1]['timestamp'],
                    'candle_count': len(candles_15min)
                }
            except:
                pass
        
        response_data = {
            'success': True,
            'candles': candles_15min,
            'vwap': overall_vwap,
            'vwap_points': vwap_points,
            'time_labels': time_labels
        }
        if debug_info:
            response_data['debug_info'] = debug_info
        
        # Add warning if data is incomplete (check if missing_data_warning was set)
        # Note: missing_data_warning is set in the past date path, need to check if it exists
        if 'missing_data_warning' in locals() and missing_data_warning:
            response_data['warning'] = missing_data_warning
        
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[VWAP CHART DATA API ERROR] {error_trace}")
        return jsonify({
            'success': False,
            'error': f'Error fetching VWAP chart data: {str(e)}'
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
            # Check if API key is the issue
            if not tracker.claude_api_key or tracker.claude_api_key == 'sk-ant-api03-YourActualClaudeAPIKeyHere-ReplaceThisWithYourRealKey':
                return jsonify({
                    'error': 'AI opinion not configured. Please update CLAUDE_API_KEY in config.py with your actual API key.'
                }), 500
            
            # Provide more specific error message
            error_msg = 'Failed to get AI analysis. This could be due to: network connectivity issues, API timeout, or Claude API service issues. Check server logs (server.log) for details.'
            return jsonify({'error': error_msg}), 500
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_msg = f'Error fetching AI opinion: {str(e)}'
        print(f"[AI OPINION API ERROR] {error_trace}", flush=True)
        # Also write to log file if it exists
        try:
            with open('server.log', 'a') as f:
                f.write(f"\n[AI OPINION API ERROR] {datetime.now()}\n{error_trace}\n\n")
        except:
            pass
        return jsonify({
            'error': error_msg
        }), 500

@app.route('/api/add-ticker', methods=['POST'])
def add_ticker():
    """Add a ticker to stocks.json"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        ticker = data.get('ticker', '').strip().upper()
        name = data.get('name', '').strip()
        industry = data.get('industry', '').strip()
        market_cap = data.get('market_cap', 0)
        
        # Validate required fields
        if not ticker:
            return jsonify({'error': 'Ticker is required'}), 400
        if not name:
            return jsonify({'error': 'Company name is required'}), 400
        if not industry:
            return jsonify({'error': 'Industry is required'}), 400
        if not market_cap or market_cap <= 0:
            return jsonify({'error': 'Valid market cap is required'}), 400
        
        # Validate industry is one of the allowed categories
        allowed_industries = ['Technology', 'Healthcare', 'Financials', 'Energy', 'Consumer', 
                             'Industrial', 'Communication', 'Utilities', 'Real Estate', 'Materials', 'ETFs']
        if industry not in allowed_industries:
            return jsonify({'error': f'Industry must be one of: {", ".join(allowed_industries)}'}), 400
        
        # Load stocks.json
        import os
        from pathlib import Path
        json_path = Path(__file__).parent / 'stocks.json'
        
        if not json_path.exists():
            return jsonify({'error': 'stocks.json file not found'}), 500
        
        # Read current data
        with open(json_path, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
        
        # Check if ticker already exists
        if ticker in stocks:
            return jsonify({'error': f'Ticker {ticker} already exists in stocks.json'}), 400
        
        # Add new ticker
        stocks[ticker] = {
            'name': name,
            'industry': industry,
            'market_cap': int(market_cap)
        }
        
        # Save back to file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(stocks, f, indent=2, ensure_ascii=False)
        
        # Invalidate cache in LayoffTracker
        # This is done by clearing the cache attribute on the next instance
        # We can't directly access the instance, but the cache will be invalidated
        # on the next file modification time check
        
        return jsonify({
            'success': True,
            'message': f'Ticker {ticker} added successfully',
            'ticker': ticker,
            'name': name,
            'industry': industry,
            'market_cap': market_cap
        })
        
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON in stocks.json: {str(e)}'}), 500
    except IOError as e:
        return jsonify({'error': f'Error reading/writing stocks.json: {str(e)}'}), 500
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ADD TICKER API ERROR] {error_trace}")
        return jsonify({'error': f'Error adding ticker: {str(e)}'}), 500

@app.route('/api/remove-ticker', methods=['POST'])
def remove_ticker():
    """Remove a ticker from stocks.json"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        ticker = data.get('ticker', '').strip().upper()
        
        # Validate required fields
        if not ticker:
            return jsonify({'error': 'Ticker is required'}), 400
        
        # Load stocks.json
        import os
        from pathlib import Path
        json_path = Path(__file__).parent / 'stocks.json'
        
        if not json_path.exists():
            return jsonify({'error': 'stocks.json file not found'}), 500
        
        # Read current data
        with open(json_path, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
        
        # Check if ticker exists
        if ticker not in stocks:
            return jsonify({'error': f'Ticker {ticker} not found in stocks.json'}), 404
        
        # Get ticker info before removal (for response)
        ticker_info = stocks[ticker].copy()
        
        # Remove ticker
        del stocks[ticker]
        
        # Save back to file (sorted by ticker)
        sorted_stocks = dict(sorted(stocks.items()))
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_stocks, f, indent=2, ensure_ascii=False)
        
        # Invalidate cache in LayoffTracker
        # This is done by clearing the cache attribute on the next instance
        # We can't directly access the instance, but the cache will be invalidated
        # on the next file modification time check
        
        return jsonify({
            'success': True,
            'message': f'Ticker {ticker} removed successfully',
            'ticker': ticker,
            'name': ticker_info.get('name', ''),
            'industry': ticker_info.get('industry', ''),
            'market_cap': ticker_info.get('market_cap', 0)
        })
        
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON in stocks.json: {str(e)}'}), 500
    except IOError as e:
        return jsonify({'error': f'Error reading/writing stocks.json: {str(e)}'}), 500
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[REMOVE TICKER API ERROR] {error_trace}")
        return jsonify({'error': f'Error removing ticker: {str(e)}'}), 500

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
    # Disable automatic dotenv loading to avoid permission issues
    import os
    os.environ['FLASK_SKIP_DOTENV'] = '1'
    
    # Redirect stdout and stderr to a log file so we can read server output
    SERVER_LOG_FILE = 'server_output.log'
    log_file = open(SERVER_LOG_FILE, 'a', encoding='utf-8')
    
    # Create a class that writes to both console and file
    class TeeOutput:
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush()
        def flush(self):
            for f in self.files:
                f.flush()
    
    # Redirect stdout and stderr to both console and file
    import sys
    sys.stdout = TeeOutput(sys.stdout, log_file)
    sys.stderr = TeeOutput(sys.stderr, log_file)
    
    print("=" * 60)
    print("Starting Flask server...")
    print("Server will be available at: http://127.0.0.1:8082")
    print(f"Server output is being logged to: {SERVER_LOG_FILE}")
    print("=" * 60)
    
    # Debug: Print all registered routes
    print("\nRegistered routes:")
    for rule in app.url_map.iter_rules():
        if '/api' in rule.rule:
            print(f"  {rule.rule} -> {rule.endpoint} (methods: {rule.methods})")
    print("=" * 60 + "\n")
    
    try:
        app.run(debug=True, host='127.0.0.1', port=8082, use_reloader=False)
    except OSError as e:
        if "Operation not permitted" in str(e) or e.errno == 1:
            print("\n" + "=" * 60)
            print("ERROR: Cannot bind to port 8082")
            print("This is a macOS security restriction.")
            print("\nPlease run this command in your terminal:")
            print("  cd '/Users/avi.horowitz/Documents/LayoffTracker -10'")
            print("  python3 app.py")
            print("=" * 60)
        else:
            print(f"\nError starting server: {e}")
            print("Trying port 8083...")
            try:
                app.run(debug=True, host='127.0.0.1', port=8083, use_reloader=False)
            except Exception as e2:
                print(f"Failed on port 8083: {e2}")
                raise

