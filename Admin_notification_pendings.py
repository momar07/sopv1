#!/usr/bin/env python3
"""
fix_returns_notifications.py
============================
يضيف:
  1. ReturnsBadge context  — React context بيجيب عدد pending/approved كل 60 ثانية
  2. DynamicSidebar.jsx    — badge أحمر/برتقالي جنب "المرتجعات" للمدير وأمين المخزن
  3. ReturnsPage.jsx       — صفحة مستقلة بتبويبين: "تحتاج موافقة" و"جاهزة للإكمال"
  4. api.js                — إضافة returnsAPI.getStats لو مش موجودة
  5. DynamicRoutes.jsx     — تسجيل مسار /returns
"""

import os, shutil, sys

BASE    = os.path.dirname(os.path.abspath(__file__))
FRONT   = os.path.join(BASE, 'pos_frontend', 'src')

FILES = {
    'api':      os.path.join(FRONT, 'services', 'api.js'),
    'sidebar':  os.path.join(FRONT, 'components', 'DynamicSidebar.jsx'),
    'routes':   os.path.join(FRONT, 'components', 'DynamicRoutes.jsx'),
    'badge_ctx':os.path.join(FRONT, 'context', 'ReturnsBadgeContext.jsx'),
    'returns_page': os.path.join(FRONT, 'pages', 'ReturnsPage.jsx'),
    'app':      os.path.join(FRONT, 'App.jsx'),
}

# ── helpers ──────────────────────────────────────────────────────────
def backup(p):
    shutil.copy2(p, p + '.bak')
    print(f'  [backup] {p}.bak')

def write(p, content):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p):
        backup(p)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  [ok]     {p}')

def abort(msg):
    print(f'\n[ERROR] {msg}')
    sys.exit(1)

# فحص الملفات الأساسية
for key in ['api', 'sidebar', 'routes', 'app']:
    if not os.path.exists(FILES[key]):
        abort(f'الملف غير موجود: {FILES[key]}')

print('\n=== fix_returns_notifications.py ===\n')

# ══════════════════════════════════════════════════════════════════════
# 1.  context/ReturnsBadgeContext.jsx
#     — يجيب stats كل 60 ثانية ويوفّرها لكل المكونات
# ══════════════════════════════════════════════════════════════════════
BADGE_CTX = """\
import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { returnsAPI } from '../services/api';
import { useAuth } from './AuthContext';

const ReturnsBadgeContext = createContext({ pending: 0, approved: 0 });

export function ReturnsBadgeProvider({ children }) {
  const { user } = useAuth();
  const [counts, setCounts] = useState({ pending: 0, approved: 0 });

  const refresh = useCallback(async () => {
    if (!user) return;
    try {
      const res = await returnsAPI.getStats();
      setCounts({
        pending:  res.data?.pending?.count  ?? 0,
        approved: res.data?.approved?.count ?? 0,
      });
    } catch {
      // صامت — مش نكسر الـ UI لو الـ API فشل
    }
  }, [user]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 60_000);   // كل دقيقة
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <ReturnsBadgeContext.Provider value={{ ...counts, refresh }}>
      {children}
    </ReturnsBadgeContext.Provider>
  );
}

export const useReturnsBadge = () => useContext(ReturnsBadgeContext);
"""

