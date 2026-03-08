# FIXES README
**Script:** `fix_ui_components.py`
**Date:** 2026-03-08 18:21:09

---
## Component Names Audit

### المشكلة
الـ seed القديم كان بيستخدم XxxPage (مثل DashboardPage, ProductsPage)
لكن الملفات الفعلية في src/pages/ بدون Page suffix.
ده بيخلي lazyPage() يـ throw error على كل route.

### الـ Mapping الصح
| component في الـ DB | الملف الفعلي         |
|---------------------|----------------------|
| Dashboard           | Dashboard.jsx        |
| Products            | Products.jsx         |
| Customers           | Customers.jsx        |
| Operations          | Operations.jsx       |
| BarcodePOS          | BarcodePOS.jsx       |
| InventoryPage       | InventoryPage.jsx    |
| FinancialReport     | FinancialReport.jsx  |
| CashRegister        | CashRegister.jsx     |
| UserManagement      | UserManagement.jsx   |
| Settings            | Settings.jsx         |
| ReturnsPage         | ReturnsPage.jsx      |
| OperationDetails    | OperationDetails.jsx |

### ملفات غير موجودة (محذوفة من الـ seed)
- PurchaseOrdersPage → الصفحة مش موجودة
- SuppliersPage → الصفحة مش موجودة
- UnitsPage → الصفحة مش موجودة

### ملف معدّل
- pos_backend/seed_ui_data.py