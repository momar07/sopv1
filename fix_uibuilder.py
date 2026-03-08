#!/usr/bin/env python3
# =============================================================================
#  fix_ui_complete.py  ·  seed UI data + fix DynamicSidebar tree
#  BASE = /home/momar/Projects/POS_DEV/posv1_dev10
# =============================================================================

import os, sys, shutil
from datetime import datetime

# ── مسارات ───────────────────────────────────────────────────────────────────
BASE      = "/home/momar/Projects/POS_DEV/posv1_dev10"
BACKEND   = os.path.join(BASE, "pos_backend")
FRONTEND  = os.path.join(BASE, "pos_frontend", "src")
SEED_FILE = os.path.join(BACKEND, "seed_ui_complete.py")
SHELL_FILE= os.path.join(BASE,   "run_seed_ui.sh")
SIDEBAR   = os.path.join(FRONTEND, "components", "DynamicSidebar.jsx")
CHANGELOG = os.path.join(BASE, "CHANGELOG.md")
README    = os.path.join(BASE, "FIXES_README.md")

SCRIPT_NAME = "fix_ui_complete.py"
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
    content = "\n".join([
        "# FIXES README",
        f"**Script:** `{SCRIPT_NAME}`",
        f"**Date:** {NOW}",
        "",
        "---",
        "",
        "## fix_ui_complete — seed UI + fix DynamicSidebar",
        "",
        "### المشكلة",
        "١. الـ DB فارغ أو بيانات ناقصة في UiRoute و UiMenuItem",
        "٢. DynamicSidebar يعرض flat list بدل tree (children مش بتتحط تحت parents)",
        "",
        "### الحل",
        "١. seed_ui_complete.py يمسح البيانات القديمة ويبني من الصفر بـ component",
        "   names تتطابق مع src/pages/ فعلاً",
        "٢. DynamicSidebar.jsx يبني tree من parent_key ويعرض collapsible sections",
        "",
        "### الـ Pages الموجودة والـ component names",
        "| Page File         | component name  |",
        "|-------------------|-----------------|",
        "| Dashboard.jsx     | Dashboard       |",
        "| Products.jsx      | Products        |",
        "| Customers.jsx     | Customers       |",
        "| Operations.jsx    | Operations      |",
        "| ReturnsPage.jsx   | ReturnsPage     |",
        "| FinancialReport.jsx | FinancialReport |",
        "| InventoryPage.jsx | InventoryPage   |",
        "| CashRegister.jsx  | CashRegister    |",
        "| UserManagement.jsx| UserManagement  |",
        "| Settings.jsx      | Settings        |",
        "| BarcodePOS.jsx    | BarcodePOS      |",
        "",
        "### الـ Sidebar Structure",
        "```",
        "الرئيسية          → /dashboard",
        "نقطة البيع        → /pos",
        "المبيعات          → /operations, /returns, /customers",
        "المخزون           → /inventory",
        "التقارير          → /financial-report",
        "الإدارة           → /cash-register, /users, /settings",
        "```",
        "",
        "### ملفات معدّلة",
        "- pos_backend/seed_ui_complete.py (مُنشأ)",
        "- run_seed_ui.sh (مُحدَّث)",
        "- pos_frontend/src/components/DynamicSidebar.jsx (مُحدَّث)",
        "- CHANGELOG.md (مُحدَّث)",
    ])
    write_file(README, content)