# ══════════════════════════════════════════════════════════════════════
# 2.  components/DynamicSidebar.jsx
#     — يضيف badge أحمر (pending) أو برتقالي (approved) جنب المرتجعات
# ══════════════════════════════════════════════════════════════════════
SIDEBAR = """\
import { Link, useLocation } from 'react-router-dom';
import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useReturnsBadge } from '../context/ReturnsBadgeContext';

export default function DynamicSidebar() {
  const location  = useLocation();
  const { ui, isAdmin, isManager } = useAuth();
  const { pending, approved }      = useReturnsBadge();

  const items = ui?.sidebar || [];

  const [collapsed, setCollapsed] = React.useState(() => {
    try { return localStorage.getItem('pos_sidebar_collapsed_v2') === '1'; }
    catch { return false; }
  });

  React.useEffect(() => {
    try { localStorage.setItem('pos_sidebar_collapsed_v2', collapsed ? '1' : '0'); }
    catch {}
  }, [collapsed]);

  const isActive = (path) => location.pathname === path;

  const fallbackIconByKeyOrPath = (item) => {
    const k = String(item?.key || '').toLowerCase();
    const p = String(item?.path || '').toLowerCase();
    if (k.includes('dashboard')  || p.includes('dashboard'))    return 'fas fa-chart-line';
    if (k.includes('pos')        || p === '/' || p.includes('/pos')) return 'fas fa-cash-register';
    if (k.includes('products')   || p.includes('products'))     return 'fas fa-boxes-stacked';
    if (k.includes('customers')  || p.includes('customers'))    return 'fas fa-users';
    if (k.includes('operations') || p.includes('operations'))   return 'fas fa-receipt';
    if (k.includes('returns')    || p.includes('returns'))      return 'fas fa-rotate-left';
    if (k.includes('reports')    || p.includes('reports'))      return 'fas fa-file-invoice';
    if (k.includes('cash')       || p.includes('cash-register'))return 'fas fa-money-bill-wave';
    if (k.includes('inventory')  || p.includes('inventory'))    return 'fas fa-warehouse';
    if (k.includes('users')      || p.includes('/users'))       return 'fas fa-user-cog';
    if (k.includes('performance')|| p.includes('performance'))  return 'fas fa-trophy';
    if (k.includes('settings')   || p.includes('settings'))     return 'fas fa-gear';
    return 'fas fa-circle';
  };

  // هل المستخدم يرى badges المرتجعات؟
  const isAdminVal   = typeof isAdmin   === 'function' ? isAdmin()   : !!isAdmin;
  const isManagerVal = typeof isManager === 'function' ? isManager() : !!isManager;
  const canSeeBadge  = isAdminVal || isManagerVal;

  const isReturnItem = (item) =>
    String(item?.path || '').includes('returns') ||
    String(item?.key  || '').toLowerCase().includes('return');

  return (
    <aside
      className={`bg-gray-800 text-white ${collapsed ? 'w-20' : 'w-64'} h-full p-4 overflow-y-auto flex flex-col transition-all duration-200`}
      aria-label="Sidebar"
    >
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
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
      <nav className="space-y-2 flex-1">
        {items.map((item) => {
          const active  = isActive(item.path);
          const iconCls = (item.icon && String(item.icon).includes('fa'))
            ? item.icon
            : fallbackIconByKeyOrPath(item);

          // حساب الـ badge لعنصر المرتجعات
          const showBadge   = canSeeBadge && isReturnItem(item);
          const badgeCount  = showBadge ? (pending + approved) : 0;
          const badgeCls    = pending > 0
            ? 'bg-red-500'       // أحمر لو فيه pending
            : 'bg-orange-400';   // برتقالي لو فيه approved بس

          return (
            <Link
              key={item.key || item.path}
              to={item.path}
              title={collapsed ? item.label : undefined}
              className={`relative flex items-center p-3 rounded-lg transition-colors ${
                active ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              } ${collapsed ? 'justify-center' : ''}`}
            >
              <i className={`${iconCls} ${collapsed ? '' : 'ml-3'}`}></i>
              {!collapsed && <span className="font-medium flex-1">{item.label}</span>}

              {/* Badge */}
              {showBadge && badgeCount > 0 && (
                <span className={`${badgeCls} text-white text-xs font-bold rounded-full min-w-[20px] h-5 flex items-center justify-center px-1 ${collapsed ? 'absolute top-1 right-1' : ''}`}>
                  {badgeCount > 99 ? '99+' : badgeCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="pt-4 border-t border-gray-700 text-xs text-gray-400">
        {!collapsed ? 'Dynamic UI' : 'UI'}
      </div>
    </aside>
  );
}
"""

