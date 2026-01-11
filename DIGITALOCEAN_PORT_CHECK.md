# DigitalOcean Port 8000 Availability Check

## Problem
Port 8000 is not accessible from outside the droplet, even though:
- UFW firewall allows port 8000
- Docker container is binding to 0.0.0.0:8000
- Application is running and healthy inside the container

## Possible Causes

### 1. DigitalOcean Cloud Firewall
DigitalOcean has a separate cloud firewall that operates at the network level, independent of UFW.

**How to Check:**
1. Log into DigitalOcean console: https://cloud.digitalocean.com
2. Go to **Networking** → **Firewalls**
3. Check if there's a firewall attached to your droplet
4. If yes, verify that it allows:
   - **Inbound Rules**: TCP port 8000 from all sources (0.0.0.0/0)
   - **Inbound Rules**: TCP port 8501 from all sources (0.0.0.0/0)

**How to Fix:**
- Option A: Add inbound rules for ports 8000 and 8501
- Option B: Remove the cloud firewall (if you're using UFW instead)

### 2. Docker Network Issues
The container might not be properly binding to the host's network interface.

**How to Check via Console:**
1. Go to **Droplets** → Select your droplet
2. Click **Access** → **Launch Droplet Console** (web-based terminal)
3. Run these commands:
   ```bash
   # Check if container is running
   docker ps
   
   # Check port bindings
   docker port inventory-api
   
   # Check if port is listening
   sudo netstat -tlnp | grep 8000
   
   # Test localhost connection
   curl -v http://localhost:8000/health
   
   # Test from container's perspective
   docker exec inventory-api curl -v http://localhost:8000/health
   ```

### 3. Application Not Binding to 0.0.0.0
The application might be binding to 127.0.0.1 instead of 0.0.0.0.

**How to Check:**
```bash
# Check the exact binding address
docker logs inventory-api | grep "Uvicorn running"
# Should show: "Uvicorn running on http://0.0.0.0:8000"
```

### 4. SELinux or AppArmor Blocking
Some security modules might block Docker port bindings.

**How to Check:**
```bash
# Check if SELinux is enabled
sestatus

# Check AppArmor status
sudo aa-status
```

## Quick Diagnostic Commands

Run these in the DigitalOcean web console:

```bash
# 1. Check container status
docker ps -a

# 2. Check detailed port bindings
docker inspect inventory-api | grep -A 10 "Ports"

# 3. Check if anything is listening on 8000
sudo lsof -i :8000

# 4. Check iptables rules (Docker creates these)
sudo iptables -L -n -t nat | grep 8000

# 5. Test internal connectivity
curl -v http://127.0.0.1:8000/health
curl -v http://localhost:8000/health
curl -v http://0.0.0.0:8000/health

# 6. Check Docker network
docker network inspect inventory-system_inventory-network

# 7. Check if Docker daemon is properly configured
sudo systemctl status docker
```

## Most Likely Solution

Based on the symptoms (UFW allows it, Docker shows it's bound, but external access fails), this is **most likely a DigitalOcean Cloud Firewall issue**.

### Steps to Fix:
1. Go to https://cloud.digitalocean.com
2. Navigate to **Networking** → **Firewalls**
3. Either:
   - **Add rules** for ports 8000 and 8501, OR
   - **Remove the cloud firewall** entirely (since you have UFW configured)

## Alternative: Use Nginx Reverse Proxy

If you want to keep the cloud firewall restrictive, you can:
1. Only allow ports 80 and 443 in the cloud firewall
2. Use Nginx to proxy requests to your application
3. This is more secure and production-ready

We already have Nginx configuration files in the `nginx/` directory that can be used for this purpose.

