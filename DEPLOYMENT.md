# Deployment Quick Reference

## TL;DR - Where Everything Lives

### Development (NOW)
- **Database:** Your computer (localhost:5432)
- **API:** Your computer (localhost:8000)
- **Frontend:** Your computer (localhost:3000)
- **URL:** http://localhost:3000

### Production (Recommended)
- **Everything:** One DigitalOcean server
- **Database:** Same server (localhost:5432)
- **API:** Same server (localhost:8000, proxied by Nginx)
- **Frontend:** Same server (static files served by Nginx)
- **URL:** https://subdomain.jgaffiliates.com
- **Cost:** $12/month

## How They Talk

```
User Browser
    ↓
subdomain.jgaffiliates.com (Nginx)
    ├─ /api/* → FastAPI → PostgreSQL
    └─ /* → React static files
```

## Setup Steps (30 minutes)

1. **Get Server:** DigitalOcean droplet ($12/month)
2. **Point Domain:** DNS A record to server IP
3. **Install:** PostgreSQL, Python, Nginx
4. **Deploy Code:** Git clone your repo
5. **Configure:** Nginx routes, SSL certificate
6. **Start:** API runs as systemd service
7. **Done:** Visit https://subdomain.jgaffiliates.com

## Files to Read

- `docs/DEPLOYMENT-ARCHITECTURE.md` - Full details
- `docs/DEPLOYMENT-DIAGRAMS.md` - Visual guides

## Need Help?

I can create:
- Deployment scripts
- Docker setup
- CI/CD pipeline

Just ask! 🚀
