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

# Required keys for deploy_api_cf.py (values not printed)
_env_missing=()
grep -qE '^[[:space:]]*DATABASE_URL=' "$ROOT/backend/.env" || _env_missing+=("DATABASE_URL")
{ grep -qE '^[[:space:]]*EBAY_CLIENT_ID=' "$ROOT/backend/.env" || grep -qE '^[[:space:]]*EBAY_APP_ID=' "$ROOT/backend/.env"; } || _env_missing+=("EBAY_CLIENT_ID or EBAY_APP_ID")
{ grep -qE '^[[:space:]]*EBAY_CLIENT_SECRET=' "$ROOT/backend/.env" || grep -qE '^[[:space:]]*EBAY_CERT_ID=' "$ROOT/backend/.env"; } || _env_missing+=("EBAY_CLIENT_SECRET or EBAY_CERT_ID")
if [[ ${#_env_missing[@]} -gt 0 ]]; then
  echo "backend/.env is missing required variable(s): ${_env_missing[*]}"
  exit 1
fi
echo "backend/.env: DATABASE_URL and eBay credentials present."

if [[ -n "$PROFILE" ]] && ! aws configure list-profiles 2>/dev/null | grep -qx "$PROFILE"; then
  echo "AWS profile '$PROFILE' not found."
  echo "Profiles on this machine: $(aws configure list-profiles 2>/dev/null | paste -sd ', ' -)"
  echo "Create the Ragnarok profile: aws configure --profile ragnarok"
  echo "Or use another profile: AWS_PROFILE=default $0"
  exit 1
fi

ACCOUNT_ID=$(aws_cli sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO}"

echo "Preflight: reachability to AWS CloudFormation API..."
if ! aws_cli cloudformation list-stacks --max-items 1 --output text >/dev/null 2>&1; then
  echo "Cannot reach CloudFormation in ${REGION}. Fix network (WSL/VPN/firewall/proxy), then retry."
  echo "Quick test: curl -sS -o /dev/null -w '%{http_code}\n' https://cloudformation.${REGION}.amazonaws.com/"
  exit 1
fi

echo "Ensuring ECR repository ${REPO}..."
aws_cli ecr describe-repositories --repository-names "$REPO" &>/dev/null || \
  aws_cli ecr create-repository --repository-name "$REPO" >/dev/null

echo "Logging in to ECR..."
aws_cli ecr get-login-password | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "Building image..."
# Rebuild pip layer when requirements-lambda.txt changes (avoid stale CACHE with old pandas/numpy pins).
if [[ "${DOCKER_BUILD_NO_CACHE:-}" == "1" ]]; then
  docker build --no-cache -f "$ROOT/Dockerfile.api-lambda" -t "${REPO}:latest" "$ROOT"
else
  docker build -f "$ROOT/Dockerfile.api-lambda" -t "${REPO}:latest" "$ROOT"
fi

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

# CloudFormation often reports "No changes" when only the :latest digest in ECR changed.
# Lambda will otherwise keep serving the previous image until we force update-function-code.
LAMBDA_NAME="${LAMBDA_FUNCTION_NAME:-ragnarok-trading-api}"
echo "Updating Lambda ${LAMBDA_NAME} to pull current ${ECR_URI}:latest digest..."
aws_cli lambda update-function-code \
  --function-name "$LAMBDA_NAME" \
  --image-uri "${ECR_URI}:latest" \
  --region "$REGION" \
  --output text \
  --query '[FunctionName,LastUpdateStatus]'
echo "Waiting for Lambda code update..."
aws_cli lambda wait function-updated --function-name "$LAMBDA_NAME" --region "$REGION"

echo ""
aws_cli cloudformation describe-stacks --stack-name "$STACK" \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' --output table

echo ""
echo "API (after DNS propagation): https://${API_HOST}"
echo "Health: curl -s https://${API_HOST}/health | head"
