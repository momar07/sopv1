from django.db import models
import uuid
from django.conf import settings


class Supplier(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=200, verbose_name='اسم المورد')
    phone        = models.CharField(max_length=20,  blank=True, default='')
    email        = models.EmailField(blank=True, default='')
    address      = models.TextField(blank=True, default='')
    notes        = models.TextField(blank=True, default='')
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'مورد'
        verbose_name_plural = 'الموردون'
        ordering            = ['name']

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    STATUS = [
        ('draft',     'مسودة'),
        ('ordered',   'تم الطلب'),
        ('received',  'مستلم'),
        ('cancelled', 'ملغي'),
    ]
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(max_length=50, unique=True)
    supplier         = models.ForeignKey(Supplier, null=True, blank=True,
                           on_delete=models.SET_NULL, related_name='orders')
    user             = models.ForeignKey(settings.AUTH_USER_MODEL,
                           null=True, on_delete=models.SET_NULL, related_name='purchase_orders')
    status           = models.CharField(max_length=20, choices=STATUS, default='draft')
    total_cost       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes            = models.TextField(blank=True, default='')
    expected_date    = models.DateField(null=True, blank=True)
    received_at      = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'أمر شراء'
        verbose_name_plural = 'أوامر الشراء'
        ordering            = ['-created_at']

    def __str__(self):
        return self.reference_number

    def recalculate_total(self):
        total = sum(i.subtotal for i in self.items.all())
        self.total_cost = total
        self.save(update_fields=['total_cost'])


class PurchaseOrderItem(models.Model):
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order            = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product          = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity         = models.PositiveIntegerField(default=1)
    received_quantity= models.PositiveIntegerField(default=0)
    unit_cost        = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def subtotal(self):
        return self.unit_cost * self.quantity

    @property
    def remaining_quantity(self):
        return max(0, self.quantity - self.received_quantity)

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


class StockAdjustment(models.Model):
    REASONS = [
        ('count',  'جرد دوري'),
        ('damage', 'تلف'),
        ('loss',   'فقد/سرقة'),
        ('return', 'مرتجع'),
        ('expiry', 'انتهاء صلاحية'),
        ('other',  'أخرى'),
    ]
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product         = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    quantity_before = models.IntegerField(default=0)
    quantity_change = models.IntegerField(default=0)
    quantity_after  = models.IntegerField(default=0)
    reason          = models.CharField(max_length=20, choices=REASONS, default='count')
    notes           = models.TextField(blank=True, default='')
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'تسوية مخزون'
        verbose_name_plural = 'تسويات المخزون'
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.product.name}: {self.quantity_change:+d}"


class StockAlert(models.Model):
    TYPES = [
        ('low',    'مخزون منخفض'),
        ('out',    'نفاد المخزون'),
        ('expiry', 'قرب انتهاء الصلاحية'),
    ]
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product       = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    alert_type    = models.CharField(max_length=20, choices=TYPES, default='low')
    threshold     = models.IntegerField(default=10)
    current_stock = models.IntegerField(default=0)
    is_resolved   = models.BooleanField(default=False)
    resolved_at   = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'تنبيه مخزون'
        verbose_name_plural = 'تنبيهات المخزون'
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.alert_type}"


class StockMovement(models.Model):
    # سجل كل حركة مخزون
    MOVEMENT_TYPES = [
        ('sale',       'بيع'),
        ('purchase',   'شراء'),
        ('adjustment', 'تسوية'),
        ('return',     'مرتجع'),
        ('initial',    'رصيد افتتاحي'),
    ]
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product       = models.ForeignKey('products.Product', on_delete=models.CASCADE,
                       related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity      = models.IntegerField()
    stock_before  = models.IntegerField(default=0)
    stock_after   = models.IntegerField(default=0)
    reference     = models.CharField(max_length=200, blank=True, default='',
                       help_text='رقم الفاتورة او امر الشراء')
    notes         = models.TextField(blank=True, default='')
    user          = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                       on_delete=models.SET_NULL)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'حركة مخزون'
        verbose_name_plural = 'حركات المخزون'
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.product.name} {self.movement_type} {self.quantity:+d}"
