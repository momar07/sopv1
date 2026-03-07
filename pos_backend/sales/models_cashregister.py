import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class CashRegister(models.Model):
    STATUS_CHOICES = [
        ('open', 'مفتوح'),
        ('closed', 'مغلق'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cash_registers', verbose_name='المستخدم')
    opening_balance = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='رصيد الافتتاح'
    )
    opened_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت الفتح')
    opening_note = models.TextField(blank=True, default='', verbose_name='ملاحظة الافتتاح')

    closing_balance = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name='رصيد الإغلاق'
    )
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='وقت الإغلاق')
    closing_note = models.TextField(blank=True, default='', verbose_name='ملاحظة الإغلاق')

    total_cash_sales = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='إجمالي مبيعات النقد'
    )
    total_card_sales = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='إجمالي مبيعات البطاقة'
    )
    total_sales = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='إجمالي المبيعات'
    )
    total_returns = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='إجمالي المرتجعات'
    )
    total_cash_returns = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='إجمالي المرتجعات النقدية'
    )
    expected_cash = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='النقد المتوقع'
    )
    actual_cash = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='النقد الفعلي'
    )
    cash_difference = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='الفرق'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='open',
        verbose_name='الحالة'
    )

    class Meta:
        ordering = ['-opened_at']
        verbose_name = 'سجل الخزنة'
        verbose_name_plural = 'سجلات الخزنة'

    def __str__(self):
        return f"خزنة {self.user.username} - {self.opened_at.strftime('%Y-%m-%d %H:%M')}"

    def calculate_expected_cash(self):
        from django.db.models import Sum
        deposits = self.transactions.filter(transaction_type='deposit').aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        withdrawals = self.transactions.filter(transaction_type='withdrawal').aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        self.expected_cash = (
            self.opening_balance
            + self.total_cash_sales
            - self.total_cash_returns
            + deposits
            - withdrawals
        )
        return self.expected_cash

    def calculate_difference(self):
        self.cash_difference = self.actual_cash - self.expected_cash
        return self.cash_difference

    def calculate_closing_balance(self):
        self.closing_balance = self.actual_cash
        return self.closing_balance

    @property
    def duration(self):
        if self.closed_at:
            delta = self.closed_at - self.opened_at
            return round(delta.total_seconds() / 3600, 2)
        return None

    @property
    def sales_count(self):
        return self.sales.count()

    @property
    def returns_count(self):
        return self.returns.count()

    @property
    def net_cash(self):
        return self.total_cash_sales - self.total_cash_returns


class CashTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'إيداع'),
        ('withdrawal', 'سحب'),
        ('adjustment', 'تسوية'),
        ('return', 'مرتجع'),        # ← نوع جديد للمرتجعات
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name='سجل الخزنة'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name='نوع الحركة'
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='المبلغ'
    )
    reason = models.CharField(max_length=255, verbose_name='السبب')
    note = models.TextField(blank=True, default='', verbose_name='ملاحظة')
    created_by = models.ForeignKey(
    	User,
    	on_delete=models.SET_NULL,
    	null=True,
    	blank=True,
    	related_name='cash_transactions',
    	verbose_name='بواسطة'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت الحركة')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'حركة خزنة'
        verbose_name_plural = 'حركات الخزنة'

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} - {self.created_at.strftime('%Y-%m-%d')}"
