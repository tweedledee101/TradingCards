#!/usr/bin/env bash
set -euo pipefail

release_json="$(curl -fsSL https://api.github.com/repos/aws/nova-act/releases/latest)"
tag="$(python - <<'PY'
import json
import sys

data = json.load(sys.stdin)
print(data["tag_name"])
PY
<<<"$release_json")"

echo "Installing NovaAct SDK from release ${tag}..."
pip install "https://github.com/aws/nova-act/archive/refs/tags/${tag}.tar.gz"