# ══════════════════════════════════════════════════════════════════════
# 3.  pages/ReturnsPage.jsx
#     — صفحة مستقلة بـ 3 تبويبات: pending / approved / all
# ══════════════════════════════════════════════════════════════════════
RETURNS_PAGE = """\
import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { returnsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useReturnsBadge } from '../context/ReturnsBadgeContext';

/* ── helpers ── */
const STATUS_CFG = {
  pending:   { text: 'قيد المراجعة', cls: 'bg-yellow-100 text-yellow-800' },
  approved:  { text: 'موافق عليه',   cls: 'bg-blue-100  text-blue-800'   },
  completed: { text: 'مكتمل',        cls: 'bg-green-100 text-green-800'  },
  rejected:  { text: 'مرفوض',        cls: 'bg-red-100   text-red-800'    },
};

const Badge = ({ s }) => {
  const c = STATUS_CFG[s] || { text: s, cls: 'bg-gray-100 text-gray-700' };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${c.cls}`}>
      {c.text}
    </span>
  );
};

const Spinner = () => (
  <div className="flex items-center justify-center py-16">
    <i className="fas fa-spinner fa-spin text-3xl text-blue-500"></i>
  </div>
);

/* ── component ── */
export default function ReturnsPage() {
  const { isAdmin, isManager } = useAuth();
  const { refresh: refreshBadge } = useReturnsBadge();

  const isAdminVal   = typeof isAdmin   === 'function' ? isAdmin()   : !!isAdmin;
  const isManagerVal = typeof isManager === 'function' ? isManager() : !!isManager;
  const canManage    = isAdminVal || isManagerVal;

  const [tab, setTab]           = useState('pending');   // pending | approved | all
  const [returns, setReturns]   = useState([]);
  const [loading, setLoading]   = useState(false);
  const [actionId, setActionId] = useState(null);
  const [toast, setToast]       = useState(null);
  const [stats, setStats]       = useState(null);

  const notify = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  /* جلب البيانات */
  const fetchReturns = useCallback(async () => {
    setLoading(true);
    try {
      const params = tab !== 'all' ? { status: tab } : {};
      const res    = await returnsAPI.getAll(params);
      setReturns(res.data?.results ?? res.data ?? []);
    } catch {
      notify('تعذر تحميل المرتجعات', 'error');
    } finally {
      setLoading(false);
    }
  }, [tab]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await returnsAPI.getStats();
      setStats(res.data);
    } catch {}
  }, []);

  useEffect(() => {
    fetchReturns();
    fetchStats();
  }, [fetchReturns, fetchStats]);

  /* إجراء على مرتجع */
  const handleAction = async (returnId, action) => {
    setActionId(returnId + action);
    try {
      await returnsAPI[action](returnId);
      const labels = {
        approve:  'تمت الموافقة ✅',
        complete: 'تم إكمال المرتجع وإرجاع المخزون 📦',
        reject:   'تم الرفض ❌',
      };
      notify(labels[action] || 'تم');
      await fetchReturns();
      await fetchStats();
      refreshBadge();          // تحديث الـ badge فوراً
    } catch (e) {
      notify(e?.response?.data?.error || 'خطأ في العملية', 'error');
    } finally {
      setActionId(null);
    }
  };

  /* الـ tabs */
  const TABS = [
    { key: 'pending',  label: 'تحتاج موافقة',    icon: 'fas fa-clock',         color: 'text-yellow-600' },
    { key: 'approved', label: 'جاهزة للإكمال',   icon: 'fas fa-box-open',      color: 'text-blue-600'   },
    { key: 'all',      label: 'كل المرتجعات',    icon: 'fas fa-list',          color: 'text-gray-600'   },
  ];

  return (
    <div className="p-6" dir="rtl">

      {/* Toast */}
      {toast && (
        <div className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-2xl shadow-xl font-bold text-sm
          ${toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-gray-800">
          <i className="fas fa-rotate-left ml-2 text-orange-500"></i>
          إدارة المرتجعات
        </h1>
        <button
          onClick={() => { fetchReturns(); fetchStats(); refreshBadge(); }}
          className="px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-semibold"
        >
          <i className="fas fa-sync-alt ml-1"></i> تحديث
        </button>
      </div>

      {/* إحصائيات سريعة */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          {[
            { label: 'اليوم',       val: stats.today?.count   ?? 0, sub: `${stats.today?.amount   ?? 0} ر.س`, cls: 'border-green-200  bg-green-50'  },
            { label: 'الأسبوع',     val: stats.week?.count    ?? 0, sub: `${stats.week?.amount    ?? 0} ر.س`, cls: 'border-blue-200   bg-blue-50'   },
            { label: 'قيد المراجعة',val: stats.pending?.count ?? 0, sub: `${stats.pending?.amount ?? 0} ر.س`, cls: 'border-yellow-200 bg-yellow-50' },
            { label: 'الشهر',       val: stats.month?.count   ?? 0, sub: `${stats.month?.amount   ?? 0} ر.س`, cls: 'border-purple-200 bg-purple-50' },
          ].map((c) => (
            <div key={c.label} className={`rounded-xl border p-4 ${c.cls}`}>
              <div className="text-xs text-gray-500 mb-1">{c.label}</div>
              <div className="text-2xl font-bold text-gray-800">{c.val}</div>
              <div className="text-xs text-gray-600">{c.sub}</div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="flex gap-2 p-3 border-b border-gray-200 flex-wrap">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                tab === t.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <i className={`${t.icon} ${tab !== t.key ? t.color : ''}`}></i>
              {t.label}
              {/* عداد صغير جنب الـ tab */}
              {t.key === 'pending'  && (stats?.pending?.count  ?? 0) > 0 && (
                <span className="bg-red-500    text-white text-xs rounded-full px-1.5 py-0.5">
                  {stats.pending.count}
                </span>
              )}
              {t.key === 'approved' && (stats?.approved?.count ?? 0) > 0 && (
                <span className="bg-orange-400 text-white text-xs rounded-full px-1.5 py-0.5">
                  {stats?.approved?.count ?? 0}
                </span>
              )}
            </button>
          ))}
        </div>

        <div className="p-4">
          {loading ? <Spinner /> : returns.length === 0 ? (
            <div className="text-center text-gray-500 py-12">
              <i className="fas fa-inbox text-4xl mb-3 block text-gray-300"></i>
              لا توجد مرتجعات في هذا التبويب
            </div>
          ) : (
            <div className="space-y-3">
              {returns.map((r) => (
                <div key={r.id}
                  className="border border-gray-200 rounded-xl p-4 hover:border-orange-300 transition-colors">

                  {/* Row 1 — معلومات رئيسية */}
                  <div className="flex items-start justify-between flex-wrap gap-3">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-sm font-bold text-gray-700">
                        #{String(r.id).slice(0, 8)}
                      </span>
                      <Badge s={r.status} />
                      {r.sale_number && (
                        <span className="text-xs text-gray-500">
                          فاتورة: <span className="font-mono font-semibold">{r.sale_number}</span>
                        </span>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-orange-700 text-lg">{r.total_amount} ر.س</div>
                      <div className="text-xs text-gray-400">
                        {new Date(r.created_at).toLocaleString('ar-SA')}
                      </div>
                    </div>
                  </div>

                  {/* Row 2 — معلومات إضافية */}
                  <div className="mt-2 flex flex-wrap gap-4 text-xs text-gray-600">
                    {r.user_name && (
                      <span><i className="fas fa-user ml-1"></i>{r.user_name}</span>
                    )}
                    {r.customer_name && (
                      <span><i className="fas fa-person ml-1"></i>{r.customer_name}</span>
                    )}
                    {r.items_count != null && (
                      <span><i className="fas fa-boxes ml-1"></i>{r.items_count} صنف</span>
                    )}
                    {r.reason && (
                      <span className="text-orange-600">
                        <i className="fas fa-comment ml-1"></i>{r.reason}
                      </span>
                    )}
                  </div>

                  {/* Row 3 — أزرار الإجراءات */}
                  <div className="mt-3 flex items-center gap-2 flex-wrap">
                    {/* رابط الفاتورة الأصلية */}
                    {r.sale && (
                      <Link
                        to={`/operations/${r.sale}`}
                        className="px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold"
                      >
                        <i className="fas fa-receipt ml-1"></i>عرض الفاتورة
                      </Link>
                    )}

                    {canManage && r.status === 'pending' && (
                      <>
                        <button
                          onClick={() => handleAction(r.id, 'approve')}
                          disabled={!!actionId}
                          className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold disabled:opacity-50"
                        >
                          {actionId === r.id + 'approve'
                            ? <i className="fas fa-spinner fa-spin"></i>
                            : '✅ موافقة'}
                        </button>
                        <button
                          onClick={() => handleAction(r.id, 'reject')}
                          disabled={!!actionId}
                          className="px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-700 text-xs font-bold disabled:opacity-50"
                        >
                          {actionId === r.id + 'reject'
                            ? <i className="fas fa-spinner fa-spin"></i>
                            : '❌ رفض'}
                        </button>
                      </>
                    )}

                    {canManage && r.status === 'approved' && (
                      <button
                        onClick={() => handleAction(r.id, 'complete')}
                        disabled={!!actionId}
                        className="px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-bold disabled:opacity-50"
                      >
                        {actionId === r.id + 'complete'
                          ? <i className="fas fa-spinner fa-spin"></i>
                          : '📦 إكمال وإرجاع المخزون'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
"""

