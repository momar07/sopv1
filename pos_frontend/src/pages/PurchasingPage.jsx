import React, { useCallback, useEffect, useState } from 'react';
import { inventoryAPI, productsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const fmt = (n) => Number(n || 0).toFixed(2);

const Badge = ({ label, color }) => {
  const map = {
    green:  'bg-green-100 text-green-800',
    red:    'bg-red-100 text-red-800',
    yellow: 'bg-yellow-100 text-yellow-800',
    blue:   'bg-blue-100 text-blue-800',
    gray:   'bg-gray-100 text-gray-600',
    purple: 'bg-purple-100 text-purple-800',
  };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${map[color]||map.gray}`}>{label}</span>;
};

const statusColor = (s) => ({ draft:'gray', ordered:'blue', received:'green', cancelled:'red' }[s]||'gray');
const Spinner = () => (
  <div className="flex items-center justify-center h-40">
    <i className="fas fa-spinner fa-spin text-4xl text-blue-500"></i>
  </div>
);
const Toast = ({ msg, type }) => (
  <div className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-2xl shadow-xl font-bold text-sm
    ${type==="error"?"bg-red-600 text-white":"bg-green-600 text-white"}`}>{msg}</div>
);
const Modal = ({ title, onClose, children }) => (
  <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      onClick={(e)=>e.stopPropagation()}>
      <div className="flex justify-between items-center px-5 py-4 border-b">
        <h3 className="font-black text-gray-800">{title}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-700 font-black text-xl">×</button>
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

// ── Priority / Status configs ──────────────────────────────────
const priorityConfig = {
  low:      { label: 'منخفضة',  color: 'bg-gray-100  text-gray-600',    dot: 'bg-gray-400'   },
  medium:   { label: 'متوسطة',  color: 'bg-blue-100  text-blue-700',    dot: 'bg-blue-500'   },
  high:     { label: 'عالية',   color: 'bg-orange-100 text-orange-700', dot: 'bg-orange-500' },
  critical: { label: 'حرجة',    color: 'bg-red-100   text-red-700',     dot: 'bg-red-500'    },
};
const ticketStatusConfig = {
  open:        { label: 'مفتوحة',        color: 'bg-red-100    text-red-700'    },
  in_progress: { label: 'قيد المعالجة', color: 'bg-yellow-100 text-yellow-700' },
  ordered:     { label: 'تم الطلب',      color: 'bg-blue-100   text-blue-700'   },
  resolved:    { label: 'محلولة',        color: 'bg-green-100  text-green-700'  },
};
const noteTypeConfig = {
  note:   { label: 'ملاحظة',      icon: '\uD83D\uDCDD', color: 'border-gray-200   bg-gray-50'   },
  quote:  { label: 'عرض سعر',    icon: '\uD83D\uDCB0', color: 'border-green-200  bg-green-50'  },
  action: { label: 'إجراء',       icon: '\u26A1',       color: 'border-blue-200   bg-blue-50'   },
  delay:  { label: 'سبب تأخير',  icon: '\u23F0',       color: 'border-orange-200 bg-orange-50' },
  system: { label: 'تحديث نظام', icon: '\uD83D\uDD27', color: 'border-purple-200 bg-purple-50' },
};

// ── Main Page ──────────────────────────────────────────────────
export default function PurchasingPage() {
  const [tab, setTab] = useState('alerts');
  const tabs = [
    { key: 'alerts',    label: 'التنبيهات' },
    { key: 'orders',    label: 'أوامر الشراء' },
    { key: 'suppliers', label: 'الموردون' },
  ];
  return (
    <div dir="rtl" className="p-4 min-h-screen bg-gray-50">
      <div className="mb-5">
        <h1 className="text-2xl font-black text-gray-800">المشتريات</h1>
        <p className="text-gray-500 text-sm mt-1">تنبيهات المخزون · أوامر الشراء · الموردون</p>
      </div>
      <div className="flex gap-2 flex-wrap mb-5">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-xl font-bold text-sm transition-all ${
              tab === t.key ? 'bg-blue-600 text-white shadow' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}>{t.label}</button>
        ))}
      </div>
      {tab === 'alerts'    && <AlertsPanel />}
      {tab === 'orders'    && <PurchaseOrdersPanel />}
      {tab === 'suppliers' && <SuppliersPanel />}
    </div>
  );
}

