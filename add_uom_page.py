# fix_add_uom_page.py
"""
ينشئ صفحة UnitsOfMeasure.jsx كاملة + seed الـ UI route/menu/action
"""
import os, shutil, datetime

BASE     = "/home/momar/Projects/POS_DEV/posv1_dev10"
FRONTEND = os.path.join(BASE, "pos_frontend/src")
BACKEND  = os.path.join(BASE, "pos_backend")
CHLOG    = os.path.join(BASE, "CHANGELOG.md")

def backup(path):
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
        print(f"  ✅ Backup: {path}.bak")

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ Written: {path}")

def update_changelog(entry):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(CHLOG, "a", encoding="utf-8") as f:
        f.write(f"\n## [{ts}] fix_add_uom_page\n{entry}\n")

# ══════════════════════════════════════════════════════════════════════════════
# FILE 1 — UnitsOfMeasure.jsx
# ══════════════════════════════════════════════════════════════════════════════
UOM_JSX = r"""
import { useState, useEffect, useCallback, useMemo } from 'react';
import { unitsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

// ─── ثوابت ────────────────────────────────────────────────────────────────
const CATEGORY_OPTIONS = [
  { value: 'count',  label: 'عدد',  icon: 'fa-hashtag',     color: 'blue'   },
  { value: 'weight', label: 'وزن',  icon: 'fa-weight-hanging', color: 'green' },
  { value: 'volume', label: 'حجم',  icon: 'fa-flask',       color: 'purple' },
  { value: 'length', label: 'طول',  icon: 'fa-ruler',       color: 'orange' },
  { value: 'other',  label: 'أخرى', icon: 'fa-shapes',      color: 'gray'   },
];

const CATEGORY_COLOR = {
  count:  'bg-blue-100 text-blue-700',
  weight: 'bg-green-100 text-green-700',
  volume: 'bg-purple-100 text-purple-700',
  length: 'bg-orange-100 text-orange-700',
  other:  'bg-gray-100 text-gray-600',
};

const EMPTY_FORM = {
  name: '', symbol: '', factor: '1',
  category: 'count', is_base: false, is_active: true,
};

// ─── Toast ────────────────────────────────────────────────────────────────
const useToast = () => {
  const [toasts, setToasts] = useState([]);
  const push = (type, text) => {
    const id = Date.now() + Math.random();
    setToasts(p => [...p, { id, type, text }]);
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 3500);
  };
  const Toast = () => (
    <div className="fixed bottom-5 left-5 z-[9999] flex flex-col gap-2 max-w-sm">
      {toasts.map(t => (
        <div key={t.id} className={`px-4 py-3 rounded-xl shadow-lg font-bold text-sm border
          ${t.type==='success'?'bg-green-50 text-green-800 border-green-200':''}
          ${t.type==='error'  ?'bg-red-50   text-red-800   border-red-200'  :''}
          ${t.type==='warning'?'bg-yellow-50 text-yellow-800 border-yellow-200':''}
          ${t.type==='info'   ?'bg-blue-50  text-blue-800  border-blue-200' :''}`}>
          {t.text}
        </div>
      ))}
    </div>
  );
  return { push, Toast };
};

// ─── Confirm Modal ────────────────────────────────────────────────────────
const ConfirmModal = ({ open, title, message, onConfirm, onCancel }) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-2">{title}</h3>
        <p className="text-gray-600 text-sm mb-6">{message}</p>
        <div className="flex gap-3">
          <button onClick={onConfirm}
            className="flex-1 py-2 rounded-xl font-bold text-white bg-red-600 hover:bg-red-700 transition">
            تأكيد الحذف
          </button>
          <button onClick={onCancel}
            className="flex-1 py-2 rounded-xl font-bold bg-gray-100 text-gray-700 hover:bg-gray-200 transition">
            إلغاء
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── UOM Modal ────────────────────────────────────────────────────────────
const UomModal = ({ open, unit, onClose, onSaved, toast }) => {
  const [form,   setForm]   = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(unit ? {
      name:      unit.name      || '',
      symbol:    unit.symbol    || '',
      factor:    unit.factor    ?? '1',
      category:  unit.category  || 'count',
      is_base:   unit.is_base   ?? false,
      is_active: unit.is_active ?? true,
    } : EMPTY_FORM);
  }, [open, unit]);

  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  // حساب مثال التحويل
  const convExample = useMemo(() => {
    const f = parseFloat(form.factor) || 1;
    if (f === 1) return null;
    return `1 ${form.name || 'وحدة'} = ${f} وحدة أساسية`;
  }, [form.factor, form.name]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim())                    return toast('error', '❌ اسم الوحدة مطلوب');
    if (parseFloat(form.factor) <= 0)         return toast('error', '❌ المعامل يجب أن يكون أكبر من صفر');
    setSaving(true);
    try {
      if (unit) {
        await unitsAPI.update(unit.id, form);
        toast('success', '✅ تم تحديث الوحدة بنجاح');
      } else {
        await unitsAPI.create(form);
        toast('success', '✅ تم إضافة الوحدة بنجاح');
      }
      onSaved();
      onClose();
    } catch (err) {
      const msg = err.response?.data
        ? Object.values(err.response.data).flat().join(' — ')
        : 'حدث خطأ أثناء الحفظ';
      toast('error', `❌ ${msg}`);
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  const INP = 'w-full border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition bg-white';

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md animate-fadeIn">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-xl font-bold text-gray-800">
            <i className={`fas ${unit ? 'fa-edit' : 'fa-plus-circle'} ml-2 text-blue-600`}></i>
            {unit ? 'تعديل وحدة قياس' : 'إضافة وحدة قياس جديدة'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">

          {/* الاسم + الرمز */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-gray-500 mb-1">
                اسم الوحدة <span className="text-red-500">*</span>
              </label>
              <input type="text" required className={INP}
                value={form.name} onChange={e => set('name', e.target.value)}
                placeholder="مثال: قطعة، كيلو، كرتون"/>
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-500 mb-1">الرمز</label>
              <input type="text" className={INP}
                value={form.symbol} onChange={e => set('symbol', e.target.value)}
                placeholder="مثال: pcs، kg، ctn"/>
            </div>
          </div>

          {/* التصنيف */}
          <div>
            <label className="block text-xs font-bold text-gray-500 mb-2">تصنيف الوحدة</label>
            <div className="grid grid-cols-5 gap-2">
              {CATEGORY_OPTIONS.map(opt => (
                <button key={opt.value} type="button"
                  onClick={() => set('category', opt.value)}
                  className={`flex flex-col items-center gap-1 py-2 px-1 rounded-xl border-2 text-xs font-bold transition
                    ${form.category === opt.value
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}>
                  <i className={`fas ${opt.icon} text-base`}></i>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* معامل التحويل */}
          <div>
            <label className="block text-xs font-bold text-gray-500 mb-1">
              معامل التحويل
              <span className="text-gray-400 font-normal mr-1">
                (كم وحدة أساسية = هذه الوحدة)
              </span>
            </label>
            <input type="number" step="0.0001" min="0.0001" className={INP}
              value={form.factor} onChange={e => set('factor', e.target.value)}
              placeholder="1"/>
            {convExample && (
              <p className="mt-1 text-xs text-blue-600 font-bold bg-blue-50 rounded-lg px-3 py-1.5">
                <i className="fas fa-info-circle ml-1"></i>{convExample}
              </p>
            )}
            {/* أمثلة سريعة */}
            <div className="flex flex-wrap gap-2 mt-2">
              {[
                { label:'قطعة ×1',   val:'1'  },
                { label:'دستة ×12',  val:'12' },
                { label:'كرتون ×24', val:'24' },
                { label:'كيلو ×1',   val:'1'  },
                { label:'طن ×1000',  val:'1000'},
              ].map(ex => (
                <button key={ex.label} type="button"
                  onClick={() => set('factor', ex.val)}
                  className="text-xs px-2 py-1 rounded-lg bg-gray-100 text-gray-600 hover:bg-blue-100 hover:text-blue-700 font-bold transition">
                  {ex.label}
                </button>
              ))}
            </div>
          </div>

          {/* وحدة أساسية + نشطة */}
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.is_base}
                onChange={e => set('is_base', e.target.checked)}
                className="w-4 h-4 accent-blue-600"/>
              <span className="text-sm font-bold text-gray-700">وحدة أساسية</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.is_active}
                onChange={e => set('is_active', e.target.checked)}
                className="w-4 h-4 accent-green-600"/>
              <span className="text-sm font-bold text-gray-700">نشطة</span>
            </label>
          </div>

          {/* Footer */}
          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={saving}
              className="flex-1 py-2.5 rounded-xl font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 transition flex items-center justify-center gap-2">
              {saving
                ? <><i className="fas fa-circle-notch fa-spin"></i> جاري الحفظ...</>
                : <><i className="fas fa-save"></i> حفظ الوحدة</>
              }
            </button>
            <button type="button" onClick={onClose} disabled={saving}
              className="flex-1 py-2.5 rounded-xl font-bold bg-gray-100 text-gray-700 hover:bg-gray-200 transition">
              إلغاء
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  UnitsOfMeasure — Main Component
// ══════════════════════════════════════════════════════════════════════════════
const UnitsOfMeasure = () => {
  const PAGE_KEY = 'units.list';
  const { hasAction } = useAuth();
  const canAdd    = hasAction(PAGE_KEY, 'units.add');
  const canDelete = hasAction(PAGE_KEY, 'units.delete');

  const { push: toast, Toast } = useToast();

  const [units,       setUnits]       = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCat,   setFilterCat]   = useState('');
  const [filterActive,setFilterActive]= useState('true');
  const [showModal,   setShowModal]   = useState(false);
  const [editing,     setEditing]     = useState(null);
  const [confirm,     setConfirm]     = useState({ open: false });

  // ── Fetch ──────────────────────────────────────────────────────────────
  const fetchUnits = useCallback(async () => {
    try {
      setLoading(true);
      const params = { page_size: 200 };
      if (searchQuery) params.search   = searchQuery;
      const res = await unitsAPI.getAll(params);
      setUnits(res.data?.results ?? res.data);
    } catch {
      toast('error', '❌ تعذّر تحميل وحدات القياس');
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  useEffect(() => { fetchUnits(); }, [fetchUnits]);

  // ── Delete ─────────────────────────────────────────────────────────────
  const handleDelete = (unit) => {
    setConfirm({
      open: true,
      title: 'حذف وحدة قياس',
      message: `هل أنت متأكد من حذف "${unit.name}"؟ لو مرتبطة بمنتجات هيتأثر عليهم.`,
      onConfirm: async () => {
        setConfirm({ open: false });
        try {
          await unitsAPI.delete(unit.id);
          toast('success', `✅ تم حذف "${unit.name}"`);
          fetchUnits();
        } catch (err) {
          const msg = err.response?.data?.detail || 'لا يمكن الحذف — الوحدة مرتبطة بمنتجات';
          toast('error', `❌ ${msg}`);
        }
      },
      onCancel: () => setConfirm({ open: false }),
    });
  };

  // ── Toggle Active ──────────────────────────────────────────────────────
  const handleToggleActive = async (unit) => {
    try {
      await unitsAPI.update(unit.id, { ...unit, is_active: !unit.is_active });
      toast('success', `✅ تم ${unit.is_active ? 'تعطيل' : 'تفعيل'} "${unit.name}"`);
      fetchUnits();
    } catch {
      toast('error', '❌ خطأ في تحديث الحالة');
    }
  };

  // ── Filtered + Stats ───────────────────────────────────────────────────
  const filtered = useMemo(() => {
    return units.filter(u => {
      if (filterCat    && u.category  !== filterCat)          return false;
      if (filterActive === 'true'  && !u.is_active)           return false;
      if (filterActive === 'false' &&  u.is_active)           return false;
      if (searchQuery  && !u.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    });
  }, [units, filterCat, filterActive, searchQuery]);

  const stats = useMemo(() => ({
    total:   units.length,
    active:  units.filter(u => u.is_active).length,
    base:    units.filter(u => u.is_base).length,
    byCategory: CATEGORY_OPTIONS.map(c => ({
      ...c,
      count: units.filter(u => u.category === c.value).length,
    })),
  }), [units]);

  // ─── Render ────────────────────────────────────────────────────────────
  return (
    <div className="p-6 bg-gray-100 min-h-screen" dir="rtl">
      <Toast />
      <ConfirmModal {...confirm} />
      <UomModal
        open={showModal}
        unit={editing}
        onClose={() => { setShowModal(false); setEditing(null); }}
        onSaved={fetchUnits}
        toast={toast}
      />

      {/* Header */}
      <div className="flex justify-between items-center mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">
            <i className="fas fa-ruler ml-2 text-blue-600"></i>وحدات القياس
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            قطعة · دستة · كرتون · كيلو · لتر — وأي وحدة تحتاجها
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchUnits} disabled={loading}
            className="px-4 py-2 rounded-xl border border-gray-200 bg-white font-bold text-gray-600 hover:bg-gray-50 transition flex items-center gap-2">
            <i className={`fas fa-sync-alt ${loading ? 'fa-spin' : ''}`}></i> تحديث
          </button>
          {canAdd && (
            <button onClick={() => { setEditing(null); setShowModal(true); }}
              className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold transition flex items-center gap-2">
              <i className="fas fa-plus"></i> إضافة وحدة
            </button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl p-4 shadow">
          <p className="text-white/80 text-sm mb-1">إجمالي الوحدات</p>
          <p className="text-3xl font-bold">{stats.total}</p>
        </div>
        <div className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-2xl p-4 shadow">
          <p className="text-white/80 text-sm mb-1">الوحدات النشطة</p>
          <p className="text-3xl font-bold">{stats.active}</p>
        </div>
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-2xl p-4 shadow">
          <p className="text-white/80 text-sm mb-1">وحدات أساسية</p>
          <p className="text-3xl font-bold">{stats.base}</p>
        </div>
        <div className="bg-white rounded-2xl p-4 shadow border border-gray-100">
          <p className="text-gray-500 text-sm mb-2 font-bold">توزيع التصنيفات</p>
          <div className="flex flex-wrap gap-1">
            {stats.byCategory.filter(c => c.count > 0).map(c => (
              <span key={c.value} className={`px-2 py-0.5 rounded-full text-xs font-bold ${CATEGORY_COLOR[c.value]}`}>
                {c.label} ({c.count})
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl shadow p-4 mb-5 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs font-bold text-gray-500 block mb-1">بحث</label>
          <div className="relative">
            <i className="fas fa-search absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
            <input type="text" placeholder="اسم الوحدة أو الرمز..."
              className="w-full border border-gray-200 rounded-xl px-3 py-2 pr-9 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition"
              value={searchQuery} onChange={e => setSearchQuery(e.target.value)}/>
          </div>
        </div>
        <div className="min-w-[150px]">
          <label className="text-xs font-bold text-gray-500 block mb-1">التصنيف</label>
          <select className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-500 transition bg-white"
            value={filterCat} onChange={e => setFilterCat(e.target.value)}>
            <option value="">كل التصنيفات</option>
            {CATEGORY_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>
        <div className="min-w-[130px]">
          <label className="text-xs font-bold text-gray-500 block mb-1">الحالة</label>
          <select className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-500 transition bg-white"
            value={filterActive} onChange={e => setFilterActive(e.target.value)}>
            <option value="">الكل</option>
            <option value="true">نشطة فقط</option>
            <option value="false">معطّلة فقط</option>
          </select>
        </div>
        {(searchQuery || filterCat || filterActive !== 'true') && (
          <button onClick={() => { setSearchQuery(''); setFilterCat(''); setFilterActive('true'); }}
            className="text-sm text-gray-500 hover:text-red-600 font-bold transition flex items-center gap-1 mt-5">
            <i className="fas fa-times-circle"></i> مسح الفلاتر
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl shadow overflow-hidden">
        <div className="px-5 py-3 border-b bg-gray-50 flex items-center justify-between">
          <span className="font-bold text-gray-700">
            <i className="fas fa-list ml-2 text-gray-400"></i>
            {filtered.length} وحدة
          </span>
        </div>

        {loading ? (
          <div className="py-16 flex items-center justify-center">
            <i className="fas fa-spinner fa-spin text-4xl text-blue-500"></i>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center">
            <i className="fas fa-ruler text-6xl text-gray-300 mb-4 block"></i>
            <p className="text-gray-500 font-semibold text-lg">لا توجد وحدات</p>
            {canAdd && (
              <button onClick={() => { setEditing(null); setShowModal(true); }}
                className="mt-4 px-6 py-2 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition">
                إضافة أول وحدة
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b">
                  <th className="px-5 py-3 text-right text-sm font-bold text-gray-600">الوحدة</th>
                  <th className="px-5 py-3 text-right text-sm font-bold text-gray-600">الرمز</th>
                  <th className="px-5 py-3 text-right text-sm font-bold text-gray-600">التصنيف</th>
                  <th className="px-5 py-3 text-center text-sm font-bold text-gray-600">المعامل</th>
                  <th className="px-5 py-3 text-center text-sm font-bold text-gray-600">أساسية</th>
                  <th className="px-5 py-3 text-center text-sm font-bold text-gray-600">الحالة</th>
                  <th className="px-5 py-3 text-center text-sm font-bold text-gray-600">الإجراءات</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(unit => (
                  <tr key={unit.id} className={`border-b transition hover:bg-gray-50 ${!unit.is_active ? 'opacity-60' : ''}`}>

                    {/* الوحدة */}
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold ${CATEGORY_COLOR[unit.category] || 'bg-gray-100 text-gray-600'}`}>
                          <i className={`fas ${CATEGORY_OPTIONS.find(c=>c.value===unit.category)?.icon || 'fa-shapes'}`}></i>
                        </div>
                        <div>
                          <p className="font-bold text-gray-800">{unit.name}</p>
                          {unit.is_base && (
                            <span className="text-xs text-green-600 font-bold">
                              <i className="fas fa-star ml-1"></i>وحدة أساسية
                            </span>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* الرمز */}
                    <td className="px-5 py-3">
                      {unit.symbol ? (
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded-lg text-sm font-mono font-bold">
                          {unit.symbol}
                        </span>
                      ) : <span className="text-gray-400 text-sm">—</span>}
                    </td>

                    {/* التصنيف */}
                    <td className="px-5 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-bold ${CATEGORY_COLOR[unit.category]}`}>
                        {CATEGORY_OPTIONS.find(c => c.value === unit.category)?.label || unit.category}
                      </span>
                    </td>

                    {/* المعامل */}
                    <td className="px-5 py-3 text-center">
                      <span className={`px-3 py-1 rounded-xl text-sm font-bold font-mono
                        ${parseFloat(unit.factor)===1 ? 'bg-gray-100 text-gray-600' : 'bg-blue-50 text-blue-700'}`}>
                        × {parseFloat(unit.factor) % 1 === 0
                           ? parseInt(unit.factor)
                           : parseFloat(unit.factor).toFixed(2)}
                      </span>
                    </td>

                    {/* أساسية */}
                    <td className="px-5 py-3 text-center">
                      {unit.is_base
                        ? <i className="fas fa-check-circle text-green-500 text-lg"></i>
                        : <i className="fas fa-circle text-gray-200 text-lg"></i>
                      }
                    </td>

                    {/* الحالة */}
                    <td className="px-5 py-3 text-center">
                      <button onClick={() => handleToggleActive(unit)}
                        className={`px-3 py-1 rounded-full text-xs font-bold transition
                          ${unit.is_active
                            ? 'bg-green-100 text-green-700 hover:bg-green-200'
                            : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}`}>
                        {unit.is_active ? 'نشطة' : 'معطّلة'}
                      </button>
                    </td>

                    {/* الإجراءات */}
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-center gap-3">
                        <button onClick={() => { setEditing(unit); setShowModal(true); }}
                          className="text-blue-600 hover:text-blue-800 transition" title="تعديل">
                          <i className="fas fa-edit"></i>
                        </button>
                        {canDelete && (
                          <button onClick={() => handleDelete(unit)}
                            className="text-red-500 hover:text-red-700 transition" title="حذف">
                            <i className="fas fa-trash"></i>
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
      </div>

      {/* Quick reference */}
      <div className="mt-5 bg-blue-50 border border-blue-200 rounded-2xl p-4">
        <h3 className="font-bold text-blue-800 mb-3 text-sm">
          <i className="fas fa-info-circle ml-2"></i>دليل سريع للمعاملات الشائعة
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { from:'قطعة',  to:'دستة',   factor:'12',   cat:'عدد'  },
            { from:'قطعة',  to:'كرتون',  factor:'24',   cat:'عدد'  },
            { from:'جرام',  to:'كيلو',   factor:'1000', cat:'وزن'  },
            { from:'مل',    to:'لتر',     factor:'1000', cat:'حجم'  },
          ].map(ex => (
            <div key={ex.to} className="bg-white rounded-xl p-3 border border-blue-100 text-center">
              <p className="text-xs text-gray-500 font-bold mb-1">{ex.cat}</p>
              <p className="text-sm font-bold text-gray-800">
                1 {ex.to} = <span className="text-blue-600">{ex.factor}</span> {ex.from}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">factor = {ex.factor}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default UnitsOfMeasure;
"""

