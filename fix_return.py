#!/usr/bin/env python3
# fix_returns.py
# يصلح 5 مشاكل في موديول المرتجعات:
# 1. superuser RBAC bug في get_queryset
# 2. stats مش بيطبق RBAC scope
# 3. debug prints كتير في views_returns.py
# 4. المرتجع بيتخلق completed فوراً بدون workflow (serializer)
# 5. زرار المرتجع بيظهر للكل بدون صلاحية (OperationDetails.jsx)

import shutil
from pathlib import Path

BASE = Path(__file__).parent

FILES = {
    'views':      BASE / 'pos_backend/sales/views_returns.py',
    'serializer': BASE / 'pos_backend/sales/serializers_returns.py',
    'frontend':   BASE / 'pos_frontend/src/pages/OperationDetails.jsx',
}

def backup(path):
    if path.exists():
        shutil.copy(path, str(path) + '.bak')
        print(f'  [backup] {path.name}.bak')

def write(path, content):
    backup(path)
    path.write_text(content, encoding='utf-8')
    print(f'  [ok]     {path}')

# ═══════════════════════════════════════════════════════
# 1. views_returns.py — الإصلاحات الثلاثة
# ═══════════════════════════════════════════════════════
VIEWS = '''from rest_framework import viewsets, status
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
'''

# ═══════════════════════════════════════════════════════
# 2. serializers_returns.py — إصلاح stock عند completed فقط
# ═══════════════════════════════════════════════════════
SERIALIZER = '''from rest_framework import serializers
from django.db import transaction
from django.db.models import Sum, F
from .models import Sale, SaleItem, Return, ReturnItem
from products.models import Product


class ReturnItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='sale_item.product_name', read_only=True
    )
    sale_item_id = serializers.UUIDField(write_only=True)

    class Meta:
        model  = ReturnItem
        fields = [
            'id', 'sale_item_id', 'product', 'product_name',
            'quantity', 'price', 'subtotal', 'created_at',
        ]
        read_only_fields = ['id', 'subtotal', 'created_at', 'product']


class ReturnSerializer(serializers.ModelSerializer):
    items         = ReturnItemSerializer(many=True)
    sale_id       = serializers.UUIDField(write_only=True)
    user_name     = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model  = Return
        fields = [
            'id', 'sale', 'sale_id', 'user', 'user_name', 'customer_name',
            'total_amount', 'reason', 'status', 'items',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'sale']

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return 'غير محدد'

    def get_customer_name(self, obj):
        if obj.sale and obj.sale.customer:
            return obj.sale.customer.name
        return 'زائر'

    @transaction.atomic
    def create(self, validated_data):
        items_data    = validated_data.pop('items')
        sale_id       = validated_data.pop('sale_id')
        cash_register = validated_data.pop('cash_register', None)
        reason        = validated_data.get('reason', '')

        # ✅ إصلاح: المرتجع يبدأ دايماً بـ pending بغض النظر عما أرسله الفرونت
        # المخزون لا يتغير هنا — يتغير فقط عند complete()
        return_status = 'pending'

        try:
            sale = Sale.objects.get(id=sale_id)
        except Sale.DoesNotExist:
            raise serializers.ValidationError('عملية البيع غير موجودة')

        if sale.status != 'completed':
            raise serializers.ValidationError('لا يمكن إرجاع فاتورة غير مكتملة')

        return_obj = Return.objects.create(
            sale=sale,
            user=self.context['request'].user,
            cash_register=cash_register,
            reason=reason,
            status=return_status,
        )

        total_amount = 0

        for item_data in items_data:
            sale_item_id = item_data.pop('sale_item_id')
            quantity     = item_data.get('quantity')
            item_data.pop('price', None)

            try:
                sale_item = SaleItem.objects.select_for_update().get(
                    id=sale_item_id, sale=sale
                )
            except SaleItem.DoesNotExist:
                raise serializers.ValidationError(
                    f'عنصر الفاتورة غير موجود: {sale_item_id}'
                )

            previous = ReturnItem.objects.filter(
                sale_item=sale_item,
                return_obj__status='completed',
            ).aggregate(total_returned=Sum('quantity'))

            total_returned    = previous['total_returned'] or 0
            remaining         = sale_item.quantity - total_returned

            if quantity <= 0:
                raise serializers.ValidationError('الكمية يجب أن تكون أكبر من صفر')

            if quantity > remaining:
                raise serializers.ValidationError(
                    f"الكمية المرتجعة ({quantity}) أكبر من المتبقي "
                    f"({remaining}) للمنتج '{sale_item.product_name}'"
                )

            return_item = ReturnItem.objects.create(
                return_obj=return_obj,
                sale_item=sale_item,
                product=sale_item.product,
                quantity=quantity,
                price=sale_item.price,
            )
            total_amount += return_item.subtotal

            # ✅ المخزون لا يتغير هنا — يتغير فقط عند complete() في الـ view

        return_obj.total_amount = total_amount
        return_obj.save(update_fields=['total_amount'])
        return return_obj


class ReturnListSerializer(serializers.ModelSerializer):
    user_name     = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    sale_number   = serializers.SerializerMethodField()
    items_count   = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model  = Return
        fields = [
            'id', 'sale', 'sale_number', 'user_name', 'customer_name',
            'total_amount', 'status', 'items_count', 'created_at',
        ]

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return 'غير محدد'

    def get_customer_name(self, obj):
        if obj.sale and obj.sale.customer:
            return obj.sale.customer.name
        return 'زائر'

    def get_sale_number(self, obj):
        return str(obj.sale.id)[:8] if obj.sale else ''
'''

