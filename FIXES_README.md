# FIXES_README — fix_serializers

## المشاكل التي تم إصلاحها

### Bug 1 — تكرار StockAlert (sales/serializers.py)
كان كود إنشاء StockAlert مكرراً 3 مرات.
الإصلاح: نقل الكود داخل حلقة الأصناف مباشرةً ومرة واحدة فقط،
مع استخدام stock_after المحسوبة مباشرةً بدل refresh_from_db.

### Bug 2 — StockAdjustment لا يحل Alerts (inventory/serializers.py)
عند تعديل المخزون يدوياً، الـ alerts القديمة كانت تبقى.
الإصلاح: بعد الحفظ، إذا after > threshold → نحل كل alerts.
          إذا 0 < after <= threshold → نحل 'out' ونُنشئ 'low' إن لم يوجد.

### Bug 3 — unit مفقود من PurchaseOrderItemSerializer
الحقل unit (ForeignKey لـ UnitOfMeasure) لم يكن موجوداً في fields.
الإصلاح: أضفنا 'unit' و 'unit_name' للـ serializer.

## الملفات المعدّلة
- pos_backend/sales/serializers.py
- pos_backend/inventory/serializers.py
