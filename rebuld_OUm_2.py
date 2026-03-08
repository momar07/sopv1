#!/usr/bin/env python3
# =============================================================
# fix_inventory_views_uom.py
# كتابة inventory/views.py الجديد مع دعم UoM في receive
# =============================================================

import os
import re
import shutil
from datetime import datetime

# ── المسارات ──────────────────────────────────────────────────
BASE      = "/home/momar/Projects/POS_DEV/posv1_dev10"
TARGET    = os.path.join(BASE, "pos_backend/inventory/views.py")
CHANGELOG = os.path.join(BASE, "CHANGELOG.md")
# ─────────────────────────────────────────────────────────────

CHANGE_MSG = "تحديث inventory/views.py: receive يحسب actual_qty = qty x unit.factor"


# ── Helpers ───────────────────────────────────────────────────
def abort(msg):
    print("\n❌  " + msg)
    raise SystemExit(1)


def backup(path):
    if os.path.isfile(path):
        bak = path + ".bak"
        shutil.copy2(path, bak)
        print("   💾  backup → " + bak)


def write_file(path, content):
    open(path, "w", encoding="utf-8").write(content)
    print("   ✅  كُتب  → " + path)


def update_changelog(msg):
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = "\n## [" + now + "] " + msg + "\n"
    try:
        txt = open(CHANGELOG, encoding="utf-8").read()
        new = re.sub(r"(---\s*\n)", r"\1" + entry, txt, count=1)
        open(CHANGELOG, "w", encoding="utf-8").write(new)
        print("   📝  CHANGELOG updated")
    except Exception as e:
        print("   ⚠️   CHANGELOG skipped: " + str(e))


