#!/usr/bin/env bash
set -euo pipefail

release_json="$(curl -fsSL -H "Accept: application/vnd.github+json" https://api.github.com/repos/aws/nova-act/releases/latest || true)"
tag="$(python - <<'PY'
import json
import sys

raw = sys.stdin.read().strip()
if not raw:
    sys.exit(0)
data = json.loads(raw)
print(data.get("tag_name", ""))
PY
<<<"$release_json")"

if [[ -z "${tag}" ]]; then
    echo "Failed to detect latest NovaAct release tag (GitHub API empty or rate-limited)." >&2
    echo "Install manually, for example:" >&2
    echo "  pip install \"https://github.com/aws/nova-act/archive/refs/tags/v3.0.157.0.tar.gz\"" >&2
    exit 1
fi

echo "Installing NovaAct SDK from release ${tag}..."
pip install "https://github.com/aws/nova-act/archive/refs/tags/${tag}.tar.gz"
