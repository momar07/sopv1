import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { salesAPI, returnsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const STATUS_LABEL = {
  pending:   { text: 'قيد الانتظار', cls: 'bg-yellow-100 text-yellow-800' },
  approved:  { text: 'موافق عليه',   cls: 'bg-blue-100 text-blue-800'   },
  completed: { text: 'مكتمل',        cls: 'bg-green-100 text-green-800'  },
  rejected:  { text: 'مرفوض',        cls: 'bg-red-100 text-red-800'      },
};

const ReturnBadge = ({ s }) => {
  const cfg = STATUS_LABEL[s] || { text: s, cls: 'bg-gray-100 text-gray-700' };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${cfg.cls}`}>
      {cfg.text}
    </span>
  );
};

const OperationDetails = () => {
  const { id } = useParams();
  const { isAdmin, isManager, hasAction } = useAuth();

  const isAdminVal   = typeof isAdmin   === 'function' ? isAdmin()   : !!isAdmin;
  const isManagerVal = typeof isManager === 'function' ? isManager() : !!isManager;

  const canCancel = isAdminVal || isManagerVal;

  // ✅ إصلاح: زرار المرتجع يظهر فقط لمن عنده صلاحية
  const canRefund = isAdminVal || isManagerVal ||
    hasAction?.('operations.details', 'sales.refund');

  // ✅ إصلاح: الموافقة والإكمال والرفض للمدير والأدمن فقط
  const canManageReturn = isAdminVal || isManagerVal;

  const [sale, setSale]                   = useState(null);
  const [returns, setReturns]             = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState('');
  const [showReturnModal, setShowReturnModal] = useState(false);
  const [returnableItems, setReturnableItems] = useState([]);
  const [returnQty, setReturnQty]         = useState({});
  const [returnReason, setReturnReason]   = useState('');
  const [returnSubmitting, setReturnSubmitting] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [toast, setToast]                 = useState(null);

  const notify = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const fetchDetails = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await salesAPI.getOne(id);
      setSale(res.data);
      const r = await salesAPI.getReturns(id);
      setReturns(r.data || []);
    } catch (e) {
      console.error(e);
      setError('تعذر تحميل تفاصيل العملية');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDetails(); }, [id]);

  const handleCancel = async () => {
    if (!sale?.id) return;
    if (!window.confirm('هل أنت متأكد من إلغاء العملية؟')) return;
    try {
      await salesAPI.cancel(sale.id);
      await fetchDetails();
      notify('تم إلغاء العملية');
    } catch (e) {
      console.error(e);
      notify('تعذر إلغاء العملية', 'error');
    }
  };

  const openReturnModal = async () => {
    if (!sale?.id) return;
    try {
      const res = await salesAPI.getReturnableItems(sale.id);
      const items = res.data || [];
      setReturnableItems(items);
      const init = {};
      items.forEach((it) => (init[it.sale_item_id] = 0));
      setReturnQty(init);
      setReturnReason('');
      setShowReturnModal(true);
    } catch (e) {
      console.error(e);
      notify('تعذر تحميل الأصناف القابلة للإرجاع', 'error');
    }
  };

  const submitReturn = async () => {
    if (!sale?.id) return;
    const items = returnableItems
      .map((it) => ({
        sale_item_id:      it.sale_item_id,
        quantity:          Number(returnQty[it.sale_item_id] || 0),
        remaining_quantity: Number(it.remaining_quantity || 0),
      }))
      .filter((x) => x.quantity > 0);

    if (!items.length) { notify('اختر كمية مرتجعة واحدة على الأقل', 'error'); return; }

    for (const it of items) {
      if (it.quantity > it.remaining_quantity) {
        notify('كمية المرتجع لا يمكن أن تتجاوز الكمية المتبقية', 'error');
        return;
      }
    }

    setReturnSubmitting(true);
    try {
      // ✅ إصلاح: لا نرسل status — الـ backend يحدده دايماً بـ pending
      await returnsAPI.create({
        sale_id: sale.id,
        reason:  returnReason || '',
        items:   items.map(({ sale_item_id, quantity }) => ({ sale_item_id, quantity })),
      });
      setShowReturnModal(false);
      await fetchDetails();
      notify('تم إنشاء طلب المرتجع — في انتظار موافقة المدير');
    } catch (e) {
      console.error(e);
      const msg = e?.response?.data?.[0] || JSON.stringify(e?.response?.data) || 'خطأ غير معروف';
      notify('تعذر إنشاء المرتجع: ' + msg, 'error');
    } finally {
      setReturnSubmitting(false);
    }
  };

  const handleReturnAction = async (returnId, action) => {
    setActionLoading(returnId + action);
    try {
      await returnsAPI[action](returnId);
      await fetchDetails();
      const labels = { approve: 'تمت الموافقة', complete: 'تم إكمال المرتجع وإرجاع المخزون', reject: 'تم الرفض' };
      notify(labels[action] || 'تم');
    } catch (e) {
      const msg = e?.response?.data?.error || 'خطأ في العملية';
      notify(msg, 'error');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) return <div className="p-6 text-gray-700">جاري التحميل...</div>;

  if (error) return (
    <div className="p-6">
      <div className="p-4 rounded-lg bg-red-50 text-red-700 border border-red-200">{error}</div>
      <div className="mt-4">
        <Link to="/operations" className="text-blue-700 hover:text-blue-900 font-semibold">العودة للعمليات</Link>
      </div>
    </div>
  );

  if (!sale) return (
    <div className="p-6">
      <div className="text-gray-700">لا توجد بيانات.</div>
      <div className="mt-4">
        <Link to="/operations" className="text-blue-700 hover:text-blue-900 font-semibold">العودة للعمليات</Link>
      </div>
    </div>
  );

  return (
    <div className="p-6" dir="rtl">

      {/* Toast */}
      {toast && (
        <div className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-2xl shadow-xl font-bold text-sm
          ${toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">تفاصيل العملية</h1>
          <div className="text-sm text-gray-600 font-mono">#{String(sale.id).slice(0, 8)}</div>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <Link to="/operations"
            className="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold">
            رجوع
          </Link>
          {/* ✅ إصلاح: زرار المرتجع يظهر فقط لمن عنده صلاحية */}
          {canRefund && sale.status === 'completed' && (
            <button type="button" onClick={openReturnModal}
              className="px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white font-semibold">
              ↩ إنشاء مرتجع
            </button>
          )}
          {canCancel && sale.status !== 'cancelled' && (
            <button type="button" onClick={handleCancel}
              className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold">
              إلغاء العملية
            </button>
          )}
        </div>
      </div>

      {/* بيانات الفاتورة */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 mb-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-gray-500">العميل</div>
            <div className="text-gray-800 font-bold">{sale.customer_name || 'زائر'}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">التاريخ</div>
            <div className="text-gray-800 font-bold">{new Date(sale.created_at).toLocaleString('ar-SA')}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">طريقة الدفع</div>
            <div className="text-gray-800 font-bold">{sale.payment_method}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">الحالة</div>
            <span className={`px-2 py-1 rounded-full text-xs font-bold ${
              sale.status === 'cancelled' ? 'bg-red-100 text-red-700' :
              sale.status === 'pending'   ? 'bg-yellow-100 text-yellow-800' :
              'bg-green-100 text-green-800'}`}>
              {sale.status === 'cancelled' ? 'ملغاة' :
               sale.status === 'pending'   ? 'قيد الانتظار' : 'مكتملة'}
            </span>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'المجموع الفرعي', val: sale.subtotal, cls: 'bg-gray-50' },
            { label: 'الخصم',          val: sale.discount,  cls: 'bg-gray-50' },
            { label: 'الضريبة',        val: sale.tax,        cls: 'bg-gray-50' },
            { label: 'الإجمالي',       val: sale.total,      cls: 'bg-green-50 border-green-200' },
          ].map((c) => (
            <div key={c.label} className={`p-3 rounded-lg border ${c.cls}`}>
              <div className="text-xs text-gray-500">{c.label}</div>
              <div className="font-bold text-gray-800">{c.val} ر.س</div>
            </div>
          ))}
        </div>

        {/* الأصناف */}
        <div className="mt-6">
          <h2 className="font-bold text-gray-800 mb-2">الأصناف</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-600 border-b">
                  <th className="text-right py-2">المنتج</th>
                  <th className="text-right py-2">الكمية</th>
                  <th className="text-right py-2">السعر</th>
                  <th className="text-right py-2">الإجمالي</th>
                </tr>
              </thead>
              <tbody>
                {sale.items?.map((it, idx) => (
                  <tr key={idx} className="border-b last:border-b-0">
                    <td className="py-2 font-semibold">{it.product_name}</td>
                    <td className="py-2 font-mono">{it.quantity}</td>
                    <td className="py-2 font-mono">{it.price}</td>
                    <td className="py-2 font-bold font-mono">{it.subtotal}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* المرتجعات */}
      {returns.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <h2 className="font-bold text-orange-700 mb-3">↩ المرتجعات ({returns.length})</h2>
          <div className="space-y-3">
            {returns.map((r) => (
              <div key={r.id} className="p-4 rounded-xl bg-orange-50 border border-orange-200">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm font-bold text-orange-800">
                      #{String(r.id).slice(0, 8)}
                    </span>
                    <ReturnBadge s={r.status} />
                  </div>
                  <div className="font-bold text-orange-800">{r.total_amount} ر.س</div>
                </div>
                <div className="text-xs text-orange-600 mt-1">
                  {new Date(r.created_at).toLocaleString('ar-SA')}
                </div>

                {/* ✅ أزرار إدارة المرتجع — للمدير والأدمن فقط */}
                {canManageReturn && (
                  <div className="flex gap-2 mt-3 flex-wrap">
                    {r.status === 'pending' && (
                      <>
                        <button
                          onClick={() => handleReturnAction(r.id, 'approve')}
                          disabled={actionLoading === r.id + 'approve'}
                          className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold">
                          {actionLoading === r.id + 'approve' ? '...' : '✅ موافقة'}
                        </button>
                        <button
                          onClick={() => handleReturnAction(r.id, 'reject')}
                          disabled={actionLoading === r.id + 'reject'}
                          className="px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-700 text-xs font-bold">
                          {actionLoading === r.id + 'reject' ? '...' : '❌ رفض'}
                        </button>
                      </>
                    )}
                    {r.status === 'approved' && (
                      <button
                        onClick={() => handleReturnAction(r.id, 'complete')}
                        disabled={actionLoading === r.id + 'complete'}
                        className="px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-bold">
                        {actionLoading === r.id + 'complete' ? '...' : '📦 إكمال وإرجاع المخزون'}
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal المرتجع */}
      {showReturnModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl">
            <div className="flex items-center justify-between px-5 py-4 border-b">
              <h3 className="font-bold text-lg">↩ إنشاء طلب مرتجع</h3>
              <button onClick={() => setShowReturnModal(false)} className="text-gray-400 hover:text-gray-700 font-black text-xl">×</button>
            </div>
            <div className="p-5">
              <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3 mb-4 text-sm text-yellow-800 font-semibold">
                ⚠️ سيتم إنشاء طلب المرتجع بحالة "قيد الانتظار" — يحتاج موافقة المدير لإرجاع المخزون
              </div>

              <div className="space-y-2 max-h-64 overflow-auto border rounded-xl p-3 mb-4">
                {returnableItems.map((it) => (
                  <div key={it.sale_item_id}
                    className="flex items-center justify-between gap-3 border-b last:border-b-0 py-2">
                    <div>
                      <div className="font-semibold text-sm">{it.product_name}</div>
                      <div className="text-xs text-gray-500">
                        المتبقي للإرجاع: <span className="font-mono font-bold">{it.remaining_quantity}</span>
                      </div>
                    </div>
                    <input
                      type="number" min="0" max={it.remaining_quantity}
                      value={returnQty[it.sale_item_id] ?? 0}
                      onChange={(e) => setReturnQty((p) => ({ ...p, [it.sale_item_id]: e.target.value }))}
                      className="w-24 border rounded-lg px-2 py-1 text-sm font-mono text-center"
                    />
                  </div>
                ))}
                {!returnableItems.length && (
                  <div className="text-sm text-gray-500 text-center py-4">لا توجد أصناف قابلة للإرجاع</div>
                )}
              </div>

              <div className="mb-4">
                <label className="block text-sm font-semibold mb-1">السبب (اختياري)</label>
                <input value={returnReason} onChange={(e) => setReturnReason(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  placeholder="مثال: العميل رجّع الصنف" />
              </div>

              <div className="flex gap-3 justify-end">
                <button onClick={() => setShowReturnModal(false)}
                  className="px-4 py-2 rounded-xl border font-bold text-sm">إغلاق</button>
                <button onClick={submitReturn} disabled={returnSubmitting}
                  className="px-5 py-2 rounded-xl bg-orange-500 hover:bg-orange-600 text-white font-bold text-sm">
                  {returnSubmitting ? 'جاري الحفظ...' : '↩ إرسال طلب المرتجع'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OperationDetails;
