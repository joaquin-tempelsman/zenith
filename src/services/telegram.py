"""
Telegram Bot API wrapper for sending messages and handling webhooks.
"""
import httpx
from typing import Dict, Any, Optional
from ..config import settings


class TelegramBot:
    """
    Telegram Bot API client for sending messages and interacting with users.
    
    Attributes:
        bot_token: Telegram bot token from BotFather
        base_url: Base URL for Telegram Bot API
    """
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize the Telegram Bot client.
        
        Args:
            bot_token: Optional bot token. If not provided, uses settings.telegram_bot_token
        """
        self.bot_token = bot_token or settings.telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """
        Send a text message to a chat.
        
        Args:
            chat_id: Unique identifier for the target chat
            text: Text of the message to send
            parse_mode: Mode for parsing entities in the message text
            
        Returns:
            Response from Telegram API as dictionary
        """
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        with httpx.Client() as client:
            response = client.post(url, json=payload)
            return response.json()
    
    async def send_message_async(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """
        Async version of send_message.
        
        Args:
            chat_id: Unique identifier for the target chat
            text: Text of the message to send
            parse_mode: Mode for parsing entities in the message text
            
        Returns:
            Response from Telegram API as dictionary
        """
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    def get_file(self, file_id: str) -> Dict[str, Any]:
        """
        Get basic info about a file and prepare it for downloading.
        
        Args:
            file_id: File identifier to get info about
            
        Returns:
            File information from Telegram API
        """
        url = f"{self.base_url}/getFile"
        payload = {"file_id": file_id}
        
        with httpx.Client() as client:
            response = client.post(url, json=payload)
            return response.json()
    
    async def get_file_async(self, file_id: str) -> Dict[str, Any]:
        """
        Async version of get_file.
        
        Args:
            file_id: File identifier to get info about
            
        Returns:
            File information from Telegram API
        """
        url = f"{self.base_url}/getFile"
        payload = {"file_id": file_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    def download_file(self, file_path: str, destination: str) -> bool:
        """
        Download a file from Telegram servers.
        
        Args:
            file_path: File path returned by getFile method
            destination: Local path where to save the file
            
        Returns:
            True if download successful, False otherwise
        """
        url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        
        try:
            with httpx.Client() as client:
                response = client.get(url)
                response.raise_for_status()
                
                with open(destination, "wb") as f:
                    f.write(response.content)
                return True
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False
    
    async def download_file_async(self, file_path: str, destination: str) -> bool:
        """
        Async version of download_file.
        
        Args:
            file_path: File path returned by getFile method
            destination: Local path where to save the file
            
        Returns:
            True if download successful, False otherwise
        """
        url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                
                with open(destination, "wb") as f:
                    f.write(response.content)
                return True
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False
    
    def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """
        Set the webhook URL for receiving updates.
        
        Args:
            webhook_url: HTTPS url to send updates to
            
        Returns:
            Response from Telegram API
        """
        url = f"{self.base_url}/setWebhook"
        payload = {"url": webhook_url}
        
        with httpx.Client() as client:
            response = client.post(url, json=payload)
            return response.json()
    
    def delete_webhook(self) -> Dict[str, Any]:
        """
        Remove webhook integration.
        
        Returns:
            Response from Telegram API
        """
        url = f"{self.base_url}/deleteWebhook"
        
        with httpx.Client() as client:
            response = client.post(url)
            return response.json()
    
    def get_webhook_info(self) -> Dict[str, Any]:
        """
        Get current webhook status.
        
        Returns:
            Webhook information from Telegram API
        """
        url = f"{self.base_url}/getWebhookInfo"
        
        with httpx.Client() as client:
            response = client.get(url)
            return response.json()


# Create a global bot instance
telegram_bot = TelegramBot()
