#!/usr/bin/env bash
# Deploy verification: confirms the CSS served in production matches the repo file.
# Usage: FINCO_URL=https://your-prod-host bash scripts/check_css_delivery.sh
set -euo pipefail

PROD_URL="${FINCO_URL:-http://localhost:8000}"
SENTINEL_RULE=".ph-grid"
CSS_FILE="static/styles.css"

echo "=== FincoGPT CSS delivery check ==="
echo "Target: $PROD_URL"

# 1. Fetch the home page HTML and extract the ?v= token
HTML=$(curl -sf "$PROD_URL/" || curl -sf "$PROD_URL/projects")
CSS_VERSION=$(echo "$HTML" | grep -oP 'styles\.css\?v=\K[^"]+' | head -1)

if [ -z "$CSS_VERSION" ]; then
  echo "FAIL: Could not extract ?v= token from HTML"
  exit 1
fi
echo "Detected CSS version token: $CSS_VERSION"

if [ "$CSS_VERSION" = "phase21-layout-fix" ]; then
  echo "FAIL: Stale hardcoded token 'phase21-layout-fix' still in production HTML"
  exit 1
fi

# 2. Fetch the versioned CSS and check for the sentinel rule
CSS_URL="$PROD_URL/static/styles.css?v=$CSS_VERSION"
echo "Fetching CSS: $CSS_URL"
SERVED_CSS=$(curl -sf "$CSS_URL")

if ! echo "$SERVED_CSS" | grep -q "$SENTINEL_RULE"; then
  echo "FAIL: Sentinel rule '$SENTINEL_RULE' not found in served CSS"
  exit 1
fi
echo "Sentinel rule '$SENTINEL_RULE' present."

# 3. Compare hash of served CSS vs repo file
SERVED_HASH=$(echo "$SERVED_CSS" | md5sum | cut -d' ' -f1)
REPO_HASH=$(md5sum "$CSS_FILE" | cut -d' ' -f1)

echo "Served CSS MD5 : $SERVED_HASH"
echo "Repo   CSS MD5 : $REPO_HASH"

if [ "$SERVED_HASH" != "$REPO_HASH" ]; then
  echo "FAIL: Served CSS does not match repo file — stale or wrong asset"
  exit 1
fi

echo "PASS: CSS delivery verified. Version=$CSS_VERSION, hash matches repo."
