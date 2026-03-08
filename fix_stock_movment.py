#!/usr/bin/env python3
"""
fix_stock_movements.py
======================
يعدّل ملفين فقط:
  1. pos_backend/sales/views.py        — cancel action يسجّل StockMovement
  2. pos_backend/sales/serializers.py  — SaleSerializer.create يسجّل StockMovement
  3. pos_backend/sales/views_returns.py — complete action يسجّل StockMovement + StockAdjustment

بعد التشغيل كل عملية بيع / إلغاء / مرتجع تسجّل في:
  ✅ inventory_stockmovement  (حركة المخزون — audit log كامل)
  ✅ inventory_stockadjustment (تسوية — للمرتجعات والتعديلات)
"""

import os, shutil, sys

BASE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(BASE, 'pos_backend')

FILES = {
    'serializers': os.path.join(BACKEND, 'sales', 'serializers.py'),
    'views_sales': os.path.join(BACKEND, 'sales', 'views.py'),
    'views_returns': os.path.join(BACKEND, 'sales', 'views_returns.py'),
}

# ══════════════════════════════════════════════════════════════════════
# أدوات مساعدة
# ══════════════════════════════════════════════════════════════════════

def backup(path):
    bak = path + '.bak'
    shutil.copy2(path, bak)
    print(f'  [backup] {bak}')

def write(path, content):
    backup(path)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  [ok]     {path}')

def abort(msg):
    print(f'\n[ERROR] {msg}')
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════
# فحص الملفات
# ══════════════════════════════════════════════════════════════════════
for key, path in FILES.items():
    if not os.path.exists(path):
        abort(f'الملف غير موجود: {path}')

# ══════════════════════════════════════════════════════════════════════
# 1. sales/serializers.py — إضافة تسجيل StockMovement عند البيع
# ══════════════════════════════════════════════════════════════════════
SERIALIZERS_CONTENT = '''\
from rest_framework import serializers
from .models import Sale, SaleItem, Return, ReturnItem
from products.models import Product
from customers.models import Customer
from django.db import transaction
from django.db.models import F, Sum


class SaleItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = SaleItem
        fields = [
            'id', 'product', 'product_id', 'product_name',
            'quantity', 'price', 'subtotal', 'created_at'
        ]
        read_only_fields = ['id', 'subtotal', 'created_at']


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, required=False)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    user_name = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    items_count = serializers.ReadOnlyField()
    total_profit = serializers.ReadOnlyField()
    has_returns = serializers.SerializerMethodField()
    returns_count = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            'id', 'invoice_number', 'customer', 'customer_name',
            'user', 'user_name', 'user_role',
            'subtotal', 'discount', 'tax', 'total', 'paid_amount',
            'payment_method', 'status', 'notes',
            'items', 'items_count', 'total_profit',
            'has_returns', 'returns_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return None

    def get_user_role(self, obj):
        if not obj.user:
            return None
        try:
            groups = [g.name for g in obj.user.groups.all()]
        except Exception:
            groups = []
        if 'Admins' in groups:
            return 'مدير النظام'
        if 'Managers' in groups:
            return 'مدير'
        if 'Cashier Plus' in groups:
            return 'كاشير بلس'
        if 'Cashiers' in groups:
            return 'كاشير'
        return groups[0] if groups else None

    def get_has_returns(self, obj):
        return obj.returns.exists()

    def get_returns_count(self, obj):
        return obj.returns.count()

    @transaction.atomic
    def create(self, validated_data):
        from inventory.models import StockMovement

        items_data = validated_data.pop('items', [])
        sale = Sale.objects.create(**validated_data)

        # المستخدم من الـ request context
        user = None
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user

        for item_data in items_data:
            product_id = item_data.pop('product_id', None) or item_data.get('product')
            if not product_id:
                raise serializers.ValidationError(
                    "يجب إرسال product_id أو product لكل عنصر"
                )

            try:
                product = Product.objects.select_for_update().get(id=product_id)
            except Product.DoesNotExist:
                raise serializers.ValidationError(
                    f"المنتج غير موجود: {product_id}"
                )

            qty = int(item_data.get('quantity') or 0)
            if qty <= 0:
                raise serializers.ValidationError(
                    f"كمية غير صحيحة للمنتج: {product.name}"
                )

            stock_before = product.stock

            # ✅ خصم المخزون atomic مع التحقق من الكفاية
            updated_rows = Product.objects.filter(
                id=product.id,
                stock__gte=qty
            ).update(stock=F('stock') - qty)

            if not updated_rows:
                product.refresh_from_db()
                raise serializers.ValidationError(
                    f"المخزون غير كافي للمنتج '{product.name}' — "
                    f"المتاح: {product.stock}, المطلوب: {qty}"
                )

            stock_after = stock_before - qty

            # ✅ تسجيل حركة المخزون (StockMovement)
            StockMovement.objects.create(
                product=product,
                movement_type='sale',
                quantity=-qty,                  # سالب لأنه خصم
                stock_before=stock_before,
                stock_after=stock_after,
                reference=sale.invoice_number or str(sale.id)[:8],
                notes=f"بيع فاتورة #{sale.invoice_number or str(sale.id)[:8]}",
                user=user,
            )

            item_data['product_name'] = item_data.get('product_name') or product.name

            SaleItem.objects.create(
                sale=sale,
                product=product,
                **item_data
            )

        # تحديث بيانات العميل
        if sale.customer and sale.status == 'completed':
            sale.customer.total_purchases += sale.total
            sale.customer.points += int(sale.total)
            sale.customer.save(update_fields=['total_purchases', 'points'])

        return sale


class SaleListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    user_name = serializers.SerializerMethodField()
    items_count = serializers.ReadOnlyField()

    class Meta:
        model = Sale
        fields = [
            'id', 'customer_name', 'user_name', 'total',
            'payment_method', 'status', 'items_count', 'created_at'
        ]

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return 'غير محدد'


class SalesStatsSerializer(serializers.Serializer):
    today_sales = serializers.DecimalField(max_digits=10, decimal_places=2)
    today_count = serializers.IntegerField()
    week_sales = serializers.DecimalField(max_digits=10, decimal_places=2)
    month_sales = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=10, decimal_places=2)
    top_products = serializers.ListField()
    recent_sales = SaleListSerializer(many=True)
'''

