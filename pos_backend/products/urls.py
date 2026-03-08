from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, UnitOfMeasureViewSet

router = DefaultRouter()
router.register('categories',    CategoryViewSet,      basename='category')
router.register('products',      ProductViewSet,       basename='product')
router.register('units',         UnitOfMeasureViewSet, basename='unit')

urlpatterns = [path('', include(router.urls))]
