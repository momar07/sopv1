from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    SupplierViewSet, PurchaseOrderViewSet,
    StockAdjustmentViewSet, StockAlertViewSet, StockMovementViewSet,
)

router = DefaultRouter()
router.register('inventory/suppliers',       SupplierViewSet,        basename='supplier')
router.register('inventory/purchase-orders', PurchaseOrderViewSet,   basename='purchase-order')
router.register('inventory/adjustments',     StockAdjustmentViewSet, basename='stock-adjustment')
router.register('inventory/alerts',          StockAlertViewSet,      basename='stock-alert')
router.register('inventory/movements',       StockMovementViewSet,   basename='stock-movement')

urlpatterns = router.urls
