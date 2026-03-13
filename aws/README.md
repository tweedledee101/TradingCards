# AWS Infrastructure

CloudFormation templates and deployment scripts for CardPulse Trading Card Platform.

## 📁 Structure

```
aws/
├── cloudformation/
│   └── ebay-compliance-lambda.yaml    # eBay compliance webhook
├── deploy-ebay-compliance.sh          # Linux/Mac deployment
└── deploy-ebay-compliance.bat         # Windows deployment
```

## 🚀 Quick Start

### Deploy eBay Compliance
```bash
# Get Hosted Zone ID
aws route53 list-hosted-zones --query 'HostedZones[?Name==`jgaffiliated.com.`].Id' --output text

# Deploy (Linux/Mac)
./deploy-ebay-compliance.sh <HOSTED_ZONE_ID>

# Deploy (Windows)
deploy-ebay-compliance.bat <HOSTED_ZONE_ID>
```

## 📚 Documentation

- [AWS Deployment Guide](../docs/AWS-DEPLOYMENT-GUIDE.md) - Complete deployment guide
- [AWS Quick Reference](../docs/AWS-QUICK-REFERENCE.md) - Quick commands

## 🎯 What's Deployed

### Phase 1: eBay Compliance (Current)
- Lambda function for eBay marketplace account deletion notifications
- API Gateway with custom domain
- Route53 DNS configuration
- ACM SSL certificate

**Endpoint:** `https://cardpulse.jgaffiliated.com/api/webhooks/ebay/account-deletion`

### Phase 2: Full Platform (Coming Soon)
- VPC + Networking
- RDS PostgreSQL
- ECS Fargate (API + Scrapers)
- S3 + CloudFront (Frontend)
- EventBridge (Scheduler)
- Secrets Manager

## 💰 Cost

**Phase 1:** ~$0.50/month  
**Phase 2:** ~$69/month (containerized) or ~$34/month (serverless)

See [AWS Deployment Guide](../docs/AWS-DEPLOYMENT-GUIDE.md) for detailed cost breakdown.

## 🔐 Security

- All credentials in Secrets Manager
- Private subnets for database
- HTTPS only
- Security groups with least privilege
- CloudWatch logging enabled

## 📊 Monitoring

- CloudWatch Logs: `/aws/lambda/ebay-compliance-webhook`
- CloudWatch Metrics: Lambda invocations, errors, duration
- CloudWatch Alarms: Error rate, cost thresholds

## 🛠️ Management

### View Stack
```bash
aws cloudformation describe-stacks --stack-name cardpulse-ebay-compliance
```

### View Logs
```bash
aws logs tail /aws/lambda/ebay-compliance-webhook --follow
```

### Update Stack
```bash
./deploy-ebay-compliance.sh <HOSTED_ZONE_ID>
```

### Delete Stack
```bash
aws cloudformation delete-stack --stack-name cardpulse-ebay-compliance
```

## 🎯 Roadmap

- [x] eBay compliance Lambda
- [ ] Full platform CloudFormation templates
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Multi-environment support (dev/staging/prod)
- [ ] Auto-scaling configuration
- [ ] Disaster recovery setup

---

**Domain:** cardpulse.jgaffiliated.com  
**Region:** us-east-1  
**Status:** Phase 1 ready to deploy