# ══════════════════════════════════════════════════════════════════════
# 2. sales/views.py — cancel action يسجّل StockMovement
# ══════════════════════════════════════════════════════════════════════
VIEWS_SALES_CONTENT = '''\
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, F, Avg, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import timedelta
from .models import Sale, SaleItem, Return
from .serializers import (
    SaleSerializer,
    SaleListSerializer,
    SalesStatsSerializer
)
from .serializers_returns import ReturnListSerializer


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related(
        'customer', 'user'
    ).prefetch_related('items').all()
    serializer_class = SaleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method', 'customer']
    search_fields = ['customer__name', 'id']
    ordering_fields = ['created_at', 'total']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        if user.has_perm('users.sales_view_team'):
            return queryset.filter(
                Q(user=user) | Q(user__profile__manager=user)
            )
        if user.has_perm('users.sales_view_own'):
            return queryset.filter(user=user)
        return queryset.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return SaleListSerializer
        return SaleSerializer

    def perform_create(self, serializer):
        from .models_cashregister import CashRegister
        cash_register = None
        if self.request.user.is_authenticated:
            cash_register = CashRegister.objects.filter(
                user=self.request.user,
                status='open'
            ).first()
        serializer.save(
            user=self.request.user if self.request.user.is_authenticated else None,
            cash_register=cash_register
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        base_queryset = self.get_queryset()

        today_sales = base_queryset.filter(
            created_at__date=today, status='completed'
        ).aggregate(total=Sum('total'), count=Count('id'))

        week_sales = base_queryset.filter(
            created_at__date__gte=week_ago, status='completed'
        ).aggregate(total=Sum('total'))

        month_sales = base_queryset.filter(
            created_at__date__gte=month_ago, status='completed'
        ).aggregate(total=Sum('total'))

        total_profit = SaleItem.objects.filter(
            sale__in=base_queryset.filter(status='completed'),
            product__isnull=False
        ).annotate(
            item_profit=ExpressionWrapper(
                (F('price') - F('product__cost')) * F('quantity'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).aggregate(total=Sum('item_profit'))['total'] or 0

        top_products = SaleItem.objects.filter(
            sale__in=base_queryset,
            sale__status='completed',
            sale__created_at__date__gte=month_ago
        ).values('product__name').annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('subtotal')
        ).order_by('-total_quantity')[:5]

        recent_sales = base_queryset.filter(
            status='completed'
        ).order_by('-created_at')[:10]

        data = {
            'today_sales':  today_sales['total'] or 0,
            'today_count':  today_sales['count'] or 0,
            'week_sales':   week_sales['total'] or 0,
            'month_sales':  month_sales['total'] or 0,
            'total_profit': total_profit,
            'top_products': list(top_products),
            'recent_sales': recent_sales,
        }
        serializer = SalesStatsSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_date_range(self, request):
        start_date = request.query_params.get('start_date')
        end_date   = request.query_params.get('end_date')
        if not start_date or not end_date:
            return Response(
                {'error': 'تاريخ البداية والنهاية مطلوبان'},
                status=status.HTTP_400_BAD_REQUEST
            )
        sales = self.get_queryset().filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status='completed'
        )
        serializer = self.get_serializer(sales, many=True)
        stats = sales.aggregate(
            total_sales=Sum('total'),
            total_count=Count('id'),
            avg_sale=Avg('total')
        )
        return Response({
            'sales': serializer.data,
            'stats': {
                'total_sales': stats['total_sales'] or 0,
                'total_count': stats['total_count'] or 0,
                'avg_sale':    stats['avg_sale'] or 0,
            }
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        from django.db import transaction
        from products.models import Product
        from inventory.models import StockMovement

        user = request.user
        if not (user.is_superuser or user.has_perm('users.sales_cancel')):
            return Response(
                {'detail': 'Not authorized'},
                status=status.HTTP_403_FORBIDDEN
            )

        sale = self.get_object()
        if sale.status == 'cancelled':
            return Response(
                {'error': 'عملية البيع ملغاة مسبقاً'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            for item in sale.items.select_related('product').all():
                if item.product:
                    product = Product.objects.select_for_update().get(pk=item.product_id)
                    stock_before = product.stock

                    Product.objects.filter(id=product.id).update(
                        stock=F('stock') + item.quantity
                    )

                    stock_after = stock_before + item.quantity

                    # ✅ تسجيل حركة المخزون عند الإلغاء
                    StockMovement.objects.create(
                        product=product,
                        movement_type='adjustment',
                        quantity=item.quantity,          # موجب لأنه إرجاع
                        stock_before=stock_before,
                        stock_after=stock_after,
                        reference=sale.invoice_number or str(sale.id)[:8],
                        notes=f"إلغاء فاتورة #{sale.invoice_number or str(sale.id)[:8]}",
                        user=user,
                    )

            # تحديث بيانات العميل
            if sale.customer:
                sale.customer.total_purchases -= sale.total
                sale.customer.points = max(0, sale.customer.points - int(sale.total))
                sale.customer.save()

            sale.status = 'cancelled'
            sale.save()

        serializer = self.get_serializer(sale)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def returns(self, request, pk=None):
        user = request.user
        if not (user.is_superuser or user.has_perm('users.returns_create')):
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        sale = self.get_object()
        returns = Return.objects.filter(sale=sale).prefetch_related('items')
        serializer = ReturnListSerializer(returns, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def returnable_items(self, request, pk=None):
        from django.db.models import Sum
        from .models import ReturnItem

        user = request.user
        if not (user.is_superuser or user.has_perm('users.returns_create')):
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        sale = self.get_object()
        items_data = []

        for sale_item in sale.items.all():
            previous_returns = ReturnItem.objects.filter(
                sale_item=sale_item,
                return_obj__status='completed'
            ).aggregate(total_returned=Sum('quantity'))

            total_returned    = previous_returns['total_returned'] or 0
            remaining_quantity = sale_item.quantity - total_returned

            items_data.append({
                'sale_item_id':       str(sale_item.id),
                'product_name':       sale_item.product_name,
                'original_quantity':  sale_item.quantity,
                'returned_quantity':  total_returned,
                'remaining_quantity': remaining_quantity,
                'price':              str(sale_item.price),
            })

        return Response(items_data)
'''

