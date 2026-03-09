# pos_backend/inventory/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from products.models import Product
from .models import StockAlert

@receiver(post_save, sender=Product)
def auto_create_stock_alert(sender, instance, **kwargs):
    """ينشئ تنبيهاً تلقائياً كل ما تغيّر مخزون المنتج"""
    # لا تُنشئ تنبيهاً لو في تنبيه نشط بالفعل
    existing = StockAlert.objects.filter(
        product=instance,
        is_resolved=False
    ).exists()
    if existing:
        return

    if instance.stock == 0:
        StockAlert.objects.create(
            product=instance,
            alert_type='out',
            threshold=10,
            current_stock=0
        )
    elif instance.stock <= 10:
        StockAlert.objects.create(
            product=instance,
            alert_type='low',
            threshold=10,
            current_stock=instance.stock
        )
