# CHANGELOG

كل التعديلات على المشروع مسجّلة هنا تلقائياً.

---

## [2026-03-08 21:06] buggy tikketing




## [2026-03-08 17:25] تحديث inventory/views.py: receive يحسب actual_qty = qty x unit.factor
## [2026-03-08 17:24] إعادة بناء النظام مع UoM المرن + منع تعديل stock مباشرة
## [2026-03-08 14:55] fix bugs




## [2026-03-08 14:36] اصلاح خريطة تدفق المخزون: StockAlert تلقائي + StockAdjustment في cancel + reason صح في receive
## [2026-03-08 13:44] اصلاح: paidAmount والـ cart يرجعوا بعد البيع (BarcodePOS persistence bug)
## [2026-03-08 12:52] إضافة صفحة التقرير المالي الشامل (FinancialReport)


## [2026-03-08 17:55:36] - fix_ui_complete.py
- seed UI complete: 10 routes + 12 sidebar items (tree) + DynamicSidebar يبني tree من parent_key

## [2026-03-08 18:07:22] - fix_ui_issues.py
- إصلاح الشاشة البيضاء (navigate /dashboard) + DynamicRoutes static fallback + seed groups

## [2026-03-08 18:21:09] - fix_ui_components.py
- إصلاح component names في seed: XxxPage → اسم الملف الفعلي في src/pages/

## [2026-03-08 18:33] fix_serializers
- Fix-1: أزلنا تكرار StockAlert (3 → 1 loop) في sales/serializers.py
- Fix-2: StockAdjustmentSerializer يحل/يُنشئ StockAlert بعد تعديل المخزون
- Fix-3: PurchaseOrderItemSerializer أضاف حقل unit و unit_name

## [2026-03-08 18:40] fix_ui_actions
- أضفنا seed_ui_actions.py يُنشئ 12 UiAction للصفحات: Products, Inventory, Customers, Users, CashRegister
- products.add/delete → MGMT | customers.add → SALE | users.* → ADMN | cashregister.* → SALE

## [2026-03-08 18:51] fix_add_categories_page
- أضفنا Categories.jsx: إدارة كاملة للتصنيفات مع color picker وicon picker
- أضفنا test_uom.py: اختبار شامل (7 مجموعات) للـ UnitOfMeasure model + API
- أضفنا seed_ui_categories.py: route + menuItem + actions للتصنيفات
- CATEGORY_SERIALIZER_PATCH.txt: إضافة products_count للـ CategorySerializer

## [2026-03-08 19:05] fix_test_uom
- Fix: endpoint /api/products/units/ → /api/units/
- Fix: guard isinstance(items, list) قبل list comprehension
- أضفنا اختبارات إضافية: PATCH, auth, search filter, profit_margin, is_low_stock

## [2026-03-08 19:06] fix_test_uom
- Fix: endpoint /api/products/units/ → /api/units/
- Fix: guard isinstance(items, list) قبل list comprehension
- أضفنا اختبارات إضافية: PATCH, auth, search filter, profit_margin, is_low_stock

## [2026-03-08 19:20] fix_units_api
- أضفنا unitsAPI في api.js: getAll, getOne, create, update, delete, setUnitPrices
- أضفنا UomPricesTab.jsx: تبويب الوحدات والأسعار داخل ProductModal


## [2026-03-08 19:28] fix_products_uom
- أضفنا unitsAPI في api.js
- أضفنا تبويب 'الوحدات والأسعار' في ProductModal
- أضفنا عمود 'الوحدة' في جدول المنتجات
- أضفنا حقل min_stock في تبويب التسعير
- السكريبت يكتب كل حاجة لوحده بدون خطوات يدوية

## [2026-03-08 19:39] fix_add_uom_page
- أضفنا UnitsOfMeasure.jsx: إدارة كاملة لوحدات القياس
- أضفنا seed_ui_uom.py: route /units + menu item + actions


## [2026-03-08 19:53] fix_products_edit
- Fix: اختفاء البيانات عند التعديل (category, cost, base_unit, purchase_unit, min_stock)
- السبب: ProductListSerializer مش فيه كل الحقول
- الحل: productsAPI.getOne(id) داخل ProductModal عند فتح التعديل
- أضفنا loading spinner أثناء جلب البيانات الكاملة
- أضفنا تبويب الوحدات والأسعار + unitsAPI

## [2026-03-08] fix_01_no_default_stock
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

## [2026-03-08] fix_02_restrict_stock_adjustment
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

## [2026-03-08] fix_03b_alert_ticket_frontend
### التغييرات
- **api.js**: أضيف getAlert, addAlertNote, createPoFromAlert, updateAlertMeta
- **InventoryPage.jsx**:
  - AlertCard: بطاقة تذكرة مع أولوية وحالة ومخزون وملاحظات
  - AlertTicketModal: تذكرة كاملة مع timeline + فورم ملاحظة
    + إنشاء PO + حل التذكرة
  - AlertsPanel: شبكة بطاقات مع فلاتر وإحصائيات
