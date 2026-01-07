#!/usr/bin/env python3
"""
Automatic Telegram Webhook Setup Script
Waits for ngrok to be ready, gets the public URL, and sets the Telegram webhook.
"""
import os
import sys
import time
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.telegram import telegram_bot
from src.config import settings


def get_ngrok_url(max_retries=30, retry_delay=2):
    """
    Get the ngrok public URL from the ngrok API.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        str: The ngrok HTTPS URL or None if failed
    """
    print("🔍 Waiting for ngrok to be ready...")
    
    for attempt in range(max_retries):
        try:
            # Try to connect to ngrok API
            response = requests.get("http://ngrok:4040/api/tunnels", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get("tunnels", [])
                
                # Find the HTTPS tunnel
                for tunnel in tunnels:
                    if tunnel.get("proto") == "https":
                        url = tunnel.get("public_url")
                        if url:
                            print(f"✅ Found ngrok URL: {url}")
                            return url
                
                print(f"⚠️  No HTTPS tunnel found (attempt {attempt + 1}/{max_retries})")
            else:
                print(f"⚠️  ngrok API returned status {response.status_code} (attempt {attempt + 1}/{max_retries})")
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Waiting for ngrok... (attempt {attempt + 1}/{max_retries})")
        
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    return None


def set_telegram_webhook(webhook_url):
    """
    Set the Telegram webhook URL.
    
    Args:
        webhook_url: The webhook URL to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"📨 Setting Telegram webhook to: {webhook_url}")
    
    try:
        response = telegram_bot.set_webhook(webhook_url)
        
        if response.get("ok"):
            print("✅ Telegram webhook set successfully!")
            
            # Get and display webhook info
            webhook_info = telegram_bot.get_webhook_info()
            if webhook_info.get("ok"):
                result = webhook_info.get("result", {})
                print(f"   URL: {result.get('url')}")
                print(f"   Pending updates: {result.get('pending_update_count', 0)}")
            
            return True
        else:
            error_desc = response.get("description", "Unknown error")
            print(f"❌ Failed to set webhook: {error_desc}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting webhook: {str(e)}")
        return False


def main():
    """Main function to set up the webhook."""
    print("════════════════════════════════════════════════════════")
    print("  🤖 Automatic Telegram Webhook Setup")
    print("════════════════════════════════════════════════════════")
    print()
    
    # Check if Telegram bot token is configured
    if not settings.telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not configured in .env")
        print("   Please add your bot token and restart")
        sys.exit(1)
    
    print("✅ Telegram bot token configured")
    print()
    
    # Get ngrok URL
    ngrok_url = get_ngrok_url()
    
    if not ngrok_url:
        print()
        print("❌ Failed to get ngrok URL")
        print("   Make sure ngrok container is running")
        sys.exit(1)
    
    print()
    
    # Build webhook URL
    webhook_url = f"{ngrok_url}/telegram-webhook"
    
    # Set the webhook
    success = set_telegram_webhook(webhook_url)
    
    print()
    print("════════════════════════════════════════════════════════")
    
    if success:
        print("  ✅ Webhook Setup Complete!")
        print("════════════════════════════════════════════════════════")
        print()
        print("🎉 Your Telegram bot is ready to receive messages!")
        print()
        print(f"📱 Send a message to your bot to test it")
        print(f"🌐 ngrok URL: {ngrok_url}")
        print(f"📊 ngrok dashboard: http://localhost:4040")
        print()
        sys.exit(0)
    else:
        print("  ❌ Webhook Setup Failed")
        print("════════════════════════════════════════════════════════")
        print()
        print("Please check the error messages above and try again")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()

