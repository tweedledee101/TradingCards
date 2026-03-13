#!/bin/bash

# Deploy eBay Compliance Lambda to AWS
# Usage: ./deploy-ebay-compliance.sh <hosted-zone-id>

set -e

STACK_NAME="cardpulse-ebay-compliance"
TEMPLATE_FILE="aws/cloudformation/ebay-compliance-lambda.yaml"
REGION="us-east-1"  # Change if needed

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: ./deploy-ebay-compliance.sh <hosted-zone-id>"
    echo ""
    echo "Find your Hosted Zone ID:"
    echo "  aws route53 list-hosted-zones --query 'HostedZones[?Name==\`jgaffiliated.com.\`].Id' --output text"
    exit 1
fi

HOSTED_ZONE_ID=$1

echo "🚀 Deploying eBay Compliance Lambda..."
echo "   Stack: $STACK_NAME"
echo "   Region: $REGION"
echo "   Domain: cardpulse.jgaffiliated.com"
echo ""

# Deploy stack
aws cloudformation deploy \
    --template-file $TEMPLATE_FILE \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        DomainName=cardpulse.jgaffiliated.com \
        HostedZoneId=$HOSTED_ZONE_ID \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION

echo ""
echo "✅ Deployment complete!"
echo ""

# Get outputs
echo "📋 Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo "🔗 eBay Compliance Endpoint:"
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text

echo ""
echo "✅ Next Steps:"
echo "   1. Copy the API endpoint URL above"
echo "   2. Go to eBay Developer Portal"
echo "   3. Configure marketplace account deletion notification endpoint"
echo "   4. Test with: curl https://cardpulse.jgaffiliated.com/api/webhooks/ebay/account-deletion"
