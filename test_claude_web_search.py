#!/usr/bin/env python3
"""
Unit test to verify if Claude API supports web_search tool
Tests if we can enable web search in Claude API calls
"""

import sys
import os
import requests
import json
from datetime import datetime, timezone
from main import LayoffTracker

def test_claude_web_search_tool():
    """Test if Claude API supports web_search tool"""
    print("=" * 80)
    print("CLAUDE API WEB SEARCH TOOL TEST")
    print("=" * 80)
    print()
    
    tracker = LayoffTracker()
    
    if not tracker.claude_api_key:
        print("❌ Claude API key not available")
        return False
    
    print("✅ Claude API key found")
    print(f"   API URL: {tracker.claude_api_url}")
    print()
    
    # Test case: HUM drop on Dec 16, 2025 (known to have news)
    test_prompt = """Search the web to find specific news about why Humana Inc (HUM) stock dropped 6.2% on December 16, 2025. 
Look for:
- Analyst downgrades, price target cuts, or upgrades
- Leadership changes, executive departures
- Earnings reports or guidance changes
- Company-specific news or press releases

Provide a summary of the news that caused the drop."""
    
    # Test different API versions and models
    # Based on error message, the correct tool name is 'web_search_20250305' and needs a 'name' field
    # Note: claude-3-haiku-20240307 does NOT support web_search_20250305
    # Testing newer models including potential "Claude 4.5" models
    test_configs = [
        {
            'name': 'claude-haiku-4-5 with web_search_20250305',
            'model': 'claude-haiku-4-5',
            'version': '2023-06-01',
            'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}]
        },
        {
            'name': 'claude-3-5-haiku-20250514 (Haiku 4.5 - latest) with web_search_20250305',
            'model': 'claude-3-5-haiku-20250514',
            'version': '2023-06-01',
            'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}]
        },
        {
            'name': 'claude-3-5-haiku-20250117 (newer date) with web_search_20250305',
            'model': 'claude-3-5-haiku-20250117',
            'version': '2023-06-01',
            'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}]
        },
        {
            'name': 'claude-3-5-haiku-20250219 (newer date) with web_search_20250305',
            'model': 'claude-3-5-haiku-20250219',
            'version': '2023-06-01',
            'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}]
        },
        {
            'name': 'claude-3-5-haiku-20250402 (newer date) with web_search_20250305',
            'model': 'claude-3-5-haiku-20250402',
            'version': '2023-06-01',
            'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}]
        },
        {
            'name': 'claude-3-5-haiku-20250501 (newer date) with web_search_20250305',
            'model': 'claude-3-5-haiku-20250501',
            'version': '2023-06-01',
            'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}]
        },
        {
            'name': 'claude-3-5-sonnet-20241022 with web_search_20250305',
            'model': 'claude-3-5-sonnet-20241022',
            'version': '2023-06-01',
            'tools': [{'type': 'web_search_20250305', 'name': 'web_search'}]
        },
        {
            'name': 'claude-3-haiku-20240307 without web_search (baseline)',
            'model': 'claude-3-haiku-20240307',
            'version': '2023-06-01',
            'tools': None  # No tools for baseline
        }
    ]
    
    results = []
    
    for config in test_configs:
        print(f"Testing: {config['name']}")
        print("-" * 80)
        
        try:
            headers = {
                'x-api-key': tracker.claude_api_key,
                'anthropic-version': config['version'],
                'content-type': 'application/json'
            }
            
            payload = {
                'model': config['model'],
                'max_tokens': 500,
                'messages': [
                    {
                        'role': 'user',
                        'content': test_prompt
                    }
                ]
            }
            
            # Add tools if specified
            if config['tools']:
                payload['tools'] = config['tools']
                print(f"   ✅ Added web_search tool to payload")
            else:
                print(f"   ⚪ No tools (baseline test)")
            
            print(f"   📡 Calling Claude API...")
            print(f"   Model: {config['model']}")
            print(f"   Version: {config['version']}")
            
            response = requests.post(
                tracker.claude_api_url,
                headers=headers,
                json=payload,
                timeout=60,
                verify=False
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Debug: Print full response structure
                print(f"   📋 Full response structure:")
                print(f"   {json.dumps(data, indent=2)[:500]}...")
                print()
                
                # Check if response contains tool use
                content = data.get('content', [])
                if content:
                    # Check if Claude used the web_search tool
                    tool_use_detected = False
                    tool_details = []
                    search_query = None
                    search_results = None
                    
                    for item in content:
                        # Check for server_tool_use (Claude requesting to use tool)
                        if item.get('type') == 'server_tool_use' or item.get('type') == 'tool_use':
                            tool_use_detected = True
                            tool_name = item.get('name', 'unknown')
                            tool_id = item.get('id', 'unknown')
                            tool_input = item.get('input', {})
                            if isinstance(tool_input, dict):
                                search_query = tool_input.get('query', '')
                            print(f"   ✅ Claude used a tool: {tool_name} (id: {tool_id})")
                            if search_query:
                                print(f"   🔍 Search query: {search_query}")
                            tool_details.append(item)
                        
                        # Check for web_search_tool_result (search results returned)
                        if item.get('type') == 'web_search_tool_result':
                            search_results = item.get('content', [])
                            print(f"   ✅ Web search results received: {len(search_results)} items")
                            # Show first result preview
                            if search_results and len(search_results) > 0:
                                first_result = search_results[0]
                                if isinstance(first_result, dict):
                                    title = first_result.get('title', 'No title')
                                    snippet = first_result.get('snippet', 'No snippet')[:100]
                                    print(f"   📰 First result: {title[:60]}...")
                                    print(f"      Snippet: {snippet}...")
                    
                    # Check for stop_reason indicating tool use
                    stop_reason = data.get('stop_reason', '')
                    if stop_reason == 'tool_use' or stop_reason == 'end_turn':
                        print(f"   ✅ Stop reason: {stop_reason}")
                    
                    # Get the text response (if any)
                    text_content = None
                    for item in content:
                        if item.get('type') == 'text':
                            text_content = item.get('text', '')
                    
                    # If we have search results but no text, we need to make a follow-up call
                    if tool_use_detected and search_results and not text_content:
                        print(f"   ⚠️  Tool was used and results received, but no text response yet")
                        print(f"   💡 This is normal - you may need to make a follow-up API call")
                        print(f"      to get Claude's analysis of the search results")
                    
                    if text_content:
                        print(f"   ✅ Claude responded with text")
                        print(f"   Response length: {len(text_content)} characters")
                        print()
                        print("   Response preview (first 300 chars):")
                        print("   " + "-" * 70)
                        print(f"   {text_content[:300]}...")
                        print("   " + "-" * 70)
                        print()
                        
                        # Check if response mentions specific news
                        text_lower = text_content.lower()
                        expected_keywords = ['analyst', 'target', 'cut', 'leadership', 'president', 'humana', 'truist', 'goldman']
                        found_keywords = [kw for kw in expected_keywords if kw in text_lower]
                        
                        print(f"   Keyword Analysis:")
                        if found_keywords:
                            print(f"   ✅ Found keywords: {', '.join(found_keywords)}")
                        missing = [kw for kw in expected_keywords if kw not in text_lower]
                        if missing:
                            print(f"   ⚠️  Missing keywords: {', '.join(missing)}")
                        
                        # Check if it says it couldn't find news
                        if 'could not find' in text_lower or 'no news' in text_lower or 'no specific news' in text_lower:
                            print(f"   ⚠️  Claude says it couldn't find specific news")
                        else:
                            print(f"   ✅ Claude appears to have found information")
                        
                        results.append({
                            'config': config['name'],
                            'success': True,
                            'tool_used': tool_use_detected,
                            'found_keywords': found_keywords,
                            'response_length': len(text_content),
                            'mentions_no_news': 'could not find' in text_lower or 'no news' in text_lower
                        })
                    else:
                        print(f"   ⚠️  No text content in response")
                        print(f"   Full response: {json.dumps(data, indent=2)[:500]}")
                        results.append({
                            'config': config['name'],
                            'success': True,
                            'tool_used': tool_use_detected,
                            'error': 'No text content'
                        })
                else:
                    print(f"   ⚠️  No content in response")
                    print(f"   Full response: {json.dumps(data, indent=2)[:500]}")
                    results.append({
                        'config': config['name'],
                        'success': True,
                        'error': 'No content in response'
                    })
                    
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                print(f"   ❌ Bad Request (400)")
                print(f"   Error: {error_msg}")
                
                # Check for specific error messages
                if 'tool' in error_msg.lower() or 'web_search' in error_msg.lower():
                    print(f"   ⚠️  This suggests web_search tool is not supported")
                if 'model' in error_msg.lower() or 'version' in error_msg.lower():
                    print(f"   ⚠️  This suggests model/version issue")
                if 'upgrade' in error_msg.lower() or 'plan' in error_msg.lower():
                    print(f"   ⚠️  This suggests you may need to upgrade your API plan")
                
                results.append({
                    'config': config['name'],
                    'success': False,
                    'error': error_msg,
                    'status_code': 400
                })
                
            elif response.status_code == 401:
                print(f"   ❌ Unauthorized (401) - Invalid API key")
                results.append({
                    'config': config['name'],
                    'success': False,
                    'error': 'Invalid API key',
                    'status_code': 401
                })
                
            elif response.status_code == 429:
                print(f"   ❌ Rate Limited (429)")
                results.append({
                    'config': config['name'],
                    'success': False,
                    'error': 'Rate limited',
                    'status_code': 429
                })
                
            else:
                print(f"   ❌ Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                results.append({
                    'config': config['name'],
                    'success': False,
                    'error': f'Status {response.status_code}',
                    'status_code': response.status_code
                })
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'config': config['name'],
                'success': False,
                'error': str(e)
            })
        
        print()
        print("=" * 80)
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    for result in results:
        config_name = result['config']
        if result.get('success'):
            status = "✅"
            tool_info = ""
            if result.get('tool_used'):
                tool_info = " (tool used)"
            elif 'web_search' in config_name.lower():
                tool_info = " (tool may not have been used)"
            
            keyword_info = ""
            if result.get('found_keywords'):
                keyword_info = f" - Found: {', '.join(result['found_keywords'])}"
            
            no_news_warning = ""
            if result.get('mentions_no_news'):
                no_news_warning = " ⚠️ (says couldn't find news)"
            
            print(f"{status} {config_name}{tool_info}{keyword_info}{no_news_warning}")
        else:
            status = "❌"
            error = result.get('error', 'Unknown error')
            print(f"{status} {config_name}: {error}")
    
    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    # Check if any config worked with web_search
    web_search_configs = [r for r in results if 'web_search' in r['config'].lower() and r.get('success')]
    if web_search_configs:
        print("✅ Web search tool appears to be supported!")
        working_config = web_search_configs[0]
        print(f"   Working configuration: {working_config['config']}")
        if working_config.get('tool_used'):
            print("   ✅ Claude actually used the web_search tool")
        else:
            print("   ⚠️  Tool was added but may not have been used")
    else:
        print("❌ Web search tool does not appear to be supported")
        print("   Possible reasons:")
        print("   - Your API plan doesn't include web search")
        print("   - The model doesn't support web search")
        print("   - The API version doesn't support tools")
        print("   - You may need to upgrade your Anthropic API plan")
    
    # Check if any found the specific news
    found_news_configs = [r for r in results if r.get('success') and not r.get('mentions_no_news') and r.get('found_keywords')]
    if found_news_configs:
        print()
        print("✅ Some configurations found news!")
        for config in found_news_configs:
            print(f"   - {config['config']}: Found {len(config['found_keywords'])} keywords")
    
    return len([r for r in results if r.get('success')]) > 0

if __name__ == "__main__":
    success = test_claude_web_search_tool()
    sys.exit(0 if success else 1)

