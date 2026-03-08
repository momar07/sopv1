#!/usr/bin/env python3
# =============================================================================
#  fix_ui_components.py  ·  إصلاح component names في الـ seed
#  يكتب seed_ui_data.py جديد بأسماء متطابقة مع src/pages/ الفعلية
# =============================================================================

import os, sys, shutil
from datetime import datetime

# ── مسارات ───────────────────────────────────────────────────────────────────
BASE      = "/home/momar/Projects/POS_DEV/posv1_dev10"
BACKEND   = os.path.join(BASE, "pos_backend")
SEED_FILE = os.path.join(BACKEND, "seed_ui_data.py")
SHELL_FILE= os.path.join(BASE,    "run_seed_ui.sh")
CHANGELOG = os.path.join(BASE,    "CHANGELOG.md")
README    = os.path.join(BASE,    "FIXES_README.md")

SCRIPT_NAME = "fix_ui_components.py"
NOW         = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ── helpers ──────────────────────────────────────────────────────────────────
def abort(msg):
    print(f"\n❌  {msg}")
    sys.exit(1)

def backup(path):
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
        print(f"   📦  backup → {os.path.basename(path)}.bak")

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"   ✅  written → {os.path.relpath(path, BASE)}")

def update_changelog(msg):
    entry = f"\n## [{NOW}] - {SCRIPT_NAME}\n- {msg}\n"
    mode = "a" if os.path.exists(CHANGELOG) else "w"
    with open(CHANGELOG, mode, encoding="utf-8") as f:
        f.write(entry)

def write_readme():
    lines = [
        "# FIXES README",
        f"**Script:** `{SCRIPT_NAME}`",
        f"**Date:** {NOW}",
        "",
        "---",
        "## Component Names Audit",
        "",
        "### المشكلة",
        "الـ seed القديم كان بيستخدم XxxPage (مثل DashboardPage, ProductsPage)",
        "لكن الملفات الفعلية في src/pages/ بدون Page suffix.",
        "ده بيخلي lazyPage() يـ throw error على كل route.",
        "",
        "### الـ Mapping الصح",
        "| component في الـ DB | الملف الفعلي         |",
        "|---------------------|----------------------|",
        "| Dashboard           | Dashboard.jsx        |",
        "| Products            | Products.jsx         |",
        "| Customers           | Customers.jsx        |",
        "| Operations          | Operations.jsx       |",
        "| BarcodePOS          | BarcodePOS.jsx       |",
        "| InventoryPage       | InventoryPage.jsx    |",
        "| FinancialReport     | FinancialReport.jsx  |",
        "| CashRegister        | CashRegister.jsx     |",
        "| UserManagement      | UserManagement.jsx   |",
        "| Settings            | Settings.jsx         |",
        "| ReturnsPage         | ReturnsPage.jsx      |",
        "| OperationDetails    | OperationDetails.jsx |",
        "",
        "### ملفات غير موجودة (محذوفة من الـ seed)",
        "- PurchaseOrdersPage → الصفحة مش موجودة",
        "- SuppliersPage → الصفحة مش موجودة",
        "- UnitsPage → الصفحة مش موجودة",
        "",
        "### ملف معدّل",
        "- pos_backend/seed_ui_data.py",
    ]
    write_file(README, "\n".join(lines))