# ── seed_ui_complete.py ───────────────────────────────────────────────────────
SEED_CONTENT = r'''# seed_ui_complete.py
# يُشغَّل داخل Django shell:
#   cd pos_backend && python manage.py shell < seed_ui_complete.py

import django, os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
django.setup()

from ui_builder.models import UiRoute, UiMenuItem, UiAction

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  🌱  seed_ui_complete  —  إعادة بناء بيانات الـ UI")
print("="*60)

# ── مسح البيانات القديمة ─────────────────────────────────────────────────────
print("\n🗑️  حذف البيانات القديمة ...")
deleted_a = UiAction.objects.all().delete()
deleted_m = UiMenuItem.objects.all().delete()
deleted_r = UiRoute.objects.all().delete()
print(f"   routes  : {deleted_r[0]} محذوف")
print(f"   menu    : {deleted_m[0]} محذوف")
print(f"   actions : {deleted_a[0]} محذوف")

# ── تعريف الـ Groups ──────────────────────────────────────────────────────────
ALL    = []          # كل يوزر مسجل دخوله
MGMT   = ["Admins", "Managers"]
ADMINS = ["Admins"]
SALES  = ["Admins", "Managers", "Cashiers"]

# ── UiRoute ──────────────────────────────────────────────────────────────────
# component = اسم الملف بدون .jsx  (يتطابق مع src/pages/ فعلاً)
print("\n📍 إنشاء الـ Routes ...")

ROUTES = [
    # key                      label             path                  component        wrapper    groups  order
    ("route.dashboard",        "لوحة التحكم",    "/dashboard",         "Dashboard",     "auth",    ALL,    1),
    ("route.pos",              "نقطة البيع",     "/pos",               "BarcodePOS",    "pos_shift",SALES, 2),
    ("route.operations",       "المبيعات",       "/operations",        "Operations",    "auth",    MGMT,   3),
    ("route.returns",          "المرتجعات",      "/returns",           "ReturnsPage",   "auth",    SALES,  4),
    ("route.customers",        "العملاء",        "/customers",         "Customers",     "auth",    SALES,  5),
    ("route.inventory",        "المخزون",        "/inventory",         "InventoryPage", "auth",    MGMT,   6),
    ("route.financial_report", "التقارير",       "/financial-report",  "FinancialReport","auth",   MGMT,   7),
    ("route.cash_register",    "الخزنة",         "/cash-register",     "CashRegister",  "auth",    MGMT,   8),
    ("route.users",            "المستخدمون",     "/users",             "UserManagement","auth",    ADMINS, 9),
    ("route.settings",         "الإعدادات",      "/settings",          "Settings",      "auth",    ADMINS, 10),
]

for key, label, path, component, wrapper, groups, order in ROUTES:
    obj, created = UiRoute.objects.get_or_create(
        key=key,
        defaults=dict(
            label=label, path=path, component=component,
            wrapper=wrapper, required_groups=groups, order=order,
        )
    )
    print(f"   {'✅ created' if created else '⏭️  exists '}  {key:35s}  →  {component}")

# ── UiMenuItem ───────────────────────────────────────────────────────────────
# parent_key = "" → root section
# parent_key = key لـ section → child
print("\n📂 إنشاء الـ Sidebar ...")

MENU = [
    # key                         label            path                icon                        parent_key              groups  order
    # ── الرئيسية ─────────────────────────────────────────────────────────────
    ("menu.dashboard",            "الرئيسية",      "/dashboard",       "fas fa-chart-line",        "",                     ALL,    1),

    # ── نقطة البيع ───────────────────────────────────────────────────────────
    ("menu.pos",                  "نقطة البيع",    "/pos",             "fas fa-cash-register",     "",                     SALES,  2),

    # ── المبيعات (section) ────────────────────────────────────────────────────
    ("menu.sales_section",        "المبيعات",      "",                 "fas fa-receipt",           "",                     MGMT,   3),
    ("menu.operations",           "الفواتير",      "/operations",      "fas fa-file-invoice",      "menu.sales_section",   MGMT,   1),
    ("menu.returns",              "المرتجعات",     "/returns",         "fas fa-rotate-left",       "menu.sales_section",   SALES,  2),
    ("menu.customers",            "العملاء",       "/customers",       "fas fa-users",             "menu.sales_section",   SALES,  3),

    # ── المخزون ──────────────────────────────────────────────────────────────
    ("menu.inventory",            "المخزون",       "/inventory",       "fas fa-warehouse",         "",                     MGMT,   4),

    # ── التقارير ─────────────────────────────────────────────────────────────
    ("menu.financial_report",     "التقارير",      "/financial-report","fas fa-chart-bar",         "",                     MGMT,   5),

    # ── الإدارة (section) ────────────────────────────────────────────────────
    ("menu.admin_section",        "الإدارة",       "",                 "fas fa-cog",               "",                     MGMT,   6),
    ("menu.cash_register",        "الخزنة",        "/cash-register",   "fas fa-coins",             "menu.admin_section",   MGMT,   1),
    ("menu.users",                "المستخدمون",    "/users",           "fas fa-user-cog",          "menu.admin_section",   ADMINS, 2),
    ("menu.settings",             "الإعدادات",     "/settings",        "fas fa-sliders-h",         "menu.admin_section",   ADMINS, 3),
]

for key, label, path, icon, parent_key, groups, order in MENU:
    obj, created = UiMenuItem.objects.get_or_create(
        key=key,
        defaults=dict(
            label=label, path=path, icon=icon,
            parent_key=parent_key, required_groups=groups, order=order,
        )
    )
    indent = "      " if parent_key else ""
    print(f"   {'✅ created' if created else '⏭️  exists '}  {indent}{key}")

# ── ملخص ─────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"  Routes  : {UiRoute.objects.count()}")
print(f"  Menu    : {UiMenuItem.objects.count()}")
print(f"  Actions : {UiAction.objects.count()}")
print("="*60)
print("\n🎉  seed اكتمل بنجاح!")
print("   أعد تشغيل الـ backend ثم تحقق من: GET /api/auth/me/")
print("   ui.routes يجب أن يحتوي على 10 routes")
print("   ui.sidebar يجب أن يحتوي على 12 item بـ parent_key")
'''

