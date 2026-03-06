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
