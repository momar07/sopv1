#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_alerts_panel.py
───────────────────
يصلح مشكلتين:
  1. Backend: يضيف 'post' لـ http_method_names في StockAlertViewSet
  2. Frontend: يصلح إرسال is_resolved كـ string مش boolean
"""

import os, sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════
# 1. إصلاح الـ Backend
# ══════════════════════════════════════════════════════
views_path = os.path.join(BASE_DIR, "pos_backend", "inventory", "views.py")

if not os.path.exists(views_path):
    print(f"❌  الملف غير موجود: {views_path}")
    sys.exit(1)

with open(views_path, "r", encoding="utf-8") as f:
    views_src = f.read()

OLD_HTTP = "http_method_names  = ['get', 'patch', 'head', 'options']"
NEW_HTTP = "http_method_names  = ['get', 'post', 'patch', 'head', 'options']"

if OLD_HTTP not in views_src:
    print("⚠️  السطر المستهدف في views.py غير موجود — تحقق يدوياً")
else:
    # نسخة احتياطية
    with open(views_path + ".bak", "w", encoding="utf-8") as f:
        f.write(views_src)
    views_src = views_src.replace(OLD_HTTP, NEW_HTTP)
    with open(views_path, "w", encoding="utf-8") as f:
        f.write(views_src)
    print("✅  تم إصلاح http_method_names في views.py")

# ══════════════════════════════════════════════════════
# 2. إصلاح الـ Frontend
# ══════════════════════════════════════════════════════
jsx_path = os.path.join(BASE_DIR, "pos_frontend", "src", "pages", "InventoryPage.jsx")

if not os.path.exists(jsx_path):
    print(f"❌  الملف غير موجود: {jsx_path}")
    sys.exit(1)

with open(jsx_path, "r", encoding="utf-8") as f:
    jsx_src = f.read()

OLD_FILTER = "const params = filter==='all' ? {} : { is_resolved: filter==='resolved' };"
NEW_FILTER = "const params = filter==='all' ? {} : { is_resolved: filter==='resolved' ? 'true' : 'false' };"

if OLD_FILTER not in jsx_src:
    print("⚠️  السطر المستهدف في InventoryPage.jsx غير موجود — تحقق يدوياً")
else:
    with open(jsx_path + ".bak", "w", encoding="utf-8") as f:
        f.write(jsx_src)
    jsx_src = jsx_src.replace(OLD_FILTER, NEW_FILTER)
    with open(jsx_path, "w", encoding="utf-8") as f:
        f.write(jsx_src)
    print("✅  تم إصلاح is_resolved filter في InventoryPage.jsx")

# ══════════════════════════════════════════════════════
print("""
🎉  اكتمل الإصلاح!

الخطوات التالية:
  1. restart الـ Backend:
       cd pos_backend && python manage.py runserver

  2. restart الـ Frontend:
       cd pos_frontend && npm run dev

  3. افتح تاب التنبيهات واضغط زر 🔄 فحص وتحديث التنبيهات
     من تاب ملخص المخزون عشان تنشئ تنبيهات جديدة
""")
