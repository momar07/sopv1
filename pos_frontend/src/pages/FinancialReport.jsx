import { useState, useEffect, useCallback } from 'react';
import { salesAPI, returnsAPI, cashRegisterAPI } from '../services/api';

/* ── ثوابت ── */
const TODAY = new Date().toISOString().slice(0, 10);
const WEEK_AGO = new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10);
const MONTH_AGO = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10);

const QUICK_RANGES = [
  { label: 'اليوم',   from: TODAY,     to: TODAY     },
  { label: 'الأسبوع', from: WEEK_AGO,  to: TODAY     },
  { label: 'الشهر',   from: MONTH_AGO, to: TODAY     },
];

const fmt  = (n) => Number(n || 0).toLocaleString('ar-SA', { minimumFractionDigits: 2 });
const fmtD = (iso) => iso ? new Date(iso).toLocaleString('ar-SA') : '—';

const Spinner = () => (
  <div className="flex items-center justify-center py-16">
    <i className="fas fa-spinner fa-spin text-3xl text-blue-500"></i>
  </div>
);

const KPI = ({ label, value, sub, icon, color }) => (
  <div className={`rounded-xl border p-5 ${color}`}>
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm font-semibold text-gray-600">{label}</span>
      <i className={`${icon} text-xl opacity-60`}></i>
    </div>
    <div className="text-3xl font-bold text-gray-800">{value}</div>
    {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
  </div>
);

/* ══════════════════════════════════════════════════════════════════ */
export default function FinancialReport() {
  const [tab, setTab]           = useState('summary');
  const [dateFrom, setDateFrom] = useState(MONTH_AGO);
  const [dateTo,   setDateTo]   = useState(TODAY);
  const [loading,  setLoading]  = useState(false);

  /* بيانات */
  const [salesStats,   setSalesStats]   = useState(null);
  const [returnsStats, setReturnsStats] = useState(null);
  const [salesData,    setSalesData]    = useState(null);
  const [returnsData,  setReturnsData]  = useState([]);
  const [shifts,       setShifts]       = useState([]);
  const [shiftDetails, setShiftDetails] = useState(null);
  const [showModal,    setShowModal]    = useState(false);

  /* ── جلب الإحصائيات الدورية ── */
  const fetchStats = useCallback(async () => {
    try {
      const [sRes, rRes] = await Promise.all([
        salesAPI.getStats(),
        returnsAPI.getStats(),
      ]);
      setSalesStats(sRes.data);
      setReturnsStats(rRes.data);
    } catch {}
  }, []);

  useEffect(() => { fetchStats(); }, [fetchStats]);

  /* ── تقرير المبيعات ── */
  const fetchSalesReport = async () => {
    if (!dateFrom || !dateTo) return;
    setLoading(true);
    try {
      const res = await salesAPI.getByDateRange(dateFrom, dateTo);
      setSalesData(res.data);
    } catch {
      alert('تعذر تحميل تقرير المبيعات');
    } finally {
      setLoading(false);
    }
  };

  /* ── تقرير المرتجعات ── */
  const fetchReturnsReport = async () => {
    if (!dateFrom || !dateTo) return;
    setLoading(true);
    try {
      const res = await returnsAPI.getAll({
        start_date: dateFrom,
        end_date:   dateTo,
        status:     'completed',
      });
      setReturnsData(res.data?.results ?? res.data ?? []);
    } catch {
      alert('تعذر تحميل تقرير المرتجعات');
    } finally {
      setLoading(false);
    }
  };

  /* ── تقرير الشيفتات ── */
  const fetchShifts = useCallback(async () => {
    setLoading(true);
    try {
      const res  = await cashRegisterAPI.getAll({});
      const data = res.data?.results ?? res.data ?? [];
      setShifts(Array.isArray(data) ? data.filter(s => s.status === 'closed') : []);
    } catch {} finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === 'shifts') fetchShifts();
  }, [tab, fetchShifts]);

  const openShift = async (id) => {
    try {
      const res = await cashRegisterAPI.getOne(id);
      setShiftDetails(res.data);
      setShowModal(true);
    } catch {
      alert('تعذر تحميل تفاصيل الشيفت');
    }
  };

  /* ── تطبيق نطاق سريع ── */
  const applyRange = (from, to) => {
    setDateFrom(from);
    setDateTo(to);
  };

  /* ── حساب الصافي ── */
  const netSales    = Number(salesStats?.today_sales  ?? 0);
  const netReturns  = Number(returnsStats?.today?.amount ?? 0);
  const netProfit   = Number(salesStats?.total_profit ?? 0);

  /* ══════════ TABS ══════════ */
  const TABS = [
    { key: 'summary',  label: 'الملخص المالي',    icon: 'fas fa-chart-pie'       },
    { key: 'sales',    label: 'تقرير المبيعات',   icon: 'fas fa-shopping-cart'   },
    { key: 'returns',  label: 'تقرير المرتجعات',  icon: 'fas fa-rotate-left'     },
    { key: 'shifts',   label: 'تقارير الشيفتات',  icon: 'fas fa-cash-register'   },
  ];

  return (
    <div className="p-6" dir="rtl">

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-gray-800">
          <i className="fas fa-chart-line ml-2 text-green-600"></i>
          التقرير المالي
        </h1>
        <button
          onClick={fetchStats}
          className="px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-semibold"
        >
          <i className="fas fa-sync-alt ml-1"></i> تحديث
        </button>
      </div>

      {/* ── فلتر التاريخ (دايماً ظاهر) ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-5">
        <div className="flex flex-wrap items-center gap-3">
          {/* نطاقات سريعة */}
          {QUICK_RANGES.map((r) => (
            <button
              key={r.label}
              onClick={() => applyRange(r.from, r.to)}
              className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors ${
                dateFrom === r.from && dateTo === r.to
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
              }`}
            >
              {r.label}
            </button>
          ))}

          <div className="flex items-center gap-2 mr-auto">
            <input
              type="date" value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
            />
            <span className="text-gray-400 text-sm">←</span>
            <input
              type="date" value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
            />
            <button
              onClick={() => {
                if (tab === 'sales')   fetchSalesReport();
                if (tab === 'returns') fetchReturnsReport();
              }}
              className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold"
            >
              <i className="fas fa-search ml-1"></i> تطبيق
            </button>
          </div>
        </div>
      </div>

      {/* ── Tabs ── */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="flex gap-1 p-3 border-b border-gray-200 flex-wrap">
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
              <i className={t.icon}></i>
              {t.label}
            </button>
          ))}
        </div>

        <div className="p-5">

          {/* ══ تبويب الملخص ══ */}
          {tab === 'summary' && (
            <div className="space-y-6">

              {/* KPI Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KPI
                  label="مبيعات اليوم"
                  value={`${fmt(salesStats?.today_sales)} ر.س`}
                  sub={`${salesStats?.today_count ?? 0} فاتورة`}
                  icon="fas fa-shopping-bag"
                  color="border-green-200 bg-green-50"
                />
                <KPI
                  label="مبيعات الأسبوع"
                  value={`${fmt(salesStats?.week_sales)} ر.س`}
                  icon="fas fa-calendar-week"
                  color="border-blue-200 bg-blue-50"
                />
                <KPI
                  label="مبيعات الشهر"
                  value={`${fmt(salesStats?.month_sales)} ر.س`}
                  icon="fas fa-calendar-alt"
                  color="border-purple-200 bg-purple-50"
                />
                <KPI
                  label="إجمالي الربح"
                  value={`${fmt(salesStats?.total_profit)} ر.س`}
                  icon="fas fa-coins"
                  color="border-yellow-200 bg-yellow-50"
                />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KPI
                  label="مرتجعات اليوم"
                  value={`${fmt(returnsStats?.today?.amount)} ر.س`}
                  sub={`${returnsStats?.today?.count ?? 0} مرتجع`}
                  icon="fas fa-rotate-left"
                  color="border-red-200 bg-red-50"
                />
                <KPI
                  label="مرتجعات الأسبوع"
                  value={`${fmt(returnsStats?.week?.amount)} ر.س`}
                  icon="fas fa-rotate-left"
                  color="border-orange-200 bg-orange-50"
                />
                <KPI
                  label="مرتجعات الشهر"
                  value={`${fmt(returnsStats?.month?.amount)} ر.س`}
                  icon="fas fa-rotate-left"
                  color="border-pink-200 bg-pink-50"
                />
                <KPI
                  label="قيد المراجعة"
                  value={returnsStats?.pending?.count ?? 0}
                  sub={`${fmt(returnsStats?.pending?.amount)} ر.س`}
                  icon="fas fa-clock"
                  color="border-yellow-200 bg-yellow-50"
                />
              </div>

              {/* صافي اليوم */}
              <div className="rounded-xl border border-gray-200 p-5 bg-gray-50">
                <h3 className="font-bold text-gray-700 mb-4 text-sm">
                  <i className="fas fa-balance-scale ml-2"></i>
                  الصافي التقريبي — اليوم
                </h3>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">المبيعات</div>
                    <div className="text-xl font-bold text-green-700">+{fmt(salesStats?.today_sales)} ر.س</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">المرتجعات</div>
                    <div className="text-xl font-bold text-red-600">-{fmt(returnsStats?.today?.amount)} ر.س</div>
                  </div>
                  <div className="border-r border-gray-200 pr-4">
                    <div className="text-xs text-gray-500 mb-1">الصافي</div>
                    <div className={`text-xl font-bold ${
                      (Number(salesStats?.today_sales ?? 0) - Number(returnsStats?.today?.amount ?? 0)) >= 0
                        ? 'text-blue-700' : 'text-red-700'
                    }`}>
                      {fmt(Number(salesStats?.today_sales ?? 0) - Number(returnsStats?.today?.amount ?? 0))} ر.س
                    </div>
                  </div>
                </div>
              </div>

              {/* أكثر المنتجات مبيعاً */}
              {salesStats?.top_products?.length > 0 && (
                <div>
                  <h3 className="font-bold text-gray-700 mb-3 text-sm">
                    <i className="fas fa-trophy ml-2 text-yellow-500"></i>
                    أكثر المنتجات مبيعاً — الشهر
                  </h3>
                  <div className="space-y-2">
                    {salesStats.top_products.map((p, i) => (
                      <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 border border-gray-100">
                        <div className="flex items-center gap-3">
                          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                            i === 0 ? 'bg-yellow-400' : i === 1 ? 'bg-gray-400' : i === 2 ? 'bg-orange-400' : 'bg-blue-400'
                          }`}>{i + 1}</span>
                          <span className="font-semibold text-sm text-gray-800">{p.product__name}</span>
                        </div>
                        <div className="text-left">
                          <div className="text-sm font-bold text-gray-700">{p.total_quantity} قطعة</div>
                          <div className="text-xs text-gray-500">{fmt(p.total_sales)} ر.س</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ══ تبويب المبيعات ══ */}
          {tab === 'sales' && (
            <div className="space-y-4">
              <div className="flex justify-end">
                <button
                  onClick={fetchSalesReport}
                  disabled={loading}
                  className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm disabled:opacity-50"
                >
                  {loading
                    ? <><i className="fas fa-spinner fa-spin ml-1"></i> جاري التحميل...</>
                    : <><i className="fas fa-chart-bar ml-1"></i> إنشاء التقرير</>}
                </button>
              </div>

              {salesData && (
                <>
                  {/* ملخص */}
                  <div className="grid grid-cols-3 gap-4">
                    <KPI label="إجمالي المبيعات" value={`${fmt(salesData.stats?.total_sales)} ر.س`} icon="fas fa-coins"      color="border-blue-200 bg-blue-50"   />
                    <KPI label="عدد الفواتير"     value={salesData.stats?.total_count ?? 0}          icon="fas fa-receipt"    color="border-green-200 bg-green-50" />
                    <KPI label="متوسط الفاتورة"   value={`${fmt(salesData.stats?.avg_sale)} ر.س`}    icon="fas fa-calculator" color="border-purple-200 bg-purple-50"/>
                  </div>

                  {/* جدول */}
                  <div className="overflow-x-auto rounded-xl border border-gray-200">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-600 text-xs">
                          <th className="text-right py-3 px-4">رقم الفاتورة</th>
                          <th className="text-right py-3 px-3">العميل</th>
                          <th className="text-right py-3 px-3">الكاشير</th>
                          <th className="text-right py-3 px-3">المبلغ</th>
                          <th className="text-right py-3 px-3">الدفع</th>
                          <th className="text-right py-3 px-3">التاريخ</th>
                        </tr>
                      </thead>
                      <tbody>
                        {salesData.sales?.length > 0 ? salesData.sales.map((s) => (
                          <tr key={s.id} className="border-b hover:bg-gray-50">
                            <td className="py-3 px-4 font-mono text-xs font-bold">
                              {s.invoice_number ? `#${s.invoice_number}` : `#${String(s.id).slice(0,8)}`}
                            </td>
                            <td className="py-3 px-3">{s.customer_name || <span className="text-gray-400">زائر</span>}</td>
                            <td className="py-3 px-3 text-xs text-gray-600">{s.user_name || '—'}</td>
                            <td className="py-3 px-3 font-bold text-green-700">{fmt(s.total)} ر.س</td>
                            <td className="py-3 px-3">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                                s.payment_method === 'cash' ? 'bg-green-100 text-green-700' :
                                s.payment_method === 'card' ? 'bg-blue-100 text-blue-700' :
                                'bg-purple-100 text-purple-700'
                              }`}>
                                {s.payment_method === 'cash' ? 'نقدي' : s.payment_method === 'card' ? 'بطاقة' : 'نقدي+بطاقة'}
                              </span>
                            </td>
                            <td className="py-3 px-3 text-xs text-gray-500">{fmtD(s.created_at)}</td>
                          </tr>
                        )) : (
                          <tr><td colSpan="6" className="py-10 text-center text-gray-400">لا توجد مبيعات في هذه الفترة</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              )}

              {!salesData && !loading && (
                <div className="text-center py-16 text-gray-400">
                  <i className="fas fa-chart-bar text-5xl mb-3 block"></i>
                  اضغط "إنشاء التقرير" لعرض المبيعات
                </div>
              )}
            </div>
          )}

          {/* ══ تبويب المرتجعات ══ */}
          {tab === 'returns' && (
            <div className="space-y-4">

              {/* إحصائيات ثابتة */}
              {returnsStats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <KPI label="مرتجعات اليوم"   value={`${fmt(returnsStats.today?.amount)} ر.س`}  sub={`${returnsStats.today?.count ?? 0} مرتجع`}  icon="fas fa-rotate-left" color="border-red-200 bg-red-50"     />
                  <KPI label="مرتجعات الأسبوع" value={`${fmt(returnsStats.week?.amount)} ر.س`}   sub={`${returnsStats.week?.count ?? 0} مرتجع`}   icon="fas fa-rotate-left" color="border-orange-200 bg-orange-50"/>
                  <KPI label="مرتجعات الشهر"   value={`${fmt(returnsStats.month?.amount)} ر.س`}  sub={`${returnsStats.month?.count ?? 0} مرتجع`}  icon="fas fa-rotate-left" color="border-pink-200 bg-pink-50"   />
                  <KPI label="قيد المراجعة"    value={returnsStats.pending?.count ?? 0}           sub={`${fmt(returnsStats.pending?.amount)} ر.س`} icon="fas fa-clock"       color="border-yellow-200 bg-yellow-50"/>
                </div>
              )}

              <div className="flex justify-end">
                <button
                  onClick={fetchReturnsReport}
                  disabled={loading}
                  className="px-5 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold text-sm disabled:opacity-50"
                >
                  {loading
                    ? <><i className="fas fa-spinner fa-spin ml-1"></i> جاري التحميل...</>
                    : <><i className="fas fa-rotate-left ml-1"></i> إنشاء التقرير</>}
                </button>
              </div>

              {returnsData.length > 0 && (
                <>
                  <div className="overflow-x-auto rounded-xl border border-gray-200">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-600 text-xs">
                          <th className="text-right py-3 px-4">رقم المرتجع</th>
                          <th className="text-right py-3 px-3">الفاتورة</th>
                          <th className="text-right py-3 px-3">العميل</th>
                          <th className="text-right py-3 px-3">الموظف</th>
                          <th className="text-right py-3 px-3">المبلغ المسترد</th>
                          <th className="text-right py-3 px-3">الأصناف</th>
                          <th className="text-right py-3 px-3">التاريخ</th>
                        </tr>
                      </thead>
                      <tbody>
                        {returnsData.map((r) => (
                          <tr key={r.id} className="border-b hover:bg-gray-50">
                            <td className="py-3 px-4 font-mono text-xs font-bold">#{String(r.id).slice(0,8)}</td>
                            <td className="py-3 px-3 font-mono text-xs">#{r.sale_number || String(r.sale).slice(0,8)}</td>
                            <td className="py-3 px-3">{r.customer_name || <span className="text-gray-400">زائر</span>}</td>
                            <td className="py-3 px-3 text-xs text-gray-600">{r.user_name || '—'}</td>
                            <td className="py-3 px-3 font-bold text-red-600">{fmt(r.total_amount)} ر.س</td>
                            <td className="py-3 px-3 text-center">
                              <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full text-xs font-bold">{r.items_count}</span>
                            </td>
                            <td className="py-3 px-3 text-xs text-gray-500">{fmtD(r.created_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* ملخص */}
                  <div className="flex justify-between items-center p-4 bg-red-50 rounded-xl border border-red-100">
                    <span className="font-semibold text-gray-700">إجمالي المرتجعات: <strong>{returnsData.length}</strong></span>
                    <span className="font-bold text-red-700 text-lg">
                      {fmt(returnsData.reduce((s, r) => s + Number(r.total_amount || 0), 0))} ر.س
                    </span>
                  </div>
                </>
              )}

              {returnsData.length === 0 && !loading && (
                <div className="text-center py-16 text-gray-400">
                  <i className="fas fa-rotate-left text-5xl mb-3 block"></i>
                  اضغط "إنشاء التقرير" لعرض المرتجعات
                </div>
              )}
            </div>
          )}

          {/* ══ تبويب الشيفتات ══ */}
          {tab === 'shifts' && (
            <div>
              {loading ? <Spinner /> : (
                <>
                  <div className="overflow-x-auto rounded-xl border border-gray-200">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-600 text-xs">
                          <th className="text-right py-3 px-4">الكاشير</th>
                          <th className="text-right py-3 px-3">الفتح</th>
                          <th className="text-right py-3 px-3">الإغلاق</th>
                          <th className="text-right py-3 px-3">إجمالي المبيعات</th>
                          <th className="text-right py-3 px-3">المرتجعات</th>
                          <th className="text-right py-3 px-3">الصافي</th>
                          <th className="text-right py-3 px-3">فرق النقدية</th>
                          <th className="text-right py-3 px-3"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {shifts.filter(s => {
                          const d = s.opened_at?.slice(0,10);
                          if (!d) return true;
                          if (dateFrom && d < dateFrom) return false;
                          if (dateTo   && d > dateTo)   return false;
                          return true;
                        }).slice(0, 50).map((s) => {
                          const net = Number(s.total_sales||0) - Number(s.total_returns||0);
                          return (
                            <tr key={s.id} className="border-b hover:bg-gray-50">
                              <td className="py-3 px-4 font-semibold">{s.user_name || '—'}</td>
                              <td className="py-3 px-3 text-xs text-gray-500">{fmtD(s.opened_at)}</td>
                              <td className="py-3 px-3 text-xs text-gray-500">{fmtD(s.closed_at)}</td>
                              <td className="py-3 px-3 font-bold text-green-700">{fmt(s.total_sales)} ر.س</td>
                              <td className="py-3 px-3 font-bold text-red-600">{fmt(s.total_returns)} ر.س</td>
                              <td className="py-3 px-3 font-bold text-blue-700">{fmt(net)} ر.س</td>
                              <td className="py-3 px-3">
                                <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                                  Number(s.cash_difference||0) === 0
                                    ? 'bg-green-100 text-green-700'
                                    : Number(s.cash_difference||0) > 0
                                    ? 'bg-blue-100 text-blue-700'
                                    : 'bg-red-100 text-red-700'
                                }`}>
                                  {fmt(s.cash_difference)} ر.س
                                </span>
                              </td>
                              <td className="py-3 px-3">
                                <button
                                  onClick={() => openShift(s.id)}
                                  className="px-3 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-bold"
                                >
                                  تفاصيل
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                        {shifts.length === 0 && (
                          <tr><td colSpan="8" className="py-10 text-center text-gray-400">لا توجد شيفتات مغلقة</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ══ Modal تفاصيل الشيفت ══ */}
      {showModal && shiftDetails && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <h3 className="font-bold text-lg">تفاصيل الشيفت</h3>
              <button onClick={() => { setShowModal(false); setShiftDetails(null); }}
                className="text-gray-400 hover:text-gray-700 text-xl font-black">×</button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: 'الكاشير',    val: shiftDetails.user_name || '—'                                      },
                  { label: 'الحالة',     val: shiftDetails.status === 'closed' ? 'مغلق' : 'مفتوح'               },
                  { label: 'وقت الفتح',  val: fmtD(shiftDetails.opened_at)                                       },
                  { label: 'وقت الإغلاق',val: fmtD(shiftDetails.closed_at)                                       },
                ].map((c) => (
                  <div key={c.label} className="bg-gray-50 rounded-lg p-3 border">
                    <div className="text-xs text-gray-500">{c.label}</div>
                    <div className="font-semibold">{c.val}</div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-3 gap-4">
                <KPI label="إجمالي المبيعات"  value={`${fmt(shiftDetails.total_sales)} ر.س`}   icon="fas fa-shopping-bag" color="border-green-200 bg-green-50" />
                <KPI label="إجمالي المرتجعات" value={`${fmt(shiftDetails.total_returns)} ر.س`}  icon="fas fa-rotate-left"  color="border-red-200 bg-red-50"    />
                <KPI label="فرق النقدية"       value={`${fmt(shiftDetails.cash_difference)} ر.س`} icon="fas fa-balance-scale" color="border-gray-200 bg-gray-50" />
              </div>

              {Array.isArray(shiftDetails.transactions) && shiftDetails.transactions.length > 0 && (
                <div>
                  <h4 className="font-bold text-gray-700 mb-3 text-sm">حركات الخزنة</h4>
                  <div className="overflow-x-auto rounded-xl border border-gray-200">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-600 text-xs">
                          <th className="text-right py-2 px-3">النوع</th>
                          <th className="text-right py-2 px-3">المبلغ</th>
                          <th className="text-right py-2 px-3">السبب</th>
                          <th className="text-right py-2 px-3">الوقت</th>
                        </tr>
                      </thead>
                      <tbody>
                        {shiftDetails.transactions.map((tx) => (
                          <tr key={tx.id} className="border-b">
                            <td className="py-2 px-3">
                              {tx.transaction_type === 'deposit'    ? 'إيداع'    :
                               tx.transaction_type === 'withdrawal' ? 'سحب'      :
                               tx.transaction_type === 'return'     ? 'مرتجع'    : 'تسوية'}
                            </td>
                            <td className="py-2 px-3 font-bold">{fmt(tx.amount)} ر.س</td>
                            <td className="py-2 px-3 text-gray-600">{tx.reason || '—'}</td>
                            <td className="py-2 px-3 text-xs text-gray-500">{fmtD(tx.created_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
