import { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { productsAPI, categoriesAPI, salesAPI, customersAPI } from '../services/api';
import { useCart }  from '../context/CartContext';
import { useAuth }  from '../context/AuthContext';

const STOCK_REFRESH_MS = 30_000; // 30 ثانية
const VISIBILITY_THROTTLE_MS = 2_000; // throttle الـ visibility change

// ─── StockBadge ───────────────────────────────────────────
const StockBadge = ({ stock }) => {
  const color = stock < 10 ? 'text-red-600' : stock < 30 ? 'text-orange-500' : 'text-green-600';
  return (
    <span className={`text-sm font-semibold ${color}`}>
      <i className="fas fa-box ml-1"></i>{stock}
    </span>
  );
};

// ─── POS ──────────────────────────────────────────────────
const POS = () => {
  const { user } = useAuth();
  const [products,         setProducts]         = useState([]);
  const [categories,       setCategories]       = useState([]);
  const [customers,        setCustomers]        = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery,      setSearchQuery]      = useState('');

  // Loading flags منفصلة
  const [initialLoading,  setInitialLoading]  = useState(true);
  const [productsLoading, setProductsLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [initError,       setInitError]       = useState(null);

  // useRef لمنع stale closure في الـ intervals
  const selectedCategoryRef = useRef(selectedCategory);
  const searchQueryRef      = useRef(searchQuery);
  const lastVisibilityRef   = useRef(0);

  useEffect(() => { selectedCategoryRef.current = selectedCategory; }, [selectedCategory]);
  useEffect(() => { searchQueryRef.current = searchQuery; }, [searchQuery]);

  const cartItemsRef = useRef(null);
  const lastItemRef  = useRef(null);
  const paidInputRef = useRef(null);

  const {
    tabs, activeTabId, setActiveTabId, createTab, closeTab,
    cart, customer, paymentMethod, discount, tax, paidAmount,
    lastAddedItemId,
    addToCart, removeFromCart, updateQuantity, clearCart,
    setCustomer, setPaymentMethod, setDiscount, setTax, setPaidAmount,
    getSubtotal, getTotal,
  } = useCart();

  // ─── Auto-scroll للعنصر المضاف ───────────────────────
  useEffect(() => {
    if (lastAddedItemId && lastItemRef.current) {
      lastItemRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [lastAddedItemId]);

  // ─── fetchProducts ────────────────────────────────────
  // silent = true → بدون loader (للـ auto-refresh)
  const fetchProducts = useCallback(async ({ silent = false, category, search } = {}) => {
    const cat = category  !== undefined ? category  : selectedCategoryRef.current;
    const q   = search    !== undefined ? search    : searchQueryRef.current;
    try {
      if (!silent) setProductsLoading(true);
      const params = {};
      if (cat) params.category = cat;
      if (q)   params.search   = q;
      const res = await productsAPI.getAll(params);
      setProducts(res.data.results || res.data);
    } catch (err) {
      console.error('Products fetch error:', err);
    } finally {
      if (!silent) setProductsLoading(false);
    }
  }, []);

  // ─── Initial data (Promise.all) ───────────────────────
  useEffect(() => {
    const init = async () => {
      try {
        setInitialLoading(true);
        setInitError(null);
        const [catRes, prodRes, custRes] = await Promise.all([
          categoriesAPI.getAll(),
          productsAPI.getAll(),
          customersAPI.getAll(),
        ]);
        setCategories(catRes.data.results  || catRes.data);
        setProducts(  prodRes.data.results || prodRes.data);
        setCustomers( custRes.data.results || custRes.data);
      } catch (err) {
        console.error('Init error:', err);
        setInitError('تعذّر تحميل البيانات. تحقق من الاتصال بالخادم.');
      } finally {
        setInitialLoading(false);
      }
    };
    init();
  }, []);

  // ─── Refetch عند تغيير الفلتر أو البحث ──────────────
  useEffect(() => {
    if (!initialLoading) {
      fetchProducts({ silent: false, category: selectedCategory, search: searchQuery });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCategory, searchQuery]);

  // ─── Auto-refresh كل 30 ثانية (silent) ───────────────
  useEffect(() => {
    const id = setInterval(() => fetchProducts({ silent: true }), STOCK_REFRESH_MS);
    return () => clearInterval(id);
  }, [fetchProducts]);

  // ─── Visibility change (silent + throttle) ───────────
  useEffect(() => {
    const handle = () => {
      if (
        document.visibilityState === 'visible' &&
        Date.now() - lastVisibilityRef.current > VISIBILITY_THROTTLE_MS
      ) {
        lastVisibilityRef.current = Date.now();
        fetchProducts({ silent: true });
      }
    };
    document.addEventListener('visibilitychange', handle);
    return () => document.removeEventListener('visibilitychange', handle);
  }, [fetchProducts]);

  // ─── Keyboard shortcut للمدفوع ───────────────────────
  useEffect(() => {
    const onKeyDown = (e) => {
      const tag = e.target?.tagName?.toLowerCase();
      if (['input','textarea','select'].includes(tag) || e.target?.isContentEditable) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (!/^\d$/.test(e.key) && e.key !== '.') return;
      if (!cart || cart.length === 0) return;
      e.preventDefault();
      const next = `${paidAmount || ''}${e.key}`;
      setPaidAmount(next);
      setTimeout(() => {
        const el = paidInputRef.current;
        if (!el) return;
        el.focus();
        const len = String(next).length;
        el.setSelectionRange?.(len, len);
      }, 0);
    };
    window.addEventListener('keydown', onKeyDown, { capture: true });
    return () => window.removeEventListener('keydown', onKeyDown, { capture: true });
  }, [cart, paidAmount, setPaidAmount]);

  // ─── Tab helpers ──────────────────────────────────────
  const closeOrResetCurrentTab = () => {
    if (tabs.length > 1) { closeTab(activeTabId); return; }
    clearCart();
  };

  const focusPaidInput = () => {
    setTimeout(() => {
      paidInputRef.current?.focus();
      paidInputRef.current?.select?.();
    }, 0);
  };

  const handleCreateNewTab = () => {
    createTab({ switchTo: true });
    focusPaidInput();
  };

  // ─── Optimistic stock update + rollback ──────────────
  const applyOptimisticStockDecrease = useCallback(() => {
    setProducts((prev) =>
      prev.map((p) => {
        const item = cart.find((c) => c.id === p.id);
        return item ? { ...p, stock: Math.max(0, p.stock - item.quantity) } : p;
      })
    );
  }, [cart]);

  // ─── Checkout ─────────────────────────────────────────
  const handleCheckout = async () => {
    if (cart.length === 0) { alert('السلة فارغة!'); return; }

    setCheckoutLoading(true);
    const snapshot = [...products]; // للـ rollback

    try {
      const subtotal       = getSubtotal();
      const discountAmount = (subtotal * discount) / 100;
      const taxAmount      = ((subtotal - discountAmount) * tax) / 100;
      const total          = getTotal();

      const saleData = {
        customer:       customer || null,
        subtotal:       subtotal.toFixed(2),
        discount:       discountAmount.toFixed(2),
        tax:            taxAmount.toFixed(2),
        total:          total.toFixed(2),
        payment_method: paymentMethod,
        status:         'completed',
        items: cart.map((item) => ({
          product_id:   item.id,
          product_name: item.name,
          quantity:     item.quantity,
          price:        item.price,
        })),
      };

      // Optimistic UI قبل الـ API call
      applyOptimisticStockDecrease();

      await salesAPI.create(saleData);
      alert('تمت عملية البيع بنجاح! ✓');
      closeOrResetCurrentTab();
      fetchProducts({ silent: true }); // silent refresh بعد البيع
    } catch (err) {
      console.error('Checkout error:', err);
      // Rollback عند فشل الـ API
      setProducts(snapshot);
      alert('حدث خطأ أثناء إتمام عملية البيع. يرجى المحاولة مجددًا.');
    } finally {
      setCheckoutLoading(false);
    }
  };

  // ─── Loading Screen ───────────────────────────────────
  if (initialLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-center">
          <i className="fas fa-spinner fa-spin text-6xl text-blue-600"></i>
          <p className="mt-4 text-gray-600 text-lg">جاري تحميل نظام البيع...</p>
        </div>
      </div>
    );
  }

  // ─── Error Screen ─────────────────────────────────────
  if (initError) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-center bg-white p-8 rounded-2xl shadow-lg max-w-md">
          <i className="fas fa-exclamation-circle text-6xl text-red-500 mb-4"></i>
          <p className="text-gray-700 font-semibold mb-6">{initError}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition"
          >
            <i className="fas fa-redo ml-2"></i>إعادة التحميل
          </button>
        </div>
      </div>
    );
  }

  // ─── Main Render ──────────────────────────────────────
  return (
    <div className="flex h-screen bg-gray-100 relative pt-12">

      {/* Tabs Bar */}
      <div className="absolute top-0 left-0 right-0 bg-white border-b z-20">
        <div className="flex items-center gap-2 px-4 py-2 overflow-x-auto">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTabId(t.id)}
              className={`flex items-center gap-2 px-3 py-1 rounded-full border whitespace-nowrap transition ${
                t.id === activeTabId
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-gray-50 text-gray-700 hover:bg-gray-100 border-gray-200'
              }`}
            >
              <span className="text-sm font-medium">{t.name}</span>
              <span className="text-xs opacity-80">
                ({t.cart?.reduce((s, i) => s + (i.quantity || 0), 0) || 0})
              </span>
              <span
                role="button"
                onClick={(e) => {
                  e.stopPropagation();
                  if ((t.cart?.length || 0) > 0 && !window.confirm('يوجد أصناف داخل هذه العملية. هل تريد إغلاقها؟')) return;
                  closeTab(t.id);
                }}
                className="ml-1 inline-flex items-center justify-center w-5 h-5 rounded-full hover:bg-black/10"
              >✕</span>
            </button>
          ))}
          <button
            onClick={handleCreateNewTab}
            className="px-3 py-1 rounded-full border border-dashed border-gray-300 text-gray-700 hover:bg-gray-50 whitespace-nowrap"
          >
            + عملية جديدة
          </button>
        </div>
      </div>

      {/* Products Section */}
      <div className="flex-1 p-6 overflow-y-auto">
        {/* Search + actions */}
        <div className="mb-4 flex gap-2">
          <input
            type="text"
            placeholder="البحث عن منتج أو مسح الباركود..."
            className="input-field flex-1"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button
            onClick={() => fetchProducts({ silent: false })}
            disabled={productsLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
            title="تحديث المخزون"
          >
            <i className={`fas fa-sync-alt ${productsLoading ? 'fa-spin' : ''}`}></i>
          </button>
          <Link
            to="/pos/barcode"
            className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition whitespace-nowrap"
          >
            <i className="fas fa-barcode ml-2"></i>وضع الباركود
          </Link>
        </div>

        {/* Categories */}
        <div className="flex gap-2 overflow-x-auto pb-2 mb-4">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-4 py-2 rounded-lg font-semibold whitespace-nowrap transition ${
              selectedCategory === null ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
            }`}
          >
            <i className="fas fa-th ml-1"></i>الكل
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-4 py-2 rounded-lg font-semibold whitespace-nowrap transition ${
                selectedCategory === cat.id ? 'text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
              style={{ backgroundColor: selectedCategory === cat.id ? cat.color : '' }}
            >
              {cat.icon && <i className={`${cat.icon} ml-1`}></i>}
              {cat.name}
            </button>
          ))}
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {productsLoading ? (
            // Skeleton Cards
            [...Array(8)].map((_, i) => (
              <div key={i} className="card animate-pulse">
                <div className="w-full h-32 bg-gray-200 rounded-lg mb-3"></div>
                <div className="h-4 bg-gray-200 rounded mb-2 w-3/4"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))
          ) : products.length === 0 ? (
            <div className="col-span-full text-center py-10">
              <i className="fas fa-box-open text-6xl text-gray-300 mb-4 block"></i>
              <p className="text-gray-500">لا توجد منتجات</p>
            </div>
          ) : (
            products.map((product) => (
              <div
                key={product.id}
                onClick={() => addToCart(product)}
                className="card cursor-pointer hover:shadow-lg transition-shadow"
              >
                {product.image_url && (
                  <img
                    src={product.image_url}
                    alt={product.name}
                    className="w-full h-32 object-cover rounded-lg mb-3"
                  />
                )}
                <h3 className="font-semibold text-gray-800 mb-2">{product.name}</h3>
                <div className="flex justify-between items-center">
                  <span className="text-lg font-bold text-blue-600">{product.price} ر.س</span>
                  <StockBadge stock={product.stock} />
                </div>
                {product.category_name && (
                  <span
                    className="inline-block mt-2 px-2 py-1 text-xs rounded-full text-white"
                    style={{ backgroundColor: product.category_color }}
                  >
                    {product.category_name}
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Cart Section */}
      <div className="w-96 bg-white shadow-lg p-6 flex flex-col">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">
          <i className="fas fa-shopping-cart ml-2"></i>سلة المشتريات
        </h2>

        <div className="flex-1 overflow-y-auto mb-4" ref={cartItemsRef}>
          {cart.length === 0 ? (
            <div className="text-center py-10">
              <i className="fas fa-shopping-basket text-6xl text-gray-300 mb-4 block"></i>
              <p className="text-gray-500">السلة فارغة</p>
            </div>
          ) : (
            <div className="space-y-3">
              {cart.map((item) => (
                <div
                  key={item.id}
                  ref={lastAddedItemId === item.id ? lastItemRef : null}
                  className={`border rounded-lg p-3 transition-all duration-500 ${
                    lastAddedItemId === item.id
                      ? 'border-green-500 bg-green-50 shadow-lg scale-105 ring-2 ring-green-400'
                      : 'border-gray-200 bg-white'
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-gray-800">{item.name}</h4>
                      {lastAddedItemId === item.id && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-green-500 text-white animate-pulse">
                          <i className="fas fa-check ml-1"></i>جديد
                        </span>
                      )}
                    </div>
                    <button onClick={() => removeFromCart(item.id)} className="text-red-500 hover:text-red-700 transition">
                      <i className="fas fa-trash"></i>
                    </button>
                  </div>
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-2 space-x-reverse">
                      <button onClick={() => updateQuantity(item.id, item.quantity - 1)} className="w-8 h-8 bg-gray-200 rounded hover:bg-gray-300 font-bold transition">-</button>
                      <span className="w-12 text-center font-semibold">{item.quantity}</span>
                      <button onClick={() => updateQuantity(item.id, item.quantity + 1)} className="w-8 h-8 bg-gray-200 rounded hover:bg-gray-300 font-bold transition">+</button>
                    </div>
                    <div className="text-left">
                      <p className="text-sm text-gray-500">{item.price} ر.س</p>
                      <p className="font-bold text-blue-600">{(item.price * item.quantity).toFixed(2)} ر.س</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {cart.length > 0 && (
          <div className="border-t pt-4 space-y-3">
            {/* Discount + Tax */}
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="text-sm text-gray-600 block mb-1">الخصم %</label>
                <input type="number" min="0" max="100" value={discount} onChange={(e) => setDiscount(Number(e.target.value))} className="input-field" />
              </div>
              <div className="flex-1">
                <label className="text-sm text-gray-600 block mb-1">الضريبة %</label>
                <input type="number" min="0" max="100" value={tax} onChange={(e) => setTax(Number(e.target.value))} className="input-field" />
              </div>
            </div>

            {/* Customer */}
            <div>
              <label className="text-sm text-gray-600 block mb-2">
                <i className="fas fa-user ml-1"></i>العميل ({customers.length} متاح)
              </label>
              <select
                value={customer || ''}
                onChange={(e) => setCustomer(e.target.value || null)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-right"
              >
                <option value="">بدون عميل (زائر)</option>
                {customers.map((c) => <option key={c.id} value={c.id}>{c.name} — {c.phone}</option>)}
              </select>
              {customer && <p className="text-xs text-green-600 mt-1">✓ تم اختيار العميل</p>}
            </div>

            {/* Payment Method */}
            <div>
              <label className="text-sm text-gray-600 block mb-2">طريقة الدفع</label>
              <select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)} className="input-field">
                <option value="cash">نقدي</option>
                <option value="card">بطاقة</option>
                <option value="both">نقدي + بطاقة</option>
              </select>
            </div>

            {/* Summary */}
            <div className="space-y-2 bg-gray-50 p-3 rounded-lg">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">المجموع الفرعي:</span>
                <span className="font-semibold">{getSubtotal().toFixed(2)} ر.س</span>
              </div>
              {discount > 0 && (
                <div className="flex justify-between text-sm text-green-600">
                  <span>الخصم ({discount}%):</span>
                  <span>-{((getSubtotal() * discount) / 100).toFixed(2)} ر.س</span>
                </div>
              )}
              {tax > 0 && (
                <div className="flex justify-between text-sm text-blue-600">
                  <span>الضريبة ({tax}%):</span>
                  <span>+{(((getSubtotal() - (getSubtotal() * discount) / 100) * tax) / 100).toFixed(2)} ر.س</span>
                </div>
              )}
              <div className="flex justify-between text-lg font-bold border-t pt-2">
                <span>الإجمالي:</span>
                <span className="text-blue-600">{getTotal().toFixed(2)} ر.س</span>
              </div>

              {/* Paid Amount */}
              <div className="mt-3 space-y-2 border-t pt-3">
                <div className="flex items-center justify-between gap-3">
                  <label className="text-sm text-gray-700 font-semibold whitespace-nowrap">المدفوع:</label>
                  <input
                    type="number"
                    ref={paidInputRef}
                    min="0"
                    step="0.01"
                    value={paidAmount}
                    onChange={(e) => setPaidAmount(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleCheckout(); } }}
                    className="w-40 p-2 border rounded text-right"
                    placeholder="0.00"
                  />
                </div>
                {paidAmount && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">الباقي / المتبقي:</span>
                    <span className={`font-bold ${(parseFloat(paidAmount) - getTotal()) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                      {(() => {
                        const diff = parseFloat(paidAmount || 0) - getTotal();
                        return `${diff >= 0 ? 'باقي' : 'متبقي'}: ${Math.abs(diff).toFixed(2)} ر.س`;
                      })()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-2">
              <button
                onClick={handleCheckout}
                disabled={checkoutLoading}
                className="w-full btn-success py-3 text-lg disabled:opacity-60 disabled:cursor-not-allowed transition"
              >
                {checkoutLoading
                  ? <><i className="fas fa-circle-notch fa-spin ml-2"></i>جاري الحفظ...</>
                  : <><i className="fas fa-check-circle ml-2"></i>إتمام عملية البيع</>
                }
              </button>
              <button
                onClick={closeOrResetCurrentTab}
                disabled={checkoutLoading}
                className="w-full btn-danger disabled:opacity-60 transition"
              >
                <i className="fas fa-times-circle ml-2"></i>إلغاء
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default POS;