# ── seed_ui_data.py الجديد ───────────────────────────────────────────────────
SEED_CONTENT = r"""# seed_ui_data.py
# يُشغَّل داخل Django shell:
#   cd pos_backend && python manage.py shell < seed_ui_data.py
#
# ======================================================
#  Component names مطابقة لـ src/pages/ الفعلية
#  (تم التحقق بتاريخ: """ + NOW + r""")
# ======================================================

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django
django.setup()

from ui_builder.models import UiRoute, UiMenuItem, UiAction

print("\n" + "="*60)
print("  seed_ui_data — component names audit fix")
print("="*60)

# ── مسح كل البيانات القديمة ─────────────────────────────────────────────────
print("\n  حذف البيانات القديمة ...")
UiAction.objects.all().delete()
UiMenuItem.objects.all().delete()
UiRoute.objects.all().delete()
print("  done.\n")

# ── Groups ───────────────────────────────────────────────────────────────────
# []     = كل authenticated user بدون فلتر
# SALES  = Admins + Managers + Cashiers
# MGMT   = Admins + Managers
# ADMINS = Admins فقط
ALL    = []
SALES  = ["Admins", "Managers", "Cashiers"]
MGMT   = ["Admins", "Managers"]
ADMINS = ["Admins"]

# ══════════════════════════════════════════════════════════════════════════════
#  UiRoute
#  component = اسم الملف بدون .jsx  ← مطابق لما يرجعه import.meta.glob
# ══════════════════════════════════════════════════════════════════════════════
print("  إنشاء Routes ...")

ROUTES = [
    # key                        label              path                  component           wrapper      groups   order
    ("route.dashboard",          "لوحة التحكم",     "/dashboard",         "Dashboard",        "auth",      ALL,     1),
    ("route.pos",                "نقطة البيع",      "/pos",               "BarcodePOS",       "pos_shift", SALES,   2),
    ("route.operations",         "المبيعات",        "/operations",        "Operations",       "auth",      MGMT,    3),
    ("route.operation_details",  "تفاصيل الفاتورة", "/operations/:id",    "OperationDetails", "auth",      MGMT,    4),
    ("route.returns",            "المرتجعات",       "/returns",           "ReturnsPage",      "auth",      SALES,   5),
    ("route.customers",          "العملاء",         "/customers",         "Customers",        "auth",      SALES,   6),
    ("route.products",           "المنتجات",        "/products",          "Products",         "auth",      MGMT,    7),
    ("route.inventory",          "المخزون",         "/inventory",         "InventoryPage",    "auth",      MGMT,    8),
    ("route.financial_report",   "التقارير",        "/financial-report",  "FinancialReport",  "auth",      MGMT,    9),
    ("route.cash_register",      "الخزنة",          "/cash-register",     "CashRegister",     "auth",      SALES,   10),
    ("route.users",              "المستخدمون",      "/users",             "UserManagement",   "auth",      ADMINS,  11),
    ("route.settings",           "الإعدادات",       "/settings",          "Settings",         "auth",      ADMINS,  12),
]

for key, label, path, component, wrapper, groups, order in ROUTES:
    UiRoute.objects.create(
        key=key, label=label, path=path,
        component=component, wrapper=wrapper,
        required_groups=groups, order=order,
    )
    print(f"    route  {path:28s}  component={component}")

# ══════════════════════════════════════════════════════════════════════════════
#  UiMenuItem  (tree via parent_key)
# ══════════════════════════════════════════════════════════════════════════════
print("\n  إنشاء Sidebar ...")

MENU = [
    # key                        label             path                  icon                         parent_key               groups   order

    # ── root items ───────────────────────────────────────────────────────────
    ("menu.dashboard",           "الرئيسية",       "/dashboard",         "fas fa-chart-line",         "",                      ALL,     1),
    ("menu.pos",                 "نقطة البيع",     "/pos",               "fas fa-cash-register",      "",                      SALES,   2),

    # ── المبيعات section ─────────────────────────────────────────────────────
    ("menu.sales_section",       "المبيعات",       "",                   "fas fa-receipt",            "",                      MGMT,    3),
    ("menu.operations",          "الفواتير",       "/operations",        "fas fa-file-invoice",       "menu.sales_section",    MGMT,    1),
    ("menu.returns",             "المرتجعات",      "/returns",           "fas fa-rotate-left",        "menu.sales_section",    SALES,   2),
    ("menu.customers",           "العملاء",        "/customers",         "fas fa-users",              "menu.sales_section",    SALES,   3),

    # ── root items ───────────────────────────────────────────────────────────
    ("menu.products",            "المنتجات",       "/products",          "fas fa-boxes-stacked",      "",                      MGMT,    4),
    ("menu.inventory",           "المخزون",        "/inventory",         "fas fa-warehouse",          "",                      MGMT,    5),
    ("menu.financial_report",    "التقارير",       "/financial-report",  "fas fa-chart-bar",          "",                      MGMT,    6),

    # ── الإدارة section ──────────────────────────────────────────────────────
    ("menu.admin_section",       "الإدارة",        "",                   "fas fa-cog",                "",                      MGMT,    7),
    ("menu.cash_register",       "الخزنة",         "/cash-register",     "fas fa-coins",              "menu.admin_section",    SALES,   1),
    ("menu.users",               "المستخدمون",     "/users",             "fas fa-user-cog",           "menu.admin_section",    ADMINS,  2),
    ("menu.settings",            "الإعدادات",      "/settings",          "fas fa-sliders-h",          "menu.admin_section",    ADMINS,  3),
]

for key, label, path, icon, parent_key, groups, order in MENU:
    UiMenuItem.objects.create(
        key=key, label=label, path=path,
        icon=icon, parent_key=parent_key,
        required_groups=groups, order=order,
    )
    indent = "      " if parent_key else "  "
    print(f"  {indent}menu  {key}")

# ══════════════════════════════════════════════════════════════════════════════
#  UiAction
# ══════════════════════════════════════════════════════════════════════════════
print("\n  إنشاء Actions ...")

ACTIONS = [
    ("action.products.add",       "route.products",       "products.add",       "إضافة منتج",     "fas fa-plus", "primary"),
    ("action.customers.add",      "route.customers",      "customers.add",      "إضافة عميل",     "fas fa-plus", "primary"),
    ("action.users.add",          "route.users",          "users.add",          "إضافة مستخدم",   "fas fa-plus", "primary"),
    ("action.cash_register.open", "route.cash_register",  "cash_register.open", "فتح وردية",      "fas fa-lock-open", "success"),
    ("action.cash_register.close","route.cash_register",  "cash_register.close","إغلاق وردية",    "fas fa-lock", "danger"),
]

for key, page_key, action_key, label, icon, variant in ACTIONS:
    UiAction.objects.create(
        key=key, page_key=page_key, action_key=action_key,
        label=label, variant=variant,
    )
    print(f"    action  {key}")

# ── ملخص ─────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"  Routes  : {UiRoute.objects.count()}")
print(f"  Menu    : {UiMenuItem.objects.count()}")
print(f"  Actions : {UiAction.objects.count()}")
print("="*60)
print("\n  seed done!")
print("  restart backend  →  GET /api/auth/me/")
print("  ui.routes يجب أن يرجع 12 route")
print("  ui.sidebar يجب أن يرجع 13 item")
"""

