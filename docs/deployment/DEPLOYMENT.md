# Deployment Guide

Comprehensive guide for deploying the AI Hedge Fund system to production.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Backend Deployment](#backend-deployment)
5. [Frontend Deployment](#frontend-deployment)
6. [Database & Caching](#database--caching)
7. [Monitoring & Logging](#monitoring--logging)
8. [Security](#security)
9. [Performance Optimization](#performance-optimization)
10. [Troubleshooting](#troubleshooting)

## Overview

The AI Hedge Fund system consists of:
- **Backend**: FastAPI application (Python 3.11+)
- **Frontend**: React + TypeScript (Vite)
- **Data Providers**: NSEpy + Yahoo Finance
- **LLM**: Gemini/GPT-4/Claude for narratives
- **Logs**: File-based with rotation
- **Cache**: In-memory (can be extended to Redis)

## Prerequisites

### System Requirements

**Minimum:**
- 2 CPU cores
- 4 GB RAM
- 20 GB disk space
- Ubuntu 20.04+ / macOS 12+ / Windows 10+

**Recommended:**
- 4 CPU cores
- 8 GB RAM
- 50 GB disk space
- Load balancer for high availability

### Software Dependencies

- Python 3.11+
- Node.js 18+
- TA-Lib system library
- Nginx (recommended)
- PostgreSQL (optional, for future)
- Redis (optional, for distributed caching)

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd "Indian Stock Fund"
```

### 2. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    ta-lib \
    build-essential \
    nginx
```

**macOS:**
```bash
brew install python@3.11 ta-lib nginx
```

### 3. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Install Frontend Dependencies

```bash
cd frontend
npm install
npm run build
cd ..
```

## Backend Deployment

### Option 1: Systemd Service (Linux)

Create `/etc/systemd/system/aihedgefund.service`:

```ini
[Unit]
Description=AI Hedge Fund API Server
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/aihedgefund
Environment="PATH=/var/www/aihedgefund/venv/bin"
ExecStart=/var/www/aihedgefund/venv/bin/uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable aihedgefund
sudo systemctl start aihedgefund
sudo systemctl status aihedgefund
```

### Option 2: Docker

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ta-lib \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Build and run:**
```bash
docker build -t aihedgefund:latest .
docker run -d \
    --name aihedgefund \
    -p 8000:8000 \
    -v $(pwd)/.env:/app/.env \
    -v $(pwd)/logs:/app/logs \
    --restart unless-stopped \
    aihedgefund:latest
```

### Option 3: Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
      - LOG_JSON=true
    volumes:
      - ./logs:/app/logs
      - ./.env:/app/.env:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - backend
    restart: unless-stopped
```

**Deploy:**
```bash
docker-compose up -d
docker-compose logs -f
```

### Option 4: Gunicorn + Uvicorn Workers

```bash
gunicorn api.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info
```

## Frontend Deployment

### Build for Production

```bash
cd frontend

# Set production API URL
echo "VITE_API_URL=https://api.yourdomain.com" > .env

# Build
npm run build

# Output in dist/ directory
```

### Option 1: Serve with Nginx

**nginx.conf:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;

    # Frontend
    location / {
        root /var/www/aihedgefund/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout for slow requests
        proxy_read_timeout 120s;
        proxy_connect_timeout 120s;
    }

    # Logging
    access_log /var/log/nginx/aihedgefund-access.log;
    error_log /var/log/nginx/aihedgefund-error.log;
}
```

### Option 2: Deploy to Vercel

```bash
cd frontend
vercel --prod
```

Set environment variable in Vercel dashboard:
- `VITE_API_URL`: Your API URL

### Option 3: Deploy to Netlify

```bash
cd frontend
npm install -g netlify-cli
netlify deploy --dir=dist --prod
```

## Environment Configuration

Create production `.env` file:

```bash
# API Configuration
API_PORT=8000
API_WORKERS=4

# Logging
LOG_LEVEL=WARNING
LOG_JSON=true

# Data Providers
NSE_RATE_LIMIT_DELAY=1.0
YAHOO_RATE_LIMIT_DELAY=0.2
DATA_CACHE_DURATION=1200

# LLM Provider (choose one)
GEMINI_API_KEY=your_gemini_key_here
# OPENAI_API_KEY=your_openai_key_here
# ANTHROPIC_API_KEY=your_anthropic_key_here

# Market Regime
REGIME_CACHE_DURATION=21600

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# Performance
SLOW_REQUEST_THRESHOLD=2000
```

## Database & Caching

### Redis (Optional)

For distributed caching across multiple instances:

```bash
# Install Redis
sudo apt-get install redis-server

# Configure
sudo nano /etc/redis/redis.conf

# Start
sudo systemctl start redis
sudo systemctl enable redis
```

**Update backend to use Redis:**
```python
import redis

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)
```

### PostgreSQL (Future)

For persistent storage of analysis history:

```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

## Monitoring & Logging

### 1. System Monitoring

**Install monitoring tools:**
```bash
# Prometheus
docker run -d \
    --name prometheus \
    -p 9090:9090 \
    -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
    prom/prometheus

# Grafana
docker run -d \
    --name grafana \
    -p 3000:3000 \
    grafana/grafana
```

### 2. Application Monitoring

**Monitor with systemd:**
```bash
# View logs
sudo journalctl -u aihedgefund -f

# Check status
sudo systemctl status aihedgefund
```

**Monitor dashboard:**
```bash
# Start monitoring dashboard
python scripts/monitor_system.py
```

### 3. Log Management

**Setup log rotation:**
Create `/etc/logrotate.d/aihedgefund`:

```
/var/www/aihedgefund/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload aihedgefund > /dev/null 2>&1 || true
    endscript
}
```

**Centralized logging with rsyslog:**
```bash
# Send logs to external server
echo "*.* @logserver:514" >> /etc/rsyslog.conf
sudo systemctl restart rsyslog
```

## Security

### 1. API Key Management

**Never commit API keys!**

Use environment variables or secrets management:

```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
    --name aihedgefund/gemini-key \
    --secret-string "your-api-key"

# Retrieve in application
import boto3
secret = boto3.client('secretsmanager').get_secret_value(
    SecretId='aihedgefund/gemini-key'
)
```

### 2. SSL/TLS Certificates

**Using Let's Encrypt:**
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 3. Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 4. Rate Limiting

**Nginx rate limiting:**
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://localhost:8000/;
    }
}
```

### 5. CORS Configuration

Update `api/main.py` for production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domain
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Performance Optimization

### 1. Backend

**Enable caching:**
- Use Redis for distributed caching
- Increase cache durations for production
- Enable HTTP caching headers

**Optimize workers:**
```bash
# Calculate optimal workers: (2 * CPU cores) + 1
uvicorn api.main:app --workers 9  # For 4 cores
```

**Database connection pooling:**
```python
# For future PostgreSQL integration
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'postgresql://user:pass@localhost/db',
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0
)
```

### 2. Frontend

**CDN:**
Use CDN for static assets (Cloudflare, AWS CloudFront)

**Asset optimization:**
```bash
# Already done by Vite build
npm run build  # Minifies, tree-shakes, gzips
```

**Lazy loading:**
Already implemented with React Router code splitting

### 3. Network

**Enable gzip compression in Nginx:**
```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
gzip_min_length 1000;
```

**HTTP/2:**
```nginx
listen 443 ssl http2;
```

## Health Checks

**Backend health:**
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "components": {
    "data_provider": {"status": "healthy"},
    "stock_scorer": {"status": "healthy"},
    "narrative_engine": {"status": "healthy"}
  }
}
```

**Automated monitoring:**
```bash
# Add to crontab
*/5 * * * * curl -f http://localhost:8000/health || systemctl restart aihedgefund
```

## Backup & Recovery

### 1. Configuration Backup

```bash
# Backup .env and configs
tar -czf backup-$(date +%Y%m%d).tar.gz .env logs/ data/
```

### 2. Log Backup

```bash
# Archive logs
find logs/ -name "*.log.*" -mtime +30 -exec gzip {} \;
aws s3 sync logs/ s3://your-bucket/logs/
```

## Scaling

### Horizontal Scaling

**Load balancer (Nginx):**
```nginx
upstream backend {
    least_conn;
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    location /api/ {
        proxy_pass http://backend/;
    }
}
```

### Vertical Scaling

- Increase worker count
- Add more RAM
- Upgrade CPU

## Troubleshooting

### Application Won't Start

```bash
# Check logs
sudo journalctl -u aihedgefund -n 100

# Test manually
source venv/bin/activate
python -m uvicorn api.main:app --reload
```

### High Memory Usage

```bash
# Check processes
ps aux | grep uvicorn

# Reduce workers
# Edit /etc/systemd/system/aihedgefund.service
--workers 2  # Instead of 4
```

### Slow Responses

```bash
# Check metrics
curl http://localhost:8000/metrics/summary

# Monitor in real-time
python scripts/monitor_system.py

# Analyze logs
python scripts/analyze_logs.py
```

### Database Connection Issues

```bash
# Test connectivity
curl -f http://localhost:8000/health

# Check data provider
python -c "from data.hybrid_provider import HybridDataProvider; HybridDataProvider().get_comprehensive_data('TCS')"
```

## Deployment Checklist

- [ ] System dependencies installed
- [ ] Python dependencies installed
- [ ] Frontend built for production
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Firewall configured
- [ ] Nginx configured
- [ ] Systemd service created
- [ ] Log rotation configured
- [ ] Monitoring setup
- [ ] Backups configured
- [ ] Health checks working
- [ ] Load testing completed
- [ ] Documentation updated

## Support

For deployment issues:
1. Check logs: `sudo journalctl -u aihedgefund -f`
2. Review metrics: `curl http://localhost:8000/metrics`
3. Test health: `curl http://localhost:8000/health`
4. Check system resources: `htop`
