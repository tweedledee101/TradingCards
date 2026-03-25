#!/usr/bin/env bash
# Build & push FastAPI container to ECR, then deploy CloudFormation (HTTP API + api.<domain>).
# Prereqs: docker, aws cli; backend/.env with DATABASE_URL, EBAY_*, etc.
# Uses AWS_PROFILE when set; otherwise profile "ragnarok" (avoids accidental default/work creds).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_REGION:-us-east-1}"
PROFILE="${AWS_PROFILE:-ragnarok}"
STACK="${STACK_NAME:-ragnarok-api-lambda}"
REPO="${ECR_REPO_NAME:-ragnarok-trading-api}"
HOSTED_ZONE_ID="${HOSTED_ZONE_ID:-Z04892492JVVLBZJ5A8OB}"
ACM_CERT_ARN="${ACM_CERT_ARN:-arn:aws:acm:us-east-1:635601810497:certificate/8dda492b-b16f-45bf-965e-9268abaabe78}"
API_HOST="${API_HOSTNAME:-api.ragnarokgamez.com}"

aws_cli() {
  if [[ -n "$PROFILE" ]]; then
    aws --profile "$PROFILE" --region "$REGION" "$@"
  else
    aws --region "$REGION" "$@"
  fi
}

if [[ ! -f "$ROOT/backend/.env" ]]; then
  echo "Missing backend/.env — need DATABASE_URL, EBAY_CLIENT_ID, EBAY_CLIENT_SECRET (and optional others)."
  exit 1
fi

ACCOUNT_ID=$(aws_cli sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO}"

echo "Ensuring ECR repository ${REPO}..."
aws_cli ecr describe-repositories --repository-names "$REPO" &>/dev/null || \
  aws_cli ecr create-repository --repository-name "$REPO" >/dev/null

echo "Logging in to ECR..."
aws_cli ecr get-login-password | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "Building image..."
docker build -f "$ROOT/Dockerfile.api-lambda" -t "${REPO}:latest" "$ROOT"

docker tag "${REPO}:latest" "${ECR_URI}:latest"

echo "Pushing ${ECR_URI}:latest ..."
docker push "${ECR_URI}:latest"

echo "Deploying CloudFormation stack ${STACK} (Python loader avoids shell-breaking DATABASE_URL)..."
python3 "$ROOT/aws/deploy_api_cf.py" \
  --profile "$PROFILE" \
  --image-uri "${ECR_URI}:latest" \
  --stack "$STACK" \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --acm-cert-arn "$ACM_CERT_ARN" \
  --api-hostname "$API_HOST" \
  --region "$REGION"

echo ""
aws_cli cloudformation describe-stacks --stack-name "$STACK" \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' --output table

echo ""
echo "API (after DNS propagation): https://${API_HOST}"
echo "Health: curl -s https://${API_HOST}/health | head"
