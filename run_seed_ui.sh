#!/usr/bin/env bash
set -e
BACKEND_DIR="$(dirname "$0")/pos_backend"
echo "=============================="
echo "  Seeding UI data ..."
echo "=============================="
cd "$BACKEND_DIR"
python manage.py shell < seed_ui_data.py
echo ""
echo "  done — restart backend"
