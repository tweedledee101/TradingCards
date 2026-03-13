# AWS Deployment Quick Reference

## 🚀 Deploy eBay Compliance (5 minutes)

### 1. Get Hosted Zone ID
```bash
aws route53 list-hosted-zones --query 'HostedZones[?Name==`jgaffiliated.com.`].Id' --output text
```

### 2. Deploy Stack
```bash
# Linux/Mac
cd /home/tweedledee101/TradingCards
chmod +x aws/deploy-ebay-compliance.sh
./aws/deploy-ebay-compliance.sh <HOSTED_ZONE_ID>

# Windows
cd \wsl.localhost\Ubuntu\home\tweedledee101\TradingCards
aws\deploy-ebay-compliance.bat <HOSTED_ZONE_ID>
```

### 3. Test Endpoint
```bash
curl https://cardpulse.jgaffiliated.com/api/webhooks/ebay/account-deletion
```

### 4. Configure eBay
- Go to eBay Developer Portal
- Add endpoint: `https://cardpulse.jgaffiliated.com/api/webhooks/ebay/account-deletion`
- Submit for verification

---

## 📋 Stack Details

**Stack Name:** `cardpulse-ebay-compliance`  
**Region:** `us-east-1`  
**Domain:** `cardpulse.jgaffiliated.com`

### Resources Created
- Lambda function (Python 3.11)
- API Gateway (HTTP API)
- ACM Certificate (SSL)
- Route53 DNS record
- CloudWatch Log Group
- IAM Role

### Cost
- **Lambda:** $0 (free tier)
- **API Gateway:** $0 (free tier)
- **Route53:** $0.50/month
- **Total:** ~$0.50/month

---

## 🔧 Management Commands

### View Stack Status
```bash
aws cloudformation describe-stacks --stack-name cardpulse-ebay-compliance --region us-east-1
```

### View Logs
```bash
aws logs tail /aws/lambda/ebay-compliance-webhook --follow --region us-east-1
```

### Update Stack
```bash
./aws/deploy-ebay-compliance.sh <HOSTED_ZONE_ID>
```

### Delete Stack
```bash
aws cloudformation delete-stack --stack-name cardpulse-ebay-compliance --region us-east-1
```

---

## 📊 Monitoring

### CloudWatch Logs
```bash
# View recent logs
aws logs tail /aws/lambda/ebay-compliance-webhook --since 1h --region us-east-1

# Follow logs in real-time
aws logs tail /aws/lambda/ebay-compliance-webhook --follow --region us-east-1
```

### Lambda Metrics
```bash
# Invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=ebay-compliance-webhook \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

---

## 🐛 Troubleshooting

### Certificate Validation Pending
**Issue:** Stack stuck at "CREATE_IN_PROGRESS" for Certificate  
**Solution:** Check Route53 for CNAME validation records, may take 5-30 minutes

### Domain Not Resolving
**Issue:** `curl` returns "Could not resolve host"  
**Solution:** DNS propagation takes 5-60 minutes, check with `dig cardpulse.jgaffiliated.com`

### Lambda Errors
**Issue:** 500 errors from endpoint  
**Solution:** Check CloudWatch Logs:
```bash
aws logs tail /aws/lambda/ebay-compliance-webhook --since 1h --region us-east-1
```

### Stack Rollback
**Issue:** Stack creation failed and rolled back  
**Solution:** Check CloudFormation events:
```bash
aws cloudformation describe-stack-events --stack-name cardpulse-ebay-compliance --region us-east-1
```

---

## 📁 Files Created

```
TradingCards/
├── aws/
│   ├── cloudformation/
│   │   └── ebay-compliance-lambda.yaml    # CloudFormation template
│   ├── deploy-ebay-compliance.sh          # Linux/Mac deployment
│   └── deploy-ebay-compliance.bat         # Windows deployment
└── docs/
    ├── AWS-DEPLOYMENT-GUIDE.md            # Full deployment guide
    └── AWS-QUICK-REFERENCE.md             # This file
```

---

## 🔗 Useful Links

- **AWS Console:** https://console.aws.amazon.com/cloudformation
- **Lambda Console:** https://console.aws.amazon.com/lambda
- **API Gateway Console:** https://console.aws.amazon.com/apigateway
- **Route53 Console:** https://console.aws.amazon.com/route53
- **CloudWatch Logs:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups

---

## 🎯 Next Steps

After eBay compliance is deployed:

1. **Test eBay API** - Verify production keyset works
2. **Deploy Full Platform** - See [AWS Deployment Guide](./AWS-DEPLOYMENT-GUIDE.md)
3. **Setup Monitoring** - CloudWatch alarms
4. **Configure CI/CD** - GitHub Actions

---

**Status:** Ready to deploy  
**Estimated Time:** 5-10 minutes  
**Cost:** ~$0.50/month
