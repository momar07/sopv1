# Rebuild: UoM System (Unit of Measure)

## Date
2026-03-08 17:24

## ما الذي تغير؟

### 1. UnitOfMeasure (موديل جديد في products)
كل وحدة قياس عندها name + factor + category + is_base.
مثال: قطعة(1), دستة(6), كرتون(12), كيلو(1), نص كيلو(0.5)

### 2. ProductUnitPrice (موديل جديد في products)
كل منتج ممكن يكون له سعر مختلف لكل وحدة بيع.
is_auto=True → السعر = base_price × factor
is_auto=False → سعر يدوي (خصم جملة مثلاً)

### 3. Product (تعديل)
أُضيف: base_unit, purchase_unit
stock أصبح read_only في الـ API — التعديل عبر StockAdjustment فقط

### 4. SaleItem (تعديل)
أُضيف: unit (FK → UoM), unit_quantity
quantity = unit_quantity × unit.factor (الكمية الفعلية بالوحدة الأساسية)

### 5. PurchaseOrderItem (تعديل)
أُضيف: unit (FK → UoM)
receive action يحسب: actual_qty = quantity × unit.factor

## مثال عملي
منتج: مياه نستله
  base_unit = قطعة (factor=1)
  purchase_unit = كرتون (factor=12)
  أسعار: قطعة=3ج, نص كرتون=15ج, كرتون=28ج

  استلام 5 كراتين → stock += 60 قطعة
  بيع 2 كرتون     → stock -= 24 قطعة
  بيع 3 قطع       → stock -= 3  قطعة

## الخطوات بعد تشغيل السكريبت
cd pos_backend
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
