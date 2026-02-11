# Deployment Options - Visual Guide

## Current: Development (Your Computer)

```
┌─────────────────────────────────────────────────────┐
│  Your Computer (localhost)                          │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   React      │→ │   FastAPI    │→ │PostgreSQL │ │
│  │   :3000      │  │   :8000      │  │   :5432   │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│                                                      │
│  Browser: http://localhost:3000                     │
└─────────────────────────────────────────────────────┘
```

---

## Recommended: Single Server (DigitalOcean)

```
                    Internet
                       │
                       ↓
        subdomain.jgaffiliates.com
                       │
                       ↓
┌──────────────────────────────────────────────────────┐
│  DigitalOcean Droplet ($12/month)                    │
│  Ubuntu 22.04 - 2GB RAM                              │
│                                                       │
│  ┌────────────────────────────────────────────────┐  │
│  │  Nginx (Port 80/443)                           │  │
│  │  - SSL Certificate (Let's Encrypt)             │  │
│  │  - Routes /api/* to FastAPI                    │  │
│  │  - Routes /* to React static files             │  │
│  └───────────┬────────────────────┬────────────────┘  │
│              │                    │                   │
│              ↓                    ↓                   │
│  ┌──────────────────┐  ┌──────────────────┐          │
│  │  FastAPI         │  │  React           │          │
│  │  Port 8000       │  │  Static Files    │          │
│  │  (Python)        │  │  /var/www/       │          │
│  └────────┬─────────┘  └──────────────────┘          │
│           │                                           │
│           ↓                                           │
│  ┌──────────────────┐                                │
│  │  PostgreSQL      │                                │
│  │  Port 5432       │                                │
│  │  (localhost)     │                                │
│  └──────────────────┘                                │
│                                                       │
└───────────────────────────────────────────────────────┘

User Flow:
1. User visits: https://subdomain.jgaffiliates.com
2. Nginx serves React app
3. React calls: https://subdomain.jgaffiliates.com/api/trending
4. Nginx forwards to FastAPI (localhost:8000)
5. FastAPI queries PostgreSQL (localhost:5432)
6. Response flows back to user
```

**Pros:**
- Simple setup
- Low cost ($12/month)
- Everything in one place
- Easy to manage

**Cons:**
- Single point of failure
- Limited scalability
- Manual backups needed

---

## Future: Separate Services (Scalable)

```
                    Internet
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ↓                           ↓
┌──────────────────┐      ┌──────────────────┐
│  Vercel (FREE)   │      │  DigitalOcean    │
│  Frontend        │      │  API Server      │
│                  │      │  ($12/month)     │
│  subdomain.      │      │                  │
│  jgaffiliates    │      │  api.subdomain.  │
│  .com            │      │  jgaffiliates    │
│                  │      │  .com            │
│  ┌────────────┐  │      │  ┌────────────┐  │
│  │   React    │  │      │  │  FastAPI   │  │
│  │   Static   │  │      │  │  Port 8000 │  │
│  └────────────┘  │      │  └──────┬─────┘  │
└──────────────────┘      └─────────┼────────┘
                                    │
                                    │ Private Network
                                    ↓
                          ┌──────────────────┐
                          │  DigitalOcean    │
                          │  Managed DB      │
                          │  ($15/month)     │
                          │                  │
                          │  ┌────────────┐  │
                          │  │PostgreSQL  │  │
                          │  │Port 5432   │  │
                          │  └────────────┘  │
                          └──────────────────┘

User Flow:
1. User visits: https://subdomain.jgaffiliates.com (Vercel)
2. Vercel serves React app (CDN, fast worldwide)
3. React calls: https://api.subdomain.jgaffiliates.com/api/trending
4. API server processes request
5. API queries managed database (private network)
6. Response flows back to user
```

**Pros:**
- Frontend on CDN (fast globally)
- API can scale independently
- Managed database (auto backups)
- More professional

**Cons:**
- More complex setup
- Higher cost ($27/month)
- Need to manage CORS

---

## How They Communicate

### Development
```
React (localhost:3000)
  ↓ HTTP Request
FastAPI (localhost:8000)
  ↓ SQL Query
PostgreSQL (localhost:5432)
  ↓ Data
FastAPI
  ↓ JSON Response
React
```

### Production (Single Server)
```
Browser
  ↓ HTTPS (subdomain.jgaffiliates.com)
Nginx (Port 443)
  ├→ /api/* → FastAPI (localhost:8000)
  │              ↓
  │         PostgreSQL (localhost:5432)
  │
  └→ /* → React Static Files
```

### Production (Separate)
```
Browser
  ↓ HTTPS
Vercel CDN (React)
  ↓ HTTPS API Call
DigitalOcean API Server
  ↓ Private Network
Managed PostgreSQL
```

---

## Configuration Files

### Single Server Nginx Config
```nginx
server {
    listen 443 ssl;
    server_name subdomain.jgaffiliates.com;
    
    ssl_certificate /etc/letsencrypt/live/subdomain.jgaffiliates.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/subdomain.jgaffiliates.com/privkey.pem;
    
    # API
    location /api {
        proxy_pass http://localhost:8000;
    }
    
    # Frontend
    location / {
        root /var/www/tradingcards/build;
        try_files $uri /index.html;
    }
}
```

### React API Config (Development)
```javascript
// src/config.js
const API_URL = process.env.NODE_ENV === 'production' 
  ? 'https://subdomain.jgaffiliates.com/api'
  : 'http://localhost:8000/api';
```

### React API Config (Separate Services)
```javascript
// src/config.js
const API_URL = process.env.NODE_ENV === 'production' 
  ? 'https://api.subdomain.jgaffiliates.com/api'
  : 'http://localhost:8000/api';
```

---

## Summary

**Start with:** Single Server (Simple, $12/month)  
**Scale to:** Separate Services (Professional, $27/month)  
**Enterprise:** AWS/GCP (Complex, $100+/month)

**My Recommendation:** Deploy single server first, scale later if needed.

Want me to create deployment scripts?