# ══════════════════════════════════════════════════════════════════════
# 4.  App.jsx  — لف الـ app بـ ReturnsBadgeProvider
# ══════════════════════════════════════════════════════════════════════
APP_CONTENT = """\
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { CartProvider } from './context/CartContext';
import { LanguageProvider } from './context/LanguageContext';
import { ReturnsBadgeProvider } from './context/ReturnsBadgeContext';
import Navbar from './components/Navbar';
import DynamicSidebar from './components/DynamicSidebar';
import DynamicRoutes from './components/DynamicRoutes';
import ErrorBoundary from './components/ErrorBoundary';
import Login from './pages/Login';
import React from 'react';

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="flex items-center justify-center h-screen">
      <i className="fas fa-spinner fa-spin text-6xl text-blue-600"></i>
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  return children;
};

const POSProtectedRoute = ({ children }) => {
  const { user, loading, isCashier } = useAuth();
  const [currentShift, setCurrentShift] = React.useState(null);
  const [shiftLoading, setShiftLoading] = React.useState(true);

  React.useEffect(() => {
    if (user && isCashier()) {
      (async () => {
        try {
          const { cashRegisterAPI } = await import('./services/api');
          const response = await cashRegisterAPI.getCurrent();
          setCurrentShift(response.data);
        } catch {
          setCurrentShift(null);
        } finally {
          setShiftLoading(false);
        }
      })();
    } else {
      setShiftLoading(false);
    }
  }, [user]);

  if (loading || shiftLoading) return (
    <div className="flex items-center justify-center h-screen">
      <i className="fas fa-spinner fa-spin text-6xl text-blue-600"></i>
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  if (isCashier() && !currentShift) return <Navigate to="/cash-register" replace />;
  return children;
};

const MainLayout = () => {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="flex items-center justify-center h-screen">
      <i className="fas fa-spinner fa-spin text-6xl text-blue-600"></i>
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  return (
    <div className="flex flex-col h-screen">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <DynamicSidebar />
        <main className="flex-1 overflow-y-auto">
          <ErrorBoundary>
            <DynamicRoutes ProtectedRoute={ProtectedRoute} POSProtectedRoute={POSProtectedRoute} />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
};

function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <ReturnsBadgeProvider>
          <CartProvider>
            <Router>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/*" element={<MainLayout />} />
              </Routes>
            </Router>
          </CartProvider>
        </ReturnsBadgeProvider>
      </AuthProvider>
    </LanguageProvider>
  );
}

export default App;
"""

