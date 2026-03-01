#!/usr/bin/env python3
"""
Test sending a hello message via Telegram
Since we can't get the chat ID from getUpdates, we'll try a different approach.
"""

import requests

BOT_TOKEN = "8390056981:AAF2-lH9I2NV3t94qz5Ss3lvKTds5j3iJzQ"

# We'll try to send to common chat ID formats
# Usually user chat IDs are positive integers

def send_message(chat_id, text):
    """Send a message to a specific chat ID"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        
        if data.get('ok'):
            print(f"✓ Message sent successfully to chat_id: {chat_id}")
            return True
        else:
            print(f"✗ Failed to send to chat_id {chat_id}: {data.get('description')}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("PLEASE ENTER YOUR TELEGRAM CHAT ID:")
    print("(You can find it by searching for @userinfobot in Telegram and sending /start)")
    print()
    chat_id = input("Enter your chat ID: ").strip()
    
    if chat_id:
        print(f"\nAttempting to send 'Hello from LayoffTracker!' to chat ID: {chat_id}")
        send_message(chat_id, "Hello from LayoffTracker! 🚀\n\nThis is a test message from your Python bot.")
    else:
        print("No chat ID provided.")
