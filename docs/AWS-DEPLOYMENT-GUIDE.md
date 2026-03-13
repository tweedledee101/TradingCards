# AWS Deployment Guide - CardPulse Trading Card Platform

**Domain:** `cardpulse.jgaffiliated.com`  
**Infrastructure:** 100% AWS with CloudFormation  
**Goal:** Scalable, cost-effective, monetization-ready

---

## 🎯 Deployment Strategy

### Phase 1: eBay Compliance (NOW)
**Goal:** Unblock eBay API access  
**Cost:** ~$0/month (Lambda free tier)  
**Time:** 10 minutes

### Phase 2: Full Platform (NEXT)
**Goal:** Production-ready platform  
**Cost:** ~$50-100/month  
**Time:** 1-2 hours

### Phase 3: Monetization (FUTURE)
**Goal:** Multi-tenant SaaS platform  
**Cost:** Variable (scales with users)  
**Time:** 2-4 weeks

---

## 📐 Architecture Overview

### Current (Development)
```
Your Computer (WSL Ubuntu)
├── PostgreSQL (localhost:5432)
├── FastAPI (localhost:8000)
└── React (localhost:3000)
```

### Phase 1: eBay Compliance Only
```
AWS Lambda (Python 3.11)
└── API Gateway → cardpulse.jgaffiliated.com
    └── /api/webhooks/ebay/account-deletion
```

### Phase 2: Full Platform (Recommended)
```
┌─────────────────────────────────────────────────────────┐
│ CloudFront CDN                                          │
│ cardpulse.jgaffiliated.com                             │
└────────┬────────────────────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
    ↓         ↓
┌─────────┐ ┌──────────────────────────────────────────┐
│ S3      │ │ API Gateway + Lambda (Serverless)        │
│ React   │ │ OR                                        │
│ Static  │ │ ALB + ECS Fargate (Containerized)        │
└─────────┘ └────────┬─────────────────────────────────┘
                     │
                     ↓
            ┌────────────────────┐
            │ RDS PostgreSQL     │
            │ (Multi-AZ)         │
            └────────────────────┘
            
┌──────────────────────────────────────────────────────────┐
│ EventBridge (Scheduler)                                  │
│ └── Daily at 2 AM → Lambda → Run scrapers                │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ Secrets Manager                                          │
│ └── eBay API keys, DB credentials                        │
└──────────────────────────────────────────────────────────┘
```

### Phase 3: Multi-Tenant SaaS
```
┌─────────────────────────────────────────────────────────┐
│ CloudFront + WAF (DDoS protection)                      │
│ cardpulse.jgaffiliated.com                             │
└────────┬────────────────────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
    ↓         ↓
┌─────────┐ ┌──────────────────────────────────────────┐
│ S3      │ │ ALB + ECS Fargate (Auto-scaling)         │
│ React   │ │ ├── API Service (FastAPI)                │
│ Static  │ │ ├── Scraper Service (Selenium)           │
└─────────┘ │ └── Worker Service (Background jobs)     │
            └────────┬─────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ↓                         ↓
┌────────────────┐      ┌────────────────────┐
│ RDS PostgreSQL │      │ ElastiCache Redis  │
│ (Multi-AZ)     │      │ (Session/Cache)    │
└────────────────┘      └────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ Cognito (User Authentication)                            │
│ └── Email/password, social login, MFA                    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ SES (Email Alerts)                                       │
│ └── Price alerts, daily reports, notifications           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ CloudWatch (Monitoring & Alerts)                         │
│ └── Metrics, logs, alarms, dashboards                    │
└──────────────────────────────────────────────────────────┘
```

---

## 💰 Cost Analysis

### Phase 1: eBay Compliance Only
| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 1M requests/month | $0 (free tier) |
| API Gateway | 1M requests/month | $0 (free tier) |
| Route53 | 1 hosted zone | $0.50/month |
| ACM Certificate | 1 cert | $0 (free) |
| **Total** | | **~$0.50/month** |

### Phase 2: Full Platform (Serverless)
| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 10M requests/month | $2.00/month |
| API Gateway | 10M requests/month | $3.50/month |
| RDS PostgreSQL | db.t3.micro | $15/month |
| S3 + CloudFront | 100GB transfer | $10/month |
| EventBridge | 30 schedules | $0 (free tier) |
| Secrets Manager | 5 secrets | $2.50/month |
| Route53 | 1 hosted zone | $0.50/month |
| **Total** | | **~$33.50/month** |

