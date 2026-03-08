#!/usr/bin/env python3
"""
fix_03b_alert_ticket_frontend.py
==================================
النقطة الثالثة — Frontend:
  - InventoryPage.jsx : استبدال AlertsPanel بنظام تذاكر كامل
  - api.js            : إضافة endpoints جديدة للـ alerts
"""

import os, shutil, sys
from datetime import datetime

BASE     = os.path.dirname(os.path.abspath(__file__))
INV_PAGE = os.path.join(BASE, 'pos_frontend', 'src', 'pages', 'InventoryPage.jsx')
API_FILE = os.path.join(BASE, 'pos_frontend', 'src', 'services', 'api.js')

for path in [INV_PAGE, API_FILE]:
    if not os.path.exists(path):
        print(f'❌  غير موجود: {path}')
        sys.exit(1)

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
for path in [INV_PAGE, API_FILE]:
    shutil.copy2(path, path + f'.bak_{stamp}')
    print(f'✅  نسخة احتياطية: {os.path.basename(path)}')

# ══════════════════════════════════════════════════════════════════════════
#  1) api.js — إضافة endpoints جديدة
# ══════════════════════════════════════════════════════════════════════════
with open(API_FILE, 'r', encoding='utf-8') as f:
    api_src = f.read()

OLD_ALERTS_API = """  // Alerts
  getAlerts:             (params) => api.get('/inventory/alerts/', { params }),
  getAlertsSummary:      (params) => api.get('/inventory/alerts/summary/', { params }),
  checkAndGenerateAlerts:(data)   => api.post('/inventory/alerts/check_and_generate/', data),
  resolveAlert:          (id)     => api.post(`/inventory/alerts/${id}/resolve/`),"""

NEW_ALERTS_API = """  // Alerts — Ticket System
  getAlerts:             (params)       => api.get('/inventory/alerts/', { params }),
  getAlert:              (id)           => api.get(`/inventory/alerts/${id}/`),
  getAlertsSummary:      (params)       => api.get('/inventory/alerts/summary/', { params }),
  checkAndGenerateAlerts:(data)         => api.post('/inventory/alerts/check_and_generate/', data),
  resolveAlert:          (id, data={}) => api.post(`/inventory/alerts/${id}/resolve/`, data),
  addAlertNote:          (id, data)     => api.post(`/inventory/alerts/${id}/add_note/`, data),
  createPoFromAlert:     (id, data)     => api.post(`/inventory/alerts/${id}/create_purchase_order/`, data),
  updateAlertMeta:       (id, data)     => api.patch(`/inventory/alerts/${id}/update_meta/`, data),"""

if OLD_ALERTS_API in api_src:
    api_src = api_src.replace(OLD_ALERTS_API, NEW_ALERTS_API, 1)
    print('✅  api.js — تم تحديث Alerts endpoints')
else:
    print('⚠️  Alerts endpoints لم تُعثر عليها — راجع api.js يدوياً')

with open(API_FILE, 'w', encoding='utf-8') as f:
    f.write(api_src)

# ══════════════════════════════════════════════════════════════════════════
#  2) InventoryPage.jsx — استبدال AlertsPanel
# ══════════════════════════════════════════════════════════════════════════
with open(INV_PAGE, 'r', encoding='utf-8') as f:
    inv_src = f.read()

