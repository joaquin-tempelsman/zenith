# 🚀 Production Deployment Checklist

Use this checklist to ensure a smooth production deployment.

## 📋 Pre-Deployment

### Local Setup
- [ ] Code is tested locally with Docker
- [ ] All tests pass (`make test` or `uv run pytest`)
- [ ] Environment variables are documented in `.env.example`
- [ ] `.gitignore` excludes sensitive files
- [ ] Code is committed to Git
- [ ] Repository is pushed to GitHub

### GitHub Setup
- [ ] Repository is created on GitHub
- [ ] Code is pushed to `main` branch
- [ ] GitHub Actions are enabled
- [ ] CI workflow runs successfully
- [ ] Docker images build without errors

### Digital Ocean Setup
- [ ] Droplet is created (Ubuntu 22.04 LTS)
- [ ] SSH key is added to droplet
- [ ] Droplet IP address is noted
- [ ] Domain name is configured (optional)
- [ ] DNS A record points to droplet IP (if using domain)

## 🔐 Security Configuration

### Secrets and Credentials
- [ ] Production `.env` file created on server
- [ ] Strong `DASHBOARD_PASSWORD` set
- [ ] Production `OPENAI_API_KEY` configured
- [ ] Production `TELEGRAM_BOT_TOKEN` configured
- [ ] GitHub Secrets configured:
  - [ ] `DO_HOST`
  - [ ] `DO_USERNAME`
  - [ ] `DO_SSH_KEY`
  - [ ] `DO_SSH_PORT`
  - [ ] `DO_APP_URL`
  - [ ] `OPENAI_API_KEY` (for tests)

### Server Security
- [ ] UFW firewall enabled
- [ ] Only necessary ports open (22, 80, 443)
- [ ] fail2ban installed and configured
- [ ] SSH password authentication disabled (key-only)
- [ ] Root login disabled (optional)
- [ ] Non-root user created for deployment
- [ ] Automatic security updates enabled

### SSL/HTTPS
- [ ] SSL certificates obtained (Let's Encrypt recommended)
- [ ] Certificates placed in `nginx/ssl/` directory
- [ ] nginx.conf updated with certificate paths
- [ ] HTTPS redirect configured
- [ ] Certificate auto-renewal configured

## 🐳 Docker Configuration

### Images and Containers
- [ ] Production images build successfully
- [ ] `docker-compose.prod.yml` configured correctly
- [ ] Environment variables set in production `.env`
- [ ] Volume mounts configured for data persistence
- [ ] Health checks configured
- [ ] Restart policies set to `always`
- [ ] Resource limits configured (optional)

### Networking
- [ ] Ports mapped correctly
- [ ] Nginx reverse proxy configured
- [ ] Internal network created
- [ ] External access tested

## 🌐 Application Configuration

### Telegram Bot
- [ ] Bot created with @BotFather
- [ ] Bot token added to `.env`
- [ ] Webhook URL configured
- [ ] Webhook set to production URL
- [ ] Bot tested with sample messages

### Database
- [ ] Database initialized
- [ ] Database volume configured
- [ ] Backup strategy planned
- [ ] Database file permissions correct

### API Configuration
- [ ] FastAPI running on correct port
- [ ] Health endpoint accessible
- [ ] API documentation accessible
- [ ] CORS configured if needed
- [ ] Rate limiting configured

### Dashboard
- [ ] Streamlit running on correct port
- [ ] Dashboard password set
- [ ] Dashboard accessible via browser
- [ ] WebSocket connections working

## 🔄 CI/CD Pipeline

### GitHub Actions
- [ ] CI workflow passes
- [ ] CD workflow configured
- [ ] Deployment triggers on push to `main`
- [ ] Manual deployment trigger works
- [ ] Deployment verification step passes
- [ ] Failed deployment notifications configured

### Deployment Process
- [ ] SSH connection to server works
- [ ] Git pull works on server
- [ ] Docker login to GHCR works
- [ ] Image pull works
- [ ] Container restart works
- [ ] Health check passes after deployment

## 📊 Monitoring and Logging

### Logging
- [ ] Application logs accessible
- [ ] Log rotation configured
- [ ] Error logs monitored
- [ ] Log retention policy set

### Monitoring
- [ ] Health checks configured
- [ ] Uptime monitoring set up (optional)
- [ ] Resource usage monitoring (optional)
- [ ] Alert notifications configured (optional)

### Backups
- [ ] Database backup script created
- [ ] Backup schedule configured
- [ ] Backup storage location set
- [ ] Backup restoration tested

## 🧪 Testing

### Functional Testing
- [ ] API endpoints tested
- [ ] Dashboard accessible
- [ ] Telegram bot responds
- [ ] Voice messages processed
- [ ] Text messages processed
- [ ] Database operations work
- [ ] Inventory queries work

### Performance Testing
- [ ] Response times acceptable
- [ ] Concurrent users tested
- [ ] Memory usage acceptable
- [ ] CPU usage acceptable
- [ ] Disk space sufficient

### Security Testing
- [ ] HTTPS working
- [ ] Unauthorized access blocked
- [ ] SQL injection tested
- [ ] XSS protection verified
- [ ] Rate limiting working

## 📝 Documentation

### Internal Documentation
- [ ] Deployment process documented
- [ ] Environment variables documented
- [ ] Troubleshooting guide created
- [ ] Runbook created for common tasks

### User Documentation
- [ ] README updated
- [ ] API documentation accessible
- [ ] User guide created (if needed)
- [ ] Bot commands documented

## 🚀 Go-Live

### Final Checks
- [ ] All checklist items completed
- [ ] Stakeholders notified
- [ ] Maintenance window scheduled (if needed)
- [ ] Rollback plan prepared
- [ ] Support team briefed

### Deployment
- [ ] Final code push to `main`
- [ ] CI/CD pipeline completes successfully
- [ ] Application accessible at production URL
- [ ] All services healthy
- [ ] Monitoring active

### Post-Deployment
- [ ] Smoke tests passed
- [ ] Users notified (if applicable)
- [ ] Documentation updated with production URLs
- [ ] Team debriefed
- [ ] Lessons learned documented

## 🆘 Emergency Contacts

- **DevOps Lead**: _________________
- **Backend Developer**: _________________
- **Digital Ocean Support**: https://www.digitalocean.com/support
- **GitHub Support**: https://support.github.com

## 📞 Rollback Procedure

If deployment fails:

1. **Stop new deployment**
   ```bash
   # Cancel GitHub Actions workflow if running
   ```

2. **Revert to previous version**
   ```bash
   ssh user@YOUR_DROPLET_IP
   cd /opt/inventory-system
   git checkout <previous-commit-hash>
   docker compose -f docker-compose.prod.yml up -d --build
   ```

3. **Verify rollback**
   ```bash
   curl http://YOUR_DROPLET_IP:8000/health
   ```

4. **Notify team**
   - Document the issue
   - Plan fix
   - Schedule re-deployment

## ✅ Sign-Off

- [ ] Technical Lead: _________________ Date: _______
- [ ] DevOps: _________________ Date: _______
- [ ] QA: _________________ Date: _______
- [ ] Product Owner: _________________ Date: _______

---

**Deployment Date**: _________________
**Deployed By**: _________________
**Production URL**: _________________
**Notes**: _________________