# ══════════════════════════════════════════════════════════════════════════════
# FILE 2 — seed_ui_uom.py
# ══════════════════════════════════════════════════════════════════════════════
SEED_UOM = '''"""
seed_ui_uom.py — يُضيف وحدات القياس في UI
"""
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
django.setup()

from ui_builder.models import UiRoute, UiMenuItem, UiAction

MGMT = ["Admins", "Managers"]

# Route
route, created = UiRoute.objects.update_or_create(
    key="route.units",
    defaults=dict(
        label="وحدات القياس",
        path="/units",
        component="UnitsOfMeasure",
        wrapper="auth",
        required_groups=MGMT,
        order=16,
        is_active=True,
    )
)
print(f"{'✅ أُنشئ' if created else '🔁 حُدِّث'} Route: route.units → /units → UnitsOfMeasure")

# MenuItem تحت قسم المنتجات
item, created = UiMenuItem.objects.update_or_create(
    key="menu.units",
    defaults=dict(
        label="وحدات القياس",
        path="/units",
        icon="fa-ruler",
        parent_key="menu.products_section",
        order=3,
        required_groups=MGMT,
        is_active=True,
    )
)
print(f"{'✅ أُنشئ' if created else '🔁 حُدِّث'} MenuItem: menu.units → parent: menu.products_section")

# Actions
for key, label, action_key, variant, order in [
    ("units.add",    "إضافة وحدة", "units.add",    "primary", 1),
    ("units.delete", "حذف وحدة",   "units.delete", "danger",  2),
]:
    a, created = UiAction.objects.update_or_create(
        key=key,
        defaults=dict(
            label=label,
            page_key="units.list",
            action_key=action_key,
            variant=variant,
            required_groups=MGMT,
            order=order,
            is_active=True,
        )
    )
    print(f"{'✅ أُنشئ' if created else '🔁 حُدِّث'} Action: {key}")

print("\\n✅ انتهى — أعد تشغيل الـ backend وسجّل دخول من جديد")
'''

# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("  fix_add_uom_page.py")
print("=" * 60)

# 1. UnitsOfMeasure.jsx
page_path = os.path.join(FRONTEND, "pages/UnitsOfMeasure.jsx")
backup(page_path)
write_file(page_path, UOM_JSX)

# 2. seed_ui_uom.py
seed_path = os.path.join(BACKEND, "seed_ui_uom.py")
backup(seed_path)
write_file(seed_path, SEED_UOM)

update_changelog(
    "- أضفنا UnitsOfMeasure.jsx: إدارة كاملة لوحدات القياس\n"
    "- أضفنا seed_ui_uom.py: route /units + menu item + actions\n"
)

print()
print("✅ تم! الخطوات:")
print()
print("  1. seed الـ UI:")
print("     cd pos_backend")
print("     python manage.py shell < seed_ui_uom.py")
print()
print("  2. restart الـ Vite (عشان الملف جديد):")
print("     Ctrl+C  ثم  npm run dev")
print()
print("  3. restart الـ backend")
