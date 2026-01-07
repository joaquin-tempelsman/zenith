# Nginx Configuration

This directory contains the Nginx reverse proxy configuration for the Voice-Managed Inventory System.

## Directory Structure

```
nginx/
├── nginx.conf          # Main Nginx configuration
├── ssl/                # SSL certificates (create this directory)
│   ├── cert.pem       # SSL certificate (not in git)
│   └── key.pem        # SSL private key (not in git)
└── logs/              # Nginx logs (created automatically)
```

## SSL Certificate Setup

### Option 1: Let's Encrypt (Recommended for Production)

1. **Install Certbot on your server**
   ```bash
   apt-get install certbot python3-certbot-nginx -y
   ```

2. **Obtain certificate**
   ```bash
   certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

3. **Update nginx.conf**
   ```nginx
   ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
   ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
   ```

4. **Auto-renewal**
   ```bash
   # Test renewal
   certbot renew --dry-run
   
   # Certbot automatically sets up a cron job for renewal
   ```

### Option 2: Self-Signed Certificate (Development Only)

1. **Create ssl directory**
   ```bash
   mkdir -p nginx/ssl
   ```

2. **Generate self-signed certificate**
   ```bash
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout nginx/ssl/key.pem \
     -out nginx/ssl/cert.pem \
     -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
   ```

3. **Restart Nginx**
   ```bash
   docker compose restart nginx
   ```

### Option 3: Existing Certificate

1. **Create ssl directory**
   ```bash
   mkdir -p nginx/ssl
   ```

2. **Copy your certificates**
   ```bash
   cp /path/to/your/certificate.crt nginx/ssl/cert.pem
   cp /path/to/your/private.key nginx/ssl/key.pem
   ```

3. **Set proper permissions**
   ```bash
   chmod 600 nginx/ssl/key.pem
   chmod 644 nginx/ssl/cert.pem
   ```

## Configuration Details

### Reverse Proxy Routes

- `/api/*` → FastAPI backend (port 8000)
- `/telegram-webhook` → Telegram webhook endpoint
- `/health` → Health check endpoint
- `/` → Streamlit dashboard (port 8501)

### Security Features

- **TLS 1.2 and 1.3** only
- **HSTS** (HTTP Strict Transport Security)
- **X-Frame-Options** protection
- **X-Content-Type-Options** protection
- **XSS Protection**
- **Rate limiting** on API and dashboard endpoints

### Rate Limiting

- API endpoints: 10 requests/second (burst: 20)
- Dashboard: 5 requests/second (burst: 10)

## Testing Configuration

```bash
# Test Nginx configuration
docker compose exec nginx nginx -t

# Reload Nginx
docker compose exec nginx nginx -s reload

# View Nginx logs
docker compose logs nginx

# Follow Nginx logs
docker compose logs -f nginx
```

## Troubleshooting

### SSL Certificate Errors

```bash
# Check certificate validity
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Check certificate and key match
openssl x509 -noout -modulus -in nginx/ssl/cert.pem | openssl md5
openssl rsa -noout -modulus -in nginx/ssl/key.pem | openssl md5
# The MD5 hashes should match
```

### Connection Issues

```bash
# Check if Nginx is running
docker compose ps nginx

# Check Nginx error logs
docker compose logs nginx | grep error

# Test from inside container
docker compose exec nginx curl -I http://api:8000/health
```

### Port Conflicts

```bash
# Check what's using port 80/443
lsof -i :80
lsof -i :443

# Kill the process or change ports in docker-compose.yml
```

## Production Checklist

- [ ] SSL certificates installed and valid
- [ ] Domain DNS configured correctly
- [ ] Firewall allows ports 80 and 443
- [ ] Rate limiting configured appropriately
- [ ] Security headers enabled
- [ ] HSTS enabled (after testing)
- [ ] Certificate auto-renewal configured
- [ ] Logs rotation configured

## Disabling Nginx (Development)

If you don't need Nginx for local development:

```bash
# Start without nginx
docker compose up api dashboard

# Or comment out nginx service in docker-compose.yml
```

## Additional Resources

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [SSL Labs Test](https://www.ssllabs.com/ssltest/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)

