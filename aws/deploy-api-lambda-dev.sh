#!/usr/bin/env bash
# Build & push the **same** API image as prod, then deploy **second** stack:
#   dev-api.ragnarokgamez.com → Lambda ragnarok-trading-api-dev → DATABASE_URL_DEV
#
# Prereqs: DATABASE_URL or DATABASE_URL_DEV in backend/.env (dev URL can be derived as …/trading_cards_dev from DATABASE_URL). ACM SAN for dev-api.*, Cognito callback for dev UI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_REGION:-us-east-1}"
PROFILE="${AWS_PROFILE:-ragnarok}"
STACK="${STACK_NAME:-ragnarok-api-lambda-dev}"
REPO="${ECR_REPO_NAME:-ragnarok-trading-api}"
HOSTED_ZONE_ID="${HOSTED_ZONE_ID:-Z04892492JVVLBZJ5A8OB}"
ACM_CERT_ARN="${ACM_CERT_ARN:-arn:aws:acm:us-east-1:635601810497:certificate/8dda492b-b16f-45bf-965e-9268abaabe78}"
API_DEV_HOST="${API_DEV_HOSTNAME:-dev-api.ragnarokgamez.com}"
LAMBDA_NAME="${LAMBDA_FUNCTION_NAME_DEV:-ragnarok-trading-api-dev}"

aws_cli() {
  if [[ -n "$PROFILE" ]]; then
    aws --profile "$PROFILE" --region "$REGION" "$@"
  else
    aws --region "$REGION" "$@"
  fi
}

if [[ ! -f "$ROOT/backend/.env" ]]; then
  echo "Missing backend/.env"
  exit 1
fi
grep -qE '^[[:space:]]*DATABASE_URL_DEV=' "$ROOT/backend/.env" \
  || grep -qE '^[[:space:]]*DATABASE_URL=' "$ROOT/backend/.env" || {
  echo "backend/.env needs DATABASE_URL (dev URL derived as .../trading_cards_dev) or DATABASE_URL_DEV"
  exit 1
}
grep -qE '^[[:space:]]*EBAY_CLIENT_ID=' "$ROOT/backend/.env" || grep -qE '^[[:space:]]*EBAY_APP_ID=' "$ROOT/backend/.env" || {
  echo "Need EBAY_CLIENT_ID or EBAY_APP_ID in backend/.env"
  exit 1
}
grep -qE '^[[:space:]]*EBAY_CLIENT_SECRET=' "$ROOT/backend/.env" || grep -qE '^[[:space:]]*EBAY_CERT_ID=' "$ROOT/backend/.env" || {
  echo "Need EBAY_CLIENT_SECRET or EBAY_CERT_ID in backend/.env"
  exit 1
}

ACCOUNT_ID=$(aws_cli sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO}"

aws_cli ecr describe-repositories --repository-names "$REPO" &>/dev/null || \
  aws_cli ecr create-repository --repository-name "$REPO" >/dev/null

aws_cli ecr get-login-password | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

if [[ "${DOCKER_BUILD_NO_CACHE:-}" == "1" ]]; then
  docker build --no-cache -f "$ROOT/Dockerfile.api-lambda" -t "${REPO}:latest" "$ROOT"
else
  docker build -f "$ROOT/Dockerfile.api-lambda" -t "${REPO}:latest" "$ROOT"
fi
docker tag "${REPO}:latest" "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"

python3 "$ROOT/aws/deploy_api_cf.py" \
  --profile "$PROFILE" \
  --image-uri "${ECR_URI}:latest" \
  --stack "$STACK" \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --acm-cert-arn "$ACM_CERT_ARN" \
  --api-hostname "$API_DEV_HOST" \
  --region "$REGION" \
  --template api-lambda-http-dev.yaml \
  --database-env-key DATABASE_URL_DEV

echo "Updating Lambda ${LAMBDA_NAME} image digest..."
aws_cli lambda update-function-code \
  --function-name "$LAMBDA_NAME" \
  --image-uri "${ECR_URI}:latest" \
  --region "$REGION" \
  --output text \
  --query '[FunctionName,LastUpdateStatus]'
aws_cli lambda wait function-updated --function-name "$LAMBDA_NAME" --region "$REGION"

aws_cli cloudformation describe-stacks --stack-name "$STACK" \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' --output table

echo ""
echo "Dev API: https://${API_DEV_HOST}"
echo "Health: curl -s https://${API_DEV_HOST}/health | jq ."
