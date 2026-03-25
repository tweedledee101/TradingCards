#!/usr/bin/env python3
"""Deploy api-lambda-http CloudFormation with secrets from backend/.env (no shell mangling of DATABASE_URL)."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env_file(path: Path) -> None:
    """Minimal KEY=VALUE parser; no python-dotenv required for deploy."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        os.environ[key] = val


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--profile",
        default=os.environ.get("AWS_PROFILE") or "ragnarok",
        help='AWS CLI profile (default: $AWS_PROFILE if set, else "ragnarok")',
    )
    p.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    p.add_argument("--stack", default="ragnarok-api-lambda")
    p.add_argument("--image-uri", required=True)
    p.add_argument("--hosted-zone-id", default="Z04892492JVVLBZJ5A8OB")
    p.add_argument(
        "--acm-cert-arn",
        default="arn:aws:acm:us-east-1:635601810497:certificate/8dda492b-b16f-45bf-965e-9268abaabe78",
    )
    p.add_argument("--api-hostname", default="api.ragnarokgamez.com")
    args = p.parse_args()

    load_env_file(ROOT / "backend" / ".env")

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("DATABASE_URL missing in backend/.env", file=sys.stderr)
        return 1

    ebay_cid = os.environ.get("EBAY_CLIENT_ID") or os.environ.get("EBAY_APP_ID", "")
    ebay_sec = os.environ.get("EBAY_CLIENT_SECRET") or os.environ.get("EBAY_CERT_ID", "")
    if not ebay_cid or not ebay_sec:
        print("EBAY_CLIENT_ID/EBAY_APP_ID and EBAY_CLIENT_SECRET/EBAY_CERT_ID required", file=sys.stderr)
        return 1

    pool = os.environ.get("COGNITO_USER_POOL_ID", "us-east-1_7WksfnG6T")
    client = os.environ.get("COGNITO_CLIENT_ID", "7lbcmb2cg1o9c0n2s4tuvftjdk")
    creg = os.environ.get("COGNITO_REGION", "us-east-1")

    template = Path(__file__).parent / "cloudformation" / "api-lambda-http.yaml"
    overrides = [
        f"LambdaImageUri={args.image_uri}",
        f"DatabaseUrl={db_url}",
        f"CognitoRegion={creg}",
        f"CognitoUserPoolId={pool}",
        f"CognitoClientId={client}",
        f"EbayClientId={ebay_cid}",
        f"EbayClientSecret={ebay_sec}",
        f"ApiHostname={args.api_hostname}",
        f"HostedZoneId={args.hosted_zone_id}",
        f"AcmCertificateArn={args.acm_cert_arn}",
    ]

    cmd = ["aws", "--profile", args.profile]
    cmd.extend(
        [
            "cloudformation",
            "deploy",
            "--stack-name",
            args.stack,
            "--template-file",
            str(template),
            "--capabilities",
            "CAPABILITY_IAM",
            "--no-fail-on-empty-changeset",
            "--region",
            args.region,
            "--parameter-overrides",
            *overrides,
        ]
    )

    print("Running aws cloudformation deploy ...")
    subprocess.check_call(cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
