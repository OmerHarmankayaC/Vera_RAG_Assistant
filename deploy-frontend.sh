#!/bin/bash
# Vera RAG sitesinin frontend'ini (RAG/) derleyip sunucuya yayınlar.
# Kullanım:  ./deploy-frontend.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSH_KEY="$HOME/.ssh/vera_hetzner"
SERVER="root@46.225.109.40"
REMOTE_STATIC="/opt/vera-rag/static/"

echo "1/3 — Frontend build alınıyor (RAG/)..."
cd "$PROJECT_DIR/RAG"
npm run build

echo "2/3 — Sunucuya kopyalanıyor..."
rsync -avz --delete -e "ssh -i $SSH_KEY" "$PROJECT_DIR/server_deploy/static/" "$SERVER:$REMOTE_STATIC"

echo "3/3 — Dosya sahipliği düzeltiliyor..."
ssh -i "$SSH_KEY" "$SERVER" "chown -R vera-rag:vera-rag /opt/vera-rag/static"

echo "Bitti. https://rag.omerharmankaya.com adresinde kontrol edebilirsin."
