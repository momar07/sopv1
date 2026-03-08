#!/usr/bin/env python3
# =============================================================
# rebuild_with_uom.py
# إعادة بناء النظام مع نظام وحدات القياس (UoM) المرن
# الخطوات:
#   1. حذف الـ migrations القديمة + reset الـ DB
#   2. كتابة الموديلات الجديدة
#   3. كتابة الـ serializers الجديدة
#   4. كتابة الـ views الجديدة
#   5. كتابة الـ urls الجديدة
#   6. كتابة سكريبت تشغيل المايجريشن
# =============================================================

import os
import re
import shutil
from datetime import datetime

# ── المسارات ──────────────────────────────────────────────────
BASE          = "/home/momar/Projects/POS_DEV/posv1_dev10"
BACKEND       = os.path.join(BASE, "pos_backend")
CHANGELOG     = os.path.join(BASE, "CHANGELOG.md")
README        = os.path.join(BASE, "FIXES_README.md")

PRODUCTS_DIR  = os.path.join(BACKEND, "products")
INVENTORY_DIR = os.path.join(BACKEND, "inventory")
SALES_DIR     = os.path.join(BACKEND, "sales")
# ─────────────────────────────────────────────────────────────

CHANGE_MSG = "إعادة بناء النظام مع UoM المرن + منع تعديل stock مباشرة"


# ── Helpers ───────────────────────────────────────────────────
def abort(msg):
    print("\n❌  " + msg)
    raise SystemExit(1)


def backup(path):
    if os.path.isfile(path):
        bak = path + ".bak"
        shutil.copy2(path, bak)
        print("   💾  backup → " + bak)


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(content)
    print("   ✅  كُتب  → " + path)


def delete_migrations(app_dir):
    mig_dir = os.path.join(app_dir, "migrations")
    if not os.path.isdir(mig_dir):
        print("   ⚠️   مفيش migrations folder في " + app_dir)
        return
    for f in os.listdir(mig_dir):
        if f != "__init__.py" and f.endswith(".py"):
            os.remove(os.path.join(mig_dir, f))
            print("   🗑️   حذف migration: " + f)


def update_changelog(msg):
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = "\n## [" + now + "] " + msg + "\n"
    try:
        txt = open(CHANGELOG, encoding="utf-8").read()
        new = re.sub(r"(---\s*\n)", r"\1" + entry, txt, count=1)
        open(CHANGELOG, "w", encoding="utf-8").write(new)
        print("   📝  CHANGELOG updated")
    except Exception as e:
        print("   ⚠️   CHANGELOG skipped: " + str(e))


