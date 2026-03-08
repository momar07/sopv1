#!/bin/bash

BACKEND_DIR="/home/momar/Projects/POS_DEV/posv1_dev10/pos_backend"
PYTHON="$BACKEND_DIR/venv/bin/python"
PIP="$BACKEND_DIR/venv/bin/pip"

echo "🐍 تشغيل الـ Backend..."
cd "$BACKEND_DIR"

# ── 1. venv ───────────────────────────────────────────────
if [ ! -d "venv" ]; then
  echo "📦 إنشاء virtual environment..."
  python3 -m venv venv
  echo "✅ تم إنشاء venv"
else
  echo "✅ venv موجود"
fi

# ── 2. install requirements ───────────────────────────────
echo "📥 تثبيت المكتبات..."
$PIP install -r requirements.txt
echo "✅ تم تثبيت المكتبات"

# ── 3. migrations ─────────────────────────────────────────
echo "🗄️  تشغيل migrations..."
$PYTHON manage.py makemigrations
$PYTHON manage.py migrate
echo "✅ تمت الـ migrations"

# ── 4. runserver ──────────────────────────────────────────
echo ""
echo "🚀 تشغيل الخادم..."
echo "🌐 http://localhost:8000"
echo "⏹️  اضغط Ctrl+C للإيقاف"
echo ""
exec $PYTHON manage.py runserver
