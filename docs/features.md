# Zenith — Features

## Inventory Management

- **Add items** — _"Add 5 apples to fruits"_ / _"Añadir leche a lácteos"_. Specify name, quantity (defaults to 1), category, and optional expiration date. If the item already exists, the quantity is incremented.
- **Remove items** — _"Remove 3 bananas"_ or _"Remove all oranges"_. Subtracts the given quantity or clears the item entirely.
- **Batch operations** — _"Add apples, bananas and oranges to fruits"_. Process multiple items in one message with a grouped summary of results.
- **Check stock** — _"How much milk do we have?"_ Returns quantity, category, and expiration date.
- **List by category** — _"Show fruits category"_. Lists all items in a category with quantities.
- **Expiration tracking** — _"Show items expiring soon"_. Items sorted by expiration date, soonest first.
- **Change history** — _"History of changes last 7 days"_. View recent inventory changes, filterable by item or category.
- **Inventory summary** — _"Give me an inventory summary"_. Returns unique item count, total quantity, and category list.
- **Smart categorization** — The bot auto-categorizes items (milk → dairy, chicken → meat) and uses your existing categories for context.
- **Reset database** — _"Reset database"_ followed by an explicit _"OK"_ confirmation. Clears all items.

## Voice Messages

- Send a **voice message** in Telegram and the bot processes it exactly like text.
- Powered by OpenAI Whisper for transcription — works in both English and Spanish.

## Bilingual Support

- Write or speak in **English or Spanish** — the bot detects the language automatically and responds in kind.
- Separate prompt templates for each language ensure natural, idiomatic responses.

## Shared Inventory (Account Linking)

- **Get your link code** — _"What's my link code?"_ / _"Dame mi código"_. Returns a unique, permanent sharing code.
- **Link accounts** — _"Link my account with code ABC123"_. After linking, all inventory operations read and write the owner's database.
- **Unlink** — _"Unlink my account"_. Returns you to your own personal inventory.
- **Check link status** — _"What's my link status?"_. See who you're linked to and how many users share your inventory.

This lets households, teams, or business partners share a single inventory seamlessly.

## Access Control

- When enabled, new users must provide a **secret access code** before they can use the bot.
- Up to 5 failed attempts before the user is permanently blocked.
- Separate toggle and codes for development vs. production environments.

## Admin Mode

- `/admin <code>` — Authenticate as an admin.
- `/admin report` — Get an on-demand usage report with user counts, active users, and token usage.
- `/admin status` — Check your admin status.
- **Automated daily reports** — All admins receive a daily summary at a configurable hour (default 21:00 UTC) with total users, daily active users, and token consumption (daily + monthly).

## Per-User Data Isolation

- Every Telegram user gets their own **private SQLite database** — complete data isolation between users.
- A shared metadata database handles account linking, access control, admin records, and usage logs.
- **WAL mode** on all databases for safe concurrent reads and reliable backups.

## Automatic Backups

- **Daily crash-safe backups** of all user databases and metadata using `sqlite3 .backup`.
- Compressed as `.tar.gz` archives with **30-day retention** (older backups are auto-deleted).
- Runs via cron on the production server — no manual intervention needed.

## Web Dashboard

- **Password-protected** Streamlit dashboard for viewing inventory data.
- Select any user from a dropdown to browse their inventory.
- **Inventory overview** — total items, quantities, categories, low-stock warnings (< 5 units), and expiring-soon alerts (within 7 days).
- **Category charts** — bar charts for items per category and total quantity per category.
- **SQL runner** — execute arbitrary queries against any user's database and export results as CSV.

## Built-in Help

- _"Help"_ / _"Ayuda"_ — returns a formatted list of all available commands with examples in the detected language.

## REST API

Beyond the Telegram bot, the app exposes HTTP endpoints for programmatic access:

| Endpoint | Purpose |
|---|---|
| `GET /health` | System health check |
| `GET /inventory?chat_id=…` | Get all items for a user |
| `GET /inventory/summary?chat_id=…` | Inventory summary stats |
| `POST /agent/process` | Send text to the agent directly |
| `POST /agent/voice` | Send voice input to the agent |
| `GET /agent/health` | Agent system health |

## Token Usage Tracking

- Every agent invocation logs input and output token counts.
- Usage is queryable by day or month and included in admin daily reports.
- Helps monitor costs and usage patterns over time.

## Schema Migrations

- **Alembic** manages database schema changes across all per-user databases automatically.
- Migrations run on every app startup — new schema changes are applied without manual steps.
- Fresh databases are auto-stamped to the current revision.

## Deployment

- **Docker Compose** setup with separate dev and production configurations.
- **Automatic HTTPS** via ngrok tunnel with a configurable domain.
- **One-shot webhook setup** — a helper container auto-registers the Telegram webhook after the API starts.
- **Health checks** — the API container is monitored every 30 seconds; dependent services wait for it to be healthy.
- **CI/CD** via GitHub Actions — tests on every push, automatic deployment to DigitalOcean on merge to main.
