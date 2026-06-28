#!/usr/bin/env bash
# Start a public HTTPS tunnel to the local AI Sales Manager API on port 8000.
# Requires npx (Node.js / npm).
#
# Usage:
#   ./scripts/start_localtunnel.sh
#
# The script prints the public URL. Keep this terminal open and your laptop
# powered on to keep the deployment accessible.

set -euo pipefail

PORT="${1:-8000}"
SUBDOMAIN="${2:-}"

echo "Starting localtunnel to http://localhost:${PORT} ..."
echo "Keep this terminal open and your laptop connected to the internet."
echo ""

LT_ARGS=("--port" "$PORT")
if [ -n "$SUBDOMAIN" ]; then
    LT_ARGS+=("--subdomain" "$SUBDOMAIN")
fi

exec npx localtunnel "${LT_ARGS[@]}"
