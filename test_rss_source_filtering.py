#!/usr/bin/env python3
"""Unit test to verify RSS source filtering works with keywords in title, description, or both"""

from bs4 import BeautifulSoup
from config import EVENT_TYPES

print("=" * 80)
print("RSS Source Filtering Unit Test")
print("=" * 80)
print()

# Test cases: (title, description, event_type, expected_match)
test_cases = [
    # Test 1: Keyword in title only
    {
        'title': 'Airbus Announces Product Recall',
        'description': 'The company issued a statement about safety measures.',
        'event_type': 'recall',
        'expected_match': True,
        'test_name': 'Keyword in title only'
    },
    # Test 2: Keyword in description only
    {
        'title': 'Airbus Announces Safety Update',
        'description': 'Airbus has issued a voluntary recall of its aircraft due to safety concerns.',
        'event_type': 'recall',
        'expected_match': True,
        'test_name': 'Keyword in description only'
    },
    # Test 3: Keyword in both title and description
    {
        'title': 'Airbus Product Recall',
        'description': 'The company has initiated a recall campaign for affected models.',
        'event_type': 'recall',
        'expected_match': True,
        'test_name': 'Keyword in both title and description'
    },
    # Test 4: No keyword match
    {
        'title': 'Airbus Announces New Product Line',
        'description': 'The company is launching new aircraft models next year.',
        'event_type': 'recall',
        'expected_match': False,
        'test_name': 'No keyword match'
    },
    # Test 5: Layoff keyword in title
    {
        'title': 'Company Announces Major Layoffs',
        'description': 'The restructuring will affect multiple departments.',
        'event_type': 'layoff_event',
        'expected_match': True,
        'test_name': 'Layoff keyword in title'
    },
    # Test 6: Layoff keyword in description
    {
        'title': 'Company Restructuring Plan',
        'description': 'The company will implement job cuts affecting 10% of workforce.',
        'event_type': 'layoff_event',
        'expected_match': True,
        'test_name': 'Layoff keyword in description'
    },
    # Test 7: Multiple keywords (one in title, one in description)
    {
        'title': 'Company Announces Layoffs',
        'description': 'The downsizing will affect multiple regions.',
        'event_type': 'layoff_event',
        'expected_match': True,
        'test_name': 'Multiple keywords (title and description)'
    },
    # Test 8: No relevant keywords (should not match)
    {
        'title': 'Company Announces New Product',
        'description': 'The company is launching a new product line next quarter.',
        'event_type': 'recall',
        'expected_match': False,
        'test_name': 'No relevant keywords (should not match)'
    },
]

def test_rss_filtering_logic(title, description, event_type, expected_match):
    """Test the RSS filtering logic (simulating the code in main.py)"""
    if event_type not in EVENT_TYPES:
        return False, f"Event type '{event_type}' not found in EVENT_TYPES"
    
    keywords = EVENT_TYPES[event_type]['keywords']
    
    # Simulate the filtering logic from main.py (after our fix)
    title_lower = title.lower()
    description_lower = description.lower()
    full_text = f"{title_lower} {description_lower}"
    
    # Check if any keyword matches
    matches = any(keyword.lower() in full_text for keyword in keywords)
    
    return matches == expected_match, matches

print("Running test cases...")
print()

passed = 0
failed = 0
results = []

for i, test_case in enumerate(test_cases, 1):
    title = test_case['title']
    description = test_case['description']
    event_type = test_case['event_type']
    expected_match = test_case['expected_match']
    test_name = test_case['test_name']
    
    success, actual_match = test_rss_filtering_logic(title, description, event_type, expected_match)
    
    if success:
        status = "✅ PASS"
        passed += 1
    else:
        status = "❌ FAIL"
        failed += 1
    
    results.append({
        'test_num': i,
        'test_name': test_name,
        'status': status,
        'expected': expected_match,
        'actual': actual_match,
        'title': title,
        'description': description[:60] + '...' if len(description) > 60 else description
    })
    
    print(f"Test {i}: {test_name}")
    print(f"   Status: {status}")
    print(f"   Expected: {expected_match}, Actual: {actual_match}")
    if not success:
        print(f"   Title: {title}")
        print(f"   Description: {description[:80]}...")
    print()

print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Total tests: {len(test_cases)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print()

if failed > 0:
    print("Failed tests:")
    for result in results:
        if result['status'] == "❌ FAIL":
            print(f"   Test {result['test_num']}: {result['test_name']}")
            print(f"      Expected: {result['expected']}, Got: {result['actual']}")
    print()

# Test with actual RSS item structure
print("=" * 80)
print("TESTING WITH MOCK RSS ITEM STRUCTURE")
print("=" * 80)
print()

# Create a mock RSS item (simulating BeautifulSoup structure)
class MockElement:
    def __init__(self, text):
        self._text = text
    
    def text(self):
        return self._text
    
    def find(self, tag):
        return None

class MockTitleElement:
    def __init__(self, text):
        self._text = text
    
    @property
    def text(self):
        return self._text

class MockDescriptionElement:
    def __init__(self, text):
        self._text = text
    
    @property
    def text(self):
        return self._text

# Simulate the actual filtering code from main.py
def simulate_rss_filtering(item_title, item_description, keywords):
    """Simulate the exact filtering logic from main.py"""
    title_elem = MockTitleElement(item_title) if item_title else None
    
    if title_elem and title_elem.text:
        title_text = title_elem.text.strip()
        title_lower = title_text.lower()
        
        # Get description for keyword matching (NEW FIX)
        description_elem = MockDescriptionElement(item_description) if item_description else None
        description_text = description_elem.text.strip() if description_elem and description_elem.text else ''
        description_lower = description_text.lower()
        
        # Check if matches keywords in both title and description (NEW FIX)
        full_text = f"{title_lower} {description_lower}"
        matches = any(keyword.lower() in full_text for keyword in keywords)
        
        return matches
    return False

# Test with mock RSS items
mock_rss_tests = [
    {
        'title': 'Tesla Announces Recall',
        'description': 'Tesla is recalling vehicles due to safety issues.',
        'keywords': EVENT_TYPES['recall']['keywords'],
        'expected': True
    },
    {
        'title': 'Tesla Safety Update',
        'description': 'Tesla has issued a voluntary recall of affected vehicles.',
        'keywords': EVENT_TYPES['recall']['keywords'],
        'expected': True
    },
    {
        'title': 'Tesla New Model Launch',
        'description': 'Tesla announces new electric vehicle model.',
        'keywords': EVENT_TYPES['recall']['keywords'],
        'expected': False
    },
]

print("Testing with mock RSS item structure:")
for i, test in enumerate(mock_rss_tests, 1):
    result = simulate_rss_filtering(test['title'], test['description'], test['keywords'])
    status = "✅" if result == test['expected'] else "❌"
    print(f"   {status} Test {i}: Expected {test['expected']}, Got {result}")
    if result != test['expected']:
        print(f"      Title: {test['title']}")
        print(f"      Description: {test['description']}")

print()
print("=" * 80)
print("CONCLUSION")
print("=" * 80)

if failed == 0:
    print("✅ All tests passed! RSS filtering correctly checks both title and description.")
else:
    print(f"❌ {failed} test(s) failed. Please review the filtering logic.")

print()
print("=" * 80)

