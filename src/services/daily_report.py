"""
Daily admin report generation and delivery.

Builds a Telegram-formatted summary of usage statistics and sends it
to all registered admin users.
"""
from datetime import date, datetime, timezone

from ..database.models import get_metadata_session
from ..database import crud
from .telegram import telegram_bot


def generate_daily_report(day: date | None = None) -> str:
    """Build the daily admin report text for *day*.

    The report includes:
    - Total registered users (distinct chat_ids that ever messaged)
    - List of all user chat_ids
    - Users active on *day* (sent at least one message)
    - Token usage for *day* and for the current calendar month

    Args:
        day: Calendar date to report on. Defaults to today (UTC).

    Returns:
        Markdown-formatted report string suitable for Telegram.
    """
    if day is None:
        day = datetime.now(timezone.utc).date()

    meta = get_metadata_session()
    try:
        total_users = crud.get_total_users(meta)
        all_ids = crud.get_all_user_chat_ids(meta)
        active_ids = crud.get_daily_active_users(meta, day)
        daily_tokens = crud.get_daily_token_usage(meta, day)
        monthly_tokens = crud.get_monthly_token_usage(meta, day.year, day.month)
    finally:
        meta.close()

    ids_str = ", ".join(str(cid) for cid in all_ids) if all_ids else "—"
    active_str = ", ".join(str(cid) for cid in active_ids) if active_ids else "—"

    lines = [
        f"📊 *Daily Report — {day.isoformat()}*",
        "",
        f"👥 *Total users:* {total_users}",
        f"🆔 *Chat IDs:* {ids_str}",
        "",
        f"📬 *Active today:* {len(active_ids)}",
        f"🆔 *Active IDs:* {active_str}",
        "",
        "🔤 *Token usage today:*",
        f"  • Input: {daily_tokens['input_tokens']:,}",
        f"  • Output: {daily_tokens['output_tokens']:,}",
        f"  • Total: {daily_tokens['total_tokens']:,}",
        "",
        f"📅 *Token usage this month ({day.strftime('%B %Y')}):*",
        f"  • Input: {monthly_tokens['input_tokens']:,}",
        f"  • Output: {monthly_tokens['output_tokens']:,}",
        f"  • Total: {monthly_tokens['total_tokens']:,}",
    ]
    return "\n".join(lines)


async def send_daily_reports(day: date | None = None) -> int:
    """Generate and send the daily report to all admin users.

    Args:
        day: Calendar date to report on. Defaults to today (UTC).

    Returns:
        Number of admin users the report was sent to.
    """
    if day is None:
        day = datetime.now(timezone.utc).date()

    meta = get_metadata_session()
    try:
        admins = crud.get_all_admins(meta)
    finally:
        meta.close()

    if not admins:
        print("📊 No admin users to send daily report to.")
        return 0

    report = generate_daily_report(day)

    sent = 0
    for admin_chat_id in admins:
        try:
            await telegram_bot.send_message_async(admin_chat_id, report)
            sent += 1
        except Exception as exc:
            print(f"⚠️ Failed to send report to {admin_chat_id}: {exc}")

    print(f"📊 Daily report sent to {sent}/{len(admins)} admins.")
    return sent
