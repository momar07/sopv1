from django.db import models
from django.contrib.auth.models import User
import uuid


class Supplier(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=200, verbose_name="اسم المورد")
    phone      = models.CharField(max_length=20, blank=True, null=True, verbose_name="الهاتف")
    email      = models.EmailField(blank=True, null=True, verbose_name="البريد الإلكتروني")
    address    = models.TextField(blank=True, null=True, verbose_name="العنوان")
    notes      = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    is_active  = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True,     verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name        = "مورد"
        verbose_name_plural = "الموردون"
        ordering            = ['name']

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft',     'مسودة'),
        ('ordered',   'تم الطلب'),
        ('received',  'تم الاستلام'),
        ('cancelled', 'ملغي'),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(max_length=50, unique=True, verbose_name="رقم المرجع")
    supplier         = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purchase_orders', verbose_name="المورد"
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='purchase_orders', verbose_name="الموظف المسؤول"
    )
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="الحالة")
    total_cost    = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="إجمالي التكلفة")
    notes         = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    expected_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الاستلام المتوقع")
    received_at   = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الاستلام الفعلي")
    created_at    = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at    = models.DateTimeField(auto_now=True,     verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name        = "أمر شراء"
        verbose_name_plural = "أوامر الشراء"
        ordering            = ['-created_at']

    def __str__(self):
        return f"أمر شراء #{self.reference_number}"

    def recalculate_total(self):
        from django.db.models import Sum, F, DecimalField, ExpressionWrapper
        total = self.items.aggregate(
            total=Sum(ExpressionWrapper(
                F('quantity') * F('unit_cost'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ))
        )['total'] or 0
        self.total_cost = total
        self.save(update_fields=['total_cost'])


class PurchaseOrderItem(models.Model):
    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order             = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items', verbose_name="أمر الشراء")
    product           = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='purchase_items', verbose_name="المنتج")
    quantity          = models.PositiveIntegerField(verbose_name="الكمية المطلوبة")
    received_quantity = models.PositiveIntegerField(default=0, verbose_name="الكمية المستلمة")
    unit_cost         = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="تكلفة الوحدة")

    class Meta:
        verbose_name        = "عنصر أمر شراء"
        verbose_name_plural = "عناصر أوامر الشراء"

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    @property
    def subtotal(self):
        return self.unit_cost * self.quantity

    @property
    def remaining_quantity(self):
        return self.quantity - self.received_quantity


class StockAdjustment(models.Model):
    REASON_CHOICES = [
        ('count',  'جرد دوري'),
        ('damage', 'تلف'),
        ('loss',   'فقد / سرقة'),
        ('return', 'مرتجع من عميل'),
        ('expiry', 'انتهاء صلاحية'),
        ('other',  'أخرى'),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product         = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='stock_adjustments', verbose_name="المنتج")
    user            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='stock_adjustments', verbose_name="الموظف")
    quantity_before = models.IntegerField(verbose_name="الكمية قبل")
    quantity_change = models.IntegerField(verbose_name="التغيير")
    quantity_after  = models.IntegerField(verbose_name="الكمية بعد")
    reason          = models.CharField(max_length=20, choices=REASON_CHOICES, default='count', verbose_name="السبب")
    notes           = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at      = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التسوية")

    class Meta:
        verbose_name        = "تسوية مخزون"
        verbose_name_plural = "تسويات المخزون"
        ordering            = ['-created_at']

    def __str__(self):
        sign = '+' if self.quantity_change >= 0 else ''
        return f"{self.product.name} | {sign}{self.quantity_change} | {self.get_reason_display()}"


class StockAlert(models.Model):
    ALERT_TYPES = [
        ('low',    'مخزون منخفض'),
        ('out',    'نفاد المخزون'),
        ('expiry', 'قرب انتهاء الصلاحية'),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product       = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='stock_alerts', verbose_name="المنتج")
    alert_type    = models.CharField(max_length=20, choices=ALERT_TYPES, verbose_name="نوع التنبيه")
    threshold     = models.IntegerField(default=10, verbose_name="حد التنبيه")
    current_stock = models.IntegerField(verbose_name="المخزون الحالي وقت التنبيه")
    is_resolved   = models.BooleanField(default=False, verbose_name="تم الحل")
    resolved_at   = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحل")
    created_at    = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التنبيه")

    class Meta:
        verbose_name        = "تنبيه مخزون"
        verbose_name_plural = "تنبيهات المخزون"
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.get_alert_type_display()} — {self.product.name} ({self.current_stock})"
