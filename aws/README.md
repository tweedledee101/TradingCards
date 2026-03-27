# AWS Infrastructure

CloudFormation templates for Ragnarok Gaming Trading Card Platform.

## Structure

```
aws/
├── cloudformation/
│   ├── cognito-auth.yaml              # Cognito User Pool + app client (optional)
│   ├── ebay-compliance-lambda.yaml    # eBay compliance webhook (API Gateway + Lambda)
│   ├── frontend-spa.yaml              # S3 + CloudFront for React/Vite static UI
│   └── rds.yaml                       # RDS PostgreSQL with self-contained VPC
├── apply-rds-migrations.sh            # Apply schema + migrations to RDS
├── migrate-to-rds.sh                  # Migrate local data to RDS
├── deploy-ebay-compliance.sh          # Linux/Mac deployment
├── deploy-frontend.sh                 # S3 + CloudFront SPA
└── deploy-ebay-compliance.bat         # Windows deployment
```

## Why `ragnarokgamez.com` may show a bad certificate or not your UI

The **eBay compliance** stack (`ebay-compliance-lambda.yaml`) creates an **API Gateway custom domain** on the **apex** name you pass (default `ragnarokgamez.com`) and a **Route53 alias** to that API. The ACM certificate is attached to **API Gateway** (regional), not to CloudFront.

Effects:

- **HTTPS to the apex** terminates at **API Gateway**. The cert is valid **only if** ACM finished **DNS validation** and the stack deployed cleanly. If validation is stuck or DNS points elsewhere, browsers show certificate errors.
- **There is no static site** on that hostname: API Gateway only serves `GET/POST /api/webhooks/ebay/account-deletion`. Opening `https://ragnarokgamez.com/` in a browser is **not** your React app.

**Recommended split (no extra AWS services beyond what you already use):**

1. **Move the eBay webhook** to a **subdomain** (e.g. `compliance.ragnarokgamez.com` or `hooks.ragnarokgamez.com`): update `DomainName` when deploying `ebay-compliance-lambda.yaml`, fix Route53, redeploy. Request an ACM certificate (same region as the API, e.g. `us-east-1`) that includes that **subdomain** only.
2. **Deploy the UI** with `frontend-spa.yaml` + `deploy-frontend.sh` using an ACM certificate in **`us-east-1`** whose **subject alternative names** include `ragnarokgamez.com` and (if you use it) `www.ragnarokgamez.com`. **CloudFront only accepts ACM certs from `us-east-1`.**
3. Point **apex** (and optional **www**) **Route53 alias** records at the **CloudFront** distribution outputs from the frontend stack—not at API Gateway.

Until step 1 is done, **do not** deploy the frontend stack’s Route53 records for the apex if the apex is still owned by the eBay stack, or CloudFormation will conflict. Either delete/update the old stack first or use a temporary hostname.

### ACM checklist (free; you pay only Route53 ~$0.50/mo if the zone exists)

- Certificate **Issued** (not `PENDING_VALIDATION`) in ACM console.
- **DNS validation** CNAME records present in the hosted zone for **every** name on the cert.
- For **CloudFront**: certificate **must** be in **us-east-1** (N. Virginia), even if other resources are elsewhere.

## Live UI (deployed)

- **Stack:** `ragnarok-frontend-spa` (us-east-1)
- **URL:** https://ragnarokgamez.com and https://www.ragnarokgamez.com
- **Bucket:** `ragnarok-spa-635601810497-us-east-1`
- **CloudFront distribution:** `E1I0LKGWO56GR5` (also `d1pl59weshza88.cloudfront.net`)

After frontend code changes: `npm run build` in `frontend/`, then `aws s3 sync dist/ s3://ragnarok-spa-635601810497-us-east-1/ --delete --profile ragnarok`, then invalidate `/*` on that distribution.

**If `describe-stacks` says the stack does not exist:** the bucket and distribution may still be there from an earlier deploy or a renamed stack. **Sync does not require CloudFormation.** Use the bucket you see in `aws s3 ls` matching `ragnarok-spa-<account-id>-us-east-1` (see `frontend-spa.yaml`), then invalidate the distribution that serves `ragnarokgamez.com`:

```bash
# After: cd frontend && npm run build
aws s3 sync dist/ s3://ragnarok-spa-635601810497-us-east-1/ --delete --profile ragnarok
aws cloudfront create-invalidation --distribution-id E1I0LKGWO56GR5 --paths "/*" --profile ragnarok
```