# ═══════════════════════════════════════════════════════
# 3. OperationDetails.jsx — إصلاح زرار المرتجع + workflow
# ═══════════════════════════════════════════════════════
FRONTEND = r"""import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { salesAPI, returnsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const STATUS_LABEL = {
  pending:   { text: 'قيد الانتظار', cls: 'bg-yellow-100 text-yellow-800' },
  approved:  { text: 'موافق عليه',   cls: 'bg-blue-100 text-blue-800'   },
  completed: { text: 'مكتمل',        cls: 'bg-green-100 text-green-800'  },
  rejected:  { text: 'مرفوض',        cls: 'bg-red-100 text-red-800'      },
};

const ReturnBadge = ({ s }) => {
  const cfg = STATUS_LABEL[s] || { text: s, cls: 'bg-gray-100 text-gray-700' };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${cfg.cls}`}>
      {cfg.text}
    </span>
  );
};

const OperationDetails = () => {
  const { id } = useParams();
  const { isAdmin, isManager, hasAction } = useAuth();

  const isAdminVal   = typeof isAdmin   === 'function' ? isAdmin()   : !!isAdmin;
  const isManagerVal = typeof isManager === 'function' ? isManager() : !!isManager;

  const canCancel = isAdminVal || isManagerVal;

  // ✅ إصلاح: زرار المرتجع يظهر فقط لمن عنده صلاحية
  const canRefund = isAdminVal || isManagerVal ||
    hasAction?.('operations.details', 'sales.refund');

  // ✅ إصلاح: الموافقة والإكمال والرفض للمدير والأدمن فقط
  const canManageReturn = isAdminVal || isManagerVal;

  const [sale, setSale]                   = useState(null);
  const [returns, setReturns]             = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState('');
  const [showReturnModal, setShowReturnModal] = useState(false);
  const [returnableItems, setReturnableItems] = useState([]);
  const [returnQty, setReturnQty]         = useState({});
  const [returnReason, setReturnReason]   = useState('');
  const [returnSubmitting, setReturnSubmitting] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [toast, setToast]                 = useState(null);

  const notify = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const fetchDetails = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await salesAPI.getOne(id);
      setSale(res.data);
      const r = await salesAPI.getReturns(id);
      setReturns(r.data || []);
    } catch (e) {
      console.error(e);
      setError('تعذر تحميل تفاصيل العملية');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDetails(); }, [id]);

  const handleCancel = async () => {
    if (!sale?.id) return;
    if (!window.confirm('هل أنت متأكد من إلغاء العملية؟')) return;
    try {
      await salesAPI.cancel(sale.id);
      await fetchDetails();
      notify('تم إلغاء العملية');
    } catch (e) {
      console.error(e);
      notify('تعذر إلغاء العملية', 'error');
    }
  };

  const openReturnModal = async () => {
    if (!sale?.id) return;
    try {
      const res = await salesAPI.getReturnableItems(sale.id);
      const items = res.data || [];
      setReturnableItems(items);
      const init = {};
      items.forEach((it) => (init[it.sale_item_id] = 0));
      setReturnQty(init);
      setReturnReason('');
      setShowReturnModal(true);
    } catch (e) {
      console.error(e);
      notify('تعذر تحميل الأصناف القابلة للإرجاع', 'error');
    }
  };

  const submitReturn = async () => {
    if (!sale?.id) return;
    const items = returnableItems
      .map((it) => ({
        sale_item_id:      it.sale_item_id,
        quantity:          Number(returnQty[it.sale_item_id] || 0),
        remaining_quantity: Number(it.remaining_quantity || 0),
      }))
      .filter((x) => x.quantity > 0);

    if (!items.length) { notify('اختر كمية مرتجعة واحدة على الأقل', 'error'); return; }

    for (const it of items) {
      if (it.quantity > it.remaining_quantity) {
        notify('كمية المرتجع لا يمكن أن تتجاوز الكمية المتبقية', 'error');
        return;
      }
    }

    setReturnSubmitting(true);
    try {
      // ✅ إصلاح: لا نرسل status — الـ backend يحدده دايماً بـ pending
      await returnsAPI.create({
        sale_id: sale.id,
        reason:  returnReason || '',
        items:   items.map(({ sale_item_id, quantity }) => ({ sale_item_id, quantity })),
      });
      setShowReturnModal(false);
      await fetchDetails();
      notify('تم إنشاء طلب المرتجع — في انتظار موافقة المدير');
    } catch (e) {
      console.error(e);
      const msg = e?.response?.data?.[0] || JSON.stringify(e?.response?.data) || 'خطأ غير معروف';
      notify('تعذر إنشاء المرتجع: ' + msg, 'error');
    } finally {
      setReturnSubmitting(false);
    }
  };

  const handleReturnAction = async (returnId, action) => {
    setActionLoading(returnId + action);
    try {
      await returnsAPI[action](returnId);
      await fetchDetails();
      const labels = { approve: 'تمت الموافقة', complete: 'تم إكمال المرتجع وإرجاع المخزون', reject: 'تم الرفض' };
      notify(labels[action] || 'تم');
    } catch (e) {
      const msg = e?.response?.data?.error || 'خطأ في العملية';
      notify(msg, 'error');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) return <div className="p-6 text-gray-700">جاري التحميل...</div>;

  if (error) return (
    <div className="p-6">
      <div className="p-4 rounded-lg bg-red-50 text-red-700 border border-red-200">{error}</div>
      <div className="mt-4">
        <Link to="/operations" className="text-blue-700 hover:text-blue-900 font-semibold">العودة للعمليات</Link>
      </div>
    </div>
  );

  if (!sale) return (
    <div className="p-6">
      <div className="text-gray-700">لا توجد بيانات.</div>
      <div className="mt-4">
        <Link to="/operations" className="text-blue-700 hover:text-blue-900 font-semibold">العودة للعمليات</Link>
      </div>
    </div>
  );

  return (
    <div className="p-6" dir="rtl">

      {/* Toast */}
      {toast && (
        <div className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-2xl shadow-xl font-bold text-sm
          ${toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">تفاصيل العملية</h1>
          <div className="text-sm text-gray-600 font-mono">#{String(sale.id).slice(0, 8)}</div>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <Link to="/operations"
            className="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold">
            رجوع
          </Link>
          {/* ✅ إصلاح: زرار المرتجع يظهر فقط لمن عنده صلاحية */}
          {canRefund && sale.status === 'completed' && (
            <button type="button" onClick={openReturnModal}
              className="px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white font-semibold">
              ↩ إنشاء مرتجع
            </button>
          )}
          {canCancel && sale.status !== 'cancelled' && (
            <button type="button" onClick={handleCancel}
              className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold">
              إلغاء العملية
            </button>
          )}
        </div>
      </div>

      {/* بيانات الفاتورة */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 mb-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-gray-500">العميل</div>
            <div className="text-gray-800 font-bold">{sale.customer_name || 'زائر'}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">التاريخ</div>
            <div className="text-gray-800 font-bold">{new Date(sale.created_at).toLocaleString('ar-SA')}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">طريقة الدفع</div>
            <div className="text-gray-800 font-bold">{sale.payment_method}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">الحالة</div>
            <span className={`px-2 py-1 rounded-full text-xs font-bold ${
              sale.status === 'cancelled' ? 'bg-red-100 text-red-700' :
              sale.status === 'pending'   ? 'bg-yellow-100 text-yellow-800' :
              'bg-green-100 text-green-800'}`}>
              {sale.status === 'cancelled' ? 'ملغاة' :
               sale.status === 'pending'   ? 'قيد الانتظار' : 'مكتملة'}
            </span>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'المجموع الفرعي', val: sale.subtotal, cls: 'bg-gray-50' },
            { label: 'الخصم',          val: sale.discount,  cls: 'bg-gray-50' },
            { label: 'الضريبة',        val: sale.tax,        cls: 'bg-gray-50' },
            { label: 'الإجمالي',       val: sale.total,      cls: 'bg-green-50 border-green-200' },
          ].map((c) => (
            <div key={c.label} className={`p-3 rounded-lg border ${c.cls}`}>
              <div className="text-xs text-gray-500">{c.label}</div>
              <div className="font-bold text-gray-800">{c.val} ر.س</div>
            </div>
          ))}
        </div>

        {/* الأصناف */}
        <div className="mt-6">
          <h2 className="font-bold text-gray-800 mb-2">الأصناف</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-600 border-b">
                  <th className="text-right py-2">المنتج</th>
                  <th className="text-right py-2">الكمية</th>
                  <th className="text-right py-2">السعر</th>
                  <th className="text-right py-2">الإجمالي</th>
                </tr>
              </thead>
              <tbody>
                {sale.items?.map((it, idx) => (
                  <tr key={idx} className="border-b last:border-b-0">
                    <td className="py-2 font-semibold">{it.product_name}</td>
                    <td className="py-2 font-mono">{it.quantity}</td>
                    <td className="py-2 font-mono">{it.price}</td>
                    <td className="py-2 font-bold font-mono">{it.subtotal}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* المرتجعات */}
      {returns.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <h2 className="font-bold text-orange-700 mb-3">↩ المرتجعات ({returns.length})</h2>
          <div className="space-y-3">
            {returns.map((r) => (
              <div key={r.id} className="p-4 rounded-xl bg-orange-50 border border-orange-200">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm font-bold text-orange-800">
                      #{String(r.id).slice(0, 8)}
                    </span>
                    <ReturnBadge s={r.status} />
                  </div>
                  <div className="font-bold text-orange-800">{r.total_amount} ر.س</div>
                </div>
                <div className="text-xs text-orange-600 mt-1">
                  {new Date(r.created_at).toLocaleString('ar-SA')}
                </div>

                {/* ✅ أزرار إدارة المرتجع — للمدير والأدمن فقط */}
                {canManageReturn && (
                  <div className="flex gap-2 mt-3 flex-wrap">
                    {r.status === 'pending' && (
                      <>
                        <button
                          onClick={() => handleReturnAction(r.id, 'approve')}
                          disabled={actionLoading === r.id + 'approve'}
                          className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold">
                          {actionLoading === r.id + 'approve' ? '...' : '✅ موافقة'}
                        </button>
                        <button
                          onClick={() => handleReturnAction(r.id, 'reject')}
                          disabled={actionLoading === r.id + 'reject'}
                          className="px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-700 text-xs font-bold">
                          {actionLoading === r.id + 'reject' ? '...' : '❌ رفض'}
                        </button>
                      </>
                    )}
                    {r.status === 'approved' && (
                      <button
                        onClick={() => handleReturnAction(r.id, 'complete')}
                        disabled={actionLoading === r.id + 'complete'}
                        className="px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-bold">
                        {actionLoading === r.id + 'complete' ? '...' : '📦 إكمال وإرجاع المخزون'}
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal المرتجع */}
      {showReturnModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl">
            <div className="flex items-center justify-between px-5 py-4 border-b">
              <h3 className="font-bold text-lg">↩ إنشاء طلب مرتجع</h3>
              <button onClick={() => setShowReturnModal(false)} className="text-gray-400 hover:text-gray-700 font-black text-xl">×</button>
            </div>
            <div className="p-5">
              <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3 mb-4 text-sm text-yellow-800 font-semibold">
                ⚠️ سيتم إنشاء طلب المرتجع بحالة "قيد الانتظار" — يحتاج موافقة المدير لإرجاع المخزون
              </div>

              <div className="space-y-2 max-h-64 overflow-auto border rounded-xl p-3 mb-4">
                {returnableItems.map((it) => (
                  <div key={it.sale_item_id}
                    className="flex items-center justify-between gap-3 border-b last:border-b-0 py-2">
                    <div>
                      <div className="font-semibold text-sm">{it.product_name}</div>
                      <div className="text-xs text-gray-500">
                        المتبقي للإرجاع: <span className="font-mono font-bold">{it.remaining_quantity}</span>
                      </div>
                    </div>
                    <input
                      type="number" min="0" max={it.remaining_quantity}
                      value={returnQty[it.sale_item_id] ?? 0}
                      onChange={(e) => setReturnQty((p) => ({ ...p, [it.sale_item_id]: e.target.value }))}
                      className="w-24 border rounded-lg px-2 py-1 text-sm font-mono text-center"
                    />
                  </div>
                ))}
                {!returnableItems.length && (
                  <div className="text-sm text-gray-500 text-center py-4">لا توجد أصناف قابلة للإرجاع</div>
                )}
              </div>

              <div className="mb-4">
                <label className="block text-sm font-semibold mb-1">السبب (اختياري)</label>
                <input value={returnReason} onChange={(e) => setReturnReason(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  placeholder="مثال: العميل رجّع الصنف" />
              </div>

              <div className="flex gap-3 justify-end">
                <button onClick={() => setShowReturnModal(false)}
                  className="px-4 py-2 rounded-xl border font-bold text-sm">إغلاق</button>
                <button onClick={submitReturn} disabled={returnSubmitting}
                  className="px-5 py-2 rounded-xl bg-orange-500 hover:bg-orange-600 text-white font-bold text-sm">
                  {returnSubmitting ? 'جاري الحفظ...' : '↩ إرسال طلب المرتجع'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OperationDetails;
"""

