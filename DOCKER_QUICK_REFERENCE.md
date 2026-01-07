# 🐳 Docker Quick Reference

Quick reference for Docker commands and workflows.

## 🚀 Getting Started

### First Time Setup

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/inventory-system.git
cd inventory-system

# 2. Create environment file
cp .env.example .env
# Edit .env with your API keys

# 3. Verify setup
./verify-setup.sh

# 4. Start application
./docker-start.sh
```

## 📋 Common Commands

### Development Environment

```bash
# Start services
docker compose up -d

# Start and view logs
docker compose up

# Stop services
docker compose down

# Restart services
docker compose restart

# Rebuild and start
docker compose up -d --build

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f api
docker compose logs -f dashboard
```

### Production Environment

```bash
# Start production services
docker compose -f docker-compose.prod.yml up -d

# Stop production services
docker compose -f docker-compose.prod.yml down

# View production logs
docker compose -f docker-compose.prod.yml logs -f

# Rebuild production
docker compose -f docker-compose.prod.yml up -d --build
```

### Using Make (Easier)

```bash
# Development
make dev              # Start development
make up               # Start services
make down             # Stop services
make logs             # View all logs
make logs-api         # View API logs
make logs-dash        # View dashboard logs
make restart          # Restart services
make clean            # Clean everything

# Production
make prod             # Start production
make prod-up          # Start production services
make prod-down        # Stop production services
make prod-logs        # View production logs
make deploy           # Deploy to production

# Utilities
make health           # Check health
make shell            # Open shell in API container
make db-init          # Initialize database
make db-backup        # Backup database
make ps               # Show running containers
```

## 🔍 Debugging

### Check Service Status

```bash
# List running containers
docker compose ps

# Check container health
docker ps

# Inspect specific container
docker inspect inventory-api
```

### View Logs

```bash
# All services
docker compose logs

# Last 100 lines
docker compose logs --tail=100

# Follow logs
docker compose logs -f

# Specific service
docker compose logs api
docker compose logs dashboard

# With timestamps
docker compose logs -f --timestamps
```

### Execute Commands in Container

```bash
# Open shell in API container
docker compose exec api /bin/bash

# Run Python command
docker compose exec api python -c "from src.database.models import init_db; init_db()"

# Check Python packages
docker compose exec api pip list

# Run tests
docker compose exec api pytest
```

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Detailed disk usage
docker system df -v
```

## 🧹 Cleanup

### Remove Containers and Volumes

```bash
# Stop and remove containers
docker compose down

# Stop and remove containers + volumes
docker compose down -v

# Stop and remove containers + volumes + images
docker compose down -v --rmi all
```

### Clean Up Docker System

```bash
# Remove unused containers, networks, images
docker system prune

# Remove everything (including volumes)
docker system prune -a --volumes

# Remove only stopped containers
docker container prune

# Remove only unused images
docker image prune

# Remove only unused volumes
docker volume prune
```

## 🔧 Troubleshooting

### Port Already in Use

```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 instead
```

### Container Won't Start

```bash
# Check logs
docker compose logs api

# Check container status
docker compose ps

# Rebuild from scratch
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### Database Issues

```bash
# Initialize database
docker compose exec api python -c "from src.database.models import init_db; init_db()"

# Check database file
docker compose exec api ls -la /app/data/

# Backup database
docker cp inventory-api:/app/data/inventory.db ./backup.db

# Restore database
docker cp ./backup.db inventory-api:/app/data/inventory.db
docker compose restart api
```

### Permission Issues

```bash
# Fix ownership of data directory
sudo chown -R $USER:$USER ./data

# Or run as root (not recommended)
docker compose exec -u root api /bin/bash
```

## 📊 Monitoring

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check from inside container
docker compose exec api curl http://localhost:8000/health

# Check all services
docker compose ps
```

### Resource Monitoring

```bash
# Real-time stats
docker stats

# Container processes
docker compose top

# Network inspection
docker network ls
docker network inspect inventory-network
```

## 🔄 Updates

### Update Application Code

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose up -d --build

# Or use deployment script
./deploy/deploy-prod.sh
```

### Update Dependencies

```bash
# Update pyproject.toml
# Then rebuild
docker compose build --no-cache
docker compose up -d
```

### Update Docker Images

```bash
# Pull latest base images
docker compose pull

# Rebuild with latest
docker compose build --pull
docker compose up -d
```

## 🌐 Networking

### Access Services

```bash
# From host machine
http://localhost:8000      # API
http://localhost:8501      # Dashboard

# From another container
http://api:8000            # API
http://dashboard:8501      # Dashboard
```

### Inspect Network

```bash
# List networks
docker network ls

# Inspect network
docker network inspect inventory-network

# Connect container to network
docker network connect inventory-network <container>
```

## 💾 Data Persistence

### Volumes

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect inventory-system_inventory-data

# Backup volume
docker run --rm -v inventory-system_inventory-data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz /data

# Restore volume
docker run --rm -v inventory-system_inventory-data:/data -v $(pwd):/backup alpine tar xzf /backup/data-backup.tar.gz -C /
```

## 🔐 Security

### Best Practices

```bash
# Don't commit .env file
echo ".env" >> .gitignore

# Use secrets for sensitive data
docker secret create my_secret secret.txt

# Run as non-root user (already configured in Dockerfile)
USER appuser

# Scan images for vulnerabilities
docker scan inventory-system:latest
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [DEPLOYMENT.md](DEPLOYMENT.md) - Full deployment guide