# الـ AlertsPanel الجديد الكامل
NEW_ALERTS_PANEL = '''// ══════════════════════════════════════════════════════
//  AlertsPanel — Ticket System
// ══════════════════════════════════════════════════════

// ── ألوان الأولوية ────────────────────────────────────
const priorityConfig = {
  low:      { label: 'منخفضة',  color: 'bg-gray-100  text-gray-600',   dot: 'bg-gray-400'   },
  medium:   { label: 'متوسطة',  color: 'bg-blue-100  text-blue-700',   dot: 'bg-blue-500'   },
  high:     { label: 'عالية',   color: 'bg-orange-100 text-orange-700', dot: 'bg-orange-500' },
  critical: { label: 'حرجة',    color: 'bg-red-100   text-red-700',    dot: 'bg-red-500'    },
};

// ── ألوان حالة التذكرة ────────────────────────────────
const ticketStatusConfig = {
  open:        { label: 'مفتوحة',        color: 'bg-red-100    text-red-700'    },
  in_progress: { label: 'قيد المعالجة', color: 'bg-yellow-100 text-yellow-700' },
  ordered:     { label: 'تم الطلب',      color: 'bg-blue-100   text-blue-700'   },
  resolved:    { label: 'محلولة',        color: 'bg-green-100  text-green-700'  },
};

// ── ألوان نوع الملاحظة ────────────────────────────────
const noteTypeConfig = {
  note:   { label: 'ملاحظة',      icon: '📝', color: 'border-gray-200   bg-gray-50'    },
  quote:  { label: 'عرض سعر',    icon: '💰', color: 'border-green-200  bg-green-50'   },
  action: { label: 'إجراء',       icon: '⚡', color: 'border-blue-200   bg-blue-50'    },
  delay:  { label: 'سبب تأخير',  icon: '⏰', color: 'border-orange-200 bg-orange-50'  },
  system: { label: 'تحديث نظام', icon: '🔧', color: 'border-purple-200 bg-purple-50'  },
};

// ── مكوّن بطاقة التذكرة في القائمة ───────────────────
function AlertCard({ alert, onOpen }) {
  const pr = priorityConfig[alert.priority]  || priorityConfig.medium;
  const st = ticketStatusConfig[alert.ticket_status] || ticketStatusConfig.open;
  const isOverdue = alert.deadline && !alert.is_resolved && new Date(alert.deadline) < new Date();

  return (
    <div
      onClick={() => onOpen(alert)}
      className={`bg-white rounded-2xl border shadow-sm p-4 cursor-pointer hover:shadow-md transition-all
        ${alert.is_resolved ? \'opacity-60\' : \'\'}
        ${isOverdue ? \'border-red-400 ring-1 ring-red-300\' : \'border-gray-200\'}`}
    >
      {/* رأس البطاقة */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${pr.dot}`}></span>
            <span className="font-black text-gray-800 text-sm truncate">{alert.product_name}</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${st.color}`}>
              {st.label}
            </span>
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${pr.color}`}>
              {pr.label}
            </span>
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full
              ${alert.alert_type === \'out\' ? \'bg-red-100 text-red-700\' : \'bg-yellow-100 text-yellow-700\'}`}>
              {alert.alert_type === \'out\' ? \'🚨 نفاد\' : \'⚠️ منخفض\'}
            </span>
          </div>
        </div>
        {/* المخزون الحالي */}
        <div className="text-center flex-shrink-0">
          <div className={`text-2xl font-black ${alert.product_current_stock === 0 ? \'text-red-600\' : \'text-orange-500\'}`}>
            {alert.product_current_stock ?? alert.current_stock}
          </div>
          <div className="text-xs text-gray-400">وحدة</div>
        </div>
      </div>

      {/* معلومات إضافية */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-3">
          {alert.notes_count > 0 && (
            <span className="flex items-center gap-1">
              💬 <span className="font-bold">{alert.notes_count}</span>
            </span>
          )}
          {alert.linked_po_reference && (
            <span className="flex items-center gap-1 text-blue-600 font-bold">
              📦 {alert.linked_po_reference}
            </span>
          )}
          {isOverdue && (
            <span className="text-red-600 font-bold flex items-center gap-1">
              ⏰ متأخرة
            </span>
          )}
        </div>
        <span>{alert.created_at?.split(\'T\')[0]}</span>
      </div>
    </div>
  );
}

// ── مكوّن التذكرة الكاملة (Modal) ────────────────────
function AlertTicketModal({ alert: initialAlert, suppliers, onClose, onUpdated }) {
  const [alert,        setAlert]       = useState(initialAlert);
  const [loading,      setLoading]     = useState(false);
  const [noteForm,     setNoteForm]    = useState({
    note_type: \'note\', text: \'\', cost: \'\', expected_date: \'\', delay_reason: \'\', supplier_name: \'\',
  });
  const [poForm,       setPoForm]      = useState({
    supplier: \'\', quantity: 1, unit_cost: \'\', expected_date: \'\', notes: \'\',
  });
  const [activeSection, setSection]   = useState(\'notes\'); // notes | create_po | resolve
  const [resolveNote,   setResolveNote] = useState(\'\');
  const [toast,         setToast]      = useState(null);
  const notify = (msg, type=\'success\') => { setToast({msg,type}); setTimeout(()=>setToast(null),4000); };

  const reload = async () => {
    try {
      const r = await inventoryAPI.getAlert(alert.id);
      setAlert(r.data);
      onUpdated();
    } catch {/* */}
  };

  // ── إضافة ملاحظة ────────────────────────────────────
  const handleAddNote = async () => {
    if (!noteForm.text.trim()) { notify(\'اكتب النص أولاً\', \'error\'); return; }
    setLoading(true);
    try {
      await inventoryAPI.addAlertNote(alert.id, {
        note_type:     noteForm.note_type,
        text:          noteForm.text,
        cost:          noteForm.cost          || null,
        expected_date: noteForm.expected_date || null,
        delay_reason:  noteForm.delay_reason  || \'\',
        supplier_name: noteForm.supplier_name || \'\',
      });
      notify(\'✅ تم إضافة الملاحظة\');
      setNoteForm({ note_type:\'note\', text:\'\', cost:\'\', expected_date:\'\', delay_reason:\'\', supplier_name:\'\' });
      reload();
    } catch(e) {
      notify(\'❌ \' + (e?.response?.data?.error || \'خطأ\'), \'error\');
    } finally { setLoading(false); }
  };

  // ── إنشاء أمر شراء ──────────────────────────────────
  const handleCreatePO = async () => {
    if (!poForm.quantity || !poForm.unit_cost) {
      notify(\'أدخل الكمية والتكلفة\', \'error\'); return;
    }
    setLoading(true);
    try {
      const r = await inventoryAPI.createPoFromAlert(alert.id, {
        supplier:      poForm.supplier      || null,
        quantity:      Number(poForm.quantity),
        unit_cost:     Number(poForm.unit_cost),
        expected_date: poForm.expected_date || null,
        notes:         poForm.notes         || \'\',
      });
      notify(\'✅ تم إنشاء أمر الشراء: \' + r.data.purchase_order.reference_number);
      setSection(\'notes\');
      reload();
    } catch(e) {
      notify(\'❌ \' + (e?.response?.data?.error || \'خطأ\'), \'error\');
    } finally { setLoading(false); }
  };

  // ── حل التذكرة ──────────────────────────────────────
  const handleResolve = async () => {
    setLoading(true);
    try {
      await inventoryAPI.resolveAlert(alert.id, { note: resolveNote });
      notify(\'✅ تم حل التذكرة\');
      reload();
      setTimeout(onClose, 1500);
    } catch(e) {
      notify(\'❌ \' + (e?.response?.data?.error || \'خطأ\'), \'error\');
    } finally { setLoading(false); }
  };

  const pr = priorityConfig[alert.priority]          || priorityConfig.medium;
  const st = ticketStatusConfig[alert.ticket_status] || ticketStatusConfig.open;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-3" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[92vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {toast && (
          <div className={`absolute top-4 left-1/2 -translate-x-1/2 z-10 px-5 py-3 rounded-2xl shadow-xl font-bold text-sm
            ${toast.type===\'error\'?\'bg-red-600 text-white\':\'bg-green-600 text-white\'}`}>
            {toast.msg}
          </div>
        )}

        {/* ── رأس التذكرة ── */}
        <div className="px-5 py-4 border-b flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`w-3 h-3 rounded-full ${pr.dot}`}></span>
              <h2 className="font-black text-gray-800 text-lg">{alert.product_name}</h2>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${st.color}`}>{st.label}</span>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${pr.color}`}>{pr.label}</span>
            </div>
            <div className="flex flex-wrap gap-3 mt-2 text-sm text-gray-500">
              <span>📦 باركود: <strong>{alert.product_barcode || \'—\'}</strong></span>
              <span>📊 المخزون الحالي: <strong className="text-red-600">{alert.product_current_stock ?? alert.current_stock}</strong></span>
              <span>🎯 الحد: <strong>{alert.threshold}</strong></span>
              {alert.linked_po_reference && (
                <span className="text-blue-600 font-bold">
                  🔗 PO: {alert.linked_po_reference}
                  <span className={`mr-1 text-xs px-1.5 py-0.5 rounded ${
                    alert.linked_po_status===\'received\'?\'bg-green-100 text-green-700\':\'bg-blue-100 text-blue-700\'
                  }`}>{alert.linked_po_status}</span>
                </span>
              )}
              {alert.deadline && (
                <span className={new Date(alert.deadline)<new Date()&&!alert.is_resolved?\'text-red-600 font-bold\':\'\'}>
                  ⏰ الموعد النهائي: {alert.deadline}
                </span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-black flex-shrink-0">✕</button>
        </div>

        {/* ── محتوى التذكرة ── */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">

          {/* ── Timeline الملاحظات ── */}
          <div>
            <h3 className="font-bold text-gray-700 text-sm mb-3 flex items-center gap-2">
              💬 سجل التذكرة
              <span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full font-bold">
                {alert.notes?.length || 0}
              </span>
            </h3>
            {(!alert.notes || alert.notes.length === 0) && (
              <div className="text-center py-6 text-gray-400 bg-gray-50 rounded-xl border border-dashed border-gray-200">
                <p className="text-2xl mb-1">📭</p>
                <p className="text-sm">لا توجد ملاحظات بعد — ابدأ بإضافة أول ملاحظة</p>
              </div>
            )}
            <div className="space-y-2">
              {(alert.notes || []).map(note => {
                const nc = noteTypeConfig[note.note_type] || noteTypeConfig.note;
                return (
                  <div key={note.id} className={`rounded-xl border p-3 ${nc.color}`}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-base">{nc.icon}</span>
                        <span className="text-xs font-bold text-gray-600">{nc.label}</span>
                        <span className="text-xs text-gray-400">— {note.user_name || \'النظام\'}</span>
                      </div>
                      <span className="text-xs text-gray-400">{note.created_at?.split(\'T\')[0]}</span>
                    </div>
                    <p className="text-sm text-gray-700 font-medium">{note.text}</p>
                    {note.cost && (
                      <p className="text-xs text-green-700 font-bold mt-1">💵 التكلفة: {Number(note.cost).toFixed(2)} ج</p>
                    )}
                    {note.expected_date && (
                      <p className="text-xs text-blue-700 font-bold mt-1">📅 تاريخ الاستلام: {note.expected_date}</p>
                    )}
                    {note.delay_reason && (
                      <p className="text-xs text-orange-700 mt-1">⏰ سبب التأخير: {note.delay_reason}</p>
                    )}
                    {note.supplier_name && (
                      <p className="text-xs text-purple-700 mt-1">🏭 المورد: {note.supplier_name}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* ── اختيار الإجراء ── */}
          {!alert.is_resolved && (
            <div>
              <div className="flex gap-2 flex-wrap mb-3">
                {[
                  { key:\'notes\',     label:\'💬 إضافة ملاحظة\' },
                  { key:\'create_po\', label:\'📦 إنشاء أمر شراء\', disabled: !!alert.linked_po },
                  { key:\'resolve\',   label:\'✅ حل التذكرة\'     },
                ].map(s => (
                  <button
                    key={s.key}
                    onClick={() => !s.disabled && setSection(s.key)}
                    disabled={s.disabled}
                    className={`px-3 py-1.5 rounded-xl text-sm font-bold transition
                      ${s.disabled ? \'bg-gray-100 text-gray-400 cursor-not-allowed\' :
                        activeSection===s.key ? \'bg-blue-600 text-white shadow\' :
                        \'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50\'}`}>
                    {s.label}
                    {s.key===\'create_po\' && alert.linked_po && <span className="mr-1 text-xs opacity-70">(مرتبط)</span>}
                  </button>
                ))}
              </div>

              {/* ── فورم الملاحظة ── */}
              {activeSection === \'notes\' && (
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-bold text-gray-500 block mb-1">نوع الملاحظة</label>
                      <select className={INP} value={noteForm.note_type}
                        onChange={e=>setNoteForm({...noteForm,note_type:e.target.value})}>
                        <option value="note">📝 ملاحظة عامة</option>
                        <option value="quote">💰 عرض سعر</option>
                        <option value="action">⚡ إجراء مُتخذ</option>
                        <option value="delay">⏰ سبب تأخير</option>
                      </select>
                    </div>
                    {noteForm.note_type === \'quote\' && (
                      <div>
                        <label className="text-xs font-bold text-gray-500 block mb-1">التكلفة / السعر</label>
                        <input type="number" step="0.01" className={INP} placeholder="0.00"
                          value={noteForm.cost} onChange={e=>setNoteForm({...noteForm,cost:e.target.value})} />
                      </div>
                    )}
                    {(noteForm.note_type === \'quote\' || noteForm.note_type === \'action\') && (
                      <div>
                        <label className="text-xs font-bold text-gray-500 block mb-1">تاريخ الاستلام المتوقع</label>
                        <input type="date" className={INP}
                          value={noteForm.expected_date}
                          onChange={e=>setNoteForm({...noteForm,expected_date:e.target.value})} />
                      </div>
                    )}
                    {noteForm.note_type === \'quote\' && (
                      <div>
                        <label className="text-xs font-bold text-gray-500 block mb-1">اسم المورد</label>
                        <input type="text" className={INP} placeholder="اسم المورد"
                          value={noteForm.supplier_name}
                          onChange={e=>setNoteForm({...noteForm,supplier_name:e.target.value})} />
                      </div>
                    )}
                    {noteForm.note_type === \'delay\' && (
                      <div className="col-span-2">
                        <label className="text-xs font-bold text-gray-500 block mb-1">سبب التأخير</label>
                        <input type="text" className={INP} placeholder="اذكر سبب التأخير..."
                          value={noteForm.delay_reason}
                          onChange={e=>setNoteForm({...noteForm,delay_reason:e.target.value})} />
                      </div>
                    )}
                  </div>
                  <div>
                    <label className="text-xs font-bold text-gray-500 block mb-1">النص <span className="text-red-500">*</span></label>
                    <textarea rows={3} className={INP+\' resize-none\'} placeholder="اكتب ملاحظتك هنا..."
                      value={noteForm.text}
                      onChange={e=>setNoteForm({...noteForm,text:e.target.value})} />
                  </div>
                  <button onClick={handleAddNote} disabled={loading}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-4 py-2 rounded-xl text-sm disabled:opacity-50 transition">
                    {loading ? \'...\' : \'إضافة الملاحظة\'}
                  </button>
                </div>
              )}

              {/* ── فورم إنشاء أمر الشراء ── */}
              {activeSection === \'create_po\' && !alert.linked_po && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-3">
                  <h4 className="font-bold text-blue-800 text-sm">📦 إنشاء أمر شراء لـ: {alert.product_name}</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-bold text-gray-500 block mb-1">المورد</label>
                      <select className={INP} value={poForm.supplier}
                        onChange={e=>setPoForm({...poForm,supplier:e.target.value})}>
                        <option value="">— بدون مورد —</option>
                        {suppliers.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-bold text-gray-500 block mb-1">الكمية المطلوبة <span className="text-red-500">*</span></label>
                      <input type="number" min={1} className={INP}
                        value={poForm.quantity}
                        onChange={e=>setPoForm({...poForm,quantity:e.target.value})} />
                    </div>
                    <div>
                      <label className="text-xs font-bold text-gray-500 block mb-1">تكلفة الوحدة <span className="text-red-500">*</span></label>
                      <input type="number" step="0.01" min={0} className={INP} placeholder="0.00"
                        value={poForm.unit_cost}
                        onChange={e=>setPoForm({...poForm,unit_cost:e.target.value})} />
                    </div>
                    <div>
                      <label className="text-xs font-bold text-gray-500 block mb-1">تاريخ الاستلام المتوقع</label>
                      <input type="date" className={INP}
                        value={poForm.expected_date}
                        onChange={e=>setPoForm({...poForm,expected_date:e.target.value})} />
                    </div>
                    <div className="col-span-2">
                      <label className="text-xs font-bold text-gray-500 block mb-1">ملاحظات</label>
                      <input type="text" className={INP} placeholder="ملاحظات اختيارية..."
                        value={poForm.notes}
                        onChange={e=>setPoForm({...poForm,notes:e.target.value})} />
                    </div>
                  </div>
                  <button onClick={handleCreatePO} disabled={loading}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-4 py-2 rounded-xl text-sm disabled:opacity-50 transition">
                    {loading ? \'...\' : \'إنشاء أمر الشراء وربطه بالتذكرة\'}
                  </button>
                </div>
              )}

              {/* ── فورم الحل ── */}
              {activeSection === \'resolve\' && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-3">
                  <h4 className="font-bold text-green-800 text-sm">✅ حل التذكرة</h4>
                  {alert.linked_po && alert.linked_po_status !== \'received\' && (
                    <div className="bg-orange-50 border border-orange-200 rounded-xl p-3 text-sm text-orange-700 font-bold">
                      ⚠️ أمر الشراء #{alert.linked_po_reference} لم يُستلم بعد.
                      استلم البضاعة أولاً من تبويب أوامر الشراء.
                    </div>
                  )}
                  <div>
                    <label className="text-xs font-bold text-gray-500 block mb-1">ملاحظة الحل (اختياري)</label>
                    <textarea rows={2} className={INP+\' resize-none\'} placeholder="سبب الحل أو ملاحظة ختامية..."
                      value={resolveNote} onChange={e=>setResolveNote(e.target.value)} />
                  </div>
                  <button
                    onClick={handleResolve}
                    disabled={loading || (alert.linked_po && alert.linked_po_status !== \'received\')}
                    className="bg-green-600 hover:bg-green-700 text-white font-bold px-4 py-2 rounded-xl text-sm disabled:opacity-50 transition">
                    {loading ? \'...\' : \'تأكيد الحل\'}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* رسالة للتذكرة المحلولة */}
          {alert.is_resolved && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
              <div className="text-3xl mb-1">✅</div>
              <p className="font-bold text-green-700">تم حل هذه التذكرة</p>
              {alert.resolved_at && (
                <p className="text-xs text-green-600 mt-1">{alert.resolved_at?.split(\'T\')[0]}</p>
              )}
            </div>
          )}
        </div>

        {/* ── footer ── */}
        <div className="px-5 py-3 border-t bg-gray-50 flex justify-end">
          <button onClick={onClose}
            className="px-4 py-2 rounded-xl border border-gray-200 font-bold text-sm text-gray-600 hover:bg-gray-100 transition">
            إغلاق
          </button>
        </div>
      </div>
    </div>
  );
}

// ── AlertsPanel الرئيسي ───────────────────────────────
function AlertsPanel() {
  const [alerts,    setAlerts]    = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [filter,    setFilter]    = useState(\'active\');
  const [priority,  setPriority]  = useState(\'\');
  const [selected,  setSelected]  = useState(null);
  const [toast,     setToast]     = useState(null);
  const notify = (msg, type=\'success\') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filter === \'active\')   params.is_resolved = \'false\';
      if (filter === \'resolved\') params.is_resolved = \'true\';
      if (priority) params.priority = priority;
      const [ar, sr] = await Promise.all([
        inventoryAPI.getAlerts(params),
        inventoryAPI.getSuppliers(),
      ]);
      setAlerts(ar.data?.results || ar.data || []);
      setSuppliers(sr.data?.results || sr.data || []);
    } catch {/* */} finally { setLoading(false); }
  }, [filter, priority]);

  useEffect(() => { load(); }, [load]);

  const stats = {
    total:    alerts.length,
    critical: alerts.filter(a => a.priority === \'critical\').length,
    high:     alerts.filter(a => a.priority === \'high\').length,
    ordered:  alerts.filter(a => a.ticket_status === \'ordered\').length,
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-5">
      {toast && <Toast msg={toast.msg} type={toast.type} />}

      {/* ── Stats ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label:\'إجمالي التنبيهات\', value: stats.total,    color:\'bg-gray-100   text-gray-700\',   icon:\'🔔\' },
          { label:\'حرجة\',             value: stats.critical, color:\'bg-red-100    text-red-700\',    icon:\'🚨\' },
          { label:\'عالية الأولوية\',   value: stats.high,     color:\'bg-orange-100 text-orange-700\', icon:\'⚠️\' },
          { label:\'قيد الطلب\',        value: stats.ordered,  color:\'bg-blue-100   text-blue-700\',   icon:\'📦\' },
        ].map(s => (
          <div key={s.label} className={`rounded-2xl p-4 ${s.color}`}>
            <div className="text-2xl mb-1">{s.icon}</div>
            <div className="text-2xl font-black">{s.value}</div>
            <div className="text-xs font-semibold mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── الفلاتر ── */}
      <div className="flex flex-wrap gap-2 items-center">
        <div className="flex gap-2">
          {[\'all\',\'active\',\'resolved\'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-xl text-sm font-bold ${
                filter===f?\'bg-blue-600 text-white shadow\':\'bg-white border text-gray-600 hover:bg-gray-50\'}`}>
              {f===\'all\'?\'الكل\':f===\'active\'?\'🔔 نشطة\':\'✅ محلولة\'}
            </button>
          ))}
        </div>
        <select className={INP+\' w-36\'} value={priority} onChange={e=>setPriority(e.target.value)}>
          <option value="">كل الأولويات</option>
          <option value="critical">🚨 حرجة</option>
          <option value="high">⚠️ عالية</option>
          <option value="medium">🔵 متوسطة</option>
          <option value="low">⬇️ منخفضة</option>
        </select>
        <button onClick={async () => {
          try {
            const r = await inventoryAPI.checkAndGenerateAlerts({ threshold:10 });
            notify(`تم إنشاء ${r.data.created_alerts} تنبيه جديد`);
            load();
          } catch { notify(\'خطأ في توليد التنبيهات\',\'error\'); }
        }} className="bg-yellow-500 hover:bg-yellow-600 text-white font-bold px-3 py-1.5 rounded-xl text-sm transition">
          🔄 فحص وتحديث
        </button>
      </div>

      {/* ── شبكة التذاكر ── */}
      {alerts.length === 0 ? (
        <div className="text-center py-16 text-gray-400 bg-white rounded-2xl border">
          <div className="text-5xl mb-3">🎉</div>
          <p className="font-bold text-lg">لا توجد تنبيهات {filter===\'active\'?\'نشطة\':\'\'}!</p>
          <p className="text-sm mt-1">المخزون في حالة جيدة</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {alerts.map(a => (
            <AlertCard key={a.id} alert={a} onOpen={setSelected} />
          ))}
        </div>
      )}

      {/* ── التذكرة الكاملة ── */}
      {selected && (
        <AlertTicketModal
          alert={selected}
          suppliers={suppliers}
          onClose={() => setSelected(null)}
          onUpdated={() => { load(); }}
        />
      )}
    </div>
  );
}'''

