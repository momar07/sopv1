#!/usr/bin/env python3
"""
fix_02_restrict_stock_adjustment.py
=====================================
النقطة الثانية: أمين المخزن لا يزيد المخزون إلا بأمر شراء.

التغييرات:
  1. inventory/views.py
       - StockAdjustmentViewSet.perform_create:
         يمنع quantity_change > 0 إلا لو المستخدم في
         مجموعة Admins أو Managers أو superuser.

  2. InventoryPage.jsx
       - AdjustPanel: يخفي حقل الكمية الموجبة ويخفي
         زر "تطبيق التسوية" لأمين المخزن تماماً،
         ويظهر رسالة توضيحية بدلاً منه.
       - يُضاف استدعاء useAuth للحصول على user groups.
"""

import os, shutil, sys
from datetime import datetime

BASE     = os.path.dirname(os.path.abspath(__file__))
VIEWS    = os.path.join(BASE, 'pos_backend',   'inventory', 'views.py')
INV_PAGE = os.path.join(BASE, 'pos_frontend',  'src', 'pages', 'InventoryPage.jsx')

# ─── التحقق ───────────────────────────────────────────────────────────────
for path in [VIEWS, INV_PAGE]:
    if not os.path.exists(path):
        print(f'❌  الملف غير موجود: {path}')
        sys.exit(1)

# ─── نسخ احتياطية ─────────────────────────────────────────────────────────
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
for path in [VIEWS, INV_PAGE]:
    bak = path + f'.bak_{stamp}'
    shutil.copy2(path, bak)
    print(f'✅  نسخة احتياطية: {os.path.basename(bak)}')

# ══════════════════════════════════════════════════════════════════════════
#  1) inventory/views.py  — تقييد StockAdjustmentViewSet
# ══════════════════════════════════════════════════════════════════════════
with open(VIEWS, 'r', encoding='utf-8') as f:
    views_src = f.read()

OLD_PERFORM = """    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ── StockAlert ────────────────────────────────────────────"""

NEW_PERFORM = """    def perform_create(self, serializer):
        user   = self.request.user
        change = serializer.validated_data.get('quantity_change', 0)

        # ✅ أمين المخزن لا يقدر يزيد المخزون يدوياً
        if change > 0:
            allowed_groups = {'Admins', 'Managers'}
            user_groups    = set(user.groups.values_list('name', flat=True))
            is_allowed     = user.is_superuser or bool(allowed_groups & user_groups)

            if not is_allowed:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    'غير مصرح: لا يمكن زيادة المخزون يدوياً. '
                    'يجب إنشاء أمر شراء واستلامه لزيادة الكمية.'
                )

        serializer.save(user=user)


# ── StockAlert ────────────────────────────────────────────"""

if OLD_PERFORM not in views_src:
    print('⚠️  لم يُعثر على perform_create في StockAdjustmentViewSet')
    sys.exit(1)

views_src = views_src.replace(OLD_PERFORM, NEW_PERFORM, 1)

with open(VIEWS, 'w', encoding='utf-8') as f:
    f.write(views_src)
print('✅  inventory/views.py — تم تحديث StockAdjustmentViewSet')

# ══════════════════════════════════════════════════════════════════════════
#  2) InventoryPage.jsx — تقييد AdjustPanel في الواجهة
# ══════════════════════════════════════════════════════════════════════════
with open(INV_PAGE, 'r', encoding='utf-8') as f:
    inv_src = f.read()

# ── 2a: إضافة import لـ useAuth ─────────────────────────────────────────
OLD_IMPORT = "import { inventoryAPI, productsAPI } from '../services/api';"
NEW_IMPORT = """import { inventoryAPI, productsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';"""

if OLD_IMPORT in inv_src:
    inv_src = inv_src.replace(OLD_IMPORT, NEW_IMPORT, 1)
    print('✅  InventoryPage.jsx — تم إضافة import useAuth')
else:
    print('⚠️  import useAuth موجود مسبقاً أو تغيّر — تخطّي')

# ── 2b: تعديل AdjustPanel لإضافة role check ──────────────────────────────
OLD_ADJUST_FUNC = """// Stock Adjustment
function AdjustPanel() {
  const [adjustments, setAdj]   = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [form, setForm]         = useState({ product:'', quantity_change:'', reason:'count', notes:'' });
  const [saving, setSaving]     = useState(false);
  const [toast, setToast]       = useState(null);
  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };"""

NEW_ADJUST_FUNC = """// Stock Adjustment
function AdjustPanel() {
  const { user }                = useAuth();
  // ✅ أمين المخزن لا يقدر يزيد المخزون يدوياً
  const userGroups              = user?.groups?.map(g => g.name) || [];
  const canIncreaseStock        = user?.is_superuser ||
                                  userGroups.includes('Admins') ||
                                  userGroups.includes('Managers');

  const [adjustments, setAdj]   = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [form, setForm]         = useState({ product:'', quantity_change:'', reason:'count', notes:'' });
  const [saving, setSaving]     = useState(false);
  const [toast, setToast]       = useState(null);
  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };"""

if OLD_ADJUST_FUNC in inv_src:
    inv_src = inv_src.replace(OLD_ADJUST_FUNC, NEW_ADJUST_FUNC, 1)
    print('✅  InventoryPage.jsx — تم إضافة canIncreaseStock في AdjustPanel')
else:
    print('⚠️  لم يُعثر على AdjustPanel header — راجع الملف يدوياً')

