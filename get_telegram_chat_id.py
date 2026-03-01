#!/usr/bin/env python3
"""
Helper script to get your Telegram Chat ID
Make sure you've started a chat with your bot and sent at least one message first!
"""

import requests
import json

# Bot token from BotFather
BOT_TOKEN = "8390056981:AAF2-lH9I2NV3t94qz5Ss3lvKTds5j3iJzQ"

def get_chat_id():
    """Fetch and display chat ID from Telegram bot updates"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    
    print("Fetching updates from Telegram...")
    print(f"URL: {url}\n")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        print("=" * 60)
        print("FULL RESPONSE:")
        print("=" * 60)
        print(json.dumps(data, indent=2))
        print("\n")
        
        if data.get('ok') and data.get('result'):
            if len(data['result']) > 0:
                print("=" * 60)
                print("FOUND CHAT IDs:")
                print("=" * 60)
                
                chat_ids = set()
                for update in data['result']:
                    if 'message' in update:
                        chat_id = update['message']['chat']['id']
                        chat_ids.add(chat_id)
                        print(f"Chat ID: {chat_id}")
                        print(f"From: {update['message']['chat'].get('first_name', 'N/A')} {update['message']['chat'].get('last_name', '')}")
                        print(f"Username: @{update['message']['chat'].get('username', 'N/A')}")
                        print(f"Message: {update['message'].get('text', 'N/A')}")
                        print("-" * 60)
                
                print("\n" + "=" * 60)
                print("YOUR CHAT ID(s):")
                print("=" * 60)
                for chat_id in chat_ids:
                    print(f"  {chat_id}")
                print("=" * 60)
                print("\nCopy one of these Chat IDs to use in your test!")
                
            else:
                print("=" * 60)
                print("NO MESSAGES FOUND!")
                print("=" * 60)
                print("\nPlease:")
                print("1. Go to: https://t.me/MarketEventAnalytics_bot")
                print("2. Click 'START' or send any message")
                print("3. Run this script again")
        else:
            print("ERROR: Invalid response from Telegram")
            print(f"Response: {data}")
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to connect to Telegram API")
        print(f"Details: {e}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    get_chat_id()
