# CHANGELOG

كل التعديلات على المشروع مسجّلة هنا تلقائياً.

---

## [2026-03-08 18:25] uibuilder optimaization




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
