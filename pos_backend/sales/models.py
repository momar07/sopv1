from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import uuid
from .models_cashregister import CashRegister, CashTransaction


class Sale(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'نقدي'),
        ('card', 'بطاقة'),
        ('both', 'نقدي + بطاقة'),
    ]
    STATUS_CHOICES = [
        ('completed', 'مكتملة'),
        ('cancelled', 'ملغاة'),
        ('pending',   'قيد الانتظار'),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer       = models.ForeignKey(
        'customers.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sales'
    )
    user           = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='sales'
    )
    cash_register  = models.ForeignKey(
        'CashRegister', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sales'
    )
    subtotal       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax            = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total          = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    notes          = models.TextField(blank=True, null=True)
    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'عملية بيع'
        verbose_name_plural = 'عمليات البيع'
        ordering            = ['-created_at']

    def __str__(self):
        return 'Sale #' + str(self.id)[:8] + ' - ' + str(self.total)

    @property
    def items_count(self):
        return self.items.count()

    @property
    def total_profit(self):
        profit = 0
        for item in self.items.all():
            if item.product:
                profit += (item.price - item.product.cost) * item.quantity
        return profit


class SaleItem(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale         = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product      = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL,
        null=True, related_name='sale_items'
    )
    product_name = models.CharField(max_length=200)

    # ── الوحدة ───────────────────────────────────────────
    unit          = models.ForeignKey(
        'products.UnitOfMeasure', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='وحدة البيع'
    )
    unit_quantity = models.DecimalField(
        max_digits=10, decimal_places=4, default=1,
        verbose_name='الكمية بوحدة البيع'
    )
    # quantity = الكمية الفعلية بالوحدة الأساسية
    quantity     = models.IntegerField(validators=[MinValueValidator(1)])

    price        = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal     = models.DecimalField(max_digits=10, decimal_places=2)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'عنصر بيع'
        verbose_name_plural = 'عناصر البيع'
        ordering            = ['created_at']

    def __str__(self):
        return self.product_name + ' x' + str(self.quantity)

    def save(self, *args, **kwargs):
        self.subtotal = self.price * self.unit_quantity
        super().save(*args, **kwargs)


class Return(models.Model):
    STATUS_CHOICES = [
        ('pending',   'قيد المراجعة'),
        ('approved',  'مقبول'),
        ('rejected',  'مرفوض'),
        ('completed', 'مكتمل'),
    ]
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale          = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns')
    user          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='processed_returns')
    cash_register = models.ForeignKey('CashRegister', on_delete=models.SET_NULL, null=True, blank=True, related_name='returns')
    total_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reason        = models.TextField(blank=True, null=True)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'مرتجع'
        verbose_name_plural = 'المرتجعات'

    def __str__(self):
        return 'مرتجع #' + str(self.id)[:8] + ' - ' + str(self.total_amount)


class ReturnItem(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_obj = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')
    sale_item  = models.ForeignKey(SaleItem, on_delete=models.CASCADE)
    product    = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True)
    quantity   = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    price      = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal   = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'عنصر مرتجع'
        verbose_name_plural = 'عناصر المرتجعات'

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        name = self.product.name if self.product else self.sale_item.product_name
        return name + ' x' + str(self.quantity)
