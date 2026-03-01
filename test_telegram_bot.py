#!/usr/bin/env python3
"""
Test script to verify Telegram bot is working
"""

import requests

BOT_TOKEN = "8390056981:AAF2-lH9I2NV3t94qz5Ss3lvKTds5j3iJzQ"

def test_bot():
    """Test if bot token is valid"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    
    print("Testing bot token...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data.get('ok'):
            print("✓ Bot token is VALID!")
            print(f"  Bot name: {data['result'].get('first_name')}")
            print(f"  Bot username: @{data['result'].get('username')}")
            print(f"  Bot ID: {data['result'].get('id')}")
        else:
            print("✗ Bot token is INVALID")
            print(f"  Error: {data}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*60)
    print("Checking for updates...")
    print("="*60)
    
    url2 = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url2)
        data = response.json()
        
        print(f"Response OK: {data.get('ok')}")
        print(f"Number of updates: {len(data.get('result', []))}")
        
        if data.get('result'):
            print("\nMessages found:")
            for update in data['result']:
                if 'message' in update:
                    print(f"  Chat ID: {update['message']['chat']['id']}")
                    print(f"  Text: {update['message'].get('text')}")
        else:
            print("\nNo messages found yet.")
            print("\nPossible reasons:")
            print("1. Message was sent to the wrong bot")
            print("2. Bot privacy mode is enabled (check bot settings)")
            print("3. Need to use /start command first")
            print("\nTry this:")
            print("1. Go to @MarketEventAnalytics_bot in Telegram")
            print("2. Type /start and send it")
            print("3. Then send 'hello'")
            print("4. Run this script again")
            
    except Exception as e:
        print(f"Error getting updates: {e}")

if __name__ == "__main__":
    test_bot()
