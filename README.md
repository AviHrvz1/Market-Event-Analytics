# Layoff Tracker

Tracks layoff announcements from publicly traded companies over the last 60 days.

## Features

- Fetches layoff news from NewsAPI
- Extracts company name, stock ticker, layoff percentage, and announcement date/time
- Filters for publicly traded companies
- Sorts by date/time (most recent first), then by layoff percentage (highest first)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Get a NewsAPI key from https://newsapi.org/
   - Free tier allows 100 requests/day

3. Create a `.env` file:
```
NEWS_API_KEY=your_api_key_here
```

## Usage

### Command Line Interface
Run the script directly:
```bash
python main.py
```

### Web Interface (Recommended)
Start the Flask web server:
```bash
python app.py
```

Then open your browser and navigate to:
```
http://localhost:5000
```

The web interface provides:
- Beautiful, modern UI with a responsive table
- Real-time data refresh
- Sortable columns (sorted by date/time by default)
- Statistics dashboard
- Auto-refresh every 5 minutes

## Output

The script prints a formatted table with:
- Company Name
- Stock Ticker
- Layoff Percentage
- Date
- Time

Sorted by date/time (most recent first), then by layoff percentage (highest first).

## Notes

- The script uses pattern matching to extract company names and layoff percentages
- Some announcements may not have exact percentages
- The company-to-ticker mapping can be expanded
- For production use, consider adding more data sources and better NLP for extraction

