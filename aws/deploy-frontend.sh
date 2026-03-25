#!/usr/bin/env bash
# Deploy S3 + CloudFront SPA (us-east-1). Prerequisite: ACM cert in us-east-1 with correct SANs.
set -euo pipefail

STACK_NAME="${STACK_NAME:-ragnarok-frontend-spa}"
REGION="${AWS_REGION:-us-east-1}"
TEMPLATE="$(dirname "$0")/cloudformation/frontend-spa.yaml"

usage() {
  echo "Usage: AWS_PROFILE=your-profile $0 <HOSTED_ZONE_ID> <ACM_CERTIFICATE_ARN_US_EAST_1> [include-www:true|false]"
  echo ""
  echo "Example:"
  echo "  $0 Z1234567890ABC arn:aws:acm:us-east-1:123456789012:certificate/abcd-..."
  echo ""
  echo "After deploy, sync the built site:"
  echo "  cd frontend && npm run build"
  echo "  aws s3 sync dist/ s3://\$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query \"Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue\" --output text) --delete"
  echo "  aws cloudfront create-invalidation --distribution-id \$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query \"Stacks[0].Outputs[?OutputKey=='CloudFrontDistributionId'].OutputValue\" --output text) --paths \"/*\""
  exit 1
}

if [[ $# -lt 2 ]]; then
  usage
fi

HOSTED_ZONE_ID="$1"
CERT_ARN="$2"
INCLUDE_WWW="${3:-true}"

aws cloudformation deploy \
  --template-file "$TEMPLATE" \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "HostedZoneId=${HOSTED_ZONE_ID}" \
    "AcmCertificateArn=${CERT_ARN}" \
    "IncludeWwwAlias=${INCLUDE_WWW}"

aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table
