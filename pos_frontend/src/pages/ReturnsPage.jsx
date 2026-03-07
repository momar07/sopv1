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
