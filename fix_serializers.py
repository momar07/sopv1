# fix_serializers.py
"""
يُصلح ثلاثة أخطاء في الـ serializers:
  1. يزيل تكرار StockAlert في sales/serializers.py
  2. يُضيف حل StockAlert عند التعديل اليدوي في inventory/serializers.py
  3. يُضيف حقل unit في PurchaseOrderItemSerializer
"""

import os, shutil, datetime

BASE    = "/home/momar/Projects/POS_DEV/posv1_dev10"
SALES_S = os.path.join(BASE, "pos_backend/sales/serializers.py")
INV_S   = os.path.join(BASE, "pos_backend/inventory/serializers.py")
CHLOG   = os.path.join(BASE, "CHANGELOG.md")
README  = os.path.join(BASE, "FIXES_README.md")

# ── helpers ──────────────────────────────────────────────────────────────────
def backup(path):
    bak = path + ".bak"
    if os.path.exists(path):
        shutil.copy2(path, bak)
        print(f"  ✅ Backup: {bak}")

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ Written: {path}")

def update_changelog(entry):
    ts   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"\n## [{ts}] fix_serializers\n{entry}\n"
    with open(CHLOG, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"  ✅ CHANGELOG updated")

# ── File 1: sales/serializers.py ─────────────────────────────────────────────
SALES_CONTENT = '''from rest_framework import serializers
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
            \'id\', \'product\', \'product_id\', \'product_name\',
            \'quantity\', \'price\', \'subtotal\', \'created_at\'
        ]
        read_only_fields = [\'id\', \'subtotal\', \'created_at\']


class SaleSerializer(serializers.ModelSerializer):
    items         = SaleItemSerializer(many=True, required=False)
    customer_name = serializers.CharField(source=\'customer.name\', read_only=True)
    user_name     = serializers.SerializerMethodField()
    user_role     = serializers.SerializerMethodField()
    items_count   = serializers.ReadOnlyField()
    total_profit  = serializers.ReadOnlyField()
    has_returns   = serializers.SerializerMethodField()
    returns_count = serializers.SerializerMethodField()

    class Meta:
        model  = Sale
        fields = [
            \'id\', \'invoice_number\', \'customer\', \'customer_name\',
            \'user\', \'user_name\', \'user_role\',
            \'subtotal\', \'discount\', \'tax\', \'total\', \'paid_amount\',
            \'payment_method\', \'status\', \'notes\',
            \'items\', \'items_count\', \'total_profit\',
            \'has_returns\', \'returns_count\',
            \'created_at\', \'updated_at\'
        ]
        read_only_fields = [\'id\', \'created_at\', \'updated_at\', \'user\']

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
        if \'Admins\'    in groups: return \'مدير النظام\'
        if \'Managers\'  in groups: return \'مدير\'
        if \'Cashier Plus\' in groups: return \'كاشير بلس\'
        if \'Cashiers\'  in groups: return \'كاشير\'
        return groups[0] if groups else None

    def get_has_returns(self, obj):
        return obj.returns.exists()

    def get_returns_count(self, obj):
        return obj.returns.count()

    @transaction.atomic
    def create(self, validated_data):
        from inventory.models import StockMovement, StockAlert

        items_data = validated_data.pop(\'items\', [])
        sale = Sale.objects.create(**validated_data)

        request = self.context.get(\'request\')
        user    = request.user if request and hasattr(request, \'user\') else None

        ALERT_THRESHOLD = 10

        for item_data in items_data:
            product_id = item_data.pop(\'product_id\', None) or item_data.get(\'product\')
            if not product_id:
                raise serializers.ValidationError("يجب إرسال product_id أو product لكل عنصر")

            try:
                product = Product.objects.select_for_update().get(id=product_id)
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"المنتج غير موجود: {product_id}")

            qty = int(item_data.get(\'quantity\') or 0)
            if qty <= 0:
                raise serializers.ValidationError(f"كمية غير صحيحة للمنتج: {product.name}")

            stock_before = product.stock

            updated_rows = Product.objects.filter(
                id=product.id, stock__gte=qty
            ).update(stock=F(\'stock\') - qty)

            if not updated_rows:
                product.refresh_from_db()
                raise serializers.ValidationError(
                    f"المخزون غير كافي للمنتج \'{product.name}\' — "
                    f"المتاح: {product.stock}, المطلوب: {qty}"
                )

            stock_after = stock_before - qty

            StockMovement.objects.create(
                product       = product,
                movement_type = \'sale\',
                quantity      = -qty,
                stock_before  = stock_before,
                stock_after   = stock_after,
                reference     = sale.invoice_number or str(sale.id)[:8],
                notes         = f"بيع فاتورة #{sale.invoice_number or str(sale.id)[:8]}",
                user          = user,
            )

            item_data[\'product_name\'] = item_data.get(\'product_name\') or product.name
            SaleItem.objects.create(sale=sale, product=product, **item_data)

            # ✅ StockAlert مرة واحدة فقط — داخل حلقة الأصناف مباشرةً
            if not StockAlert.objects.filter(product=product, is_resolved=False).exists():
                if stock_after == 0:
                    StockAlert.objects.create(
                        product=product, alert_type=\'out\',
                        threshold=ALERT_THRESHOLD, current_stock=0,
                    )
                elif stock_after <= ALERT_THRESHOLD:
                    StockAlert.objects.create(
                        product=product, alert_type=\'low\',
                        threshold=ALERT_THRESHOLD, current_stock=stock_after,
                    )

        # تحديث بيانات العميل
        if sale.customer and sale.status == \'completed\':
            sale.customer.total_purchases += sale.total
            sale.customer.points          += int(sale.total)
            sale.customer.save(update_fields=[\'total_purchases\', \'points\'])

        return sale


class SaleListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source=\'customer.name\', read_only=True)
    user_name     = serializers.SerializerMethodField()
    items_count   = serializers.ReadOnlyField()
    has_returns   = serializers.SerializerMethodField()
    returns_count = serializers.SerializerMethodField()

    class Meta:
        model  = Sale
        fields = [
            \'id\', \'invoice_number\', \'customer_name\', \'user_name\',
            \'total\', \'payment_method\', \'status\',
            \'items_count\', \'has_returns\', \'returns_count\', \'created_at\'
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username if obj.user else \'غير محدد\'

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
'''

