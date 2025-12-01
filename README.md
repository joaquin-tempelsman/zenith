# Daily HTML Pipeline

A simple automated pipeline that runs daily on a DigitalOcean droplet, generates an HTML page with a timestamp, and serves it publicly via Nginx.

## 🚀 Quick Start

### On Your Droplet

```bash
# Clone this repository
git clone https://github.com/joaquin-tempelsman/zenith.git
cd zenith

# Make scripts executable
chmod +x setup.sh run_pipeline.sh

# Run the setup script
sudo ./setup.sh
```

That's it! Your pipeline is now running and accessible at your droplet's IP address.

## 📁 Project Structure

```
.
├── generate_html.py      # Python script that generates the HTML
├── run_pipeline.sh       # Bash script that runs the pipeline
├── setup.sh              # One-time setup script
├── requirements.txt      # Python dependencies
├── nginx.conf            # Nginx web server configuration
├── PROJECT_PLAN.md       # Detailed project documentation
└── README.md             # This file
```

## 🔧 What Gets Installed

- Python 3 with virtual environment
- Nginx web server (configured for IPv4 and IPv6)
- UFW firewall (ports 80, 443, 22)
- Cron job (runs every minute)

## 📋 Manual Usage

### Run the pipeline manually
```bash
./run_pipeline.sh
```

### View the generated HTML
```bash
cat /var/www/daily-pipeline/index.html
```

### Check logs
```bash
tail -f /var/log/daily-pipeline.log
```

### Test locally
```bash
curl http://localhost
```

### Access from browser
- IPv4: `http://YOUR_DROPLET_IP`
- IPv6: `http://[YOUR_DROPLET_IPV6]`

## ⚙️ Configuration

### Change Cron Schedule

Edit your crontab:
```bash
crontab -e
```

Current schedule (every minute):
```
* * * * * /opt/daily-html-pipeline/run_pipeline.sh >> /var/log/daily-pipeline.log 2>&1
```

**Common schedules:**
- Every 5 minutes: `*/5 * * * *`
- Every hour: `0 * * * *`
- Every 6 hours: `0 */6 * * *`
- Twice daily (6 AM & 6 PM): `0 6,18 * * *`
- Every Monday at 9 AM: `0 9 * * 1`

### Change Output Directory

Set the `HTML_OUTPUT_PATH` environment variable:
```bash
export HTML_OUTPUT_PATH=/custom/path/index.html
python3 generate_html.py
```

## 🛠️ Troubleshooting

### Check Nginx status
```bash
sudo systemctl status nginx
```

### Test Nginx configuration
```bash
sudo nginx -t
```

### Restart Nginx
```bash
sudo systemctl restart nginx
```

### Check firewall
```bash
sudo ufw status verbose
```

### Verify cron job is scheduled
```bash
crontab -l
```

### View cron execution history
```bash
# View recent cron executions
grep CRON /var/log/syslog | tail -20

# Or use journalctl
journalctl -u cron | tail -20

# Watch pipeline logs in real-time
tail -f /var/log/daily-pipeline.log
```

### Check if cron is running
```bash
sudo systemctl status cron
```

### View recent cron executions
```bash
grep CRON /var/log/syslog | tail -20
```

### Check Python virtual environment
```bash
source venv/bin/activate
python --version
pip list
```

## 🔐 Security Notes

- **UFW Firewall**: Configured to allow HTTP (80), HTTPS (443), and SSH (22)
- **Optional**: Set up DigitalOcean Cloud Firewall in the control panel for additional security
- **SSH**: Consider restricting SSH access to your IP only
- **Updates**: Keep system packages updated with `sudo apt update && sudo apt upgrade`

## 📈 Expanding the Pipeline

This project starts with a simple "Hello World" example. Here are ideas for expansion:

### Add Data Visualization
```python
# Install matplotlib or plotly
pip install matplotlib pandas
```

### Fetch External Data
```python
# Install requests
pip install requests
# Fetch from APIs, databases, etc.
```

### Use HTML Templates
```python
# Install jinja2
pip install jinja2
# Create professional-looking reports
```

### Add Multiple Pages
```python
# Generate dashboard, reports, archives
# Update Nginx config to serve multiple endpoints
```

See `PROJECT_PLAN.md` for more detailed expansion ideas.

## 📝 Files Explained

### `generate_html.py`
Python script that:
- Gets current timestamp in `YYMMDD_HHMMSS` format
- Creates styled HTML with "Hello World" and timestamp
- Saves to `/var/www/daily-pipeline/index.html`

### `run_pipeline.sh`
Bash script that:
- Activates Python virtual environment
- Runs `generate_html.py`
- Logs output
- Used by cron for scheduled runs

### `setup.sh`
One-time setup script that:
- Installs system packages
- Creates Python virtual environment
- Configures Nginx
- Sets up firewall
- Creates cron job
- Runs initial pipeline

### `nginx.conf`
Web server configuration that:
- Listens on IPv4 and IPv6
- Serves files from `/var/www/daily-pipeline`
- Includes security headers
- Disables caching for development

## 🌐 Network Information

This project works with:
- **IPv4**: Standard IP address access
- **IPv6**: Full dual-stack support
- **VPC**: DigitalOcean private networking ready

Both IPv4 and IPv6 are handled automatically by Nginx and UFW.

## 📜 License

This is a toy project for learning purposes. Feel free to modify and use as you like.

## 🤝 Contributing

This is a personal learning project, but suggestions are welcome!

## 📞 Support

For issues or questions, refer to `PROJECT_PLAN.md` for detailed documentation and troubleshooting steps.

---

**Generated**: November 30, 2025  
**Author**: Data Science Pipeline Project
