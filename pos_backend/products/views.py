from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from .models import Category, Product, UnitOfMeasure, ProductUnitPrice
from .serializers import (
    CategorySerializer, ProductSerializer,
    ProductListSerializer, UnitOfMeasureSerializer,
    ProductUnitPriceSerializer,
)


class UnitOfMeasureViewSet(viewsets.ModelViewSet):
    queryset           = UnitOfMeasure.objects.filter(is_active=True)
    serializer_class   = UnitOfMeasureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'symbol']
    ordering           = ['category', 'factor']


class CategoryViewSet(viewsets.ModelViewSet):
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name']
    ordering           = ['name']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related(
        'category', 'base_unit', 'purchase_unit'
    ).prefetch_related('unit_prices__unit').all()
    serializer_class   = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['category', 'is_active']
    search_fields      = ['name', 'barcode']
    ordering_fields    = ['name', 'price', 'stock', 'created_at']
    ordering           = ['-created_at']

    def _require_perm(self, request, perm):
        if not (request.user.is_superuser or request.user.has_perm('users.' + perm)):
            raise PermissionDenied('غير مصرح')

    def get_queryset(self):
        user = self.request.user
        if not (user.is_superuser
                or user.has_perm('users.products_view')
                or user.has_perm('users.products_manage')):
            return Product.objects.none()
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer

    def perform_create(self, serializer):
        self._require_perm(self.request, 'products_manage')
        product = serializer.save()
        # ✅ initial StockMovement لو المنتج اتضاف بمخزون
        if product.stock and product.stock > 0:
            from inventory.models import StockMovement
            StockMovement.objects.create(
                product=product,
                movement_type='initial',
                quantity=product.stock,
                stock_before=0,
                stock_after=product.stock,
                unit=product.base_unit,
                unit_quantity=product.stock,
                notes='initial stock',
                user=self.request.user,
            )

    def perform_update(self, serializer):
        self._require_perm(self.request, 'products_manage')
        serializer.save()

    def perform_destroy(self, instance):
        self._require_perm(self.request, 'products_manage')
        instance.delete()

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        products = self.get_queryset().filter(is_active=True).filter(
            stock__lte=F('min_stock')
        )
        return Response(self.get_serializer(products, many=True).data)

    @action(detail=False, methods=['get'])
    def by_barcode(self, request):
        barcode = request.query_params.get('barcode', '')
        if not barcode:
            return Response({'error': 'الباركود مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.select_related(
                'base_unit', 'purchase_unit'
            ).prefetch_related('unit_prices__unit').get(
                barcode=barcode, is_active=True
            )
            return Response(ProductSerializer(product).data)
        except Product.DoesNotExist:
            return Response({'error': 'المنتج غير موجود'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def set_unit_prices(self, request, pk=None):
        """تحديث/إنشاء أسعار الوحدات للمنتج"""
        self._require_perm(request, 'products_manage')
        product = self.get_object()
        prices  = request.data.get('prices', [])
        for p in prices:
            unit_id  = p.get('unit')
            price    = p.get('price')
            is_auto  = p.get('is_auto', False)
            is_active = p.get('is_active', True)
            if not unit_id:
                continue
            obj, _ = ProductUnitPrice.objects.get_or_create(
                product=product, unit_id=unit_id
            )
            obj.is_auto   = is_auto
            obj.is_active = is_active
            if not is_auto and price is not None:
                obj.price = price
            obj.save()
        return Response(ProductSerializer(product).data)
