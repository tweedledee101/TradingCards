# AWS Infrastructure

CloudFormation templates for Ragnarok Gaming Trading Card Platform.

## Structure

```
aws/
├── cloudformation/
│   ├── ebay-compliance-lambda.yaml    # eBay compliance webhook
│   └── rds.yaml                       # RDS PostgreSQL with self-contained VPC
├── apply-rds-migrations.sh            # Apply schema + migrations to RDS
├── migrate-to-rds.sh                  # Migrate local data to RDS
├── deploy-ebay-compliance.sh          # Linux/Mac deployment
└── deploy-ebay-compliance.bat         # Windows deployment
```

## Deploy eBay Compliance

```bash
# Get Hosted Zone ID
aws route53 list-hosted-zones --query 'HostedZones[?Name==`ragnarokgamez.com.`].Id' --output text

# Deploy
./aws/deploy-ebay-compliance.sh <HOSTED_ZONE_ID>

# Test
curl https://ragnarokgamez.com/api/webhooks/ebay/account-deletion
```

## What's Deployed

**RDS PostgreSQL** (free tier)
- Endpoint: `cardpulse-db.ckvp9bhavaww.us-east-1.rds.amazonaws.com:5432`
- Database: `trading_cards`, User: `cardpulse`
- Self-contained VPC (10.0.0.0/16), 2 public subnets, internet gateway
- db.t3.micro, 20GB gp2, postgres 14
- Schema + all migrations (001-011) applied

**eBay Compliance Lambda** (~$0.50/month)
- Lambda function for eBay account deletion notifications
- API Gateway with custom domain
- Route53 DNS + ACM SSL certificate

**Endpoint:** `https://ragnarokgamez.com/api/webhooks/ebay/account-deletion`

## Management

```bash
aws cloudformation describe-stacks --stack-name cardpulse-ebay-compliance
aws logs tail /aws/lambda/ebay-compliance-webhook --follow
aws cloudformation delete-stack --stack-name cardpulse-ebay-compliance
```

**Domain:** ragnarokgamez.com | **Region:** us-east-1
