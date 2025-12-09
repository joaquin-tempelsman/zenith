"""
FastAPI application entry point.
Handles Telegram webhook for voice and text-based inventory management.
"""
import os
import tempfile
from datetime import datetime, date
from typing import Dict, Any
from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .config import settings
from .database.models import init_db, get_db, Item
from .database import crud
from .services.ai_processor import (
    transcribe_audio, 
    parse_intent, 
    parse_intent_async, 
    generate_response_message,
    route_action
)
from .services.telegram import telegram_bot

# Initialize FastAPI app
app = FastAPI(
    title="Voice-Managed Inventory System",
    description="FastAPI backend for managing inventory via Telegram bot",
    version="1.0.0"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on application startup."""
    init_db()
    print("✅ Database initialized successfully")
    print(f"📱 Telegram Bot Token configured: {bool(settings.telegram_bot_token)}")
    print(f"🤖 OpenAI API Key configured: {bool(settings.openai_api_key)}")


@app.get("/")
async def root():
    """
    Root endpoint for health check.
    
    Returns:
        JSON response with API status
    """
    return {
        "status": "online",
        "service": "Voice-Managed Inventory System",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "/telegram-webhook",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON response with system health status
    """
    return {
        "status": "healthy",
        "database": "connected",
        "telegram_configured": bool(settings.telegram_bot_token),
        "openai_configured": bool(settings.openai_api_key),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Telegram webhook endpoint to receive and process messages.
    
    Workflow:
    1. Receive Telegram payload (voice or text)
    2. If voice: Download audio -> Transcribe with Whisper
    3. If text: Use text directly
    4. Parse intent using GPT (structured JSON)
    5. Execute database operation via CRUD
    6. Reply to user via Telegram
    
    Args:
        request: FastAPI request object containing Telegram update
        db: Database session dependency
        
    Returns:
        JSON response with processing status
    """
    try:
        # Parse incoming Telegram update
        payload = await request.json()
        
        # Extract message data
        if "message" not in payload:
            return JSONResponse({"status": "ignored", "reason": "no_message"})
        
        message = payload["message"]
        chat_id = message["chat"]["id"]
        
        # Initialize variables
        text_input = None
        
        # Check if it's a voice message
        if "voice" in message:
            try:
                voice = message["voice"]
                file_id = voice["file_id"]
                
                # Get file info from Telegram
                file_info = await telegram_bot.get_file_async(file_id)
                
                if not file_info.get("ok"):
                    raise Exception("Failed to get file info from Telegram")
                
                file_path = file_info["result"]["file_path"]
                
                # Create temporary directory for audio files
                temp_dir = Path(tempfile.gettempdir()) / "inventory_audio"
                temp_dir.mkdir(exist_ok=True)
                
                # Download audio file
                audio_file_path = temp_dir / f"{file_id}.ogg"
                download_success = await telegram_bot.download_file_async(
                    file_path, 
                    str(audio_file_path)
                )
                
                if not download_success:
                    raise Exception("Failed to download audio file")
                
                # Transcribe audio to text
                text_input = await transcribe_audio(str(audio_file_path))
                
                # Clean up audio file
                try:
                    os.remove(audio_file_path)
                except Exception:
                    pass
                    
            except Exception as e:
                error_msg = f"❌ Error processing voice message: {str(e)}"
                await telegram_bot.send_message_async(chat_id, error_msg)
                return JSONResponse({
                    "status": "error",
                    "error": str(e),
                    "type": "voice_processing"
                })
        
        # Check if it's a text message
        elif "text" in message:
            text_input = message["text"]
        
        else:
            # Unsupported message type
            await telegram_bot.send_message_async(
                chat_id,
                "❌ Please send either a text or voice message."
            )
            return JSONResponse({"status": "ignored", "reason": "unsupported_type"})
        
        # Parse intent from text
        intent = await parse_intent_async(text_input)
        
        if intent.get("action_type") == "unknown":
            error_msg = "❌ I couldn't understand your request. Please try again."
            if "error" in intent:
                error_msg += f"\n\nDetails: {intent['error']}"
            await telegram_bot.send_message_async(chat_id, error_msg)
            return JSONResponse({"status": "error", "reason": "unknown_intent", "intent": intent})
        
        # Route to appropriate action handler
        try:
            result = route_action(intent, db)
        except Exception as e:
            error_msg = f"❌ Database error: {str(e)}"
            await telegram_bot.send_message_async(chat_id, error_msg)
            return JSONResponse({
                "status": "error",
                "error": str(e),
                "type": "database"
            })
        
        # Generate and send response message
        response_message = generate_response_message(intent, result)
        await telegram_bot.send_message_async(chat_id, response_message)
        
        return JSONResponse({
            "status": "success",
            "action_type": intent.get("action_type"),
            "intent": intent,
            "response": response_message
        })
    
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e),
            "type": "general"
        }, status_code=500)


@app.get("/webhook-info")
async def webhook_info():
    """
    Get current Telegram webhook configuration.
    
    Returns:
        JSON response with webhook status
    """
    try:
        info = telegram_bot.get_webhook_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set-webhook")
async def set_webhook(webhook_url: str):
    """
    Set Telegram webhook URL.
    
    Args:
        webhook_url: HTTPS URL for receiving updates
        
    Returns:
        JSON response with operation status
    """
    try:
        result = telegram_bot.set_webhook(webhook_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Additional inventory management endpoints
@app.get("/inventory")
async def get_inventory(db: Session = Depends(get_db)):
    """
    Get all inventory items.
    
    Args:
        db: Database session dependency
        
    Returns:
        JSON response with all items
    """
    items = crud.get_all_items(db)
    return {
        "items": [item.to_dict() for item in items],
        "count": len(items)
    }


@app.get("/inventory/summary")
async def get_inventory_summary(db: Session = Depends(get_db)):
    """
    Get inventory summary statistics.
    
    Args:
        db: Database session dependency
        
    Returns:
        JSON response with summary data
    """
    summary = crud.get_inventory_summary(db)
    return summary


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True
    )
