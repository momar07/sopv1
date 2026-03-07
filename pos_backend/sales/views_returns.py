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