# إيجاد واستبدال AlertsPanel القديم
OLD_ALERTS_PANEL_START = '// Alerts\nfunction AlertsPanel() {'
OLD_ALERTS_PANEL_END   = "// Suppliers\nfunction SuppliersPanel() {"

start_idx = inv_src.find(OLD_ALERTS_PANEL_START)
end_idx   = inv_src.find(OLD_ALERTS_PANEL_END)

if start_idx == -1 or end_idx == -1:
    print('⚠️  لم يُعثر على AlertsPanel — جرّب البحث عن النص يدوياً')
    sys.exit(1)

inv_src = (
    inv_src[:start_idx]
    + NEW_ALERTS_PANEL
    + '\n\n'
    + inv_src[end_idx:]
)

with open(INV_PAGE, 'w', encoding='utf-8') as f:
    f.write(inv_src)
print('✅  InventoryPage.jsx — تم استبدال AlertsPanel')

# ─── CHANGELOG ────────────────────────────────────────────────────────────
changelog = os.path.join(BASE, 'CHANGELOG.md')
entry = f"""
## [{datetime.now().strftime('%Y-%m-%d')}] fix_03b_alert_ticket_frontend
### التغييرات
- **api.js**: أضيف getAlert, addAlertNote, createPoFromAlert, updateAlertMeta
- **InventoryPage.jsx**:
  - AlertCard: بطاقة تذكرة مع أولوية وحالة ومخزون وملاحظات
  - AlertTicketModal: تذكرة كاملة مع timeline + فورم ملاحظة
    + إنشاء PO + حل التذكرة
  - AlertsPanel: شبكة بطاقات مع فلاتر وإحصائيات
"""
with open(changelog, 'a', encoding='utf-8') as f:
    f.write(entry)
print('✅  CHANGELOG.md تم التحديث')

print()
print('─' * 60)
print('✅  fix_03b مكتمل!')
print()
print('   افتح المتصفح → صفحة المخزون → تبويب التنبيهات')
print('   اضغط على أي تذكرة لتفتح وتشوف الـ Ticket System')
print('─' * 60)
