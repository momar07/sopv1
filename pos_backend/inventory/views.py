from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from .models import (
    Supplier, PurchaseOrder, PurchaseOrderItem,
    StockAdjustment, StockAlert, StockAlertNote, StockMovement,
)
from .serializers import (
    SupplierSerializer, PurchaseOrderSerializer,
    StockAdjustmentSerializer,
    StockAlertSerializer, StockAlertNoteSerializer,
    StockMovementSerializer,
)
from products.models import Product


# ── Supplier ──────────────────────────────────────────────
class SupplierViewSet(viewsets.ModelViewSet):
    queryset           = Supplier.objects.all()
    serializer_class   = SupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'phone', 'email']
    ordering           = ['name']


# ── PurchaseOrder ─────────────────────────────────────────
class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related(
        'supplier', 'user'
    ).prefetch_related('items__product', 'items__unit').all()
    serializer_class   = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['status', 'supplier']
    search_fields      = ['reference_number', 'supplier__name']
    ordering           = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        order = self.get_object()

        if order.status == 'cancelled':
            return Response(
                {'error': 'لا يمكن استلام امر ملغي'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if order.status == 'received':
            return Response(
                {'error': 'تم استلام هذا الامر مسبقا'},
                status=status.HTTP_400_BAD_REQUEST
            )

        received_quantities = request.data.get('received_quantities', {})

        with transaction.atomic():
            for item in order.items.select_related('product', 'unit').all():
                qty = received_quantities.get(str(item.id), item.remaining_quantity)
                qty = max(0, int(qty))

                if qty == 0:
                    continue

                product = item.product

                # ✅ UoM: actual_qty = qty × unit.factor
                unit       = item.unit
                factor     = float(unit.factor) if unit and unit.factor else 1.0
                actual_qty = int(qty * factor)

                stock_before = product.stock

                Product.objects.filter(id=product.id).update(
                    stock=F('stock') + actual_qty,
                    cost=item.unit_cost,
                )
                product.refresh_from_db()
                stock_after = product.stock

                item.received_quantity += qty
                item.save(update_fields=['received_quantity'])

                # تسوية مخزون
                StockAdjustment.objects.create(
                    product         = product,
                    user            = request.user,
                    quantity_before = stock_before,
                    quantity_change = actual_qty,
                    quantity_after  = stock_after,
                    reason          = 'other',
                    notes           = 'استلام امر شراء #' + order.reference_number,
                )

                # حركة مخزون
                StockMovement.objects.create(
                    product       = product,
                    movement_type = 'purchase',
                    quantity      = actual_qty,
                    stock_before  = stock_before,
                    stock_after   = stock_after,
                    unit          = unit,
                    unit_quantity = qty,
                    reference     = order.reference_number,
                    user          = request.user,
                    notes         = 'استلام امر شراء #' + order.reference_number,
                )

                # ✅ resolve StockAlert لو المخزون رجع فوق الـ threshold
                from inventory.models import StockAlert as _SA
                if product.stock > 0:
                    _SA.objects.filter(
                        product=product, is_resolved=False
                    ).update(is_resolved=True, resolved_at=timezone.now())

            order.status      = 'received'
            order.received_at = timezone.now()
            order.save(update_fields=['status', 'received_at'])

        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status == 'received':
            return Response(
                {'error': 'لا يمكن الغاء امر تم استلامه'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        return Response(self.get_serializer(order).data)


# ── StockAdjustment ───────────────────────────────────────
class StockAdjustmentViewSet(viewsets.ModelViewSet):
    queryset           = StockAdjustment.objects.select_related('product', 'user').all()
    serializer_class   = StockAdjustmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['product', 'reason']
    search_fields      = ['product__name', 'notes']
    ordering           = ['-created_at']
    http_method_names  = ['get', 'post', 'head', 'options']

    def perform_create(self, serializer):
        user   = self.request.user
        change = serializer.validated_data.get('quantity_change', 0)

        # ✅ أمين المخزن لا يقدر يزيد المخزون يدوياً
        if change > 0:
            allowed_groups = {'Admins', 'Managers'}
            user_groups    = set(user.groups.values_list('name', flat=True))
            is_allowed     = user.is_superuser or bool(allowed_groups & user_groups)

            if not is_allowed:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    'غير مصرح: لا يمكن زيادة المخزون يدوياً. '
                    'يجب إنشاء أمر شراء واستلامه لزيادة الكمية.'
                )

        serializer.save(user=user)


# ── StockAlert ── Ticket System ──────────────────────────
class StockAlertViewSet(viewsets.ModelViewSet):
    queryset = StockAlert.objects.select_related(
        'product', 'assigned_to', 'linked_po'
    ).prefetch_related('notes__user').all()
    serializer_class   = StockAlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['alert_type', 'is_resolved', 'product', 'priority', 'ticket_status']
    ordering           = ['-created_at']
    http_method_names  = ['get', 'post', 'patch', 'head', 'options']

    @action(detail=False, methods=['post'])
    def check_and_generate(self, request):
        threshold = int(request.data.get('threshold', 10))
        products  = Product.objects.filter(is_active=True)
        created   = 0
        for product in products:
            if StockAlert.objects.filter(product=product, is_resolved=False).exists():
                continue
            if product.stock == 0:
                StockAlert.objects.create(
                    product=product, alert_type='out', priority='critical',
                    threshold=threshold, current_stock=0
                )
                created += 1
            elif product.stock <= threshold:
                StockAlert.objects.create(
                    product=product, alert_type='low', priority='high',
                    threshold=threshold, current_stock=product.stock
                )
                created += 1
        return Response({'created_alerts': created, 'checked_products': products.count()})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        threshold      = int(request.query_params.get('threshold', 10))
        total_products = Product.objects.filter(is_active=True).count()
        out_of_stock   = Product.objects.filter(is_active=True, stock=0).count()
        low_stock      = Product.objects.filter(is_active=True, stock__gt=0, stock__lte=threshold).count()
        unresolved     = StockAlert.objects.filter(is_resolved=False).count()
        return Response({
            'total_products':    total_products,
            'out_of_stock':      out_of_stock,
            'low_stock':         low_stock,
            'healthy_stock':     total_products - out_of_stock - low_stock,
            'unresolved_alerts': unresolved,
        })

    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        alert = self.get_object()
        if alert.is_resolved:
            return Response(
                {'error': 'لا يمكن إضافة ملاحظة لتذكرة محلولة'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = StockAlertNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(alert=alert, user=request.user)
        if alert.ticket_status == 'open':
            alert.ticket_status = 'in_progress'
            alert.save(update_fields=['ticket_status'])
        return Response(StockAlertSerializer(alert).data)

    @action(detail=True, methods=['post'])
    def create_purchase_order(self, request, pk=None):
        alert   = self.get_object()
        product = alert.product
        if alert.is_resolved:
            return Response({'error': 'التذكرة محلولة مسبقاً'}, status=status.HTTP_400_BAD_REQUEST)
        if alert.linked_po:
            return Response(
                {'error': 'يوجد أمر شراء مرتبط بالفعل: ' + alert.linked_po.reference_number},
                status=status.HTTP_400_BAD_REQUEST
            )
        supplier_id   = request.data.get('supplier')
        quantity      = int(request.data.get('quantity', 1))
        unit_cost     = request.data.get('unit_cost', 0)
        unit_id       = request.data.get('unit')
        expected_date = request.data.get('expected_date')
        po_notes      = request.data.get('notes', '')
        with transaction.atomic():
            ref = 'PO-ALERT-' + str(alert.id)[:8].upper()
            po  = PurchaseOrder.objects.create(
                reference_number = ref,
                supplier_id      = supplier_id or None,
                user             = request.user,
                status           = 'ordered',
                expected_date    = expected_date or None,
                notes            = po_notes or 'أمر شراء من تنبيه المنتج: ' + product.name,
            )
            PurchaseOrderItem.objects.create(
                order     = po,
                product   = product,
                unit_id   = unit_id or None,
                quantity  = quantity,
                unit_cost = unit_cost,
            )
            po.recalculate_total()
            alert.linked_po     = po
            alert.ticket_status = 'ordered'
            alert.save(update_fields=['linked_po', 'ticket_status'])
            StockAlertNote.objects.create(
                alert=alert, user=request.user, note_type='action',
                text='تم إنشاء أمر شراء #' + po.reference_number + ' بكمية ' + str(quantity) + ' وحدة',
            )
        return Response({
            'alert': StockAlertSerializer(alert).data,
            'purchase_order': {
                'id':               str(po.id),
                'reference_number': po.reference_number,
                'status':           po.status,
                'total_cost':       str(po.total_cost),
            },
        })

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        if alert.linked_po and alert.linked_po.status != 'received':
            return Response(
                {'error': 'أمر الشراء #' + alert.linked_po.reference_number + ' لم يُستلم بعد. استلم البضاعة أولاً.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        note_text = request.data.get('note', '')
        with transaction.atomic():
            alert.resolve(user=request.user)
            if note_text:
                StockAlertNote.objects.create(
                    alert=alert, user=request.user,
                    note_type='action',
                    text='تم الحل: ' + note_text,
                )
        return Response(StockAlertSerializer(alert).data)

    @action(detail=True, methods=['patch'])
    def update_meta(self, request, pk=None):
        alert   = self.get_object()
        allowed = ['priority', 'assigned_to', 'deadline', 'ticket_status']
        for field in allowed:
            if field in request.data:
                setattr(alert, field, request.data[field] or None)
        alert.save()
        return Response(StockAlertSerializer(alert).data)

# ── StockMovement (read-only) ──────────────────────────────
class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset           = StockMovement.objects.select_related('product', 'user', 'unit').all()
    serializer_class   = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['movement_type', 'product']
    search_fields      = ['product__name', 'reference', 'notes']
    ordering           = ['-created_at']
