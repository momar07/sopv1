# FIXES README
Last updated: 2026-03-09

---

## Fix-07 — Purchasing Module Full Overhaul
Date: 2026-03-09
Status: Applied

### Problems Fixed
1. Receive button in Purchase Orders table removed.
2. Multiple purchase quotes per alert (linked_pos M2M).
3. Note creation failed on empty date string.
4. Alert not auto-resolved when all linked POs received.
5. Suppliers tab moved from Inventory to Purchasing.
6. Assignment feature added (assign_to_me / assign_to_user / unassign).
7. created_by shown on AlertCard.

### Backend — inventory/models.py
- linked_po FK replaced with linked_pos ManyToManyField.
- created_by ForeignKey added.
- check_and_auto_resolve() method added.
- Duplicate method/field definitions removed.

### Backend — inventory/serializers.py
- linked_pos_data SerializerMethodField (list of POs).
- linked_pos_count SerializerMethodField.
- created_by_name CharField.
- validate_expected_date on StockAlertNoteSerializer.

### Backend — inventory/views.py
- create_purchase_order: uses linked_pos.add(po), no single-PO restriction.
- resolve: checks all linked_pos received/cancelled.
- receive: sets ticket_status=resolved on auto-resolve.
- check_and_generate: passes created_by=request.user.
- New actions: assign_to_me, assign_to_user, unassign.

### Frontend — api.js
- Added: assignAlertToMe, assignAlertToUser, unassignAlert.

### Frontend — PurchasingPage.jsx (rewritten)
- Tabs: Alerts / Purchase Orders / Suppliers.
- AlertCard: created_by_name, assignment status, linked_pos_count.
- AlertTicketModal: multiple POs in create_po tab.
- AssignSection: assign-to-me + manager dropdown + unassign.
- PurchaseOrdersPanel: receive button removed.
- SuppliersPanel: full CRUD.

### Frontend — InventoryPage.jsx
- Suppliers tab removed.

### Migration
  python manage.py makemigrations inventory --name fix07_created_by_linked_pos_m2m
  python manage.py migrate inventory

---

## Fix-03b — Alert Ticket Frontend
Date: 2026-03-08 | Status: Superseded by Fix-07
- AlertCard, AlertTicketModal, AlertsPanel.

## Fix-03 — UoM in PurchaseOrderItem
Date: 2026-03-08 | Status: Applied
- unit and unit_name fields in PurchaseOrderItemSerializer.

## Fix-02 — StockAdjustment Auto-Resolve
Date: 2026-03-08 | Status: Applied
- stock > threshold: resolve all alerts.
- 0 < stock <= threshold: resolve out alert, create low alert.

## Fix-01 — No Default Stock
Date: 2026-03-08 | Status: Applied
- Removed default stock from Products.jsx add/edit modal.