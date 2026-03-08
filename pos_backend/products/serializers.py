from rest_framework import serializers
from .models import Category, Product, UnitOfMeasure, ProductUnitPrice


class UnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UnitOfMeasure
        fields = ['id', 'name', 'symbol', 'factor', 'category', 'is_base', 'is_active']


class ProductUnitPriceSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    factor    = serializers.DecimalField(source='unit.factor', max_digits=10,
                                         decimal_places=4, read_only=True)

    class Meta:
        model  = ProductUnitPrice
        fields = ['id', 'unit', 'unit_name', 'factor', 'price', 'is_auto', 'is_active']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ['id', 'name', 'icon', 'color', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    category_name  = serializers.CharField(source='category.name', read_only=True)
    base_unit_name = serializers.CharField(source='base_unit.name', read_only=True)
    purchase_unit_name = serializers.CharField(source='purchase_unit.name', read_only=True)
    unit_prices    = ProductUnitPriceSerializer(many=True, read_only=True)
    profit_margin  = serializers.ReadOnlyField()
    is_low_stock   = serializers.ReadOnlyField()

    # stock للقراءة فقط — التعديل عبر StockAdjustment
    stock = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'category', 'category_name',
            'barcode', 'description', 'image_url', 'is_active',
            'price', 'cost', 'stock', 'min_stock',
            'base_unit', 'base_unit_name',
            'purchase_unit', 'purchase_unit_name',
            'unit_prices',
            'profit_margin', 'is_low_stock',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'stock', 'created_at', 'updated_at']


class ProductListSerializer(serializers.ModelSerializer):
    category_name  = serializers.CharField(source='category.name', read_only=True)
    base_unit_name = serializers.CharField(source='base_unit.name', read_only=True)
    unit_prices    = ProductUnitPriceSerializer(many=True, read_only=True)
    is_low_stock   = serializers.ReadOnlyField()

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'category_name', 'barcode',
            'price', 'stock', 'min_stock', 'is_active',
            'base_unit_name', 'unit_prices', 'is_low_stock',
        ]