# ── run_seed_ui.sh ────────────────────────────────────────────────────────────
SHELL_CONTENT = '''#!/usr/bin/env bash
# run_seed_ui.sh
set -e
BACKEND_DIR="$(dirname "$0")/pos_backend"
echo "=============================================="
echo "  Seeding UI data ..."
echo "=============================================="
cd "$BACKEND_DIR"
python manage.py shell < seed_ui_complete.py
echo ""
echo "✅  Seed done — restart backend then check /api/auth/me/"
'''

# ── DynamicSidebar.jsx ────────────────────────────────────────────────────────
SIDEBAR_CONTENT = r"""import { Link, useLocation } from 'react-router-dom';
import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useReturnsBadge } from '../context/ReturnsBadgeContext';

// ─── build tree from flat sidebar list ───────────────────────────────────────
function buildTree(items) {
  const map = {};
  const roots = [];

  // أول مرور: ننشئ كل node مع children فاضي
  items.forEach((item) => {
    map[item.key] = { ...item, children: [] };
  });

  // تاني مرور: نربط كل child بـ parent بتاعه
  items.forEach((item) => {
    if (item.parent_key && map[item.parent_key]) {
      map[item.parent_key].children.push(map[item.key]);
    } else {
      roots.push(map[item.key]);
    }
  });

  // ترتيب كل مستوى بـ order
  const sortByOrder = (arr) =>
    [...arr].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));

  roots.forEach((r) => {
    r.children = sortByOrder(r.children);
  });

  return sortByOrder(roots);
}

// ─── fallback icon ───────────────────────────────────────────────────────────
function fallbackIcon(item) {
  const k = String(item?.key  || '').toLowerCase();
  const p = String(item?.path || '').toLowerCase();
  if (k.includes('dashboard')   || p.includes('dashboard'))     return 'fas fa-chart-line';
  if (k.includes('pos')         || p.includes('/pos'))          return 'fas fa-cash-register';
  if (k.includes('operations')  || p.includes('operations'))    return 'fas fa-receipt';
  if (k.includes('returns')     || p.includes('returns'))       return 'fas fa-rotate-left';
  if (k.includes('customers')   || p.includes('customers'))     return 'fas fa-users';
  if (k.includes('inventory')   || p.includes('inventory'))     return 'fas fa-warehouse';
  if (k.includes('financial')   || p.includes('financial'))     return 'fas fa-chart-bar';
  if (k.includes('cash')        || p.includes('cash-register')) return 'fas fa-coins';
  if (k.includes('users')       || p.includes('/users'))        return 'fas fa-user-cog';
  if (k.includes('settings')    || p.includes('settings'))      return 'fas fa-sliders-h';
  if (k.includes('sales')       || k.includes('section'))       return 'fas fa-layer-group';
  return 'fas fa-circle';
}

// ─── SidebarItem — يعرض node واحد (مع children لو section) ───────────────────
function SidebarItem({ node, collapsed, depth = 0 }) {
  const location  = useLocation();
  const { pending, approved } = useReturnsBadge();
  const { isAdmin, isManager } = useAuth();

  const isAdminVal   = typeof isAdmin   === 'function' ? isAdmin()   : !!isAdmin;
  const isManagerVal = typeof isManager === 'function' ? isManager() : !!isManager;
  const canSeeBadge  = isAdminVal || isManagerVal;

  const isReturnNode = (n) =>
    String(n?.path || '').includes('returns') ||
    String(n?.key  || '').toLowerCase().includes('return');

  const hasChildren = node.children && node.children.length > 0;
  const isSection   = hasChildren || !node.path;

  // تحديد الـ active state
  const isActivePath = (path) => !!path && location.pathname === path;
  const isActiveSection = hasChildren &&
    node.children.some((c) => isActivePath(c.path));

  const [open, setOpen] = React.useState(() => isActiveSection);

  // لما الـ route يتغير، افتح الـ section لو فيه child active
  React.useEffect(() => {
    if (hasChildren && node.children.some((c) => isActivePath(c.path))) {
      setOpen(true);
    }
  }, [location.pathname]);

  const iconCls = (node.icon && String(node.icon).includes('fa'))
    ? node.icon
    : fallbackIcon(node);

  // ── Section (parent بدون path أو عنده children) ──────────────────────────
  if (isSection) {
    return (
      <div className="space-y-1">
        {/* Section header */}
        <button
          onClick={() => setOpen((v) => !v)}
          className={`w-full flex items-center p-3 rounded-lg transition-colors text-gray-300 hover:bg-gray-700 hover:text-white ${
            isActiveSection ? 'text-blue-400' : ''
          } ${collapsed ? 'justify-center' : ''}`}
          title={collapsed ? node.label : undefined}
          type="button"
        >
          <i className={`${iconCls} ${collapsed ? '' : 'ml-3'}`}></i>
          {!collapsed && (
            <>
              <span className="font-medium flex-1 text-right">{node.label}</span>
              <i className={`fas fa-chevron-${open ? 'up' : 'down'} text-xs text-gray-400`}></i>
            </>
          )}
        </button>

        {/* Children */}
        {!collapsed && open && (
          <div className="mr-4 border-r border-gray-600 pr-2 space-y-1">
            {node.children.map((child) => (
              <SidebarItem
                key={child.key}
                node={child}
                collapsed={false}
                depth={depth + 1}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── Link عادي ──────────────────────────────────────────────────────────────
  const active      = isActivePath(node.path);
  const showBadge   = canSeeBadge && isReturnNode(node);
  const badgeCount  = showBadge ? (pending + approved) : 0;
  const badgeCls    = pending > 0 ? 'bg-red-500' : 'bg-orange-400';

  return (
    <Link
      to={node.path}
      title={collapsed ? node.label : undefined}
      className={`relative flex items-center p-3 rounded-lg transition-colors ${
        active
          ? 'bg-blue-600 text-white'
          : 'text-gray-300 hover:bg-gray-700 hover:text-white'
      } ${collapsed ? 'justify-center' : ''}`}
    >
      <i className={`${iconCls} ${collapsed ? '' : 'ml-3'}`}></i>
      {!collapsed && (
        <span className="font-medium flex-1">{node.label}</span>
      )}
      {showBadge && badgeCount > 0 && (
        <span
          className={`${badgeCls} text-white text-xs font-bold rounded-full min-w-[20px] h-5 flex items-center justify-center px-1 ${
            collapsed ? 'absolute top-1 right-1' : ''
          }`}
        >
          {badgeCount > 99 ? '99+' : badgeCount}
        </span>
      )}
    </Link>
  );
}

// ─── DynamicSidebar ──────────────────────────────────────────────────────────
export default function DynamicSidebar() {
  const { ui, logout } = useAuth();

  const [collapsed, setCollapsed] = React.useState(() => {
    try { return localStorage.getItem('pos_sidebar_collapsed_v2') === '1'; }
    catch { return false; }
  });

  React.useEffect(() => {
    try { localStorage.setItem('pos_sidebar_collapsed_v2', collapsed ? '1' : '0'); }
    catch {}
  }, [collapsed]);

  // بناء الـ tree من الـ flat list اللي بيجي من الـ backend
  const flatItems = ui?.sidebar || [];
  const tree      = React.useMemo(() => buildTree(flatItems), [flatItems]);

  return (
    <aside
      className={`bg-gray-800 text-white ${
        collapsed ? 'w-20' : 'w-64'
      } h-full flex flex-col transition-all duration-200 overflow-hidden`}
      aria-label="Sidebar"
    >
      {/* Header */}
      <div className="p-4 mb-2 flex items-center justify-between border-b border-gray-700">
        <div className={`text-2xl font-bold ${collapsed ? 'text-center w-full' : ''}`}>
          <i className="fas fa-store ml-2"></i>
          {!collapsed && 'POS'}
        </div>
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="text-gray-200 hover:text-white p-2 rounded-lg hover:bg-gray-700 transition-colors"
          title={collapsed ? 'توسيع القائمة' : 'تصغير القائمة'}
          type="button"
        >
          <i className={`fas ${collapsed ? 'fa-angle-left' : 'fa-angle-right'}`}></i>
        </button>
      </div>

      {/* Menu */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-1">
        {tree.map((node) => (
          <SidebarItem
            key={node.key}
            node={node}
            collapsed={collapsed}
          />
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700">
        <button
          onClick={logout}
          className={`w-full flex items-center p-3 rounded-lg text-red-400 hover:bg-red-900 hover:text-red-200 transition-colors ${
            collapsed ? 'justify-center' : ''
          }`}
          title={collapsed ? 'تسجيل الخروج' : undefined}
          type="button"
        >
          <i className={`fas fa-sign-out-alt ${collapsed ? '' : 'ml-3'}`}></i>
          {!collapsed && <span className="font-medium">تسجيل الخروج</span>}
        </button>
      </div>
    </aside>
  );
}
"""

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 62)
    print("  🔧  fix_ui_complete.py")
    print("=" * 62)

    # ── 1. seed file ──────────────────────────────────────────────────────────
    print("\n[1] كتابة seed_ui_complete.py ...")
    backup(SEED_FILE)
    write_file(SEED_FILE, SEED_CONTENT)

    # ── 2. shell runner ───────────────────────────────────────────────────────
    print("\n[2] كتابة run_seed_ui.sh ...")
    backup(SHELL_FILE)
    write_file(SHELL_FILE, SHELL_CONTENT)
    os.chmod(SHELL_FILE, 0o755)

    # ── 3. DynamicSidebar ────────────────────────────────────────────────────
    print("\n[3] تحديث DynamicSidebar.jsx ...")
    if not os.path.exists(os.path.dirname(SIDEBAR)):
        abort(f"المجلد مش موجود: {os.path.dirname(SIDEBAR)}")
    backup(SIDEBAR)
    write_file(SIDEBAR, SIDEBAR_CONTENT)

    # ── 4. README + CHANGELOG ─────────────────────────────────────────────────
    print("\n[4] README + CHANGELOG ...")
    write_readme()
    update_changelog(
        "seed UI complete: 10 routes + 12 sidebar items (tree) + DynamicSidebar يبني tree من parent_key"
    )

    # ── خطوات التشغيل ────────────────────────────────────────────────────────
    print()
    print("=" * 62)
    print("  ✅  اكتمل! الخطوات التالية:")
    print("=" * 62)
    print("""
  1. شغّل الـ seed:
     cd /home/momar/Projects/POS_DEV/posv1_dev10
     bash run_seed_ui.sh

  2. أعد تشغيل الـ backend

  3. افتح الـ browser وتحقق من:
     GET /api/auth/me/
     → ui.routes  : 10 items
     → ui.sidebar : 12 items بـ parent_key

  4. الـ Sidebar هيبني tree تلقائياً من parent_key
""")


if __name__ == "__main__":
    main()
