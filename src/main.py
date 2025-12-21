"""
FastAPI application entry point.
Handles Telegram webhook for voice and text-based inventory management.
"""
import os
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .config import settings
from .database.models import init_db, get_db
from .database import crud
from .services.ai_processor import transcribe_audio
from .services.telegram import telegram_bot
from .services.agent import run_inventory_agent
from .models import AgentConfig

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


async def _process_telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Core webhook processing logic for Telegram messages.

    Workflow:
    1. Receive Telegram payload (voice or text)
    2. If voice: Download audio -> Transcribe with Whisper
    3. If text: Use text directly
    4. Process with LangChain agent (parse_intent -> modify_db/query_db)
    5. Reply to user via Telegram

    Args:
        request: FastAPI request object containing Telegram update
        db: Database session dependency

    Returns:
        JSON response with processing status
    """
    try:
        payload = await request.json()
        print(f"📨 Received webhook payload: {payload}")

        if "message" not in payload:
            print("⚠️ No message in payload, skipping")
            return JSONResponse({"ok": True})

        message = payload["message"]
        chat_id = message["chat"]["id"]
        print(f"💬 Processing message for chat_id: {chat_id}")

        text_input = None

        if "voice" in message:
            try:
                voice = message["voice"]
                file_id = voice["file_id"]

                file_info = await telegram_bot.get_file_async(file_id)

                if not file_info.get("ok"):
                    raise Exception("Failed to get file info from Telegram")

                file_path = file_info["result"]["file_path"]

                temp_dir = Path(tempfile.gettempdir()) / "inventory_audio"
                temp_dir.mkdir(exist_ok=True)

                audio_file_path = temp_dir / f"{file_id}.ogg"
                download_success = await telegram_bot.download_file_async(
                    file_path, str(audio_file_path)
                )

                if not download_success:
                    raise Exception("Failed to download audio file")

                text_input = transcribe_audio(str(audio_file_path))

                try:
                    os.remove(audio_file_path)
                except Exception:
                    pass

            except Exception as e:
                error_msg = f"❌ Error processing voice message: {str(e)}"
                await telegram_bot.send_message_async(chat_id, error_msg)
                return JSONResponse(
                    {"status": "error", "error": str(e), "type": "voice_processing"}
                )

        elif "text" in message:
            text_input = message["text"]
            print(f"📝 Received text message: {text_input}")

        else:
            print("❌ No text or voice in message")
            await telegram_bot.send_message_async(
                chat_id, "❌ Please send either a text or voice message."
            )
            return JSONResponse({"ok": True})

        try:
            print(f"🤖 Processing with agent: {text_input}")
            result = run_inventory_agent(text_input, db)
            response_message = result.get("response_message", "")
            print(f"✅ Agent response: {response_message}")

            if not response_message:
                response_message = "❌ I couldn't process your request. Please try again."

            print(f"📤 Sending response to chat_id {chat_id}: {response_message}")
            await telegram_bot.send_message_async(chat_id, response_message)
            print("✅ Response sent successfully")
            return JSONResponse({"ok": True})

        except Exception as e:
            error_msg = f"❌ Error processing request: {str(e)}"
            print(f"🚨 Agent processing error: {str(e)}")
            await telegram_bot.send_message_async(chat_id, error_msg)
            return JSONResponse(
                {"status": "error", "error": str(e), "type": "agent_processing"}
            )

    except Exception as e:
        print(f"🚨 Webhook processing error: {str(e)}")
        return JSONResponse({"ok": True}, status_code=200)


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Telegram webhook endpoint to receive and process messages.
    """
    return await _process_telegram_webhook(request, db)


@app.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """
    Alternative webhook endpoint (alias for /telegram-webhook).
    """
    return await _process_telegram_webhook(request, db)


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


# ============================================================================
# NEW: LangGraph 1.0 Agent Endpoints
# ============================================================================


@app.post("/agent/process")
async def agent_process(user_input: str, db: Session = Depends(get_db)):
    """
    Process user input using the LangChain 1.0 inventory agent.

    This endpoint uses the new agent system with:
    - OpenAI API integration via LangChain create_agent
    - Tools: parse_intent, modify_db, query_db
    - Pydantic input validation

    Args:
        user_input: User's text input (or transcribed audio)
        db: Database session dependency

    Returns:
        JSON response with agent response and metadata
    """
    try:
        result = run_inventory_agent(user_input, db)
        return {
            "status": result.get("result", "success"),
            "response": result.get("response_message", ""),
            "tools_used": result.get("tools_used", []),
            "metadata": result.get("metadata", {}),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "response": "❌ Error processing request with agent",
        }


@app.post("/agent/voice")
async def agent_voice(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Process voice input using the LangGraph 1.0 inventory agent.
    
    Workflow:
    1. Extract voice message from Telegram payload
    2. Download and transcribe audio
    3. Pass transcribed text to agent
    4. Return agent response
    
    Args:
        request: FastAPI request containing Telegram update
        db: Database session dependency
        
    Returns:
        JSON response with agent processing result
    """
    try:
        payload = await request.json()
        
        if "message" not in payload or "voice" not in payload["message"]:
            return {
                "status": "error",
                "error": "No voice message in payload"
            }
        
        message = payload["message"]
        file_id = message["voice"]["file_id"]
        
        # Get file info from Telegram
        file_info = await telegram_bot.get_file_async(file_id)
        if not file_info.get("ok"):
            return {
                "status": "error",
                "error": "Failed to get file info from Telegram"
            }
        
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
            return {
                "status": "error",
                "error": "Failed to download audio file"
            }
        
        # Transcribe audio to text
        transcribed_text = transcribe_audio(str(audio_file_path))

        # Clean up audio file
        try:
            os.remove(audio_file_path)
        except Exception:
            pass

        # Process with agent
        result = run_inventory_agent(transcribed_text, db)

        return {
            "status": result.get("result", "success"),
            "transcribed_text": transcribed_text,
            "response": result.get("response_message", ""),
            "tools_used": result.get("tools_used", []),
            "metadata": result.get("metadata", {}),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "response": "❌ Error processing voice with agent",
        }


@app.get("/agent/health")
async def agent_health():
    """
    Check agent system health and configuration.

    Returns:
        JSON response with agent status
    """
    try:
        from .services.agent import create_inventory_agent

        agent = create_inventory_agent()

        return {
            "status": "healthy",
            "agent_type": "LangChain 1.0",
            "model": "OpenAI gpt-4o-mini",
            "tools": ["parse_intent", "modify_db", "query_db"],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_type": "LangChain 1.0",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app", host=settings.app_host, port=settings.app_port, reload=True
    )
