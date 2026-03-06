from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, StockAdjustment, StockAlert


class PurchaseOrderItemInline(admin.TabularInline):
    model       = PurchaseOrderItem
    extra       = 0
    readonly_fields = ['received_quantity']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display  = ['name', 'phone', 'email', 'is_active', 'created_at']
    search_fields = ['name', 'phone', 'email']
    list_filter   = ['is_active']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display    = ['reference_number','supplier','status','total_cost','user','created_at']
    list_filter     = ['status', 'supplier']
    search_fields   = ['reference_number', 'supplier__name']
    inlines         = [PurchaseOrderItemInline]
    readonly_fields = ['total_cost','received_at','created_at','updated_at']


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display    = ['product','quantity_before','quantity_change','quantity_after','reason','user','created_at']
    list_filter     = ['reason', 'created_at']
    search_fields   = ['product__name', 'notes']
    readonly_fields = ['quantity_before','quantity_after','created_at']


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display  = ['product','alert_type','current_stock','threshold','is_resolved','created_at']
    list_filter   = ['alert_type', 'is_resolved']
    search_fields = ['product__name']