### Phase 2: Full Platform (Containerized - Recommended for Growth)
| Service | Usage | Cost |
|---------|-------|------|
| ECS Fargate | 0.25 vCPU, 0.5GB | $10/month |
| ALB | 1 load balancer | $16/month |
| RDS PostgreSQL | db.t3.small | $30/month |
| S3 + CloudFront | 100GB transfer | $10/month |
| EventBridge | 30 schedules | $0 (free tier) |
| Secrets Manager | 5 secrets | $2.50/month |
| Route53 | 1 hosted zone | $0.50/month |
| **Total** | | **~$69/month** |

### Phase 3: Multi-Tenant SaaS (100 users)
| Service | Usage | Cost |
|---------|-------|------|
| ECS Fargate | 1 vCPU, 2GB (auto-scale) | $40/month |
| ALB | 1 load balancer | $16/month |
| RDS PostgreSQL | db.t3.medium (Multi-AZ) | $120/month |
| ElastiCache Redis | cache.t3.micro | $15/month |
| S3 + CloudFront | 500GB transfer | $40/month |
| Cognito | 100 MAU | $0 (free tier) |
| SES | 10K emails/month | $1/month |
| WAF | Basic rules | $10/month |
| CloudWatch | Logs + metrics | $10/month |
| **Total** | | **~$252/month** |

**Revenue Target:** $10-50/user/month = $1,000-5,000/month  
**Profit Margin:** 75-95% after infrastructure costs

---

## 🚀 Phase 1: Deploy eBay Compliance (NOW)

### Prerequisites
- AWS CLI installed and configured
- Route53 hosted zone for `jgaffiliated.com`
- AWS account with permissions

### Step 1: Get Hosted Zone ID
```bash
aws route53 list-hosted-zones --query 'HostedZones[?Name==`jgaffiliated.com.`].Id' --output text
```

### Step 2: Deploy CloudFormation Stack
```bash
cd /home/tweedledee101/TradingCards
chmod +x aws/deploy-ebay-compliance.sh
./aws/deploy-ebay-compliance.sh <HOSTED_ZONE_ID>
```

### Step 3: Verify Deployment
```bash
# Test endpoint
curl https://cardpulse.jgaffiliated.com/api/webhooks/ebay/account-deletion

# Expected response:
# {"status":"healthy","service":"ebay-compliance-webhook","timestamp":"2025-02-15T..."}
```

### Step 4: Configure eBay
1. Go to eBay Developer Portal
2. Navigate to your production keyset
3. Configure marketplace account deletion notification:
   - **Endpoint URL:** `https://cardpulse.jgaffiliated.com/api/webhooks/ebay/account-deletion`
   - **Verification Token:** (generate random string)
4. Submit for verification

### Step 5: Update .env
```bash
# backend/.env
EBAY_COMPLIANCE_ENDPOINT=https://cardpulse.jgaffiliated.com/api/webhooks/ebay/account-deletion
```

---

## 🏗️ Phase 2: Deploy Full Platform

### Option A: Serverless (Cheapest, ~$34/month)

**Best for:**
- MVP/testing
- Low traffic (<1M requests/month)
- Simple deployment

**Limitations:**
- Cold starts (1-2s delay)
- 15-minute Lambda timeout
- Limited for long-running scrapers

### Option B: Containerized (Recommended, ~$69/month)

**Best for:**
- Production workloads
- Consistent performance
- Long-running scrapers
- Future growth

**Advantages:**
- No cold starts
- Full control
- Easy to scale
- Better for Selenium/Chrome

### Recommended: Option B (Containerized)

I'll create CloudFormation templates for:
1. **VPC + Networking** - Private subnets, NAT gateway
2. **RDS PostgreSQL** - Database with backups
3. **ECS Fargate** - Containerized API + scrapers
4. **ALB** - Load balancer with SSL
5. **S3 + CloudFront** - Frontend hosting
6. **EventBridge** - Scheduled scraper runs
7. **Secrets Manager** - Secure credential storage

---

## 📋 Service Breakdown

### API Service (FastAPI)
- **Deployment:** ECS Fargate container
- **Scaling:** 1-5 tasks (auto-scale on CPU)
- **Health Check:** `/health` endpoint
- **Logs:** CloudWatch Logs

### Scraper Service (Selenium)
- **Deployment:** ECS Fargate container with Chrome
- **Trigger:** EventBridge schedule (daily 2 AM)
- **Timeout:** 1 hour max
- **Logs:** CloudWatch Logs

### Frontend (React)
- **Deployment:** S3 static hosting
- **CDN:** CloudFront with SSL
- **Cache:** 1 hour TTL
- **Invalidation:** On deploy

