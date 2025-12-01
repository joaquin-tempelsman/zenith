# Daily HTML Pipeline Project Plan

## Project Overview
A simple automated pipeline that runs daily on a DigitalOcean droplet, generates an HTML page with the current date, and serves it via a public web server.

## Architecture
```
┌─────────────────────────────────────────┐
│  DigitalOcean Droplet (Ubuntu/Debian)  │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Python Pipeline (Cron Job)       │ │
│  │  - Runs daily                     │ │
│  │  - Generates HTML                 │ │
│  │  - Saves to web directory         │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Nginx Web Server                 │ │
│  │  - Serves static HTML             │ │
│  │  - Public port 80/443             │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Prerequisites
- DigitalOcean droplet with Ubuntu 20.04+ or Debian 10+
- SSH access to the droplet
- Domain name (optional, can use droplet IPv4/IPv6 address)
- Basic knowledge of terminal commands
- Note: Droplet comes with IPv6 enabled and VPC configured by default

## Phase 1: Initial Setup Steps

### 1. Prepare Your Droplet
```bash
# SSH into your droplet (use IPv4 or IPv6)
ssh root@your_droplet_ipv4
# OR using IPv6:
# ssh root@[your_droplet_ipv6]

# Verify network configuration
ip a  # Check IPv4 and IPv6 addresses
ip route  # Verify VPC routing

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx git
```

### 2. Setup Project Structure
```bash
# Create project directory
mkdir -p /opt/daily-html-pipeline
cd /opt/daily-html-pipeline

# Clone this repository
git clone <your-repo-url> .

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies (if any)
pip install -r requirements.txt
```

### 3. Configure Web Server (Nginx)
```bash
# Create directory for HTML output
sudo mkdir -p /var/www/daily-pipeline
sudo chown -R $USER:$USER /var/www/daily-pipeline

# Configure Nginx (will create config file)
sudo nano /etc/nginx/sites-available/daily-pipeline

# Enable the site
sudo ln -s /etc/nginx/sites-available/daily-pipeline /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Configure firewall (allow IPv4 and IPv6 traffic)
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
# UFW automatically handles both IPv4 and IPv6 by default
sudo ufw enable

# Verify firewall rules
sudo ufw status verbose
```

### 4. Setup Cron Job for Daily Execution
```bash
# Edit crontab
crontab -e

# Add the following line (runs daily at 6:00 AM)
0 6 * * * /opt/daily-html-pipeline/run_pipeline.sh >> /var/log/daily-pipeline.log 2>&1
```

## Phase 2: Project Components

### Files to Create

#### 1. `generate_html.py`
Python script that:
- Gets current date
- Generates HTML with "Hello World {today's date}"
- Saves to `/var/www/daily-pipeline/index.html`

#### 2. `run_pipeline.sh`
Bash script that:
- Activates virtual environment
- Runs the Python pipeline
- Logs execution
- Handles errors

#### 3. `requirements.txt`
Python dependencies (minimal for Phase 1)

#### 4. `nginx.conf`
Nginx configuration for serving the HTML
- Configured to listen on both IPv4 and IPv6
- Works with DigitalOcean VPC setup

#### 5. `setup.sh`
One-time setup script that:
- Installs dependencies
- Configures Nginx
- Sets up cron job
- Runs initial pipeline

## Phase 3: Testing & Verification

### Manual Testing
```bash
# Test Python script manually
cd /opt/daily-html-pipeline
source venv/bin/activate
python generate_html.py

# Check generated HTML
cat /var/www/daily-pipeline/index.html

# Test web server (IPv4 and IPv6)
curl http://localhost
curl -4 http://localhost  # Force IPv4
curl -6 http://localhost  # Force IPv6
curl http://[::1]         # IPv6 loopback
```

### Access from Browser
- Navigate to `http://your_droplet_ipv4` or `http://[your_droplet_ipv6]`
- Should see "Hello World {today's date}"
- Note: IPv6 addresses must be wrapped in brackets in URLs

### Verify Cron Job
```bash
# Check cron logs
grep CRON /var/log/syslog

# Check pipeline logs
tail -f /var/log/daily-pipeline.log
```

## Phase 4: Future Iterations

### Potential Enhancements
1. **Data Visualization**
   - Add charts using matplotlib/plotly
   - Display time series data
   - Create interactive dashboards

2. **Data Sources**
   - Fetch data from APIs
   - Query databases
   - Process CSV/JSON files
   - Web scraping

3. **Advanced Features**
   - Multiple pages/reports
   - Historical archive
   - Email notifications
   - Slack/Discord webhooks
   - Custom styling with CSS frameworks

4. **Security**
   - HTTPS with Let's Encrypt
   - Basic authentication
   - API rate limiting

5. **Monitoring**
   - Health checks
   - Error alerting
   - Performance metrics

## Troubleshooting

### Common Issues

**Nginx won't start**
```bash
sudo nginx -t  # Check configuration
sudo systemctl status nginx  # Check service status
```

**Permission denied errors**
```bash
# Fix ownership
sudo chown -R $USER:$USER /var/www/daily-pipeline
sudo chown -R $USER:$USER /opt/daily-html-pipeline
```

**Cron job not running**
```bash
# Check cron service
sudo systemctl status cron

# Verify crontab
crontab -l

# Check logs
grep CRON /var/log/syslog
```

**Python script errors**
```bash
# Check Python version
python3 --version

# Verify virtual environment
which python

# Check logs
cat /var/log/daily-pipeline.log
```

## Security Considerations

1. **Firewall**: Only open necessary ports (80, 443, 22)
   - UFW automatically handles both IPv4 and IPv6 rules
   - Monitor both protocol versions for security
2. **SSH**: Use key-based authentication, disable password auth
3. **Updates**: Regularly update system packages
4. **User Permissions**: Don't run as root when possible
5. **Nginx**: Keep configuration minimal and secure
   - Ensure both IPv4 and IPv6 listeners are properly configured
6. **VPC**: Leverage DigitalOcean VPC for internal communication
   - Use private network for database/backend services if added later
   - Public web traffic on IPv4/IPv6, private services on VPC

## Quick Start Commands Summary

```bash
# On your local machine
git clone <repo-url>
cd docean_droplet_work

# On your droplet
scp -r . root@your_droplet_ip:/opt/daily-html-pipeline
ssh root@your_droplet_ip
cd /opt/daily-html-pipeline
chmod +x setup.sh run_pipeline.sh
./setup.sh
```

## Next Steps

After reviewing this plan:
1. Let me know you're ready to proceed
2. I'll create all the necessary code files
3. You'll clone this repo to your droplet
4. Run the setup script
5. Start iterating on the pipeline

---

**Note**: This plan starts simple with "Hello World" and is designed to be easily extensible for more complex data pipelines later.
