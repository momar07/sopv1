#!/bin/bash
# reset_db.sh — حذف الـ DB وإعادة البناء
set -e

BACKEND='/home/momar/Projects/POS_DEV/posv1_dev10/pos_backend'
PYTHON="$BACKEND/venv/bin/python"

echo ''
echo '================================================'
echo '  🗑️   حذف قاعدة البيانات...'
echo '================================================'
rm -f "$BACKEND/db.sqlite3"

echo ''
echo '  📦  makemigrations...'
cd "$BACKEND"
"$PYTHON" manage.py makemigrations

echo ''
echo '  🗄️   migrate...'
"$PYTHON" manage.py migrate

echo ''
echo '  👤  createsuperuser...'
"$PYTHON" manage.py createsuperuser

echo ''
echo '================================================'
echo '  ✅  تم! شغّل: ./run-backend.sh'
echo '================================================'
echo ''
