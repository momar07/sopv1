#!/usr/bin/env python3
"""
fix_01_no_default_stock.py
==========================
النقطة الأولى: إلغاء إمكانية إدخال مخزون ابتدائي عند إضافة منتج جديد.

التغييرات:
  - Products.jsx  : إزالة حقل الكمية من تاب التسعير عند الإضافة
                    + إضافة رسالة توضيحية بدلاً منه

ملاحظة: serializers.py و views.py لا يحتاجان تعديل لأن stock
         موجود بالفعل كـ read_only=True في ProductSerializer.
"""

import os, shutil, sys
from datetime import datetime

BASE   = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, 'pos_frontend', 'src', 'pages', 'Products.jsx')

# ─── التحقق من وجود الملف ─────────────────────────────────────────────────
if not os.path.exists(TARGET):
    print(f'❌  الملف غير موجود: {TARGET}')
    sys.exit(1)

# ─── نسخة احتياطية ────────────────────────────────────────────────────────
stamp  = datetime.now().strftime('%Y%m%d_%H%M%S')
backup = TARGET + f'.bak_{stamp}'
shutil.copy2(TARGET, backup)
print(f'✅  نسخة احتياطية: {os.path.basename(backup)}')

# ─── قراءة الملف ──────────────────────────────────────────────────────────
with open(TARGET, 'r', encoding='utf-8') as f:
    src = f.read()

# ─── التعديل المطلوب ──────────────────────────────────────────────────────
# الكود القديم: حقل الكمية مع disabled={!!product}
OLD = """                  <div>
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
                  </div>"""

# الكود الجديد: رسالة توضيحية عند الإضافة، قراءة فقط عند التعديل
NEW = """                  {product ? (
                    /* ── تعديل منتج: المخزون للقراءة فقط ── */
                    <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 flex items-start gap-3">
                      <i className="fas fa-info-circle text-blue-500 mt-0.5 text-sm"></i>
                      <div>
                        <p className="text-sm font-bold text-blue-700">
                          المخزون الحالي: <strong>{product.stock}</strong> وحدة
                        </p>
                        <p className="text-xs text-blue-500 mt-1">
                          لتعديل المخزون استخدم زر <strong>±</strong> في جدول المنتجات،
                          أو أنشئ <strong>أمر شراء</strong> من صفحة المخزون.
                        </p>
                      </div>
                    </div>
                  ) : (
                    /* ── منتج جديد: المخزون يبدأ بـ 0 دائماً ── */
                    <div className="bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3 flex items-start gap-3">
                      <i className="fas fa-exclamation-triangle text-yellow-500 mt-0.5 text-sm"></i>
                      <div>
                        <p className="text-sm font-bold text-yellow-700">
                          المخزون الابتدائي = <strong>0</strong>
                        </p>
                        <p className="text-xs text-yellow-600 mt-1">
                          بعد حفظ المنتج، أنشئ <strong>أمر شراء</strong> من صفحة المخزون
                          لإضافة الكمية الأولى وتسجيل حركة الاستلام.
                        </p>
                      </div>
                    </div>
                  )}"""

# ─── تطبيق التغيير ────────────────────────────────────────────────────────
if OLD not in src:
    print('⚠️  لم يُعثر على النص القديم — ربما الملف تغيّر مسبقاً.')
    print('    راجع Products.jsx يدوياً في تاب pricing حول حقل stock.')
    sys.exit(1)

new_src = src.replace(OLD, NEW, 1)

# ─── كتابة الملف المحدَّث ─────────────────────────────────────────────────
with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(new_src)

print('✅  Products.jsx تم تحديثه بنجاح')

# ─── تحديث CHANGELOG ──────────────────────────────────────────────────────
changelog = os.path.join(BASE, 'CHANGELOG.md')
entry = f"""
## [{datetime.now().strftime('%Y-%m-%d')}] fix_01_no_default_stock
### المشكلة
حقل "الكمية الافتراضية" في فورم إضافة المنتج كان يوهم المستخدم
بإمكانية إدخال مخزون ابتدائي رغم أن الـ backend يتجاهله (stock = read_only).

### التغيير
- **Products.jsx** — تاب "التسعير والمخزون":
  - عند الإضافة: استُبدل الحقل برسالة توضيحية صفراء تشرح أن المخزون
    يبدأ بـ 0 وأن الإضافة تتم عبر أمر شراء.
  - عند التعديل: استُبدل الحقل المعطّل برسالة زرقاء تعرض المخزون الحالي
    وتوجّه المستخدم لاستخدام زر ± أو أمر شراء.

### ملاحظة
لم يتغيّر شيء في Backend لأن ProductSerializer يعامل stock كـ read_only
بالفعل منذ البداية.
"""
with open(changelog, 'a', encoding='utf-8') as f:
    f.write(entry)
print('✅  CHANGELOG.md تم التحديث')
print()
print('─' * 50)
print('✅  النقطة الأولى مكتملة!')
print('   لا يلزم إعادة تشغيل الـ backend.')
print('   Vite سيُعيد تحميل الصفحة تلقائياً.')
print('─' * 50)