# ══════════════════════════════════════════════════════════════════════
# 5.  DynamicRoutes.jsx  — إضافة مسار /returns ثابت
# ══════════════════════════════════════════════════════════════════════
ROUTES_CONTENT = """\
import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { lazyPage } from '../ui/componentLoader';
import { useAuth } from '../context/AuthContext';

const ReturnsPage = lazy(() => import('../pages/ReturnsPage'));

const Fallback = () => (
  <div className="flex items-center justify-center h-[60vh]">
    <i className="fas fa-spinner fa-spin text-4xl text-blue-600"></i>
  </div>
);

export default function DynamicRoutes({ ProtectedRoute, POSProtectedRoute }) {
  const { ui } = useAuth();
  const routes = ui?.routes || [];
  if (!ui) return null;

  return (
    <Suspense fallback={<Fallback />}>
      <Routes>
        {/* مسار ثابت للمرتجعات — مش محتاج يكون في الـ DB */}
        <Route
          path="/returns"
          element={
            <ProtectedRoute>
              <ReturnsPage />
            </ProtectedRoute>
          }
        />

        {routes.map((r) => {
          const Page = lazyPage(r.component);
          const element = (() => {
            if (r.wrapper === 'public') return <Page />;
            if (r.wrapper === 'pos_shift') return (
              <POSProtectedRoute><Page /></POSProtectedRoute>
            );
            return <ProtectedRoute><Page /></ProtectedRoute>;
          })();
          return <Route key={r.key || r.path} path={r.path} element={element} />;
        })}

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
"""

