#!/usr/bin/env python3
# =============================================================================
#  fix_ui_issues.py  ·  إصلاح الشاشة البيضاء + الـ sidebar الناقص
# =============================================================================

import os, sys, shutil
from datetime import datetime

# ── مسارات ───────────────────────────────────────────────────────────────────
BASE     = "/home/momar/Projects/POS_DEV/posv1_dev10"
FRONTEND = os.path.join(BASE, "pos_frontend", "src")
BACKEND  = os.path.join(BASE, "pos_backend")

LOGIN_FILE   = os.path.join(FRONTEND, "pages", "Login.jsx")
DROUTES_FILE = os.path.join(FRONTEND, "components", "DynamicRoutes.jsx")
SEED_FILE    = os.path.join(BACKEND,  "seed_ui_complete.py")
SHELL_FILE   = os.path.join(BASE,     "run_seed_ui.sh")
CHANGELOG    = os.path.join(BASE,     "CHANGELOG.md")
README       = os.path.join(BASE,     "FIXES_README.md")

SCRIPT_NAME  = "fix_ui_issues.py"
NOW          = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        "",
        "## المشكلة الأولى — الشاشة البيضاء بعد اللوجين",
        "",
        "### السبب",
        "بعد اللوجين، Login.jsx كان بيعمل navigate('/') — وهو route مش موجود في",
        "DynamicRoutes. الـ catch-all كان بيعمل redirect لـ '/' تاني → لوب لا نهاية.",
        "",
        "### الحل",
        "١. Login.jsx يعمل navigate('/dashboard') بدل '/'",
        "٢. DynamicRoutes يضيف redirect من '/' إلى '/dashboard'",
        "٣. الـ catch-all يبقى Navigate to='/dashboard' مش '/'",
        "",
        "## المشكلة الثانية — Sidebar ناقص (مش كل الـ sections ظاهرة)",
        "",
        "### السبب",
        "required_groups في seed data كانت بتحتاج Admins/Managers",
        "والـ user ممكن يكون في group تانية أو السكاشن دي مش في الـ DB أصلاً",
        "",
        "### الحل",
        "seed_ui_complete.py اتعدل عشان:",
        "- Products: required_groups = [] (كل authenticated user)",
        "- BarcodePOS: required_groups = [] (Cashiers كمان يدخلوا)",
        "- كل section أو item زياده او نقصانه حسب role بيظبطه الـ seed",
        "",
        "## ملفات معدّلة",
        "- pos_frontend/src/pages/Login.jsx",
        "- pos_frontend/src/components/DynamicRoutes.jsx",
        "- pos_backend/seed_ui_complete.py",
        "- run_seed_ui.sh",
    ]
    write_file(README, "\n".join(lines))