# ── File 2: inventory/serializers.py ─────────────────────────────────────────
INV_CONTENT = '''from rest_framework import serializers
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, StockAdjustment, StockAlert, StockMovement
from products.models import Product


class SupplierSerializer(serializers.ModelSerializer):
    orders_count = serializers.SerializerMethodField()

    class Meta:
        model  = Supplier
        fields = [\'id\',\'name\',\'phone\',\'email\',\'address\',\'notes\',\'is_active\',\'created_at\',\'orders_count\']

    def get_orders_count(self, obj):
        return obj.orders.count()


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name    = serializers.CharField(source=\'product.name\',    read_only=True)
    product_barcode = serializers.CharField(source=\'product.barcode\', read_only=True)
    # ✅ Fix-3: أضفنا unit حتى يُحسب actual_quantity بشكل صحيح
    unit_name          = serializers.CharField(source=\'unit.name\', read_only=True, default=None)
    subtotal           = serializers.ReadOnlyField()
    remaining_quantity = serializers.ReadOnlyField()

    class Meta:
        model  = PurchaseOrderItem
        fields = [\'id\',\'product\',\'product_name\',\'product_barcode\',
                  \'unit\',\'unit_name\',
                  \'quantity\',\'received_quantity\',\'unit_cost\',
                  \'subtotal\',\'remaining_quantity\']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items         = PurchaseOrderItemSerializer(many=True)
    supplier_name = serializers.CharField(source=\'supplier.name\',   read_only=True)
    user_name     = serializers.CharField(source=\'user.username\',   read_only=True)

    class Meta:
        model  = PurchaseOrder
        fields = [\'id\',\'reference_number\',\'supplier\',\'supplier_name\',
                  \'user\',\'user_name\',\'status\',\'total_cost\',\'notes\',
                  \'expected_date\',\'received_at\',\'created_at\',\'items\']
        read_only_fields = [\'user\',\'total_cost\',\'received_at\',\'created_at\']

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop(\'items\', [])
        order = PurchaseOrder.objects.create(**validated_data)
        for item_data in items_data:
            PurchaseOrderItem.objects.create(order=order, **item_data)
        order.recalculate_total()
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop(\'items\', None)
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
    product_name   = serializers.CharField(source=\'product.name\',       read_only=True)
    user_name      = serializers.CharField(source=\'user.username\',       read_only=True)
    reason_display = serializers.CharField(source=\'get_reason_display\',  read_only=True)

    class Meta:
        model  = StockAdjustment
        fields = [\'id\',\'product\',\'product_name\',\'user\',\'user_name\',
                  \'quantity_before\',\'quantity_change\',\'quantity_after\',
                  \'reason\',\'reason_display\',\'notes\',\'created_at\']
        read_only_fields = [\'user\',\'quantity_before\',\'quantity_after\',\'created_at\']

    @transaction.atomic
    def create(self, validated_data):
        product = validated_data[\'product\']
        change  = validated_data[\'quantity_change\']
        before  = product.stock
        after   = before + change

        if after < 0:
            raise serializers.ValidationError(
                f"المخزون سيصبح سالباً ({after}). المخزون الحالي: {before}"
            )

        validated_data[\'quantity_before\'] = before
        validated_data[\'quantity_after\']  = after
        Product.objects.filter(id=product.id).update(stock=F(\'stock\') + change)

        adj = StockAdjustment.objects.create(**validated_data)

        StockMovement.objects.create(
            product       = product,
            movement_type = \'adjustment\',
            quantity      = change,
            stock_before  = before,
            stock_after   = after,
            notes         = validated_data.get(\'notes\', \'\'),
            user          = validated_data.get(\'user\'),
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
                product=product, alert_type=\'out\', is_resolved=False
            ).update(is_resolved=True, resolved_at=timezone.now())
            if not StockAlert.objects.filter(product=product, alert_type=\'low\', is_resolved=False).exists():
                StockAlert.objects.create(
                    product=product, alert_type=\'low\',
                    threshold=ALERT_THRESHOLD, current_stock=after,
                )

        return adj


class StockAlertSerializer(serializers.ModelSerializer):
    product_name       = serializers.CharField(source=\'product.name\',           read_only=True)
    product_barcode    = serializers.CharField(source=\'product.barcode\',         read_only=True)
    alert_type_display = serializers.CharField(source=\'get_alert_type_display\',  read_only=True)

    class Meta:
        model  = StockAlert
        fields = [\'id\',\'product\',\'product_name\',\'product_barcode\',
                  \'alert_type\',\'alert_type_display\',\'threshold\',\'current_stock\',
                  \'is_resolved\',\'resolved_at\',\'created_at\']


class StockMovementSerializer(serializers.ModelSerializer):
    product_name          = serializers.CharField(source=\'product.name\',              read_only=True)
    product_barcode       = serializers.CharField(source=\'product.barcode\',            read_only=True)
    movement_type_display = serializers.CharField(source=\'get_movement_type_display\',  read_only=True)
    user_name             = serializers.CharField(source=\'user.username\',              read_only=True)

    class Meta:
        model  = StockMovement
        fields = [\'id\',\'product\',\'product_name\',\'product_barcode\',
                  \'movement_type\',\'movement_type_display\',
                  \'quantity\',\'stock_before\',\'stock_after\',
                  \'reference\',\'notes\',\'user\',\'user_name\',\'created_at\']
        read_only_fields = [\'created_at\']
'''

