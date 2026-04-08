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
    p.add_argument(
        "--template",
        default="api-lambda-http.yaml",
        help="Template file under aws/cloudformation/ (e.g. api-lambda-http-dev.yaml)",
    )
    p.add_argument(
        "--database-env-key",
        default="DATABASE_URL",
        help="Env key to read from backend/.env after load (use DATABASE_URL_DEV for dev stack)",
    )
    p.add_argument(
        "--cors-origins",
        default=None,
        help="Override CorsAllowOrigins CloudFormation parameter (comma-separated)",
    )
    args = p.parse_args()

    load_env_file(ROOT / "backend" / ".env")

    db_url = os.environ.get(args.database_env_key, "").strip()
    if not db_url and args.database_env_key == "DATABASE_URL_DEV":
        sys.path.insert(0, str(ROOT))
        from backend.utils.dev_postgres import DEFAULT_DEV_DATABASE, derive_dev_database_url

        prod = os.environ.get("DATABASE_URL", "").strip()
        if prod:
            db_url = derive_dev_database_url(prod, DEFAULT_DEV_DATABASE)
            print(
                f"Derived DATABASE_URL_DEV from DATABASE_URL (…/{DEFAULT_DEV_DATABASE})",
                file=sys.stderr,
            )
    if not db_url:
        hint = ""
        if args.database_env_key == "DATABASE_URL_DEV":
            hint = " — or set DATABASE_URL to derive …/trading_cards_dev"
        print(
            f"{args.database_env_key} missing in backend/.env{hint}",
            file=sys.stderr,
        )
        return 1

    ebay_cid = os.environ.get("EBAY_CLIENT_ID") or os.environ.get("EBAY_APP_ID", "")
    ebay_sec = os.environ.get("EBAY_CLIENT_SECRET") or os.environ.get("EBAY_CERT_ID", "")
    if not ebay_cid or not ebay_sec:
        print("EBAY_CLIENT_ID/EBAY_APP_ID and EBAY_CLIENT_SECRET/EBAY_CERT_ID required", file=sys.stderr)
        return 1

    pool = os.environ.get("COGNITO_USER_POOL_ID", "us-east-1_7WksfnG6T")
    client = os.environ.get("COGNITO_CLIENT_ID", "7lbcmb2cg1o9c0n2s4tuvftjdk")
    creg = os.environ.get("COGNITO_REGION", "us-east-1")

    template = Path(__file__).parent / "cloudformation" / args.template
    if not template.is_file():
        print(f"Template not found: {template}", file=sys.stderr)
        return 1

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
    if args.cors_origins:
        overrides.append(f"CorsAllowOrigins={args.cors_origins}")

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
    # Use run() not check_call(): CalledProcessError embeds the full argv (secrets in --parameter-overrides).
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print(
            "\nCloudFormation deploy failed (exit %s).\n"
            "- If you see 'Could not connect to the endpoint URL': this machine cannot reach AWS HTTPS "
            "(WSL networking, VPN, firewall, or proxy). Try: "
            "curl -sSI https://cloudformation.us-east-1.amazonaws.com/ | head -5\n"
            "- Retry from Windows PowerShell, fix WSL DNS, or change VPN.\n"
            "- Stale Docker layer after editing requirements? Run: DOCKER_BUILD_NO_CACHE=1 ./aws/deploy-api-lambda.sh\n"
            % proc.returncode,
            file=sys.stderr,
        )
        return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