# ── README ────────────────────────────────────────────────────
def write_readme():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Rebuild: UoM System (Unit of Measure)",
        "",
        "## Date",
        now,
        "",
        "## ما الذي تغير؟",
        "",
        "### 1. UnitOfMeasure (موديل جديد في products)",
        "كل وحدة قياس عندها name + factor + category + is_base.",
        "مثال: قطعة(1), دستة(6), كرتون(12), كيلو(1), نص كيلو(0.5)",
        "",
        "### 2. ProductUnitPrice (موديل جديد في products)",
        "كل منتج ممكن يكون له سعر مختلف لكل وحدة بيع.",
        "is_auto=True → السعر = base_price × factor",
        "is_auto=False → سعر يدوي (خصم جملة مثلاً)",
        "",
        "### 3. Product (تعديل)",
        "أُضيف: base_unit, purchase_unit",
        "stock أصبح read_only في الـ API — التعديل عبر StockAdjustment فقط",
        "",
        "### 4. SaleItem (تعديل)",
        "أُضيف: unit (FK → UoM), unit_quantity",
        "quantity = unit_quantity × unit.factor (الكمية الفعلية بالوحدة الأساسية)",
        "",
        "### 5. PurchaseOrderItem (تعديل)",
        "أُضيف: unit (FK → UoM)",
        "receive action يحسب: actual_qty = quantity × unit.factor",
        "",
        "## مثال عملي",
        "منتج: مياه نستله",
        "  base_unit = قطعة (factor=1)",
        "  purchase_unit = كرتون (factor=12)",
        "  أسعار: قطعة=3ج, نص كرتون=15ج, كرتون=28ج",
        "",
        "  استلام 5 كراتين → stock += 60 قطعة",
        "  بيع 2 كرتون     → stock -= 24 قطعة",
        "  بيع 3 قطع       → stock -= 3  قطعة",
        "",
        "## الخطوات بعد تشغيل السكريبت",
        "cd pos_backend",
        "python manage.py makemigrations",
        "python manage.py migrate",
        "python manage.py createsuperuser",
        "python manage.py runserver",
    ]
    open(README, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("   📄  README → " + README)


# ═══════════════════════════════════════════════════════════════
# 1. products/models.py  الجديد
# ═══════════════════════════════════════════════════════════════
PRODUCTS_MODELS = (
    "from django.db import models\n"
    "import uuid\n"
    "\n"
    "\n"
    "class UnitOfMeasure(models.Model):\n"
    "    \"\"\"وحدة القياس — قطعة / دستة / كرتون / كيلو ...\"\"\"\n"
    "\n"
    "    CATEGORY_CHOICES = [\n"
    "        ('count',  'عدد'),\n"
    "        ('weight', 'وزن'),\n"
    "        ('volume', 'حجم'),\n"
    "        ('length', 'طول'),\n"
    "        ('other',  'أخرى'),\n"
    "    ]\n"
    "\n"
    "    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    name        = models.CharField(max_length=50, unique=True, verbose_name='اسم الوحدة')\n"
    "    symbol      = models.CharField(max_length=10, blank=True, default='', verbose_name='الرمز')\n"
    "    factor      = models.DecimalField(\n"
    "        max_digits=10, decimal_places=4, default=1,\n"
    "        verbose_name='معامل التحويل',\n"
    "        help_text='كم وحدة أساسية تعادل هذه الوحدة — مثال: كرتون=12'\n"
    "    )\n"
    "    category    = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='count')\n"
    "    is_base     = models.BooleanField(default=False, verbose_name='وحدة أساسية')\n"
    "    is_active   = models.BooleanField(default=True)\n"
    "    created_at  = models.DateTimeField(auto_now_add=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'وحدة قياس'\n"
    "        verbose_name_plural = 'وحدات القياس'\n"
    "        ordering            = ['category', 'factor']\n"
    "\n"
    "    def __str__(self):\n"
    "        return self.name\n"
    "\n"
    "\n"
    "class Category(models.Model):\n"
    "    \"\"\"فئة المنتجات\"\"\"\n"
    "    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    name       = models.CharField(max_length=100, verbose_name='اسم الفئة')\n"
    "    icon       = models.CharField(max_length=50, blank=True, null=True)\n"
    "    color      = models.CharField(max_length=7, default='#3B82F6')\n"
    "    created_at = models.DateTimeField(auto_now_add=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'فئة'\n"
    "        verbose_name_plural = 'الفئات'\n"
    "        ordering            = ['name']\n"
    "\n"
    "    def __str__(self):\n"
    "        return self.name\n"
    "\n"
    "\n"
    "class Product(models.Model):\n"
    "    \"\"\"المنتج — المخزون دايماً بالوحدة الأساسية\"\"\"\n"
    "\n"
    "    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    name         = models.CharField(max_length=200, verbose_name='اسم المنتج')\n"
    "    category     = models.ForeignKey(\n"
    "        Category, on_delete=models.SET_NULL,\n"
    "        null=True, blank=True, related_name='products'\n"
    "    )\n"
    "    barcode      = models.CharField(max_length=100, unique=True, blank=True, null=True)\n"
    "    description  = models.TextField(blank=True, null=True)\n"
    "    image_url    = models.URLField(blank=True, null=True)\n"
    "    is_active    = models.BooleanField(default=True)\n"
    "\n"
    "    # ── الأسعار ──────────────────────────────────────────\n"
    "    price        = models.DecimalField(\n"
    "        max_digits=10, decimal_places=2,\n"
    "        verbose_name='سعر البيع (بالوحدة الأساسية)'\n"
    "    )\n"
    "    cost         = models.DecimalField(\n"
    "        max_digits=10, decimal_places=2, default=0,\n"
    "        verbose_name='تكلفة الشراء (بالوحدة الأساسية)'\n"
    "    )\n"
    "\n"
    "    # ── المخزون ──────────────────────────────────────────\n"
    "    # دايماً بالوحدة الأساسية — لا يُعدَّل مباشرة من الـ API\n"
    "    stock        = models.IntegerField(default=0, verbose_name='المخزون (بالوحدة الأساسية)')\n"
    "    min_stock    = models.IntegerField(default=10, verbose_name='الحد الأدنى للتنبيه')\n"
    "\n"
    "    # ── وحدات القياس ─────────────────────────────────────\n"
    "    base_unit    = models.ForeignKey(\n"
    "        UnitOfMeasure, on_delete=models.PROTECT,\n"
    "        related_name='base_products',\n"
    "        null=True, blank=True,\n"
    "        verbose_name='الوحدة الأساسية'\n"
    "    )\n"
    "    purchase_unit = models.ForeignKey(\n"
    "        UnitOfMeasure, on_delete=models.SET_NULL,\n"
    "        related_name='purchase_products',\n"
    "        null=True, blank=True,\n"
    "        verbose_name='وحدة الشراء الافتراضية'\n"
    "    )\n"
    "\n"
    "    created_at   = models.DateTimeField(auto_now_add=True)\n"
    "    updated_at   = models.DateTimeField(auto_now=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'منتج'\n"
    "        verbose_name_plural = 'المنتجات'\n"
    "        ordering            = ['-created_at']\n"
    "\n"
    "    def __str__(self):\n"
    "        return self.name\n"
    "\n"
    "    @property\n"
    "    def profit_margin(self):\n"
    "        if self.cost and self.cost > 0:\n"
    "            return float((self.price - self.cost) / self.cost * 100)\n"
    "        return 0\n"
    "\n"
    "    @property\n"
    "    def is_low_stock(self):\n"
    "        return self.stock <= self.min_stock\n"
    "\n"
    "\n"
    "class ProductUnitPrice(models.Model):\n"
    "    \"\"\"سعر المنتج لكل وحدة بيع\"\"\"\n"
    "\n"
    "    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    product = models.ForeignKey(\n"
    "        Product, on_delete=models.CASCADE,\n"
    "        related_name='unit_prices'\n"
    "    )\n"
    "    unit    = models.ForeignKey(\n"
    "        UnitOfMeasure, on_delete=models.CASCADE,\n"
    "        related_name='product_prices'\n"
    "    )\n"
    "    price   = models.DecimalField(max_digits=10, decimal_places=2)\n"
    "    is_auto = models.BooleanField(\n"
    "        default=True,\n"
    "        help_text='True = محسوب تلقائياً (base_price × factor) | False = سعر يدوي'\n"
    "    )\n"
    "    is_active = models.BooleanField(default=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'سعر الوحدة'\n"
    "        verbose_name_plural = 'أسعار الوحدات'\n"
    "        unique_together     = ('product', 'unit')\n"
    "\n"
    "    def save(self, *args, **kwargs):\n"
    "        if self.is_auto and self.product and self.unit:\n"
    "            self.price = self.product.price * self.unit.factor\n"
    "        super().save(*args, **kwargs)\n"
    "\n"
    "    def __str__(self):\n"
    "        return self.product.name + ' / ' + self.unit.name + ' = ' + str(self.price)\n"
)


# ═══════════════════════════════════════════════════════════════
# 2. inventory/models.py  الجديد
# ═══════════════════════════════════════════════════════════════
INVENTORY_MODELS = (
    "from django.db import models\n"
    "import uuid\n"
    "from django.conf import settings\n"
    "\n"
    "\n"
    "class Supplier(models.Model):\n"
    "    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    name       = models.CharField(max_length=200, verbose_name='اسم المورد')\n"
    "    phone      = models.CharField(max_length=20,  blank=True, default='')\n"
    "    email      = models.EmailField(blank=True, default='')\n"
    "    address    = models.TextField(blank=True, default='')\n"
    "    notes      = models.TextField(blank=True, default='')\n"
    "    is_active  = models.BooleanField(default=True)\n"
    "    created_at = models.DateTimeField(auto_now_add=True)\n"
    "    updated_at = models.DateTimeField(auto_now=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'مورد'\n"
    "        verbose_name_plural = 'الموردون'\n"
    "        ordering            = ['name']\n"
    "\n"
    "    def __str__(self):\n"
    "        return self.name\n"
    "\n"
    "\n"
    "class PurchaseOrder(models.Model):\n"
    "    STATUS = [\n"
    "        ('draft',     'مسودة'),\n"
    "        ('ordered',   'تم الطلب'),\n"
    "        ('received',  'مستلم'),\n"
    "        ('cancelled', 'ملغي'),\n"
    "    ]\n"
    "    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    reference_number = models.CharField(max_length=50, unique=True)\n"
    "    supplier         = models.ForeignKey(\n"
    "        Supplier, null=True, blank=True,\n"
    "        on_delete=models.SET_NULL, related_name='orders'\n"
    "    )\n"
    "    user             = models.ForeignKey(\n"
    "        settings.AUTH_USER_MODEL, null=True,\n"
    "        on_delete=models.SET_NULL, related_name='purchase_orders'\n"
    "    )\n"
    "    status           = models.CharField(max_length=20, choices=STATUS, default='draft')\n"
    "    total_cost       = models.DecimalField(max_digits=12, decimal_places=2, default=0)\n"
    "    notes            = models.TextField(blank=True, default='')\n"
    "    expected_date    = models.DateField(null=True, blank=True)\n"
    "    received_at      = models.DateTimeField(null=True, blank=True)\n"
    "    created_at       = models.DateTimeField(auto_now_add=True)\n"
    "    updated_at       = models.DateTimeField(auto_now=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'أمر شراء'\n"
    "        verbose_name_plural = 'أوامر الشراء'\n"
    "        ordering            = ['-created_at']\n"
    "\n"
    "    def __str__(self):\n"
    "        return self.reference_number\n"
    "\n"
    "    def recalculate_total(self):\n"
    "        total = sum(i.subtotal for i in self.items.all())\n"
    "        self.total_cost = total\n"
    "        self.save(update_fields=['total_cost'])\n"
    "\n"
    "\n"
    "class PurchaseOrderItem(models.Model):\n"
    "    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    order             = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')\n"
    "    product           = models.ForeignKey('products.Product', on_delete=models.CASCADE)\n"
    "    unit              = models.ForeignKey(\n"
    "        'products.UnitOfMeasure', on_delete=models.PROTECT,\n"
    "        null=True, blank=True,\n"
    "        verbose_name='وحدة الاستلام'\n"
    "    )\n"
    "    quantity          = models.PositiveIntegerField(default=1, verbose_name='الكمية بالوحدة')\n"
    "    received_quantity = models.PositiveIntegerField(default=0)\n"
    "    unit_cost         = models.DecimalField(max_digits=10, decimal_places=2, default=0)\n"
    "\n"
    "    @property\n"
    "    def factor(self):\n"
    "        \"\"\"معامل تحويل الوحدة\"\"\"\n"
    "        if self.unit and self.unit.factor:\n"
    "            return float(self.unit.factor)\n"
    "        return 1.0\n"
    "\n"
    "    @property\n"
    "    def actual_quantity(self):\n"
    "        \"\"\"الكمية الفعلية بالوحدة الأساسية\"\"\"\n"
    "        return int(self.quantity * self.factor)\n"
    "\n"
    "    @property\n"
    "    def actual_received(self):\n"
    "        return int(self.received_quantity * self.factor)\n"
    "\n"
    "    @property\n"
    "    def remaining_quantity(self):\n"
    "        return max(0, self.quantity - self.received_quantity)\n"
    "\n"
    "    @property\n"
    "    def subtotal(self):\n"
    "        return self.unit_cost * self.quantity\n"
    "\n"
    "    def __str__(self):\n"
    "        unit_name = self.unit.name if self.unit else 'قطعة'\n"
    "        return self.product.name + ' x' + str(self.quantity) + ' ' + unit_name\n"
    "\n"
    "\n"
    "class StockAdjustment(models.Model):\n"
    "    REASONS = [\n"
    "        ('count',  'جرد دوري'),\n"
    "        ('damage', 'تلف'),\n"
    "        ('loss',   'فقد/سرقة'),\n"
    "        ('return', 'مرتجع'),\n"
    "        ('expiry', 'انتهاء صلاحية'),\n"
    "        ('other',  'أخرى'),\n"
    "    ]\n"
    "    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    product         = models.ForeignKey('products.Product', on_delete=models.CASCADE)\n"
    "    user            = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)\n"
    "    quantity_before = models.IntegerField(default=0)\n"
    "    quantity_change = models.IntegerField(default=0)\n"
    "    quantity_after  = models.IntegerField(default=0)\n"
    "    reason          = models.CharField(max_length=20, choices=REASONS, default='count')\n"
    "    notes           = models.TextField(blank=True, default='')\n"
    "    created_at      = models.DateTimeField(auto_now_add=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'تسوية مخزون'\n"
    "        verbose_name_plural = 'تسويات المخزون'\n"
    "        ordering            = ['-created_at']\n"
    "\n"
    "    def __str__(self):\n"
    "        return self.product.name + ': ' + ('+' if self.quantity_change >= 0 else '') + str(self.quantity_change)\n"
    "\n"
    "\n"
    "class StockAlert(models.Model):\n"
    "    TYPES = [\n"
    "        ('low',    'مخزون منخفض'),\n"
    "        ('out',    'نفاد المخزون'),\n"
    "        ('expiry', 'قرب انتهاء الصلاحية'),\n"
    "    ]\n"
    "    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    product       = models.ForeignKey('products.Product', on_delete=models.CASCADE)\n"
    "    alert_type    = models.CharField(max_length=20, choices=TYPES, default='low')\n"
    "    threshold     = models.IntegerField(default=10)\n"
    "    current_stock = models.IntegerField(default=0)\n"
    "    is_resolved   = models.BooleanField(default=False)\n"
    "    resolved_at   = models.DateTimeField(null=True, blank=True)\n"
    "    created_at    = models.DateTimeField(auto_now_add=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'تنبيه مخزون'\n"
    "        verbose_name_plural = 'تنبيهات المخزون'\n"
    "        ordering            = ['-created_at']\n"
    "\n"
    "    def __str__(self):\n"
    "        return self.product.name + ' - ' + self.alert_type\n"
    "\n"
    "\n"
    "class StockMovement(models.Model):\n"
    "    MOVEMENT_TYPES = [\n"
    "        ('sale',       'بيع'),\n"
    "        ('purchase',   'شراء'),\n"
    "        ('adjustment', 'تسوية'),\n"
    "        ('return',     'مرتجع'),\n"
    "        ('initial',    'رصيد افتتاحي'),\n"
    "    ]\n"
    "    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    product       = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='movements')\n"
    "    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)\n"
    "    quantity      = models.IntegerField(verbose_name='الكمية بالوحدة الأساسية')\n"
    "    stock_before  = models.IntegerField(default=0)\n"
    "    stock_after   = models.IntegerField(default=0)\n"
    "    unit          = models.ForeignKey(\n"
    "        'products.UnitOfMeasure', on_delete=models.SET_NULL,\n"
    "        null=True, blank=True,\n"
    "        verbose_name='الوحدة المستخدمة'\n"
    "    )\n"
    "    unit_quantity = models.DecimalField(\n"
    "        max_digits=10, decimal_places=4,\n"
    "        null=True, blank=True,\n"
    "        verbose_name='الكمية بالوحدة المستخدمة'\n"
    "    )\n"
    "    reference     = models.CharField(max_length=200, blank=True, default='')\n"
    "    notes         = models.TextField(blank=True, default='')\n"
    "    user          = models.ForeignKey(\n"
    "        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL\n"
    "    )\n"
    "    created_at    = models.DateTimeField(auto_now_add=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'حركة مخزون'\n"
    "        verbose_name_plural = 'حركات المخزون'\n"
    "        ordering            = ['-created_at']\n"
    "\n"
    "    def __str__(self):\n"
    "        sign = '+' if self.quantity >= 0 else ''\n"
    "        return self.product.name + ' ' + self.movement_type + ' ' + sign + str(self.quantity)\n"
)


# ═══════════════════════════════════════════════════════════════
# 3. sales/models.py  الجديد — يضيف unit و unit_quantity لـ SaleItem
# ═══════════════════════════════════════════════════════════════
SALES_MODELS = (
    "from django.db import models\n"
    "from django.contrib.auth.models import User\n"
    "from django.core.validators import MinValueValidator\n"
    "import uuid\n"
    "from .models_cashregister import CashRegister, CashTransaction\n"
    "\n"
    "\n"
    "class Sale(models.Model):\n"
    "    PAYMENT_METHODS = [\n"
    "        ('cash', 'نقدي'),\n"
    "        ('card', 'بطاقة'),\n"
    "        ('both', 'نقدي + بطاقة'),\n"
    "    ]\n"
    "    STATUS_CHOICES = [\n"
    "        ('completed', 'مكتملة'),\n"
    "        ('cancelled', 'ملغاة'),\n"
    "        ('pending',   'قيد الانتظار'),\n"
    "    ]\n"
    "\n"
    "    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    customer       = models.ForeignKey(\n"
    "        'customers.Customer', on_delete=models.SET_NULL,\n"
    "        null=True, blank=True, related_name='sales'\n"
    "    )\n"
    "    user           = models.ForeignKey(\n"
    "        User, on_delete=models.SET_NULL,\n"
    "        null=True, related_name='sales'\n"
    "    )\n"
    "    cash_register  = models.ForeignKey(\n"
    "        'CashRegister', on_delete=models.SET_NULL,\n"
    "        null=True, blank=True, related_name='sales'\n"
    "    )\n"
    "    subtotal       = models.DecimalField(max_digits=10, decimal_places=2, default=0)\n"
    "    discount       = models.DecimalField(max_digits=10, decimal_places=2, default=0)\n"
    "    tax            = models.DecimalField(max_digits=10, decimal_places=2, default=0)\n"
    "    total          = models.DecimalField(max_digits=10, decimal_places=2)\n"
    "    paid_amount    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)\n"
    "    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')\n"
    "    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')\n"
    "    notes          = models.TextField(blank=True, null=True)\n"
    "    invoice_number = models.CharField(max_length=50, blank=True, null=True)\n"
    "    created_at     = models.DateTimeField(auto_now_add=True)\n"
    "    updated_at     = models.DateTimeField(auto_now=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'عملية بيع'\n"
    "        verbose_name_plural = 'عمليات البيع'\n"
    "        ordering            = ['-created_at']\n"
    "\n"
    "    def __str__(self):\n"
    "        return 'Sale #' + str(self.id)[:8] + ' - ' + str(self.total)\n"
    "\n"
    "    @property\n"
    "    def items_count(self):\n"
    "        return self.items.count()\n"
    "\n"
    "    @property\n"
    "    def total_profit(self):\n"
    "        profit = 0\n"
    "        for item in self.items.all():\n"
    "            if item.product:\n"
    "                profit += (item.price - item.product.cost) * item.quantity\n"
    "        return profit\n"
    "\n"
    "\n"
    "class SaleItem(models.Model):\n"
    "    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    sale         = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')\n"
    "    product      = models.ForeignKey(\n"
    "        'products.Product', on_delete=models.SET_NULL,\n"
    "        null=True, related_name='sale_items'\n"
    "    )\n"
    "    product_name = models.CharField(max_length=200)\n"
    "\n"
    "    # ── الوحدة ───────────────────────────────────────────\n"
    "    unit          = models.ForeignKey(\n"
    "        'products.UnitOfMeasure', on_delete=models.SET_NULL,\n"
    "        null=True, blank=True,\n"
    "        verbose_name='وحدة البيع'\n"
    "    )\n"
    "    unit_quantity = models.DecimalField(\n"
    "        max_digits=10, decimal_places=4, default=1,\n"
    "        verbose_name='الكمية بوحدة البيع'\n"
    "    )\n"
    "    # quantity = الكمية الفعلية بالوحدة الأساسية\n"
    "    quantity     = models.IntegerField(validators=[MinValueValidator(1)])\n"
    "\n"
    "    price        = models.DecimalField(max_digits=10, decimal_places=2)\n"
    "    subtotal     = models.DecimalField(max_digits=10, decimal_places=2)\n"
    "    created_at   = models.DateTimeField(auto_now_add=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'عنصر بيع'\n"
    "        verbose_name_plural = 'عناصر البيع'\n"
    "        ordering            = ['created_at']\n"
    "\n"
    "    def __str__(self):\n"
    "        return self.product_name + ' x' + str(self.quantity)\n"
    "\n"
    "    def save(self, *args, **kwargs):\n"
    "        self.subtotal = self.price * self.unit_quantity\n"
    "        super().save(*args, **kwargs)\n"
    "\n"
    "\n"
    "class Return(models.Model):\n"
    "    STATUS_CHOICES = [\n"
    "        ('pending',   'قيد المراجعة'),\n"
    "        ('approved',  'مقبول'),\n"
    "        ('rejected',  'مرفوض'),\n"
    "        ('completed', 'مكتمل'),\n"
    "    ]\n"
    "    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    sale          = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns')\n"
    "    user          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='processed_returns')\n"
    "    cash_register = models.ForeignKey('CashRegister', on_delete=models.SET_NULL, null=True, blank=True, related_name='returns')\n"
    "    total_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0)\n"
    "    reason        = models.TextField(blank=True, null=True)\n"
    "    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')\n"
    "    created_at    = models.DateTimeField(auto_now_add=True)\n"
    "    updated_at    = models.DateTimeField(auto_now=True)\n"
    "\n"
    "    class Meta:\n"
    "        ordering            = ['-created_at']\n"
    "        verbose_name        = 'مرتجع'\n"
    "        verbose_name_plural = 'المرتجعات'\n"
    "\n"
    "    def __str__(self):\n"
    "        return 'مرتجع #' + str(self.id)[:8] + ' - ' + str(self.total_amount)\n"
    "\n"
    "\n"
    "class ReturnItem(models.Model):\n"
    "    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
    "    return_obj = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')\n"
    "    sale_item  = models.ForeignKey(SaleItem, on_delete=models.CASCADE)\n"
    "    product    = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True)\n"
    "    quantity   = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])\n"
    "    price      = models.DecimalField(max_digits=10, decimal_places=2)\n"
    "    subtotal   = models.DecimalField(max_digits=10, decimal_places=2)\n"
    "    created_at = models.DateTimeField(auto_now_add=True)\n"
    "\n"
    "    class Meta:\n"
    "        verbose_name        = 'عنصر مرتجع'\n"
    "        verbose_name_plural = 'عناصر المرتجعات'\n"
    "\n"
    "    def save(self, *args, **kwargs):\n"
    "        self.subtotal = self.quantity * self.price\n"
    "        super().save(*args, **kwargs)\n"
    "\n"
    "    def __str__(self):\n"
    "        name = self.product.name if self.product else self.sale_item.product_name\n"
    "        return name + ' x' + str(self.quantity)\n"
)


# ═══════════════════════════════════════════════════════════════
# 4. products/serializers.py  الجديد
# ═══════════════════════════════════════════════════════════════
PRODUCTS_SERIALIZERS = (
    "from rest_framework import serializers\n"
    "from .models import Category, Product, UnitOfMeasure, ProductUnitPrice\n"
    "\n"
    "\n"
    "class UnitOfMeasureSerializer(serializers.ModelSerializer):\n"
    "    class Meta:\n"
    "        model  = UnitOfMeasure\n"
    "        fields = ['id', 'name', 'symbol', 'factor', 'category', 'is_base', 'is_active']\n"
    "\n"
    "\n"
    "class ProductUnitPriceSerializer(serializers.ModelSerializer):\n"
    "    unit_name = serializers.CharField(source='unit.name', read_only=True)\n"
    "    factor    = serializers.DecimalField(source='unit.factor', max_digits=10,\n"
    "                                         decimal_places=4, read_only=True)\n"
    "\n"
    "    class Meta:\n"
    "        model  = ProductUnitPrice\n"
    "        fields = ['id', 'unit', 'unit_name', 'factor', 'price', 'is_auto', 'is_active']\n"
    "\n"
    "\n"
    "class CategorySerializer(serializers.ModelSerializer):\n"
    "    class Meta:\n"
    "        model  = Category\n"
    "        fields = ['id', 'name', 'icon', 'color', 'created_at']\n"
    "\n"
    "\n"
    "class ProductSerializer(serializers.ModelSerializer):\n"
    "    category_name  = serializers.CharField(source='category.name', read_only=True)\n"
    "    base_unit_name = serializers.CharField(source='base_unit.name', read_only=True)\n"
    "    purchase_unit_name = serializers.CharField(source='purchase_unit.name', read_only=True)\n"
    "    unit_prices    = ProductUnitPriceSerializer(many=True, read_only=True)\n"
    "    profit_margin  = serializers.ReadOnlyField()\n"
    "    is_low_stock   = serializers.ReadOnlyField()\n"
    "\n"
    "    # stock للقراءة فقط — التعديل عبر StockAdjustment\n"
    "    stock = serializers.IntegerField(read_only=True)\n"
    "\n"
    "    class Meta:\n"
    "        model  = Product\n"
    "        fields = [\n"
    "            'id', 'name', 'category', 'category_name',\n"
    "            'barcode', 'description', 'image_url', 'is_active',\n"
    "            'price', 'cost', 'stock', 'min_stock',\n"
    "            'base_unit', 'base_unit_name',\n"
    "            'purchase_unit', 'purchase_unit_name',\n"
    "            'unit_prices',\n"
    "            'profit_margin', 'is_low_stock',\n"
    "            'created_at', 'updated_at',\n"
    "        ]\n"
    "        read_only_fields = ['id', 'stock', 'created_at', 'updated_at']\n"
    "\n"
    "\n"
    "class ProductListSerializer(serializers.ModelSerializer):\n"
    "    category_name  = serializers.CharField(source='category.name', read_only=True)\n"
    "    base_unit_name = serializers.CharField(source='base_unit.name', read_only=True)\n"
    "    unit_prices    = ProductUnitPriceSerializer(many=True, read_only=True)\n"
    "    is_low_stock   = serializers.ReadOnlyField()\n"
    "\n"
    "    class Meta:\n"
    "        model  = Product\n"
    "        fields = [\n"
    "            'id', 'name', 'category_name', 'barcode',\n"
    "            'price', 'stock', 'min_stock', 'is_active',\n"
    "            'base_unit_name', 'unit_prices', 'is_low_stock',\n"
    "        ]\n"
)


# ═══════════════════════════════════════════════════════════════
# 5. products/views.py  الجديد
# ═══════════════════════════════════════════════════════════════
PRODUCTS_VIEWS = (
    "from rest_framework import viewsets, filters, status\n"
    "from rest_framework.decorators import action\n"
    "from rest_framework.response import Response\n"
    "from rest_framework.permissions import IsAuthenticated\n"
    "from rest_framework.exceptions import PermissionDenied\n"
    "from django_filters.rest_framework import DjangoFilterBackend\n"
    "from django.db.models import F\n"
    "from .models import Category, Product, UnitOfMeasure, ProductUnitPrice\n"
    "from .serializers import (\n"
    "    CategorySerializer, ProductSerializer,\n"
    "    ProductListSerializer, UnitOfMeasureSerializer,\n"
    "    ProductUnitPriceSerializer,\n"
    ")\n"
    "\n"
    "\n"
    "class UnitOfMeasureViewSet(viewsets.ModelViewSet):\n"
    "    queryset           = UnitOfMeasure.objects.filter(is_active=True)\n"
    "    serializer_class   = UnitOfMeasureSerializer\n"
    "    permission_classes = [IsAuthenticated]\n"
    "    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]\n"
    "    search_fields      = ['name', 'symbol']\n"
    "    ordering           = ['category', 'factor']\n"
    "\n"
    "\n"
    "class CategoryViewSet(viewsets.ModelViewSet):\n"
    "    queryset           = Category.objects.all()\n"
    "    serializer_class   = CategorySerializer\n"
    "    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]\n"
    "    search_fields      = ['name']\n"
    "    ordering           = ['name']\n"
    "\n"
    "\n"
    "class ProductViewSet(viewsets.ModelViewSet):\n"
    "    queryset = Product.objects.select_related(\n"
    "        'category', 'base_unit', 'purchase_unit'\n"
    "    ).prefetch_related('unit_prices__unit').all()\n"
    "    serializer_class   = ProductSerializer\n"
    "    permission_classes = [IsAuthenticated]\n"
    "    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]\n"
    "    filterset_fields   = ['category', 'is_active']\n"
    "    search_fields      = ['name', 'barcode']\n"
    "    ordering_fields    = ['name', 'price', 'stock', 'created_at']\n"
    "    ordering           = ['-created_at']\n"
    "\n"
    "    def _require_perm(self, request, perm):\n"
    "        if not (request.user.is_superuser or request.user.has_perm('users.' + perm)):\n"
    "            raise PermissionDenied('غير مصرح')\n"
    "\n"
    "    def get_queryset(self):\n"
    "        user = self.request.user\n"
    "        if not (user.is_superuser\n"
    "                or user.has_perm('users.products_view')\n"
    "                or user.has_perm('users.products_manage')):\n"
    "            return Product.objects.none()\n"
    "        return super().get_queryset()\n"
    "\n"
    "    def get_serializer_class(self):\n"
    "        if self.action == 'list':\n"
    "            return ProductListSerializer\n"
    "        return ProductSerializer\n"
    "\n"
    "    def perform_create(self, serializer):\n"
    "        self._require_perm(self.request, 'products_manage')\n"
    "        product = serializer.save()\n"
    "        # ✅ initial StockMovement لو المنتج اتضاف بمخزون\n"
    "        if product.stock and product.stock > 0:\n"
    "            from inventory.models import StockMovement\n"
    "            StockMovement.objects.create(\n"
    "                product=product,\n"
    "                movement_type='initial',\n"
    "                quantity=product.stock,\n"
    "                stock_before=0,\n"
    "                stock_after=product.stock,\n"
    "                unit=product.base_unit,\n"
    "                unit_quantity=product.stock,\n"
    "                notes='initial stock',\n"
    "                user=self.request.user,\n"
    "            )\n"
    "\n"
    "    def perform_update(self, serializer):\n"
    "        self._require_perm(self.request, 'products_manage')\n"
    "        serializer.save()\n"
    "\n"
    "    def perform_destroy(self, instance):\n"
    "        self._require_perm(self.request, 'products_manage')\n"
    "        instance.delete()\n"
    "\n"
    "    @action(detail=False, methods=['get'])\n"
    "    def low_stock(self, request):\n"
    "        products = self.get_queryset().filter(is_active=True).filter(\n"
    "            stock__lte=F('min_stock')\n"
    "        )\n"
    "        return Response(self.get_serializer(products, many=True).data)\n"
    "\n"
    "    @action(detail=False, methods=['get'])\n"
    "    def by_barcode(self, request):\n"
    "        barcode = request.query_params.get('barcode', '')\n"
    "        if not barcode:\n"
    "            return Response({'error': 'الباركود مطلوب'}, status=status.HTTP_400_BAD_REQUEST)\n"
    "        try:\n"
    "            product = Product.objects.select_related(\n"
    "                'base_unit', 'purchase_unit'\n"
    "            ).prefetch_related('unit_prices__unit').get(\n"
    "                barcode=barcode, is_active=True\n"
    "            )\n"
    "            return Response(ProductSerializer(product).data)\n"
    "        except Product.DoesNotExist:\n"
    "            return Response({'error': 'المنتج غير موجود'}, status=status.HTTP_404_NOT_FOUND)\n"
    "\n"
    "    @action(detail=True, methods=['post'])\n"
    "    def set_unit_prices(self, request, pk=None):\n"
    "        \"\"\"تحديث/إنشاء أسعار الوحدات للمنتج\"\"\"\n"
    "        self._require_perm(request, 'products_manage')\n"
    "        product = self.get_object()\n"
    "        prices  = request.data.get('prices', [])\n"
    "        for p in prices:\n"
    "            unit_id  = p.get('unit')\n"
    "            price    = p.get('price')\n"
    "            is_auto  = p.get('is_auto', False)\n"
    "            is_active = p.get('is_active', True)\n"
    "            if not unit_id:\n"
    "                continue\n"
    "            obj, _ = ProductUnitPrice.objects.get_or_create(\n"
    "                product=product, unit_id=unit_id\n"
    "            )\n"
    "            obj.is_auto   = is_auto\n"
    "            obj.is_active = is_active\n"
    "            if not is_auto and price is not None:\n"
    "                obj.price = price\n"
    "            obj.save()\n"
    "        return Response(ProductSerializer(product).data)\n"
)


# ═══════════════════════════════════════════════════════════════
# 6. products/urls.py  الجديد
# ═══════════════════════════════════════════════════════════════
PRODUCTS_URLS = (
    "from django.urls import path, include\n"
    "from rest_framework.routers import DefaultRouter\n"
    "from .views import CategoryViewSet, ProductViewSet, UnitOfMeasureViewSet\n"
    "\n"
    "router = DefaultRouter()\n"
    "router.register('categories',    CategoryViewSet,      basename='category')\n"
    "router.register('products',      ProductViewSet,       basename='product')\n"
    "router.register('units',         UnitOfMeasureViewSet, basename='unit')\n"
    "\n"
    "urlpatterns = [path('', include(router.urls))]\n"
)


# ═══════════════════════════════════════════════════════════════
# 7. inventory/views.py  — تعديل receive فقط (factor)
# ═══════════════════════════════════════════════════════════════
OLD_RECEIVE = (
    "                if qty > 0:\n"
    "                    product = item.product\n"
    "                    stock_before = product.stock\n"
    "                    Product.objects.filter(id=product.id).update(\n"
    "                        stock=F('stock') + qty,\n"
    "                        cost=item.unit_cost\n"
    "                    )\n"
    "                    product.refresh_from_db()\n"
    "                    stock_after = product.stock\n"
    "                    item.received_quantity = item.received_quantity + qty\n"
    "                    item.save(update_fields=['received_quantity'])\n"
    "                    StockAdjustment.objects.create(\n"
    "                        product         = product,\n"
    "                        user            = request.user,\n"
    "                        quantity_before = stock_before,\n"
    "                        quantity_change = qty,\n"
    "                        quantity_after  = stock_after,\n"
    "                        reason          = 'other',\n"
    "                        notes           = 'استلام من امر شراء #' + order.reference_number\n"
    "                    )\n"
    "                    StockMovement.objects.create(\n"
    "                        product       = product,\n"
    "                        movement_type = 'purchase',\n"
    "                        quantity      = qty,\n"
    "                        stock_before  = stock_before,\n"
    "                        stock_after   = stock_after,\n"
    "                        reference     = order.reference_number,\n"
    "                        user          = request.user,\n"
    "                        notes         = 'استلام امر شراء #' + order.reference_number\n"
    "                    )"
)

NEW_RECEIVE = (
    "                if qty > 0:\n"
    "                    product = item.product\n"
    "                    # ✅ UoM: actual_qty = qty × unit.factor\n"
    "                    unit        = item.unit\n"
    "                    factor      = float(unit.factor) if unit and unit.factor else 1.0\n"
    "                    actual_qty  = int(qty * factor)\n"
    "                    stock_before = product.stock\n"
    "                    Product.objects.filter(id=product.id).update(\n"
    "                        stock=F('stock') + actual_qty,\n"
    "                        cost=item.unit_cost\n"
    "                    )\n"
    "                    product.refresh_from_db()\n"
    "                    stock_after = product.stock\n"
    "                    item.received_quantity = item.received_quantity + qty\n"
    "                    item.save(update_fields=['received_quantity'])\n"
    "                    StockAdjustment.objects.create(\n"
    "                        product         = product,\n"
    "                        user            = request.user,\n"
    "                        quantity_before = stock_before,\n"
    "                        quantity_change = actual_qty,\n"
    "                        quantity_after  = stock_after,\n"
    "                        reason          = 'other',\n"
    "                        notes           = 'استلام امر شراء #' + order.reference_number\n"
    "                    )\n"
    "                    StockMovement.objects.create(\n"
    "                        product       = product,\n"
    "                        movement_type = 'purchase',\n"
    "                        quantity      = actual_qty,\n"
    "                        stock_before  = stock_before,\n"
    "                        stock_after   = stock_after,\n"
    "                        unit          = unit,\n"
    "                        unit_quantity = qty,\n"
    "                        reference     = order.reference_number,\n"
    "                        user          = request.user,\n"
    "                        notes         = 'استلام امر شراء #' + order.reference_number\n"
    "                    )"
)


# ═══════════════════════════════════════════════════════════════
# 8. سكريبت shell لحذف الـ DB وإعادة البناء
# ═══════════════════════════════════════════════════════════════
RESET_SCRIPT = (
    "#!/bin/bash\n"
    "# reset_db.sh — حذف الـ DB وإعادة البناء\n"
    "set -e\n"
    "\n"
    "BACKEND='/home/momar/Projects/POS_DEV/posv1_dev10/pos_backend'\n"
    "PYTHON=\"$BACKEND/venv/bin/python\"\n"
    "\n"
    "echo ''\n"
    "echo '================================================'\n"
    "echo '  🗑️   حذف قاعدة البيانات...'\n"
    "echo '================================================'\n"
    "rm -f \"$BACKEND/db.sqlite3\"\n"
    "\n"
    "echo ''\n"
    "echo '  📦  makemigrations...'\n"
    "cd \"$BACKEND\"\n"
    "\"$PYTHON\" manage.py makemigrations\n"
    "\n"
    "echo ''\n"
    "echo '  🗄️   migrate...'\n"
    "\"$PYTHON\" manage.py migrate\n"
    "\n"
    "echo ''\n"
    "echo '  👤  createsuperuser...'\n"
    "\"$PYTHON\" manage.py createsuperuser\n"
    "\n"
    "echo ''\n"
    "echo '================================================'\n"
    "echo '  ✅  تم! شغّل: ./run-backend.sh'\n"
    "echo '================================================'\n"
    "echo ''\n"
)


# ── apply functions ───────────────────────────────────────────
def step_delete_migrations():
    print("\n[1/8] حذف الـ migrations القديمة ...")
    for app_dir in [PRODUCTS_DIR, INVENTORY_DIR, SALES_DIR]:
        delete_migrations(app_dir)


def step_products_models():
    print("\n[2/8] كتابة products/models.py ...")
    path = os.path.join(PRODUCTS_DIR, "models.py")
    backup(path)
    write_file(path, PRODUCTS_MODELS)


def step_inventory_models():
    print("\n[3/8] كتابة inventory/models.py ...")
    path = os.path.join(INVENTORY_DIR, "models.py")
    backup(path)
    write_file(path, INVENTORY_MODELS)


def step_sales_models():
    print("\n[4/8] كتابة sales/models.py ...")
    path = os.path.join(SALES_DIR, "models.py")
    backup(path)
    write_file(path, SALES_MODELS)


def step_products_serializers():
    print("\n[5/8] كتابة products/serializers.py ...")
    path = os.path.join(PRODUCTS_DIR, "serializers.py")
    backup(path)
    write_file(path, PRODUCTS_SERIALIZERS)


def step_products_views():
    print("\n[6/8] كتابة products/views.py + urls.py ...")
    path_v = os.path.join(PRODUCTS_DIR, "views.py")
    path_u = os.path.join(PRODUCTS_DIR, "urls.py")
    backup(path_v)
    backup(path_u)
    write_file(path_v, PRODUCTS_VIEWS)
    write_file(path_u, PRODUCTS_URLS)


def step_inventory_views():
    print("\n[7/8] تعديل inventory/views.py (receive + UoM factor) ...")
    path = os.path.join(INVENTORY_DIR, "views.py")
    src  = open(path, encoding="utf-8").read()
    if OLD_RECEIVE not in src:
        print("   ⚠️   receive block مش موجود بهذا الشكل — تخطي")
        return
    backup(path)
    write_file(path, src.replace(OLD_RECEIVE, NEW_RECEIVE, 1))


def step_reset_script():
    print("\n[8/8] كتابة reset_db.sh ...")
    path = os.path.join(BASE, "reset_db.sh")
    write_file(path, RESET_SCRIPT)
    os.chmod(path, 0o755)
    print("   🔑  chmod +x reset_db.sh")


# ── main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("=" * 58)
    print("  🔧  rebuild_with_uom.py")
    print("=" * 58)

    step_delete_migrations()
    step_products_models()
    step_inventory_models()
    step_sales_models()
    step_products_serializers()
    step_products_views()
    step_inventory_views()
    step_reset_script()

    print("\n[README] ...")
    write_readme()

    print("\n[CHANGELOG] ...")
    update_changelog(CHANGE_MSG)

    print()
    print("=" * 58)
    print("  🎉  تم!")
    print()
    print("  الخطوة التالية — شغّل:")
    print("  ./reset_db.sh")
    print()
    print("  ثم:")
    print("  ./run-backend.sh")
    print("=" * 58)
    print()