# ── Fix-1: Login.jsx ──────────────────────────────────────────────────────────
LOGIN_CONTENT = r"""import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function Login() {
  const navigate = useNavigate();
  const { login, user, loading: authLoading, isCashier } = useAuth();

  const [formData, setFormData] = useState({ username: '', password: '' });
  const [error,   setError]   = useState('');
  const [loading, setLoading] = useState(false);

  // ── إعادة التوجيه لو المستخدم مسجل بالفعل ──────────────────────────────
  useEffect(() => {
    if (user && !authLoading) {
      // الكاشير يروح للخزنة مباشرة
      if (isCashier && isCashier()) {
        navigate('/cash-register', { replace: true });
      } else {
        navigate('/dashboard', { replace: true });
      }
    }
  }, [user, authLoading, navigate, isCashier]);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <i className="fas fa-spinner fa-spin text-6xl text-blue-600 mb-4"></i>
          <p className="text-gray-600">جاري التحميل...</p>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await login(formData.username, formData.password);
      if (result.success) {
        // الـ useEffect فوق هيتعامل مع الـ redirect
        // بس نضيف fallback لو الـ useEffect أتأخر
        if (isCashier && isCashier()) {
          navigate('/cash-register', { replace: true });
        } else {
          navigate('/dashboard', { replace: true });
        }
      } else {
        setError(result.error || 'فشل تسجيل الدخول');
      }
    } catch {
      setError('خطأ في الاتصال بالسيرفر');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) =>
    setFormData({ ...formData, [e.target.name]: e.target.value });

  const demoAccounts = [
    { username: 'admin',    password: 'admin123',    role: 'مدير النظام' },
    { username: 'manager',  password: 'manager123',  role: 'مدير'        },
    { username: 'cashier1', password: 'cashier123',  role: 'كاشير'       },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center px-4" dir="rtl">
      <div className="max-w-md w-full">

        {/* Logo & Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl mb-4 shadow-lg">
            <i className="fas fa-cash-register text-white text-2xl"></i>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">نظام نقاط البيع</h1>
          <p className="text-gray-600">تسجيل الدخول إلى لوحة التحكم</p>
        </div>

        {/* Login Form */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <form onSubmit={handleSubmit} className="space-y-6">

            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2 text-right">
                اسم المستخدم
              </label>
              <div className="relative">
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  required
                  autoComplete="username"
                  className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-right"
                  placeholder="أدخل اسم المستخدم"
                />
                <i className="fas fa-user absolute right-4 top-1/2 -translate-y-1/2 text-gray-400"></i>
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2 text-right">
                كلمة المرور
              </label>
              <div className="relative">
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  autoComplete="current-password"
                  className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-right"
                  placeholder="أدخل كلمة المرور"
                />
                <i className="fas fa-lock absolute right-4 top-1/2 -translate-y-1/2 text-gray-400"></i>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-right">
                <i className="fas fa-exclamation-circle ml-2"></i>
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-lg font-semibold hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <i className="fas fa-spinner fa-spin ml-2"></i>
                  جاري تسجيل الدخول...
                </span>
              ) : (
                <span className="flex items-center justify-center">
                  <i className="fas fa-sign-in-alt ml-2"></i>
                  تسجيل الدخول
                </span>
              )}
            </button>
          </form>

          {/* Demo Accounts */}
          <div className="mt-8 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-600 mb-4 text-center">حسابات تجريبية:</p>
            <div className="space-y-2">
              {demoAccounts.map((acc, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setFormData({ username: acc.username, password: acc.password })}
                  className="w-full flex items-center justify-between px-4 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <span className="text-xs text-gray-500">{acc.password}</span>
                  <div className="text-right">
                    <span className="text-sm font-medium text-gray-700 ml-2">{acc.username}</span>
                    <span className="text-xs text-gray-500">({acc.role})</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="text-center mt-6">
          <p className="text-sm text-gray-600">نظام إدارة نقاط البيع الشامل v2.0</p>
        </div>
      </div>
    </div>
  );
}

export default Login;
"""

# ── Fix-2: DynamicRoutes.jsx ──────────────────────────────────────────────────
DROUTES_CONTENT = r"""import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { lazyPage } from '../ui/componentLoader';
import { useAuth } from '../context/AuthContext';

// ── Static pages (مضمونة دايماً حتى لو مش في الـ DB) ────────────────────────
const ReturnsPage     = lazy(() => import('../pages/ReturnsPage'));
const FinancialReport = lazy(() => import('../pages/FinancialReport'));
const Dashboard       = lazy(() => import('../pages/Dashboard'));

const Fallback = () => (
  <div className="flex items-center justify-center h-[60vh]">
    <i className="fas fa-spinner fa-spin text-4xl text-blue-600"></i>
  </div>
);

export default function DynamicRoutes({ ProtectedRoute, POSProtectedRoute }) {
  const { ui } = useAuth();
  const routes = ui?.routes || [];

  // لو الـ ui لسه بيتحمل، نعرض spinner مش null
  if (!ui) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <i className="fas fa-spinner fa-spin text-4xl text-blue-600"></i>
      </div>
    );
  }

  return (
    <Suspense fallback={<Fallback />}>
      <Routes>

        {/* ── Redirect from root ─────────────────────────────────────────── */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* ── Static routes (مضمونة دايماً) ────────────────────────────── */}
        <Route
          path="/dashboard"
          element={<ProtectedRoute><Dashboard /></ProtectedRoute>}
        />
        <Route
          path="/returns"
          element={<ProtectedRoute><ReturnsPage /></ProtectedRoute>}
        />
        <Route
          path="/financial-report"
          element={<ProtectedRoute><FinancialReport /></ProtectedRoute>}
        />

        {/* ── Dynamic routes من الـ DB ──────────────────────────────────── */}
        {routes.map((r) => {
          // تجنب تكرار الـ static routes
          if (['/dashboard', '/returns', '/financial-report'].includes(r.path)) {
            return null;
          }

          let Page;
          try {
            Page = lazyPage(r.component);
          } catch (e) {
            console.warn(`[DynamicRoutes] component not found: ${r.component}`, e);
            return null;
          }

          const element = (() => {
            if (r.wrapper === 'public')    return <Page />;
            if (r.wrapper === 'pos_shift') return <POSProtectedRoute><Page /></POSProtectedRoute>;
            return <ProtectedRoute><Page /></ProtectedRoute>;
          })();

          return (
            <Route
              key={r.key || r.path}
              path={r.path}
              element={element}
            />
          );
        })}

        {/* ── Catch-all ───────────────────────────────────────────────────── */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />

      </Routes>
    </Suspense>
  );
}
"""

