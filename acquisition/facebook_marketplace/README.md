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

**Python 3.10+ is required.** The PyPI package `nova-act` declares `requires-python >= 3.10`. On Ubuntu/WSL, default `python3` is often **3.8 or 3.9**, which makes `pip install nova-act` fail with **"No matching distribution found"** — you must use **python3.12** (or 3.10/3.11), not the old system `python3`.

```bash
python3.12 --version   # or: apt install python3.12 python3.12-venv
python3.12 -m pip install --user nova-act
python3.12 -m playwright install chrome
python3.12 -c "import nova_act; print('ok')"
```

**Use one interpreter for everything:** the same `python3.12` for `pip`, `playwright`, and `scripts/dev/nova_act_listing_visual_probe.py`.

Optional: `./acquisition/facebook_marketplace/install_novaact.sh` with `NOVAACT_PYTHON=python3.12` if `python3` is too old.

The package is on PyPI as `nova-act`. You can also install from the latest stable GitHub release tag.
Use the helper script to always install the latest release:

```bash
./acquisition/facebook_marketplace/install_novaact.sh
```

If GitHub API rate limiting or release metadata lookup fails, you can override the
release tag or provide a token:

```bash
export NOVAACT_RELEASE_TAG="v3.0.157.0"
export GITHUB_TOKEN="ghp_your_token"
./acquisition/facebook_marketplace/install_novaact.sh
```

Or install a specific release from GitHub (same Python 3.10+ rule):

```bash
NOVAACT_PYTHON=python3.12
$NOVAACT_PYTHON -m pip install "https://github.com/aws/nova-act/archive/refs/tags/v3.0.157.0.tar.gz"
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

## Quick demos

- **Watch the browser (no eBay):** `python3.12 scripts/dev/nova_act_smoke_gym.py` — headed Chrome on Amazon’s gym page.
- **Extract card fields from eBay photos:** `python3.12 scripts/dev/nova_act_listing_card_extract.py --listing-url "https://www.ebay.com/itm/..."` — JSON for SCP retry.

## eBay listing visual check (Nova Act SDK proof script)

The Nova Act **Python SDK** drives a real browser (Playwright); the model **perceives pages via screenshots**, which is how you get “look at the listing photo and compare to our expected card” behavior. That is different from calling the Nova **chat** HTTP API with a text-only prompt (those calls do not guarantee a live browser session).

Dev script (structured `act_get` + Pydantic schema):

```bash
python scripts/dev/nova_act_listing_visual_probe.py --dry-run
export NOVA_ACT_API_KEY="..."   # from https://nova.amazon.com/act
python scripts/dev/nova_act_listing_visual_probe.py \
  --listing-url "https://www.ebay.com/itm/..." \
  --expected "2023 Topps Chrome Julio Rodriguez base rookie"
```

Use cases: ambiguous titles, suspected wrong parallel, stock photo vs actual slab, “iffy” opportunities before BIN. A future pipeline step could enqueue listing URLs + expected `card_id` text for human or agent review.

References: [What is Nova Act?](https://docs.aws.amazon.com/nova-act/latest/userguide/what-is-nova-act.html), [aws/nova-act README](https://github.com/aws/nova-act).

## Notes
- Do **not** commit secrets. Use environment variables or local `.env` files (ignored by git).
