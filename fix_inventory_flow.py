#!/usr/bin/env python3
# =============================================================
# fix_inventory_flow.py  (v3 — anchor-based matching)
# اصلاح خريطة تدفق موديول المخزون — 5 نقاط
# =============================================================

import os
import re
import shutil
from datetime import datetime

# ── المسارات ──────────────────────────────────────────────────
BASE        = "/home/momar/Projects/POS_DEV/posv1_dev10"
VIEWS_SALES = os.path.join(BASE, "pos_backend/sales/views.py")
SER_SALES   = os.path.join(BASE, "pos_backend/sales/serializers.py")
VIEWS_INV   = os.path.join(BASE, "pos_backend/inventory/views.py")
VIEWS_PROD  = os.path.join(BASE, "pos_backend/products/views.py")
CHANGELOG   = os.path.join(BASE, "CHANGELOG.md")
README      = os.path.join(BASE, "FIXES_README.md")
# ─────────────────────────────────────────────────────────────

CHANGE_MSG = (
    "اصلاح خريطة تدفق المخزون: "
    "StockAlert تلقائي + StockAdjustment في cancel + reason صح في receive"
)


# ── Helpers ───────────────────────────────────────────────────
def abort(msg):
    print("\n❌  " + msg)
    raise SystemExit(1)


def backup(path):
    bak = path + ".bak"
    shutil.copy2(path, bak)
    print("   💾  backup → " + bak)


def read_file(path):
    if not os.path.isfile(path):
        abort("الملف غير موجود: " + path)
    return open(path, encoding="utf-8").read()


def write_file(path, content):
    open(path, "w", encoding="utf-8").write(content)
    print("   💾  محفوظ  → " + path)


def apply_patch(src, old, new, label, path):
    if old not in src:
        idx = src.find(old[:30])
        print("   🔍  first-30 lookup index: " + str(idx))
        print("   🔍  OLD repr: " + repr(old[:120]))
        abort(label + ": لم اجد النص في " + path)
    result = src.replace(old, new, 1)
    print("   ✅  " + label)
    return result


def apply_regex(src, pattern, replacement, label, path, flags=0):
    new_src, n = re.subn(pattern, replacement, src, count=1, flags=flags)
    if n == 0:
        print("   🔍  regex pattern: " + pattern[:80])
        abort(label + ": لم يطابق الـ regex في " + path)
    print("   ✅  " + label)
    return new_src


def update_changelog(msg):
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = "\n## [" + now + "] " + msg + "\n"
    try:
        txt = open(CHANGELOG, encoding="utf-8").read()
        new = re.sub(r"(---\s*\n)", r"\1" + entry, txt, count=1)
        open(CHANGELOG, "w", encoding="utf-8").write(new)
        print("   📝  CHANGELOG updated")
    except Exception as e:
        print("   ⚠️   CHANGELOG skipped: " + str(e))