// ── AlertCard ──────────────────────────────────────────────────
function AlertCard({ alert, onOpen }) {
  const pr = priorityConfig[alert.priority] || priorityConfig.medium;
  const st = ticketStatusConfig[alert.ticket_status] || ticketStatusConfig.open;
  const isOverdue = alert.deadline && !alert.is_resolved && new Date(alert.deadline) < new Date();
  return (
    <div onClick={() => onOpen(alert)}
      className={`bg-white rounded-2xl border shadow-sm p-4 cursor-pointer hover:shadow-md transition-all
        ${alert.is_resolved ? 'opacity-60' : ''}
        ${isOverdue ? 'border-red-400 ring-1 ring-red-300' : 'border-gray-200'}`}>
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${pr.dot}`}></span>
            <span className="font-black text-gray-800 text-sm truncate">{alert.product_name}</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${st.color}`}>{st.label}</span>
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${pr.color}`}>{pr.label}</span>
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
              alert.alert_type==='out'?'bg-red-100 text-red-700':'bg-yellow-100 text-yellow-700'}` }>
              {alert.alert_type==='out'?'نفاد':'منخفض'}
            </span>
          </div>
        </div>
        <div className="text-center flex-shrink-0">
          <div className={`text-2xl font-black ${alert.product_current_stock===0?'text-red-600':'text-orange-500'}`}>
            {alert.product_current_stock ?? alert.current_stock}
          </div>
          <div className="text-xs text-gray-400">وحدة</div>
        </div>
      </div>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-3">
          {alert.notes_count > 0 && <span>{alert.notes_count} ملاحظة</span>}
          {alert.linked_pos_count > 0 && (
            <span className="text-blue-600">{alert.linked_pos_count} عروض شراء</span>
          )}
          {alert.assigned_to_name
            ? <span className="text-green-600">مخصص: {alert.assigned_to_name}</span>
            : <span className="text-gray-400">غير مخصص</span>
          }
          {isOverdue && <span className="text-red-600 font-bold">متأخر</span>}
        </div>
        <div className="text-left">
          {alert.created_by_name && <div>بواسطة: {alert.created_by_name}</div>}
          <div>{alert.created_at?.split('T')[0]}</div>
        </div>
      </div>
    </div>
  );
}

