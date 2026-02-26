#!/usr/bin/env python3
"""
Production Telegram Webhook Setup Script
Sets the Telegram webhook to the production domain/IP.
"""
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.telegram import telegram_bot
from src.config import settings


def get_public_url():
    """
    Get the public URL from environment or detect it.
    
    Returns:
        str: The public URL or None if not configured
    """
    # Try to get from environment
    public_url = os.getenv("PUBLIC_URL") or os.getenv("DOMAIN_NAME")
    
    if public_url:
        # Ensure it has https://
        if not public_url.startswith("http"):
            public_url = f"https://{public_url}"
        return public_url
    
    # Try to get server IP
    try:
        import socket
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        
        # Use HTTP for IP addresses (HTTPS requires valid cert)
        return f"http://{ip}:8000"
    except Exception:
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
    print("  🚀 Production Telegram Webhook Setup")
    print("════════════════════════════════════════════════════════")
    print()
    
    # Check if Telegram bot token is configured
    if not settings.telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not configured in .env")
        print("   Please add your bot token and restart")
        sys.exit(1)
    
    print("✅ Telegram bot token configured")
    print()
    
    # Get public URL
    public_url = get_public_url()
    
    if not public_url:
        print("❌ Could not determine public URL")
        print()
        print("Please set one of these environment variables:")
        print("  PUBLIC_URL=https://yourdomain.com")
        print("  DOMAIN_NAME=yourdomain.com")
        print()
        print("Or run with:")
        print("  PUBLIC_URL=https://yourdomain.com python scripts/setup-webhook-production.py")
        print()
        sys.exit(1)
    
    print(f"🌐 Public URL: {public_url}")
    print()
    
    # Build webhook URL
    webhook_url = f"{public_url}/telegram-webhook"
    
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

