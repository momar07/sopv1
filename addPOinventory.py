#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_inventory_page.py
─────────────────────
يكتب ملف InventoryPage.jsx بالكامل بالنسخة الصحيحة
التي تتضمن زر طلب شراء + QuickOrderModal

الاستخدام:
  python fix_inventory_page.py
"""

import os, sys

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "pos_frontend", "src", "pages", "InventoryPage.jsx")

if not os.path.exists(os.path.dirname(FILE_PATH)):
    print(f"❌  المسار غير موجود: {os.path.dirname(FILE_PATH)}")
    sys.exit(1)

# نسخة احتياطية
if os.path.exists(FILE_PATH):
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        old = f.read()
    bak = FILE_PATH + ".bak"
    with open(bak, "w", encoding="utf-8") as f:
        f.write(old)
    print(f"✅  نسخة احتياطية: {bak}")

# ══════════════════════════════════════════════════════════════════════════════
CONTENT = r"""import React, { useCallback, useEffect, useState } from 'react';
import { inventoryAPI, productsAPI } from '../services/api';

const fmt = (n) => Number(n || 0).toFixed(2);

const Badge = ({ label, color }) => {
  const map = {
    green:  'bg-green-100 text-green-800',
    red:    'bg-red-100 text-red-800',
    yellow: 'bg-yellow-100 text-yellow-800',
    blue:   'bg-blue-100 text-blue-800',
    gray:   'bg-gray-100 text-gray-600',
  };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${map[color]||map.gray}`}>{label}</span>;
};

const statusColor = (s) => ({ draft:'gray', ordered:'blue', received:'green', cancelled:'red' }[s]||'gray');
const alertColor  = (t) => ({ out:'red', low:'yellow', expiry:'yellow' }[t]||'gray');

const Spinner = () => (
  <div className="flex items-center justify-center h-40">
    <i className="fas fa-spinner fa-spin text-4xl text-blue-500"></i>
  </div>
);

const Toast = ({ msg, type }) => (
  <div className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-2xl shadow-xl font-bold text-sm
    ${type==='error'?'bg-red-600 text-white':'bg-green-600 text-white'}`}>{msg}</div>
);

const Modal = ({ title, onClose, children }) => (
  <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      onClick={(e)=>e.stopPropagation()}>
      <div className="flex justify-between items-center px-5 py-4 border-b">
        <h3 className="font-black text-gray-800">{title}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-700 font-black text-xl">x</button>
      </div>
      <div className="p-5">{children}</div>
    </div>
  </div>
);

const Field = ({ label, children }) => (
  <div>
    <label className="block text-xs font-bold text-gray-500 mb-1">{label}</label>
    {children}
  </div>
);

const INP = 'w-full border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 bg-white transition';

