#!/bin/bash
cd "$(dirname "$0")/pos_backend"
echo "▶ تشغيل seed_ui_actions.py..."
python manage.py shell < seed_ui_actions.py
echo "✅ انتهى"
