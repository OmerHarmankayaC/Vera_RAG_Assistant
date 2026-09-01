#!/bin/bash
# Build the Vera RAG frontend (RAG/) and publish it to the demo server.
#
# Usage:
#   VERA_DEPLOY_HOST=root@203.0.113.10 ./deploy-frontend.sh
#
# Configure once instead of passing it every time by exporting the variables in
# your shell profile (or a local, git-ignored .env you `source` first):
#   VERA_DEPLOY_HOST   user@host of the demo server            (required)
#   VERA_DEPLOY_KEY    ssh private key                         (default: ~/.ssh/id_ed25519)
#   VERA_REMOTE_STATIC remote static dir                       (default: /opt/vera-rag/static/)
#   VERA_REMOTE_USER   owner of the deployed files             (default: vera-rag)
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSH_KEY="${VERA_DEPLOY_KEY:-$HOME/.ssh/id_ed25519}"
REMOTE_STATIC="${VERA_REMOTE_STATIC:-/opt/vera-rag/static/}"
REMOTE_USER="${VERA_REMOTE_USER:-vera-rag}"

if [[ -z "${VERA_DEPLOY_HOST:-}" ]]; then
  echo "VERA_DEPLOY_HOST is not set (expected e.g. root@203.0.113.10)." >&2
  exit 1
fi

echo "1/3 — Building the frontend (RAG/)..."
cd "$PROJECT_DIR/RAG"
npm run build

echo "2/3 — Copying to $VERA_DEPLOY_HOST:$REMOTE_STATIC ..."
rsync -avz --delete -e "ssh -i $SSH_KEY" \
  "$PROJECT_DIR/server_deploy/static/" "$VERA_DEPLOY_HOST:$REMOTE_STATIC"

echo "3/3 — Fixing ownership..."
ssh -i "$SSH_KEY" "$VERA_DEPLOY_HOST" \
  "chown -R $REMOTE_USER:$REMOTE_USER ${REMOTE_STATIC%/}"

echo "Done."