# ═══════════════════════════════════════════════════════
# 4. تحديث api.js — إضافة approve/complete/reject
# ═══════════════════════════════════════════════════════
def patch_api_js(base):
    api_file = base / 'pos_frontend/src/services/api.js'
    if not api_file.exists():
        print('  [warn] api.js not found — skip')
        return

    content = api_file.read_text(encoding='utf-8')

    old = "  getStats: () => api.get('/returns/stats/'),"
    new = (
        "  getStats:  () => api.get('/returns/stats/'),\n"
        "  approve:   (id) => api.post(`/returns/${id}/approve/`),\n"
        "  complete:  (id) => api.post(`/returns/${id}/complete/`),\n"
        "  reject:    (id) => api.post(`/returns/${id}/reject/`),\n"
    )

    if 'approve:' in content:
        print('  [skip] api.js already has approve/complete/reject')
        return

    if old in content:
        shutil.copy(api_file, str(api_file) + '.bak')
        content = content.replace(old, new)
        api_file.write_text(content, encoding='utf-8')
        print('  [ok]  api.js patched — approve/complete/reject added')
    else:
        print('  [warn] api.js: insertion point not found — add manually:')
        print('         approve:  (id) => api.post(`/returns/${id}/approve/`),')
        print('         complete: (id) => api.post(`/returns/${id}/complete/`),')
        print('         reject:   (id) => api.post(`/returns/${id}/reject/`),')

