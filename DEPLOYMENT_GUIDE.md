# Deployment Guide

**Version**: 2.0
**Target**: Production Environment
**Last Updated**: February 1, 2026

---

## 📋 Prerequisites

### System Requirements

**Minimum**:
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB SSD
- OS: Linux (Ubuntu 20.04+), macOS, Windows

**Recommended**:
- CPU: 4 cores
- RAM: 8GB
- Storage: 50GB SSD
- OS: Ubuntu 22.04 LTS

### Software Requirements

- Python 3.11+
- Node.js 18+
- nginx (for production)
- SQLite 3.35+
- Git

---

## 🚀 Deployment Options

### Option 1: Docker Deployment (Recommended)

#### 1.1 Create Docker Files

**Dockerfile (Backend)**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Dockerfile (Frontend)**:
```dockerfile
FROM node:18-alpine AS build

WORKDIR /app

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Build application
COPY frontend/ .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - LOG_LEVEL=INFO
      - ENABLE_HISTORICAL_COLLECTION=true
      - DATABASE_PATH=/app/data/analysis_history.db
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  data:
```

#### 1.2 Deploy with Docker

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Update application
git pull
docker-compose up -d --build
```

---

### Option 2: Traditional Deployment

#### 2.1 Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3-pip nodejs npm nginx git

# Install PM2 for process management
sudo npm install -g pm2

# Clone repository
git clone <repository-url>
cd "Indian Stock Fund"
```

#### 2.2 Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create data directory
mkdir -p data

# Configure environment
cp .env.example .env
nano .env  # Edit configuration

# Test run
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Setup PM2
pm2 start "uvicorn api.main:app --host 0.0.0.0 --port 8000" --name ai-hedge-fund-api
pm2 save
pm2 startup
```

#### 2.3 Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# The dist/ folder contains the production build
```

#### 2.4 nginx Configuration

Create `/etc/nginx/sites-available/ai-hedge-fund`:

```nginx
# Backend API
upstream api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        root /path/to/Indian Stock Fund/frontend/dist;
        try_files $uri $uri/ /index.html;

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api/ {
        proxy_pass http://api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API docs
    location /docs {
        proxy_pass http://api/docs;
        proxy_set_header Host $host;
    }

    # Health check
    location /health {
        proxy_pass http://api/health;
        access_log off;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/ai-hedge-fund /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔒 SSL/HTTPS Setup

### Using Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

nginx will be automatically configured for HTTPS.

---

## 🗄️ Database Setup

### Initialize Database

```bash
# The database is created automatically on first run
# To manually initialize:
python3 -c "from data.historical_db import HistoricalDatabase; HistoricalDatabase()"
```

### Database Backup

Create backup script `/scripts/backup_db.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/ai-hedge-fund"
DB_PATH="/path/to/data/analysis_history.db"

mkdir -p $BACKUP_DIR

# SQLite backup
sqlite3 $DB_PATH ".backup $BACKUP_DIR/db_$DATE.db"

# Compress
gzip $BACKUP_DIR/db_$DATE.db

# Keep only last 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: db_$DATE.db.gz"
```

Setup cron job:
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /scripts/backup_db.sh
```

---

## 📊 Monitoring

### PM2 Monitoring

```bash
# View status
pm2 status

# View logs
pm2 logs ai-hedge-fund-api

# Monitor resources
pm2 monit

# Restart
pm2 restart ai-hedge-fund-api

# View detailed info
pm2 info ai-hedge-fund-api
```

### Log Management

Configure log rotation in `/etc/logrotate.d/ai-hedge-fund`:

```
/var/log/ai-hedge-fund/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
    sharedscripts
    postrotate
        pm2 reloadLogs
    endscript
}
```

### System Monitoring

Install monitoring tools:
```bash
# Install htop for system monitoring
sudo apt install htop

# Install iotop for I/O monitoring
sudo apt install iotop

# Monitor with htop
htop
```

---

## 🔄 Continuous Deployment

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /path/to/Indian\ Stock\ Fund
            git pull

            # Backend
            source venv/bin/activate
            pip install -r requirements.txt
            pm2 restart ai-hedge-fund-api

            # Frontend
            cd frontend
            npm install
            npm run build

            # Reload nginx
            sudo systemctl reload nginx
