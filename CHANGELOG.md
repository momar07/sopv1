
## Fix-12 — Bulk Alert (Grouped Multi-Product Alert) [20260309]
### Added
- `StockAlertItem` model: links multiple products to a single alert
- `check_and_generate` view: new `bulk_mode=true` creates one grouped alert
- `create_bulk_purchase_order` action: supports `mode=single` (one PO) or `mode=per_item` (PO per product)
- `BulkPOSection` React component in AlertTicketModal
- `CreateAlertsModal` now sends bulk request instead of N individual requests
### Migration
- `python manage.py makemigrations inventory --name fix12_alert_items`
- `python manage.py migrate inventory`

# CHANGELOG

## [2026-03-09] — Fix-07: Purchasing Module — Full Overhaul
### Added
- StockAlert.created_by FK — tracks which user generated the alert.
- StockAlert.linked_pos ManyToManyField replacing single linked_po FK.
- StockAlert.check_and_auto_resolve() — auto-resolves when all linked POs received.
- assign_to_me action on StockAlertViewSet.
- assign_to_user action on StockAlertViewSet — managers/admins only.
- unassign action on StockAlertViewSet.
- AssignSection React component in PurchasingPage.
- SuppliersPanel moved to PurchasingPage as tab 3.
- linked_pos_data serializer field — list of all linked POs.
- created_by_name serializer field.
- assignAlertToMe, assignAlertToUser, unassignAlert in api.js.

### Changed
- PurchasingPage.jsx fully rewritten — tabs: Alerts / Purchase Orders / Suppliers.
- AlertTicketModal create_po tab allows multiple purchase quotes per alert.
- AlertCard shows created_by_name, assignment status, linked_pos_count.
- PurchaseOrdersPanel — receive button removed.
- StockAlertViewSet.resolve — validates all linked POs received/cancelled.
- InventoryPage.jsx — Suppliers tab removed.

### Fixed
- Duplicate check_and_auto_resolve method in models.py removed.
- Duplicate created_by field definition in models.py removed.
- StockAlertNoteSerializer.validate_expected_date handles empty string.
- UnicodeEncodeError in previous fix scripts.

## [2026-03-09] — Fix-05/06: Purchasing v1 (superseded by Fix-07)
- Initial purchasing improvements — superseded.

## Earlier
- Fix-03b: Alert ticket frontend.
- Fix-03: PurchaseOrderItemSerializer unit fields.
- Fix-02: StockAdjustment auto-resolves StockAlerts.
- Fix-01: Removed default stock field from Products.jsx.
