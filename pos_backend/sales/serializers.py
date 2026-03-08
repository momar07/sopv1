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
    items         = SaleItemSerializer(many=True, required=False)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    user_name     = serializers.SerializerMethodField()
    user_role     = serializers.SerializerMethodField()
    items_count   = serializers.ReadOnlyField()
    total_profit  = serializers.ReadOnlyField()
    has_returns   = serializers.SerializerMethodField()
    returns_count = serializers.SerializerMethodField()

    class Meta:
        model  = Sale
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
        if 'Admins'    in groups: return 'مدير النظام'
        if 'Managers'  in groups: return 'مدير'
        if 'Cashier Plus' in groups: return 'كاشير بلس'
        if 'Cashiers'  in groups: return 'كاشير'
        return groups[0] if groups else None

    def get_has_returns(self, obj):
        return obj.returns.exists()

    def get_returns_count(self, obj):
        return obj.returns.count()

    @transaction.atomic
    def create(self, validated_data):
        from inventory.models import StockMovement, StockAlert

        items_data = validated_data.pop('items', [])
        sale = Sale.objects.create(**validated_data)

        request = self.context.get('request')
        user    = request.user if request and hasattr(request, 'user') else None

        ALERT_THRESHOLD = 10

        for item_data in items_data:
            product_id = item_data.pop('product_id', None) or item_data.get('product')
            if not product_id:
                raise serializers.ValidationError("يجب إرسال product_id أو product لكل عنصر")

            try:
                product = Product.objects.select_for_update().get(id=product_id)
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"المنتج غير موجود: {product_id}")

            qty = int(item_data.get('quantity') or 0)
            if qty <= 0:
                raise serializers.ValidationError(f"كمية غير صحيحة للمنتج: {product.name}")

            stock_before = product.stock

            updated_rows = Product.objects.filter(
                id=product.id, stock__gte=qty
            ).update(stock=F('stock') - qty)

            if not updated_rows:
                product.refresh_from_db()
                raise serializers.ValidationError(
                    f"المخزون غير كافي للمنتج '{product.name}' — "
                    f"المتاح: {product.stock}, المطلوب: {qty}"
                )

            stock_after = stock_before - qty

            StockMovement.objects.create(
                product       = product,
                movement_type = 'sale',
                quantity      = -qty,
                stock_before  = stock_before,
                stock_after   = stock_after,
                reference     = sale.invoice_number or str(sale.id)[:8],
                notes         = f"بيع فاتورة #{sale.invoice_number or str(sale.id)[:8]}",
                user          = user,
            )

            item_data['product_name'] = item_data.get('product_name') or product.name
            SaleItem.objects.create(sale=sale, product=product, **item_data)

            # ✅ StockAlert مرة واحدة فقط — داخل حلقة الأصناف مباشرةً
            if not StockAlert.objects.filter(product=product, is_resolved=False).exists():
                if stock_after == 0:
                    StockAlert.objects.create(
                        product=product, alert_type='out',
                        threshold=ALERT_THRESHOLD, current_stock=0,
                    )
                elif stock_after <= ALERT_THRESHOLD:
                    StockAlert.objects.create(
                        product=product, alert_type='low',
                        threshold=ALERT_THRESHOLD, current_stock=stock_after,
                    )

        # تحديث بيانات العميل
        if sale.customer and sale.status == 'completed':
            sale.customer.total_purchases += sale.total
            sale.customer.points          += int(sale.total)
            sale.customer.save(update_fields=['total_purchases', 'points'])

        return sale


class SaleListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    user_name     = serializers.SerializerMethodField()
    items_count   = serializers.ReadOnlyField()
    has_returns   = serializers.SerializerMethodField()
    returns_count = serializers.SerializerMethodField()

    class Meta:
        model  = Sale
        fields = [
            'id', 'invoice_number', 'customer_name', 'user_name',
            'total', 'payment_method', 'status',
            'items_count', 'has_returns', 'returns_count', 'created_at'
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username if obj.user else 'غير محدد'

    def get_has_returns(self, obj):
        return obj.returns.exists()

    def get_returns_count(self, obj):
        return obj.returns.count()


class SalesStatsSerializer(serializers.Serializer):
    today_sales  = serializers.DecimalField(max_digits=10, decimal_places=2)
    today_count  = serializers.IntegerField()
    week_sales   = serializers.DecimalField(max_digits=10, decimal_places=2)
    month_sales  = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=10, decimal_places=2)
    top_products = serializers.ListField()
    recent_sales = SaleListSerializer(many=True)