// ── AssignSection ──────────────────────────────────────────────
function AssignSection({ data, onUpdated, notify }) {
  const { user } = useAuth();
  const [users, setUsers]       = useState([]);
  const [selUser, setSelUser]   = useState('');
  const [saving, setSaving]     = useState(false);

  const isManager = user?.is_superuser ||
    (user?.groups || []).some(g => g === 'Admins' || g === 'Managers');

  useEffect(() => {
    if (!isManager) return;
    import('../services/api').then(m => {
      const api = m.usersAPI || m.default?.usersAPI;
      if (api) api.getAll().then(r => setUsers(r.data?.results || r.data || []));
    });
  }, [isManager]);

  const handleAssignMe = async () => {
    setSaving(true);
    try {
      await inventoryAPI.assignAlertToMe(data.id);
      notify('تم التخصيص لك');
      onUpdated();
    } catch { notify('خطأ في التخصيص', 'error'); }
    finally { setSaving(false); }
  };

  const handleAssignUser = async () => {
    if (!selUser) return notify('اختر مستخدم', 'error');
    setSaving(true);
    try {
      await inventoryAPI.assignAlertToUser(data.id, { user_id: selUser });
      notify('تم التخصيص');
      onUpdated();
    } catch { notify('خطأ', 'error'); }
    finally { setSaving(false); }
  };

  const handleUnassign = async () => {
    setSaving(true);
    try {
      await inventoryAPI.unassignAlert(data.id);
      notify('تم الغاء التخصيص');
      onUpdated();
    } catch { notify('خطأ', 'error'); }
    finally { setSaving(false); }
  };

  return (
    <div className="mb-4 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
      <p className="text-xs font-bold text-gray-500 mb-2">التخصيص</p>
      <div className="flex items-center gap-2 flex-wrap">
        {data.assigned_to_name ? (
          <>
            <span className="text-sm font-bold text-blue-700">مخصص لـ: {data.assigned_to_name}</span>
            <button onClick={handleUnassign} disabled={saving}
              className="text-xs bg-red-100 hover:bg-red-200 text-red-700 font-bold px-2 py-1 rounded-lg">
              الغاء التخصيص
            </button>
          </>
        ) : (
          <span className="text-sm text-gray-400">غير مخصص لأحد</span>
        )}
        <button onClick={handleAssignMe} disabled={saving}
          className="text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 font-bold px-2 py-1 rounded-lg">
          تخصيص لي
        </button>
        {isManager && (
          <div className="flex items-center gap-1">
            <select className="text-xs border border-gray-200 rounded-lg px-2 py-1"
              value={selUser} onChange={e => setSelUser(e.target.value)}>
              <option value="">اختر مستخدم...</option>
              {users.map(u => <option key={u.id} value={u.id}>{u.username}</option>)}
            </select>
            <button onClick={handleAssignUser} disabled={saving || !selUser}
              className="text-xs bg-purple-100 hover:bg-purple-200 text-purple-700 font-bold px-2 py-1 rounded-lg">
              تخصيص
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── AlertsPanel ────────────────────────────────────────────────
function AlertsPanel() {
  const [alerts, setAlerts]       = useState([]);
  const [loading, setLoading]     = useState(true);
  const [filter, setFilter]       = useState('unresolved');
  const [selected, setSelected]   = useState(null);
  const [toast, setToast]         = useState(null);
  const [suppliers, setSuppliers] = useState([]);
  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filter === 'unresolved') params.is_resolved = false;
      else if (filter === 'resolved') params.is_resolved = true;
      else if (filter === 'critical') { params.is_resolved = false; params.priority = 'critical'; }
      else if (filter === 'out') { params.is_resolved = false; params.alert_type = 'out'; }
      const [a, s] = await Promise.all([
        inventoryAPI.getAlerts(params),
        inventoryAPI.getSuppliers(),
      ]);
      setAlerts(a.data?.results || a.data || []);
      setSuppliers(s.data?.results || s.data || []);
    } catch { /**/ } finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const handleGenerate = async () => {
    try {
      const r = await inventoryAPI.checkAndGenerateAlerts({ threshold: 10 });
      notify('تم إنشاء ' + r.data.created_alerts + ' تنبيه جديد');
      load();
    } catch { notify('خطأ في توليد التنبيهات', 'error'); }
  };

  const filters = [
    { key: 'unresolved', label: 'غير محلولة' },
    { key: 'out',        label: 'نفاد'     },
    { key: 'critical',   label: 'حرجة'     },
    { key: 'resolved',   label: 'محلولة'   },
    { key: 'all',        label: 'الكل'        },
  ];

  if (loading) return <Spinner />;
  return (
    <div className="space-y-4">
      {toast && <Toast msg={toast.msg} type={toast.type} />}
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <div className="flex gap-2 flex-wrap">
          {filters.map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)}
              className={`px-3 py-1.5 rounded-xl text-sm font-bold transition ${
                filter === f.key ? 'bg-blue-600 text-white' : 'bg-white border text-gray-600 hover:bg-gray-50'
              }`}>{f.label}</button>
          ))}
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="bg-white border text-gray-600 hover:bg-gray-50 font-bold px-3 py-1.5 rounded-xl text-sm">تحديث</button>
          <button onClick={handleGenerate}
            className="bg-yellow-500 hover:bg-yellow-600 text-white font-bold px-4 py-1.5 rounded-xl text-sm">
            فحص وتوليد التنبيهات
          </button>
        </div>
      </div>
      {alerts.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center text-gray-400">
          <p className="font-bold">لا توجد تنبيهات</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {alerts.map(a => (
            <AlertCard key={a.id} alert={a} onOpen={setSelected} />
          ))}
        </div>
      )}
      {selected && (
        <AlertTicketModal
          alert={selected}
          suppliers={suppliers}
          onClose={() => setSelected(null)}
          onUpdated={() => { setSelected(null); load(); }}
          notify={notify}
        />
      )}
    </div>
  );
}

