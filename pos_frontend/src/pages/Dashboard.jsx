import { useState, useEffect, useRef, useCallback } from 'react';
import { salesAPI } from '../services/api';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement,
  Title, Tooltip, Legend, ArcElement,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

// ─── ثوابت ────────────────────────────────────────────────
const REFRESH_INTERVAL = 30; // ثانية

// ─── Sub-components ───────────────────────────────────────
const StatCard = ({ label, value, sub, icon, gradient }) => (
  <div className={`card bg-gradient-to-br ${gradient} text-white`}>
    <div className="flex items-center justify-between">
      <div>
        <p className="text-white/70 mb-1">{label}</p>
        <h2 className="text-3xl font-bold">{value ?? 0} ر.س</h2>
        {sub && <p className="text-white/70 mt-2 text-sm">{sub}</p>}
      </div>
      <div className="text-5xl opacity-20">
        <i className={`fas ${icon}`}></i>
      </div>
    </div>
  </div>
);

const EmptyState = ({ colSpan = 7, message = 'لا توجد بيانات' }) => (
  <tr>
    <td colSpan={colSpan} className="px-4 py-10 text-center text-gray-500">
      <i className="fas fa-inbox text-4xl mb-3 block text-gray-300"></i>
      {message}
    </td>
  </tr>
);

