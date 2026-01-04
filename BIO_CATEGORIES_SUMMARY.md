# Small-Cap & Mid-Cap Biotech Categories

## Overview

Created two new categories for biotech companies based on market capitalization and high volume trading:

1. **Small-Cap Biotech** - Market cap ~$300M-$2B, high volume (≥500K ADV)
2. **Mid-Cap Biotech** - Market cap ~$2B-$10B, high volume (≥1M ADV)

## Implementation Details

### 1. New Event Types in `config.py`

Added two new event types:

```python
'bio_companies_small_cap': {
    'name': 'Small-Cap Biotech',
    'keywords': [],
    'requires_all': False,
    'query_by_company_names': True,
    'category': 'small_cap',
    'sic_codes': [2834, 2836]
},
'bio_companies_mid_cap': {
    'name': 'Mid-Cap Biotech',
    'keywords': [],
    'requires_all': False,
    'query_by_company_names': True,
    'category': 'mid_cap',
    'sic_codes': [2834, 2836]
}
```

### 2. Updated `_get_bio_pharma_companies()` Method

The method now accepts a `category` parameter:
- `'small_cap'` - Returns 117 small-cap biotech companies
- `'mid_cap'` - Returns 55 mid-cap biotech companies  
- `'all'` - Returns all liquid companies (backwards compatibility, 59 companies)

### 3. Company Lists

#### Small-Cap Biotech (117 companies)
**Criteria:** Market cap ~$300M-$2B, Average Daily Volume ≥500K shares

**Sample companies:**
- ATHIRA PHARMA
- CENTURY THERAPEUTICS
- VISTAGEN THERAPEUTICS
- PYXIS ONCOLOGY
- GEOVAX LABS
- NOVABAY PHARMACEUTICALS
- CUMBERLAND PHARMACEUTICALS
- AMC ROBOTICS CORPORATION
- FATE THERAPEUTICS
- KURA ONCOLOGY
- And 107 more...

#### Mid-Cap Biotech (55 companies)
**Criteria:** Market cap ~$2B-$10B, Average Daily Volume ≥1M shares

**Sample companies:**
- MODERNA
- BIONTECH
- NOVAVAX
- ILLUMINA
- VERTEX PHARMACEUTICALS
- ALNYLAM
- EXELIXIS
- INCYTE
- SEATTLE GENETICS
- CLOVIS ONCOLOGY
- And 45 more...

### 4. Updated Search Logic

The search logic in `search_google_news_rss()` and `_try_google_news_rss()` now:
- Detects `query_by_company_names` flag (works for all bio_companies variants)
- Extracts `category` from event config
- Calls `_get_bio_pharma_companies(category=category)` with appropriate category
- Creates Google News queries using company names from the selected category

### 5. Optimized Company Name Extraction

The `extract_layoff_info()` method now:
- Detects bio_companies event types (all variants)
- Gets the appropriate category from event config
- Uses the category-specific company list as candidates for fast matching
- Falls back to SEC EDGAR search only if needed

## Usage

### In Code

```python
from main import LayoffTracker
from config import EVENT_TYPES

tracker = LayoffTracker()

# Get small-cap companies
small_cap = tracker._get_bio_pharma_companies('small_cap')
print(f"Small-cap: {len(small_cap)} companies")

# Get mid-cap companies
mid_cap = tracker._get_bio_pharma_companies('mid_cap')
print(f"Mid-cap: {len(mid_cap)} companies")

# Search for articles
articles = tracker.search_google_news_rss(event_types=['bio_companies_small_cap'])
```

### In UI

Users can now select:
- **"Small-Cap Biotech"** - Searches 117 small-cap companies
- **"Mid-Cap Biotech"** - Searches 55 mid-cap companies
- **"Bio Companies"** - Searches all liquid companies (backwards compatible)

## Benefits

1. **Focused Searches**: Users can target specific market cap ranges
2. **Better Performance**: Smaller lists = faster searches and processing
3. **High Volume Focus**: Only includes stocks with active trading (better liquidity)
4. **Backwards Compatible**: Original `bio_companies` event type still works

## Statistics

- **Small-Cap Biotech**: 117 companies (≥500K ADV)
- **Mid-Cap Biotech**: 55 companies (≥1M ADV)
- **All Bio Companies**: 59 companies (≥1M ADV, includes large-cap)

## Next Steps

To use these categories in the UI, update `templates/index.html` to:
1. Add options for "Small-Cap Biotech" and "Mid-Cap Biotech" in the event types dropdown
2. Update JavaScript to handle the new event types
3. Test that searches work correctly for each category

