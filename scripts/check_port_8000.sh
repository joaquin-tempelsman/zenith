#!/bin/bash
# Script to diagnose port 8000 availability on the droplet

echo "=== Checking Port 8000 Availability ==="
echo ""

echo "1. Checking if Docker containers are running:"
docker ps
echo ""

echo "2. Checking port bindings for inventory-api:"
docker port inventory-api 2>/dev/null || echo "Container not found or not running"
echo ""

echo "3. Checking processes listening on port 8000:"
sudo netstat -tlnp | grep 8000 || echo "No process listening on port 8000"
echo ""

echo "4. Checking UFW firewall status:"
sudo ufw status | grep 8000
echo ""

echo "5. Testing localhost connection to port 8000:"
curl -s -m 3 http://localhost:8000/health && echo "✅ Localhost connection successful" || echo "❌ Localhost connection failed"
echo ""

echo "6. Testing 0.0.0.0 connection to port 8000:"
curl -s -m 3 http://0.0.0.0:8000/health && echo "✅ 0.0.0.0 connection successful" || echo "❌ 0.0.0.0 connection failed"
echo ""

echo "7. Checking if port 8000 is listening on all interfaces:"
sudo ss -tlnp | grep :8000
echo ""

echo "8. Checking Docker network settings:"
docker inspect inventory-api --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null || echo "Container not found"
echo ""

echo "9. Checking iptables rules (Docker creates these):"
sudo iptables -L -n | grep 8000 || echo "No iptables rules for port 8000"
echo ""

echo "10. Checking container logs (last 10 lines):"
docker logs inventory-api --tail=10 2>/dev/null || echo "Container not found"
echo ""

echo "=== Diagnostic Complete ==="

