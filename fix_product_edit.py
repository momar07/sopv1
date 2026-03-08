# fix_products_edit.py
"""
يُصلح مشكلة اختفاء البيانات عند التعديل في Products.jsx
السبب: الجدول بيستخدم ProductListSerializer (مش فيه cost/category UUID)
الحل: عند الضغط على تعديل، نجيب المنتج كامل من GET /api/products/:id/
"""
import os, shutil, datetime

BASE     = "/home/momar/Projects/POS_DEV/posv1_dev10"
PRODUCTS = os.path.join(BASE, "pos_frontend/src/pages/Products.jsx")
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

PRODUCTS_JSX = r"""
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { productsAPI, categoriesAPI, unitsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const PAGE_SIZE_OPTIONS   = [10, 25, 50, 100];
const DEBOUNCE_MS         = 400;
const LOW_STOCK_THRESHOLD = 10;

// ─── Toast ────────────────────────────────────────────────────────────────
const useToast = () => {
  const [toasts, setToasts] = useState([]);
  const seq = useRef(1);
  const push = useCallback((type, text, duration = 3500) => {
    const id = seq.current++;
    setToasts(p => [...p, { id, type, text }]);
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), duration);
  }, []);
  const dismiss = useCallback(id => setToasts(p => p.filter(t => t.id !== id)), []);
  const ToastContainer = useCallback(() => (
    <div className="fixed bottom-5 left-5 z-[9999] flex flex-col gap-2 max-w-sm">
      {toasts.map(t => (
        <div key={t.id} className={`flex items-start justify-between gap-3 px-4 py-3 rounded-xl shadow-lg border font-semibold text-sm
          ${t.type==='success'?'bg-green-50 border-green-200 text-green-800':''}
          ${t.type==='error'  ?'bg-red-50   border-red-200   text-red-800'  :''}
          ${t.type==='warning'?'bg-yellow-50 border-yellow-200 text-yellow-800':''}
          ${t.type==='info'   ?'bg-blue-50  border-blue-200  text-blue-800' :''}`}>
          <span>{t.text}</span>
          <button onClick={() => dismiss(t.id)} className="opacity-60 hover:opacity-100">✕</button>
        </div>
      ))}
    </div>
  ), [toasts, dismiss]);
  return { push, ToastContainer };
};

// ─── Confirm Modal ────────────────────────────────────────────────────────
const ConfirmModal = ({ open, title, message, confirmLabel='تأكيد', danger=false, onConfirm, onCancel }) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-2">{title}</h3>
        <p className="text-gray-600 text-sm mb-6">{message}</p>
        <div className="flex gap-3">
          <button onClick={onConfirm}
            className={`flex-1 py-2 rounded-xl font-bold text-white transition ${danger?'bg-red-600 hover:bg-red-700':'bg-blue-600 hover:bg-blue-700'}`}>
            {confirmLabel}
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

// ─── Skeleton / Badges ───────────────────────────────────────────────────
const SkeletonRow = () => (
  <tr className="border-b animate-pulse">
    {[...Array(9)].map((_,i) => (
      <td key={i} className="px-4 py-3"><div className="h-4 bg-gray-200 rounded w-3/4"></div></td>
    ))}
  </tr>
);

const ProfitBadge = ({ margin }) => {
  const m = parseFloat(margin)||0;
  const c = m>=20?'bg-green-100 text-green-700':m>=10?'bg-yellow-100 text-yellow-700':'bg-red-100 text-red-700';
  return <span className={`px-2 py-1 rounded-full text-xs font-bold ${c}`}>{m.toFixed(1)}%</span>;
};

const StockBadge = ({ stock }) => {
  const c = stock<LOW_STOCK_THRESHOLD?'bg-red-100 text-red-700':stock<30?'bg-yellow-100 text-yellow-700':'bg-green-100 text-green-700';
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-bold ${c}`}>
      <i className={`fas fa-box ml-1 ${stock<LOW_STOCK_THRESHOLD?'fa-beat':''}`}></i>{stock}
    </span>
  );
};

// ─── Inline Stock Adjust ─────────────────────────────────────────────────
const InlineStockAdjust = ({ product, onDone, onError }) => {
  const [val, setVal]   = useState('');
  const [ld,  setLd]    = useState(false);
  const ref             = useRef(null);
  useEffect(() => { ref.current?.focus(); }, []);
  const apply = async () => {
    const adj = parseInt(val);
    if (isNaN(adj)||adj===0) { onError('أدخل رقماً صحيحاً غير صفر'); return; }
    setLd(true);
    try   { onDone((await productsAPI.adjustStock(product.id, adj)).data); }
    catch (e) { onError(e.response?.data?.error||'خطأ في تعديل المخزون'); }
    finally   { setLd(false); }
  };
  return (
    <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-xl px-3 py-2 w-fit">
      <span className="text-xs text-blue-700 font-bold whitespace-nowrap">المتاح: {product.stock}</span>
      <input ref={ref} type="number" value={val} onChange={e=>setVal(e.target.value)}
        onKeyDown={e=>{if(e.key==='Enter')apply();if(e.key==='Escape')onDone(null);}}
        placeholder="±"
        className="w-16 border border-blue-300 rounded-lg px-2 py-1 text-center text-sm font-bold outline-none focus:ring-2 focus:ring-blue-400"/>
      <button onClick={apply} disabled={ld}
        className="text-xs bg-blue-600 text-white rounded-lg px-2 py-1 font-bold hover:bg-blue-700 disabled:opacity-50 transition">
        {ld?<i className="fas fa-circle-notch fa-spin"/>:'تطبيق'}
      </button>
      <button onClick={()=>onDone(null)} className="text-xs text-gray-500 hover:text-gray-700 font-bold">✕</button>
    </div>
  );
};

// ─── UomPricesTab ────────────────────────────────────────────────────────
const INP = 'w-full border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition bg-white';

const UomPricesTab = ({ form, set, units=[], unitPrices=[], onPriceChange, onAddPrice, onRemovePrice, isEdit=false }) => {
  const active  = useMemo(()=>units.filter(u=>u.is_active),[units]);
  const addable = useMemo(()=>active.filter(u=>!unitPrices.some(p=>p.unit===u.id)),[active,unitPrices]);
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-bold text-gray-500 mb-1">
            الوحدة الأساسية <span className="text-gray-400 font-normal mr-1">(المخزون يُحسب بها)</span>
          </label>
          <select className={INP} value={form.base_unit||''} onChange={e=>set('base_unit',e.target.value||null)}>
            <option value="">— بدون وحدة —</option>
            {active.map(u=><option key={u.id} value={u.id}>{u.name}{u.symbol?` (${u.symbol})`:''}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 mb-1">
            وحدة الشراء الافتراضية <span className="text-gray-400 font-normal mr-1">(في أوامر الشراء)</span>
          </label>
          <select className={INP} value={form.purchase_unit||''} onChange={e=>set('purchase_unit',e.target.value||null)}>
            <option value="">— نفس الأساسية —</option>
            {active.map(u=><option key={u.id} value={u.id}>{u.name}{u.factor!=='1.0000'&&u.factor!=='1'?` × ${u.factor}`:''}</option>)}
          </select>
        </div>
      </div>
      <div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="font-bold text-gray-700 text-sm">أسعار البيع لكل وحدة</h4>
            <p className="text-xs text-gray-400 mt-0.5">السعر التلقائي = سعر البيع × معامل الوحدة</p>
          </div>
          {isEdit && addable.length>0 && (
            <select className="border border-blue-200 rounded-xl px-3 py-1.5 text-sm text-blue-700 font-bold bg-blue-50 outline-none cursor-pointer hover:bg-blue-100 transition"
              value="" onChange={e=>{if(e.target.value)onAddPrice(e.target.value);}}>
              <option value="">+ إضافة وحدة</option>
              {addable.map(u=><option key={u.id} value={u.id}>{u.name} (× {u.factor})</option>)}
            </select>
          )}
        </div>
        {!isEdit&&<div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 text-sm text-blue-700 font-bold flex items-center gap-2"><i className="fas fa-info-circle"></i>أسعار الوحدات تُضاف بعد حفظ المنتج.</div>}
        {isEdit&&unitPrices.length===0&&<div className="bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-500 text-center"><i className="fas fa-tags ml-2 opacity-50"></i>لا توجد وحدات مضافة.</div>}
        {isEdit&&unitPrices.length>0&&(
          <div className="space-y-2">
            <div className="grid grid-cols-12 gap-2 px-3 py-1">
              <span className="col-span-3 text-xs font-bold text-gray-400">الوحدة</span>
              <span className="col-span-2 text-xs font-bold text-gray-400 text-center">المعامل</span>
              <span className="col-span-3 text-xs font-bold text-gray-400 text-center">السعر</span>
              <span className="col-span-2 text-xs font-bold text-gray-400 text-center">تلقائي</span>
              <span className="col-span-1 text-xs font-bold text-gray-400 text-center">نشط</span>
              <span className="col-span-1"></span>
            </div>
            {unitPrices.map(up=>(
              <div key={up.unit} className={`grid grid-cols-12 gap-2 items-center px-3 py-2 rounded-xl border ${up.is_active?'bg-white border-gray-200':'bg-gray-50 border-gray-100 opacity-60'}`}>
                <div className="col-span-3"><span className="font-bold text-gray-700 text-sm">{up.unit_name}</span></div>
                <div className="col-span-2 text-center"><span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-lg font-mono">×{up.factor}</span></div>
                <div className="col-span-3">
                  <input type="number" step="0.01" min="0" disabled={up.is_auto} value={up.price}
                    onChange={e=>onPriceChange(up.unit,'price',e.target.value)}
                    className={`w-full border rounded-lg px-2 py-1 text-sm text-center font-bold outline-none transition ${up.is_auto?'bg-gray-100 text-gray-500 border-gray-200 cursor-not-allowed':'border-blue-300 focus:ring-2 focus:ring-blue-100 text-blue-700'}`}/>
                </div>
                <div className="col-span-2 flex justify-center">
                  <button type="button" onClick={()=>onPriceChange(up.unit,'is_auto',!up.is_auto)}
                    className={`w-10 h-5 rounded-full transition relative ${up.is_auto?'bg-blue-500':'bg-gray-300'}`}>
                    <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-all ${up.is_auto?'right-0.5':'left-0.5'}`}/>
                  </button>
                </div>
                <div className="col-span-1 flex justify-center">
                  <input type="checkbox" checked={up.is_active} onChange={e=>onPriceChange(up.unit,'is_active',e.target.checked)} className="w-4 h-4 accent-blue-600 cursor-pointer"/>
                </div>
                <div className="col-span-1 flex justify-center">
                  <button type="button" onClick={()=>onRemovePrice(up.unit)} className="text-red-400 hover:text-red-600 transition text-sm"><i className="fas fa-times"></i></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Product Modal ────────────────────────────────────────────────────────
const EMPTY_FORM = {
  name:'', category:'', price:'', cost:'', stock:'',
  barcode:'', image_url:'', is_active:true, description:'',
  base_unit:null, purchase_unit:null, min_stock:10,
};

const ProductModal = ({ open, product, categories, units, onClose, onSaved, toast }) => {
  const [form,        setForm]      = useState(EMPTY_FORM);
  const [saving,      setSaving]    = useState(false);
  const [loadingFull, setLoadingF]  = useState(false);  // ✅ جديد: loading عند جلب البيانات الكاملة
  const [imgError,    setImgError]  = useState(false);
  const [activeTab,   setActiveTab] = useState('basic');
  const [unitPrices,  setUnitPrices]= useState([]);
  const [savingPrices,setSavingP]   = useState(false);

  // ✅ الإصلاح الأساسي: عند التعديل نجيب البيانات الكاملة من GET /api/products/:id/
  useEffect(() => {
    if (!open) return;
    setActiveTab('basic');
    setImgError(false);

    if (product) {
      // نجيب البيانات الكاملة عشان ProductListSerializer مش فيه كل الحقول
      setLoadingF(true);
      productsAPI.getOne(product.id)
        .then(res => {
          const p = res.data;
          setForm({
            name:          p.name          || '',
            category:      p.category      || '',   // ✅ UUID من ProductSerializer الكامل
            price:         p.price         || '',
            cost:          p.cost          || '',   // ✅ موجود في ProductSerializer
            stock:         p.stock         ?? '',
            barcode:       p.barcode       || '',
            image_url:     p.image_url     || '',
            is_active:     p.is_active     ?? true,
            description:   p.description   || '',
            base_unit:     p.base_unit     || null, // ✅ UUID
            purchase_unit: p.purchase_unit || null, // ✅ UUID
            min_stock:     p.min_stock     ?? 10,
          });
          // unit_prices من ProductSerializer
          setUnitPrices(
            (p.unit_prices || []).map(up => ({
              unit:      up.unit,
              unit_name: up.unit_name,
              factor:    up.factor,
              price:     up.price,
              is_auto:   up.is_auto,
              is_active: up.is_active,
            }))
          );
        })
        .catch(() => toast('error', '❌ تعذّر تحميل بيانات المنتج'))
        .finally(() => setLoadingF(false));
    } else {
      setForm(EMPTY_FORM);
      setUnitPrices([]);
    }
  }, [open, product]);

  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const liveMargin = useMemo(() => {
    const p=parseFloat(form.price)||0, c=parseFloat(form.cost)||0;
    if (c<=0||p<=0) return null;
    return ((p-c)/c*100).toFixed(1);
  }, [form.price, form.cost]);

  const priceWarn = useMemo(() => {
    const p=parseFloat(form.price)||0, c=parseFloat(form.cost)||0;
    return c>0&&p>0&&p<c;
  }, [form.price, form.cost]);

  const handlePriceChange = (unitId, field, val) =>
    setUnitPrices(prev => prev.map(up => up.unit===unitId ? {...up,[field]:val} : up));

  const handleAddPrice = (unitId) => {
    const unit = units.find(u => u.id === unitId);
    if (!unit) return;
    const autoPrice = (parseFloat(form.price)||0) * parseFloat(unit.factor||1);
    setUnitPrices(prev => [...prev, {
      unit: unit.id, unit_name: unit.name, factor: unit.factor,
      price: autoPrice.toFixed(2), is_auto: true, is_active: true,
    }]);
  };

  const handleRemovePrice = (unitId) =>
    setUnitPrices(prev => prev.filter(up => up.unit !== unitId));

  const handleSubmit = async (e) => {
    e?.preventDefault();
    setSaving(true);
    try {
      let savedProduct;
      if (product) {
        const res = await productsAPI.update(product.id, form);
        savedProduct = res.data;
        toast('success', '✅ تم تحديث المنتج بنجاح');
      } else {
        const res = await productsAPI.create(form);
        savedProduct = res.data;
        toast('success', '✅ تم إضافة المنتج بنجاح');
      }
      if (unitPrices.length > 0 && savedProduct?.id) {
        setSavingP(true);
        try { await unitsAPI.setUnitPrices(savedProduct.id, unitPrices); }
        catch { toast('warning', '⚠️ تم حفظ المنتج لكن حدث خطأ في أسعار الوحدات'); }
        finally { setSavingP(false); }
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
    { key:'basic',   label:'البيانات الأساسية', icon:'fa-info-circle' },
    { key:'pricing', label:'التسعير والمخزون',  icon:'fa-tags'        },
    { key:'units',   label:'الوحدات والأسعار',  icon:'fa-ruler'       },
    { key:'media',   label:'الصورة والوصف',     icon:'fa-image'       },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-xl font-bold text-gray-800">
            <i className={`fas ${product?'fa-edit':'fa-plus-circle'} ml-2 text-blue-600`}></i>
            {product ? 'تعديل منتج' : 'إضافة منتج جديد'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>

        {/* ✅ Loading indicator عند جلب البيانات */}
        {loadingFull ? (
          <div className="flex-1 flex items-center justify-center py-20">
            <div className="text-center">
              <i className="fas fa-circle-notch fa-spin text-3xl text-blue-500 mb-3 block"></i>
              <p className="text-gray-500 text-sm font-bold">جاري تحميل بيانات المنتج...</p>
            </div>
          </div>
        ) : (
          <>
            {/* Tabs */}
            <div className="flex border-b px-6 overflow-x-auto">
              {tabs.map(t => (
                <button key={t.key} type="button" onClick={()=>setActiveTab(t.key)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-bold border-b-2 transition -mb-px whitespace-nowrap
                    ${activeTab===t.key?'border-blue-600 text-blue-600':'border-transparent text-gray-500 hover:text-gray-700'}`}>
                  <i className={`fas ${t.icon}`}></i>{t.label}
                </button>
              ))}
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-6 py-5 space-y-4">

              {/* ── basic ── */}
              {activeTab==='basic' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">اسم المنتج <span className="text-red-500">*</span></label>
                    <input type="text" required className="input-field"
                      value={form.name} onChange={e=>set('name',e.target.value)} placeholder="مثال: شوكولاتة كيت كات"/>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">الفئة <span className="text-red-500">*</span></label>
                    <select required className="input-field" value={form.category} onChange={e=>set('category',e.target.value)}>
                      <option value="">— اختر الفئة —</option>
                      {categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">الباركود</label>
                    <div className="relative">
                      <i className="fas fa-barcode absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
                      <input type="text" className="input-field pr-9"
                        value={form.barcode} onChange={e=>set('barcode',e.target.value)} placeholder="أدخل أو امسح الباركود"/>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl border">
                    <input type="checkbox" id="is_active" checked={form.is_active}
                      onChange={e=>set('is_active',e.target.checked)} className="w-4 h-4 accent-blue-600"/>
                    <label htmlFor="is_active" className="text-sm font-bold text-gray-700 cursor-pointer">
                      المنتج نشط (يظهر في نقطة البيع)
                    </label>
                  </div>
                </div>
              )}

              {/* ── pricing ── */}
              {activeTab==='pricing' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-1">سعر البيع (ر.س) <span className="text-red-500">*</span></label>
                      <input type="number" step="0.01" min="0" required className="input-field"
                        value={form.price} onChange={e=>set('price',e.target.value)} placeholder="0.00"/>
                    </div>
                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-1">التكلفة (ر.س) <span className="text-red-500">*</span></label>
                      <input type="number" step="0.01" min="0" required className="input-field"
                        value={form.cost} onChange={e=>set('cost',e.target.value)} placeholder="0.00"/>
                    </div>
                  </div>
                  {liveMargin!==null && (
                    <div className={`flex items-center gap-3 p-3 rounded-xl border text-sm font-bold
                      ${priceWarn?'bg-red-50 border-red-200 text-red-700':parseFloat(liveMargin)>=20?'bg-green-50 border-green-200 text-green-700':'bg-yellow-50 border-yellow-200 text-yellow-700'}`}>
                      <i className={`fas ${priceWarn?'fa-exclamation-triangle':'fa-chart-line'}`}></i>
                      {priceWarn?'⚠️ تحذير: السعر أقل من التكلفة!': `هامش الربح: ${liveMargin}%`}
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">
                      الكمية الافتراضية <span className="text-red-500">*</span>
                      {product && <span className="text-xs text-gray-400 mr-2">(للتعديل استخدم زر ± في الجدول)</span>}
                    </label>
                    <input type="number" min="0" required className="input-field"
                      value={form.stock} onChange={e=>set('stock',e.target.value)} placeholder="0" disabled={!!product}/>
                    {product && (
                      <p className="text-xs text-blue-600 mt-1">
                        <i className="fas fa-info-circle ml-1"></i>الكمية الحالية: <strong>{product.stock}</strong>
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">حد المخزون الأدنى للتنبيه</label>
                    <input type="number" min="0" className="input-field"
                      value={form.min_stock??10} onChange={e=>set('min_stock',e.target.value)} placeholder="10"/>
                  </div>
                </div>
              )}

              {/* ── units ── */}
              {activeTab==='units' && (
                <UomPricesTab form={form} set={set} units={units}
                  unitPrices={unitPrices}
                  onPriceChange={handlePriceChange}
                  onAddPrice={handleAddPrice}
                  onRemovePrice={handleRemovePrice}
                  isEdit={!!product}
                />
              )}

              {/* ── media ── */}
              {activeTab==='media' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">رابط الصورة</label>
                    <input type="url" className="input-field"
                      value={form.image_url}
                      onChange={e=>{set('image_url',e.target.value);setImgError(false);}}
                      placeholder="https://example.com/image.jpg"/>
                  </div>
                  {form.image_url && (
                    <div className="flex justify-center">
                      {imgError?(
                        <div className="w-40 h-40 rounded-xl bg-gray-100 border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-400">
                          <i className="fas fa-image text-3xl mb-2"></i>
                          <span className="text-xs">رابط الصورة غير صحيح</span>
                        </div>
                      ):(
                        <img src={form.image_url} alt="معاينة" onError={()=>setImgError(true)}
                          className="w-40 h-40 object-cover rounded-xl border-2 border-blue-200 shadow"/>
                      )}
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">الوصف</label>
                    <textarea className="input-field resize-none" rows="4"
                      value={form.description} onChange={e=>set('description',e.target.value)}
                      placeholder="وصف اختياري للمنتج..."/>
                  </div>
                </div>
              )}
            </form>

            {/* Footer */}
            <div className="px-6 py-4 border-t flex gap-3">
              <button type="button" onClick={handleSubmit} disabled={saving||savingPrices}
                className="flex-1 btn-primary flex items-center justify-center gap-2 disabled:opacity-60">
                {saving||savingPrices
                  ?<><i className="fas fa-circle-notch fa-spin"></i> جاري الحفظ...</>
                  :<><i className="fas fa-save"></i> حفظ المنتج</>}
              </button>
              <button type="button" onClick={onClose} disabled={saving}
                className="flex-1 btn-secondary flex items-center justify-center gap-2">
                <i className="fas fa-times"></i> إلغاء
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  Products — Main Component
// ══════════════════════════════════════════════════════════════════════════════
const Products = () => {
  const PAGE_KEY = 'products.list';
  const { hasAction } = useAuth();
  const canAdd    = hasAction(PAGE_KEY, 'products.add');
  const canDelete = hasAction(PAGE_KEY, 'products.delete');

  const { push: toast, ToastContainer } = useToast();

  const [products,    setProducts]    = useState([]);
  const [categories,  setCategories]  = useState([]);
  const [units,       setUnits]       = useState([]);
  const [stats,       setStats]       = useState({ total:0, active:0, lowStock:0, totalValue:0 });
  const [loading,     setLoading]     = useState(true);
  const [saving,      setSaving]      = useState(false);

  const [searchQuery,    setSearchQuery]    = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterStatus,   setFilterStatus]   = useState('');
  const [filterLowStock, setFilterLowStock] = useState(false);
  const [page,     setPage]     = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total,    setTotal]    = useState(0);
  const [sortBy,   setSortBy]   = useState('-created_at');
  const [selected,       setSelected]       = useState(new Set());
  const [adjustingId,    setAdjustingId]    = useState(null);
  const [showModal,      setShowModal]      = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [confirmState,   setConfirmState]   = useState({ open:false });
  const debounceRef = useRef(null);

  // ── Fetch categories + units مرة واحدة ────────────────────────────────
  useEffect(() => {
    categoriesAPI.getAll()
      .then(r => setCategories(r.data.results||r.data))
      .catch(() => toast('error','❌ تعذّر تحميل الفئات'));
    unitsAPI.getAll({ page_size:200 })
      .then(r => setUnits(r.data.results||r.data))
      .catch(() => {});
  }, []);

  // ── Fetch Products ─────────────────────────────────────────────────────
  const fetchProducts = useCallback(async ({
    q=searchQuery, category=filterCategory, status=filterStatus,
    lowStock=filterLowStock, pg=page, size=pageSize, ordering=sortBy, silent=false,
  }={}) => {
    try {
      if (!silent) setLoading(true);
      setSelected(new Set());
      const params = { page:pg, page_size:size, ordering };
      if (q)        params.search    = q;
      if (category) params.category  = category;
      if (status)   params.is_active = status;
      if (lowStock) params.stock__lt = LOW_STOCK_THRESHOLD;
      const res  = await productsAPI.getAll(params);
      const data = res.data.results ?? res.data;
      setProducts(data);
      setTotal(res.data.count ?? data.length);
      if (!silent) {
        productsAPI.getAll({ page_size:9999, is_active:'' }).then(all => {
          const d = all.data.results ?? all.data;
          setStats({
            total:      d.length,
            active:     d.filter(p=>p.is_active).length,
            lowStock:   d.filter(p=>p.stock<LOW_STOCK_THRESHOLD&&p.is_active).length,
            totalValue: d.reduce((s,p)=>s+(parseFloat(p.cost||0)*parseInt(p.stock||0)),0),
          });
        }).catch(()=>{});
      }
    } catch { toast('error','❌ تعذّر تحميل المنتجات'); }
    finally   { if (!silent) setLoading(false); }
  }, [searchQuery,filterCategory,filterStatus,filterLowStock,page,pageSize,sortBy]);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(()=>{setPage(1);fetchProducts({q:searchQuery,pg:1});},
      searchQuery?DEBOUNCE_MS:0);
    return ()=>clearTimeout(debounceRef.current);
  }, [searchQuery]);

  useEffect(()=>{setPage(1);fetchProducts({pg:1});},[filterCategory,filterStatus,filterLowStock,pageSize,sortBy]);
  useEffect(()=>{fetchProducts({pg:page});},[page]);

  const handleSort = f => setSortBy(p=>p===f?`-${f}`:f);
  const SortIcon = ({ field }) => {
    if (sortBy===field)       return <i className="fas fa-sort-up   text-blue-600 mr-1"></i>;
    if (sortBy===`-${field}`) return <i className="fas fa-sort-down text-blue-600 mr-1"></i>;
    return <i className="fas fa-sort text-gray-300 mr-1"></i>;
  };

  const allSelected = products.length>0 && products.every(p=>selected.has(p.id));
  const toggleSelectAll = ()=>allSelected?setSelected(new Set()):setSelected(new Set(products.map(p=>p.id)));
  const toggleSelect = id=>setSelected(prev=>{const n=new Set(prev);n.has(id)?n.delete(id):n.add(id);return n;});

  const handleBulkDelete = ()=>setConfirmState({
    open:true, title:'حذف متعدد', message:`حذف ${selected.size} منتج؟`,
    confirmLabel:`حذف ${selected.size}`, danger:true,
    onConfirm:async()=>{
      setConfirmState({open:false});setSaving(true);
      try{await Promise.all([...selected].map(id=>productsAPI.delete(id)));toast('success',`✅ تم حذف ${selected.size} منتج`);fetchProducts({silent:false});}
      catch{toast('error','❌ خطأ في الحذف');}finally{setSaving(false);}
    },
    onCancel:()=>setConfirmState({open:false}),
  });

  const handleBulkToggle = activate=>setConfirmState({
    open:true, title:activate?'تفعيل':'تعطيل',
    message:`${activate?'تفعيل':'تعطيل'} ${selected.size} منتج؟`,
    confirmLabel:`${activate?'تفعيل':'تعطيل'} ${selected.size}`, danger:!activate,
    onConfirm:async()=>{
      setConfirmState({open:false});setSaving(true);
      try{
        await Promise.all([...selected].map(id=>{const p=products.find(p=>p.id===id);return productsAPI.update(id,{...p,is_active:activate});}));
        toast('success',`✅ تم ${activate?'تفعيل':'تعطيل'} ${selected.size} منتج`);fetchProducts({silent:false});
      }catch{toast('error','❌ خطأ');}finally{setSaving(false);}
    },
    onCancel:()=>setConfirmState({open:false}),
  });

  const handleDelete = p=>setConfirmState({
    open:true, title:'حذف منتج', message:`حذف "${p.name}"؟`,
    confirmLabel:'حذف', danger:true,
    onConfirm:async()=>{
      setConfirmState({open:false});
      try{await productsAPI.delete(p.id);toast('success',`✅ تم حذف "${p.name}"`);fetchProducts({silent:false});}
      catch{toast('error','❌ خطأ في الحذف');}
    },
    onCancel:()=>setConfirmState({open:false}),
  });

  const handleStockDone = updated=>{
    setAdjustingId(null);
    if(updated){
      setProducts(prev=>prev.map(p=>p.id===updated.id?{...p,stock:updated.stock}:p));
      toast('success',`✅ تم تحديث مخزون "${updated.name}" إلى ${updated.stock}`);
    }
  };

  // ✅ فتح modal التعديل — نمرر الـ product من الجدول فقط (للـ id)
  // البيانات الكاملة هتتجلب داخل ProductModal من getOne
  const handleEdit = (product) => {
    setEditingProduct(product);
    setShowModal(true);
  };

  const totalPages = Math.ceil(total/pageSize)||1;
  const copyBarcode = b=>navigator.clipboard.writeText(b).then(()=>toast('info',`📋 تم نسخ: ${b}`));

  return (
    <div className="p-6 bg-gray-100 min-h-screen">
      <ToastContainer />
      <ConfirmModal {...confirmState} />
      <ProductModal
        open={showModal}
        product={editingProduct}
        categories={categories}
        units={units}
        onClose={()=>{setShowModal(false);setEditingProduct(null);}}
        onSaved={()=>fetchProducts({silent:false})}
        toast={toast}
      />

      {/* Header */}
      <div className="flex justify-between items-center mb-6 flex-wrap gap-3">
        <h1 className="text-3xl font-bold text-gray-800">
          <i className="fas fa-box ml-2 text-blue-600"></i>إدارة المنتجات
        </h1>
        <div className="flex gap-2 flex-wrap">
          <button onClick={()=>fetchProducts({silent:false})} disabled={loading}
            className="btn-secondary flex items-center gap-2">
            <i className={`fas fa-sync-alt ${loading?'fa-spin':''}`}></i>تحديث
          </button>
          {canAdd&&(
            <button onClick={()=>{setEditingProduct(null);setShowModal(true);}}
              className="btn-primary flex items-center gap-2">
              <i className="fas fa-plus"></i>إضافة منتج
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          {label:'إجمالي المنتجات',value:stats.total,   icon:'fa-box',                color:'from-blue-500 to-blue-600'},
          {label:'المنتجات النشطة',value:stats.active,  icon:'fa-check-circle',        color:'from-green-500 to-green-600'},
          {label:'مخزون منخفض',    value:stats.lowStock,icon:'fa-exclamation-triangle',color:stats.lowStock>0?'from-red-500 to-red-600':'from-gray-400 to-gray-500'},
          {label:'قيمة المخزون',   value:`${stats.totalValue.toLocaleString('ar-SA',{maximumFractionDigits:0})} ر.س`,icon:'fa-coins',color:'from-purple-500 to-purple-600'},
        ].map(s=>(
          <div key={s.label} className={`bg-gradient-to-br ${s.color} text-white rounded-2xl p-4 shadow`}>
            <div className="flex items-center justify-between">
              <div><p className="text-white/80 text-sm mb-1">{s.label}</p><p className="text-2xl font-bold">{s.value}</p></div>
              <i className={`fas ${s.icon} text-4xl opacity-20`}></i>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl shadow p-4 mb-5 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs font-bold text-gray-500 block mb-1">بحث</label>
          <div className="relative">
            <i className="fas fa-search absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
            <input type="text" className="input-field pr-9" placeholder="اسم المنتج أو الباركود..."
              value={searchQuery} onChange={e=>setSearchQuery(e.target.value)}/>
          </div>
        </div>
        <div className="min-w-[160px]">
          <label className="text-xs font-bold text-gray-500 block mb-1">الفئة</label>
          <select className="input-field" value={filterCategory} onChange={e=>setFilterCategory(e.target.value)}>
            <option value="">كل الفئات</option>
            {categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div className="min-w-[140px]">
          <label className="text-xs font-bold text-gray-500 block mb-1">الحالة</label>
          <select className="input-field" value={filterStatus} onChange={e=>setFilterStatus(e.target.value)}>
            <option value="">الكل</option>
            <option value="true">نشط فقط</option>
            <option value="false">غير نشط</option>
          </select>
        </div>
        <div className="flex items-center gap-2 min-w-[140px]">
          <input type="checkbox" id="lowStockFilter" checked={filterLowStock}
            onChange={e=>setFilterLowStock(e.target.checked)} className="w-4 h-4 accent-red-600"/>
          <label htmlFor="lowStockFilter" className="text-sm font-bold text-red-600 cursor-pointer whitespace-nowrap">
            <i className="fas fa-exclamation-triangle ml-1"></i>مخزون منخفض فقط
          </label>
        </div>
        <div className="min-w-[100px]">
          <label className="text-xs font-bold text-gray-500 block mb-1">لكل صفحة</label>
          <select className="input-field" value={pageSize} onChange={e=>setPageSize(Number(e.target.value))}>
            {PAGE_SIZE_OPTIONS.map(n=><option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        {(searchQuery||filterCategory||filterStatus||filterLowStock)&&(
          <button onClick={()=>{setSearchQuery('');setFilterCategory('');setFilterStatus('');setFilterLowStock(false);}}
            className="text-sm text-gray-500 hover:text-red-600 font-bold transition flex items-center gap-1 mt-5">
            <i className="fas fa-times-circle"></i> مسح الفلاتر
          </button>
        )}
      </div>

      {/* Bulk bar */}
      {selected.size>0&&(
        <div className="bg-blue-600 text-white rounded-2xl px-5 py-3 mb-4 flex items-center justify-between gap-3 flex-wrap shadow-lg">
          <span className="font-bold"><i className="fas fa-check-square ml-2"></i>تم تحديد {selected.size} منتج</span>
          <div className="flex gap-2 flex-wrap">
            <button onClick={()=>handleBulkToggle(true)}  className="bg-green-500 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-bold transition"><i className="fas fa-eye ml-1"></i>تفعيل</button>
            <button onClick={()=>handleBulkToggle(false)} className="bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-1.5 rounded-lg text-sm font-bold transition"><i className="fas fa-eye-slash ml-1"></i>تعطيل</button>
            {canDelete&&<button onClick={handleBulkDelete} className="bg-red-500 hover:bg-red-600 text-white px-3 py-1.5 rounded-lg text-sm font-bold transition"><i className="fas fa-trash ml-1"></i>حذف</button>}
            <button onClick={()=>setSelected(new Set())} className="bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded-lg text-sm font-bold transition"><i className="fas fa-times ml-1"></i>إلغاء</button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-2xl shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="px-4 py-3 w-10"><input type="checkbox" checked={allSelected} onChange={toggleSelectAll} className="w-4 h-4 accent-blue-600"/></th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600 cursor-pointer hover:text-blue-600" onClick={()=>handleSort('name')}><SortIcon field="name"/>المنتج</th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600">الفئة</th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600 cursor-pointer hover:text-blue-600" onClick={()=>handleSort('price')}><SortIcon field="price"/>سعر البيع</th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600 cursor-pointer hover:text-blue-600" onClick={()=>handleSort('cost')}><SortIcon field="cost"/>التكلفة</th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600">هامش الربح</th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600">الوحدة</th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600 cursor-pointer hover:text-blue-600" onClick={()=>handleSort('stock')}><SortIcon field="stock"/>المخزون</th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600">الحالة</th>
                <th className="px-4 py-3 text-right text-sm font-bold text-gray-600">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {loading?([...Array(5)].map((_,i)=><SkeletonRow key={i}/>))
              :products.length===0?(
                <tr><td colSpan="10" className="text-center py-16">
                  <i className="fas fa-box-open text-6xl text-gray-300 mb-4 block"></i>
                  <p className="text-gray-500 font-semibold">لا توجد منتجات مطابقة</p>
                </td></tr>
              ):products.map(product=>(
                <tr key={product.id} className={`border-b transition hover:bg-gray-50 ${selected.has(product.id)?'bg-blue-50':''}`}>
                  <td className="px-4 py-3"><input type="checkbox" checked={selected.has(product.id)} onChange={()=>toggleSelect(product.id)} className="w-4 h-4 accent-blue-600"/></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {product.image_url?(<img src={product.image_url} alt={product.name} className="w-12 h-12 object-cover rounded-xl border"/>):(
                        <div className="w-12 h-12 rounded-xl bg-gray-100 border flex items-center justify-center text-gray-400"><i className="fas fa-box"></i></div>
                      )}
                      <div>
                        <p className="font-bold text-gray-800 text-sm">{product.name}</p>
                        {product.barcode&&(<button onClick={()=>copyBarcode(product.barcode)} className="text-xs text-gray-400 hover:text-blue-600 transition flex items-center gap-1 mt-0.5"><i className="fas fa-barcode"></i>{product.barcode}</button>)}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {product.category_name?(<span className="px-2 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700">{product.category_name}</span>):<span className="text-gray-400 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3 font-bold text-gray-800">{parseFloat(product.price).toFixed(2)} ر.س</td>
                  <td className="px-4 py-3 text-gray-600">{parseFloat(product.cost||0).toFixed(2)} ر.س</td>
                  <td className="px-4 py-3"><ProfitBadge margin={product.profit_margin}/></td>
                  <td className="px-4 py-3">
                    {product.base_unit_name?(<span className="px-2 py-1 rounded-full text-xs font-bold bg-purple-50 text-purple-700"><i className="fas fa-ruler ml-1"></i>{product.base_unit_name}</span>):<span className="text-gray-400 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    {adjustingId===product.id?(
                      <InlineStockAdjust product={product} onDone={handleStockDone} onError={msg=>toast('error',`❌ ${msg}`)}/>
                    ):(
                      <div className="flex items-center gap-2">
                        <StockBadge stock={product.stock}/>
                        <button onClick={()=>setAdjustingId(product.id)} className="text-xs text-blue-600 hover:text-blue-800 font-bold transition" title="تعديل المخزون"><i className="fas fa-edit"></i></button>
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-bold ${product.is_active?'bg-green-100 text-green-700':'bg-gray-100 text-gray-500'}`}>
                      {product.is_active?'نشط':'معطّل'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button onClick={()=>handleEdit(product)} className="text-blue-600 hover:text-blue-800 transition" title="تعديل"><i className="fas fa-edit"></i></button>
                      {canDelete&&(<button onClick={()=>handleDelete(product)} className="text-red-500 hover:text-red-700 transition" title="حذف"><i className="fas fa-trash"></i></button>)}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {totalPages>1&&(
          <div className="px-6 py-4 border-t flex items-center justify-between flex-wrap gap-3">
            <span className="text-sm text-gray-500">عرض {((page-1)*pageSize)+1}–{Math.min(page*pageSize,total)} من {total}</span>
            <div className="flex gap-2">
              <button onClick={()=>setPage(1)} disabled={page===1} className="px-3 py-1.5 rounded-lg border text-sm font-bold disabled:opacity-40 hover:bg-gray-50">«</button>
              <button onClick={()=>setPage(p=>Math.max(1,p-1))} disabled={page===1} className="px-3 py-1.5 rounded-lg border text-sm font-bold disabled:opacity-40 hover:bg-gray-50">‹</button>
              {[...Array(Math.min(5,totalPages))].map((_,i)=>{
                const pg=Math.max(1,Math.min(totalPages-4,page-2))+i;
                return(<button key={pg} onClick={()=>setPage(pg)} className={`px-3 py-1.5 rounded-lg border text-sm font-bold transition ${page===pg?'bg-blue-600 text-white border-blue-600':'hover:bg-gray-50'}`}>{pg}</button>);
              })}
              <button onClick={()=>setPage(p=>Math.min(totalPages,p+1))} disabled={page===totalPages} className="px-3 py-1.5 rounded-lg border text-sm font-bold disabled:opacity-40 hover:bg-gray-50">›</button>
              <button onClick={()=>setPage(totalPages)} disabled={page===totalPages} className="px-3 py-1.5 rounded-lg border text-sm font-bold disabled:opacity-40 hover:bg-gray-50">»</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Products;
"""

# ── Main ─────────────────────────────────────────────────────────────────────
print("="*60)
print("  fix_products_edit.py — إصلاح اختفاء البيانات عند التعديل")
print("="*60)
print()
print("  السبب: ProductListSerializer مش فيه cost/category UUID")
print("  الحل:  عند فتح modal التعديل، نجيب GET /api/products/:id/")
print("         اللي بيرجع ProductSerializer الكامل")
print()

backup(PRODUCTS)
write_file(PRODUCTS, PRODUCTS_JSX)

ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
with open(CHLOG, "a", encoding="utf-8") as f:
    f.write(
        f"\n## [{ts}] fix_products_edit\n"
        "- Fix: اختفاء البيانات عند التعديل (category, cost, base_unit, purchase_unit, min_stock)\n"
        "- السبب: ProductListSerializer مش فيه كل الحقول\n"
        "- الحل: productsAPI.getOne(id) داخل ProductModal عند فتح التعديل\n"
        "- أضفنا loading spinner أثناء جلب البيانات الكاملة\n"
        "- أضفنا تبويب الوحدات والأسعار + unitsAPI\n"
    )
print("  ✅ CHANGELOG updated")
print()
print("✅ تم! شغّل:")
print("   python3 fix_products_edit.py")
