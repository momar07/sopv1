
import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { salesAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

/* ── ثوابت ── */
const PAYMENT_LABELS = { cash: 'نقدي', card: 'بطاقة', both: 'نقدي+بطاقة' };
const PAYMENT_COLORS = {
  cash: 'bg-green-100 text-green-700',
  card: 'bg-blue-100  text-blue-700',
  both: 'bg-purple-100 text-purple-700',
};
const STATUS_CFG = {
  completed: { text: 'مكتملة',        cls: 'bg-green-100  text-green-800'  },
  cancelled:  { text: 'ملغاة',         cls: 'bg-red-100    text-red-700'    },
  pending:    { text: 'قيد الانتظار',  cls: 'bg-yellow-100 text-yellow-800' },
};
const PAGE_SIZE = 20;

/* ── مكونات مساعدة ── */
const Badge = ({ val, map, colorMap }) => {
  const cfg = map[val]     || { text: val,   cls: 'bg-gray-100 text-gray-600' };
  const cls = colorMap?.[val] || cfg.cls;
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${cls}`}>
      {cfg.text ?? cfg}
    </span>
  );
};

const SummaryCard = ({ label, value, sub, colorCls }) => (
  <div className={`rounded-xl border p-4 ${colorCls}`}>
    <div className="text-xs text-gray-500 mb-1">{label}</div>
    <div className="text-2xl font-bold text-gray-800">{value}</div>
    {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
  </div>
);

const Spinner = () => (
  <div className="flex items-center justify-center py-16">
    <i className="fas fa-spinner fa-spin text-3xl text-blue-500"></i>
  </div>
);

/* ══════════════════════════════════════════════════════════════════ */
const Operations = () => {
  const { isAdmin, isManager } = useAuth();

  /* ✅ إصلاح: isAdmin/isManager هما functions */
  const isAdminVal   = typeof isAdmin   === 'function' ? isAdmin()   : !!isAdmin;
  const isManagerVal = typeof isManager === 'function' ? isManager() : !!isManager;
  const canCancel    = isAdminVal || isManagerVal;

  /* state البيانات */
  const [sales,   setSales]   = useState([]);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');
  const [stats,   setStats]   = useState(null);

  /* state الفلاتر */
  const [search,      setSearch]      = useState('');
  const [statusF,     setStatusF]     = useState('');
  const [paymentF,    setPaymentF]    = useState('');
  const [dateFrom,    setDateFrom]    = useState('');
  const [dateTo,      setDateTo]      = useState('');

  /* state Pagination */
  const [page,       setPage]       = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  /* toast */
  const [toast, setToast] = useState(null);
  const notify = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  /* ── جلب البيانات ── */
  const fetchSales = useCallback(async (overridePage) => {
    const currentPage = overridePage ?? page;
    setLoading(true);
    setError('');
    try {
      const params = {
        limit:    PAGE_SIZE,
        offset:   (currentPage - 1) * PAGE_SIZE,
        ordering: '-created_at',
      };
      if (search.trim())   params.search         = search.trim().replace(/^#/, '');
      if (statusF)         params.status         = statusF;
      if (paymentF)        params.payment_method = paymentF;
      if (dateFrom)        params.start_date     = dateFrom;
      if (dateTo)          params.end_date       = dateTo;

      const res  = await salesAPI.getAll(params);
      const data = res.data;

      /* دعم pagination object أو array مباشر */
      if (data?.results !== undefined) {
        setSales(data.results);
        setTotalCount(data.count ?? data.results.length);
      } else {
        setSales(Array.isArray(data) ? data : []);
        setTotalCount(Array.isArray(data) ? data.length : 0);
      }
    } catch {
      setError('تعذر تحميل العمليات');
    } finally {
      setLoading(false);
    }
  }, [page, search, statusF, paymentF, dateFrom, dateTo]);

  /* جلب إحصائيات سريعة */
  const fetchStats = useCallback(async () => {
    try {
      const res = await salesAPI.getStats();
      setStats(res.data);
    } catch {}
  }, []);

  useEffect(() => { fetchSales(); fetchStats(); }, []);

  /* ── بحث ── */
  const handleSearch = (e) => {
    e?.preventDefault?.();
    setPage(1);
    fetchSales(1);
  };

  const handleReset = () => {
    setSearch('');
    setStatusF('');
    setPaymentF('');
    setDateFrom('');
    setDateTo('');
    setPage(1);
    setTimeout(() => fetchSales(1), 0);
  };

  /* ── Pagination ── */
  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;
  const goTo = (p) => {
    setPage(p);
    fetchSales(p);
  };

  /* ── إلغاء فاتورة ── */
  const handleCancel = async (sale) => {
    if (!sale?.id) return;
    if (!window.confirm('هل أنت متأكد من إلغاء العملية؟ سيتم إرجاع المخزون.')) return;
    try {
      await salesAPI.cancel(sale.id);
      notify('تم إلغاء العملية بنجاح');
      fetchSales();
      fetchStats();
    } catch {
      notify('تعذر إلغاء العملية — تأكد من الصلاحيات', 'error');
    }
  };

  /* ══════════════ render ══════════════ */
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
          <i className="fas fa-receipt ml-2 text-blue-500"></i>
          العمليات
        </h1>
        <button
          onClick={() => { fetchSales(); fetchStats(); }}
          className="px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-semibold"
        >
          <i className="fas fa-sync-alt ml-1"></i> تحديث
        </button>
      </div>

      {/* ── Summary Cards ── */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          <SummaryCard
            label="مبيعات اليوم"
            value={`${stats.today_sales ?? 0} ر.س`}
            sub={`${stats.today_count ?? 0} فاتورة`}
            colorCls="border-green-200 bg-green-50"
          />
          <SummaryCard
            label="مبيعات الأسبوع"
            value={`${stats.week_sales ?? 0} ر.س`}
            colorCls="border-blue-200 bg-blue-50"
          />
          <SummaryCard
            label="مبيعات الشهر"
            value={`${stats.month_sales ?? 0} ر.س`}
            colorCls="border-purple-200 bg-purple-50"
          />
          <SummaryCard
            label="إجمالي الربح"
            value={`${stats.total_profit ?? 0} ر.س`}
            colorCls="border-orange-200 bg-orange-50"
          />
        </div>
      )}

      {/* ── فلاتر البحث (دايماً ظاهرة) ── */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-4">
        <form onSubmit={handleSearch}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">

            {/* نص البحث */}
            <div className="xl:col-span-2">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="رقم الفاتورة أو اسم العميل..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
              />
            </div>

            {/* الحالة */}
            <select
              value={statusF}
              onChange={(e) => setStatusF(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            >
              <option value="">كل الحالات</option>
              <option value="completed">مكتملة</option>
              <option value="cancelled">ملغاة</option>
              <option value="pending">قيد الانتظار</option>
            </select>

            {/* طريقة الدفع */}
            <select
              value={paymentF}
              onChange={(e) => setPaymentF(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            >
              <option value="">كل طرق الدفع</option>
              <option value="cash">نقدي</option>
              <option value="card">بطاقة</option>
              <option value="both">نقدي + بطاقة</option>
            </select>

            {/* من تاريخ */}
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
              title="من تاريخ"
            />

            {/* إلى تاريخ */}
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
              title="إلى تاريخ"
            />
          </div>

          {/* أزرار البحث */}
          <div className="flex gap-2 mt-3">
            <button
              type="submit"
              className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm"
            >
              <i className="fas fa-search ml-1"></i> بحث
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold text-sm"
            >
              <i className="fas fa-times ml-1"></i> مسح
            </button>
          </div>
        </form>
      </div>

      {/* ── الجدول ── */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">

        {/* header الجدول */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <span className="text-sm font-semibold text-gray-600">
            {loading ? 'جاري التحميل...' : `${totalCount} نتيجة`}
          </span>
          {totalPages > 1 && (
            <span className="text-xs text-gray-400">
              صفحة {page} من {totalPages}
            </span>
          )}
        </div>

        {error && (
          <div className="m-4 p-3 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm">
            {error}
          </div>
        )}

        {loading ? <Spinner /> : sales.length === 0 ? (
          <div className="text-center text-gray-500 py-16">
            <i className="fas fa-inbox text-4xl mb-3 block text-gray-300"></i>
            لا توجد عمليات تطابق البحث
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-xs border-b bg-gray-50">
                  <th className="text-right py-3 px-4 font-semibold">رقم الفاتورة</th>
                  <th className="text-right py-3 px-3 font-semibold">العميل</th>
                  <th className="text-right py-3 px-3 font-semibold">الكاشير</th>
                  <th className="text-right py-3 px-3 font-semibold">التاريخ</th>
                  <th className="text-right py-3 px-3 font-semibold">الإجمالي</th>
                  <th className="text-right py-3 px-3 font-semibold">الدفع</th>
                  <th className="text-right py-3 px-3 font-semibold">الحالة</th>
                  <th className="text-right py-3 px-3 font-semibold">مرتجع</th>
                  <th className="text-right py-3 px-3 font-semibold">إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {sales.map((s) => (
                  <tr
                    key={s.id}
                    className={`border-b last:border-b-0 hover:bg-gray-50 transition-colors ${
                      s.status === 'cancelled' ? 'opacity-60' : ''
                    }`}
                  >
                    {/* رقم الفاتورة */}
                    <td className="py-3 px-4">
                      <div className="font-mono text-xs text-gray-800 font-bold">
                        {s.invoice_number
                          ? `#${s.invoice_number}`
                          : `#${String(s.id).slice(0, 8)}`}
                      </div>
                    </td>

                    {/* العميل */}
                    <td className="py-3 px-3 text-gray-800">
                      {s.customer_name
                        ? <span className="font-semibold">{s.customer_name}</span>
                        : <span className="text-gray-400 text-xs">زائر</span>}
                    </td>

                    {/* الكاشير */}
                    <td className="py-3 px-3 text-gray-600 text-xs">
                      {s.user_name || <span className="text-gray-400">—</span>}
                    </td>

                    {/* التاريخ */}
                    <td className="py-3 px-3 text-gray-500 text-xs whitespace-nowrap">
                      {new Date(s.created_at).toLocaleString('ar-SA', {
                        year:  'numeric', month: 'short',
                        day:   'numeric', hour:  '2-digit', minute: '2-digit',
                      })}
                    </td>

                    {/* الإجمالي */}
                    <td className="py-3 px-3 font-bold text-green-700 whitespace-nowrap">
                      {s.total} ر.س
                    </td>

                    {/* طريقة الدفع */}
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                        PAYMENT_COLORS[s.payment_method] ?? 'bg-gray-100 text-gray-600'
                      }`}>
                        {PAYMENT_LABELS[s.payment_method] ?? s.payment_method}
                      </span>
                    </td>

                    {/* الحالة */}
                    <td className="py-3 px-3">
                      {(() => {
                        const cfg = STATUS_CFG[s.status] ?? { text: s.status, cls: 'bg-gray-100 text-gray-600' };
                        return (
                          <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${cfg.cls}`}>
                            {cfg.text}
                          </span>
                        );
                      })()}
                    </td>

                    {/* مرتجع */}
                    <td className="py-3 px-3">
                      {s.has_returns ? (
                        <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-orange-100 text-orange-700">
                          ↩ {s.returns_count ?? ''}
                        </span>
                      ) : (
                        <span className="text-gray-300 text-xs">—</span>
                      )}
                    </td>

                    {/* إجراءات */}
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/operations/${s.id}`}
                          className="px-3 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-bold"
                        >
                          تفاصيل
                        </Link>
                        {canCancel && s.status !== 'cancelled' && (
                          <button
                            type="button"
                            onClick={() => handleCancel(s)}
                            className="px-3 py-1 rounded-lg bg-red-50 hover:bg-red-100 text-red-700 text-xs font-bold"
                          >
                            إلغاء
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Pagination ── */}
        {!loading && totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
            <button
              onClick={() => goTo(page - 1)}
              disabled={page <= 1}
              className="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <i className="fas fa-chevron-right ml-1"></i> السابق
            </button>

            {/* أرقام الصفحات (max 5) */}
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                const start = Math.max(1, Math.min(page - 2, totalPages - 4));
                const p = start + i;
                return (
                  <button
                    key={p}
                    onClick={() => goTo(p)}
                    className={`w-9 h-9 rounded-lg text-sm font-bold transition-colors ${
                      p === page
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                    }`}
                  >
                    {p}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => goTo(page + 1)}
              disabled={page >= totalPages}
              className="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
            >
              التالي <i className="fas fa-chevron-left mr-1"></i>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Operations;
