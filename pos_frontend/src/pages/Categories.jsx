
import { useState, useEffect, useCallback } from 'react';
import { categoriesAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

// ─── ثوابت ────────────────────────────────────────────────────────────────
const PRESET_COLORS = [
  '#3B82F6','#10B981','#F59E0B','#EF4444','#8B5CF6',
  '#EC4899','#06B6D4','#84CC16','#F97316','#6B7280',
];

const PRESET_ICONS = [
  'fa-box','fa-utensils','fa-tshirt','fa-laptop','fa-mobile-alt',
  'fa-car','fa-heartbeat','fa-book','fa-coffee','fa-gamepad',
  'fa-pills','fa-paint-brush','fa-tools','fa-music','fa-star',
];

const EMPTY_FORM = { name: '', icon: 'fa-box', color: '#3B82F6' };

// ─── Toast ────────────────────────────────────────────────────────────────
const useToast = () => {
  const [toasts, setToasts] = useState([]);
  const push = (type, text) => {
    const id = Date.now();
    setToasts(p => [...p, { id, type, text }]);
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 3500);
  };
  const Toast = () => (
    <div className="fixed bottom-5 left-5 z-[9999] flex flex-col gap-2">
      {toasts.map(t => (
        <div key={t.id} className={`px-4 py-3 rounded-xl shadow-lg font-bold text-sm border
          ${t.type === 'success' ? 'bg-green-50 text-green-800 border-green-200' : ''}
          ${t.type === 'error'   ? 'bg-red-50   text-red-800   border-red-200'   : ''}
          ${t.type === 'info'    ? 'bg-blue-50  text-blue-800  border-blue-200'  : ''}
        `}>{t.text}</div>
      ))}
    </div>
  );
  return { push, Toast };
};

// ─── Confirm Modal ─────────────────────────────────────────────────────────
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

