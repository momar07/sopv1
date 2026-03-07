from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Return, ReturnItem
from .serializers_returns import ReturnSerializer, ReturnListSerializer


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

        # فلترة حسب الحالة
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        # فلترة حسب التاريخ
        start_date = self.request.query_params.get('start_date')
        end_date   = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        user = self.request.user

        # ✅ إصلاح: superuser يشوف الكل بدون فلتر
        if user.is_superuser:
            return queryset.order_by('-created_at')

        # Manager يشوف مرتجعاته + مرتجعات فريقه
        if user.has_perm('users.sales_view_team'):
            queryset = queryset.filter(
                Q(user=user) | Q(user__profile__manager=user)
            )
        else:
            # Cashier يشوف مرتجعاته بس
            queryset = queryset.filter(user=user)

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        # RBAC — فقط من عنده صلاحية returns_create
        user = self.request.user
        if not (user.is_superuser or user.has_perm('users.returns_create')):
            raise PermissionDenied('ليس لديك صلاحية إنشاء مرتجع')

        from .models_cashregister import CashRegister
        cash_register = None
        if user.is_authenticated:
            cash_register = CashRegister.objects.filter(
                user=user, status='open'
            ).first()

        serializer.save(cash_register=cash_register)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """موافقة على المرتجع — للمدير والأدمن فقط"""
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
        """إكمال المرتجع وإرجاع المخزون — للمدير والأدمن فقط"""
        from django.db import transaction
        from django.db.models import F, Sum
        from products.models import Product

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

        with transaction.atomic():
            for item in ret.items.select_related('product').all():
                if item.product:
                    Product.objects.filter(
                        id=item.product.id
                    ).update(stock=F('stock') + item.quantity)
            ret.status = 'completed'
            ret.save(update_fields=['status'])

        return Response(self.get_serializer(ret).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """رفض المرتجع — للمدير والأدمن فقط"""
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
        """إحصائيات المرتجعات — مع RBAC scope"""
        today     = timezone.now().date()
        week_ago  = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # ✅ إصلاح: استخدم get_queryset عشان يطبق الـ RBAC scope
        base = self.get_queryset()

        def agg(qs):
            return qs.aggregate(
                total=Sum('total_amount'),
                count=Count('id')
            )

        today_stats = agg(base.filter(created_at__date=today,          status='completed'))
        week_stats  = agg(base.filter(created_at__date__gte=week_ago,  status='completed'))
        month_stats = agg(base.filter(created_at__date__gte=month_ago, status='completed'))

        # إحصائيات المرتجعات قيد الانتظار
        pending_stats = agg(base.filter(status='pending'))

        return Response({
            'today': {
                'amount': today_stats['total'] or 0,
                'count':  today_stats['count'] or 0,
            },
            'week': {
                'amount': week_stats['total'] or 0,
                'count':  week_stats['count'] or 0,
            },
            'month': {
                'amount': month_stats['total'] or 0,
                'count':  month_stats['count'] or 0,
            },
            'pending': {
                'amount': pending_stats['total'] or 0,
                'count':  pending_stats['count'] or 0,
            },
        })
