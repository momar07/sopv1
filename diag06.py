#!/usr/bin/env python3
# diag_06.py — يطبع الأسطر المهمة من كل ملف عشان نعرف الـ patterns الفعلية

import os

BASE     = "/home/momar/Projects/POS_DEV/posv1_dev10"
BACKEND  = BASE + "/pos_backend/inventory"
FRONTEND = BASE + "/pos_frontend/src"

def show(label, path, keywords, context=3):
    print("\n" + "="*60)
    print("FILE: " + label)
    print("PATH: " + path)
    if not os.path.exists(path):
        print("  !! FILE NOT FOUND !!")
        return
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    for kw in keywords:
        found = False
        for i, line in enumerate(lines):
            if kw in line:
                found = True
                start = max(0, i - context)
                end   = min(len(lines), i + context + 1)
                print("\n  --- match: " + repr(kw) + " at line " + str(i+1) + " ---")
                for j in range(start, end):
                    marker = ">>>" if j == i else "   "
                    print(marker + " " + str(j+1).rjust(4) + ": " + lines[j].rstrip())
        if not found:
            print("\n  [NOT FOUND]: " + repr(kw))

# ── models.py ─────────────────────────────────────────────
show("models.py", BACKEND + "/models.py", [
    "linked_po",
    "linked_pos",
    "created_by",
    "check_and_auto_resolve",
])

# ── serializers.py ────────────────────────────────────────
show("serializers.py", BACKEND + "/serializers.py", [
    "linked_po_reference",
    "linked_pos",
    "linked_pos_data",
    "get_linked_pos_data",
    "validate_expected_date",
    "get_notes_count",
    "read_only_fields = ['alert', 'user', 'created_at']",
])

# ── views.py ──────────────────────────────────────────────
show("views.py", BACKEND + "/views.py", [
    "linked_po",
    "linked_pos",
    "created_by",
    "resolveAlert",
    "assign_to_me",
    "check_and_generate",
    "create_purchase_order",
    "resolve",
    "# -- StockMovement",
    "# \u2500\u2500 StockMovement",
    "update_meta",
    "StockMovement (read-only)",
])

# ── api.js ─────────────────────────────────────────────────
show("api.js", FRONTEND + "/services/api.js", [
    "resolveAlert",
    "assignAlert",
    "getSuppliers",
    "createSupplier",
])

# ── PurchasingPage.jsx ────────────────────────────────────
show("PurchasingPage.jsx", FRONTEND + "/pages/PurchasingPage.jsx", [
    "const tabs",
    "suppliers",
    "SuppliersPanel",
    "AssignSection",
    "linked_po_reference",
    "linked_pos_data",
    "created_by_name",
    "استلام",
    "ReceiveModal",
])

# ── InventoryPage.jsx ─────────────────────────────────────
show("InventoryPage.jsx", FRONTEND + "/pages/InventoryPage.jsx", [
    "suppliers",
    "SuppliersPanel",
])

print("\n" + "="*60)
print("DONE — paste the output above")
print("="*60)
