
"""
seed_ui_actions.py  —  يُشغَّل داخل Django shell
يحذف الـ UiActions الموجودة ويُعيد إنشاءها بشكل صحيح
"""
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
django.setup()

from ui_builder.models import UiAction

# ── مجموعات الصلاحيات ──────────────────────────────────────────────
ALL  = []                                   # الكل بدون قيد
MGMT = ["Admins", "Managers"]               # الإدارة فقط
ADMN = ["Admins"]                           # الأدمن فقط
SALE = ["Admins", "Managers", "Cashiers", "Cashier Plus"]  # كل من له علاقة بالبيع

# ── تعريف الـ Actions ──────────────────────────────────────────────
# (key, label, page_key, action_key, variant, required_groups, order)
ACTIONS = [
    # ── Products page ──────────────────────────────────────────────
    (
        "products.add",        "إضافة منتج",
        "products.list",       "products.add",
        "primary",             MGMT,   1,
    ),
    (
        "products.delete",     "حذف منتج",
        "products.list",       "products.delete",
        "danger",              MGMT,   2,
    ),
    (
        "products.export",     "تصدير المنتجات",
        "products.list",       "products.export",
        "secondary",           MGMT,   3,
    ),

    # ── Inventory page ─────────────────────────────────────────────
    (
        "inventory.add_order", "إضافة أمر شراء",
        "inventory.list",      "inventory.add_order",
        "primary",             MGMT,   1,
    ),
    (
        "inventory.add_supplier", "إضافة مورد",
        "inventory.list",         "inventory.add_supplier",
        "secondary",              MGMT,   2,
    ),
    (
        "inventory.adjust_stock", "تسوية مخزون",
        "inventory.list",         "inventory.adjust_stock",
        "warning",                MGMT,   3,
    ),

    # ── Customers page ─────────────────────────────────────────────
    (
        "customers.add",       "إضافة عميل",
        "customers.list",      "customers.add",
        "primary",             SALE,   1,
    ),
    (
        "customers.delete",    "حذف عميل",
        "customers.list",      "customers.delete",
        "danger",              MGMT,   2,
    ),

    # ── Users page ─────────────────────────────────────────────────
    (
        "users.add",           "إضافة مستخدم",
        "users.list",          "users.add",
        "primary",             ADMN,   1,
    ),
    (
        "users.delete",        "حذف مستخدم",
        "users.list",          "users.delete",
        "danger",              ADMN,   2,
    ),

    # ── CashRegister page ──────────────────────────────────────────
    (
        "cashregister.open",   "فتح وردية",
        "cashregister.main",   "cashregister.open",
        "primary",             SALE,   1,
    ),
    (
        "cashregister.close",  "إغلاق وردية",
        "cashregister.main",   "cashregister.close",
        "danger",              SALE,   2,
    ),
]

# ── تنفيذ ──────────────────────────────────────────────────────────
print("🗑  حذف الـ UiActions الموجودة...")
deleted, _ = UiAction.objects.all().delete()
print(f"   حُذف {deleted} سجل")

print("➕ إنشاء الـ UiActions الجديدة...")
created = 0
for (key, label, page_key, action_key, variant, groups, order) in ACTIONS:
    UiAction.objects.create(
        key              = key,
        label            = label,
        page_key         = page_key,
        action_key       = action_key,
        variant          = variant,
        required_groups  = groups,
        order            = order,
        is_active        = True,
    )
    created += 1
    print(f"   ✅ {key:35s} → page: {page_key}")

print(f"\n✅ تم إنشاء {created} UiAction بنجاح")
print("\n👉 الخطوات التالية:")
print("   1. أعد تشغيل الـ backend")
print("   2. سجّل خروج ودخول")
print("   3. ستجد زرار 'إضافة منتج' ظاهراً لـ Admins/Managers")
