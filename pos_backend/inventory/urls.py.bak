from rest_framework.routers import DefaultRouter
from .views import SupplierViewSet, PurchaseOrderViewSet, StockAdjustmentViewSet, StockAlertViewSet

router = DefaultRouter()
router.register('inventory/suppliers',       SupplierViewSet,       basename='supplier')
router.register('inventory/purchase-orders', PurchaseOrderViewSet,  basename='purchase-order')
router.register('inventory/adjustments',     StockAdjustmentViewSet,basename='stock-adjustment')
router.register('inventory/alerts',          StockAlertViewSet,     basename='stock-alert')

urlpatterns = router.urls
