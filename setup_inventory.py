#!/usr/bin/env python3
"""
setup_inventory.py
==================
سكريبت تلقائي لإضافة موديول المخزون كامل (backend + frontend)
شغّله من root الـ project (جنب مجلد pos_backend و pos_frontend):
    python setup_inventory.py
"""

import os
import subprocess
import sys
import textwrap

# ─── paths ────────────────────────────────────────────────────────────────────
ROOT          = os.path.dirname(os.path.abspath(__file__))
BACKEND       = os.path.join(ROOT, "pos_backend")
FRONTEND_SRC  = os.path.join(ROOT, "pos_frontend", "src")
PAGES_DIR     = os.path.join(FRONTEND_SRC, "pages")
SERVICES_FILE = os.path.join(FRONTEND_SRC, "services", "api.js")
INVENTORY_APP = os.path.join(BACKEND, "inventory")
SETTINGS_FILE = os.path.join(BACKEND, "pos_backend", "settings.py")
URLS_FILE     = os.path.join(BACKEND, "pos_backend", "urls.py")

# ─── helpers ──────────────────────────────────────────────────────────────────
def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).lstrip("\n"))
    print(f"  ✅ كتب: {os.path.relpath(path, ROOT)}")

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def patch(path, marker, addition, mode="after"):
    """أضف سطر/نص قبل أو بعد marker — لو مش موجود أصلاً."""
    content = read(path)
    if addition.strip() in content:
        print(f"  ⏭️  موجود بالفعل: {os.path.relpath(path, ROOT)}")
        return
    if marker not in content:
        print(f"  ⚠️  Marker مش موجود في {os.path.relpath(path, ROOT)} — تخطّي")
        return
    if mode == "after":
        content = content.replace(marker, marker + "\n" + addition, 1)
    else:
        content = content.replace(marker, addition + "\n" + marker, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ عدّل: {os.path.relpath(path, ROOT)}")

def run(cmd, cwd=None):
    print(f"  ▶ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or BACKEND)
    if result.returncode != 0:
        print(f"  ⚠️  الأمر انتهى بكود {result.returncode}")

def section(title):
    print(f"\n{'═'*55}")
    print(f"  {title}")
    print('═'*55)

# ══════════════════════════════════════════════════════════════════════════════
#  1. BACKEND FILES
# ══════════════════════════════════════════════════════════════════════════════
section("1/6 — إنشاء ملفات الـ inventory app")

# __init__.py
write(os.path.join(INVENTORY_APP, "__init__.py"), "")

# apps.py
write(os.path.join(INVENTORY_APP, "apps.py"), """
    from django.apps import AppConfig

    class InventoryConfig(AppConfig):
        default_auto_field = 'django.db.models.BigAutoField'
        name = 'inventory'
        verbose_name = 'إدارة المخزون'
""")

# models.py
write(os.path.join(INVENTORY_APP, "models.py"), """
    from django.db import models
    from django.contrib.auth.models import User
    import uuid


    class Supplier(models.Model):
        id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
        name       = models.CharField(max_length=200, verbose_name="اسم المورد")
        phone      = models.CharField(max_length=20, blank=True, null=True, verbose_name="الهاتف")
        email      = models.EmailField(blank=True, null=True, verbose_name="البريد الإلكتروني")
        address    = models.TextField(blank=True, null=True, verbose_name="العنوان")
        notes      = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
        is_active  = models.BooleanField(default=True, verbose_name="نشط")
        created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
        updated_at = models.DateTimeField(auto_now=True,     verbose_name="تاريخ التحديث")

        class Meta:
            verbose_name        = "مورد"
            verbose_name_plural = "الموردون"
            ordering            = ['name']

        def __str__(self):
            return self.name


    class PurchaseOrder(models.Model):
        STATUS_CHOICES = [
            ('draft',     'مسودة'),
            ('ordered',   'تم الطلب'),
            ('received',  'تم الاستلام'),
            ('cancelled', 'ملغي'),
        ]

        id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
        reference_number = models.CharField(max_length=50, unique=True, verbose_name="رقم المرجع")
        supplier         = models.ForeignKey(
            Supplier, on_delete=models.SET_NULL, null=True, blank=True,
            related_name='purchase_orders', verbose_name="المورد"
        )
        user = models.ForeignKey(
            User, on_delete=models.SET_NULL, null=True,
            related_name='purchase_orders', verbose_name="الموظف المسؤول"
        )
        status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="الحالة")
        total_cost    = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="إجمالي التكلفة")
        notes         = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
        expected_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الاستلام المتوقع")
        received_at   = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الاستلام الفعلي")
        created_at    = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
        updated_at    = models.DateTimeField(auto_now=True,     verbose_name="تاريخ التحديث")

        class Meta:
            verbose_name        = "أمر شراء"
            verbose_name_plural = "أوامر الشراء"
            ordering            = ['-created_at']

        def __str__(self):
            return f"أمر شراء #{self.reference_number}"

        def recalculate_total(self):
            from django.db.models import Sum, F, DecimalField, ExpressionWrapper
            total = self.items.aggregate(
                total=Sum(ExpressionWrapper(
                    F('quantity') * F('unit_cost'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                ))
            )['total'] or 0
            self.total_cost = total
            self.save(update_fields=['total_cost'])


    class PurchaseOrderItem(models.Model):
        id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
        order             = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items', verbose_name="أمر الشراء")
        product           = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='purchase_items', verbose_name="المنتج")
        quantity          = models.PositiveIntegerField(verbose_name="الكمية المطلوبة")
        received_quantity = models.PositiveIntegerField(default=0, verbose_name="الكمية المستلمة")
        unit_cost         = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="تكلفة الوحدة")

        class Meta:
            verbose_name        = "عنصر أمر شراء"
            verbose_name_plural = "عناصر أوامر الشراء"

        def __str__(self):
            return f"{self.product.name} × {self.quantity}"

        @property
        def subtotal(self):
            return self.unit_cost * self.quantity

        @property
        def remaining_quantity(self):
            return self.quantity - self.received_quantity


    class StockAdjustment(models.Model):
        REASON_CHOICES = [
            ('count',  'جرد دوري'),
            ('damage', 'تلف'),
            ('loss',   'فقد / سرقة'),
            ('return', 'مرتجع من عميل'),
            ('expiry', 'انتهاء صلاحية'),
            ('other',  'أخرى'),
        ]

        id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
        product         = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='stock_adjustments', verbose_name="المنتج")
        user            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='stock_adjustments', verbose_name="الموظف")
        quantity_before = models.IntegerField(verbose_name="الكمية قبل")
        quantity_change = models.IntegerField(verbose_name="التغيير")
        quantity_after  = models.IntegerField(verbose_name="الكمية بعد")
        reason          = models.CharField(max_length=20, choices=REASON_CHOICES, default='count', verbose_name="السبب")
        notes           = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
        created_at      = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التسوية")

        class Meta:
            verbose_name        = "تسوية مخزون"
            verbose_name_plural = "تسويات المخزون"
            ordering            = ['-created_at']

        def __str__(self):
            sign = '+' if self.quantity_change >= 0 else ''
            return f"{self.product.name} | {sign}{self.quantity_change} | {self.get_reason_display()}"


    class StockAlert(models.Model):
        ALERT_TYPES = [
            ('low',    'مخزون منخفض'),
            ('out',    'نفاد المخزون'),
            ('expiry', 'قرب انتهاء الصلاحية'),
        ]

        id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
        product       = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='stock_alerts', verbose_name="المنتج")
        alert_type    = models.CharField(max_length=20, choices=ALERT_TYPES, verbose_name="نوع التنبيه")
        threshold     = models.IntegerField(default=10, verbose_name="حد التنبيه")
        current_stock = models.IntegerField(verbose_name="المخزون الحالي وقت التنبيه")
        is_resolved   = models.BooleanField(default=False, verbose_name="تم الحل")
        resolved_at   = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحل")
        created_at    = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التنبيه")

        class Meta:
            verbose_name        = "تنبيه مخزون"
            verbose_name_plural = "تنبيهات المخزون"
            ordering            = ['-created_at']

        def __str__(self):
            return f"{self.get_alert_type_display()} — {self.product.name} ({self.current_stock})"
""")

# serializers.py
write(os.path.join(INVENTORY_APP, "serializers.py"), """
    from rest_framework import serializers
    from django.db import transaction
    from django.utils import timezone
    from django.db.models import F
    from .models import Supplier, PurchaseOrder, PurchaseOrderItem, StockAdjustment, StockAlert
    from products.models import Product


    class SupplierSerializer(serializers.ModelSerializer):
        orders_count = serializers.SerializerMethodField()

        class Meta:
            model  = Supplier
            fields = ['id','name','phone','email','address','notes','is_active','orders_count','created_at','updated_at']
            read_only_fields = ['id','created_at','updated_at']

        def get_orders_count(self, obj):
            return obj.purchase_orders.count()


    class PurchaseOrderItemSerializer(serializers.ModelSerializer):
        product_name    = serializers.CharField(source='product.name',    read_only=True)
        product_barcode = serializers.CharField(source='product.barcode', read_only=True)
        subtotal            = serializers.ReadOnlyField()
        remaining_quantity  = serializers.ReadOnlyField()

        class Meta:
            model  = PurchaseOrderItem
            fields = ['id','product','product_name','product_barcode',
                      'quantity','received_quantity','unit_cost','subtotal','remaining_quantity']
            read_only_fields = ['id','received_quantity']


    class PurchaseOrderSerializer(serializers.ModelSerializer):
        items         = PurchaseOrderItemSerializer(many=True)
        supplier_name = serializers.CharField(source='supplier.name', read_only=True)
        user_name     = serializers.SerializerMethodField()

        class Meta:
            model  = PurchaseOrder
            fields = ['id','reference_number','supplier','supplier_name','user','user_name',
                      'status','total_cost','notes','expected_date','received_at',
                      'items','created_at','updated_at']
            read_only_fields = ['id','user','total_cost','received_at','created_at','updated_at']

        def get_user_name(self, obj):
            return obj.user.get_full_name() or obj.user.username if obj.user else None

        @transaction.atomic
        def create(self, validated_data):
            items_data = validated_data.pop('items', [])
            order = PurchaseOrder.objects.create(**validated_data)
            for item in items_data:
                PurchaseOrderItem.objects.create(order=order, **item)
            order.recalculate_total()
            return order

        @transaction.atomic
        def update(self, instance, validated_data):
            items_data = validated_data.pop('items', None)
            for attr, val in validated_data.items():
                setattr(instance, attr, val)
            instance.save()
            if items_data is not None:
                instance.items.all().delete()
                for item in items_data:
                    PurchaseOrderItem.objects.create(order=instance, **item)
                instance.recalculate_total()
            return instance


    class StockAdjustmentSerializer(serializers.ModelSerializer):
        product_name   = serializers.CharField(source='product.name', read_only=True)
        user_name      = serializers.SerializerMethodField()
        reason_display = serializers.CharField(source='get_reason_display', read_only=True)

        class Meta:
            model  = StockAdjustment
            fields = ['id','product','product_name','user','user_name',
                      'quantity_before','quantity_change','quantity_after',
                      'reason','reason_display','notes','created_at']
            read_only_fields = ['id','user','quantity_before','quantity_after','created_at']

        def get_user_name(self, obj):
            return obj.user.get_full_name() or obj.user.username if obj.user else None

        @transaction.atomic
        def create(self, validated_data):
            product = validated_data['product']
            change  = validated_data['quantity_change']
            qty_before = product.stock
            qty_after  = qty_before + change
            if qty_after < 0:
                raise serializers.ValidationError(
                    f"المخزون لا يمكن أن يكون سالباً — المتاح: {qty_before}, التغيير: {change}"
                )
            Product.objects.filter(id=product.id).update(stock=F('stock') + change)
            validated_data['quantity_before'] = qty_before
            validated_data['quantity_after']  = qty_after
            return super().create(validated_data)


    class StockAlertSerializer(serializers.ModelSerializer):
        product_name      = serializers.CharField(source='product.name',    read_only=True)
        product_barcode   = serializers.CharField(source='product.barcode', read_only=True)
        alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)

        class Meta:
            model  = StockAlert
            fields = ['id','product','product_name','product_barcode',
                      'alert_type','alert_type_display','threshold',
                      'current_stock','is_resolved','resolved_at','created_at']
            read_only_fields = ['id','created_at']
""")

# views.py
write(os.path.join(INVENTORY_APP, "views.py"), """
    from rest_framework import viewsets, filters, status
    from rest_framework.decorators import action
    from rest_framework.response import Response
    from rest_framework.permissions import IsAuthenticated
    from django_filters.rest_framework import DjangoFilterBackend
    from django.utils import timezone
    from django.db.models import F
    from .models import Supplier, PurchaseOrder, StockAdjustment, StockAlert
    from .serializers import (
        SupplierSerializer, PurchaseOrderSerializer,
        StockAdjustmentSerializer, StockAlertSerializer,
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
                return Response({'error': 'لا يمكن استلام أمر ملغي'}, status=status.HTTP_400_BAD_REQUEST)
            if order.status == 'received':
                return Response({'error': 'تم استلام هذا الأمر مسبقاً'}, status=status.HTTP_400_BAD_REQUEST)

            received_quantities = request.data.get('received_quantities', {})
            from django.db import transaction
            with transaction.atomic():
                for item in order.items.select_related('product').all():
                    qty = received_quantities.get(str(item.id), item.remaining_quantity)
                    qty = max(0, int(qty))
                    if qty > 0:
                        Product.objects.filter(id=item.product.id).update(
                            stock=F('stock') + qty,
                            cost=item.unit_cost
                        )
                        item.received_quantity = item.received_quantity + qty
                        item.save(update_fields=['received_quantity'])
                        product = item.product
                        product.refresh_from_db()
                        StockAdjustment.objects.create(
                            product=product,
                            user=request.user,
                            quantity_before=product.stock - qty,
                            quantity_change=qty,
                            quantity_after=product.stock,
                            reason='count',
                            notes=f'استلام من أمر شراء #{order.reference_number}'
                        )
                order.status      = 'received'
                order.received_at = timezone.now()
                order.save(update_fields=['status', 'received_at'])

            return Response(self.get_serializer(order).data)

        @action(detail=True, methods=['post'])
        def cancel(self, request, pk=None):
            order = self.get_object()
            if order.status == 'received':
                return Response({'error': 'لا يمكن إلغاء أمر تم استلامه'}, status=status.HTTP_400_BAD_REQUEST)
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
        http_method_names  = ['get', 'patch', 'head', 'options']

        @action(detail=False, methods=['post'])
        def check_and_generate(self, request):
            threshold = int(request.data.get('threshold', 10))
            products  = Product.objects.filter(is_active=True)
            created   = 0
            for product in products:
                if StockAlert.objects.filter(product=product, is_resolved=False).exists():
                    continue
                if product.stock == 0:
                    StockAlert.objects.create(product=product, alert_type='out',  threshold=threshold, current_stock=0)
                    created += 1
                elif product.stock <= threshold:
                    StockAlert.objects.create(product=product, alert_type='low',  threshold=threshold, current_stock=product.stock)
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
""")

# urls.py
write(os.path.join(INVENTORY_APP, "urls.py"), """
    from rest_framework.routers import DefaultRouter
    from .views import SupplierViewSet, PurchaseOrderViewSet, StockAdjustmentViewSet, StockAlertViewSet

    router = DefaultRouter()
    router.register('inventory/suppliers',       SupplierViewSet,       basename='supplier')
    router.register('inventory/purchase-orders', PurchaseOrderViewSet,  basename='purchase-order')
    router.register('inventory/adjustments',     StockAdjustmentViewSet,basename='stock-adjustment')
    router.register('inventory/alerts',          StockAlertViewSet,     basename='stock-alert')

    urlpatterns = router.urls
""")

# admin.py
write(os.path.join(INVENTORY_APP, "admin.py"), """
    from django.contrib import admin
    from .models import Supplier, PurchaseOrder, PurchaseOrderItem, StockAdjustment, StockAlert


    class PurchaseOrderItemInline(admin.TabularInline):
        model       = PurchaseOrderItem
        extra       = 0
        readonly_fields = ['received_quantity']


    @admin.register(Supplier)
    class SupplierAdmin(admin.ModelAdmin):
        list_display  = ['name', 'phone', 'email', 'is_active', 'created_at']
        search_fields = ['name', 'phone', 'email']
        list_filter   = ['is_active']


    @admin.register(PurchaseOrder)
    class PurchaseOrderAdmin(admin.ModelAdmin):
        list_display    = ['reference_number','supplier','status','total_cost','user','created_at']
        list_filter     = ['status', 'supplier']
        search_fields   = ['reference_number', 'supplier__name']
        inlines         = [PurchaseOrderItemInline]
        readonly_fields = ['total_cost','received_at','created_at','updated_at']


    @admin.register(StockAdjustment)
    class StockAdjustmentAdmin(admin.ModelAdmin):
        list_display    = ['product','quantity_before','quantity_change','quantity_after','reason','user','created_at']
        list_filter     = ['reason', 'created_at']
        search_fields   = ['product__name', 'notes']
        readonly_fields = ['quantity_before','quantity_after','created_at']


    @admin.register(StockAlert)
    class StockAlertAdmin(admin.ModelAdmin):
        list_display  = ['product','alert_type','current_stock','threshold','is_resolved','created_at']
        list_filter   = ['alert_type', 'is_resolved']
        search_fields = ['product__name']
""")

# migrations/__init__.py
write(os.path.join(INVENTORY_APP, "migrations", "__init__.py"), "")

# ══════════════════════════════════════════════════════════════════════════════
#  2. PATCH settings.py
# ══════════════════════════════════════════════════════════════════════════════
section("2/6 — تعديل settings.py")
patch(
    SETTINGS_FILE,
    "    'ui_builder',",
    "    'inventory',",
    mode="after"
)

# ══════════════════════════════════════════════════════════════════════════════
#  3. PATCH urls.py
# ══════════════════════════════════════════════════════════════════════════════
section("3/6 — تعديل urls.py")
patch(
    URLS_FILE,
    "    path('api/', include('sales.urls')),",
    "    path('api/', include('inventory.urls')),",
    mode="after"
)

# ══════════════════════════════════════════════════════════════════════════════
#  4. RUN MIGRATIONS
# ══════════════════════════════════════════════════════════════════════════════
section("4/6 — تشغيل Migrations")
run("python manage.py makemigrations inventory")
run("python manage.py migrate")

# ══════════════════════════════════════════════════════════════════════════════
#  5. FRONTEND — api.js
# ══════════════════════════════════════════════════════════════════════════════
section("5/6 — تعديل frontend/services/api.js")

INVENTORY_API_BLOCK = """
// ── Inventory API ──────────────────────────────────────────────────────────
export const inventoryAPI = {
  // Suppliers
  getSuppliers:    (params) => api.get('/inventory/suppliers/', { params }),
  createSupplier:  (data)   => api.post('/inventory/suppliers/', data),
  updateSupplier:  (id, data) => api.put(`/inventory/suppliers/${id}/`, data),
  deleteSupplier:  (id)     => api.delete(`/inventory/suppliers/${id}/`),

  // Purchase Orders
  getPurchaseOrders:      (params) => api.get('/inventory/purchase-orders/', { params }),
  getPurchaseOrder:       (id)     => api.get(`/inventory/purchase-orders/${id}/`),
  createPurchaseOrder:    (data)   => api.post('/inventory/purchase-orders/', data),
  updatePurchaseOrder:    (id, data) => api.put(`/inventory/purchase-orders/${id}/`, data),
  receivePurchaseOrder:   (id, data) => api.post(`/inventory/purchase-orders/${id}/receive/`, data),
  cancelPurchaseOrder:    (id)     => api.post(`/inventory/purchase-orders/${id}/cancel/`),

  // Stock Adjustments
  getAdjustments:   (params) => api.get('/inventory/adjustments/', { params }),
  createAdjustment: (data)   => api.post('/inventory/adjustments/', data),

  // Alerts
  getAlerts:             (params) => api.get('/inventory/alerts/', { params }),
  getAlertsSummary:      (params) => api.get('/inventory/alerts/summary/', { params }),
  checkAndGenerateAlerts:(data)   => api.post('/inventory/alerts/check_and_generate/', data),
  resolveAlert:          (id)     => api.post(`/inventory/alerts/${id}/resolve/`),
};
"""

patch(SERVICES_FILE, "export default api;", INVENTORY_API_BLOCK, mode="before")

# ══════════════════════════════════════════════════════════════════════════════
#  6. FRONTEND — InventoryPage.jsx
# ══════════════════════════════════════════════════════════════════════════════
section("6/6 — إنشاء InventoryPage.jsx")

INVENTORY_PAGE = r"""
import React, { useCallback, useEffect, useState } from 'react';
import { inventoryAPI, productsAPI } from '../services/api';

const fmt = (n) => Number(n || 0).toFixed(2);

const Badge = ({ label, color }) => {
  const map = {
    green:  'bg-green-100 text-green-800',
    red:    'bg-red-100 text-red-800',
    yellow: 'bg-yellow-100 text-yellow-800',
    blue:   'bg-blue-100 text-blue-800',
    gray:   'bg-gray-100 text-gray-600',
  };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${map[color]||map.gray}`}>{label}</span>;
};

const statusColor = (s) => ({ draft:'gray', ordered:'blue', received:'green', cancelled:'red' }[s]||'gray');
const alertColor  = (t) => ({ out:'red', low:'yellow', expiry:'yellow' }[t]||'gray');

const Spinner = () => (
  <div className="flex items-center justify-center h-40">
    <i className="fas fa-spinner fa-spin text-4xl text-blue-500"></i>
  </div>
);

const Toast = ({ msg, type }) => (
  <div className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-2xl shadow-xl font-bold text-sm
    ${type==='error'?'bg-red-600 text-white':'bg-green-600 text-white'}`}>{msg}</div>
);

const Modal = ({ title, onClose, children }) => (
  <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      onClick={(e)=>e.stopPropagation()}>
      <div className="flex justify-between items-center px-5 py-4 border-b">
        <h3 className="font-black text-gray-800">{title}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-700 font-black text-xl">×</button>
      </div>
      <div className="p-5">{children}</div>
    </div>
  </div>
);

const Field = ({ label, children }) => (
  <div>
    <label className="block text-xs font-bold text-gray-500 mb-1">{label}</label>
    {children}
  </div>
);

const INP = 'w-full border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 bg-white transition';

// ═══════════════════════════════════════════════════════════════════════════
export default function InventoryPage() {
  const [tab, setTab] = useState('summary');
  const tabs = [
    { key:'summary',   label:'📊 ملخص المخزون' },
    { key:'orders',    label:'📦 أوامر الشراء'  },
    { key:'adjust',    label:'⚖️ تسوية المخزون' },
    { key:'alerts',    label:'🔔 التنبيهات'     },
    { key:'suppliers', label:'🏭 الموردون'       },
  ];
  return (
    <div dir="rtl" className="p-4 min-h-screen bg-gray-50">
      <div className="mb-5">
        <h1 className="text-2xl font-black text-gray-800">🏪 إدارة المخزون</h1>
        <p className="text-gray-500 text-sm mt-1">استلام البضاعة · تسوية المخزون · تنبيهات النقص</p>
      </div>
      <div className="flex gap-2 flex-wrap mb-5">
        {tabs.map((t) => (
          <button key={t.key} onClick={()=>setTab(t.key)}
            className={`px-4 py-2 rounded-xl font-bold text-sm transition-all ${
              tab===t.key ? 'bg-blue-600 text-white shadow' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}>{t.label}</button>
        ))}
      </div>
      {tab==='summary'   && <SummaryPanel />}
      {tab==='orders'    && <PurchaseOrdersPanel />}
      {tab==='adjust'    && <AdjustPanel />}
      {tab==='alerts'    && <AlertsPanel />}
      {tab==='suppliers' && <SuppliersPanel />}
    </div>
  );
}

// ─── Summary ────────────────────────────────────────────────────────────────
function SummaryPanel() {
  const [summary, setSummary]     = useState(null);
  const [lowProducts, setLow]     = useState([]);
  const [loading, setLoading]     = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, lp] = await Promise.all([
        inventoryAPI.getAlertsSummary({ threshold:10 }),
        productsAPI.getLowStock(),
      ]);
      setSummary(s.data);
      setLow(lp.data || []);
    } catch { /**/ } finally { setLoading(false); }
  }, []);

  useEffect(()=>{ load(); }, [load]);

  const handleGenerate = async () => {
    await inventoryAPI.checkAndGenerateAlerts({ threshold:10 });
    load();
  };

  if (loading) return <Spinner />;

  const cards = [
    { label:'إجمالي المنتجات',    value: summary?.total_products   ||0, color:'blue',   icon:'📦' },
    { label:'مخزون منخفض',        value: summary?.low_stock        ||0, color:'yellow', icon:'⚠️' },
    { label:'نفاد المخزون',        value: summary?.out_of_stock     ||0, color:'red',    icon:'🚨' },
    { label:'مخزون كافي',          value: summary?.healthy_stock    ||0, color:'green',  icon:'✅' },
    { label:'تنبيهات غير محلولة', value: summary?.unresolved_alerts||0, color:'red',    icon:'🔔' },
  ];
  const cm = { blue:'bg-blue-50 border-blue-200 text-blue-700', yellow:'bg-yellow-50 border-yellow-200 text-yellow-700', red:'bg-red-50 border-red-200 text-red-700', green:'bg-green-50 border-green-200 text-green-700' };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {cards.map((c) => (
          <div key={c.label} className={`rounded-2xl border p-4 ${cm[c.color]}`}>
            <div className="text-2xl mb-1">{c.icon}</div>
            <div className="text-3xl font-black">{c.value}</div>
            <div className="text-sm font-semibold mt-1">{c.label}</div>
          </div>
        ))}
      </div>
      <button onClick={handleGenerate}
        className="bg-yellow-500 hover:bg-yellow-600 text-white font-bold px-5 py-2 rounded-xl text-sm transition">
        🔄 فحص وتحديث التنبيهات
      </button>
      {lowProducts.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b bg-yellow-50">
            <h2 className="font-black text-yellow-800">⚠️ منتجات تحتاج إعادة طلب ({lowProducts.length})</h2>
          </div>
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50 text-gray-500 text-right">
              <th className="px-4 py-3 font-bold">المنتج</th>
              <th className="px-4 py-3 font-bold">الباركود</th>
              <th className="px-4 py-3 font-bold">المخزون</th>
              <th className="px-4 py-3 font-bold">سعر البيع</th>
            </tr></thead>
            <tbody>
              {lowProducts.map((p) => (
                <tr key={p.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3 font-bold">{p.name}</td>
                  <td className="px-4 py-3 text-gray-500">{p.barcode||'—'}</td>
                  <td className="px-4 py-3"><span className={`font-black ${p.stock===0?'text-red-600':'text-yellow-600'}`}>{p.stock}</span></td>
                  <td className="px-4 py-3">{fmt(p.price)} ج</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Purchase Orders ─────────────────────────────────────────────────────────
function PurchaseOrdersPanel() {
  const [orders, setOrders]       = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts]   = useState([]);
  const [loading, setLoading]     = useState(true);
  const [showForm, setShowForm]   = useState(false);
  const [selected, setSelected]   = useState(null);
  const [toast, setToast]         = useState(null);
  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [o,s,p] = await Promise.all([
        inventoryAPI.getPurchaseOrders(),
        inventoryAPI.getSuppliers(),
        productsAPI.getAll({ page_size:200 }),
      ]);
      setOrders(o.data?.results||o.data||[]);
      setSuppliers(s.data?.results||s.data||[]);
      setProducts(p.data?.results||p.data||[]);
    } catch {/**/ } finally { setLoading(false); }
  }, []);

  useEffect(()=>{ load(); }, [load]);

  const handleReceive = async (order, receivedQtys) => {
    try {
      await inventoryAPI.receivePurchaseOrder(order.id, { received_quantities: receivedQtys });
      notify('✅ تم استلام البضاعة وتحديث المخزون');
      setSelected(null); load();
    } catch(e) { notify('❌ '+(e?.response?.data?.error||'خطأ في الاستلام'),'error'); }
  };

  const handleCancel = async (id) => {
    if (!window.confirm('هل أنت متأكد من إلغاء الأمر؟')) return;
    try { await inventoryAPI.cancelPurchaseOrder(id); notify('تم الإلغاء'); load(); }
    catch(e) { notify('❌ '+(e?.response?.data?.error||'خطأ'),'error'); }
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      {toast && <Toast msg={toast.msg} type={toast.type} />}
      <div className="flex justify-between items-center">
        <h2 className="font-black text-gray-700 text-lg">أوامر الشراء</h2>
        <button onClick={()=>setShowForm(true)} className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-4 py-2 rounded-xl text-sm">➕ أمر شراء جديد</button>
      </div>
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="bg-gray-50 text-gray-500 text-right">
            <th className="px-4 py-3 font-bold">رقم المرجع</th>
            <th className="px-4 py-3 font-bold">المورد</th>
            <th className="px-4 py-3 font-bold">الحالة</th>
            <th className="px-4 py-3 font-bold">الإجمالي</th>
            <th className="px-4 py-3 font-bold">التاريخ</th>
            <th className="px-4 py-3 font-bold">إجراءات</th>
          </tr></thead>
          <tbody>
            {orders.length===0 && <tr><td colSpan={6} className="text-center py-8 text-gray-400">لا توجد أوامر شراء</td></tr>}
            {orders.map((o)=>(
              <tr key={o.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 font-bold text-blue-700">{o.reference_number}</td>
                <td className="px-4 py-3">{o.supplier_name||'—'}</td>
                <td className="px-4 py-3"><Badge label={o.status} color={statusColor(o.status)} /></td>
                <td className="px-4 py-3 font-bold">{fmt(o.total_cost)} ج</td>
                <td className="px-4 py-3 text-gray-500">{o.created_at?.split('T')[0]}</td>
                <td className="px-4 py-3 flex gap-2">
                  {(o.status==='ordered'||o.status==='draft') && (
                    <button onClick={()=>setSelected(o)} className="bg-green-500 hover:bg-green-600 text-white text-xs font-bold px-3 py-1 rounded-lg">📥 استلام</button>
                  )}
                  {o.status!=='received'&&o.status!=='cancelled' && (
                    <button onClick={()=>handleCancel(o.id)} className="bg-red-100 hover:bg-red-200 text-red-700 text-xs font-bold px-3 py-1 rounded-lg">❌ إلغاء</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showForm && <NewOrderModal suppliers={suppliers} products={products}
        onClose={()=>setShowForm(false)}
        onSaved={()=>{ setShowForm(false); load(); notify('✅ تم إنشاء أمر الشراء'); }}
        onError={(msg)=>notify('❌ '+msg,'error')} />}
      {selected && <ReceiveModal order={selected} onClose={()=>setSelected(null)} onReceive={handleReceive} />}
    </div>
  );
}

function NewOrderModal({ suppliers, products, onClose, onSaved, onError }) {
  const [form, setForm] = useState({ reference_number:`PO-${Date.now()}`, supplier:'', expected_date:'', notes:'', status:'ordered' });
  const [items, setItems] = useState([{ product:'', quantity:1, unit_cost:'' }]);
  const [saving, setSaving] = useState(false);

  const addItem = () => setItems([...items,{ product:'', quantity:1, unit_cost:'' }]);
  const removeItem = (i) => setItems(items.filter((_,idx)=>idx!==i));
  const updateItem = (i,field,val) => { const n=[...items]; n[i]={...n[i],[field]:val}; setItems(n); };

  const handleSave = async () => {
    if (!form.reference_number) return onError('رقم المرجع مطلوب');
    const valid = items.filter(it=>it.product&&it.quantity>0&&it.unit_cost);
    if (!valid.length) return onError('أضف منتجاً واحداً على الأقل');
    setSaving(true);
    try {
      await inventoryAPI.createPurchaseOrder({
        ...form, supplier: form.supplier||null,
        items: valid.map(it=>({...it, quantity:Number(it.quantity), unit_cost:Number(it.unit_cost)}))
      });
      onSaved();
    } catch(e) { onError(JSON.stringify(e?.response?.data||'خطأ')); }
    finally { setSaving(false); }
  };

  return (
    <Modal title="➕ أمر شراء جديد" onClose={onClose}>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="رقم المرجع *"><input className={INP} value={form.reference_number} onChange={e=>setForm({...form,reference_number:e.target.value})} /></Field>
          <Field label="المورد">
            <select className={INP} value={form.supplier} onChange={e=>setForm({...form,supplier:e.target.value})}>
              <option value="">بدون مورد</option>
              {suppliers.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="تاريخ الاستلام المتوقع"><input type="date" className={INP} value={form.expected_date} onChange={e=>setForm({...form,expected_date:e.target.value})} /></Field>
          <Field label="الحالة">
            <select className={INP} value={form.status} onChange={e=>setForm({...form,status:e.target.value})}>
              <option value="draft">مسودة</option><option value="ordered">تم الطلب</option>
            </select>
          </Field>
        </div>
        <Field label="ملاحظات"><textarea className={INP} rows={2} value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})} /></Field>
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="font-bold text-gray-700 text-sm">المنتجات</span>
            <button onClick={addItem} className="text-blue-600 text-sm font-bold hover:underline">+ إضافة منتج</button>
          </div>
          {items.map((item,i)=>(
            <div key={i} className="flex gap-2 mb-2 items-end">
              <div className="flex-1">
                <select className={INP+' text-xs'} value={item.product} onChange={e=>updateItem(i,'product',e.target.value)}>
                  <option value="">اختر منتج</option>
                  {products.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div className="w-20"><input type="number" className={INP+' text-xs text-center'} placeholder="الكمية" min={1} value={item.quantity} onChange={e=>updateItem(i,'quantity',e.target.value)} /></div>
              <div className="w-24"><input type="number" className={INP+' text-xs text-center'} placeholder="التكلفة" min={0} step="0.01" value={item.unit_cost} onChange={e=>updateItem(i,'unit_cost',e.target.value)} /></div>
              <button onClick={()=>removeItem(i)} className="text-red-500 font-black text-xl leading-none mb-1">×</button>
            </div>
          ))}
        </div>
        <div className="flex gap-3 justify-end pt-2">
          <button onClick={onClose} className="px-4 py-2 rounded-xl border font-bold text-sm">إلغاء</button>
          <button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2 rounded-xl text-sm">{saving?'...':'💾 حفظ'}</button>
        </div>
      </div>
    </Modal>
  );
}

function ReceiveModal({ order, onClose, onReceive }) {
  const [qtys, setQtys]       = useState({});
  const [receiving, setRec]   = useState(false);
  useEffect(()=>{ const init={}; (order.items||[]).forEach(it=>{ init[it.id]=it.remaining_quantity??it.quantity; }); setQtys(init); }, [order]);
  const handleSubmit = async () => { setRec(true); await onReceive(order,qtys); setRec(false); };
  return (
    <Modal title={`📥 استلام أمر #${order.reference_number}`} onClose={onClose}>
      <table className="w-full text-sm mb-4">
        <thead><tr className="bg-gray-50 text-gray-500 text-right">
          <th className="px-3 py-2 font-bold">المنتج</th>
          <th className="px-3 py-2 font-bold">مطلوب</th>
          <th className="px-3 py-2 font-bold">مستلم فعلياً</th>
        </tr></thead>
        <tbody>
          {(order.items||[]).map(it=>(
            <tr key={it.id} className="border-t">
              <td className="px-3 py-2">{it.product_name}</td>
              <td className="px-3 py-2 font-bold">{it.quantity}</td>
              <td className="px-3 py-2">
                <input type="number" min={0} max={it.quantity} value={qtys[it.id]??it.quantity}
                  onChange={e=>setQtys({...qtys,[it.id]:Number(e.target.value)})}
                  className={INP+' w-20 text-center'} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex gap-3 justify-end">
        <button onClick={onClose} className="px-4 py-2 rounded-xl border font-bold text-sm">إلغاء</button>
        <button onClick={handleSubmit} disabled={receiving} className="bg-green-600 hover:bg-green-700 text-white font-bold px-5 py-2 rounded-xl text-sm">{receiving?'...':'📥 تأكيد الاستلام'}</button>
      </div>
    </Modal>
  );
}

// ─── Stock Adjustment ────────────────────────────────────────────────────────
function AdjustPanel() {
  const [adjustments, setAdj] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [form, setForm]         = useState({ product:'', quantity_change:'', reason:'count', notes:'' });
  const [saving, setSaving]     = useState(false);
  const [toast, setToast]       = useState(null);
  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a,p] = await Promise.all([
        inventoryAPI.getAdjustments(),
        productsAPI.getAll({ page_size:200 }),
      ]);
      setAdj(a.data?.results||a.data||[]);
      setProducts(p.data?.results||p.data||[]);
    } catch {/**/ } finally { setLoading(false); }
  }, []);

  useEffect(()=>{ load(); }, [load]);

  const handleSave = async () => {
    if (!form.product||!form.quantity_change) return notify('❌ اختر المنتج وأدخل الكمية','error');
    setSaving(true);
    try {
      await inventoryAPI.createAdjustment({ product:form.product, quantity_change:Number(form.quantity_change), reason:form.reason, notes:form.notes });
      notify('✅ تمت التسوية بنجاح');
      setForm({ product:'', quantity_change:'', reason:'count', notes:'' });
      load();
    } catch(e) { notify('❌ '+(e?.response?.data?.[0]||JSON.stringify(e?.response?.data)||'خطأ'),'error'); }
    finally { setSaving(false); }
  };

  if (loading) return <Spinner />;

  const reasonLabels = { count:'جرد دوري', damage:'تلف', loss:'فقد/سرقة', return:'مرتجع', expiry:'انتهاء صلاحية', other:'أخرى' };

  return (
    <div className="space-y-5">
      {toast && <Toast msg={toast.msg} type={toast.type} />}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
        <h2 className="font-black text-gray-700 mb-4">⚖️ تسوية مخزون جديدة</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <Field label="المنتج *">
            <select className={INP} value={form.product} onChange={e=>setForm({...form,product:e.target.value})}>
              <option value="">اختر منتج</option>
              {products.map(p=><option key={p.id} value={p.id}>{p.name} ({p.stock})</option>)}
            </select>
          </Field>
          <Field label="الكمية (+ إضافة / - خصم) *">
            <input type="number" className={INP} placeholder="مثال: 10 أو -5" value={form.quantity_change} onChange={e=>setForm({...form,quantity_change:e.target.value})} />
          </Field>
          <Field label="السبب">
            <select className={INP} value={form.reason} onChange={e=>setForm({...form,reason:e.target.value})}>
              {Object.entries(reasonLabels).map(([k,v])=><option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
          <Field label="ملاحظات">
            <input className={INP} placeholder="اختياري" value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})} />
          </Field>
        </div>
        <button onClick={handleSave} disabled={saving}
          className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2 rounded-xl text-sm">
          {saving?'...':'💾 تطبيق التسوية'}
        </button>
      </div>
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b bg-gray-50 font-black text-gray-700">سجل التسويات</div>
        <table className="w-full text-sm">
          <thead><tr className="bg-gray-50 text-gray-500 text-right">
            <th className="px-4 py-3 font-bold">المنتج</th><th className="px-4 py-3 font-bold">قبل</th>
            <th className="px-4 py-3 font-bold">التغيير</th><th className="px-4 py-3 font-bold">بعد</th>
            <th className="px-4 py-3 font-bold">السبب</th><th className="px-4 py-3 font-bold">الموظف</th>
            <th className="px-4 py-3 font-bold">التاريخ</th>
          </tr></thead>
          <tbody>
            {adjustments.length===0 && <tr><td colSpan={7} className="text-center py-8 text-gray-400">لا توجد تسويات</td></tr>}
            {adjustments.map(a=>(
              <tr key={a.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 font-bold">{a.product_name}</td>
                <td className="px-4 py-3">{a.quantity_before}</td>
                <td className="px-4 py-3"><span className={`font-black ${a.quantity_change>=0?'text-green-600':'text-red-600'}`}>{a.quantity_change>=0?'+':''}{a.quantity_change}</span></td>
                <td className="px-4 py-3 font-bold">{a.quantity_after}</td>
                <td className="px-4 py-3">{a.reason_display}</td>
                <td className="px-4 py-3 text-gray-500">{a.user_name||'—'}</td>
                <td className="px-4 py-3 text-gray-500">{a.created_at?.split('T')[0]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Alerts ──────────────────────────────────────────────────────────────────
function AlertsPanel() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter]   = useState('active');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = filter==='all' ? {} : { is_resolved: filter==='resolved' };
      const res = await inventoryAPI.getAlerts(params);
      setAlerts(res.data?.results||res.data||[]);
    } catch {/**/ } finally { setLoading(false); }
  }, [filter]);

  useEffect(()=>{ load(); }, [load]);

  const handleResolve = async (id) => {
    await inventoryAPI.resolveAlert(id);
    load();
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {['all','active','resolved'].map(f=>(
          <button key={f} onClick={()=>setFilter(f)}
            className={`px-3 py-1.5 rounded-xl text-sm font-bold ${filter===f?'bg-blue-600 text-white':'bg-white border text-gray-600'}`}>
            {f==='all'?'الكل':f==='active'?'🔴 نشطة':'✅ محلولة'}
          </button>
        ))}
      </div>
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="bg-gray-50 text-gray-500 text-right">
            <th className="px-4 py-3 font-bold">المنتج</th><th className="px-4 py-3 font-bold">الباركود</th>
            <th className="px-4 py-3 font-bold">نوع التنبيه</th><th className="px-4 py-3 font-bold">المخزون</th>
            <th className="px-4 py-3 font-bold">الحد</th><th className="px-4 py-3 font-bold">الحالة</th>
            <th className="px-4 py-3 font-bold">التاريخ</th><th className="px-4 py-3 font-bold">إجراء</th>
          </tr></thead>
          <tbody>
            {alerts.length===0 && <tr><td colSpan={8} className="text-center py-8 text-gray-400">لا توجد تنبيهات</td></tr>}
            {alerts.map(a=>(
              <tr key={a.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 font-bold">{a.product_name}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{a.product_barcode||'—'}</td>
                <td className="px-4 py-3"><Badge label={a.alert_type_display} color={alertColor(a.alert_type)} /></td>
                <td className="px-4 py-3 font-black text-red-600">{a.current_stock}</td>
                <td className="px-4 py-3">{a.threshold}</td>
                <td className="px-4 py-3"><Badge label={a.is_resolved?'محلول':'نشط'} color={a.is_resolved?'green':'red'} /></td>
                <td className="px-4 py-3 text-gray-500">{a.created_at?.split('T')[0]}</td>
                <td className="px-4 py-3">
                  {!a.is_resolved && (
                    <button onClick={()=>handleResolve(a.id)}
                      className="bg-green-100 hover:bg-green-200 text-green-700 text-xs font-bold px-3 py-1 rounded-lg">✅ حل</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Suppliers ───────────────────────────────────────────────────────────────
function SuppliersPanel() {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [showForm, setShowForm]   = useState(false);
  const [editing, setEditing]     = useState(null);
  const [toast, setToast]         = useState(null);
  const notify = (msg,type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await inventoryAPI.getSuppliers(); setSuppliers(r.data?.results||r.data||[]); }
    catch {/**/ } finally { setLoading(false); }
  }, []);

  useEffect(()=>{ load(); }, [load]);

  const handleSave = async (data) => {
    try {
      if (editing) await inventoryAPI.updateSupplier(editing.id, data);
      else await inventoryAPI.createSupplier(data);
      notify('✅ تم الحفظ'); setShowForm(false); setEditing(null); load();
    } catch(e) { notify('❌ '+JSON.stringify(e?.response?.data||'خطأ'),'error'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('حذف المورد؟')) return;
    try { await inventoryAPI.deleteSupplier(id); notify('تم الحذف'); load(); }
    catch { notify('❌ خطأ في الحذف','error'); }
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      {toast && <Toast msg={toast.msg} type={toast.type} />}
      <div className="flex justify-between items-center">
        <h2 className="font-black text-gray-700 text-lg">الموردون</h2>
        <button onClick={()=>{ setEditing(null); setShowForm(true); }}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-4 py-2 rounded-xl text-sm">➕ مورد جديد</button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {suppliers.length===0 && <p className="text-gray-400 col-span-3 text-center py-8">لا يوجد موردون</p>}
        {suppliers.map(s=>(
          <div key={s.id} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-black text-gray-800">{s.name}</div>
                {s.phone && <div className="text-sm text-gray-500 mt-1">📞 {s.phone}</div>}
                {s.email && <div className="text-sm text-gray-500">✉️ {s.email}</div>}
                <div className="text-xs text-blue-600 mt-2 font-bold">{s.orders_count} أوامر شراء</div>
              </div>
              <div className="flex gap-2">
                <button onClick={()=>{ setEditing(s); setShowForm(true); }} className="text-blue-500 hover:text-blue-700 text-sm">✏️</button>
                <button onClick={()=>handleDelete(s.id)} className="text-red-400 hover:text-red-600 text-sm">🗑️</button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {showForm && (
        <SupplierModal initial={editing} onClose={()=>{ setShowForm(false); setEditing(null); }} onSave={handleSave} />
      )}
    </div>
  );
}

function SupplierModal({ initial, onClose, onSave }) {
  const [form, setForm] = useState({ name:'', phone:'', email:'', address:'', notes:'', ...initial });
  const [saving, setSaving] = useState(false);
  const handle = async () => { setSaving(true); await onSave(form); setSaving(false); };
  return (
    <Modal title={initial?'✏️ تعديل المورد':'➕ مورد جديد'} onClose={onClose}>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="الاسم *"><input className={INP} value={form.name} onChange={e=>setForm({...form,name:e.target.value})} /></Field>
          <Field label="الهاتف"><input className={INP} value={form.phone||''} onChange={e=>setForm({...form,phone:e.target.value})} /></Field>
          <Field label="البريد الإلكتروني"><input className={INP} value={form.email||''} onChange={e=>setForm({...form,email:e.target.value})} /></Field>
          <Field label="العنوان"><input className={INP} value={form.address||''} onChange={e=>setForm({...form,address:e.target.value})} /></Field>
        </div>
        <Field label="ملاحظات"><textarea className={INP} rows={2} value={form.notes||''} onChange={e=>setForm({...form,notes:e.target.value})} /></Field>
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded-xl border font-bold text-sm">إلغاء</button>
          <button onClick={handle} disabled={saving} className="bg-blue-600 text-white font-bold px-5 py-2 rounded-xl text-sm">{saving?'...':'💾 حفظ'}</button>
        </div>
      </div>
    </Modal>
  );
}
"""

write(os.path.join(PAGES_DIR, "InventoryPage.jsx"), INVENTORY_PAGE)

# ══════════════════════════════════════════════════════════════════════════════
#  DONE
# ══════════════════════════════════════════════════════════════════════════════
section("✅ اكتمل السكريبت!")
print("""
  الخطوات المتبقية يدوياً:
  ─────────────────────────────────────────────────────
  1. افتح Django Admin → UI Builder → Routes → أضف:
       path:      /inventory
       component: InventoryPage
       label:     إدارة المخزون
       wrapper:   auth

  2. في UI Builder → Sidebar Items → أضف:
       path:  /inventory
       label: إدارة المخزون
       icon:  fas fa-warehouse
       key:   inventory

  3. شغّل الفرونت:
       cd pos_frontend && npm run dev
  ─────────────────────────────────────────────────────
""")