// ═══════════════════════════════════════════════════════════════════════════
export default function InventoryPage() {
  const [tab, setTab] = useState('summary');
  const tabs = [
    { key:'summary',   label:'📊 ملخص المخزون' },
    { key:'orders',    label:'📦 أوامر الشراء'  },
    { key:'adjust',    label:'⚖️ تسوية المخزون' },
    { key:'alerts',    label:'🔔 التنبيهات'     },
    { key:'suppliers', label:'🏭 الموردون'       },
  ];
  return (
    <div dir="rtl" className="p-4 min-h-screen bg-gray-50">
      <div className="mb-5">
        <h1 className="text-2xl font-black text-gray-800">🏪 إدارة المخزون</h1>
        <p className="text-gray-500 text-sm mt-1">استلام البضاعة · تسوية المخزون · تنبيهات النقص</p>
      </div>
      <div className="flex gap-2 flex-wrap mb-5">
        {tabs.map((t) => (
          <button key={t.key} onClick={()=>setTab(t.key)}
            className={`px-4 py-2 rounded-xl font-bold text-sm transition-all ${
              tab===t.key ? 'bg-blue-600 text-white shadow' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}>{t.label}</button>
        ))}
      </div>
      {tab==='summary'   && <SummaryPanel />}
      {tab==='orders'    && <PurchaseOrdersPanel />}
      {tab==='adjust'    && <AdjustPanel />}
      {tab==='alerts'    && <AlertsPanel />}
      {tab==='suppliers' && <SuppliersPanel />}
    </div>
  );
}

// ─── Summary ─────────────────────────────────────────────────────────────────
function SummaryPanel() {
  const [summary, setSummary]         = useState(null);
  const [lowProducts, setLow]         = useState([]);
  const [loading, setLoading]         = useState(true);
  const [quickOrderProduct, setQuick] = useState(null);
  const [suppliers, setSuppliers]     = useState([]);
  const [toast, setToast]             = useState(null);
  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, lp, sup] = await Promise.all([
        inventoryAPI.getAlertsSummary({ threshold:10 }),
        productsAPI.getLowStock(),
        inventoryAPI.getSuppliers(),
      ]);
      setSummary(s.data);
      setLow(lp.data?.results || lp.data || []);
      setSuppliers(sup.data?.results || sup.data || []);
    } catch { /**/ } finally { setLoading(false); }
  }, []);

  useEffect(()=>{ load(); }, [load]);

  const handleGenerate = async () => {
    await inventoryAPI.checkAndGenerateAlerts({ threshold:10 });
    load();
  };

  if (loading) return <Spinner />;

  const cards = [
    { label:'إجمالي المنتجات',    value: summary?.total_products   ||0, color:'blue',   icon:'📦' },
    { label:'مخزون منخفض',        value: summary?.low_stock        ||0, color:'yellow', icon:'⚠️' },
    { label:'نفاد المخزون',        value: summary?.out_of_stock     ||0, color:'red',    icon:'🚨' },
    { label:'مخزون كافي',          value: summary?.healthy_stock    ||0, color:'green',  icon:'✅' },
    { label:'تنبيهات غير محلولة', value: summary?.unresolved_alerts||0, color:'red',    icon:'🔔' },
  ];
  const cm = {
    blue:   'bg-blue-50 border-blue-200 text-blue-700',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
    red:    'bg-red-50 border-red-200 text-red-700',
    green:  'bg-green-50 border-green-200 text-green-700',
  };

  return (
    <div className="space-y-6">
      {toast && <Toast msg={toast.msg} type={toast.type} />}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {cards.map((c) => (
          <div key={c.label} className={`rounded-2xl border p-4 ${cm[c.color]}`}>
            <div className="text-2xl mb-1">{c.icon}</div>
            <div className="text-3xl font-black">{c.value}</div>
            <div className="text-sm font-semibold mt-1">{c.label}</div>
          </div>
        ))}
      </div>

      <button onClick={handleGenerate}
        className="bg-yellow-500 hover:bg-yellow-600 text-white font-bold px-5 py-2 rounded-xl text-sm transition">
        🔄 فحص وتحديث التنبيهات
      </button>

      {lowProducts.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b bg-yellow-50">
            <h2 className="font-black text-yellow-800">⚠️ منتجات تحتاج إعادة طلب ({lowProducts.length})</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-gray-500 text-right">
                <th className="px-4 py-3 font-bold">المنتج</th>
                <th className="px-4 py-3 font-bold">الباركود</th>
                <th className="px-4 py-3 font-bold">المخزون</th>
                <th className="px-4 py-3 font-bold">سعر البيع</th>
                <th className="px-4 py-3 font-bold">إجراء</th>
              </tr>
            </thead>
            <tbody>
              {lowProducts.map((p) => (
                <tr key={p.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3 font-bold">{p.name}</td>
                  <td className="px-4 py-3 text-gray-500">{p.barcode||'—'}</td>
                  <td className="px-4 py-3">
                    <span className={`font-black ${p.stock===0?'text-red-600':'text-yellow-600'}`}>{p.stock}</span>
                  </td>
                  <td className="px-4 py-3">{fmt(p.price)} ج</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setQuick(p)}
                      className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition">
                      📦 طلب شراء
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {quickOrderProduct && (
        <QuickOrderModal
          product={quickOrderProduct}
          suppliers={suppliers}
          onClose={() => setQuick(null)}
          onSaved={() => { setQuick(null); notify('✅ تم إنشاء طلب الشراء بنجاح'); }}
          onError={(msg) => notify('❌ ' + msg, 'error')}
        />
      )}
    </div>
  );
}

// ─── Purchase Orders ──────────────────────────────────────────────────────────
function PurchaseOrdersPanel() {
  const [orders, setOrders]       = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts]   = useState([]);
  const [loading, setLoading]     = useState(true);
  const [showForm, setShowForm]   = useState(false);
  const [selected, setSelected]   = useState(null);
  const [toast, setToast]         = useState(null);
  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [o,s,p] = await Promise.all([
        inventoryAPI.getPurchaseOrders(),
        inventoryAPI.getSuppliers(),
        productsAPI.getAll({ page_size:200 }),
      ]);
      setOrders(o.data?.results||o.data||[]);
      setSuppliers(s.data?.results||s.data||[]);
      setProducts(p.data?.results||p.data||[]);
    } catch {/**/ } finally { setLoading(false); }
  }, []);

  useEffect(()=>{ load(); }, [load]);

  const handleReceive = async (order, receivedQtys) => {
    try {
      await inventoryAPI.receivePurchaseOrder(order.id, { received_quantities: receivedQtys });
      notify('✅ تم استلام البضاعة وتحديث المخزون');
      setSelected(null); load();
    } catch(e) { notify('❌ '+(e?.response?.data?.error||'خطأ في الاستلام'),'error'); }
  };

  const handleCancel = async (id) => {
    if (!window.confirm('هل أنت متأكد من إلغاء الأمر؟')) return;
    try { await inventoryAPI.cancelPurchaseOrder(id); notify('تم الإلغاء'); load(); }
    catch(e) { notify('❌ '+(e?.response?.data?.error||'خطأ'),'error'); }
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      {toast && <Toast msg={toast.msg} type={toast.type} />}
      <div className="flex justify-between items-center">
        <h2 className="font-black text-gray-700 text-lg">أوامر الشراء</h2>
        <button onClick={()=>setShowForm(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-4 py-2 rounded-xl text-sm">
          ➕ أمر شراء جديد
        </button>
      </div>
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="bg-gray-50 text-gray-500 text-right">
            <th className="px-4 py-3 font-bold">رقم المرجع</th>
            <th className="px-4 py-3 font-bold">المورد</th>
            <th className="px-4 py-3 font-bold">الحالة</th>
            <th className="px-4 py-3 font-bold">الإجمالي</th>
            <th className="px-4 py-3 font-bold">التاريخ</th>
            <th className="px-4 py-3 font-bold">إجراءات</th>
          </tr></thead>
          <tbody>
            {orders.length===0 && <tr><td colSpan={6} className="text-center py-8 text-gray-400">لا توجد أوامر شراء</td></tr>}
            {orders.map((o)=>(
              <tr key={o.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 font-bold text-blue-700">{o.reference_number}</td>
                <td className="px-4 py-3">{o.supplier_name||'—'}</td>
                <td className="px-4 py-3"><Badge label={o.status} color={statusColor(o.status)} /></td>
                <td className="px-4 py-3 font-bold">{fmt(o.total_cost)} ج</td>
                <td className="px-4 py-3 text-gray-500">{o.created_at?.split('T')[0]}</td>
                <td className="px-4 py-3 flex gap-2">
                  {(o.status==='ordered'||o.status==='draft') && (
                    <button onClick={()=>setSelected(o)}
                      className="bg-green-500 hover:bg-green-600 text-white text-xs font-bold px-3 py-1 rounded-lg">
                      📥 استلام
                    </button>
                  )}
                  {o.status!=='received'&&o.status!=='cancelled' && (
                    <button onClick={()=>handleCancel(o.id)}
                      className="bg-red-100 hover:bg-red-200 text-red-700 text-xs font-bold px-3 py-1 rounded-lg">
                      ❌ إلغاء
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showForm && (
        <NewOrderModal suppliers={suppliers} products={products}
          onClose={()=>setShowForm(false)}
          onSaved={()=>{ setShowForm(false); load(); notify('✅ تم إنشاء أمر الشراء'); }}
          onError={(msg)=>notify('❌ '+msg,'error')} />
      )}
      {selected && (
        <ReceiveModal order={selected} onClose={()=>setSelected(null)} onReceive={handleReceive} />
      )}
    </div>
  );
}

function NewOrderModal({ suppliers, products, onClose, onSaved, onError }) {
  const [form, setForm] = useState({
    reference_number: `PO-${Date.now()}`,
    supplier: '', expected_date: '', notes: '', status: 'ordered',
  });
  const [items, setItems] = useState([{ product:'', quantity:1, unit_cost:'' }]);
  const [saving, setSaving] = useState(false);

  const addItem    = () => setItems([...items,{ product:'', quantity:1, unit_cost:'' }]);
  const removeItem = (i) => setItems(items.filter((_,idx)=>idx!==i));
  const updateItem = (i,field,val) => { const n=[...items]; n[i]={...n[i],[field]:val}; setItems(n); };

  const handleSave = async () => {
    if (!form.reference_number) return onError('رقم المرجع مطلوب');
    const valid = items.filter(it=>it.product&&it.quantity>0&&it.unit_cost);
    if (!valid.length) return onError('أضف منتجاً واحداً على الأقل');
    setSaving(true);
    try {
      await inventoryAPI.createPurchaseOrder({
        ...form, supplier: form.supplier||null,
        items: valid.map(it=>({...it, quantity:Number(it.quantity), unit_cost:Number(it.unit_cost)}))
      });
      onSaved();
    } catch(e) { onError(JSON.stringify(e?.response?.data||'خطأ')); }
    finally { setSaving(false); }
  };

  return (
    <Modal title="➕ أمر شراء جديد" onClose={onClose}>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="رقم المرجع *">
            <input className={INP} value={form.reference_number}
              onChange={e=>setForm({...form,reference_number:e.target.value})} />
          </Field>
          <Field label="المورد">
            <select className={INP} value={form.supplier}
              onChange={e=>setForm({...form,supplier:e.target.value})}>
              <option value="">بدون مورد</option>
              {suppliers.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="تاريخ الاستلام المتوقع">
            <input type="date" className={INP} value={form.expected_date}
              onChange={e=>setForm({...form,expected_date:e.target.value})} />
          </Field>
          <Field label="الحالة">
            <select className={INP} value={form.status}
              onChange={e=>setForm({...form,status:e.target.value})}>
              <option value="draft">مسودة</option>
              <option value="ordered">تم الطلب</option>
            </select>
          </Field>
        </div>
        <Field label="ملاحظات">
          <textarea className={INP} rows={2} value={form.notes}
            onChange={e=>setForm({...form,notes:e.target.value})} />
        </Field>
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="font-bold text-gray-700 text-sm">المنتجات</span>
            <button onClick={addItem} className="text-blue-600 text-sm font-bold hover:underline">+ إضافة منتج</button>
          </div>
          {items.map((item,i)=>(
            <div key={i} className="flex gap-2 mb-2 items-end">
              <div className="flex-1">
                <select className={INP+' text-xs'} value={item.product}
                  onChange={e=>updateItem(i,'product',e.target.value)}>
                  <option value="">اختر منتج</option>
                  {products.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div className="w-20">
                <input type="number" className={INP+' text-xs text-center'} placeholder="الكمية"
                  min={1} value={item.quantity}
                  onChange={e=>updateItem(i,'quantity',e.target.value)} />
              </div>
              <div className="w-24">
                <input type="number" className={INP+' text-xs text-center'} placeholder="التكلفة"
                  min={0} step="0.01" value={item.unit_cost}
                  onChange={e=>updateItem(i,'unit_cost',e.target.value)} />
              </div>
              <button onClick={()=>removeItem(i)}
                className="text-red-500 font-black text-xl leading-none mb-1">x</button>
            </div>
          ))}
        </div>
        <div className="flex gap-3 justify-end pt-2">
          <button onClick={onClose} className="px-4 py-2 rounded-xl border font-bold text-sm">إلغاء</button>
          <button onClick={handleSave} disabled={saving}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2 rounded-xl text-sm">
            {saving?'...':'💾 حفظ'}
          </button>
        </div>
      </div>
    </Modal>
  );
}

function ReceiveModal({ order, onClose, onReceive }) {
  const [qtys, setQtys]     = useState({});
  const [receiving, setRec] = useState(false);
  useEffect(()=>{
    const init={};
    (order.items||[]).forEach(it=>{ init[it.id]=it.remaining_quantity??it.quantity; });
    setQtys(init);
  }, [order]);
  const handleSubmit = async () => { setRec(true); await onReceive(order,qtys); setRec(false); };
  return (
    <Modal title={`📥 استلام أمر #${order.reference_number}`} onClose={onClose}>
      <table className="w-full text-sm mb-4">
        <thead><tr className="bg-gray-50 text-gray-500 text-right">
          <th className="px-3 py-2 font-bold">المنتج</th>
          <th className="px-3 py-2 font-bold">مطلوب</th>
          <th className="px-3 py-2 font-bold">مستلم فعلياً</th>
        </tr></thead>
        <tbody>
          {(order.items||[]).map(it=>(
            <tr key={it.id} className="border-t">
              <td className="px-3 py-2">{it.product_name}</td>
              <td className="px-3 py-2 font-bold">{it.quantity}</td>
              <td className="px-3 py-2">
                <input type="number" min={0} max={it.quantity}
                  value={qtys[it.id]??it.quantity}
                  onChange={e=>setQtys({...qtys,[it.id]:Number(e.target.value)})}
                  className={INP+' w-20 text-center'} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex gap-3 justify-end">
        <button onClick={onClose} className="px-4 py-2 rounded-xl border font-bold text-sm">إلغاء</button>
        <button onClick={handleSubmit} disabled={receiving}
          className="bg-green-600 hover:bg-green-700 text-white font-bold px-5 py-2 rounded-xl text-sm">
          {receiving?'...':'📥 تأكيد الاستلام'}
        </button>
      </div>
    </Modal>
  );
}

// ─── Stock Adjustment ─────────────────────────────────────────────────────────
function AdjustPanel() {
  const [adjustments, setAdj]   = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [form, setForm]         = useState({ product:'', quantity_change:'', reason:'count', notes:'' });
  const [saving, setSaving]     = useState(false);
  const [toast, setToast]       = useState(null);
  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a,p] = await Promise.all([
        inventoryAPI.getAdjustments(),
        productsAPI.getAll({ page_size:200 }),
      ]);
      setAdj(a.data?.results||a.data||[]);
      setProducts(p.data?.results||p.data||[]);
    } catch {/**/ } finally { setLoading(false); }
  }, []);

  useEffect(()=>{ load(); }, [load]);

  const handleSave = async () => {
    if (!form.product||!form.quantity_change) return notify('❌ اختر المنتج وأدخل الكمية','error');
    setSaving(true);
    try {
      await inventoryAPI.createAdjustment({
        product: form.product,
        quantity_change: Number(form.quantity_change),
        reason: form.reason,
        notes: form.notes,
      });
      notify('✅ تمت التسوية بنجاح');
      setForm({ product:'', quantity_change:'', reason:'count', notes:'' });
      load();
    } catch(e) {
      notify('❌ '+(e?.response?.data?.[0]||JSON.stringify(e?.response?.data)||'خطأ'),'error');
    } finally { setSaving(false); }
  };

  if (loading) return <Spinner />;

  const reasonLabels = {
    count:'جرد دوري', damage:'تلف', loss:'فقد/سرقة',
    return:'مرتجع', expiry:'انتهاء صلاحية', other:'أخرى',
  };

  return (
    <div className="space-y-5">
      {toast && <Toast msg={toast.msg} type={toast.type} />}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
        <h2 className="font-black text-gray-700 mb-4">⚖️ تسوية مخزون جديدة</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <Field label="المنتج *">
            <select className={INP} value={form.product}
              onChange={e=>setForm({...form,product:e.target.value})}>
              <option value="">اختر منتج</option>
              {products.map(p=><option key={p.id} value={p.id}>{p.name} ({p.stock})</option>)}
            </select>
          </Field>
          <Field label="الكمية (+ إضافة / - خصم) *">
            <input type="number" className={INP} placeholder="مثال: 10 أو -5"
              value={form.quantity_change}
              onChange={e=>setForm({...form,quantity_change:e.target.value})} />
          </Field>
          <Field label="السبب">
            <select className={INP} value={form.reason}
              onChange={e=>setForm({...form,reason:e.target.value})}>
              {Object.entries(reasonLabels).map(([k,v])=><option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
          <Field label="ملاحظات">
            <input className={INP} placeholder="اختياري" value={form.notes}
              onChange={e=>setForm({...form,notes:e.target.value})} />
          </Field>
        </div>
        <button onClick={handleSave} disabled={saving}
          className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2 rounded-xl text-sm">
          {saving?'...':'💾 تطبيق التسوية'}
        </button>
      </div>
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b bg-gray-50 font-black text-gray-700">سجل التسويات</div>
        <table className="w-full text-sm">
          <thead><tr className="bg-gray-50 text-gray-500 text-right">
            <th className="px-4 py-3 font-bold">المنتج</th>
            <th className="px-4 py-3 font-bold">قبل</th>
            <th className="px-4 py-3 font-bold">التغيير</th>
            <th className="px-4 py-3 font-bold">بعد</th>
            <th className="px-4 py-3 font-bold">السبب</th>
            <th className="px-4 py-3 font-bold">الموظف</th>
            <th className="px-4 py-3 font-bold">التاريخ</th>
          </tr></thead>
          <tbody>
            {adjustments.length===0 && (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">لا توجد تسويات</td></tr>
            )}
            {adjustments.map(a=>(
              <tr key={a.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 font-bold">{a.product_name}</td>
                <td className="px-4 py-3">{a.quantity_before}</td>
                <td className="px-4 py-3">
                  <span className={`font-black ${a.quantity_change>=0?'text-green-600':'text-red-600'}`}>
                    {a.quantity_change>=0?'+':''}{a.quantity_change}
                  </span>
                </td>
                <td className="px-4 py-3 font-bold">{a.quantity_after}</td>
                <td className="px-4 py-3">{a.reason_display}</td>
                <td className="px-4 py-3 text-gray-500">{a.user_name||'—'}</td>
                <td className="px-4 py-3 text-gray-500">{a.created_at?.split('T')[0]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Alerts ───────────────────────────────────────────────────────────────────
function AlertsPanel() {
  const [alerts, setAlerts]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter]   = useState('active');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = filter==='all' ? {} : { is_resolved: filter==='resolved' };
      const res = await inventoryAPI.getAlerts(params);
      setAlerts(res.data?.results||res.data||[]);
    } catch {/**/ } finally { setLoading(false); }
  }, [filter]);

  useEffect(()=>{ load(); }, [load]);

  const handleResolve = async (id) => {
    await inventoryAPI.resolveAlert(id);
    load();
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {['all','active','resolved'].map(f=>(
          <button key={f} onClick={()=>setFilter(f)}
            className={`px-3 py-1.5 rounded-xl text-sm font-bold ${
              filter===f?'bg-blue-600 text-white':'bg-white border text-gray-600'
            }`}>
            {f==='all'?'الكل':f==='active'?'🔴 نشطة':'✅ محلولة'}
          </button>
        ))}
      </div>
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="bg-gray-50 text-gray-500 text-right">
            <th className="px-4 py-3 font-bold">المنتج</th>
            <th className="px-4 py-3 font-bold">الباركود</th>
            <th className="px-4 py-3 font-bold">نوع التنبيه</th>
            <th className="px-4 py-3 font-bold">المخزون</th>
            <th className="px-4 py-3 font-bold">الحد</th>
            <th className="px-4 py-3 font-bold">الحالة</th>
            <th className="px-4 py-3 font-bold">التاريخ</th>
            <th className="px-4 py-3 font-bold">إجراء</th>
          </tr></thead>
          <tbody>
            {alerts.length===0 && (
              <tr><td colSpan={8} className="text-center py-8 text-gray-400">لا توجد تنبيهات</td></tr>
            )}
            {alerts.map(a=>(
              <tr key={a.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 font-bold">{a.product_name}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{a.product_barcode||'—'}</td>
                <td className="px-4 py-3">
                  <Badge label={a.alert_type_display} color={alertColor(a.alert_type)} />
                </td>
                <td className="px-4 py-3 font-black text-red-600">{a.current_stock}</td>
                <td className="px-4 py-3">{a.threshold}</td>
                <td className="px-4 py-3">
                  <Badge label={a.is_resolved?'محلول':'نشط'} color={a.is_resolved?'green':'red'} />
                </td>
                <td className="px-4 py-3 text-gray-500">{a.created_at?.split('T')[0]}</td>
                <td className="px-4 py-3">
                  {!a.is_resolved && (
                    <button onClick={()=>handleResolve(a.id)}
                      className="bg-green-100 hover:bg-green-200 text-green-700 text-xs font-bold px-3 py-1 rounded-lg">
                      ✅ حل
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Suppliers ────────────────────────────────────────────────────────────────
function SuppliersPanel() {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [showForm, setShowForm]   = useState(false);
  const [editing, setEditing]     = useState(null);
  const [toast, setToast]         = useState(null);
  const notify = (msg,type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await inventoryAPI.getSuppliers();
      setSuppliers(r.data?.results||r.data||[]);
    } catch {/**/ } finally { setLoading(false); }
  }, []);

  useEffect(()=>{ load(); }, [load]);

  const handleSave = async (data) => {
    try {
      if (editing) await inventoryAPI.updateSupplier(editing.id, data);
      else         await inventoryAPI.createSupplier(data);
      notify('✅ تم الحفظ');
      setShowForm(false); setEditing(null); load();
    } catch(e) { notify('❌ '+JSON.stringify(e?.response?.data||'خطأ'),'error'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('حذف المورد؟')) return;
    try { await inventoryAPI.deleteSupplier(id); notify('تم الحذف'); load(); }
    catch { notify('❌ خطأ في الحذف','error'); }
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      {toast && <Toast msg={toast.msg} type={toast.type} />}
      <div className="flex justify-between items-center">
        <h2 className="font-black text-gray-700 text-lg">الموردون</h2>
        <button onClick={()=>{ setEditing(null); setShowForm(true); }}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-4 py-2 rounded-xl text-sm">
          ➕ مورد جديد
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {suppliers.length===0 && (
          <p className="text-gray-400 col-span-3 text-center py-8">لا يوجد موردون</p>
        )}
        {suppliers.map(s=>(
          <div key={s.id} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-black text-gray-800">{s.name}</div>
                {s.phone && <div className="text-sm text-gray-500 mt-1">📞 {s.phone}</div>}
                {s.email && <div className="text-sm text-gray-500">✉️ {s.email}</div>}
                <div className="text-xs text-blue-600 mt-2 font-bold">{s.orders_count} أوامر شراء</div>
              </div>
              <div className="flex gap-2">
                <button onClick={()=>{ setEditing(s); setShowForm(true); }}
                  className="text-blue-500 hover:text-blue-700 text-sm">✏️</button>
                <button onClick={()=>handleDelete(s.id)}
                  className="text-red-400 hover:text-red-600 text-sm">🗑️</button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {showForm && (
        <SupplierModal
          initial={editing}
          onClose={()=>{ setShowForm(false); setEditing(null); }}
          onSave={handleSave} />
      )}
    </div>
  );
}

function SupplierModal({ initial, onClose, onSave }) {
  const [form, setForm] = useState({ name:'', phone:'', email:'', address:'', notes:'', ...initial });
  const [saving, setSaving] = useState(false);
  const handle = async () => { setSaving(true); await onSave(form); setSaving(false); };
  return (
    <Modal title={initial?'✏️ تعديل المورد':'➕ مورد جديد'} onClose={onClose}>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="الاسم *">
            <input className={INP} value={form.name}
              onChange={e=>setForm({...form,name:e.target.value})} />
          </Field>
          <Field label="الهاتف">
            <input className={INP} value={form.phone||''}
              onChange={e=>setForm({...form,phone:e.target.value})} />
          </Field>
          <Field label="البريد الإلكتروني">
            <input className={INP} value={form.email||''}
              onChange={e=>setForm({...form,email:e.target.value})} />
          </Field>
          <Field label="العنوان">
            <input className={INP} value={form.address||''}
              onChange={e=>setForm({...form,address:e.target.value})} />
          </Field>
        </div>
        <Field label="ملاحظات">
          <textarea className={INP} rows={2} value={form.notes||''}
            onChange={e=>setForm({...form,notes:e.target.value})} />
        </Field>
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded-xl border font-bold text-sm">إلغاء</button>
          <button onClick={handle} disabled={saving}
            className="bg-blue-600 text-white font-bold px-5 py-2 rounded-xl text-sm">
            {saving?'...':'💾 حفظ'}
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ─── Quick Order Modal ────────────────────────────────────────────────────────
function QuickOrderModal({ product, suppliers, onClose, onSaved, onError }) {
  const [form, setForm] = useState({
    reference_number: `PO-${Date.now()}`,
    supplier:         '',
    expected_date:    '',
    notes:            '',
    status:           'ordered',
  });
  const [quantity,  setQuantity] = useState(10);
  const [unit_cost, setUnitCost] = useState(product.cost || '');
  const [saving,    setSaving]   = useState(false);

  const handleSave = async () => {
    if (!quantity || Number(quantity) <= 0) return onError('الكمية يجب أن تكون أكبر من صفر');
    if (!unit_cost || Number(unit_cost) <= 0) return onError('أدخل تكلفة الوحدة');
    setSaving(true);
    try {
      await inventoryAPI.createPurchaseOrder({
        ...form,
        supplier: form.supplier || null,
        items: [{
          product:   product.id,
          quantity:  Number(quantity),
          unit_cost: Number(unit_cost),
        }],
      });
      onSaved();
    } catch(e) {
      onError(JSON.stringify(e?.response?.data || 'خطأ'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={`📦 طلب شراء سريع`} onClose={onClose}>
      <div className="space-y-4">

        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3 flex items-center gap-3">
          <div className="text-3xl">⚠️</div>
          <div>
            <div className="font-black text-gray-800">{product.name}</div>
            <div className="text-sm text-gray-500 mt-0.5">
              الباركود: {product.barcode || '—'}
              {' | '}
              المخزون الحالي:{' '}
              <span className={`font-black ${product.stock===0?'text-red-600':'text-yellow-600'}`}>
                {product.stock}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="رقم المرجع *">
            <input className={INP} value={form.reference_number}
              onChange={e=>setForm({...form, reference_number: e.target.value})} />
          </Field>
          <Field label="المورد">
            <select className={INP} value={form.supplier}
              onChange={e=>setForm({...form, supplier: e.target.value})}>
              <option value="">بدون مورد</option>
              {suppliers.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="الكمية المطلوبة *">
            <input type="number" min={1} className={INP} value={quantity}
              onChange={e=>setQuantity(e.target.value)} />
          </Field>
          <Field label="تكلفة الوحدة *">
            <input type="number" min={0} step="0.01" className={INP} value={unit_cost}
              onChange={e=>setUnitCost(e.target.value)} />
          </Field>
          <Field label="تاريخ الاستلام المتوقع">
            <input type="date" className={INP} value={form.expected_date}
              onChange={e=>setForm({...form, expected_date: e.target.value})} />
          </Field>
          <Field label="الحالة">
            <select className={INP} value={form.status}
              onChange={e=>setForm({...form, status: e.target.value})}>
              <option value="draft">مسودة</option>
              <option value="ordered">تم الطلب</option>
            </select>
          </Field>
        </div>

        <Field label="ملاحظات">
          <textarea className={INP} rows={2} value={form.notes}
            onChange={e=>setForm({...form, notes: e.target.value})} />
        </Field>

        {Number(quantity) > 0 && Number(unit_cost) > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 text-sm">
            <span className="text-gray-600">إجمالي التكلفة المتوقعة: </span>
            <span className="font-black text-blue-700 text-base">
              {fmt(Number(quantity) * Number(unit_cost))} ج
            </span>
          </div>
        )}

        <div className="flex gap-3 justify-end pt-1">
          <button onClick={onClose}
            className="px-4 py-2 rounded-xl border font-bold text-sm text-gray-600 hover:bg-gray-50">
            إلغاء
          </button>
          <button onClick={handleSave} disabled={saving}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2 rounded-xl text-sm">
            {saving ? '...' : '💾 إنشاء الطلب'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
"""
# ══════════════════════════════════════════════════════════════════════════════

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(CONTENT)

print(f"\n🎉  تم كتابة الملف بالكامل بنجاح!")
print(f"    {FILE_PATH}")
print("""
الخطوات التالية:
  cd pos_frontend && npm run dev
""")
