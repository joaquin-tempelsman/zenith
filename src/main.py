"""
FastAPI application entry point.
Handles Telegram webhook for voice and text-based inventory management.
"""
import asyncio
from datetime import datetime, timezone, date

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from .config import settings
from .database.models import get_session_for_user, get_metadata_session
from .database import crud
from .services.telegram import telegram_bot
from .services.message_handler import extract_message_text, extract_voice_text
from .services.daily_report import generate_daily_report, send_daily_reports
from .agent import run_inventory_agent
from .models import AgentConfig

# Initialize FastAPI app
app = FastAPI(
    title="Voice-Managed Inventory System",
    description="FastAPI backend for managing inventory via Telegram bot",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Log configuration status, run migrations, and start the daily-report scheduler."""
    print(f"📱 Telegram Bot Token configured: {bool(settings.telegram_bot_token)}")
    print(f"🤖 OpenAI API Key configured: {bool(settings.openai_api_key)}")
    print(f"🔑 Admin secret code configured: {bool(settings.admin_secret_code)}")

    # Auto-apply pending Alembic migrations to all per-user databases
    from .database.models import run_migrations
    run_migrations()

    print(f"📊 Daily report scheduled at {settings.daily_report_hour}:00 UTC")
    asyncio.create_task(_daily_report_loop())


async def _daily_report_loop():
    """Background loop that sends the daily admin report once per day.

    Runs indefinitely, sleeping until the configured UTC hour.
    """
    while True:
        now = datetime.now(timezone.utc)
        target_hour = settings.daily_report_hour
        # Calculate seconds until next target_hour
        target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        if now >= target:
            target = target.replace(day=target.day + 1) if target.month == now.month else target
            # Safer: just add 86400 and re-compute
            from datetime import timedelta
            target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        print(f"⏰ Next daily report in {wait_seconds:.0f}s")
        await asyncio.sleep(wait_seconds)
        try:
            await send_daily_reports()
        except Exception as exc:
            print(f"🚨 Daily report error: {exc}")


def get_resolved_session(chat_id: int) -> tuple:
    """Resolve account linking and return the appropriate DB session.

    Checks the shared metadata database for an active account link.  If the
    user is linked to another user's inventory, the returned session points
    to the owner's database.

    Args:
        chat_id: Telegram chat/user ID of the requesting user

    Returns:
        Tuple of (db_session, effective_chat_id, is_linked)
    """
    meta = get_metadata_session()
    try:
        effective = crud.resolve_effective_chat_id(meta, chat_id)
    finally:
        meta.close()
    db = get_session_for_user(effective)
    return db, effective, effective != chat_id


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        JSON response with system health status including
        service name, version, configuration flags, and timestamp
    """
    return {
        "status": "healthy",
        "service": "Voice-Managed Inventory System",
        "version": "1.0.0",
        "telegram_configured": bool(settings.telegram_bot_token),
        "openai_configured": bool(settings.openai_api_key),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _handle_admin_command(chat_id: int, raw_text: str):
    """Handle /admin commands from Telegram users.

    Supported sub-commands:
    - ``/admin <code>``  — authenticate as admin using the admin secret code
    - ``/admin report``  — (admin only) trigger an immediate daily report
    - ``/admin status``  — (admin only) check admin status

    Args:
        chat_id: Telegram chat/user ID
        raw_text: Full text of the message (e.g. ``/admin mysecretcode``)

    Returns:
        JSONResponse to acknowledge the webhook
    """
    parts = raw_text.split(maxsplit=1)
    arg = parts[1].strip() if len(parts) > 1 else ""

    meta = get_metadata_session()
    try:
        already_admin = crud.is_admin(meta, chat_id)

        # /admin (no arg) — show status
        if not arg:
            if already_admin:
                await telegram_bot.send_message_async(
                    chat_id, "✅ You are an admin. Use /admin report to get a report."
                )
            else:
                await telegram_bot.send_message_async(
                    chat_id, "🔑 Usage: /admin <code>"
                )
            return JSONResponse({"ok": True})

        # /admin report — send report now
        if arg.lower() == "report":
            if not already_admin:
                await telegram_bot.send_message_async(chat_id, "🔒 Admin access required.")
                return JSONResponse({"ok": True})
            report = generate_daily_report(date.today())
            await telegram_bot.send_message_async(chat_id, report)
            return JSONResponse({"ok": True})

        # /admin status
        if arg.lower() == "status":
            if already_admin:
                await telegram_bot.send_message_async(chat_id, "✅ You are an admin.")
            else:
                await telegram_bot.send_message_async(chat_id, "❌ You are not an admin.")
            return JSONResponse({"ok": True})

        # /admin <code> — authenticate
        if settings.admin_secret_code and arg == settings.admin_secret_code:
            crud.grant_admin(meta, chat_id)
            await telegram_bot.send_message_async(
                chat_id, "✅ Admin access granted. You will receive daily reports."
            )
        else:
            await telegram_bot.send_message_async(chat_id, "❌ Invalid admin code.")
    finally:
        meta.close()

    return JSONResponse({"ok": True})


async def _process_telegram_webhook(request: Request):
    """
    Core webhook processing logic for Telegram messages.

    Workflow:
    1. Receive Telegram payload (voice or text)
    2. Extract chat_id and open a per-user database session
    3. Extract text via :func:`extract_message_text` (handles voice/text)
    4. Process with LangChain agent
    5. Reply to user via Telegram

    Args:
        request: FastAPI request object containing Telegram update

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

        # ---- Access control gate ----
        if settings.allowed_users_only:
            meta = get_metadata_session()
            try:
                if crud.is_user_authorized(meta, chat_id):
                    pass  # proceed normally
                else:
                    raw_text = message.get("text", "")
                    code = raw_text.strip()

                    # Check for secret code (guard against empty code)
                    if settings.secret_code and code == settings.secret_code:
                        crud.authorize_user(meta, chat_id)
                        await telegram_bot.send_message_async(
                            chat_id, "✅ Acceso concedido / Access granted"
                        )
                        return JSONResponse({"ok": True})

                    if crud.is_user_blocked(meta, chat_id):
                        # Silently ignore — no response
                        return JSONResponse({"ok": True})

                    # Only count actual text (non-command) messages as
                    # failed code attempts.  /start, voice messages, etc.
                    # just get the prompt without burning an attempt.
                    is_code_attempt = bool(code) and not code.startswith("/")
                    if is_code_attempt:
                        attempts = crud.increment_failed_attempts(meta, chat_id)
                        if attempts <= crud.MAX_ACCESS_ATTEMPTS:
                            await telegram_bot.send_message_async(
                                chat_id,
                                "🔒 Por favor proveer código de ingreso / Please provide access code",
                            )
                    else:
                        await telegram_bot.send_message_async(
                            chat_id,
                            "🔒 Por favor proveer código de ingreso / Please provide access code",
                        )
                    return JSONResponse({"ok": True})
            finally:
                meta.close()

        # ---- Log every authorized message ----
        meta = get_metadata_session()
        try:
            crud.log_message(meta, chat_id)
        except Exception:
            pass
        finally:
            meta.close()

        # ---- Admin command handling ----
        raw_text = message.get("text", "").strip()
        if raw_text.startswith("/admin"):
            return await _handle_admin_command(chat_id, raw_text)

        db, effective_chat_id, is_linked = get_resolved_session(chat_id)

        try:
            try:
                text_input = await extract_message_text(message)
            except Exception as e:
                error_msg = f"❌ Error processing voice message: {str(e)}"
                await telegram_bot.send_message_async(chat_id, error_msg)
                return JSONResponse(
                    {"status": "error", "error": str(e), "type": "voice_processing"}
                )

            if text_input is None:
                print("❌ No text or voice in message")
                await telegram_bot.send_message_async(
                    chat_id, "❌ Please send either a text or voice message."
                )
                return JSONResponse({"ok": True})

            print(f"📝 Input text: {text_input}")

            try:
                print(f"🤖 Processing with agent: {text_input}")
                result = run_inventory_agent(text_input, db, chat_id)
                response_message = result.get("response_message", "")
                print(f"✅ Agent response: {response_message}")

                if not response_message:
                    response_message = "❌ I couldn't process your request. Please try again."

                await telegram_bot.send_message_async(chat_id, response_message)
                return JSONResponse({"ok": True})

            except Exception as e:
                error_msg = f"❌ Error processing request: {str(e)}"
                print(f"🚨 Agent processing error: {str(e)}")
                await telegram_bot.send_message_async(chat_id, error_msg)
                return JSONResponse(
                    {"status": "error", "error": str(e), "type": "agent_processing"}
                )

        finally:
            db.close()

    except Exception as e:
        print(f"🚨 Webhook processing error: {str(e)}")
        return JSONResponse({"ok": True}, status_code=200)


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint to receive and process messages.

    Args:
        request: FastAPI request object containing the Telegram update payload

    Returns:
        JSON response with processing status
    """
    return await _process_telegram_webhook(request)


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
async def get_inventory(chat_id: int):
    """
    Get all inventory items for a specific user.

    Args:
        chat_id: Telegram chat/user ID whose inventory to retrieve

    Returns:
        JSON response with all items and total count
    """
    db, effective_chat_id, is_linked = get_resolved_session(chat_id)
    try:
        items = crud.get_all_items(db)
        return {
            "items": [item.to_dict() for item in items],
            "count": len(items),
        }
    finally:
        db.close()


@app.get("/inventory/summary")
async def get_inventory_summary(chat_id: int):
    """
    Get inventory summary statistics for a specific user.

    Args:
        chat_id: Telegram chat/user ID whose inventory to summarise

    Returns:
        JSON response with summary data
    """
    db, effective_chat_id, is_linked = get_resolved_session(chat_id)
    try:
        return crud.get_inventory_summary(db)
    finally:
        db.close()


# ============================================================================
# NEW: LangGraph 1.0 Agent Endpoints
# ============================================================================


@app.post("/agent/process")
async def agent_process(user_input: str, chat_id: int):
    """
    Process user input using the LangChain 1.0 inventory agent.

    This endpoint uses the new agent system with:
    - OpenAI API integration via LangChain create_agent
    - Tools: parse_intent, modify_db, query_db
    - Pydantic input validation
    - Per-user database isolation

    Args:
        user_input: User's text input (or transcribed audio)
        chat_id: Telegram chat/user ID whose database to use

    Returns:
        JSON response with agent response and metadata
    """
    db, effective_chat_id, is_linked = get_resolved_session(chat_id)
    try:
        result = run_inventory_agent(user_input, db, chat_id)
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
    finally:
        db.close()


@app.post("/agent/voice")
async def agent_voice(request: Request):
    """
    Process voice input using the LangGraph 1.0 inventory agent.

    Workflow:
    1. Extract chat_id and voice message from Telegram payload
    2. Open per-user database session
    3. Transcribe audio via :func:`extract_voice_text`
    4. Pass transcribed text to agent
    5. Return agent response

    Args:
        request: FastAPI request containing Telegram update payload

    Returns:
        JSON response with agent processing result
    """
    try:
        payload = await request.json()

        if "message" not in payload or "voice" not in payload["message"]:
            return {
                "status": "error",
                "error": "No voice message in payload",
            }

        message = payload["message"]
        chat_id = message["chat"]["id"]

        db, effective_chat_id, is_linked = get_resolved_session(chat_id)
        try:
            transcribed_text = await extract_voice_text(message)
            result = run_inventory_agent(transcribed_text, db, chat_id)

            return {
                "status": result.get("result", "success"),
                "transcribed_text": transcribed_text,
                "response": result.get("response_message", ""),
                "tools_used": result.get("tools_used", []),
                "metadata": result.get("metadata", {}),
            }
        finally:
            db.close()

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
        from .agent import create_inventory_agent

        create_inventory_agent()

        return {
            "status": "healthy",
            "agent_type": "LangChain 1.0",
            "model": "OpenAI gpt-4o-mini",
            "tools": ["parse_intent", "modify_db", "query_db"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
