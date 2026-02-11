# Deployment Architecture

## Current State (Development)

**Everything runs locally on your machine:**

```
Your Computer (localhost)
├── PostgreSQL Database (port 5432)
├── FastAPI Server (port 8000)
└── Future: React Frontend (port 3000)
```

**Communication:**
- API connects to DB via: `localhost:5432`
- Frontend connects to API via: `http://localhost:8000`

---

## Production Architecture (Recommended)

### Option 1: Single Server (Simple & Cheap)

**Best for:** MVP, low traffic, budget-friendly

```
DigitalOcean Droplet ($12/month)
subdomain.jgaffiliates.com
├── PostgreSQL (localhost:5432)
├── FastAPI (localhost:8000)
├── Nginx (port 80/443)
│   ├── /api/* → FastAPI
│   └── /* → React static files
└── SSL Certificate (Let's Encrypt)
```

**Communication:**
- User → `https://subdomain.jgaffiliates.com` → Nginx
- Nginx → `/api/*` → FastAPI (localhost:8000)
- Nginx → `/*` → React static files
- FastAPI → PostgreSQL (localhost:5432)

**Setup:**
```bash
# On DigitalOcean droplet
sudo apt install postgresql nginx
pip install -r requirements.txt
npm run build  # React frontend

# Nginx config
location /api {
    proxy_pass http://localhost:8000;
}
location / {
    root /var/www/frontend/build;
}
```

**Cost:** ~$12/month

---

### Option 2: Separate Services (Scalable)

**Best for:** Growth, scalability, professional setup

```
┌─────────────────────────────────────────────┐
│  subdomain.jgaffiliates.com                 │
│  (Vercel/Netlify - FREE)                    │
│  React Frontend                             │
└─────────────┬───────────────────────────────┘
              │ HTTPS
              ↓
┌─────────────────────────────────────────────┐
│  api.subdomain.jgaffiliates.com             │
│  (DigitalOcean/AWS - $12-20/month)          │
│  FastAPI Server                             │
└─────────────┬───────────────────────────────┘
              │ Private Network
              ↓
┌─────────────────────────────────────────────┐
│  Database                                   │
│  (DigitalOcean Managed DB - $15/month)      │
│  PostgreSQL                                 │
└─────────────────────────────────────────────┘
```

**Communication:**
- User → `https://subdomain.jgaffiliates.com` → Vercel (Frontend)
- Frontend → `https://api.subdomain.jgaffiliates.com` → API Server
- API → Private IP → Managed Database

**Cost:** ~$15-35/month

---

### Option 3: AWS (Enterprise)

**Best for:** High traffic, enterprise features

```
┌─────────────────────────────────────────────┐
│  CloudFront CDN                             │
│  subdomain.jgaffiliates.com                 │
└─────────────┬───────────────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
    ↓                   ↓
┌─────────┐      ┌─────────────┐
│ S3      │      │ API Gateway │
│ React   │      │ + Lambda    │
│ Static  │      │ or EC2      │
└─────────┘      └──────┬──────┘
                        │
                        ↓
                 ┌─────────────┐
                 │ RDS         │
                 │ PostgreSQL  │
                 └─────────────┘
```

**Cost:** ~$50-100/month

---

## Recommended Setup for You

### Phase 1: Development (NOW)
```
Your Computer
├── PostgreSQL (localhost:5432)
├── FastAPI (localhost:8000)
└── React (localhost:3000)
```

### Phase 2: MVP Deployment
```
DigitalOcean Droplet ($12/month)
subdomain.jgaffiliates.com
├── PostgreSQL
├── FastAPI
├── Nginx
└── React (static files)
```

### Phase 3: Scale Up
```
Frontend: Vercel (FREE)
API: DigitalOcean ($12/month)
DB: Managed PostgreSQL ($15/month)
```

---

## Detailed Setup: Single Server (Recommended Start)

### 1. Get a DigitalOcean Droplet
- Ubuntu 22.04
- $12/month (2GB RAM)
- Choose datacenter near your users

### 2. Setup Domain
```
DNS Records (at your domain registrar):
A Record: subdomain.jgaffiliates.com → [Droplet IP]
```

### 3. Install Everything
```bash
# SSH into droplet
ssh root@[droplet-ip]

# Install dependencies
sudo apt update
sudo apt install postgresql nginx python3-pip nodejs npm

# Clone your repo
git clone https://github.com/tweedledee101/TradingCards.git
cd TradingCards

# Setup database
sudo -u postgres psql -c "CREATE DATABASE trading_cards;"
sudo -u postgres psql -d trading_cards -f backend/models/schema.sql

# Install Python packages
cd backend
pip install -r requirements.txt

# Setup environment
cp .env.example .env
nano .env  # Add production credentials
```

### 4. Configure Nginx
```nginx
# /etc/nginx/sites-available/tradingcards
server {
    listen 80;
    server_name subdomain.jgaffiliates.com;

    # API endpoints
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Frontend
    location / {
        root /var/www/tradingcards/frontend/build;
        try_files $uri /index.html;
    }
}
```

### 5. Run API as Service
```bash
# /etc/systemd/system/tradingcards-api.service
[Unit]
Description=Trading Cards API
After=network.target

[Service]
User=root
WorkingDirectory=/root/TradingCards
ExecStart=/usr/local/bin/uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable tradingcards-api
sudo systemctl start tradingcards-api
```

### 6. SSL Certificate
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d subdomain.jgaffiliates.com
```

---

## Environment Variables

### Development (.env)
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_cards
DB_USER=postgres
DB_PASSWORD=your_local_password
```

### Production (.env)
```bash
DB_HOST=localhost  # or managed DB IP
DB_PORT=5432
DB_NAME=trading_cards
DB_USER=tradingcards_user
DB_PASSWORD=strong_production_password
EBAY_TOKEN=your_production_token
```

---

## Communication Flow

### Development
```
Browser → http://localhost:3000 (React)
React → http://localhost:8000/api (FastAPI)
FastAPI → localhost:5432 (PostgreSQL)
```

### Production (Single Server)
```
Browser → https://subdomain.jgaffiliates.com
Nginx → /api/* → localhost:8000 (FastAPI)
Nginx → /* → /var/www/frontend/build (React)
FastAPI → localhost:5432 (PostgreSQL)
```

### Production (Separate Services)
```
Browser → https://subdomain.jgaffiliates.com (Vercel)
React → https://api.subdomain.jgaffiliates.com (API Server)
FastAPI → [private-ip]:5432 (Managed DB)
```

---

## Next Steps

1. **Finish Development** - Build React frontend locally
2. **Test Locally** - Make sure everything works on localhost
3. **Get DigitalOcean Droplet** - $12/month
4. **Deploy Single Server** - Follow setup above
5. **Add SSL** - Free with Let's Encrypt
6. **Scale Later** - Move to separate services if needed

---

## Quick Deploy Script

I can create a deployment script that automates this. Want me to?

**Estimated Time to Deploy:** 30 minutes  
**Estimated Cost:** $12/month