# ══════════════════════════════════════════════════════════════════════
# تحديث api.js — إضافة approved stats لو مش موجودة
# ══════════════════════════════════════════════════════════════════════
def patch_api(path):
    with open(path, encoding='utf-8') as f:
        content = f.read()

    # لو getStats موجودة بالفعل في returnsAPI خليها
    if 'getStats' in content and 'returnsAPI' in content:
        print('  [skip]   api.js — returnsAPI.getStats موجودة مسبقاً')
        return

    old = "export const returnsAPI = {"
    new_block = """\
export const returnsAPI = {
  getAll:    (params) => api.get('/returns/', { params }),
  getOne:    (id)     => api.get(`/returns/${id}/`),
  create:    (data)   => api.post('/returns/', data),
  getStats:  ()       => api.get('/returns/stats/'),
  approve:   (id)     => api.post(`/returns/${id}/approve/`),
  complete:  (id)     => api.post(`/returns/${id}/complete/`),
  reject:    (id)     => api.post(`/returns/${id}/reject/`),
};"""

    if old not in content:
        print('  [warn]   api.js — لم يُعثر على returnsAPI block، راجع الملف يدوياً')
        return

    # استخرج نهاية الـ block الحالي
    start = content.index(old)
    end   = content.index('};', start) + 2
    backup(path)
    content = content[:start] + new_block + content[end:]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  [ok]     {path}')

# ══════════════════════════════════════════════════════════════════════
# تنفيذ
# ══════════════════════════════════════════════════════════════════════
write(FILES['badge_ctx'],    BADGE_CTX)
write(FILES['sidebar'],      SIDEBAR)
write(FILES['returns_page'], RETURNS_PAGE)
write(FILES['app'],          APP_CONTENT)
write(FILES['routes'],       ROUTES_CONTENT)
patch_api(FILES['api'])

print("""
✅ تم بنجاح!

الخطوة الأخيرة — أضف رابط "المرتجعات" في الـ Sidebar من لوحة الأدمن
(أو من أي مكان بتدير فيه ui.sidebar) بالقيم دي:
  path  : /returns
  label : المرتجعات
  icon  : fas fa-rotate-left

ثم شغّل الـ frontend:
  cd pos_frontend && npm run dev
""")
