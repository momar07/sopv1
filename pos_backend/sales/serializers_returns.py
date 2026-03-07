from rest_framework import serializers
from django.db import transaction
from django.db.models import Sum, F
from .models import Sale, SaleItem, Return, ReturnItem
from products.models import Product


class ReturnItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='sale_item.product_name', read_only=True
    )
    sale_item_id = serializers.UUIDField(write_only=True)

    # ✅ price اختياري عند الإنشاء — الـ backend يأخذه من sale_item.price
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False,
        write_only=True,
    )

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