// ─── Category Modal ────────────────────────────────────────────────────────
const CategoryModal = ({ open, category, onClose, onSaved, toast }) => {
  const [form, setForm]     = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(category
      ? { name: category.name, icon: category.icon || 'fa-box', color: category.color || '#3B82F6' }
      : EMPTY_FORM
    );
  }, [open, category]);

  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return toast('error', '❌ اسم الفئة مطلوب');
    setSaving(true);
    try {
      if (category) {
        await categoriesAPI.update(category.id, form);
        toast('success', '✅ تم تحديث الفئة بنجاح');
      } else {
        await categoriesAPI.create(form);
        toast('success', '✅ تم إضافة الفئة بنجاح');
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

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg animate-fadeIn">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-xl font-bold text-gray-800">
            <i className={`fas ${category ? 'fa-edit' : 'fa-plus-circle'} ml-2 text-blue-600`}></i>
            {category ? 'تعديل فئة' : 'إضافة فئة جديدة'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5">

          {/* Preview */}
          <div className="flex items-center justify-center">
            <div className="w-20 h-20 rounded-2xl flex items-center justify-center shadow-lg"
              style={{ backgroundColor: form.color }}>
              <i className={`fas ${form.icon} text-3xl text-white`}></i>
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-1">
              اسم الفئة <span className="text-red-500">*</span>
            </label>
            <input
              type="text" required
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition"
              value={form.name}
              onChange={e => set('name', e.target.value)}
              placeholder="مثال: مشروبات، مواد غذائية..."
            />
          </div>

          {/* Icon Picker */}
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">الأيقونة</label>
            <div className="grid grid-cols-8 gap-2">
              {PRESET_ICONS.map(ic => (
                <button key={ic} type="button"
                  onClick={() => set('icon', ic)}
                  className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm transition
                    ${form.icon === ic
                      ? 'ring-2 ring-blue-500 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  style={form.icon === ic ? { backgroundColor: form.color } : {}}
                >
                  <i className={`fas ${ic}`}></i>
                </button>
              ))}
            </div>
            {/* Custom icon input */}
            <input
              type="text"
              className="mt-2 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition"
              value={form.icon}
              onChange={e => set('icon', e.target.value)}
              placeholder="fa-box أو أي أيقونة Font Awesome..."
            />
          </div>

          {/* Color Picker */}
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">اللون</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {PRESET_COLORS.map(c => (
                <button key={c} type="button"
                  onClick={() => set('color', c)}
                  className={`w-8 h-8 rounded-full border-2 transition
                    ${form.color === c ? 'border-gray-800 scale-110' : 'border-transparent'}`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
            <div className="flex items-center gap-3">
              <input type="color" value={form.color}
                onChange={e => set('color', e.target.value)}
                className="w-10 h-10 rounded-lg border border-gray-200 cursor-pointer p-0.5"
              />
              <span className="text-sm font-mono text-gray-500">{form.color}</span>
            </div>
          </div>

          {/* Footer */}
          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={saving}
              className="flex-1 py-2.5 rounded-xl font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 transition flex items-center justify-center gap-2">
              {saving
                ? <><i className="fas fa-circle-notch fa-spin"></i> جاري الحفظ...</>
                : <><i className="fas fa-save"></i> حفظ الفئة</>
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
//  Categories — Main Component
// ══════════════════════════════════════════════════════════════════════════════
const Categories = () => {
  const PAGE_KEY = 'categories.list';
  const { hasAction } = useAuth();
  const canAdd    = hasAction(PAGE_KEY, 'categories.add');
  const canDelete = hasAction(PAGE_KEY, 'categories.delete');

  const { push: toast, Toast } = useToast();

  const [categories,  setCategories]  = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showModal,   setShowModal]   = useState(false);
  const [editing,     setEditing]     = useState(null);
  const [confirm,     setConfirm]     = useState({ open: false });

  // ─── Fetch ──────────────────────────────────────────────────────────────
  const fetchCategories = useCallback(async () => {
    try {
      setLoading(true);
      const res = await categoriesAPI.getAll({ search: searchQuery });
      setCategories(res.data?.results ?? res.data);
    } catch {
      toast('error', '❌ تعذّر تحميل الفئات');
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  useEffect(() => { fetchCategories(); }, [fetchCategories]);

  // ─── Delete ─────────────────────────────────────────────────────────────
  const handleDelete = (cat) => {
    setConfirm({
      open: true,
      title: 'حذف فئة',
      message: `هل أنت متأكد من حذف فئة "${cat.name}"؟ سيتم إزالة الفئة من جميع المنتجات المرتبطة بها.`,
      onConfirm: async () => {
        setConfirm({ open: false });
        try {
          await categoriesAPI.delete(cat.id);
          toast('success', `✅ تم حذف "${cat.name}"`);
          fetchCategories();
        } catch {
          toast('error', '❌ حدث خطأ أثناء الحذف');
        }
      },
      onCancel: () => setConfirm({ open: false }),
    });
  };

  // ─── Filtered ────────────────────────────────────────────────────────────
  const filtered = searchQuery
    ? categories.filter(c => c.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : categories;

  // ─── Render ──────────────────────────────────────────────────────────────
  return (
    <div className="p-6 bg-gray-100 min-h-screen" dir="rtl">
      <Toast />
      <ConfirmModal {...confirm} />
      <CategoryModal
        open={showModal}
        category={editing}
        onClose={() => { setShowModal(false); setEditing(null); }}
        onSaved={fetchCategories}
        toast={toast}
      />

      {/* Header */}
      <div className="flex justify-between items-center mb-6 flex-wrap gap-3">
        <h1 className="text-3xl font-bold text-gray-800">
          <i className="fas fa-tags ml-2 text-blue-600"></i>إدارة التصنيفات
        </h1>
        <div className="flex gap-2">
          <button onClick={fetchCategories} disabled={loading}
            className="px-4 py-2 rounded-xl border border-gray-200 bg-white font-bold text-gray-600 hover:bg-gray-50 transition flex items-center gap-2">
            <i className={`fas fa-sync-alt ${loading ? 'fa-spin' : ''}`}></i> تحديث
          </button>
          {canAdd && (
            <button
              onClick={() => { setEditing(null); setShowModal(true); }}
              className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold transition flex items-center gap-2">
              <i className="fas fa-plus"></i> إضافة فئة
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl p-4 shadow">
          <p className="text-white/80 text-sm mb-1">إجمالي الفئات</p>
          <p className="text-3xl font-bold">{categories.length}</p>
        </div>
        <div className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-2xl p-4 shadow">
          <p className="text-white/80 text-sm mb-1">الفئات النشطة</p>
          <p className="text-3xl font-bold">{categories.length}</p>
        </div>
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-2xl p-4 shadow">
          <p className="text-white/80 text-sm mb-1">إجمالي المنتجات</p>
          <p className="text-3xl font-bold">
            {categories.reduce((s, c) => s + (c.products_count ?? 0), 0)}
          </p>
        </div>
        <div className="bg-gradient-to-br from-orange-500 to-orange-600 text-white rounded-2xl p-4 shadow">
          <p className="text-white/80 text-sm mb-1">متوسط المنتجات/فئة</p>
          <p className="text-3xl font-bold">
            {categories.length
              ? Math.round(categories.reduce((s, c) => s + (c.products_count ?? 0), 0) / categories.length)
              : 0}
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="bg-white rounded-2xl shadow p-4 mb-5">
        <div className="relative max-w-md">
          <i className="fas fa-search absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
          <input
            type="text"
            className="w-full border border-gray-200 rounded-xl px-3 py-2 pr-9 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition"
            placeholder="البحث عن فئة..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="bg-white rounded-2xl shadow p-5 animate-pulse">
              <div className="w-14 h-14 bg-gray-200 rounded-2xl mb-4"></div>
              <div className="h-5 bg-gray-200 rounded w-2/3 mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-1/3"></div>
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl shadow p-16 text-center">
          <i className="fas fa-tags text-6xl text-gray-300 mb-4 block"></i>
          <p className="text-gray-500 font-semibold text-lg">لا توجد فئات</p>
          {canAdd && (
            <button onClick={() => { setEditing(null); setShowModal(true); }}
              className="mt-4 px-6 py-2 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition">
              إضافة أول فئة
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map(cat => (
            <div key={cat.id}
              className="bg-white rounded-2xl shadow hover:shadow-md transition group overflow-hidden">

              {/* Color strip */}
              <div className="h-2 w-full" style={{ backgroundColor: cat.color || '#3B82F6' }}></div>

              <div className="p-5">
                {/* Icon + Name */}
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center shadow flex-shrink-0"
                    style={{ backgroundColor: cat.color || '#3B82F6' }}>
                    <i className={`fas ${cat.icon || 'fa-box'} text-2xl text-white`}></i>
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-bold text-gray-800 text-lg truncate">{cat.name}</h3>
                    <p className="text-sm text-gray-400 font-mono">{cat.color || '#3B82F6'}</p>
                  </div>
                </div>

                {/* Products count */}
                <div className="flex items-center justify-between mb-4 bg-gray-50 rounded-xl px-3 py-2">
                  <span className="text-sm text-gray-500 font-bold">عدد المنتجات</span>
                  <span className="text-lg font-bold text-blue-600">
                    {cat.products_count ?? 0}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => { setEditing(cat); setShowModal(true); }}
                    className="flex-1 py-2 rounded-xl bg-blue-50 text-blue-600 font-bold text-sm hover:bg-blue-100 transition flex items-center justify-center gap-1">
                    <i className="fas fa-edit"></i> تعديل
                  </button>
                  {canDelete && (
                    <button
                      onClick={() => handleDelete(cat)}
                      className="flex-1 py-2 rounded-xl bg-red-50 text-red-600 font-bold text-sm hover:bg-red-100 transition flex items-center justify-center gap-1">
                      <i className="fas fa-trash"></i> حذف
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Categories;