# ── Main ──────────────────────────────────────────────────────────────────────
print("=" * 60)
print("  fix_serializers.py — إصلاح 3 أخطاء في الـ serializers")
print("=" * 60)

backup(SALES_S)
backup(INV_S)

write_file(SALES_S, SALES_CONTENT)
write_file(INV_S,   INV_CONTENT)

update_changelog(
    "- Fix-1: أزلنا تكرار StockAlert (3 → 1 loop) في sales/serializers.py\n"
    "- Fix-2: StockAdjustmentSerializer يحل/يُنشئ StockAlert بعد تعديل المخزون\n"
    "- Fix-3: PurchaseOrderItemSerializer أضاف حقل unit و unit_name"
)

readme = """# FIXES_README — fix_serializers

## المشاكل التي تم إصلاحها

### Bug 1 — تكرار StockAlert (sales/serializers.py)
كان كود إنشاء StockAlert مكرراً 3 مرات.
الإصلاح: نقل الكود داخل حلقة الأصناف مباشرةً ومرة واحدة فقط،
مع استخدام stock_after المحسوبة مباشرةً بدل refresh_from_db.

### Bug 2 — StockAdjustment لا يحل Alerts (inventory/serializers.py)
عند تعديل المخزون يدوياً، الـ alerts القديمة كانت تبقى.
الإصلاح: بعد الحفظ، إذا after > threshold → نحل كل alerts.
          إذا 0 < after <= threshold → نحل 'out' ونُنشئ 'low' إن لم يوجد.

### Bug 3 — unit مفقود من PurchaseOrderItemSerializer
الحقل unit (ForeignKey لـ UnitOfMeasure) لم يكن موجوداً في fields.
الإصلاح: أضفنا 'unit' و 'unit_name' للـ serializer.

## الملفات المعدّلة
- pos_backend/sales/serializers.py
- pos_backend/inventory/serializers.py
"""
write_file(README, readme)

print()
print("✅ تم بنجاح! الخطوات التالية:")
print("   cd /home/momar/Projects/POS_DEV/posv1_dev10/pos_backend")
print("   python manage.py check")
print("   # إعادة تشغيل الـ backend")