```

---

## 🔐 Security

### Best Practices

1. **Environment Variables**:
   - Never commit `.env` file
   - Use strong, unique values
   - Rotate API keys regularly

2. **Firewall**:
```bash
# UFW setup
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

3. **SSH Security**:
```bash
# Disable password authentication
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart sshd
```

4. **Regular Updates**:
```bash
# Create update script
sudo apt update && sudo apt upgrade -y
pip install --upgrade -r requirements.txt
```

---

## 📈 Performance Tuning

### Backend Optimization

**Gunicorn Configuration** (`gunicorn_config.py`):
```python
workers = 4  # 2 * CPU cores
worker_class = "uvicorn.workers.UvicornWorker"
bind = "127.0.0.1:8000"
keepalive = 120
timeout = 120
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50
```

Run with:
```bash
gunicorn -c gunicorn_config.py api.main:app
```

### Frontend Optimization

Already optimized in build:
- Code splitting ✅
- Minification ✅
- Tree shaking ✅
- Gzip compression via nginx ✅

### Database Optimization

```bash
# Run optimization
sqlite3 data/analysis_history.db "VACUUM; ANALYZE;"

# Schedule weekly optimization
crontab -e
# Add: 0 3 * * 0 sqlite3 /path/to/data/analysis_history.db "VACUUM; ANALYZE;"
```

---

## 🧪 Health Checks

### Application Health Check

```bash
# Backend
curl http://localhost:8000/health

# Expected: {"status":"healthy",...}
```

### Automated Monitoring

Setup monitoring script `/scripts/health_check.sh`:

```bash
#!/bin/bash

# Check backend
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "Backend: OK"
else
    echo "Backend: FAILED"
    pm2 restart ai-hedge-fund-api
    # Send alert (email, Slack, etc.)
fi

# Check frontend
if curl -s http://localhost | grep -q "html"; then
    echo "Frontend: OK"
else
    echo "Frontend: FAILED"
    sudo systemctl restart nginx
fi
```

Run every 5 minutes:
```bash
crontab -e
# Add: */5 * * * * /scripts/health_check.sh
```

---

## 🆘 Troubleshooting

### Common Issues

**1. Port Already in Use**:
```bash
# Find process
sudo lsof -i :8000
# Kill process
sudo kill -9 <PID>
```

**2. Permission Denied**:
```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/
chmod 755 data/
```

**3. Database Locked**:
```bash
# Check for other processes
fuser data/analysis_history.db
# Kill if necessary
```

**4. Frontend Not Loading**:
```bash
# Check nginx status
sudo systemctl status nginx
# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

**5. High Memory Usage**:
```bash
# Reduce Gunicorn workers
# Increase swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📝 Maintenance

### Regular Tasks

**Daily**:
- Check application logs
- Monitor disk space
- Review error rates

**Weekly**:
- Database vacuum/analyze
- Review performance metrics
- Check for updates

**Monthly**:
- System updates
- Security audit
- Backup verification

### Maintenance Mode

Create `/usr/share/nginx/html/maintenance.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Maintenance</title>
</head>
<body>
    <h1>System Maintenance</h1>
    <p>We'll be back shortly!</p>
</body>
</html>
```

Enable maintenance mode in nginx:
```nginx
location / {
    return 503;
    error_page 503 /maintenance.html;
}

location = /maintenance.html {
    root /usr/share/nginx/html;
    internal;
}
```

---

## 🔄 Rollback Procedure

```bash
# 1. Note current version
git log -1 --oneline

# 2. Stop services
pm2 stop ai-hedge-fund-api

# 3. Rollback code
git checkout <previous-commit>

# 4. Reinstall dependencies (if needed)
source venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..

# 5. Restart services
pm2 start ai-hedge-fund-api
sudo systemctl reload nginx

# 6. Verify
curl http://localhost:8000/health
```

---

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] Code tested locally
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Environment variables configured
- [ ] Database backup taken
- [ ] SSL certificate valid

### Deployment
- [ ] Code deployed successfully
- [ ] Dependencies installed
- [ ] Services restarted
- [ ] Health checks passing
- [ ] Frontend accessible
- [ ] API responding

### Post-Deployment
- [ ] Monitor logs for errors
- [ ] Check performance metrics
- [ ] Verify core functionality
- [ ] Test critical workflows
- [ ] Notify team

---

**Deployment Guide Version**: 2.0
**Last Updated**: February 1, 2026
**Status**: Production Ready ✅