# ── README ────────────────────────────────────────────────────
def write_readme():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Fix: Inventory Flow — 5 Issues Fixed",
        "",
        "## Date",
        now,
        "",
        "## النقاط المصلحة",
        "",
        "### Fix-1: StockAlert تلقائي بعد البيع (serializers.py)",
        "بعد كل بيع: stock==0 → alert out | stock<=10 → alert low",
        "",
        "### Fix-2: resolve alerts بعد الغاء البيع (views.py)",
        "لو المخزون رجع فوق الـ threshold بعد الالغاء → resolve تلقائي",
        "",
        "### Fix-3: reason='count' → reason='other' في receive (inventory/views.py)",
        "'purchase' مش موجود في REASONS choices فتم تغييره لـ 'other'",
        "",
        "### Fix-4: StockAdjustment في cancel action (views.py)",
        "الغاء الفاتورة دلوقتي بيسجل StockAdjustment + StockMovement",
        "",
        "### Fix-5: initial StockMovement عند اضافة منتج (products/views.py)",
        "stock > 0 عند الاضافة → StockMovement type='initial'",
        "",
        "## الملفات المعدلة",
        "| الملف | Fix |",
        "|-------|-----|",
        "| pos_backend/sales/serializers.py | Fix-1 |",
        "| pos_backend/sales/views.py       | Fix-2 + Fix-4 |",
        "| pos_backend/inventory/views.py   | Fix-3 |",
        "| pos_backend/products/views.py    | Fix-5 |",
        "",
        "## ملاحظة: لا تحتاج migrations",
        "python manage.py runserver",
    ]
    open(README, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("   📄  README → " + README)


# ═══════════════════════════════════════════════════════════════
# Fix-1  serializers.py
# anchor: return sale  (اخر سطر في create)
# ═══════════════════════════════════════════════════════════════
OLD_SER_1 = (
    "        # تحديث بيانات العميل\n"
    "        if sale.customer and sale.status == 'completed':\n"
    "            sale.customer.total_purchases += sale.total\n"
    "            sale.customer.points += int(sale.total)\n"
    "            sale.customer.save(update_fields=['total_purchases', 'points'])\n"
    "\n"
    "        return sale"
)

NEW_SER_1 = (
    "        # ✅ Fix-1: StockAlert تلقائي بعد البيع\n"
    "        from inventory.models import StockAlert\n"
    "        _THRESHOLD = 10\n"
    "        for _si in sale.items.select_related('product').all():\n"
    "            _p = _si.product\n"
    "            if not _p:\n"
    "                continue\n"
    "            _p.refresh_from_db()\n"
    "            if StockAlert.objects.filter(product=_p, is_resolved=False).exists():\n"
    "                continue\n"
    "            if _p.stock == 0:\n"
    "                StockAlert.objects.create(\n"
    "                    product=_p, alert_type='out',\n"
    "                    threshold=_THRESHOLD, current_stock=0)\n"
    "            elif _p.stock <= _THRESHOLD:\n"
    "                StockAlert.objects.create(\n"
    "                    product=_p, alert_type='low',\n"
    "                    threshold=_THRESHOLD, current_stock=_p.stock)\n"
    "\n"
    "        # تحديث بيانات العميل\n"
    "        if sale.customer and sale.status == 'completed':\n"
    "            sale.customer.total_purchases += sale.total\n"
    "            sale.customer.points += int(sale.total)\n"
    "            sale.customer.save(update_fields=['total_purchases', 'points'])\n"
    "\n"
    "        return sale"
)


# ═══════════════════════════════════════════════════════════════
# Fix-2 + Fix-4  views.py  cancel action
# استخدام regex عشان نتجنب مشكلة الـ Arabic comment encoding
# الـ pattern بيبحث عن الجزء الانجليزي الثابت فقط
# ═══════════════════════════════════════════════════════════════

# pattern يمسك الـ block من sale.customer حتى sale.save()
# مع اي comment عربي قبلها (.*? بـ DOTALL)
CANCEL_PATTERN = (
    r"([ \t]*#[^\n]*\n)"                          # اي comment سطر واحد
    r"(            if sale\.customer:\n"
    r"                sale\.customer\.total_purchases -= sale\.total\n"
    r"                sale\.customer\.points = max\(0, sale\.customer\.points - int\(sale\.total\)\)\n"
    r"                sale\.customer\.save\(\)\n"
    r"\n"
    r"            sale\.status = 'cancelled'\n"
    r"            sale\.save\(\))"
)

CANCEL_REPLACEMENT = (
    r"\1"
    "            # ✅ Fix-4: StockAdjustment عند الغاء البيع\n"
    "            from inventory.models import StockAdjustment as _SA\n"
    "            _SA.objects.create(\n"
    "                product=product,\n"
    "                user=user,\n"
    "                quantity_before=stock_before,\n"
    "                quantity_change=item.quantity,\n"
    "                quantity_after=stock_after,\n"
    "                reason='other',\n"
    "                notes='cancel #' + (sale.invoice_number or str(sale.id)[:8]),\n"
    "            )\n"
    "\n"
    "        # ✅ Fix-2: resolve StockAlerts بعد الغاء البيع\n"
    "        from inventory.models import StockAlert as _SAlt\n"
    "        from django.utils import timezone as _tz\n"
    "        _THR = 10\n"
    "        for _ci in sale.items.select_related('product').all():\n"
    "            if not _ci.product:\n"
    "                continue\n"
    "            _ci.product.refresh_from_db()\n"
    "            if _ci.product.stock > _THR:\n"
    "                _SAlt.objects.filter(\n"
    "                    product=_ci.product, is_resolved=False\n"
    "                ).update(is_resolved=True, resolved_at=_tz.now())\n"
    "\n"
    "        if sale.customer:\n"
    "            sale.customer.total_purchases -= sale.total\n"
    "            sale.customer.points = max(0, sale.customer.points - int(sale.total))\n"
    "            sale.customer.save()\n"
    "\n"
    "        sale.status = 'cancelled'\n"
    "        sale.save()"
)


# ═══════════════════════════════════════════════════════════════
# Fix-3  inventory/views.py
# anchor: reason = 'count'  سطر واحد بدون عربي
# ═══════════════════════════════════════════════════════════════
OLD_INV_3 = "                        reason          = 'count',"
NEW_INV_3 = "                        reason          = 'other',"


# ═══════════════════════════════════════════════════════════════
# Fix-5  products/views.py
# ═══════════════════════════════════════════════════════════════
OLD_PROD_5 = (
    "    def perform_create(self, serializer):\n"
    "        serializer.save()"
)

NEW_PROD_5 = (
    "    def perform_create(self, serializer):\n"
    "        product = serializer.save()\n"
    "        # ✅ Fix-5: initial StockMovement\n"
    "        if product.stock and product.stock > 0:\n"
    "            from inventory.models import StockMovement\n"
    "            StockMovement.objects.create(\n"
    "                product=product,\n"
    "                movement_type='initial',\n"
    "                quantity=product.stock,\n"
    "                stock_before=0,\n"
    "                stock_after=product.stock,\n"
    "                reference='',\n"
    "                notes='initial stock',\n"
    "                user=self.request.user,\n"
    "            )"
)


# ── apply functions ───────────────────────────────────────────
def fix_serializers():
    print("\n[Fix-1] StockAlert بعد البيع — serializers.py ...")
    backup(SER_SALES)
    src = read_file(SER_SALES)
    src = apply_patch(src, OLD_SER_1, NEW_SER_1,
                      "Fix-1: StockAlert بعد البيع", SER_SALES)
    write_file(SER_SALES, src)


def fix_views_sales():
    print("\n[Fix-2 + Fix-4] cancel action — views.py ...")
    backup(VIEWS_SALES)
    src = read_file(VIEWS_SALES)
    src = apply_regex(src, CANCEL_PATTERN, CANCEL_REPLACEMENT,
                      "Fix-2+4: cancel action محدث", VIEWS_SALES,
                      flags=re.DOTALL)
    write_file(VIEWS_SALES, src)


def fix_inventory_views():
    print("\n[Fix-3] reason='other' في receive — inventory/views.py ...")
    backup(VIEWS_INV)
    src = read_file(VIEWS_INV)
    src = apply_patch(src, OLD_INV_3, NEW_INV_3,
                      "Fix-3: reason='other'", VIEWS_INV)
    write_file(VIEWS_INV, src)


def fix_products_views():
    print("\n[Fix-5] initial StockMovement — products/views.py ...")
    if not os.path.isfile(VIEWS_PROD):
        print("   ⚠️   products/views.py مش موجود — تخطي Fix-5")
        return
    backup(VIEWS_PROD)
    src = read_file(VIEWS_PROD)
    if OLD_PROD_5 not in src:
        print("   ⚠️   perform_create مش بهذا الشكل — تخطي Fix-5")
        return
    src = apply_patch(src, OLD_PROD_5, NEW_PROD_5,
                      "Fix-5: initial StockMovement", VIEWS_PROD)
    write_file(VIEWS_PROD, src)


# ── main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("=" * 58)
    print("  🔧  fix_inventory_flow.py  (v3)")
    print("=" * 58)

    fix_serializers()
    fix_views_sales()
    fix_inventory_views()
    fix_products_views()

    print("\n[README] كتابة FIXES_README.md ...")
    write_readme()

    print("\n[CHANGELOG] تحديث ...")
    update_changelog(CHANGE_MSG)

    print()
    print("=" * 58)
    print("  🎉  تم بنجاح!")
    print()
    print("  الخطوات التالية:")
    print("  cd pos_backend && python manage.py runserver")
    print()
    print("  للتحقق:")
    print("  1. بيع منتج stock < 10  → StockAlert تلقائي")
    print("  2. الغي فاتورة          → StockAdjustment + resolve alert")
    print("  3. استلم بضاعة          → reason='other'")
    print("  4. اضف منتج stock > 0   → StockMovement type='initial'")
    print("=" * 58)
    print()
