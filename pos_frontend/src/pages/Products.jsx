import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { productsAPI, categoriesAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

// ─── ثوابت ────────────────────────────────────────────────
const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];
const DEBOUNCE_MS       = 400;
const LOW_STOCK_THRESHOLD = 10;

// ─── Toast System ─────────────────────────────────────────
const useToast = () => {
  const [toasts, setToasts] = useState([]);
  const seq = useRef(1);

  const push = useCallback((type, text, duration = 3500) => {
    const id = seq.current++;
    setToasts((p) => [...p, { id, type, text }]);
    setTimeout(() => setToasts((p) => p.filter((t) => t.id !== id)), duration);
  }, []);

  const dismiss = useCallback((id) => setToasts((p) => p.filter((t) => t.id !== id)), []);

  const ToastContainer = useCallback(() => (
    <div className="fixed bottom-5 left-5 z-[9999] flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-start justify-between gap-3 px-4 py-3 rounded-xl shadow-lg border font-semibold text-sm animate-fadeIn
            ${t.type === 'success' ? 'bg-green-50  border-green-200  text-green-800'  : ''}
            ${t.type === 'error'   ? 'bg-red-50    border-red-200    text-red-800'    : ''}
            ${t.type === 'warning' ? 'bg-yellow-50 border-yellow-200 text-yellow-800' : ''}
            ${t.type === 'info'    ? 'bg-blue-50   border-blue-200   text-blue-800'   : ''}
          `}
        >
          <span>{t.text}</span>
          <button onClick={() => dismiss(t.id)} className="opacity-60 hover:opacity-100 transition">✕</button>
        </div>
      ))}
    </div>
  ), [toasts, dismiss]);

  return { push, ToastContainer };
};

// ─── Confirm Modal ─────────────────────────────────────────
const ConfirmModal = ({ open, title, message, confirmLabel = 'تأكيد', danger = false, onConfirm, onCancel }) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 animate-fadeIn">
        <h3 className="text-lg font-bold text-gray-800 mb-2">{title}</h3>
        <p className="text-gray-600 text-sm mb-6">{message}</p>
        <div className="flex gap-3">
          <button
            onClick={onConfirm}
            className={`flex-1 py-2 rounded-xl font-bold text-white transition
              ${danger ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {confirmLabel}
          </button>
          <button
            onClick={onCancel}
            className="flex-1 py-2 rounded-xl font-bold bg-gray-100 text-gray-700 hover:bg-gray-200 transition"
          >
            إلغاء
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── Skeleton Row ──────────────────────────────────────────
const SkeletonRow = () => (
  <tr className="border-b animate-pulse">
    {[...Array(8)].map((_, i) => (
      <td key={i} className="px-4 py-3">
        <div className="h-4 bg-gray-200 rounded w-3/4"></div>
      </td>
    ))}
  </tr>
);

// ─── Profit Badge ──────────────────────────────────────────
const ProfitBadge = ({ margin }) => {
  const m = parseFloat(margin) || 0;
  const color = m >= 20 ? 'bg-green-100 text-green-700'
              : m >= 10 ? 'bg-yellow-100 text-yellow-700'
              :            'bg-red-100 text-red-700';
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-bold ${color}`}>
      {m.toFixed(1)}%
    </span>
  );
};

// ─── Stock Badge ───────────────────────────────────────────
const StockBadge = ({ stock }) => {
  const color = stock < LOW_STOCK_THRESHOLD
    ? 'bg-red-100 text-red-700'
    : stock < 30
    ? 'bg-yellow-100 text-yellow-700'
    : 'bg-green-100 text-green-700';
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-bold ${color}`}>
      <i className={`fas fa-box ml-1 ${stock < LOW_STOCK_THRESHOLD ? 'fa-beat' : ''}`}></i>
      {stock}
    </span>
  );
};

// ─── Inline Stock Adjust ───────────────────────────────────
const InlineStockAdjust = ({ product, onDone, onError }) => {
  const [val, setVal] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleApply = async () => {
    const adj = parseInt(val);
    if (isNaN(adj) || adj === 0) { onError('أدخل رقماً صحيحاً غير صفر'); return; }
    setLoading(true);
    try {
      const res = await productsAPI.adjustStock(product.id, adj);
      onDone(res.data);
    } catch (e) {
      onError(e.response?.data?.error || 'خطأ في تعديل المخزون');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-xl px-3 py-2 w-fit">
      <span className="text-xs text-blue-700 font-bold whitespace-nowrap">
        المتاح: {product.stock}
      </span>
      <input
        ref={inputRef}
        type="number"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') handleApply(); if (e.key === 'Escape') onDone(null); }}
        placeholder="±"
        className="w-16 border border-blue-300 rounded-lg px-2 py-1 text-center text-sm font-bold outline-none focus:ring-2 focus:ring-blue-400"
      />
      <button
        onClick={handleApply}
        disabled={loading}
        className="text-xs bg-blue-600 text-white rounded-lg px-2 py-1 font-bold hover:bg-blue-700 disabled:opacity-50 transition"
      >
        {loading ? <i className="fas fa-circle-notch fa-spin"></i> : 'تطبيق'}
      </button>
      <button
        onClick={() => onDone(null)}
        className="text-xs text-gray-500 hover:text-gray-700 font-bold transition"
      >✕</button>
    </div>
  );
};

// ─── Product Form Modal ────────────────────────────────────
const EMPTY_FORM = {
  name: '', category: '', price: '', cost: '',
  stock: '', barcode: '', image_url: '', is_active: true, description: '',
};

const ProductModal = ({ open, product, categories, onClose, onSaved, toast }) => {
  const [form, setForm]         = useState(EMPTY_FORM);
  const [saving, setSaving]     = useState(false);
  const [imgError, setImgError] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');

  // ملء الفورم عند فتح الـ modal للتعديل
  useEffect(() => {
    if (!open) return;
    setActiveTab('basic');
    setImgError(false);
    if (product) {
      setForm({
        name:        product.name         || '',
        category:    product.category     || '',
        price:       product.price        || '',
        cost:        product.cost         || '',
        stock:       product.stock        ?? '',
        barcode:     product.barcode      || '',
        image_url:   product.image_url    || '',
        is_active:   product.is_active    ?? true,
        description: product.description  || '',
      });
    } else {
      setForm(EMPTY_FORM);
    }
  }, [open, product]);

  const set = (key, val) => setForm((p) => ({ ...p, [key]: val }));

  // حساب هامش الربح لحظياً
  const liveMargin = useMemo(() => {
    const p = parseFloat(form.price) || 0;
    const c = parseFloat(form.cost)  || 0;
    if (c <= 0 || p <= 0) return null;
    return ((p - c) / c * 100).toFixed(1);
  }, [form.price, form.cost]);

  const priceWarning = useMemo(() => {
    const p = parseFloat(form.price) || 0;
    const c = parseFloat(form.cost)  || 0;
    return c > 0 && p > 0 && p < c;
  }, [form.price, form.cost]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (product) {
        await productsAPI.update(product.id, form);
        toast('success', '✅ تم تحديث المنتج بنجاح');
      } else {
        await productsAPI.create(form);
        toast('success', '✅ تم إضافة المنتج بنجاح');
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

  const tabs = [
    { key: 'basic',   label: 'البيانات الأساسية', icon: 'fa-info-circle'  },
    { key: 'pricing', label: 'التسعير والمخزون',  icon: 'fa-tags'         },
    { key: 'media',   label: 'الصورة والوصف',     icon: 'fa-image'        },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col animate-fadeIn">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-xl font-bold text-gray-800">
            <i className={`fas ${product ? 'fa-edit' : 'fa-plus-circle'} ml-2 text-blue-600`}></i>
            {product ? 'تعديل منتج' : 'إضافة منتج جديد'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl transition">✕</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b px-6">
          {tabs.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setActiveTab(t.key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-bold border-b-2 transition -mb-px
                ${activeTab === t.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'}`}
            >
              <i className={`fas ${t.icon}`}></i>
              {t.label}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-6 py-5 space-y-4">

          {/* ── Tab: البيانات الأساسية ── */}
          {activeTab === 'basic' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 mb-1">اسم المنتج <span className="text-red-500">*</span></label>
                <input
                  type="text" required className="input-field"
                  value={form.name}
                  onChange={(e) => set('name', e.target.value)}
                  placeholder="مثال: شوكولاتة كيت كات"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-gray-700 mb-1">الفئة <span className="text-red-500">*</span></label>
                <select
                  required className="input-field"
                  value={form.category}
                  onChange={(e) => set('category', e.target.value)}
                >
                  <option value="">— اختر الفئة —</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-bold text-gray-700 mb-1">الباركود</label>
                <div className="relative">
                  <i className="fas fa-barcode absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
                  <input
                    type="text" className="input-field pr-9"
                    value={form.barcode}
                    onChange={(e) => set('barcode', e.target.value)}
                    placeholder="أدخل أو امسح الباركود"
                  />
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl border">
                <input
                  type="checkbox" id="is_active"
                  checked={form.is_active}
                  onChange={(e) => set('is_active', e.target.checked)}
                  className="w-4 h-4 accent-blue-600"
                />
                <label htmlFor="is_active" className="text-sm font-bold text-gray-700 cursor-pointer">
                  المنتج نشط (يظهر في نقطة البيع)
                </label>
              </div>
            </div>
          )}

          {/* ── Tab: التسعير والمخزون ── */}
          {activeTab === 'pricing' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-1">سعر البيع (ر.س) <span className="text-red-500">*</span></label>
                  <input
                    type="number" step="0.01" min="0" required className="input-field"
                    value={form.price}
                    onChange={(e) => set('price', e.target.value)}
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-1">التكلفة (ر.س) <span className="text-red-500">*</span></label>
                  <input
                    type="number" step="0.01" min="0" required className="input-field"
                    value={form.cost}
                    onChange={(e) => set('cost', e.target.value)}
                    placeholder="0.00"
                  />
                </div>
              </div>

              {/* Live Margin Indicator */}
              {liveMargin !== null && (
                <div className={`flex items-center gap-3 p-3 rounded-xl border text-sm font-bold
                  ${priceWarning
                    ? 'bg-red-50 border-red-200 text-red-700'
                    : parseFloat(liveMargin) >= 20
                    ? 'bg-green-50 border-green-200 text-green-700'
                    : 'bg-yellow-50 border-yellow-200 text-yellow-700'
                  }`}
                >
                  <i className={`fas ${priceWarning ? 'fa-exclamation-triangle' : 'fa-chart-line'}`}></i>
                  {priceWarning
                    ? '⚠️ تحذير: السعر أقل من التكلفة! ستبيع بخسارة.'
                    : `هامش الربح: ${liveMargin}%`
                  }
                </div>
              )}

              <div>
                <label className="block text-sm font-bold text-gray-700 mb-1">
                  الكمية الافتراضية <span className="text-red-500">*</span>
                  {product && <span className="text-xs text-gray-400 mr-2">(لتعديل المخزون بعد الحفظ استخدم زر التعديل المباشر)</span>}
                </label>
                <input
                  type="number" min="0" required className="input-field"
                  value={form.stock}
                  onChange={(e) => set('stock', e.target.value)}
                  placeholder="0"
                  disabled={!!product}
                />
                {product && (
                  <p className="text-xs text-blue-600 mt-1">
                    <i className="fas fa-info-circle ml-1"></i>
                    الكمية الحالية: <strong>{product.stock}</strong> — عدّلها بزر ± في الجدول
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ── Tab: الصورة والوصف ── */}
          {activeTab === 'media' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 mb-1">رابط الصورة</label>
                <input
                  type="url" className="input-field"
                  value={form.image_url}
                  onChange={(e) => { set('image_url', e.target.value); setImgError(false); }}
                  placeholder="https://example.com/image.jpg"
                />
              </div>

              {/* Live Image Preview */}
              {form.image_url && (
                <div className="flex justify-center">
                  {imgError ? (
                    <div className="w-40 h-40 rounded-xl bg-gray-100 border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-400">
                      <i className="fas fa-image-slash text-3xl mb-2"></i>
                      <span className="text-xs">رابط الصورة غير صحيح</span>
                    </div>
                  ) : (
                    <img
                      src={form.image_url}
                      alt="معاينة"
                      onError={() => setImgError(true)}
                      className="w-40 h-40 object-cover rounded-xl border-2 border-blue-200 shadow"
                    />
                  )}
                </div>
              )}

              <div>
                <label className="block text-sm font-bold text-gray-700 mb-1">الوصف</label>
                <textarea
                  className="input-field resize-none"
                  rows="4"
                  value={form.description}
                  onChange={(e) => set('description', e.target.value)}
                  placeholder="وصف اختياري للمنتج..."
                />
              </div>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex gap-3">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={saving}
            className="flex-1 btn-primary flex items-center justify-center gap-2 disabled:opacity-60"
          >
            {saving
              ? <><i className="fas fa-circle-notch fa-spin"></i> جاري الحفظ...</>
              : <><i className="fas fa-save"></i> حفظ المنتج</>
            }
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="flex-1 btn-secondary flex items-center justify-center gap-2"
          >
            <i className="fas fa-times"></i> إلغاء
          </button>
        </div>
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════
//  Products — Main Component
// ══════════════════════════════════════════════════════════
const Products = () => {
  const PAGE_KEY = 'products.list';
  const { hasAction } = useAuth();
  const canAdd    = hasAction(PAGE_KEY, 'products.add');
  const canDelete = hasAction(PAGE_KEY, 'products.delete');

  const { push: toast, ToastContainer } = useToast();

  // ─── State ────────────────────────────────────────────
  const [products,    setProducts]    = useState([]);
  const [categories,  setCategories]  = useState([]);
  const [stats,       setStats]       = useState({ total: 0, active: 0, lowStock: 0, totalValue: 0 });
  const [loading,     setLoading]     = useState(true);
  const [saving,      setSaving]      = useState(false);

  // Filters
  const [searchQuery,      setSearchQuery]      = useState('');
  const [filterCategory,   setFilterCategory]   = useState('');
  const [filterStatus,     setFilterStatus]     = useState('');   // '' | 'true' | 'false'
  const [filterLowStock,   setFilterLowStock]   = useState(false);

  // Pagination
  const [page,     setPage]     = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total,    setTotal]    = useState(0);

  // Sorting
  const [sortBy,  setSortBy]  = useState('-created_at');

  // Selection (bulk)
  const [selected,  setSelected]  = useState(new Set());

  // Inline stock adjust
  const [adjustingId, setAdjustingId] = useState(null);

  // Modals
  const [showModal,      setShowModal]      = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [confirmState,   setConfirmState]   = useState({ open: false });

  // Debounce ref
  const debounceRef = useRef(null);

  // ─── Fetch Categories (مرة واحدة فقط) ───────────────
  useEffect(() => {
    categoriesAPI.getAll()
      .then((r) => setCategories(r.data.results || r.data))
      .catch(() => toast('error', '❌ تعذّر تحميل الفئات'));
  }, []);

  // ─── Fetch Products ───────────────────────────────────
  const fetchProducts = useCallback(async ({
    q          = searchQuery,
    category   = filterCategory,
    status     = filterStatus,
    lowStock   = filterLowStock,
    pg         = page,
    size       = pageSize,
    ordering   = sortBy,
    silent     = false,
  } = {}) => {
    try {
      if (!silent) setLoading(true);
      setSelected(new Set());

      const params = { page: pg, page_size: size, ordering };
      if (q)        params.search    = q;
      if (category) params.category  = category;
      if (status)   params.is_active = status;
      if (lowStock) params.stock__lt = LOW_STOCK_THRESHOLD;

      const res = await productsAPI.getAll(params);
      const data     = res.data.results ?? res.data;
      const count    = res.data.count   ?? data.length;

      setProducts(data);
      setTotal(count);

      // إحصائيات سريعة من البيانات المحملة
      // (نحسبها من كل الصفحات عبر طلب إضافي بدون pagination)
      if (!silent) {
        productsAPI.getAll({ page_size: 9999, is_active: '' }).then((all) => {
          const allData = all.data.results ?? all.data;
          setStats({
            total:      allData.length,
            active:     allData.filter((p) => p.is_active).length,
            lowStock:   allData.filter((p) => p.stock < LOW_STOCK_THRESHOLD && p.is_active).length,
            totalValue: allData.reduce((s, p) => s + (parseFloat(p.cost || 0) * parseInt(p.stock || 0)), 0),
          });
        }).catch(() => {});
      }
    } catch {
      toast('error', '❌ تعذّر تحميل المنتجات');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [searchQuery, filterCategory, filterStatus, filterLowStock, page, pageSize, sortBy]);

  // ─── أول تحميل + إعادة الجلب عند تغيير الفلاتر ──────
  useEffect(() => {
    // Debounce على البحث النصي فقط
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      fetchProducts({ q: searchQuery, pg: 1 });
    }, searchQuery ? DEBOUNCE_MS : 0);
    return () => clearTimeout(debounceRef.current);
  }, [searchQuery]);

  useEffect(() => {
    setPage(1);
    fetchProducts({ pg: 1 });
  }, [filterCategory, filterStatus, filterLowStock, pageSize, sortBy]);

  useEffect(() => {
    fetchProducts({ pg: page });
  }, [page]);

  // ─── Sorting helper ───────────────────────────────────
  const handleSort = (field) => {
    setSortBy((prev) => (prev === field ? `-${field}` : field));
  };

  const SortIcon = ({ field }) => {
    if (sortBy === field)  return <i className="fas fa-sort-up   text-blue-600 mr-1"></i>;
    if (sortBy === `-${field}`) return <i className="fas fa-sort-down text-blue-600 mr-1"></i>;
    return <i className="fas fa-sort text-gray-300 mr-1"></i>;
  };

  // ─── Selection ────────────────────────────────────────
  const allSelected = products.length > 0 && products.every((p) => selected.has(p.id));

  const toggleSelectAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(products.map((p) => p.id)));
  };

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  // ─── Bulk Delete ──────────────────────────────────────
  const handleBulkDelete = () => {
    setConfirmState({
      open:         true,
      title:        'حذف متعدد',
      message:      `هل أنت متأكد من حذف ${selected.size} منتج؟ لا يمكن التراجع عن هذا الإجراء.`,
      confirmLabel: `حذف ${selected.size} منتجات`,
      danger:       true,
      onConfirm:    async () => {
        setConfirmState({ open: false });
        setSaving(true);
        try {
          await Promise.all([...selected].map((id) => productsAPI.delete(id)));
          toast('success', `✅ تم حذف ${selected.size} منتج بنجاح`);
          fetchProducts({ silent: false });
        } catch {
          toast('error', '❌ حدث خطأ أثناء الحذف');
        } finally {
          setSaving(false);
        }
      },
      onCancel: () => setConfirmState({ open: false }),
    });
  };

  // ─── Bulk Toggle Active ───────────────────────────────
  const handleBulkToggleActive = (activate) => {
    setConfirmState({
      open:         true,
      title:        activate ? 'تفعيل منتجات' : 'تعطيل منتجات',
      message:      `هل تريد ${activate ? 'تفعيل' : 'تعطيل'} ${selected.size} منتج؟`,
      confirmLabel: `${activate ? 'تفعيل' : 'تعطيل'} ${selected.size}`,
      danger:       !activate,
      onConfirm:    async () => {
        setConfirmState({ open: false });
        setSaving(true);
        try {
          await Promise.all(
            [...selected].map((id) => {
              const prod = products.find((p) => p.id === id);
              return productsAPI.update(id, { ...prod, is_active: activate });
            })
          );
          toast('success', `✅ تم ${activate ? 'تفعيل' : 'تعطيل'} ${selected.size} منتج`);
          fetchProducts({ silent: false });
        } catch {
          toast('error', '❌ حدث خطأ أثناء التحديث');
        } finally {
          setSaving(false);
        }
      },
      onCancel: () => setConfirmState({ open: false }),
    });
  };

  // ─── Single Delete ────────────────────────────────────
  const handleDelete = (product) => {
    setConfirmState({
      open:         true,
      title:        'حذف منتج',
      message:      `هل أنت متأكد من حذف "${product.name}"؟`,
      confirmLabel: 'حذف',
      danger:       true,
      onConfirm:    async () => {
        setConfirmState({ open: false });
        try {
          await productsAPI.delete(product.id);
          toast('success', `✅ تم حذف "${product.name}"`);
          fetchProducts({ silent: false });
        } catch {
          toast('error', '❌ حدث خطأ أثناء الحذف');
        }
      },
      onCancel: () => setConfirmState({ open: false }),
    });
  };

  // ─── Inline Stock Done ────────────────────────────────
  const handleStockAdjustDone = (updatedProduct) => {
    setAdjustingId(null);
    if (updatedProduct) {
      setProducts((prev) =>
        prev.map((p) => (p.id === updatedProduct.id ? { ...p, stock: updatedProduct.stock } : p))
      );
      toast('success', `✅ تم تحديث مخزون "${updatedProduct.name}" إلى ${updatedProduct.stock}`);
    }
  };

  // ─── Pagination helpers ───────────────────────────────
  const totalPages = Math.ceil(total / pageSize) || 1;

  const copyBarcode = (barcode) => {
    navigator.clipboard.writeText(barcode).then(() => toast('info', `📋 تم نسخ الباركود: ${barcode}`));
  };

  // ─── Render ───────────────────────────────────────────
  return (
    <div className="p-6 bg-gray-100 min-h-screen">
      <ToastContainer />
      <ConfirmModal {...confirmState} />

      {/* ── Header ── */}
      <div className="flex justify-between items-center mb-6 flex-wrap gap-3">
        <h1 className="text-3xl font-bold text-gray-800">
          <i className="fas fa-box ml-2 text-blue-600"></i>إدارة المنتجات
        </h1>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => fetchProducts({ silent: false })}
            className="btn-secondary flex items-center gap-2"
            disabled={loading}
          >
            <i className={`fas fa-sync-alt ${loading ? 'fa-spin' : ''}`}></i>
            تحديث
          </button>
          {canAdd && (
            <button
              onClick={() => { setEditingProduct(null); setShowModal(true); }}
              className="btn-primary flex items-center gap-2"
            >
              <i className="fas fa-plus"></i>إضافة منتج
            </button>
          )}
        </div>
      </div>

      {/* ── Stats Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'إجمالي المنتجات',   value: stats.total,      icon: 'fa-box',           color: 'from-blue-500 to-blue-600'   },
          { label: 'المنتجات النشطة',   value: stats.active,     icon: 'fa-check-circle',  color: 'from-green-500 to-green-600' },
          { label: 'مخزون منخفض',       value: stats.lowStock,   icon: 'fa-exclamation-triangle', color: stats.lowStock > 0 ? 'from-red-500 to-red-600' : 'from-gray-400 to-gray-500' },
          { label: 'قيمة المخزون',      value: `${stats.totalValue.toLocaleString('ar-SA', { maximumFractionDigits: 0 })} ر.س`, icon: 'fa-coins', color: 'from-purple-500 to-purple-600' },
        ].map((s) => (
          <div key={s.label} className={`bg-gradient-to-br ${s.color} text-white rounded-2xl p-4 shadow`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/80 text-sm mb-1">{s.label}</p>
                <p className="text-2xl font-bold">{s.value}</p>
              </div>
              <i className={`fas ${s.icon} text-4xl opacity-20`}></i>
            </div>
          </div>
        ))}
      </div>

      {/* ── Filters ── */}
      <div className="bg-white rounded-2xl shadow p-4 mb-5 flex flex-wrap gap-3 items-end">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs font-bold text-gray-500 block mb-1">بحث</label>
          <div className="relative">
            <i className="fas fa-search absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
            <input
              type="text"
              className="input-field pr-9"
              placeholder="اسم المنتج أو الباركود..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Category filter */}
        <div className="min-w-[160px]">
          <label className="text-xs font-bold text-gray-500 block mb-1">الفئة</label>
          <select
            className="input-field"
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
          >
            <option value="">كل الفئات</option>
            {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>

        {/* Status filter */}
        <div className="min-w-[140px]">
          <label className="text-xs font-bold text-gray-500 block mb-1">الحالة</label>
          <select
            className="input-field"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">الكل</option>
            <option value="true">نشط فقط</option>
            <option value="false">غير نشط</option>
          </select>
        </div>

        {/* Low stock toggle */}
        <div className="flex items-center gap-2 min-w-[140px]">
          <input
            type="checkbox"
            id="lowStockFilter"
            checked={filterLowStock}
            onChange={(e) => setFilterLowStock(e.target.checked)}
            className="w-4 h-4 accent-red-600"
          />
          <label htmlFor="lowStockFilter" className="text-sm font-bold text-red-600 cursor-pointer whitespace-nowrap">
            <i className="fas fa-exclamation-triangle ml-1"></i>مخزون منخفض فقط
          </label>
        </div>

        {/* Page size */}
        <div className="min-w-[100px]">
          <label className="text-xs font-bold text-gray-500 block mb-1">لكل صفحة</label>
          <select
            className="input-field"
            value={pageSize}
            onChange={(e) => setPageSize(Number(e.target.value))}
          >
            {PAGE_SIZE_OPTIONS.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>

        {/* Reset filters */}
        {(searchQuery || filterCategory || filterStatus || filterLowStock) && (
          <button
            onClick={() => {
              setSearchQuery('');
              setFilterCategory('');
              setFilterStatus('');
              setFilterLowStock(false);
            }}
            className="text-sm text-gray-500 hover:text-red-600 font-bold transition flex items-center gap-1 mt-5"
          >
            <i className="fas fa-times-circle"></i> مسح الفلاتر
          </button>
        )}
      </div>

      {/* ── Bulk Actions Bar ── */}
      {selected.size > 0 && (
        <div className="bg-blue-600 text-white rounded-2xl px-5 py-3 mb-4 flex items-center justify-between gap-3 flex-wrap animate-fadeIn shadow-lg">
          <span className="font-bold">
            <i className="fas fa-check-square ml-2"></i>
            تم تحديد {selected.size} منتج
          </span>
          <div className="flex gap-2 flex-wrap">
            <button onClick={() => handleBulkToggleActive(true)}  className="bg-green-500 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-bold transition"><i className="fas fa-eye ml-1"></i>تفعيل</button>
            <button onClick={() => handleBulkToggleActive(false)} className="bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-1.5 rounded-lg text-sm font-bold transition"><i className="fas fa-eye-slash ml-1"></i>تعطيل</button>
            {canDelete && (
              <button onClick={handleBulkDelete} className="bg-red-500 hover:bg-red-600 text-white px-3 py-1.5 rounded-lg text-sm font-bold transition"><i className="fas fa-trash ml-1"></i>حذف</button>
            )}
            <button onClick={() => setSelected(new Set())} className="bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded-lg text-sm font-bold transition"><i className="fas fa-times ml-1"></i>إلغاء</button>
          </div>
        </div>
      )}

      {/* ── Table ── */}
      <div className="bg-white rounded-2xl shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="px-4 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleSelectAll}
                    className="w-4 h-4 accent-blue-600"
                  />
                </th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600 cursor-pointer hover:text-blue-600 transition" onClick={() => handleSort('name')}>
                  <SortIcon field="name" />المنتج
                </th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600">الفئة</th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600 cursor-pointer hover:text-blue-600 transition" onClick={() => handleSort('price')}>
                  <SortIcon field="price" />سعر البيع
                </th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600 cursor-pointer hover:text-blue-600 transition" onClick={() => handleSort('cost')}>
                  <SortIcon field="cost" />التكلفة
                </th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600">هامش الربح</th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600 cursor-pointer hover:text-blue-600 transition" onClick={() => handleSort('stock')}>
                  <SortIcon field="stock" />المخزون
                </th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600">الحالة</th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                [...Array(pageSize > 10 ? 8 : 5)].map((_, i) => <SkeletonRow key={i} />)
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan="9" className="text-center py-16">
                    <i className="fas fa-box-open text-6xl text-gray-300 mb-4 block"></i>
                    <p className="text-gray-500 font-semibold">لا توجد منتجات مطابقة</p>
                    {(searchQuery || filterCategory || filterStatus || filterLowStock) && (
                      <button
                        onClick={() => { setSearchQuery(''); setFilterCategory(''); setFilterStatus(''); setFilterLowStock(false); }}
                        className="mt-3 text-blue-600 hover:underline text-sm font-bold"
                      >
                        مسح الفلاتر والعرض الكامل
                      </button>
                    )}
                  </td>
                </tr>
              ) : (
                products.map((product) => (
                  <tr
                    key={product.id}
                    className={`border-b transition hover:bg-gray-50 ${selected.has(product.id) ? 'bg-blue-50' : ''}`}
                  >
                    {/* Checkbox */}
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selected.has(product.id)}
                        onChange={() => toggleSelect(product.id)}
                        className="w-4 h-4 accent-blue-600"
                      />
                    </td>

                    {/* Product */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        {product.image_url ? (
                          <img src={product.image_url} alt={product.name} className="w-12 h-12 object-cover rounded-xl border" />
                        ) : (
                          <div className="w-12 h-12 rounded-xl bg-gray-100 border flex items-center justify-center text-gray-400">
                            <i className="fas fa-box"></i>
                          </div>
                        )}
                        <div>
                          <p className="font-bold text-gray-800 text-sm">{product.name}</p>
                          {product.barcode && (
                            <button
                              onClick={() => copyBarcode(product.barcode)}
                              className="text-xs text-gray-400 hover:text-blue-600 transition flex items-center gap-1 mt-0.5"
                              title="نسخ الباركود"
                            >
                              <i className="fas fa-barcode"></i>
                              {product.barcode}
                              <i className="fas fa-copy opacity-0 group-hover:opacity-100"></i>
                            </button>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Category */}
                    <td className="px-4 py-3">
                      {product.category_name ? (
                        <span
                          className="px-2 py-1 rounded-full text-xs font-bold text-white"
                          style={{ backgroundColor: product.category_color || '#6B7280' }}
                        >
                          {product.category_name}
                        </span>
                      ) : <span className="text-gray-400 text-xs">—</span>}
                    </td>

                    {/* Price */}
                    <td className="px-4 py-3 font-bold text-blue-600 text-sm">{parseFloat(product.price).toFixed(2)} ر.س</td>

                    {/* Cost */}
                    <td className="px-4 py-3 text-gray-500 text-sm">{parseFloat(product.cost || 0).toFixed(2)} ر.س</td>

                    {/* Profit Margin */}
                    <td className="px-4 py-3">
                      <ProfitBadge margin={product.profit_margin} />
                    </td>

                    {/* Stock + Inline Adjust */}
                    <td className="px-4 py-3">
                      {adjustingId === product.id ? (
                        <InlineStockAdjust
                          product={product}
                          onDone={handleStockAdjustDone}
                          onError={(msg) => toast('error', `❌ ${msg}`)}
                        />
                      ) : (
                        <div className="flex items-center gap-2">
                          <StockBadge stock={product.stock} />
                          <button
                            onClick={() => setAdjustingId(product.id)}
                            className="text-xs text-gray-400 hover:text-blue-600 transition font-bold"
                            title="تعديل المخزون مباشرة"
                          >
                            <i className="fas fa-plus-minus"></i>
                          </button>
                        </div>
                      )}
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-bold ${product.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {product.is_active ? 'نشط' : 'معطّل'}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => { setEditingProduct(product); setShowModal(true); }}
                          className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 transition flex items-center justify-center"
                          title="تعديل"
                        >
                          <i className="fas fa-edit text-sm"></i>
                        </button>
                        {canDelete && (
                          <button
                            onClick={() => handleDelete(product)}
                            className="w-8 h-8 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 transition flex items-center justify-center"
                            title="حذف"
                          >
                            <i className="fas fa-trash text-sm"></i>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* ── Pagination ── */}
        {!loading && total > 0 && (
          <div className="px-5 py-4 border-t flex items-center justify-between flex-wrap gap-3">
            <p className="text-sm text-gray-500">
              عرض <strong>{(page - 1) * pageSize + 1}</strong> – <strong>{Math.min(page * pageSize, total)}</strong> من <strong>{total}</strong> منتج
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(1)}
                disabled={page === 1}
                className="w-8 h-8 rounded-lg border text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition text-sm font-bold"
              >«</button>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="w-8 h-8 rounded-lg border text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition text-sm font-bold"
              >‹</button>

              {/* Page numbers */}
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pg;
                if (totalPages <= 5) pg = i + 1;
                else if (page <= 3) pg = i + 1;
                else if (page >= totalPages - 2) pg = totalPages - 4 + i;
                else pg = page - 2 + i;
                return (
                  <button
                    key={pg}
                    onClick={() => setPage(pg)}
                    className={`w-8 h-8 rounded-lg border text-sm font-bold transition
                      ${pg === page ? 'bg-blue-600 text-white border-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}
                  >
                    {pg}
                  </button>
                );
              })}

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="w-8 h-8 rounded-lg border text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition text-sm font-bold"
              >›</button>
              <button
                onClick={() => setPage(totalPages)}
                disabled={page === totalPages}
                className="w-8 h-8 rounded-lg border text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition text-sm font-bold"
              >»</button>
            </div>
          </div>
        )}
      </div>

      {/* ── Product Modal ── */}
      <ProductModal
        open={showModal}
        product={editingProduct}
        categories={categories}
        onClose={() => { setShowModal(false); setEditingProduct(null); }}
        onSaved={() => fetchProducts({ silent: false })}
        toast={toast}
      />
    </div>
  );
};

export default Products;