# ══════════════════════════════════════════════════════════════════════
# 3. sales/views_returns.py — complete يسجّل StockMovement + StockAdjustment
# ══════════════════════════════════════════════════════════════════════
VIEWS_RETURNS_CONTENT = '''\
import logging
from django.db import transaction
from django.db.models import F, Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Return, ReturnItem
from .models_cashregister import CashRegister, CashTransaction
from .serializers_returns import ReturnSerializer, ReturnListSerializer

logger = logging.getLogger(__name__)


class ReturnViewSet(viewsets.ModelViewSet):
    queryset = Return.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return ReturnListSerializer
        return ReturnSerializer

    def get_queryset(self):
        queryset = Return.objects.select_related(
            'sale', 'user'
        ).prefetch_related('items')

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        start_date = self.request.query_params.get('start_date')
        end_date   = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        user = self.request.user
        if user.is_superuser:
            return queryset.order_by('-created_at')
        if user.has_perm('users.sales_view_team'):
            queryset = queryset.filter(
                Q(user=user) | Q(user__profile__manager=user)
            )
        else:
            queryset = queryset.filter(user=user)
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_superuser or user.has_perm('users.returns_create')):
            raise PermissionDenied('ليس لديك صلاحية إنشاء مرتجع')
        cash_register = CashRegister.objects.filter(
            user=user, status='open'
        ).first()
        serializer.save(cash_register=cash_register)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        user = request.user
        if not (user.is_superuser or user.has_perm('users.sales_view_team')):
            return Response(
                {'error': 'ليس لديك صلاحية الموافقة على المرتجع'},
                status=status.HTTP_403_FORBIDDEN
            )
        ret = self.get_object()
        if ret.status != 'pending':
            return Response(
                {'error': f'لا يمكن الموافقة على مرتجع بحالة: {ret.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        ret.status = 'approved'
        ret.save(update_fields=['status'])
        return Response(self.get_serializer(ret).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        إكمال المرتجع بشكل ذري — يشمل:
          1. زيادة مخزون كل منتج مُرجَع
          2. تسجيل StockMovement  (حركة المخزون — audit log)
          3. تسجيل StockAdjustment (تسوية مخزون — سبب: مرتجع)
          4. تسجيل CashTransaction  (حركة الخزنة — نوع: return)
          5. تحديث CashRegister.total_returns و total_cash_returns
        """
        from products.models import Product
        from inventory.models import StockMovement, StockAdjustment

        user = request.user
        if not (user.is_superuser or user.has_perm('users.sales_view_team')):
            return Response(
                {'error': 'ليس لديك صلاحية إكمال المرتجع'},
                status=status.HTTP_403_FORBIDDEN
            )

        ret = self.get_object()
        if ret.status not in ('pending', 'approved'):
            return Response(
                {'error': f'لا يمكن إكمال مرتجع بحالة: {ret.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoice_ref = (
            ret.sale.invoice_number if ret.sale else str(ret.pk)[:8]
        )

        try:
            with transaction.atomic():

                # ── 1 + 2 + 3. المخزون ─────────────────────────────────
                return_items = ret.items.select_related('product').all()

                for item in return_items:
                    if not item.product:
                        continue

                    product = Product.objects.select_for_update().get(
                        pk=item.product_id
                    )
                    stock_before = product.stock

                    Product.objects.filter(pk=product.pk).update(
                        stock=F('stock') + item.quantity
                    )

                    stock_after = stock_before + item.quantity

                    # ✅ حركة مخزون (audit log كامل)
                    StockMovement.objects.create(
                        product=product,
                        movement_type='return',
                        quantity=item.quantity,          # موجب لأنه إضافة
                        stock_before=stock_before,
                        stock_after=stock_after,
                        reference=invoice_ref,
                        notes=f"مرتجع فاتورة #{invoice_ref}",
                        user=user,
                    )

                    # ✅ تسوية مخزون (مع السبب)
                    StockAdjustment.objects.create(
                        product=product,
                        user=user,
                        quantity_before=stock_before,
                        quantity_change=item.quantity,
                        quantity_after=stock_after,
                        reason='return',
                        notes=f"مرتجع فاتورة #{invoice_ref}",
                    )

                # ── 4 + 5. الخزنة ──────────────────────────────────────
                cash_register = ret.cash_register

                if cash_register and cash_register.status == 'open':
                    is_cash = (
                        ret.sale.payment_method in ('cash', 'both')
                        if ret.sale else True
                    )

                    CashTransaction.objects.create(
                        cash_register=cash_register,
                        transaction_type='return',
                        amount=ret.total_amount,
                        reason=f"مرتجع فاتورة #{invoice_ref}",
                        note=ret.reason or '',
                        created_by=user,
                    )

                    register_update = {
                        'total_returns': F('total_returns') + ret.total_amount
                    }
                    if is_cash:
                        register_update['total_cash_returns'] = (
                            F('total_cash_returns') + ret.total_amount
                        )
                    CashRegister.objects.filter(pk=cash_register.pk).update(
                        **register_update
                    )
                else:
                    logger.warning(
                        'complete_return: لا توجد خزنة مفتوحة للمرتجع %s', ret.pk
                    )

                # ── 6. تغيير حالة المرتجع ─────────────────────────────
                ret.status = 'completed'
                ret.save(update_fields=['status'])

        except Exception as exc:
            logger.exception('complete_return failed: %s', exc)
            return Response(
                {'error': 'حدث خطأ أثناء إكمال المرتجع، يرجى المحاولة مرة أخرى.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(self.get_serializer(ret).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        user = request.user
        if not (user.is_superuser or user.has_perm('users.sales_view_team')):
            return Response(
                {'error': 'ليس لديك صلاحية رفض المرتجع'},
                status=status.HTTP_403_FORBIDDEN
            )
        ret = self.get_object()
        if ret.status not in ('pending', 'approved'):
            return Response(
                {'error': f'لا يمكن رفض مرتجع بحالة: {ret.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        ret.status = 'rejected'
        ret.save(update_fields=['status'])
        return Response(self.get_serializer(ret).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        today     = timezone.now().date()
        week_ago  = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        base = self.get_queryset()

        def agg(qs):
            return qs.aggregate(total=Sum('total_amount'), count=Count('id'))

        today_stats   = agg(base.filter(created_at__date=today,          status='completed'))
        week_stats    = agg(base.filter(created_at__date__gte=week_ago,  status='completed'))
        month_stats   = agg(base.filter(created_at__date__gte=month_ago, status='completed'))
        pending_stats = agg(base.filter(status='pending'))

        return Response({
            'today':   {'amount': today_stats['total']   or 0, 'count': today_stats['count']   or 0},
            'week':    {'amount': week_stats['total']    or 0, 'count': week_stats['count']    or 0},
            'month':   {'amount': month_stats['total']   or 0, 'count': month_stats['count']   or 0},
            'pending': {'amount': pending_stats['total'] or 0, 'count': pending_stats['count'] or 0},
        })
'''

# ══════════════════════════════════════════════════════════════════════
# تنفيذ الكتابة
# ══════════════════════════════════════════════════════════════════════
print('\n=== fix_stock_movements.py ===\n')

write(FILES['serializers'],   SERIALIZERS_CONTENT)
write(FILES['views_sales'],   VIEWS_SALES_CONTENT)
write(FILES['views_returns'], VIEWS_RETURNS_CONTENT)

print('\n✅ تم التعديل بنجاح!')
print('\nالخطوة التالية — أعد تشغيل الخادم:')
print('  cd pos_backend && python3 manage.py runserver')
print('\nمش محتاج migration — مفيش تعديل في الـ models.\n')
