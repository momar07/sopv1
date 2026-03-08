from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import F
from .models import Supplier, PurchaseOrder, StockAdjustment, StockAlert, StockMovement
from .serializers import (
    SupplierSerializer, PurchaseOrderSerializer,
    StockAdjustmentSerializer, StockAlertSerializer, StockMovementSerializer,
)
from products.models import Product


class SupplierViewSet(viewsets.ModelViewSet):
    queryset           = Supplier.objects.all()
    serializer_class   = SupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'phone', 'email']
    ordering           = ['name']


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('supplier','user').prefetch_related('items__product').all()
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
            return Response({'error': 'لا يمكن استلام امر ملغي'}, status=status.HTTP_400_BAD_REQUEST)
        if order.status == 'received':
            return Response({'error': 'تم استلام هذا الامر مسبقا'}, status=status.HTTP_400_BAD_REQUEST)

        received_quantities = request.data.get('received_quantities', {})
        from django.db import transaction
        with transaction.atomic():
            for item in order.items.select_related('product').all():
                qty = received_quantities.get(str(item.id), item.remaining_quantity)
                qty = max(0, int(qty))
                if qty > 0:
                    product = item.product
                    stock_before = product.stock
                    Product.objects.filter(id=product.id).update(
                        stock=F('stock') + qty,
                        cost=item.unit_cost
                    )
                    product.refresh_from_db()
                    stock_after = product.stock
                    item.received_quantity = item.received_quantity + qty
                    item.save(update_fields=['received_quantity'])
                    StockAdjustment.objects.create(
                        product         = product,
                        user            = request.user,
                        quantity_before = stock_before,
                        quantity_change = qty,
                        quantity_after  = stock_after,
                        reason          = 'other',
                        notes           = f"استلام من امر شراء #{order.reference_number}"
                    )
                    StockMovement.objects.create(
                        product       = product,
                        movement_type = 'purchase',
                        quantity      = qty,
                        stock_before  = stock_before,
                        stock_after   = stock_after,
                        reference     = order.reference_number,
                        user          = request.user,
                        notes         = f"استلام امر شراء #{order.reference_number}"
                    )
            order.status      = 'received'
            order.received_at = timezone.now()
            order.save(update_fields=['status', 'received_at'])

        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status == 'received':
            return Response({'error': 'لا يمكن الغاء امر تم استلامه'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        return Response(self.get_serializer(order).data)


class StockAdjustmentViewSet(viewsets.ModelViewSet):
    queryset           = StockAdjustment.objects.select_related('product','user').all()
    serializer_class   = StockAdjustmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['product', 'reason']
    search_fields      = ['product__name', 'notes']
    ordering           = ['-created_at']
    http_method_names  = ['get', 'post', 'head', 'options']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class StockAlertViewSet(viewsets.ModelViewSet):
    queryset           = StockAlert.objects.select_related('product').all()
    serializer_class   = StockAlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['alert_type', 'is_resolved', 'product']
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
                StockAlert.objects.create(product=product, alert_type='out',
                    threshold=threshold, current_stock=0)
                created += 1
            elif product.stock <= threshold:
                StockAlert.objects.create(product=product, alert_type='low',
                    threshold=threshold, current_stock=product.stock)
                created += 1
        return Response({'created_alerts': created, 'checked_products': products.count()})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert             = self.get_object()
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save(update_fields=['is_resolved', 'resolved_at'])
        return Response(self.get_serializer(alert).data)

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


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset           = StockMovement.objects.select_related('product','user').all()
    serializer_class   = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['movement_type', 'product']
    search_fields      = ['product__name', 'reference', 'notes']
    ordering           = ['-created_at']
