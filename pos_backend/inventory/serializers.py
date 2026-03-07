from rest_framework import serializers
from django.db import transaction
from django.db.models import F
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, StockAdjustment, StockAlert, StockMovement
from products.models import Product


class SupplierSerializer(serializers.ModelSerializer):
    orders_count = serializers.SerializerMethodField()

    class Meta:
        model  = Supplier
        fields = ['id','name','phone','email','address','notes','is_active','created_at','orders_count']

    def get_orders_count(self, obj):
        return obj.orders.count()


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name       = serializers.CharField(source='product.name', read_only=True)
    product_barcode    = serializers.CharField(source='product.barcode', read_only=True)
    subtotal           = serializers.ReadOnlyField()
    remaining_quantity = serializers.ReadOnlyField()

    class Meta:
        model  = PurchaseOrderItem
        fields = ['id','product','product_name','product_barcode',
                  'quantity','received_quantity','unit_cost','subtotal','remaining_quantity']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items         = PurchaseOrderItemSerializer(many=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    user_name     = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model  = PurchaseOrder
        fields = ['id','reference_number','supplier','supplier_name','user','user_name',
                  'status','total_cost','notes','expected_date','received_at','created_at','items']
        read_only_fields = ['user','total_cost','received_at','created_at']

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = PurchaseOrder.objects.create(**validated_data)
        for item_data in items_data:
            PurchaseOrderItem.objects.create(order=order, **item_data)
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
            for item_data in items_data:
                PurchaseOrderItem.objects.create(order=instance, **item_data)
        instance.recalculate_total()
        return instance


class StockAdjustmentSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    user_name    = serializers.CharField(source='user.username', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)

    class Meta:
        model  = StockAdjustment
        fields = ['id','product','product_name','user','user_name',
                  'quantity_before','quantity_change','quantity_after',
                  'reason','reason_display','notes','created_at']
        read_only_fields = ['user','quantity_before','quantity_after','created_at']

    @transaction.atomic
    def create(self, validated_data):
        product = validated_data['product']
        change  = validated_data['quantity_change']
        before  = product.stock
        after   = before + change
        if after < 0:
            raise serializers.ValidationError(f"المخزون سيصبح سالباً ({after}). المخزون الحالي: {before}")
        validated_data['quantity_before'] = before
        validated_data['quantity_after']  = after
        Product.objects.filter(id=product.id).update(stock=F('stock') + change)
        adj = StockAdjustment.objects.create(**validated_data)
        StockMovement.objects.create(
            product       = product,
            movement_type = 'adjustment',
            quantity      = change,
            stock_before  = before,
            stock_after   = after,
            notes         = validated_data.get('notes',''),
            user          = validated_data.get('user'),
        )
        return adj


class StockAlertSerializer(serializers.ModelSerializer):
    product_name     = serializers.CharField(source='product.name', read_only=True)
    product_barcode  = serializers.CharField(source='product.barcode', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)

    class Meta:
        model  = StockAlert
        fields = ['id','product','product_name','product_barcode',
                  'alert_type','alert_type_display','threshold','current_stock',
                  'is_resolved','resolved_at','created_at']


class StockMovementSerializer(serializers.ModelSerializer):
    product_name        = serializers.CharField(source='product.name', read_only=True)
    product_barcode     = serializers.CharField(source='product.barcode', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    user_name           = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model  = StockMovement
        fields = ['id','product','product_name','product_barcode',
                  'movement_type','movement_type_display',
                  'quantity','stock_before','stock_after',
                  'reference','notes','user','user_name','created_at']
        read_only_fields = ['created_at']