To confirm the distribution ID if yours differs: `aws cloudfront list-distributions --profile ragnarok` and find the entry whose **Aliases** include `ragnarokgamez.com` (or whose origin is the SPA bucket).

Production builds use `frontend/.env.production`: API base **`https://api.ragnarokgamez.com`**. Point that name at your FastAPI origin (ALB, API Gateway + Lambda, App Runner, etc.) when you host the API in AWS. Until then, the UI loads but data calls will fail until that hostname serves your API with HTTPS and CORS.

## Deploy the static UI (S3 + CloudFront)

Prerequisites: hosted zone for `ragnarokgamez.com`, ACM cert in **us-east-1** covering the viewer hostnames, apex free of conflicting alias (see above).

```bash
export AWS_PROFILE="your-profile-name"
export AWS_REGION=us-east-1

# List cert ARNs (must show Issued)
aws acm list-certificates --region us-east-1

./aws/deploy-frontend.sh ZYOURHOSTEDZONEID arn:aws:acm:us-east-1:ACCOUNT:certificate/UUID

cd frontend
npm ci
npm run build
# Set API URL for the browser (see below)
# Outputs use keys BucketName and CloudFrontDistributionId (not WebsiteBucketName).
BUCKET=$(aws cloudformation describe-stacks --stack-name ragnarok-frontend-spa --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)
aws s3 sync dist/ "s3://${BUCKET}/" --delete
DIST=$(aws cloudformation describe-stacks --stack-name ragnarok-frontend-spa --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDistributionId'].OutputValue" --output text)
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*"
```

### Local API + UI on the public domain

Browsers load `https://ragnarokgamez.com` from **CloudFront** (HTTPS). Calling `http://localhost:8000` from that page is **mixed content** and usually **blocked**. Zero-cost patterns:

- **Develop:** run the UI with `npm run dev` (Vite proxies `/api` to localhost) — no CloudFront involved.
- **Production-shaped test:** expose local FastAPI over **HTTPS** with a free tunnel (**Cloudflare Tunnel**, **ngrok**, etc.), set `VITE_API_URL` to that URL **before** `npm run build`, then sync `dist/` to S3.

`frontend/src/api/client.js` uses `import.meta.env.VITE_API_URL || 'http://localhost:8000'`.

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

## Troubleshooting: `ImportError: DEFAULT_CIPHERS` (WSL / pip AWS CLI)

If `aws` fails with:

`ImportError: cannot import name 'DEFAULT_CIPHERS' from 'urllib3.util.ssl_'`

your **user pip** install of `awscli` is paired with **urllib3 2.x**, which dropped that symbol. Older `botocore` still expects it.

**Recommended:** install **AWS CLI v2** (no Python dependency conflicts). Example user install (no `sudo`):

```bash
cd /tmp
curl -fsSLo awscliv2.zip "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip"
unzip -q awscliv2.zip
./aws/install -i "$HOME/.local/aws-cli" -b "$HOME/.local/bin"
hash -r
aws --version
```

Ensure `$HOME/.local/bin` is **before** any broken `~/.local/bin/aws` shim, or remove the old wrapper: `rm -f ~/.local/bin/aws` after confirming the new `aws` resolves correctly (`command -v aws`).

**Alternative (stay on pip):** align versions, e.g. upgrade the CLI stack or pin urllib3:

```bash
python3 -m pip install --user --upgrade 'awscli' 'botocore'
# If it still breaks:
python3 -m pip install --user 'urllib3<2'
```

## Troubleshooting: `The config profile (ragnarok) could not be found`

The deploy scripts default to **`AWS_PROFILE=ragnarok`** so you do not accidentally use another profile (e.g. work). On a **new machine** (or new WSL distro), that name only works after you define it.

**See what profiles exist:**

```bash
aws configure list-profiles
```

**Create `ragnarok`** (interactive; use your personal AWS access key for the Ragnarok account):

```bash
aws configure --profile ragnarok
# AWS Access Key ID: ...
# AWS Secret Access Key: ...
# Default region name: us-east-1
# Default output format: json
```

Optional `~/.aws/config` snippet so the region is explicit:

```ini
[profile ragnarok]
region = us-east-1
output = json
```

**Or** keep your existing profile name and pass it for one command:

```bash
AWS_PROFILE=your-actual-profile-name ./aws/deploy-api-lambda.sh
```

If your keys live only under `[default]` in `~/.aws/credentials` and you want a separate name, duplicate that block and rename the header to `[ragnarok]` (same keys, different label).