### Database (PostgreSQL)
- **Deployment:** RDS Multi-AZ
- **Backups:** Daily automated
- **Retention:** 7 days
- **Encryption:** At rest + in transit

### Scheduler (EventBridge)
- **Triggers:** Daily scraper runs
- **Target:** ECS Fargate task
- **Retry:** 3 attempts

---

## 🔐 Security Best Practices

### Secrets Management
- Store all credentials in Secrets Manager
- Rotate secrets every 90 days
- Never commit secrets to Git

### Network Security
- Private subnets for database
- Security groups with least privilege
- VPC endpoints for AWS services

### Application Security
- HTTPS only (enforce via CloudFront)
- CORS configured properly
- Rate limiting on API Gateway
- WAF rules (Phase 3)

### Monitoring
- CloudWatch alarms for errors
- Log all API requests
- Track scraper failures
- Monitor costs

---

## 🎯 Monetization Strategy

### Pricing Tiers

**Free Tier**
- 10 cards in watchlist
- Daily updates
- Basic analytics
- Ad-supported

**Pro Tier ($19/month)**
- Unlimited watchlist
- Hourly updates
- Advanced analytics
- Price alerts
- No ads

**Premium Tier ($49/month)**
- Everything in Pro
- Custom scrapers
- API access
- Priority support
- White-label option

### Revenue Projections

| Users | Free | Pro | Premium | MRR | ARR |
|-------|------|-----|---------|-----|-----|
| 100 | 70 | 25 | 5 | $725 | $8,700 |
| 500 | 350 | 125 | 25 | $3,625 | $43,500 |
| 1000 | 700 | 250 | 50 | $7,250 | $87,000 |

**Infrastructure Cost at 1000 users:** ~$250/month  
**Profit Margin:** 97% ($7,000/month profit)

---

## 📊 Monitoring & Observability

### CloudWatch Dashboards
- API request rate
- Error rate
- Response time (p50, p95, p99)
- Database connections
- Scraper success rate
- Cost tracking

### Alarms
- API error rate >5%
- Database CPU >80%
- Scraper failures >3
- Monthly cost >$150

### Logs
- API access logs (7 days)
- Application logs (30 days)
- Scraper logs (30 days)
- Database logs (7 days)

---

## 🔄 CI/CD Pipeline (Future)

### GitHub Actions Workflow
```yaml
on:
  push:
    branches: [main]

jobs:
  deploy:
    - Build Docker images
    - Push to ECR
    - Update ECS service
    - Invalidate CloudFront
    - Run smoke tests
```

---

## 📝 Next Steps

### Immediate (Today)
1. ✅ Deploy eBay compliance Lambda
2. ✅ Configure eBay Developer Portal
3. ✅ Test endpoint
4. ✅ Enable production eBay API

### Short Term (This Week)
5. Create full platform CloudFormation templates
6. Deploy RDS database
7. Containerize FastAPI app
8. Deploy to ECS Fargate
9. Deploy frontend to S3/CloudFront

### Medium Term (This Month)
10. Add EventBridge scheduler
11. Implement monitoring
12. Load testing
13. Documentation
14. Beta testing

### Long Term (Next Quarter)
15. User authentication (Cognito)
16. Email alerts (SES)
17. Pricing tiers
18. Payment processing (Stripe)
19. Marketing site
20. Launch! 🚀

---

## 📚 Documentation Structure

```
TradingCards/
├── aws/
│   ├── cloudformation/
│   │   ├── ebay-compliance-lambda.yaml       ✅ Created
│   │   ├── vpc-networking.yaml               ⏳ Next
│   │   ├── rds-database.yaml                 ⏳ Next
│   │   ├── ecs-api-service.yaml              ⏳ Next
│   │   ├── ecs-scraper-service.yaml          ⏳ Next
│   │   ├── s3-cloudfront-frontend.yaml       ⏳ Next
│   │   ├── eventbridge-scheduler.yaml        ⏳ Next
│   │   └── full-stack.yaml                   ⏳ Next (master)
│   ├── deploy-ebay-compliance.sh             ✅ Created
│   ├── deploy-full-platform.sh               ⏳ Next
│   └── teardown.sh                           ⏳ Next
├── docs/
│   └── AWS-DEPLOYMENT-GUIDE.md               ✅ This file
└── README.md                                 ⏳ Update
```

---

**Status:** Phase 1 ready to deploy  
**Next:** Deploy eBay compliance, then create Phase 2 templates  
**Timeline:** eBay compliance today, full platform this week