# ── 2c: تقييد حقل الكمية وزر الحفظ ────────────────────────────────────────
OLD_QTY_FIELD = """          <Field label="الكمية (+ اضافة / - خصم) *">
            <input type="number" className={INP} placeholder="مثال: 10 او -5"
              value={form.quantity_change}
              onChange={e=>setForm({...form,quantity_change:e.target.value})} />
          </Field>"""

NEW_QTY_FIELD = """          <Field label="الكمية (+ اضافة / - خصم) *">
            <input
              type="number"
              className={INP}
              placeholder={canIncreaseStock ? 'مثال: 10 او -5' : 'مثال: -5 (تخفيض فقط)'}
              value={form.quantity_change}
              min={canIncreaseStock ? undefined : undefined}
              onChange={e => {
                const val = e.target.value;
                // ✅ أمين المخزن: يُسمح بالقيم السالبة فقط
                if (!canIncreaseStock && Number(val) > 0) return;
                setForm({...form, quantity_change: val});
              }}
            />
            {!canIncreaseStock && (
              <p className="text-xs text-orange-600 mt-1 font-bold">
                <i className="fas fa-lock ml-1"></i>
                صلاحيتك تسمح بتخفيض المخزون فقط (تلف / فقد / جرد).
                لزيادة المخزون أنشئ <strong>أمر شراء</strong>.
              </p>
            )}
          </Field>"""

if OLD_QTY_FIELD in inv_src:
    inv_src = inv_src.replace(OLD_QTY_FIELD, NEW_QTY_FIELD, 1)
    print('✅  InventoryPage.jsx — تم تقييد حقل الكمية')
else:
    print('⚠️  لم يُعثر على حقل الكمية في AdjustPanel — راجع الملف يدوياً')

# ── 2d: تقييد زر "تطبيق التسوية" لمنع الإرسال الموجب ──────────────────────
OLD_SAVE_BTN = """        <button onClick={handleSave} disabled={saving}
          className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2 rounded-xl text-sm">
          {saving?'...':'تطبيق التسوية'}
        </button>"""

NEW_SAVE_BTN = """        {/* ✅ تحذير لأمين المخزن */}
        {!canIncreaseStock && (
          <div className="mt-4 bg-orange-50 border border-orange-200 rounded-xl px-4 py-3 flex items-start gap-3">
            <i className="fas fa-info-circle text-orange-500 mt-0.5 text-sm"></i>
            <div>
              <p className="text-sm font-bold text-orange-700">تسوية المخزون — صلاحية محدودة</p>
              <p className="text-xs text-orange-600 mt-1">
                يمكنك تسجيل <strong>تخفيض</strong> المخزون فقط (تلف / فقد / جرد دوري).<br/>
                لزيادة المخزون اذهب إلى تبويب <strong>أوامر الشراء</strong> وأنشئ أمر شراء جديد.
              </p>
            </div>
          </div>
        )}
        <button
          onClick={handleSave}
          disabled={saving || (!canIncreaseStock && Number(form.quantity_change) > 0)}
          className={`mt-4 font-bold px-5 py-2 rounded-xl text-sm text-white transition
            ${saving || (!canIncreaseStock && Number(form.quantity_change) > 0)
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'}`}>
          {saving ? '...' : 'تطبيق التسوية'}
        </button>"""

if OLD_SAVE_BTN in inv_src:
    inv_src = inv_src.replace(OLD_SAVE_BTN, NEW_SAVE_BTN, 1)
    print('✅  InventoryPage.jsx — تم تقييد زر التسوية')
else:
    print('⚠️  لم يُعثر على زر التسوية — راجع الملف يدوياً')

# ─── كتابة الملف المحدَّث ─────────────────────────────────────────────────
with open(INV_PAGE, 'w', encoding='utf-8') as f:
    f.write(inv_src)
print('✅  InventoryPage.jsx — تم الحفظ')

# ─── تحديث CHANGELOG ──────────────────────────────────────────────────────
changelog = os.path.join(BASE, 'CHANGELOG.md')
entry = f"""
## [{datetime.now().strftime('%Y-%m-%d')}] fix_02_restrict_stock_adjustment
### المشكلة
أمين المخزن كان يقدر يزيد المخزون يدوياً من تسوية المخزون
بدون أي قيد، وده يكسر مبدأ أن زيادة المخزون تكون فقط عبر أمر شراء.

### التغييرات
- **inventory/views.py** — StockAdjustmentViewSet.perform_create:
  يرفع PermissionDenied إذا كان quantity_change > 0
  والمستخدم ليس في Admins أو Managers أو superuser.

- **InventoryPage.jsx** — AdjustPanel:
  - يقرأ groups المستخدم من AuthContext.
  - يمنع إدخال قيم موجبة في حقل الكمية لأمين المخزن.
  - يُعطّل زر "تطبيق التسوية" إذا كانت الكمية موجبة وغير مصرح.
  - يعرض رسالة توضيحية برتقالية توجّه لاستخدام أوامر الشراء.

### الأدوار المسموح لها بزيادة المخزون يدوياً
  - Superuser
  - Admins
  - Managers

### الأدوار المقيّدة (تخفيض فقط)
  - Storekeepers (أمناء المخازن)
  - Cashiers (الكاشيرية)
  - أي role آخر
"""
with open(changelog, 'a', encoding='utf-8') as f:
    f.write(entry)
print('✅  CHANGELOG.md تم التحديث')

print()
print('─' * 55)
print('✅  النقطة الثانية مكتملة!')
print()
print('   الخطوة التالية:')
print('   cd pos_backend && python manage.py runserver')
print('   (لا يلزم migration — التغيير في الكود فقط)')
print('─' * 55)
