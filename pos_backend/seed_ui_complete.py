# seed_ui_complete.py
# يُشغَّل داخل Django shell:
#   cd pos_backend && python manage.py shell < seed_ui_complete.py

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")

import django
django.setup()

from ui_builder.models import UiRoute, UiMenuItem, UiAction

print("\n" + "="*60)
print("  seed_ui_complete  —  إعادة بناء بيانات الـ UI")
print("="*60)

# ── مسح البيانات القديمة ─────────────────────────────────────────────────────
print("\n  حذف البيانات القديمة ...")
UiAction.objects.all().delete()
UiMenuItem.objects.all().delete()
UiRoute.objects.all().delete()
print("   done")

# ── Groups ───────────────────────────────────────────────────────────────────
# [] = كل يوزر مسجل دخوله (no group filter)
ALL    = []
MGMT   = ["Admins", "Managers"]
ADMINS = ["Admins"]
SALES  = ["Admins", "Managers", "Cashiers"]

# ── UiRoute ──────────────────────────────────────────────────────────────────
# component = اسم الملف في src/pages/ بدون .jsx
print("\n  إنشاء Routes ...")

ROUTES = [
    ("route.dashboard",        "لوحة التحكم",  "/dashboard",        "Dashboard",      "auth",      ALL,    1),
    ("route.pos",              "نقطة البيع",   "/pos",              "BarcodePOS",     "pos_shift", SALES,  2),
    ("route.operations",       "المبيعات",     "/operations",       "Operations",     "auth",      MGMT,   3),
    ("route.returns",          "المرتجعات",    "/returns",          "ReturnsPage",    "auth",      SALES,  4),
    ("route.customers",        "العملاء",      "/customers",        "Customers",      "auth",      SALES,  5),
    ("route.inventory",        "المخزون",      "/inventory",        "InventoryPage",  "auth",      MGMT,   6),
    ("route.financial_report", "التقارير",     "/financial-report", "FinancialReport","auth",      MGMT,   7),
    ("route.cash_register",    "الخزنة",       "/cash-register",    "CashRegister",   "auth",      SALES,  8),
    ("route.users",            "المستخدمون",   "/users",            "UserManagement", "auth",      ADMINS, 9),
    ("route.settings",         "الإعدادات",    "/settings",         "Settings",       "auth",      ADMINS, 10),
]

for key, label, path, component, wrapper, groups, order in ROUTES:
    UiRoute.objects.create(
        key=key, label=label, path=path,
        component=component, wrapper=wrapper,
        required_groups=groups, order=order,
    )
    print(f"   route  {path:25s}  ->  {component}")

# ── UiMenuItem ───────────────────────────────────────────────────────────────
print("\n  إنشاء Sidebar ...")

MENU = [
    # ─── root items (parent_key = "") ────────────────────────────────────────
    ("menu.dashboard",        "الرئيسية",    "/dashboard",        "fas fa-chart-line",    "",                   ALL,   1),
    ("menu.pos",              "نقطة البيع",  "/pos",              "fas fa-cash-register", "",                   SALES, 2),

    # ─── المبيعات section ────────────────────────────────────────────────────
    ("menu.sales_section",    "المبيعات",    "",                  "fas fa-receipt",       "",                   MGMT,  3),
    ("menu.operations",       "الفواتير",    "/operations",       "fas fa-file-invoice",  "menu.sales_section", MGMT,  1),
    ("menu.returns",          "المرتجعات",   "/returns",          "fas fa-rotate-left",   "menu.sales_section", SALES, 2),
    ("menu.customers",        "العملاء",     "/customers",        "fas fa-users",         "menu.sales_section", SALES, 3),

    # ─── root items ──────────────────────────────────────────────────────────
    ("menu.inventory",        "المخزون",     "/inventory",        "fas fa-warehouse",     "",                   MGMT,  4),
    ("menu.financial_report", "التقارير",    "/financial-report", "fas fa-chart-bar",     "",                   MGMT,  5),

    # ─── الإدارة section ─────────────────────────────────────────────────────
    ("menu.admin_section",    "الإدارة",     "",                  "fas fa-cog",           "",                   MGMT,  6),
    ("menu.cash_register",    "الخزنة",      "/cash-register",    "fas fa-coins",         "menu.admin_section", SALES, 1),
    ("menu.users",            "المستخدمون",  "/users",            "fas fa-user-cog",      "menu.admin_section", ADMINS,2),
    ("menu.settings",         "الإعدادات",   "/settings",         "fas fa-sliders-h",     "menu.admin_section", ADMINS,3),
]

for key, label, path, icon, parent_key, groups, order in MENU:
    UiMenuItem.objects.create(
        key=key, label=label, path=path,
        icon=icon, parent_key=parent_key,
        required_groups=groups, order=order,
    )
    indent = "      " if parent_key else "   "
    print(f"{indent}menu  {key}")

# ── ملخص ─────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"  Routes  : {UiRoute.objects.count()}")
print(f"  Menu    : {UiMenuItem.objects.count()}")
print(f"  Actions : {UiAction.objects.count()}")
print("="*60)
print("\n  seed done!")
print("  restart backend then: GET /api/auth/me/")
