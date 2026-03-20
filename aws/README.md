# AWS Infrastructure

CloudFormation templates for CardPulse Trading Card Platform.

## Structure

```
aws/
├── cloudformation/
│   └── ebay-compliance-lambda.yaml    # eBay compliance webhook
├── deploy-ebay-compliance.sh          # Linux/Mac deployment
└── deploy-ebay-compliance.bat         # Windows deployment
```

## Deploy eBay Compliance

```bash
# Get Hosted Zone ID
aws route53 list-hosted-zones --query 'HostedZones[?Name==`jgaffiliated.com.`].Id' --output text

# Deploy
./aws/deploy-ebay-compliance.sh <HOSTED_ZONE_ID>

# Test
curl https://cardpulse.jgaffiliated.com/api/webhooks/ebay/account-deletion
```

## What's Deployed

**Phase 1: eBay Compliance** (~$0.50/month)
- Lambda function for eBay account deletion notifications
- API Gateway with custom domain
- Route53 DNS + ACM SSL certificate

**Endpoint:** `https://cardpulse.jgaffiliated.com/api/webhooks/ebay/account-deletion`

## Management

```bash
aws cloudformation describe-stacks --stack-name cardpulse-ebay-compliance
aws logs tail /aws/lambda/ebay-compliance-webhook --follow
aws cloudformation delete-stack --stack-name cardpulse-ebay-compliance
```

**Domain:** cardpulse.jgaffiliated.com | **Region:** us-east-1