# ═══════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════
print('\n=== fix_returns.py ===\n')

for name, path in FILES.items():
    if not path.parent.exists():
        print(f'  [error] directory not found: {path.parent}')
        continue

content_map = {
    'views':      VIEWS,
    'serializer': SERIALIZER,
    'frontend':   FRONTEND,
}

for name, path in FILES.items():
    print(f'--- {name} ---')
    write(path, content_map[name])

print('\n--- api.js ---')
patch_api_js(BASE)

print('\n=== Done ===')
print('''
ملخص التغييرات:
  Backend:
  ✅ superuser يشوف كل المرتجعات بدون فلتر
  ✅ stats يطبق RBAC scope
  ✅ debug prints اتشالت
  ✅ المرتجع يبدأ بـ pending دايماً
  ✅ المخزون يتغير فقط عند complete()
  ✅ endpoints جديدة: approve / complete / reject

  Frontend:
  ✅ زرار المرتجع يظهر لمن عنده صلاحية فقط
  ✅ workflow كامل: pending → approved → completed
  ✅ أزرار الموافقة/الإكمال/الرفض للمدير فقط
  ✅ رسالة توضيحية إن المرتجع يحتاج موافقة

الخطوة التالية:
  cd pos_backend && python3 manage.py runserver
  cd pos_frontend && npm run dev
''')
