# SEC EDGAR Search Diagnosis Report

## Problem
The SEC EDGAR search is not finding expected filings, even though they should match keywords like "earnings miss", "trial failure", "guidance cut", etc.

## Root Cause Analysis

### Issue #1: SEC EDGAR Atom Feed Contains Only Metadata

The SEC EDGAR Atom feed (`/cgi-bin/browse-edgar?action=getcurrent&type=8-K&output=atom`) **does NOT contain the actual filing content**. It only provides:

✅ **What the feed contains:**
- Company name (in title)
- Filing date
- Accession number
- File size
- Item numbers (e.g., "Item 8.01: Other Events", "Item 2.02: Results of Operations")

❌ **What the feed does NOT contain:**
- Actual filing text/content
- Details about earnings, trials, guidance, etc.
- Any substantive information that would match keywords

### Example Entry Structure

```
Title: "8-K - Flux Power Holdings, Inc. (0001083743) (Filer)"
Summary: "Filed: 2025-12-12 AccNo: 0001493152-25-027595 Size: 24 MB
Item 8.01: Other Events
Item 9.01: Financial Statements and Exhibits"
```

**Result:** When the code checks if keywords like "earnings miss" or "trial failure" are in the title or summary, they're never found because that information isn't in the feed.

### Issue #2: Keyword Matching Logic

The current implementation in `search_sec_edgar()` does:

```python
title_text = title_elem.text.strip()
summary_text = summary_elem.text.strip()
combined_text = f"{title_text} {summary_text}".lower()
matches = any(keyword.lower() in combined_text for keyword in all_keywords)
```

This only checks the title and summary (metadata), not the actual filing content.

### Issue #3: Expected Filings May Not Be in Feed

The test searched for:
- MAIA Biotechnology (MAIA) - Dec 11, 2025
- Immuron (IMRN) - Dec 10, 2025
- Applied Therapeutics (APLT) - Dec 9, 2025
- Merck (MRK) - Dec 5, 2025

**None of these were found in the recent entries**, which could mean:
1. They weren't filed on those exact dates
2. The dates are in the future (relative to when the test runs)
3. The Atom feed may not include all filings immediately

## Why It's Not Working

1. **No Content in Feed**: The Atom feed summary only contains Item numbers (like "Item 8.01: Other Events"), not the actual content of those items.

2. **Keyword Matching Fails**: Keywords like "earnings miss", "trial failure", "guidance cut" are in the actual 8-K document, not in the Atom feed metadata.

3. **Need to Fetch Documents**: To match keywords, the system would need to:
   - Fetch each 8-K filing document from the URL
   - Parse the HTML/XBRL content
   - Extract the text
   - Match keywords against the full text

## Current Limitations

The current `search_sec_edgar()` implementation has a fundamental limitation:
- ✅ It can find all recent 8-K filings
- ✅ It can filter by date
- ❌ It **cannot** match keywords because the content isn't in the feed
- ❌ It **cannot** identify what the filing is about without fetching the document

## What Would Be Needed to Fix This

To actually match keywords and find filings like "earnings miss" or "trial failure", the system would need to:

1. **Fetch Each Filing Document**:
   - Parse the filing index page URL from the Atom feed
   - Find the actual document URL (usually HTML or XBRL)
   - Download the document

2. **Parse Document Content**:
   - Extract text from HTML/XBRL
   - Handle different document formats
   - Parse structured data (tables, exhibits)

3. **Match Keywords**:
   - Search the full document text for keywords
   - This would be much slower (requires fetching 100+ documents per search)

4. **Performance Considerations**:
   - Fetching and parsing 100+ documents would be slow
   - SEC EDGAR has rate limits
   - Would need caching to avoid re-fetching

## Conclusion

The SEC EDGAR search is working correctly from a technical standpoint - it's fetching the Atom feed and parsing entries. However, **it cannot match keywords because the Atom feed doesn't contain the filing content**, only metadata.

The expected filings (MAIA, Immuron, Applied Therapeutics, Merck) either:
- Aren't in the feed (possibly wrong dates or not filed yet)
- Are in the feed but can't be matched because keywords aren't in the metadata

To make this work, the system would need to fetch and parse the actual 8-K filing documents, which is a much more complex and slower operation.