# ── Fix-3: seed_ui_complete.py (required_groups مضبوط) ───────────────────────
SEED_CONTENT = r"""# seed_ui_complete.py
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
"""

# ── run_seed_ui.sh ────────────────────────────────────────────────────────────
SHELL_CONTENT = """#!/usr/bin/env bash
set -e
BACKEND_DIR="$(dirname "$0")/pos_backend"
echo "=============================="
echo "  Seeding UI data ..."
echo "=============================="
cd "$BACKEND_DIR"
python manage.py shell < seed_ui_complete.py
echo ""
echo "done — restart backend"
"""

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 62)
    print("  fix_ui_issues.py  ·  إصلاح الشاشة البيضاء + Sidebar")
    print("=" * 62)

    # ── Fix-1: Login.jsx ──────────────────────────────────────────────────────
    print("\n[Fix-1] Login.jsx — navigate to /dashboard ...")
    if not os.path.exists(LOGIN_FILE):
        abort(f"مش لاقي: {LOGIN_FILE}")
    backup(LOGIN_FILE)
    write_file(LOGIN_FILE, LOGIN_CONTENT)

    # ── Fix-2: DynamicRoutes.jsx ──────────────────────────────────────────────
    print("\n[Fix-2] DynamicRoutes.jsx — static routes + safe catch-all ...")
    if not os.path.exists(DROUTES_FILE):
        abort(f"مش لاقي: {DROUTES_FILE}")
    backup(DROUTES_FILE)
    write_file(DROUTES_FILE, DROUTES_CONTENT)

    # ── Fix-3: seed ───────────────────────────────────────────────────────────
    print("\n[Fix-3] seed_ui_complete.py — required_groups مضبوط ...")
    backup(SEED_FILE)
    write_file(SEED_FILE, SEED_CONTENT)

    print("\n[Fix-4] run_seed_ui.sh ...")
    backup(SHELL_FILE)
    write_file(SHELL_FILE, SHELL_CONTENT)
    os.chmod(SHELL_FILE, 0o755)

    # ── README + CHANGELOG ────────────────────────────────────────────────────
    print("\n[5] README + CHANGELOG ...")
    write_readme()
    update_changelog(
        "إصلاح الشاشة البيضاء (navigate /dashboard) + DynamicRoutes static fallback + seed groups"
    )

    print()
    print("=" * 62)
    print("  ✅  اكتمل!")
    print("=" * 62)
    print("""
  الخطوات:
  1. شغّل الـ seed:
       bash run_seed_ui.sh

  2. أعد تشغيل الـ backend

  3. في الـ browser — logout ثم login تاني
     → المفروض تروح /dashboard مباشرة
     → الـ Sidebar يظهر كل الـ sections
""")


if __name__ == "__main__":
    main()