# ═══════════════════════════════════════════════════════════════
# المحتوى الكامل لـ inventory/views.py
# ═══════════════════════════════════════════════════════════════
CONTENT = (
    "from rest_framework import viewsets, filters, status\n"
    "from rest_framework.decorators import action\n"
    "from rest_framework.response import Response\n"
    "from rest_framework.permissions import IsAuthenticated\n"
    "from django_filters.rest_framework import DjangoFilterBackend\n"
    "from django.utils import timezone\n"
    "from django.db import transaction\n"
    "from django.db.models import F\n"
    "from .models import (\n"
    "    Supplier, PurchaseOrder,\n"
    "    StockAdjustment, StockAlert, StockMovement,\n"
    ")\n"
    "from .serializers import (\n"
    "    SupplierSerializer, PurchaseOrderSerializer,\n"
    "    StockAdjustmentSerializer, StockAlertSerializer, StockMovementSerializer,\n"
    ")\n"
    "from products.models import Product\n"
    "\n"
    "\n"
    "# ── Supplier ──────────────────────────────────────────────\n"
    "class SupplierViewSet(viewsets.ModelViewSet):\n"
    "    queryset           = Supplier.objects.all()\n"
    "    serializer_class   = SupplierSerializer\n"
    "    permission_classes = [IsAuthenticated]\n"
    "    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]\n"
    "    search_fields      = ['name', 'phone', 'email']\n"
    "    ordering           = ['name']\n"
    "\n"
    "\n"
    "# ── PurchaseOrder ─────────────────────────────────────────\n"
    "class PurchaseOrderViewSet(viewsets.ModelViewSet):\n"
    "    queryset = PurchaseOrder.objects.select_related(\n"
    "        'supplier', 'user'\n"
    "    ).prefetch_related('items__product', 'items__unit').all()\n"
    "    serializer_class   = PurchaseOrderSerializer\n"
    "    permission_classes = [IsAuthenticated]\n"
    "    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]\n"
    "    filterset_fields   = ['status', 'supplier']\n"
    "    search_fields      = ['reference_number', 'supplier__name']\n"
    "    ordering           = ['-created_at']\n"
    "\n"
    "    def perform_create(self, serializer):\n"
    "        serializer.save(user=self.request.user)\n"
    "\n"
    "    @action(detail=True, methods=['post'])\n"
    "    def receive(self, request, pk=None):\n"
    "        order = self.get_object()\n"
    "\n"
    "        if order.status == 'cancelled':\n"
    "            return Response(\n"
    "                {'error': 'لا يمكن استلام امر ملغي'},\n"
    "                status=status.HTTP_400_BAD_REQUEST\n"
    "            )\n"
    "        if order.status == 'received':\n"
    "            return Response(\n"
    "                {'error': 'تم استلام هذا الامر مسبقا'},\n"
    "                status=status.HTTP_400_BAD_REQUEST\n"
    "            )\n"
    "\n"
    "        received_quantities = request.data.get('received_quantities', {})\n"
    "\n"
    "        with transaction.atomic():\n"
    "            for item in order.items.select_related('product', 'unit').all():\n"
    "                qty = received_quantities.get(str(item.id), item.remaining_quantity)\n"
    "                qty = max(0, int(qty))\n"
    "\n"
    "                if qty == 0:\n"
    "                    continue\n"
    "\n"
    "                product = item.product\n"
    "\n"
    "                # ✅ UoM: actual_qty = qty × unit.factor\n"
    "                unit       = item.unit\n"
    "                factor     = float(unit.factor) if unit and unit.factor else 1.0\n"
    "                actual_qty = int(qty * factor)\n"
    "\n"
    "                stock_before = product.stock\n"
    "\n"
    "                Product.objects.filter(id=product.id).update(\n"
    "                    stock=F('stock') + actual_qty,\n"
    "                    cost=item.unit_cost,\n"
    "                )\n"
    "                product.refresh_from_db()\n"
    "                stock_after = product.stock\n"
    "\n"
    "                item.received_quantity += qty\n"
    "                item.save(update_fields=['received_quantity'])\n"
    "\n"
    "                # تسوية مخزون\n"
    "                StockAdjustment.objects.create(\n"
    "                    product         = product,\n"
    "                    user            = request.user,\n"
    "                    quantity_before = stock_before,\n"
    "                    quantity_change = actual_qty,\n"
    "                    quantity_after  = stock_after,\n"
    "                    reason          = 'other',\n"
    "                    notes           = 'استلام امر شراء #' + order.reference_number,\n"
    "                )\n"
    "\n"
    "                # حركة مخزون\n"
    "                StockMovement.objects.create(\n"
    "                    product       = product,\n"
    "                    movement_type = 'purchase',\n"
    "                    quantity      = actual_qty,\n"
    "                    stock_before  = stock_before,\n"
    "                    stock_after   = stock_after,\n"
    "                    unit          = unit,\n"
    "                    unit_quantity = qty,\n"
    "                    reference     = order.reference_number,\n"
    "                    user          = request.user,\n"
    "                    notes         = 'استلام امر شراء #' + order.reference_number,\n"
    "                )\n"
    "\n"
    "                # ✅ resolve StockAlert لو المخزون رجع فوق الـ threshold\n"
    "                from inventory.models import StockAlert as _SA\n"
    "                if product.stock > 0:\n"
    "                    _SA.objects.filter(\n"
    "                        product=product, is_resolved=False\n"
    "                    ).update(is_resolved=True, resolved_at=timezone.now())\n"
    "\n"
    "            order.status      = 'received'\n"
    "            order.received_at = timezone.now()\n"
    "            order.save(update_fields=['status', 'received_at'])\n"
    "\n"
    "        return Response(self.get_serializer(order).data)\n"
    "\n"
    "    @action(detail=True, methods=['post'])\n"
    "    def cancel(self, request, pk=None):\n"
    "        order = self.get_object()\n"
    "        if order.status == 'received':\n"
    "            return Response(\n"
    "                {'error': 'لا يمكن الغاء امر تم استلامه'},\n"
    "                status=status.HTTP_400_BAD_REQUEST\n"
    "            )\n"
    "        order.status = 'cancelled'\n"
    "        order.save(update_fields=['status'])\n"
    "        return Response(self.get_serializer(order).data)\n"
    "\n"
    "\n"
    "# ── StockAdjustment ───────────────────────────────────────\n"
    "class StockAdjustmentViewSet(viewsets.ModelViewSet):\n"
    "    queryset           = StockAdjustment.objects.select_related('product', 'user').all()\n"
    "    serializer_class   = StockAdjustmentSerializer\n"
    "    permission_classes = [IsAuthenticated]\n"
    "    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]\n"
    "    filterset_fields   = ['product', 'reason']\n"
    "    search_fields      = ['product__name', 'notes']\n"
    "    ordering           = ['-created_at']\n"
    "    http_method_names  = ['get', 'post', 'head', 'options']\n"
    "\n"
    "    def perform_create(self, serializer):\n"
    "        serializer.save(user=self.request.user)\n"
    "\n"
    "\n"
    "# ── StockAlert ────────────────────────────────────────────\n"
    "class StockAlertViewSet(viewsets.ModelViewSet):\n"
    "    queryset           = StockAlert.objects.select_related('product').all()\n"
    "    serializer_class   = StockAlertSerializer\n"
    "    permission_classes = [IsAuthenticated]\n"
    "    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]\n"
    "    filterset_fields   = ['alert_type', 'is_resolved', 'product']\n"
    "    ordering           = ['-created_at']\n"
    "    http_method_names  = ['get', 'post', 'patch', 'head', 'options']\n"
    "\n"
    "    @action(detail=False, methods=['post'])\n"
    "    def check_and_generate(self, request):\n"
    "        threshold = int(request.data.get('threshold', 10))\n"
    "        products  = Product.objects.filter(is_active=True)\n"
    "        created   = 0\n"
    "        for product in products:\n"
    "            if StockAlert.objects.filter(product=product, is_resolved=False).exists():\n"
    "                continue\n"
    "            if product.stock == 0:\n"
    "                StockAlert.objects.create(\n"
    "                    product=product, alert_type='out',\n"
    "                    threshold=threshold, current_stock=0\n"
    "                )\n"
    "                created += 1\n"
    "            elif product.stock <= threshold:\n"
    "                StockAlert.objects.create(\n"
    "                    product=product, alert_type='low',\n"
    "                    threshold=threshold, current_stock=product.stock\n"
    "                )\n"
    "                created += 1\n"
    "        return Response({\n"
    "            'created_alerts':    created,\n"
    "            'checked_products':  products.count(),\n"
    "        })\n"
    "\n"
    "    @action(detail=True, methods=['post'])\n"
    "    def resolve(self, request, pk=None):\n"
    "        alert             = self.get_object()\n"
    "        alert.is_resolved = True\n"
    "        alert.resolved_at = timezone.now()\n"
    "        alert.save(update_fields=['is_resolved', 'resolved_at'])\n"
    "        return Response(self.get_serializer(alert).data)\n"
    "\n"
    "    @action(detail=False, methods=['get'])\n"
    "    def summary(self, request):\n"
    "        threshold      = int(request.query_params.get('threshold', 10))\n"
    "        total_products = Product.objects.filter(is_active=True).count()\n"
    "        out_of_stock   = Product.objects.filter(is_active=True, stock=0).count()\n"
    "        low_stock      = Product.objects.filter(\n"
    "            is_active=True, stock__gt=0, stock__lte=threshold\n"
    "        ).count()\n"
    "        unresolved     = StockAlert.objects.filter(is_resolved=False).count()\n"
    "        return Response({\n"
    "            'total_products':    total_products,\n"
    "            'out_of_stock':      out_of_stock,\n"
    "            'low_stock':         low_stock,\n"
    "            'healthy_stock':     total_products - out_of_stock - low_stock,\n"
    "            'unresolved_alerts': unresolved,\n"
    "        })\n"
    "\n"
    "\n"
    "# ── StockMovement (read-only) ──────────────────────────────\n"
    "class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):\n"
    "    queryset           = StockMovement.objects.select_related('product', 'user', 'unit').all()\n"
    "    serializer_class   = StockMovementSerializer\n"
    "    permission_classes = [IsAuthenticated]\n"
    "    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]\n"
    "    filterset_fields   = ['movement_type', 'product']\n"
    "    search_fields      = ['product__name', 'reference', 'notes']\n"
    "    ordering           = ['-created_at']\n"
)


# ── main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("=" * 58)
    print("  🔧  fix_inventory_views_uom.py")
    print("=" * 58)

    print("\n[1/2] كتابة inventory/views.py ...")
    if not os.path.isfile(TARGET):
        abort("الملف غير موجود: " + TARGET)
    backup(TARGET)
    write_file(TARGET, CONTENT)

    print("\n[2/2] تحديث CHANGELOG ...")
    update_changelog(CHANGE_MSG)

    print()
    print("=" * 58)
    print("  🎉  تم!")
    print()
    print("  الخطوة التالية:")
    print("  ./reset_db.sh")
    print("=" * 58)
    print()
