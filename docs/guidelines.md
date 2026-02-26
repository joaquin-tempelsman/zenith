# Usage Guidelines

How to run and use the Zenith inventory management system.

## Starting the Application

### Development (Local)

```bash
# Recommended
./start-dev.sh

# Or using Make
make dev

# Or directly with Docker
docker compose up -d
```

### Production

```bash
docker compose -f docker-compose.prod.yml up -d
```

## Accessing Services

| Service | Development URL | Production URL |
|---------|-----------------|----------------|
| Dashboard | http://localhost:8501 | http://your-server:8501 |
| API | http://localhost:8000 | http://your-server:8000 |
| API Docs | http://localhost:8000/docs | http://your-server:8000/docs |
| ngrok Inspector | http://localhost:4040 | N/A |

## Using the Telegram Bot

Send messages to your bot naturally. The bot understands English and Spanish.

### Add Items
- "Add 5 apples to fruits"
- "Añadir leche a lácteos"
- "Add apples, bananas, and oranges" (batch)

### Remove Items
- "Remove 3 bananas"
- "Quitar todas las naranjas"

### Check Stock
- "How much milk do we have?"
- "Cuánto hay de manzanas"

### List Items
- "Show fruits category"
- "Mostrar items que vencen pronto"

### Get Help
- "Help"
- "Ayuda"

### Reset Database
- "Reset database" (requires confirmation with "CONFIRM")

## Using the Dashboard

1. Open http://localhost:8501
2. Enter dashboard password
3. **Inventory Tab**: View items, filter, see charts
4. **SQL Runner Tab**: Run custom queries, export CSV

## Common Commands

```bash
# View logs
docker compose logs -f

# Restart services
docker compose restart

# Stop services
docker compose down

# Check service status
docker compose ps

# Check webhook status
curl http://localhost:8000/webhook-info

# Check inventory
curl http://localhost:8000/inventory
```

## Make Shortcuts

```bash
make dev      # Start development
make up       # Start containers
make down     # Stop containers
make logs     # View logs
make restart  # Restart all
make health   # Check health
make clean    # Full cleanup
```

## Troubleshooting

### Bot not responding
1. Check webhook: `curl http://localhost:8000/webhook-info`
2. Check logs: `docker compose logs api`

### Dashboard not loading
1. Verify container: `docker compose ps`
2. Check logs: `docker compose logs dashboard`

### Port conflicts
```bash
# Check what's using port 8000
lsof -i :8000

# Stop conflicting process or change port in docker-compose.yml
```