// ─── Dashboard ────────────────────────────────────────────
const Dashboard = () => {
  const [stats,       setStats]       = useState(null);
  const [loading,     setLoading]     = useState(true);   // أول تحميل فقط
  const [refreshing,  setRefreshing]  = useState(false);  // silent refresh
  const [error,       setError]       = useState(null);
  const [lastUpdate,  setLastUpdate]  = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [countdown,   setCountdown]   = useState(REFRESH_INTERVAL);

  // useRef يضمن أن الـ interval يقرأ أحدث قيمة دائمًا (يحل مشكلة stale closure)
  const autoRefreshRef  = useRef(autoRefresh);
  const lastFetchRef    = useRef(0);

  useEffect(() => { autoRefreshRef.current = autoRefresh; }, [autoRefresh]);

  // ─── fetchStats ──────────────────────────────────────
  const fetchStats = useCallback(async (silent = false) => {
    try {
      if (silent) setRefreshing(true);
      else        setLoading(true);
      setError(null);

      const res = await salesAPI.getStats();
      setStats(res.data);
      setLastUpdate(new Date());
      lastFetchRef.current = Date.now();
      setCountdown(REFRESH_INTERVAL);       // أعد العدّاد بعد كل refresh
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      if (!silent) setError('تعذّر تحميل البيانات. تحقق من الاتصال وأعد المحاولة.');
      // في حالة الـ silent refresh نتجاهل الخطأ بهدوء
    } finally {
      if (silent) setRefreshing(false);
      else        setLoading(false);
    }
  }, []);

  // ─── أول تحميل ───────────────────────────────────────
  useEffect(() => { fetchStats(false); }, [fetchStats]);

  // ─── Auto-refresh interval + Countdown ───────────────
  useEffect(() => {
    if (!autoRefresh) {
      setCountdown(REFRESH_INTERVAL);
      return;
    }

    // عدّاد تنازلي — يتحدث كل ثانية
    const tick = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          if (autoRefreshRef.current) fetchStats(true); // silent refresh
          return REFRESH_INTERVAL;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(tick);
  }, [autoRefresh, fetchStats]);

  // ─── Visibility Change (silent + throttle 2 ثانية) ───
  useEffect(() => {
    const handle = () => {
      if (
        document.visibilityState === 'visible' &&
        Date.now() - lastFetchRef.current > 2000
      ) {
        fetchStats(true);
      }
    };
    document.addEventListener('visibilitychange', handle);
    return () => document.removeEventListener('visibilitychange', handle);
  }, [fetchStats]);

  // ─── Chart data ───────────────────────────────────────
  const topProductsChart = {
    labels: stats?.top_products?.map((p) => p.product__name) || [],
    datasets: [{
      label: 'المبيعات (ر.س)',
      data: stats?.top_products?.map((p) => p.total_sales) || [],
      backgroundColor: [
        'rgba(59,130,246,.85)',
        'rgba(16,185,129,.85)',
        'rgba(251,146,60,.85)',
        'rgba(239,68,68,.85)',
        'rgba(168,85,247,.85)',
      ],
      borderRadius: 8,
    }],
  };

  // ─── Loading Screen ───────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-center">
          <i className="fas fa-spinner fa-spin text-6xl text-blue-600"></i>
          <p className="mt-4 text-gray-500 text-lg">جاري تحميل البيانات...</p>
        </div>
      </div>
    );
  }

  // ─── Error Screen ─────────────────────────────────────
  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-center bg-white p-8 rounded-2xl shadow-lg max-w-md">
          <i className="fas fa-exclamation-circle text-6xl text-red-500 mb-4"></i>
          <p className="text-gray-700 font-semibold mb-6">{error}</p>
          <button
            onClick={() => fetchStats(false)}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition"
          >
            <i className="fas fa-redo ml-2"></i>إعادة المحاولة
          </button>
        </div>
      </div>
    );
  }

  // ─── Main Render ──────────────────────────────────────
  return (
    <div className="p-6 bg-gray-100 min-h-screen">

      {/* Header */}
      <div className="flex justify-between items-center mb-6 flex-wrap gap-3">
        <h1 className="text-3xl font-bold text-gray-800">
          <i className="fas fa-chart-line ml-2"></i>لوحة التحكم
        </h1>

        <div className="flex items-center gap-3 flex-wrap">
          {/* آخر تحديث */}
          {lastUpdate && (
            <span className="text-sm text-gray-500">
              <i className="fas fa-clock ml-1"></i>
              آخر تحديث: {lastUpdate.toLocaleTimeString('ar-SA')}
            </span>
          )}

          {/* Silent refresh indicator */}
          {refreshing && (
            <span className="text-sm text-blue-500 flex items-center gap-1">
              <i className="fas fa-circle-notch fa-spin"></i> يتحدث...
            </span>
          )}

          {/* Countdown Badge */}
          {autoRefresh && !refreshing && (
            <span className="text-xs bg-blue-50 text-blue-600 border border-blue-200 rounded-full px-3 py-1 font-bold">
              <i className="fas fa-stopwatch ml-1"></i>
              تحديث خلال {countdown}ث
            </span>
          )}

          {/* Manual refresh */}
          <button
            onClick={() => fetchStats(false)}
            disabled={loading || refreshing}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-50 transition"
          >
            <i className={`fas fa-sync-alt ml-2 ${loading ? 'fa-spin' : ''}`}></i>تحديث
          </button>

          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh((v) => !v)}
            className={`px-4 py-2 rounded-xl font-semibold transition ${
              autoRefresh
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <i className={`fas ${autoRefresh ? 'fa-pause' : 'fa-play'} ml-2`}></i>
            {autoRefresh ? 'تلقائي' : 'يدوي'}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <StatCard label="مبيعات اليوم"  value={stats?.today_sales}  icon="fa-calendar-day"  gradient="from-blue-500 to-blue-600"
          sub={<><i className="fas fa-shopping-bag ml-1"></i>{stats?.today_count ?? 0} عملية</>}
        />
        <StatCard label="مبيعات الأسبوع" value={stats?.week_sales}  icon="fa-calendar-week" gradient="from-green-500 to-green-600" />
        <StatCard label="مبيعات الشهر"   value={stats?.month_sales} icon="fa-calendar-alt"  gradient="from-purple-500 to-purple-600" />
        <StatCard label="إجمالي الأرباح" value={stats?.total_profit} icon="fa-chart-line"   gradient="from-orange-500 to-orange-600" />
      </div>

      {/* Charts + List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="card p-5">
          <h3 className="text-xl font-bold mb-4 text-gray-800">
            <i className="fas fa-trophy ml-2 text-yellow-500"></i>أكثر المنتجات مبيعًا
          </h3>
          {stats?.top_products?.length > 0 ? (
            <Bar data={topProductsChart} options={{ responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }} />
          ) : (
            <p className="text-gray-400 text-center py-10">لا توجد بيانات</p>
          )}
        </div>

        <div className="card p-5">
          <h3 className="text-xl font-bold mb-4 text-gray-800">
            <i className="fas fa-list-ol ml-2"></i>تفاصيل الأكثر مبيعًا
          </h3>
          <div className="space-y-3">
            {stats?.top_products?.length > 0 ? stats.top_products.map((p, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">{i + 1}</div>
                  <div>
                    <p className="font-semibold text-gray-800">{p.product__name}</p>
                    <p className="text-xs text-gray-500">الكمية: {p.total_quantity}</p>
                  </div>
                </div>
                <span className="font-bold text-blue-600">{p.total_sales} ر.س</span>
              </div>
            )) : <p className="text-gray-400 text-center py-10">لا توجد بيانات</p>}
          </div>
        </div>
      </div>

      {/* Recent Sales */}
      <div className="card p-5">
        <h3 className="text-xl font-bold mb-4 text-gray-800">
          <i className="fas fa-clock ml-2"></i>آخر العمليات
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50">
                {['رقم العملية','العميل','البائع','المبلغ','طريقة الدفع','الحالة','التاريخ'].map((h) => (
                  <th key={h} className="px-4 py-3 text-right text-sm font-semibold text-gray-700">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {stats?.recent_sales?.length > 0 ? stats.recent_sales.map((sale) => (
                <tr key={sale.id} className="border-b hover:bg-gray-50 transition">
                  <td className="px-4 py-3 text-sm font-mono">#{sale.id.substring(0,8)}</td>
                  <td className="px-4 py-3 text-sm">{sale.customer_name || 'زائر'}</td>
                  <td className="px-4 py-3 text-sm">
                    <i className="fas fa-user-circle text-blue-500 ml-1"></i>{sale.user_name || 'غير محدد'}
                  </td>
                  <td className="px-4 py-3 text-sm font-semibold text-blue-600">{sale.total} ر.س</td>
                  <td className="px-4 py-3 text-sm">
                    {{ cash: 'نقدي', card: 'بطاقة', both: 'نقدي + بطاقة' }[sale.payment_method] || sale.payment_method}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      sale.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {sale.status === 'completed' ? 'مكتملة' : 'ملغاة'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(sale.created_at).toLocaleDateString('ar-SA')}
                  </td>
                </tr>
              )) : <EmptyState message="لا توجد عمليات بيع بعد" />}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
