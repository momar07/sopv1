#!/usr/bin/env bash
# =============================================================
#  run_seed_ui.sh  ·  تشغيل seed_ui_data.py عبر Django shell
# =============================================================
set -e

BACKEND_DIR="$(dirname "$0")/pos_backend"

echo "=============================================="
echo "  🌱  Seeding UI data ..."
echo "=============================================="

cd "$BACKEND_DIR"
python manage.py shell < seed_ui_data.py

echo ""
echo "✅  Seed اكتمل - أعد تشغيل الـ backend ثم تحقق من /api/auth/me/"
