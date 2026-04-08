#!/usr/bin/env bash
# Deploy dev SPA stack: https://dev.ragnarokgamez.com (us-east-1).
# ACM certificate must include dev.ragnarokgamez.com (or *.ragnarokgamez.com).
set -euo pipefail

STACK_NAME="${STACK_NAME:-ragnarok-frontend-spa-dev}"
REGION="${AWS_REGION:-us-east-1}"
TEMPLATE="$(dirname "$0")/cloudformation/frontend-spa-dev.yaml"

usage() {
  echo "Usage: AWS_PROFILE=your-profile $0 <HOSTED_ZONE_ID> <ACM_CERTIFICATE_ARN_US_EAST_1>"
  echo ""
  echo "Cert must list SAN: dev.ragnarokgamez.com (or use a wildcard cert for the zone)."
  echo ""
  echo "Build and publish:"
  echo "  cd frontend && npm run build:dev"
  echo "  aws s3 sync dist/ s3://\$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query \"Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue\" --output text) --delete --profile \${AWS_PROFILE:-default}"
  echo "  aws cloudfront create-invalidation --distribution-id \$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query \"Stacks[0].Outputs[?OutputKey=='CloudFrontDistributionId'].OutputValue\" --output text) --paths \"/*\" --profile \${AWS_PROFILE:-default}"
  echo ""
  echo "Cognito: add https://dev.ragnarokgamez.com/auth/callback (and sign-out URL if used) to the app client."
  exit 1
}

if [[ $# -lt 2 ]]; then
  usage
fi

HOSTED_ZONE_ID="$1"
CERT_ARN="$2"

aws cloudformation deploy \
  --template-file "$TEMPLATE" \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "HostedZoneId=${HOSTED_ZONE_ID}" \
    "AcmCertificateArn=${CERT_ARN}"

aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table
