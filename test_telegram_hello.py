#!/usr/bin/env python3
"""
Unit test: Send a hello message via Telegram
This test verifies that we can send messages to Telegram successfully.
"""

import requests

# Telegram Bot Configuration (hardcoded as requested)
BOT_TOKEN = "8390056981:AAF2-lH9I2NV3t94qz5Ss3lvKTds5j3iJzQ"
CHAT_ID = "8363966707"

def send_telegram_message(chat_id, text):
    """
    Send a message via Telegram Bot API
    
    Args:
        chat_id (str): The chat ID to send the message to
        text (str): The message text to send
        
    Returns:
        dict: Response from Telegram API
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'  # Allows HTML formatting in messages
    }
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        
        if not response.ok:
            print(f"HTTP Error {response.status_code}: {response.reason}")
            print(f"Response: {data}")
            
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        return None

def test_send_hello():
    """Test sending a hello message"""
    print("=" * 60)
    print("TELEGRAM HELLO MESSAGE TEST")
    print("=" * 60)
    print(f"Bot Token: {BOT_TOKEN[:20]}...")
    print(f"Chat ID: {CHAT_ID}")
    print()
    
    message = "Hello! 👋\n\nThis is a test message from your LayoffTracker bot!"
    
    print(f"Sending message: '{message}'")
    print()
    
    result = send_telegram_message(CHAT_ID, message)
    
    if result and result.get('ok'):
        print("✓ SUCCESS! Message sent to Telegram!")
        print(f"  Message ID: {result['result']['message_id']}")
        print(f"  Chat ID: {result['result']['chat']['id']}")
        print(f"  Date: {result['result']['date']}")
        print()
        print("Check your Telegram - you should see the message!")
    else:
        print("✗ FAILED to send message")
        if result:
            print(f"  Error: {result.get('description', 'Unknown error')}")
        print()
        print("Please check:")
        print("1. Bot token is correct")
        print("2. Chat ID is correct")
        print("3. You've started a chat with the bot")
    
    print("=" * 60)
    return result

if __name__ == "__main__":
    test_send_hello()
