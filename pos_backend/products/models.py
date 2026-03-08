from django.db import models
import uuid


class UnitOfMeasure(models.Model):
    """وحدة القياس — قطعة / دستة / كرتون / كيلو ..."""

    CATEGORY_CHOICES = [
        ('count',  'عدد'),
        ('weight', 'وزن'),
        ('volume', 'حجم'),
        ('length', 'طول'),
        ('other',  'أخرى'),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=50, unique=True, verbose_name='اسم الوحدة')
    symbol      = models.CharField(max_length=10, blank=True, default='', verbose_name='الرمز')
    factor      = models.DecimalField(
        max_digits=10, decimal_places=4, default=1,
        verbose_name='معامل التحويل',
        help_text='كم وحدة أساسية تعادل هذه الوحدة — مثال: كرتون=12'
    )
    category    = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='count')
    is_base     = models.BooleanField(default=False, verbose_name='وحدة أساسية')
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'وحدة قياس'
        verbose_name_plural = 'وحدات القياس'
        ordering            = ['category', 'factor']

    def __str__(self):
        return self.name


class Category(models.Model):
    """فئة المنتجات"""
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=100, verbose_name='اسم الفئة')
    icon       = models.CharField(max_length=50, blank=True, null=True)
    color      = models.CharField(max_length=7, default='#3B82F6')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'فئة'
        verbose_name_plural = 'الفئات'
        ordering            = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """المنتج — المخزون دايماً بالوحدة الأساسية"""

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=200, verbose_name='اسم المنتج')
    category     = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products'
    )
    barcode      = models.CharField(max_length=100, unique=True, blank=True, null=True)
    description  = models.TextField(blank=True, null=True)
    image_url    = models.URLField(blank=True, null=True)
    is_active    = models.BooleanField(default=True)

    # ── الأسعار ──────────────────────────────────────────
    price        = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='سعر البيع (بالوحدة الأساسية)'
    )
    cost         = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='تكلفة الشراء (بالوحدة الأساسية)'
    )

    # ── المخزون ──────────────────────────────────────────
    # دايماً بالوحدة الأساسية — لا يُعدَّل مباشرة من الـ API
    stock        = models.IntegerField(default=0, verbose_name='المخزون (بالوحدة الأساسية)')
    min_stock    = models.IntegerField(default=10, verbose_name='الحد الأدنى للتنبيه')

    # ── وحدات القياس ─────────────────────────────────────
    base_unit    = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT,
        related_name='base_products',
        null=True, blank=True,
        verbose_name='الوحدة الأساسية'
    )
    purchase_unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.SET_NULL,
        related_name='purchase_products',
        null=True, blank=True,
        verbose_name='وحدة الشراء الافتراضية'
    )

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'منتج'
        verbose_name_plural = 'المنتجات'
        ordering            = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def profit_margin(self):
        if self.cost and self.cost > 0:
            return float((self.price - self.cost) / self.cost * 100)
        return 0

    @property
    def is_low_stock(self):
        return self.stock <= self.min_stock


class ProductUnitPrice(models.Model):
    """سعر المنتج لكل وحدة بيع"""

    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='unit_prices'
    )
    unit    = models.ForeignKey(
        UnitOfMeasure, on_delete=models.CASCADE,
        related_name='product_prices'
    )
    price   = models.DecimalField(max_digits=10, decimal_places=2)
    is_auto = models.BooleanField(
        default=True,
        help_text='True = محسوب تلقائياً (base_price × factor) | False = سعر يدوي'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name        = 'سعر الوحدة'
        verbose_name_plural = 'أسعار الوحدات'
        unique_together     = ('product', 'unit')

    def save(self, *args, **kwargs):
        if self.is_auto and self.product and self.unit:
            self.price = self.product.price * self.unit.factor
        super().save(*args, **kwargs)

    def __str__(self):
        return self.product.name + ' / ' + self.unit.name + ' = ' + str(self.price)
