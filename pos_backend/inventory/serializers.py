from rest_framework import serializers
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, StockAdjustment, StockAlert, StockAlertNote, StockMovement
from products.models import Product


class SupplierSerializer(serializers.ModelSerializer):
    orders_count = serializers.SerializerMethodField()

    class Meta:
        model  = Supplier
        fields = ['id','name','phone','email','address','notes','is_active','created_at','orders_count']

    def get_orders_count(self, obj):
        return obj.orders.count()


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name    = serializers.CharField(source='product.name',    read_only=True)
    product_barcode = serializers.CharField(source='product.barcode', read_only=True)
    # ✅ Fix-3: أضفنا unit حتى يُحسب actual_quantity بشكل صحيح
    unit_name          = serializers.CharField(source='unit.name', read_only=True, default=None)
    subtotal           = serializers.ReadOnlyField()
    remaining_quantity = serializers.ReadOnlyField()

    class Meta:
        model  = PurchaseOrderItem
        fields = ['id','product','product_name','product_barcode',
                  'unit','unit_name',
                  'quantity','received_quantity','unit_cost',
                  'subtotal','remaining_quantity']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items         = PurchaseOrderItemSerializer(many=True)
    supplier_name = serializers.CharField(source='supplier.name',   read_only=True)
    user_name     = serializers.CharField(source='user.username',   read_only=True)

    class Meta:
        model  = PurchaseOrder
        fields = ['id','reference_number','supplier','supplier_name',
                  'user','user_name','status','total_cost','notes',
                  'expected_date','received_at','created_at','items']
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
    product_name   = serializers.CharField(source='product.name',       read_only=True)
    user_name      = serializers.CharField(source='user.username',       read_only=True)
    reason_display = serializers.CharField(source='get_reason_display',  read_only=True)

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
            raise serializers.ValidationError(
                f"المخزون سيصبح سالباً ({after}). المخزون الحالي: {before}"
            )

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
            notes         = validated_data.get('notes', ''),
            user          = validated_data.get('user'),
        )

        # ✅ Fix-2: حل StockAlerts عند التعديل اليدوي إذا عادت الكمية طيبة
        ALERT_THRESHOLD = 10
        if after > ALERT_THRESHOLD:
            # حلّ كل alerts غير محلولة للمنتج ده
            StockAlert.objects.filter(product=product, is_resolved=False).update(
                is_resolved = True,
                resolved_at = timezone.now(),
            )
        elif after > 0 and after <= ALERT_THRESHOLD:
            # حلّ alert "نفاد" فقط لو الكمية رجعت، وأنشئ "low" لو مافيش
            StockAlert.objects.filter(
                product=product, alert_type='out', is_resolved=False
            ).update(is_resolved=True, resolved_at=timezone.now())
            if not StockAlert.objects.filter(product=product, alert_type='low', is_resolved=False).exists():
                StockAlert.objects.create(
                    product=product, alert_type='low',
                    threshold=ALERT_THRESHOLD, current_stock=after,
                )

        return adj




class StockAlertNoteSerializer(serializers.ModelSerializer):
    user_name         = serializers.CharField(source='user.username', read_only=True)
    note_type_display = serializers.CharField(source='get_note_type_display', read_only=True)

    class Meta:
        model  = StockAlertNote
        fields = [
            'id', 'alert', 'user', 'user_name',
            'note_type', 'note_type_display', 'text',
            'cost', 'expected_date', 'delay_reason', 'supplier_name',
            'created_at',
        ]
        read_only_fields = ['user', 'created_at']

class StockAlertSerializer(serializers.ModelSerializer):
    product_name          = serializers.CharField(source='product.name',               read_only=True)
    product_barcode       = serializers.CharField(source='product.barcode',             read_only=True)
    product_current_stock = serializers.IntegerField(source='product.stock',            read_only=True)
    alert_type_display    = serializers.CharField(source='get_alert_type_display',      read_only=True)
    priority_display      = serializers.CharField(source='get_priority_display',        read_only=True)
    ticket_status_display = serializers.CharField(source='get_ticket_status_display',   read_only=True)
    assigned_to_name      = serializers.CharField(source='assigned_to.username',        read_only=True)
    linked_po_reference   = serializers.CharField(source='linked_po.reference_number',  read_only=True)
    linked_po_status      = serializers.CharField(source='linked_po.status',            read_only=True)
    notes                 = StockAlertNoteSerializer(many=True, read_only=True)
    notes_count           = serializers.SerializerMethodField()

    class Meta:
        model  = StockAlert
        fields = [
            'id', 'product', 'product_name', 'product_barcode', 'product_current_stock',
            'alert_type', 'alert_type_display',
            'threshold', 'current_stock',
            'priority', 'priority_display',
            'ticket_status', 'ticket_status_display',
            'assigned_to', 'assigned_to_name',
            'deadline',
            'linked_po', 'linked_po_reference', 'linked_po_status',
            'is_resolved', 'resolved_at',
            'notes', 'notes_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['is_resolved', 'resolved_at', 'created_at', 'updated_at']

    def get_notes_count(self, obj):
        return obj.notes.count()

class StockMovementSerializer(serializers.ModelSerializer):
    product_name          = serializers.CharField(source='product.name',              read_only=True)
    product_barcode       = serializers.CharField(source='product.barcode',            read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display',  read_only=True)
    user_name             = serializers.CharField(source='user.username',              read_only=True)

    class Meta:
        model  = StockMovement
        fields = ['id','product','product_name','product_barcode',
                  'movement_type','movement_type_display',
                  'quantity','stock_before','stock_after',
                  'reference','notes','user','user_name','created_at']
        read_only_fields = ['created_at']