// ── AlertTicketModal ───────────────────────────────────────────
function AlertTicketModal({ alert, suppliers, onClose, onUpdated, notify }) {
  const [data, setData]     = useState(alert);
  const [noteForm, setNote] = useState({ note_type:'note', text:'', cost:'', expected_date:'', delay_reason:'', supplier_name:'' });
  const [poForm, setPo]     = useState({ supplier:'', quantity:1, unit_cost:'', expected_date:'', notes:'' });
  const [tab, setTab]       = useState('timeline');
  const [saving, setSaving] = useState(false);

  const reload = async () => {
    try { const r = await inventoryAPI.getAlert(data.id); setData(r.data); } catch {}
  };

  const handleAddNote = async () => {
    if (!noteForm.text.trim()) return notify('اكتب نص الملاحظة', 'error');
    setSaving(true);
    try {
      await inventoryAPI.addAlertNote(data.id, noteForm);
      setNote({ note_type:'note', text:'', cost:'', expected_date:'', delay_reason:'', supplier_name:'' });
      await reload();
      notify('تمت إضافة الملاحظة');
    } catch(e) { notify('خطأ: '+(e?.response?.data?.error||JSON.stringify(e?.response?.data)||'خطأ'), 'error'); }
    finally { setSaving(false); }
  };

  const handleCreatePO = async () => {
    if (!poForm.quantity || !poForm.unit_cost) return notify('الكمية والتكلفة مطلوبان', 'error');
    setSaving(true);
    try {
      await inventoryAPI.createPoFromAlert(data.id, {
        supplier: poForm.supplier || null,
        quantity: Number(poForm.quantity),
        unit_cost: Number(poForm.unit_cost),
        expected_date: poForm.expected_date || null,
        notes: poForm.notes,
      });
      notify('تم إنشاء عرض الشراء وربطه بالتنبيه');
      await reload();
      setPo({ supplier:'', quantity:1, unit_cost:'', expected_date:'', notes:'' });
    } catch(e) { notify('خطأ: '+(e?.response?.data?.error||JSON.stringify(e?.response?.data)||'خطأ'), 'error'); }
    finally { setSaving(false); }
  };

  const handleResolve = async () => {
    setSaving(true);
    try {
      await inventoryAPI.resolveAlert(data.id, { note: 'تم الحل يدوياً' });
      notify('تم حل التنبيه');
      onUpdated();
    } catch(e) { notify('خطأ: '+(e?.response?.data?.error||JSON.stringify(e?.response?.data)||'خطأ'), 'error'); }
    finally { setSaving(false); }
  };

  const pr = priorityConfig[data.priority] || priorityConfig.medium;
  const st = ticketStatusConfig[data.ticket_status] || ticketStatusConfig.open;

  return (
    <Modal title={'تذكرة: ' + data.product_name} onClose={onClose}>
      {/* badges */}
      <div className="flex flex-wrap gap-2 mb-3">
        <span className={`text-xs font-bold px-2 py-1 rounded-full ${st.color}`}>{st.label}</span>
        <span className={`text-xs font-bold px-2 py-1 rounded-full ${pr.color}`}>{pr.label}</span>
        <span className={`text-xs font-bold px-2 py-1 rounded-full ${
          data.alert_type==='out'?'bg-red-100 text-red-700':'bg-yellow-100 text-yellow-700'}`}>
          {data.alert_type==='out'?'نفاد المخزون':'مخزون منخفض'}
        </span>
        <span className="text-xs font-bold px-2 py-1 rounded-full bg-gray-100 text-gray-700">
          المخزون: {data.product_current_stock ?? data.current_stock} وحدة
        </span>
        {data.created_by_name && (
          <span className="text-xs font-bold px-2 py-1 rounded-full bg-gray-100 text-gray-600">
            بواسطة: {data.created_by_name}
          </span>
        )}
      </div>

      {/* عروض الشراء المرتبطة */}
      {data.linked_pos_data && data.linked_pos_data.length > 0 && (
        <div className="mb-3 bg-blue-50 border border-blue-200 rounded-xl p-3">
          <p className="text-xs font-bold text-blue-700 mb-2">عروض الشراء ({data.linked_pos_data.length}):</p>
          {data.linked_pos_data.map(po => (
            <div key={po.id} className="flex justify-between text-xs text-blue-600 py-1 border-t border-blue-100">
              <span className="font-bold">{po.reference_number}</span>
              <span>{po.status}</span>
              {po.expected_date && <span>{po.expected_date}</span>}
            </div>
          ))}
        </div>
      )}

      {/* التخصيص */}
      <AssignSection data={data} onUpdated={async () => { await reload(); onUpdated && onUpdated(); }} notify={notify} />

      {/* تبويبات */}
      <div className="flex gap-2 border-b mb-4">
        {[
          {key:'timeline', label:'السجل'},
          {key:'add_note', label:'إضافة'},
          {key:'create_po',label:'عرض شراء'},
          {key:'resolve',  label:'حل'},
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-sm font-bold border-b-2 transition -mb-px ${
              tab===t.key?'border-blue-600 text-blue-600':'border-transparent text-gray-500 hover:text-gray-700'
            }`}>{t.label}</button>
        ))}
      </div>

      {/* السجل */}
      {tab === 'timeline' && (
        <div className="space-y-3 max-h-72 overflow-y-auto">
          {(!data.notes || data.notes.length === 0) ? (
            <p className="text-center text-gray-400 py-6">لا توجد ملاحظات بعد</p>
          ) : (
            data.notes.map(n => {
              const nc = noteTypeConfig[n.note_type] || noteTypeConfig.note;
              return (
                <div key={n.id} className={`rounded-xl border p-3 ${nc.color}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold">{nc.icon} {nc.label}</span>
                    <span className="text-xs text-gray-400">{n.user_name} · {n.created_at?.split('T')[0]}</span>
                  </div>
                  <p className="text-sm text-gray-700">{n.text}</p>
                  {n.cost && <p className="text-xs text-green-700 mt-1 font-bold">تكلفة: {fmt(n.cost)}</p>}
                  {n.expected_date && <p className="text-xs text-blue-700 mt-1">تاريخ الاستلام: {n.expected_date}</p>}
                  {n.delay_reason && <p className="text-xs text-orange-700 mt-1">سبب التأخير: {n.delay_reason}</p>}
                  {n.supplier_name && <p className="text-xs text-gray-600 mt-1">المورد: {n.supplier_name}</p>}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* إضافة ملاحظة */}
      {tab === 'add_note' && (
        <div className="space-y-3">
          <Field label="نوع الملاحظة">
            <select className={INP} value={noteForm.note_type} onChange={e=>setNote({...noteForm,note_type:e.target.value})}>
              {Object.entries(noteTypeConfig).map(([k,v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
          </Field>
          <Field label="النص *">
            <textarea className={INP} rows={3} value={noteForm.text}
              onChange={e=>setNote({...noteForm,text:e.target.value})} placeholder="اكتب ملاحظتك هنا..." />
          </Field>
          {noteForm.note_type === 'quote' && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Field label="التكلفة">
                  <input type="number" className={INP} value={noteForm.cost}
                    onChange={e=>setNote({...noteForm,cost:e.target.value})} placeholder="0.00" />
                </Field>
                <Field label="اسم المورد">
                  <input type="text" className={INP} value={noteForm.supplier_name}
                    onChange={e=>setNote({...noteForm,supplier_name:e.target.value})} />
                </Field>
              </div>
              <Field label="تاريخ الاستلام المتوقع">
                <input type="date" className={INP} value={noteForm.expected_date}
                  onChange={e=>setNote({...noteForm,expected_date:e.target.value})} />
              </Field>
            </>
          )}
          {noteForm.note_type === 'delay' && (
            <Field label="سبب التأخير">
              <textarea className={INP} rows={2} value={noteForm.delay_reason}
                onChange={e=>setNote({...noteForm,delay_reason:e.target.value})} />
            </Field>
          )}
          <button onClick={handleAddNote} disabled={saving}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 rounded-xl text-sm disabled:opacity-50">
            {saving ? '...' : 'إضافة الملاحظة'}
          </button>
        </div>
      )}

      {/* إنشاء عرض شراء */}
      {tab === 'create_po' && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="المورد">
              <select className={INP} value={poForm.supplier} onChange={e=>setPo({...poForm,supplier:e.target.value})}>
                <option value="">بدون مورد</option>
                {suppliers.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </Field>
            <Field label="الكمية *">
              <input type="number" min={1} className={INP} value={poForm.quantity}
                onChange={e=>setPo({...poForm,quantity:e.target.value})} />
            </Field>
            <Field label="تكلفة الوحدة *">
              <input type="number" step="0.01" className={INP} value={poForm.unit_cost}
                onChange={e=>setPo({...poForm,unit_cost:e.target.value})} />
            </Field>
            <Field label="تاريخ الاستلام المتوقع">
              <input type="date" className={INP} value={poForm.expected_date}
                onChange={e=>setPo({...poForm,expected_date:e.target.value})} />
            </Field>
          </div>
          <Field label="ملاحظات">
            <input type="text" className={INP} value={poForm.notes}
              onChange={e=>setPo({...poForm,notes:e.target.value})} placeholder="اختياري" />
          </Field>
          <button onClick={handleCreatePO} disabled={saving}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 rounded-xl text-sm disabled:opacity-50">
            {saving ? '...' : 'إنشاء عرض شراء'}
          </button>
        </div>
      )}

      {/* حل التذكرة */}
      {tab === 'resolve' && (
        <div className="space-y-3">
          {data.is_resolved ? (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700 font-bold text-center">
              هذه التذكرة محلولة بالفعل
            </div>
          ) : (
            <>
              {data.linked_pos_data && data.linked_pos_data.some(p => p.status !== 'received' && p.status !== 'cancelled') && (
                <div className="bg-orange-50 border border-orange-200 rounded-xl p-3 text-sm text-orange-700 font-bold">
                  بعض عروض الشراء لم تُستلم بعد. تأكد من الاستلام أولاً.
                </div>
              )}
              <button onClick={handleResolve} disabled={saving}
                className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 rounded-xl text-sm disabled:opacity-50">
                {saving ? '...' : 'تأكيد الحل وإغلاق التذكرة'}
              </button>
            </>
          )}
        </div>
      )}
    </Modal>
  );
}

// ── PurchaseOrdersPanel ────────────────────────────────────────
function PurchaseOrdersPanel() {
  const [orders, setOrders]       = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts]   = useState([]);
  const [loading, setLoading]     = useState(true);
  const [showForm, setShowForm]   = useState(false);
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
    } catch {/**/} finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCancel = async (id) => {
    if (!window.confirm('هل أنت متأكد من الإلغاء؟')) return;
    try { await inventoryAPI.cancelPurchaseOrder(id); notify('تم الإلغاء'); load(); }
    catch(e) { notify('خطأ: '+(e?.response?.data?.error||'خطأ'),'error'); }
  };

  if (loading) return <Spinner />;
  return (
    <div className="space-y-4">
      {toast && <Toast msg={toast.msg} type={toast.type} />}
      <div className="flex justify-between items-center">
        <h2 className="font-black text-gray-700 text-lg">أوامر الشراء</h2>
        <button onClick={() => setShowForm(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-4 py-2 rounded-xl text-sm">
          إنشاء أمر شراء
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
            {orders.length===0 && (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">لا توجد أوامر شراء</td></tr>
            )}
            {orders.map(o => (
              <tr key={o.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 font-bold text-blue-700">{o.reference_number}</td>
                <td className="px-4 py-3">{o.supplier_name||'—'}</td>
                <td className="px-4 py-3"><Badge label={o.status} color={statusColor(o.status)} /></td>
                <td className="px-4 py-3 font-bold">{fmt(o.total_cost)}</td>
                <td className="px-4 py-3 text-gray-500">{o.created_at?.split('T')[0]}</td>
                <td className="px-4 py-3">
                  {o.status!=='received'&&o.status!=='cancelled' && (
                    <button onClick={() => handleCancel(o.id)}
                      className="bg-red-100 hover:bg-red-200 text-red-700 text-xs font-bold px-3 py-1 rounded-lg">
                      إلغاء
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
          onClose={() => setShowForm(false)}
          onSaved={() => { setShowForm(false); load(); notify('تم إنشاء أمر الشراء'); }}
          onError={(msg) => notify('خطأ: '+msg,'error')} />
      )}
    </div>
  );
}

// ── NewOrderModal ──────────────────────────────────────────────
function NewOrderModal({ suppliers, products, onClose, onSaved, onError }) {
  const [form, setForm] = useState({
    reference_number: 'PO-'+Date.now(),
    supplier:'', expected_date:'', notes:'', status:'ordered',
  });
  const [items, setItems]   = useState([{ product:'', quantity:1, unit_cost:'' }]);
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
    <Modal title="أمر شراء جديد" onClose={onClose}>
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
          <Field label="تاريخ الاستلام">
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
            <button onClick={addItem} className="text-blue-600 text-sm font-bold hover:underline">+ إضافة</button>
          </div>
          {items.map((item,i) => (
            <div key={i} className="flex gap-2 mb-2 items-end">
              <div className="flex-1">
                <select className={INP+' text-xs'} value={item.product}
                  onChange={e=>updateItem(i,'product',e.target.value)}>
                  <option value="">اختر منتج</option>
                  {products.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div className="w-20">
                <input type="number" className={INP+' text-xs text-center'} placeholder="كمية"
                  min={1} value={item.quantity} onChange={e=>updateItem(i,'quantity',e.target.value)} />
              </div>
              <div className="w-24">
                <input type="number" className={INP+' text-xs text-center'} placeholder="تكلفة"
                  min={0} step="0.01" value={item.unit_cost} onChange={e=>updateItem(i,'unit_cost',e.target.value)} />
              </div>
              <button onClick={()=>removeItem(i)}
                className="text-red-500 font-black text-xl leading-none mb-1">×</button>
            </div>
          ))}
        </div>
        <div className="flex gap-3 justify-end pt-2">
          <button onClick={onClose} className="px-4 py-2 rounded-xl border font-bold text-sm">إلغاء</button>
          <button onClick={handleSave} disabled={saving}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2 rounded-xl text-sm">
            {saving?'...':'حفظ'}
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ── SuppliersPanel ─────────────────────────────────────────────
function SuppliersPanel() {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [toast, setToast]         = useState(null);
  const [showForm, setShowForm]   = useState(false);
  const [editing, setEditing]     = useState(null);
  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await inventoryAPI.getSuppliers();
      setSuppliers(r.data?.results || r.data || []);
    } catch {/**/} finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (form) => {
    try {
      if (editing) {
        await inventoryAPI.updateSupplier(editing.id, form);
        notify('تم التعديل');
      } else {
        await inventoryAPI.createSupplier(form);
        notify('تم الإضافة');
      }
      setShowForm(false); setEditing(null); load();
    } catch { notify('خطأ', 'error'); }
  };

  if (loading) return <Spinner />;
  return (
    <div className="space-y-4">
      {toast && <Toast msg={toast.msg} type={toast.type} />}
      <div className="flex justify-between items-center">
        <h2 className="font-black text-gray-700 text-lg">الموردون</h2>
        <button onClick={() => { setEditing(null); setShowForm(true); }}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-4 py-2 rounded-xl text-sm">
          إضافة مورد
        </button>
      </div>
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="bg-gray-50 text-gray-500 text-right">
            <th className="px-4 py-3 font-bold">الاسم</th>
            <th className="px-4 py-3 font-bold">الهاتف</th>
            <th className="px-4 py-3 font-bold">البريد</th>
            <th className="px-4 py-3 font-bold">الطلبات</th>
            <th className="px-4 py-3 font-bold">إجراءات</th>
          </tr></thead>
          <tbody>
            {suppliers.length===0 && (
              <tr><td colSpan={5} className="text-center py-8 text-gray-400">لا يوجد موردون</td></tr>
            )}
            {suppliers.map(s => (
              <tr key={s.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 font-bold">{s.name}</td>
                <td className="px-4 py-3">{s.phone||'-'}</td>
                <td className="px-4 py-3">{s.email||'-'}</td>
                <td className="px-4 py-3">{s.orders_count}</td>
                <td className="px-4 py-3">
                  <button onClick={() => { setEditing(s); setShowForm(true); }}
                    className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold px-2 py-1 rounded-lg">
                    تعديل
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showForm && (
        <SupplierFormModal
          initial={editing}
          onClose={() => { setShowForm(false); setEditing(null); }}
          onSave={handleSave}
        />
      )}
    </div>
  );
}

function SupplierFormModal({ initial, onClose, onSave }) {
  const [form, setForm] = useState(
    initial ? { ...initial } : { name:'', phone:'', email:'', address:'', notes:'' }
  );
  const [saving, setSaving] = useState(false);
  const handleSave = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    await onSave(form);
    setSaving(false);
  };
  return (
    <Modal title={initial ? 'تعديل مورد' : 'إضافة مورد'} onClose={onClose}>
      <div className="space-y-3">
        <Field label="الاسم *"><input className={INP} value={form.name}
          onChange={e=>setForm({...form,name:e.target.value})} /></Field>
        <Field label="الهاتف"><input className={INP} value={form.phone}
          onChange={e=>setForm({...form,phone:e.target.value})} /></Field>
        <Field label="البريد"><input className={INP} value={form.email}
          onChange={e=>setForm({...form,email:e.target.value})} /></Field>
        <Field label="العنوان"><textarea className={INP} rows={2} value={form.address}
          onChange={e=>setForm({...form,address:e.target.value})} /></Field>
        <Field label="ملاحظات"><textarea className={INP} rows={2} value={form.notes}
          onChange={e=>setForm({...form,notes:e.target.value})} /></Field>
        <div className="flex gap-3 justify-end pt-2">
          <button onClick={onClose} className="px-4 py-2 rounded-xl border font-bold text-sm">إلغاء</button>
          <button onClick={handleSave} disabled={saving||!form.name.trim()}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2 rounded-xl text-sm disabled:opacity-50">
            {saving?'...':'حفظ'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