# ── run_seed_ui.sh ────────────────────────────────────────────────────────────
SHELL_CONTENT = """#!/usr/bin/env bash
set -e
BACKEND_DIR="$(dirname "$0")/pos_backend"
echo "=============================="
echo "  Seeding UI data ..."
echo "=============================="
cd "$BACKEND_DIR"
python manage.py shell < seed_ui_data.py
echo ""
echo "  done — restart backend"
"""

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 62)
    print("  fix_ui_components.py  ·  Component Names Audit Fix")
    print("=" * 62)

    print("\n[1] seed_ui_data.py ...")
    backup(SEED_FILE)
    write_file(SEED_FILE, SEED_CONTENT)

    print("\n[2] run_seed_ui.sh ...")
    backup(SHELL_FILE)
    write_file(SHELL_FILE, SHELL_CONTENT)
    os.chmod(SHELL_FILE, 0o755)

    print("\n[3] README + CHANGELOG ...")
    write_readme()
    update_changelog(
        "إصلاح component names في seed: XxxPage → اسم الملف الفعلي في src/pages/"
    )

    print()
    print("=" * 62)
    print("  ✅  اكتمل!")
    print("=" * 62)
    print("""
  الخطوات:
  1.  python3 fix_ui_components.py
  2.  bash run_seed_ui.sh
  3.  أعد تشغيل الـ backend
  4.  في الـ browser: logout ثم login
      → كل الـ routes والـ sidebar يظهروا صح
""")


if __name__ == "__main__":
    main()
