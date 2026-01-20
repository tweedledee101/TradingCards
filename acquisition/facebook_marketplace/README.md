# Facebook Marketplace Intake (NovaAct)

This module is the starting point for automating Facebook Marketplace intake using NovaAct.

## Configuration
Set the NovaAct API key in an environment variable:

```bash
export NOVAACT_API_KEY="your-key-here"
```

Optional:

```bash
export NOVAACT_BASE_URL="https://api.novaact.example"
```

## Install NovaAct SDK
Install the NovaAct SDK locally (required when not using `--dry-run`).
The package is not published to PyPI, so install from the latest stable GitHub release tag.
Use the helper script to always install the latest release:

```bash
./acquisition/facebook_marketplace/install_novaact.sh
```

Or install a specific release manually:

```bash
pip install "https://github.com/aws/nova-act/archive/refs/tags/v3.0.157.0.tar.gz"
```

## Sync local repo with GitHub
From your local clone:

```bash
git fetch origin
git checkout main
git pull origin main
```

## Run

Dry-run (validates config, prints intended actions):

```bash
python acquisition/facebook_marketplace/novaact_intake.py --dry-run
```

Live run (requires NovaAct SDK):

```bash
python acquisition/facebook_marketplace/novaact_intake.py --query "trading cards"
```

## Next Steps
- Wire in the NovaAct SDK or HTTP client calls for:
  - Authentication
  - Browser/session initialization
  - Facebook login
  - Marketplace search
- Save normalized listing data into the acquisition pipeline intake schema.

## Notes
- Do **not** commit secrets. Use environment variables or local `.env` files (ignored by git).
