#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upgrade_inventory_v2.py  —  النسخة المُصلحة
الاستخدام:  python3 upgrade_inventory_v2.py
"""

import os, sys, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
BE   = os.path.join(BASE, "pos_backend")
FE   = os.path.join(BASE, "pos_frontend", "src", "pages")

def bak(path):
    if os.path.exists(path):
        with open(path,"r",encoding="utf-8") as f: c=f.read()
        with open(path+".bak","w",encoding="utf-8") as f: f.write(c)
        print(f"  📁 backup  {path}.bak")

def write(path, content):
    bak(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w",encoding="utf-8") as f: f.write(content)
    print(f"  ✅ written  {path}")

# ─────────────────────────────────────────────────────────────────────────────
# نستخدم single-quote strings ''' بدل """ لتجنب التعارض
# ─────────────────────────────────────────────────────────────────────────────

MODELS = '''from django.db import models
from django.contrib.auth.models import User
import uuid


class Supplier(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=200, verbose_name="اسم المورد")
    phone      = models.CharField(max_length=20, blank=True, null=True)
    email      = models.EmailField(blank=True, null=True)
    address    = models.TextField(blank=True, null=True)
    notes      = models.TextField(blank=True, null=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مورد"
        verbose_name_plural = "الموردون"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ("draft",     "مسودة"),
        ("ordered",   "تم الطلب"),
        ("partial",   "استلام جزئي"),
        ("received",  "تم الاستلام"),
        ("cancelled", "ملغي"),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(max_length=50, unique=True)
    supplier         = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="purchase_orders"
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name="purchase_orders"
    )
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    total_cost    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes         = models.TextField(blank=True, null=True)
    expected_date = models.DateField(null=True, blank=True)
    received_at   = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "أمر شراء"
        verbose_name_plural = "أوامر الشراء"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PO#{self.reference_number}"

    def recalculate_total(self):
        from django.db.models import Sum, F, DecimalField, ExpressionWrapper
        total = self.items.aggregate(
            total=Sum(ExpressionWrapper(
                F("quantity") * F("unit_cost"),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ))
        )["total"] or 0
        self.total_cost = total
        self.save(update_fields=["total_cost"])

    @property
    def received_percentage(self):
        items = list(self.items.all())
        if not items:
            return 0
        total_ordered  = sum(i.quantity for i in items)
        total_received = sum(i.received_quantity for i in items)
        if total_ordered == 0:
            return 0
        return round((total_received / total_ordered) * 100)


class PurchaseOrderItem(models.Model):
    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order             = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product           = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="purchase_items")
    quantity          = models.PositiveIntegerField()
    received_quantity = models.PositiveIntegerField(default=0)
    unit_cost         = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.unit_cost * self.quantity

    @property
    def remaining_quantity(self):
        return self.quantity - self.received_quantity


class StockAdjustment(models.Model):
    REASON_CHOICES = [
        ("count",  "جرد دوري"),
        ("damage", "تلف"),
        ("loss",   "فقد / سرقة"),
        ("return", "مرتجع من عميل"),
        ("expiry", "انتهاء صلاحية"),
        ("other",  "أخرى"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product         = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="stock_adjustments")
    user            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="stock_adjustments")
    quantity_before = models.IntegerField()
    quantity_change = models.IntegerField()
    quantity_after  = models.IntegerField()
    reason          = models.CharField(max_length=20, choices=REASON_CHOICES, default="count")
    notes           = models.TextField(blank=True, null=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تسوية مخزون"
        verbose_name_plural = "تسويات المخزون"
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.quantity_change >= 0 else ""
        return f"{self.product.name} | {sign}{self.quantity_change}"


class StockAlert(models.Model):
    ALERT_TYPES = [
        ("low",    "مخزون منخفض"),
        ("out",    "نفاد المخزون"),
        ("expiry", "قرب انتهاء الصلاحية"),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product       = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="stock_alerts")
    alert_type    = models.CharField(max_length=20, choices=ALERT_TYPES)
    threshold     = models.IntegerField(default=10)
    current_stock = models.IntegerField()
    is_resolved   = models.BooleanField(default=False)
    resolved_at   = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تنبيه مخزون"
        verbose_name_plural = "تنبيهات المخزون"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_alert_type_display()} — {self.product.name}"


# سجل كل حركة مخزون: شراء / بيع / تسوية / مرتجع
class StockMovement(models.Model):
    MOVE_TYPES = [
        ("sale",       "بيع"),
        ("purchase",   "شراء"),
        ("adjustment", "تسوية"),
        ("return",     "مرتجع"),
        ("initial",    "رصيد أولي"),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product      = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="movements")
    user         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    move_type    = models.CharField(max_length=20, choices=MOVE_TYPES)
    quantity     = models.IntegerField()           # موجب = دخول، سالب = خروج
    stock_before = models.IntegerField()
    stock_after  = models.IntegerField()
    reference    = models.CharField(max_length=100, blank=True, null=True)
    notes        = models.TextField(blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "حركة مخزون"
        verbose_name_plural = "حركات المخزون"
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.quantity >= 0 else ""
        return f"{self.product.name} | {sign}{self.quantity} | {self.get_move_type_display()}"
'''

SERIALIZERS = '''from rest_framework import serializers
from django.db import transaction
from django.db.models import F
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, StockAdjustment, StockAlert, StockMovement
from products.models import Product


class SupplierSerializer(serializers.ModelSerializer):
    orders_count        = serializers.SerializerMethodField()
    total_ordered_value = serializers.SerializerMethodField()

    class Meta:
        model  = Supplier
        fields = ["id","name","phone","email","address","notes","is_active",
                  "orders_count","total_ordered_value","created_at","updated_at"]
        read_only_fields = ["id","created_at","updated_at"]

    def get_orders_count(self, obj):
        return obj.purchase_orders.count()

    def get_total_ordered_value(self, obj):
        from django.db.models import Sum
        total = obj.purchase_orders.aggregate(t=Sum("total_cost"))["t"]
        return float(total or 0)


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name       = serializers.CharField(source="product.name",    read_only=True)
    product_barcode    = serializers.CharField(source="product.barcode", read_only=True)
    product_stock      = serializers.IntegerField(source="product.stock", read_only=True)
    subtotal           = serializers.ReadOnlyField()
    remaining_quantity = serializers.ReadOnlyField()

    class Meta:
        model  = PurchaseOrderItem
        fields = ["id","product","product_name","product_barcode","product_stock",
                  "quantity","received_quantity","unit_cost","subtotal","remaining_quantity"]
        read_only_fields = ["id","received_quantity"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items               = PurchaseOrderItemSerializer(many=True)
    supplier_name       = serializers.CharField(source="supplier.name", read_only=True)
    user_name           = serializers.SerializerMethodField()
    received_percentage = serializers.ReadOnlyField()

    class Meta:
        model  = PurchaseOrder
        fields = ["id","reference_number","supplier","supplier_name","user","user_name",
                  "status","total_cost","notes","expected_date","received_at",
                  "received_percentage","items","created_at","updated_at"]
        read_only_fields = ["id","user","total_cost","received_at","created_at","updated_at"]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username if obj.user else None

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        order = PurchaseOrder.objects.create(**validated_data)
        for item in items_data:
            PurchaseOrderItem.objects.create(order=order, **item)
        order.recalculate_total()
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for item in items_data:
                PurchaseOrderItem.objects.create(order=instance, **item)
            instance.recalculate_total()
        return instance


class StockAdjustmentSerializer(serializers.ModelSerializer):
    product_name   = serializers.CharField(source="product.name", read_only=True)
    user_name      = serializers.SerializerMethodField()
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)

    class Meta:
        model  = StockAdjustment
        fields = ["id","product","product_name","user","user_name",
                  "quantity_before","quantity_change","quantity_after",
                  "reason","reason_display","notes","created_at"]
        read_only_fields = ["id","user","quantity_before","quantity_after","created_at"]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username if obj.user else None

    @transaction.atomic
    def create(self, validated_data):
        product    = validated_data["product"]
        change     = validated_data["quantity_change"]
        qty_before = product.stock
        qty_after  = qty_before + change
        if qty_after < 0:
            raise serializers.ValidationError(
                f"المخزون لا يمكن أن يكون سالباً — المتاح: {qty_before}, التغيير: {change}"
            )
        Product.objects.filter(id=product.id).update(stock=F("stock") + change)
        validated_data["quantity_before"] = qty_before
        validated_data["quantity_after"]  = qty_after
        adj = super().create(validated_data)
        StockMovement.objects.create(
            product=product,
            user=validated_data.get("user"),
            move_type="adjustment",
            quantity=change,
            stock_before=qty_before,
            stock_after=qty_after,
            notes=validated_data.get("notes",""),
        )
        return adj


class StockAlertSerializer(serializers.ModelSerializer):
    product_name       = serializers.CharField(source="product.name",    read_only=True)
    product_barcode    = serializers.CharField(source="product.barcode", read_only=True)
    product_stock      = serializers.IntegerField(source="product.stock", read_only=True)
    alert_type_display = serializers.CharField(source="get_alert_type_display", read_only=True)

    class Meta:
        model  = StockAlert
        fields = ["id","product","product_name","product_barcode","product_stock",
                  "alert_type","alert_type_display","threshold",
                  "current_stock","is_resolved","resolved_at","created_at"]
        read_only_fields = ["id","created_at"]


class StockMovementSerializer(serializers.ModelSerializer):
    product_name      = serializers.CharField(source="product.name",    read_only=True)
    product_barcode   = serializers.CharField(source="product.barcode", read_only=True)
    user_name         = serializers.SerializerMethodField()
    move_type_display = serializers.CharField(source="get_move_type_display", read_only=True)

    class Meta:
        model  = StockMovement
        fields = ["id","product","product_name","product_barcode",
                  "user","user_name","move_type","move_type_display",
                  "quantity","stock_before","stock_after",
                  "reference","notes","created_at"]
        read_only_fields = ["id","created_at"]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username if obj.user else "—"
'''

VIEWS = '''from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from .models import Supplier, PurchaseOrder, StockAdjustment, StockAlert, StockMovement
from .serializers import (
    SupplierSerializer, PurchaseOrderSerializer,
    StockAdjustmentSerializer, StockAlertSerializer, StockMovementSerializer,
)
from products.models import Product


class SupplierViewSet(viewsets.ModelViewSet):
    queryset           = Supplier.objects.all()
    serializer_class   = SupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ["name", "phone", "email"]
    ordering_fields    = ["name", "created_at"]
    ordering           = ["name"]


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related("supplier","user").prefetch_related("items__product").all()
    serializer_class   = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ["status", "supplier"]
    search_fields      = ["reference_number", "supplier__name"]
    ordering           = ["-created_at"]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        order = self.get_object()
        if order.status == "cancelled":
            return Response({"error": "لا يمكن استلام أمر ملغي"}, status=status.HTTP_400_BAD_REQUEST)
        if order.status == "received":
            return Response({"error": "تم استلام هذا الأمر مسبقاً"}, status=status.HTTP_400_BAD_REQUEST)

        received_quantities = request.data.get("received_quantities", {})
        with transaction.atomic():
            for item in order.items.select_related("product").all():
                qty = received_quantities.get(str(item.id), item.remaining_quantity)
                qty = max(0, int(qty))
                if qty > 0:
                    product      = item.product
                    stock_before = product.stock
                    Product.objects.filter(id=product.id).update(
                        stock=F("stock") + qty,
                        cost=item.unit_cost,
                    )
                    product.refresh_from_db()
                    item.received_quantity += qty
                    item.save(update_fields=["received_quantity"])

                    StockAdjustment.objects.create(
                        product=product, user=request.user,
                        quantity_before=stock_before,
                        quantity_change=qty,
                        quantity_after=product.stock,
                        reason="count",
                        notes=f"استلام من أمر شراء #{order.reference_number}",
                    )
                    StockMovement.objects.create(
                        product=product, user=request.user,
                        move_type="purchase", quantity=qty,
                        stock_before=stock_before, stock_after=product.stock,
                        reference=order.reference_number,
                    )

            total_ordered  = sum(i.quantity for i in order.items.all())
            total_received = sum(i.received_quantity for i in order.items.all())
            if total_received >= total_ordered:
                order.status      = "received"
                order.received_at = timezone.now()
            else:
                order.status = "partial"
            order.save(update_fields=["status", "received_at"])

        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status == "received":
            return Response({"error": "لا يمكن إلغاء أمر تم استلامه"}, status=status.HTTP_400_BAD_REQUEST)
        order.status = "cancelled"
        order.save(update_fields=["status"])
        return Response(self.get_serializer(order).data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        qs = PurchaseOrder.objects.all()
        return Response({
            "total":       qs.count(),
            "draft":       qs.filter(status="draft").count(),
            "ordered":     qs.filter(status="ordered").count(),
            "partial":     qs.filter(status="partial").count(),
            "received":    qs.filter(status="received").count(),
            "cancelled":   qs.filter(status="cancelled").count(),
            "total_value": float(qs.aggregate(t=Sum("total_cost"))["t"] or 0),
        })


class StockAdjustmentViewSet(viewsets.ModelViewSet):
    queryset           = StockAdjustment.objects.select_related("product","user").all()
    serializer_class   = StockAdjustmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ["product", "reason"]
    search_fields      = ["product__name", "notes"]
    ordering           = ["-created_at"]
    http_method_names  = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class StockAlertViewSet(viewsets.ModelViewSet):
    queryset           = StockAlert.objects.select_related("product").all()
    serializer_class   = StockAlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ["alert_type", "is_resolved", "product"]
    ordering           = ["-created_at"]
    http_method_names  = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        is_resolved = self.request.query_params.get("is_resolved")
        if is_resolved == "true":
            qs = qs.filter(is_resolved=True)
        elif is_resolved == "false":
            qs = qs.filter(is_resolved=False)
        return qs

    @action(detail=False, methods=["post"])
    def check_and_generate(self, request):
        threshold = int(request.data.get("threshold", 10))
        products  = Product.objects.filter(is_active=True)
        created   = 0
        for product in products:
            if StockAlert.objects.filter(product=product, is_resolved=False).exists():
                continue
            if product.stock == 0:
                StockAlert.objects.create(product=product, alert_type="out",
                                          threshold=threshold, current_stock=0)
                created += 1
            elif product.stock <= threshold:
                StockAlert.objects.create(product=product, alert_type="low",
                                          threshold=threshold, current_stock=product.stock)
                created += 1
        return Response({"created_alerts": created, "checked_products": products.count()})

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert             = self.get_object()
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save(update_fields=["is_resolved", "resolved_at"])
        return Response(self.get_serializer(alert).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        threshold      = int(request.query_params.get("threshold", 10))
        total_products = Product.objects.filter(is_active=True).count()
        out_of_stock   = Product.objects.filter(is_active=True, stock=0).count()
        low_stock      = Product.objects.filter(is_active=True, stock__gt=0, stock__lte=threshold).count()
        unresolved     = StockAlert.objects.filter(is_resolved=False).count()
        total_value    = Product.objects.filter(is_active=True).aggregate(
            tv=Sum(ExpressionWrapper(
                F("stock") * F("cost"),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            ))
        )["tv"] or 0
        return Response({
            "total_products":    total_products,
            "out_of_stock":      out_of_stock,
            "low_stock":         low_stock,
            "healthy_stock":     total_products - out_of_stock - low_stock,
            "unresolved_alerts": unresolved,
            "total_stock_value": float(total_value),
        })


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset           = StockMovement.objects.select_related("product","user").all()
    serializer_class   = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ["product", "move_type"]
    search_fields      = ["product__name", "reference", "notes"]
    ordering           = ["-created_at"]
'''

URLS = '''from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SupplierViewSet, PurchaseOrderViewSet,
    StockAdjustmentViewSet, StockAlertViewSet, StockMovementViewSet,
)

router = DefaultRouter()
router.register("inventory/suppliers",       SupplierViewSet,        basename="supplier")
router.register("inventory/purchase-orders", PurchaseOrderViewSet,   basename="purchase-order")
router.register("inventory/adjustments",     StockAdjustmentViewSet, basename="adjustment")
router.register("inventory/alerts",          StockAlertViewSet,      basename="alert")
router.register("inventory/movements",       StockMovementViewSet,   basename="movement")

urlpatterns = [path("", include(router.urls))]
'''

# JSX — بيستخدم single quotes في Python string لأن JSX نفسه بيستخدم double quotes
JSX = '''import React, { useCallback, useEffect, useState } from 'react';
import { inventoryAPI, productsAPI } from '../services/api';

const fmt  = (n) => Number(n||0).toLocaleString('ar-EG', {minimumFractionDigits:2, maximumFractionDigits:2});
const fmtN = (n) => Number(n||0).toLocaleString('ar-EG');

const COLORS = {
  green:  'bg-green-100 text-green-800 border-green-200',
  red:    'bg-red-100 text-red-800 border-red-200',
  yellow: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  blue:   'bg-blue-100 text-blue-800 border-blue-200',
  gray:   'bg-gray-100 text-gray-600 border-gray-200',
  purple: 'bg-purple-100 text-purple-800 border-purple-200',
};

const Badge = ({ label, color='gray', dot=false }) => (
  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold border ${COLORS[color]||COLORS.gray}`}>
    {dot && <span className={`w-1.5 h-1.5 rounded-full ${color==='green'?'bg-green-500':color==='red'?'bg-red-500':color==='yellow'?'bg-yellow-500':'bg-gray-400'}`}/>}
    {label}
  </span>
);

const Spinner = () => (
  <div className="flex flex-col items-center justify-center h-48 gap-3">
    <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"/>
    <span className="text-gray-400 text-sm font-medium">جاري التحميل...</span>
  </div>
);

const Toast = ({ msg, type, onClose }) => (
  <div className={`fixed top-5 right-5 z-[999] flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl font-bold text-sm text-white
    ${type==='error'?'bg-red-600':type==='warning'?'bg-yellow-500':'bg-emerald-600'}`}>
    <span>{type==='error'?'❌':type==='warning'?'⚠️':'✅'}</span>
    <span>{msg}</span>
    <button onClick={onClose} className="mr-2 opacity-70 hover:opacity-100 text-lg leading-none">×</button>
  </div>
);

const Modal = ({ title, onClose, wide=false, children }) => (
  <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
    <div className={`bg-white rounded-3xl shadow-2xl w-full ${wide?'max-w-4xl':'max-w-2xl'} max-h-[92vh] overflow-y-auto`}
      onClick={e=>e.stopPropagation()}>
      <div className="flex justify-between items-center px-6 py-4 border-b bg-gray-50 rounded-t-3xl">
        <h3 className="font-black text-gray-800 text-lg">{title}</h3>
        <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-200 hover:bg-gray-300 text-gray-600 font-black transition">×</button>
      </div>
      <div className="p-6">{children}</div>
    </div>
  </div>
);

const Field = ({ label, required=false, children }) => (
  <div>
    <label className="block text-xs font-bold text-gray-500 mb-1.5">
      {label}{required && <span className="text-red-500 mr-1">*</span>}
    </label>
    {children}
  </div>
);

const INP = 'w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 bg-white transition';

const KPICard = ({ icon, label, value, color='blue' }) => {
  const bg = { blue:'from-blue-500 to-blue-700', green:'from-emerald-500 to-emerald-700',
               red:'from-red-500 to-red-700', yellow:'from-amber-500 to-amber-700', purple:'from-purple-500 to-purple-700' };
  return (
    <div className={`bg-gradient-to-br ${bg[color]||bg.blue} rounded-2xl p-5 text-white shadow-lg`}>
      <div className="text-3xl mb-2">{icon}</div>
      <div className="text-3xl font-black">{value}</div>
      <div className="text-sm font-semibold opacity-90 mt-1">{label}</div>
    </div>
  );
};

const useToast = () => {
  const [toast, setToast] = useState(null);
  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),4000); };
  const ToastComp = toast ? <Toast msg={toast.msg} type={toast.type} onClose={()=>setToast(null)}/> : null;
  return { notify, ToastComp };
};

const statusMap = {
  draft:     { label:'مسودة',          color:'gray'   },
  ordered:   { label:'تم الطلب',       color:'blue'   },
  partial:   { label:'استلام جزئي',    color:'yellow' },
  received:  { label:'مستلم',          color:'green'  },
  cancelled: { label:'ملغي',           color:'red'    },
};
const alertMap = {
  low:    { label:'مخزون منخفض',  color:'yellow' },
  out:    { label:'نفاد المخزون', color:'red'    },
  expiry: { label:'انتهاء صلاحية',color:'purple' },
};
const moveTypeMap = {
  sale:       { label:'بيع',        color:'red'    },
  purchase:   { label:'شراء',       color:'green'  },
  adjustment: { label:'تسوية',      color:'blue'   },
  return:     { label:'مرتجع',      color:'yellow' },
  initial:    { label:'رصيد أولي',  color:'gray'   },
};

export default function InventoryPage() {
  const [tab, setTab] = useState('summary');
  const tabs = [
    { key:'summary',   label:'📊 الملخص'         },
    { key:'orders',    label:'📦 أوامر الشراء'   },
    { key:'adjust',    label:'⚖️ التسوية'         },
    { key:'movements', label:'🔄 حركات المخزون'  },
    { key:'alerts',    label:'🔔 التنبيهات'      },
    { key:'suppliers', label:'🏭 الموردون'        },
  ];
  return (
    <div dir="rtl" className="min-h-screen bg-gray-50">
      <div className="bg-white border-b px-6 py-4">
        <h1 className="text-xl font-black text-gray-800">🏪 إدارة المخزون</h1>
        <p className="text-gray-400 text-xs mt-0.5">استلام · تسوية · تنبيهات · حركات</p>
      </div>
      <div className="bg-white border-b px-6">
        <div className="flex gap-1 overflow-x-auto">
          {tabs.map(t => (
            <button key={t.key} onClick={()=>setTab(t.key)}
              className={`px-4 py-3 font-bold text-sm whitespace-nowrap border-b-2 transition-all ${
                tab===t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}>{t.label}</button>
          ))}
        </div>
      </div>
      <div className="p-5">
        {tab==='summary'   && <SummaryPanel   />}
        {tab==='orders'    && <OrdersPanel    />}
        {tab==='adjust'    && <AdjustPanel    />}
        {tab==='movements' && <MovementsPanel />}
        {tab==='alerts'    && <AlertsPanel    />}
        {tab==='suppliers' && <SuppliersPanel />}
      </div>
    </div>
  );
}

function SummaryPanel() {
  const [summary, setSummary]     = useState(null);
  const [low, setLow]             = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [quickProd, setQuick]     = useState(null);
  const { notify, ToastComp }     = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, lp, sup] = await Promise.all([
        inventoryAPI.getAlertsSummary({ threshold:10 }),
        productsAPI.getLowStock(),
        inventoryAPI.getSuppliers(),
      ]);
      setSummary(s.data);
      setLow(lp.data?.results || lp.data || []);
      setSuppliers(sup.data?.results || sup.data || []);
    } catch {/**/} finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Spinner />;

  const kpis = [
    { icon:'📦', label:'إجمالي المنتجات',    value: fmtN(summary?.total_products),    color:'blue'   },
    { icon:'✅', label:'مخزون كافي',          value: fmtN(summary?.healthy_stock),     color:'green'  },
    { icon:'⚠️', label:'مخزون منخفض',        value: fmtN(summary?.low_stock),         color:'yellow' },
    { icon:'🚨', label:'نفاد المخزون',        value: fmtN(summary?.out_of_stock),      color:'red'    },
    { icon:'💰', label:'قيمة المخزون (ج)',    value: fmt(summary?.total_stock_value),  color:'purple' },
    { icon:'🔔', label:'تنبيهات غير محلولة', value: fmtN(summary?.unresolved_alerts), color:'red'    },
  ];

  return (
    <div className="space-y-6">
      {ToastComp}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {kpis.map(k => <KPICard key={k.label} {...k} />)}
      </div>
      <button onClick={async()=>{ await inventoryAPI.checkAndGenerateAlerts({threshold:10}); load(); notify('تم فحص التنبيهات'); }}
        className="bg-amber-500 hover:bg-amber-600 text-white font-bold px-5 py-2.5 rounded-xl text-sm shadow transition">
        🔄 فحص وتحديث التنبيهات
      </button>
      {low.length > 0 && (
        <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b bg-amber-50 flex items-center justify-between">
            <h2 className="font-black text-amber-800">⚠️ منتجات تحتاج إعادة طلب</h2>
            <Badge label={`${low.length} منتج`} color="yellow"/>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-gray-500 text-right text-xs border-b">
                  <th className="px-4 py-3">المنتج</th><th className="px-4 py-3">الباركود</th>
                  <th className="px-4 py-3">المخزون</th><th className="px-4 py-3">سعر البيع</th>
                  <th className="px-4 py-3">التكلفة</th><th className="px-4 py-3">إجراء</th>
                </tr>
              </thead>
              <tbody>
                {low.map(p => (
                  <tr key={p.id} className="border-t hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-bold text-gray-800">{p.name}</td>
                    <td className="px-4 py-3 text-gray-400 font-mono text-xs">{p.barcode||'—'}</td>
                    <td className="px-4 py-3">
                      <span className={`font-black text-base ${p.stock===0?'text-red-600':'text-amber-600'}`}>{p.stock}</span>
                    </td>
                    <td className="px-4 py-3 font-semibold">{fmt(p.price)} ج</td>
                    <td className="px-4 py-3 text-gray-500">{fmt(p.cost)} ج</td>
                    <td className="px-4 py-3">
                      <button onClick={()=>setQuick(p)}
                        className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition shadow-sm">
                        📦 طلب شراء
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {quickProd && (
        <QuickOrderModal product={quickProd} suppliers={suppliers}
          onClose={()=>setQuick(null)}
          onSaved={()=>{ setQuick(null); notify('✅ تم إنشاء طلب الشراء'); load(); }}
          onError={msg=>notify(msg,'error')} />
      )}
    </div>
  );
}

function OrdersPanel() {
  const [orders, setOrders]             = useState([]);
  const [suppliers, setSuppliers]       = useState([]);
  const [products, setProducts]         = useState([]);
  const [loading, setLoading]           = useState(true);
  const [showNew, setShowNew]           = useState(false);
  const [receiving, setReceiving]       = useState(null);
  const [search, setSearch]             = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const { notify, ToastComp }           = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      const [o,s,p] = await Promise.all([
        inventoryAPI.getPurchaseOrders(params),
        inventoryAPI.getSuppliers(),
        productsAPI.getAll({ page_size:500 }),
      ]);
      setOrders(o.data?.results||o.data||[]);
      setSuppliers(s.data?.results||s.data||[]);
      setProducts(p.data?.results||p.data||[]);
    } catch {/**/} finally { setLoading(false); }
  }, [search, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleCancel = async (id) => {
    if (!window.confirm('إلغاء هذا الأمر؟')) return;
    try { await inventoryAPI.cancelPurchaseOrder(id); notify('تم الإلغاء'); load(); }
    catch(e) { notify(e?.response?.data?.error||'خطأ','error'); }
  };

  const handleReceive = async (order, qtys) => {
    try {
      await inventoryAPI.receivePurchaseOrder(order.id, { received_quantities: qtys });
      notify('✅ تم استلام البضاعة وتحديث المخزون');
      setReceiving(null); load();
    } catch(e) { notify(e?.response?.data?.error||'خطأ في الاستلام','error'); }
  };

  return (
    <div className="space-y-4">
      {ToastComp}
      <div className="bg-white rounded-2xl border shadow-sm p-4 flex flex-wrap gap-3 items-center justify-between">
        <div className="flex gap-3 flex-wrap flex-1">
          <input value={search} onChange={e=>setSearch(e.target.value)}
            placeholder="🔍 بحث برقم المرجع أو المورد..."
            className={INP+' max-w-xs'} />
          <select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)} className={INP+' w-44'}>
            <option value="">كل الحالات</option>
            {Object.entries(statusMap).map(([k,v])=><option key={k} value={k}>{v.label}</option>)}
          </select>
        </div>
        <button onClick={()=>setShowNew(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2.5 rounded-xl text-sm shadow transition">
          ➕ أمر شراء جديد
        </button>
      </div>
      {loading ? <Spinner /> : (
        <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-gray-500 text-right text-xs border-b">
                  <th className="px-4 py-3">المرجع</th><th className="px-4 py-3">المورد</th>
                  <th className="px-4 py-3">الحالة</th><th className="px-4 py-3">التقدم</th>
                  <th className="px-4 py-3">الإجمالي</th><th className="px-4 py-3">التاريخ المتوقع</th>
                  <th className="px-4 py-3">إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {orders.length===0 && (
                  <tr><td colSpan={7} className="text-center py-12 text-gray-400">
                    <div className="text-4xl mb-2">📭</div>لا توجد أوامر شراء
                  </td></tr>
                )}
                {orders.map(o => {
                  const st  = statusMap[o.status]||{label:o.status,color:'gray'};
                  const pct = o.received_percentage||0;
                  return (
                    <tr key={o.id} className="border-t hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-black text-blue-700">{o.reference_number}</td>
                      <td className="px-4 py-3 text-gray-600">{o.supplier_name||'—'}</td>
                      <td className="px-4 py-3"><Badge label={st.label} color={st.color} dot/></td>
                      <td className="px-4 py-3 w-32">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                            <div className={`h-1.5 rounded-full transition-all ${pct===100?'bg-green-500':pct>0?'bg-blue-500':'bg-gray-300'}`}
                              style={{width:`${pct}%`}}/>
                          </div>
                          <span className="text-xs text-gray-500 w-8">{pct}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-bold">{fmt(o.total_cost)} ج</td>
                      <td className="px-4 py-3 text-gray-500">{o.expected_date||'—'}</td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          {(o.status==='ordered'||o.status==='draft'||o.status==='partial') && (
                            <button onClick={()=>setReceiving(o)}
                              className="bg-green-500 hover:bg-green-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-sm transition">
                              📥 استلام
                            </button>
                          )}
                          {o.status!=='received'&&o.status!=='cancelled' && (
                            <button onClick={()=>handleCancel(o.id)}
                              className="bg-red-100 hover:bg-red-200 text-red-700 text-xs font-bold px-3 py-1.5 rounded-lg transition">
                              ❌ إلغاء
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {showNew && (
        <NewOrderModal suppliers={suppliers} products={products}
          onClose={()=>setShowNew(false)}
          onSaved={()=>{ setShowNew(false); load(); notify('✅ تم إنشاء الأمر'); }}
          onError={msg=>notify(msg,'error')} />
      )}
      {receiving && (
        <ReceiveModal order={receiving} onClose={()=>setReceiving(null)} onReceive={handleReceive} />
      )}
    </div>
  );
}

function NewOrderModal({ suppliers, products, onClose, onSaved, onError }) {
  const [form, setForm] = useState({
    reference_number:`PO-${Date.now()}`, supplier:'', expected_date:'', notes:'', status:'ordered',
  });
  const [items, setItems] = useState([{ product:'', quantity:1, unit_cost:'' }]);
  const [saving, setSaving] = useState(false);

  const addItem    = () => setItems([...items, { product:'', quantity:1, unit_cost:'' }]);
  const removeItem = i  => setItems(items.filter((_,idx)=>idx!==i));
  const upd        = (i,f,v) => { const n=[...items]; n[i]={...n[i],[f]:v}; setItems(n); };
  const total = items.reduce((s,it)=>s+(Number(it.quantity)||0)*(Number(it.unit_cost)||0),0);

  const save = async () => {
    if (!form.reference_number) return onError('رقم المرجع مطلوب');
    const valid = items.filter(it=>it.product&&it.quantity>0&&it.unit_cost);
    if (!valid.length) return onError('أضف منتجاً على الأقل');
    setSaving(true);
    try {
      await inventoryAPI.createPurchaseOrder({
        ...form, supplier:form.supplier||null,
        items:valid.map(it=>({...it, quantity:Number(it.quantity), unit_cost:Number(it.unit_cost)}))
      });
      onSaved();
    } catch(e) { onError(JSON.stringify(e?.response?.data||'خطأ')); }
    finally { setSaving(false); }
  };

  return (
    <Modal title="➕ أمر شراء جديد" onClose={onClose} wide>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <Field label="رقم المرجع" required><input className={INP} value={form.reference_number} onChange={e=>setForm({...form,reference_number:e.target.value})}/></Field>
          <Field label="المورد">
            <select className={INP} value={form.supplier} onChange={e=>setForm({...form,supplier:e.target.value})}>
              <option value="">بدون مورد</option>
              {suppliers.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="تاريخ الاستلام المتوقع"><input type="date" className={INP} value={form.expected_date} onChange={e=>setForm({...form,expected_date:e.target.value})}/></Field>
          <Field label="الحالة">
            <select className={INP} value={form.status} onChange={e=>setForm({...form,status:e.target.value})}>
              <option value="draft">مسودة</option><option value="ordered">تم الطلب</option>
            </select>
          </Field>
        </div>
        <Field label="ملاحظات"><textarea className={INP} rows={2} value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})}/></Field>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="flex justify-between items-center mb-3">
            <span className="font-bold text-gray-700">المنتجات</span>
            <button onClick={addItem} className="text-blue-600 text-sm font-bold hover:underline">+ إضافة</button>
          </div>
          <div className="space-y-2">
            {items.map((item,i)=>(
              <div key={i} className="flex gap-2 items-center bg-white p-2 rounded-lg border">
                <div className="flex-1">
                  <select className={INP+' text-xs'} value={item.product} onChange={e=>upd(i,'product',e.target.value)}>
                    <option value="">اختر منتج</option>
                    {products.map(p=><option key={p.id} value={p.id}>{p.name} (مخزون: {p.stock})</option>)}
                  </select>
                </div>
                <input type="number" className={INP+' w-20 text-xs text-center'} placeholder="كمية" min={1} value={item.quantity} onChange={e=>upd(i,'quantity',e.target.value)}/>
                <input type="number" className={INP+' w-24 text-xs text-center'} placeholder="تكلفة" min={0} step="0.01" value={item.unit_cost} onChange={e=>upd(i,'unit_cost',e.target.value)}/>
                <span className="text-xs text-gray-400 w-20 text-center">{fmt((Number(item.quantity)||0)*(Number(item.unit_cost)||0))} ج</span>
                <button onClick={()=>removeItem(i)} className="text-red-400 hover:text-red-600 font-black text-lg px-1">×</button>
              </div>
            ))}
          </div>
          {total>0 && (
            <div className="mt-3 pt-3 border-t flex justify-between font-black text-gray-700">
              <span>الإجمالي:</span>
              <span className="text-blue-700 text-lg">{fmt(total)} ج</span>
            </div>
          )}
        </div>
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-5 py-2.5 rounded-xl border font-bold text-sm text-gray-600">إلغاء</button>
          <button onClick={save} disabled={saving} className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-6 py-2.5 rounded-xl text-sm shadow transition">{saving?'...':'💾 حفظ الأمر'}</button>
        </div>
      </div>
    </Modal>
  );
}

function ReceiveModal({ order, onClose, onReceive }) {
  const [qtys, setQtys] = useState({});
  const [busy, setBusy] = useState(false);
  useEffect(()=>{
    const init={};
    (order.items||[]).forEach(it=>{ init[it.id]=it.remaining_quantity??it.quantity; });
    setQtys(init);
  },[order]);
  const submit = async () => { setBusy(true); await onReceive(order,qtys); setBusy(false); };
  return (
    <Modal title={`📥 استلام أمر #${order.reference_number}`} onClose={onClose} wide>
      <div className="space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-gray-500 text-right text-xs border-b">
                <th className="px-3 py-2">المنتج</th><th className="px-3 py-2">مخزون حالي</th>
                <th className="px-3 py-2">مطلوب</th><th className="px-3 py-2">مستلم سابقاً</th>
                <th className="px-3 py-2">مستلم الآن</th>
              </tr>
            </thead>
            <tbody>
              {(order.items||[]).map(it=>(
                <tr key={it.id} className="border-t">
                  <td className="px-3 py-2.5 font-bold">{it.product_name}</td>
                  <td className="px-3 py-2.5 text-gray-500">{it.product_stock??'—'}</td>
                  <td className="px-3 py-2.5 font-bold">{it.quantity}</td>
                  <td className="px-3 py-2.5 text-green-600 font-bold">{it.received_quantity}</td>
                  <td className="px-3 py-2.5">
                    <input type="number" min={0} max={it.remaining_quantity}
                      value={qtys[it.id]??it.remaining_quantity}
                      onChange={e=>setQtys({...qtys,[it.id]:Number(e.target.value)})}
                      className={INP+' w-24 text-center'}/>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-5 py-2.5 rounded-xl border font-bold text-sm text-gray-600">إلغاء</button>
          <button onClick={submit} disabled={busy} className="bg-green-600 hover:bg-green-700 text-white font-bold px-6 py-2.5 rounded-xl text-sm shadow transition">{busy?'...':'📥 تأكيد الاستلام'}</button>
        </div>
      </div>
    </Modal>
  );
}

function AdjustPanel() {
  const [adjs, setAdjs]         = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [form, setForm]         = useState({ product:'', quantity_change:'', reason:'count', notes:'' });
  const [saving, setSaving]     = useState(false);
  const { notify, ToastComp }   = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a,p] = await Promise.all([inventoryAPI.getAdjustments(), productsAPI.getAll({page_size:500})]);
      setAdjs(a.data?.results||a.data||[]);
      setProducts(p.data?.results||p.data||[]);
    } catch {/**/} finally { setLoading(false); }
  },[]);
  useEffect(()=>{ load(); },[load]);

  const save = async () => {
    if (!form.product||!form.quantity_change) return notify('اختر المنتج وأدخل الكمية','error');
    setSaving(true);
    try {
      await inventoryAPI.createAdjustment({ product:form.product, quantity_change:Number(form.quantity_change), reason:form.reason, notes:form.notes });
      notify('✅ تمت التسوية');
      setForm({ product:'', quantity_change:'', reason:'count', notes:'' });
      load();
    } catch(e) { notify(e?.response?.data?.[0]||JSON.stringify(e?.response?.data)||'خطأ','error'); }
    finally { setSaving(false); }
  };

  const reasons = { count:'جرد دوري', damage:'تلف', loss:'فقد/سرقة', return:'مرتجع', expiry:'انتهاء صلاحية', other:'أخرى' };
  const selProd = products.find(p=>p.id===form.product);

  return (
    <div className="space-y-5">
      {ToastComp}
      <div className="bg-white rounded-2xl border shadow-sm p-5">
        <h2 className="font-black text-gray-700 mb-4 text-lg">⚖️ تسوية مخزون جديدة</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <Field label="المنتج" required>
            <select className={INP} value={form.product} onChange={e=>setForm({...form,product:e.target.value})}>
              <option value="">اختر منتج</option>
              {products.map(p=><option key={p.id} value={p.id}>{p.name} (مخزون: {p.stock})</option>)}
            </select>
          </Field>
          <Field label="الكمية (+ أو -)" required>
            <input type="number" className={INP} placeholder="10 أو -5" value={form.quantity_change} onChange={e=>setForm({...form,quantity_change:e.target.value})}/>
          </Field>
          <Field label="السبب">
            <select className={INP} value={form.reason} onChange={e=>setForm({...form,reason:e.target.value})}>
              {Object.entries(reasons).map(([k,v])=><option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
          <Field label="ملاحظات">
            <input className={INP} value={form.notes} placeholder="اختياري" onChange={e=>setForm({...form,notes:e.target.value})}/>
          </Field>
        </div>
        {selProd && form.quantity_change && (
          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 flex gap-6 text-sm">
            <span>قبل: <strong>{selProd.stock}</strong></span>
            <span>التغيير: <strong className={Number(form.quantity_change)>=0?'text-green-600':'text-red-600'}>{Number(form.quantity_change)>=0?'+':''}{form.quantity_change}</strong></span>
            <span>بعد: <strong className={selProd.stock+Number(form.quantity_change)<0?'text-red-600':'text-blue-700'}>{selProd.stock+Number(form.quantity_change)}</strong></span>
          </div>
        )}
        <button onClick={save} disabled={saving} className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-bold px-6 py-2.5 rounded-xl text-sm shadow transition">{saving?'...':'💾 تطبيق التسوية'}</button>
      </div>
      {loading ? <Spinner /> : (
        <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b bg-gray-50 font-black text-gray-700">سجل التسويات</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-50 text-gray-500 text-right text-xs border-b">
                <th className="px-4 py-3">المنتج</th><th className="px-4 py-3">قبل</th>
                <th className="px-4 py-3">التغيير</th><th className="px-4 py-3">بعد</th>
                <th className="px-4 py-3">السبب</th><th className="px-4 py-3">الموظف</th>
                <th className="px-4 py-3">التاريخ</th>
              </tr></thead>
              <tbody>
                {adjs.length===0 && <tr><td colSpan={7} className="text-center py-10 text-gray-400"><div className="text-3xl mb-1">📋</div>لا توجد تسويات</td></tr>}
                {adjs.map(a=>(
                  <tr key={a.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-3 font-bold">{a.product_name}</td>
                    <td className="px-4 py-3 text-gray-500">{a.quantity_before}</td>
                    <td className="px-4 py-3"><span className={`font-black ${a.quantity_change>=0?'text-green-600':'text-red-600'}`}>{a.quantity_change>=0?'+':''}{a.quantity_change}</span></td>
                    <td className="px-4 py-3 font-bold">{a.quantity_after}</td>
                    <td className="px-4 py-3"><Badge label={a.reason_display} color="blue"/></td>
                    <td className="px-4 py-3 text-gray-500">{a.user_name||'—'}</td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{a.created_at?.split('T')[0]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function MovementsPanel() {
  const [moves, setMoves]       = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [typeFilter, setType]   = useState('');
  const [prodFilter, setProd]   = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (typeFilter) params.move_type = typeFilter;
      if (prodFilter) params.product   = prodFilter;
      const [m,p] = await Promise.all([inventoryAPI.getMovements(params), productsAPI.getAll({page_size:500})]);
      setMoves(m.data?.results||m.data||[]);
      setProducts(p.data?.results||p.data||[]);
    } catch {/**/} finally { setLoading(false); }
  },[typeFilter,prodFilter]);
  useEffect(()=>{ load(); },[load]);

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-2xl border shadow-sm p-4 flex flex-wrap gap-3">
        <select value={typeFilter} onChange={e=>setType(e.target.value)} className={INP+' w-44'}>
          <option value="">كل الأنواع</option>
          {Object.entries(moveTypeMap).map(([k,v])=><option key={k} value={k}>{v.label}</option>)}
        </select>
        <select value={prodFilter} onChange={e=>setProd(e.target.value)} className={INP+' w-56'}>
          <option value="">كل المنتجات</option>
          {products.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>
      {loading ? <Spinner /> : (
        <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-50 text-gray-500 text-right text-xs border-b">
                <th className="px-4 py-3">المنتج</th><th className="px-4 py-3">النوع</th>
                <th className="px-4 py-3">الكمية</th><th className="px-4 py-3">قبل</th>
                <th className="px-4 py-3">بعد</th><th className="px-4 py-3">المرجع</th>
                <th className="px-4 py-3">الموظف</th><th className="px-4 py-3">التاريخ</th>
              </tr></thead>
              <tbody>
                {moves.length===0 && <tr><td colSpan={8} className="text-center py-12 text-gray-400"><div className="text-4xl mb-2">📊</div>لا توجد حركات</td></tr>}
                {moves.map(m=>{
                  const mt=moveTypeMap[m.move_type]||{label:m.move_type,color:'gray'};
                  return (
                    <tr key={m.id} className="border-t hover:bg-gray-50">
                      <td className="px-4 py-3 font-bold">{m.product_name}</td>
                      <td className="px-4 py-3"><Badge label={mt.label} color={mt.color} dot/></td>
                      <td className="px-4 py-3"><span className={`font-black ${m.quantity>=0?'text-green-600':'text-red-600'}`}>{m.quantity>=0?'+':''}{m.quantity}</span></td>
                      <td className="px-4 py-3 text-gray-500">{m.stock_before}</td>
                      <td className="px-4 py-3 font-bold">{m.stock_after}</td>
                      <td className="px-4 py-3 text-gray-400 font-mono text-xs">{m.reference||'—'}</td>
                      <td className="px-4 py-3 text-gray-500">{m.user_name||'—'}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{m.created_at?.split('T')[0]}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function AlertsPanel() {
  const [alerts, setAlerts]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter]   = useState('active');
  const { notify, ToastComp } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = filter==='all' ? {} : { is_resolved: filter==='resolved' ? 'true' : 'false' };
      const res = await inventoryAPI.getAlerts(params);
      setAlerts(res.data?.results||res.data||[]);
    } catch {/**/} finally { setLoading(false); }
  },[filter]);
  useEffect(()=>{ load(); },[load]);

  const resolve = async (id) => {
    try { await inventoryAPI.resolveAlert(id); notify('تم حل التنبيه'); load(); }
    catch { notify('خطأ','error'); }
  };

  return (
    <div className="space-y-4">
      {ToastComp}
      <div className="flex gap-2">
        {[['all','الكل'],['active','🔴 نشطة'],['resolved','✅ محلولة']].map(([f,l])=>(
          <button key={f} onClick={()=>setFilter(f)}
            className={`px-4 py-2 rounded-xl text-sm font-bold transition ${filter===f?'bg-blue-600 text-white shadow':'bg-white border text-gray-600 hover:bg-gray-50'}`}>{l}</button>
        ))}
      </div>
      {loading ? <Spinner /> : (
        <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-50 text-gray-500 text-right text-xs border-b">
                <th className="px-4 py-3">المنتج</th><th className="px-4 py-3">الباركود</th>
                <th className="px-4 py-3">نوع التنبيه</th><th className="px-4 py-3">مخزون وقت التنبيه</th>
                <th className="px-4 py-3">المخزون الحالي</th><th className="px-4 py-3">الحد</th>
                <th className="px-4 py-3">الحالة</th><th className="px-4 py-3">التاريخ</th>
                <th className="px-4 py-3">إجراء</th>
              </tr></thead>
              <tbody>
                {alerts.length===0 && <tr><td colSpan={9} className="text-center py-12 text-gray-400"><div className="text-4xl mb-2">🔔</div>لا توجد تنبيهات</td></tr>}
                {alerts.map(a=>{
                  const at=alertMap[a.alert_type]||{label:a.alert_type,color:'gray'};
                  return (
                    <tr key={a.id} className="border-t hover:bg-gray-50">
                      <td className="px-4 py-3 font-bold">{a.product_name}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-400">{a.product_barcode||'—'}</td>
                      <td className="px-4 py-3"><Badge label={at.label} color={at.color} dot/></td>
                      <td className="px-4 py-3 font-black text-red-600">{a.current_stock}</td>
                      <td className="px-4 py-3 font-bold">{a.product_stock??'—'}</td>
                      <td className="px-4 py-3 text-gray-500">{a.threshold}</td>
                      <td className="px-4 py-3"><Badge label={a.is_resolved?'محلول':'نشط'} color={a.is_resolved?'green':'red'} dot/></td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{a.created_at?.split('T')[0]}</td>
                      <td className="px-4 py-3">
                        {!a.is_resolved && (
                          <button onClick={()=>resolve(a.id)}
                            className="bg-emerald-100 hover:bg-emerald-200 text-emerald-700 text-xs font-bold px-3 py-1.5 rounded-lg transition">
                            ✅ حل
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function SuppliersPanel() {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [editing, setEditing]     = useState(null);
  const [showForm, setShowForm]   = useState(false);
  const { notify, ToastComp }     = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try { const r=await inventoryAPI.getSuppliers(); setSuppliers(r.data?.results||r.data||[]); }
    catch {/**/} finally { setLoading(false); }
  },[]);
  useEffect(()=>{ load(); },[load]);

  const save = async (data) => {
    try {
      if (editing) await inventoryAPI.updateSupplier(editing.id,data);
      else         await inventoryAPI.createSupplier(data);
      notify('✅ تم الحفظ'); setShowForm(false); setEditing(null); load();
    } catch(e) { notify(JSON.stringify(e?.response?.data||'خطأ'),'error'); }
  };
  const del = async (id) => {
    if (!window.confirm('حذف المورد؟')) return;
    try { await inventoryAPI.deleteSupplier(id); notify('تم الحذف'); load(); }
    catch { notify('خطأ في الحذف','error'); }
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      {ToastComp}
      <div className="flex justify-between items-center">
        <h2 className="font-black text-gray-700 text-lg">🏭 الموردون</h2>
        <button onClick={()=>{ setEditing(null); setShowForm(true); }}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2.5 rounded-xl text-sm shadow transition">
          ➕ مورد جديد
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {suppliers.length===0 && <div className="col-span-3 text-center py-12 text-gray-400"><div className="text-4xl mb-2">🏭</div>لا يوجد موردون</div>}
        {suppliers.map(s=>(
          <div key={s.id} className="bg-white rounded-2xl border shadow-sm p-5 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-3">
              <div>
                <div className="font-black text-gray-800 text-lg">{s.name}</div>
                <Badge label={s.is_active?'نشط':'غير نشط'} color={s.is_active?'green':'gray'} dot/>
              </div>
              <div className="flex gap-2">
                <button onClick={()=>{ setEditing(s); setShowForm(true); }} className="w-8 h-8 flex items-center justify-center rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-600 transition">✏️</button>
                <button onClick={()=>del(s.id)} className="w-8 h-8 flex items-center justify-center rounded-lg bg-red-50 hover:bg-red-100 text-red-500 transition">🗑️</button>
              </div>
            </div>
            <div className="space-y-1 text-sm text-gray-500">
              {s.phone   && <div>📞 {s.phone}</div>}
              {s.email   && <div>✉️ {s.email}</div>}
              {s.address && <div>📍 {s.address}</div>}
            </div>
            <div className="mt-3 pt-3 border-t flex justify-between text-xs">
              <span className="text-blue-600 font-bold">{s.orders_count} أمر شراء</span>
              <span className="text-gray-500">{fmt(s.total_ordered_value)} ج إجمالي</span>
            </div>
          </div>
        ))}
      </div>
      {showForm && <SupplierModal initial={editing} onClose={()=>{ setShowForm(false); setEditing(null); }} onSave={save}/>}
    </div>
  );
}

function SupplierModal({ initial, onClose, onSave }) {
  const [form, setForm] = useState({ name:'', phone:'', email:'', address:'', notes:'', is_active:true, ...initial });
  const [saving, setSaving] = useState(false);
  const handle = async () => { setSaving(true); await onSave(form); setSaving(false); };
  return (
    <Modal title={initial?'✏️ تعديل المورد':'➕ مورد جديد'} onClose={onClose}>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="الاسم" required><input className={INP} value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></Field>
          <Field label="الهاتف"><input className={INP} value={form.phone||''} onChange={e=>setForm({...form,phone:e.target.value})}/></Field>
          <Field label="البريد الإلكتروني"><input className={INP} value={form.email||''} onChange={e=>setForm({...form,email:e.target.value})}/></Field>
          <Field label="العنوان"><input className={INP} value={form.address||''} onChange={e=>setForm({...form,address:e.target.value})}/></Field>
        </div>
        <Field label="ملاحظات"><textarea className={INP} rows={2} value={form.notes||''} onChange={e=>setForm({...form,notes:e.target.value})}/></Field>
        <label className="flex items-center gap-2 text-sm font-bold text-gray-600 cursor-pointer">
          <input type="checkbox" checked={form.is_active} onChange={e=>setForm({...form,is_active:e.target.checked})} className="w-4 h-4 rounded"/>
          مورد نشط
        </label>
        <div className="flex gap-3 justify-end pt-2">
          <button onClick={onClose} className="px-5 py-2.5 rounded-xl border font-bold text-sm text-gray-600">إلغاء</button>
          <button onClick={handle} disabled={saving} className="bg-blue-600 text-white font-bold px-6 py-2.5 rounded-xl text-sm shadow">{saving?'...':'💾 حفظ'}</button>
        </div>
      </div>
    </Modal>
  );
}

function QuickOrderModal({ product, suppliers, onClose, onSaved, onError }) {
  const [form, setForm] = useState({
    reference_number:`PO-${Date.now()}`, supplier:'', expected_date:'', notes:'', status:'ordered',
  });
  const [quantity, setQty]  = useState(10);
  const [unit_cost, setCost]= useState(product.cost||'');
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!quantity||Number(quantity)<=0) return onError('الكمية يجب أن تكون أكبر من صفر');
    if (!unit_cost||Number(unit_cost)<=0) return onError('أدخل تكلفة الوحدة');
    setSaving(true);
    try {
      await inventoryAPI.createPurchaseOrder({
        ...form, supplier:form.supplier||null,
        items:[{ product:product.id, quantity:Number(quantity), unit_cost:Number(unit_cost) }],
      });
      onSaved();
    } catch(e) { onError(JSON.stringify(e?.response?.data||'خطأ')); }
    finally { setSaving(false); }
  };

  return (
    <Modal title="📦 طلب شراء سريع" onClose={onClose}>
      <div className="space-y-4">
        <div className={`rounded-xl p-3 flex gap-3 items-center border ${product.stock===0?'bg-red-50 border-red-200':'bg-amber-50 border-amber-200'}`}>
          <div className="text-3xl">{product.stock===0?'🚨':'⚠️'}</div>
          <div>
            <div className="font-black text-gray-800">{product.name}</div>
            <div className="text-xs text-gray-500 mt-0.5">
              {product.barcode && `باركود: ${product.barcode} · `}
              المخزون الحالي: <span className={`font-black ${product.stock===0?'text-red-600':'text-amber-600'}`}>{product.stock}</span>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="رقم المرجع" required><input className={INP} value={form.reference_number} onChange={e=>setForm({...form,reference_number:e.target.value})}/></Field>
          <Field label="المورد">
            <select className={INP} value={form.supplier} onChange={e=>setForm({...form,supplier:e.target.value})}>
              <option value="">بدون مورد</option>
              {suppliers.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="الكمية المطلوبة" required><input type="number" min={1} className={INP} value={quantity} onChange={e=>setQty(e.target.value)}/></Field>
          <Field label="تكلفة الوحدة" required><input type="number" min={0} step="0.01" className={INP} value={unit_cost} onChange={e=>setCost(e.target.value)}/></Field>
          <Field label="تاريخ الاستلام"><input type="date" className={INP} value={form.expected_date} onChange={e=>setForm({...form,expected_date:e.target.value})}/></Field>
          <Field label="الحالة">
            <select className={INP} value={form.status} onChange={e=>setForm({...form,status:e.target.value})}>
              <option value="draft">مسودة</option><option value="ordered">تم الطلب</option>
            </select>
          </Field>
        </div>
        {Number(quantity)>0&&Number(unit_cost)>0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 flex justify-between text-sm">
            <span className="text-gray-600 font-bold">إجمالي التكلفة المتوقعة:</span>
            <span className="font-black text-blue-700 text-base">{fmt(Number(quantity)*Number(unit_cost))} ج</span>
          </div>
        )}
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-5 py-2.5 rounded-xl border font-bold text-sm text-gray-600">إلغاء</button>
          <button onClick={save} disabled={saving} className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-6 py-2.5 rounded-xl text-sm shadow transition">{saving?'...':'💾 إنشاء الطلب'}</button>
        </div>
      </div>
    </Modal>
  );
}
'''

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
print("\n🚀 upgrade_inventory_v2  (fixed)")
print("="*45)

print("\n📦 Backend...")
write(os.path.join(BE,"inventory","models.py"),      MODELS)
write(os.path.join(BE,"inventory","serializers.py"), SERIALIZERS)
write(os.path.join(BE,"inventory","views.py"),       VIEWS)
write(os.path.join(BE,"inventory","urls.py"),        URLS)

print("\n🎨 Frontend...")
write(os.path.join(FE,"InventoryPage.jsx"), JSX)

# patch api.js
API_PATH = os.path.join(BASE,"pos_frontend","src","services","api.js")
if os.path.exists(API_PATH):
    with open(API_PATH,"r",encoding="utf-8") as f: api_src=f.read()
    if "getMovements" in api_src:
        print("  ⚠️  getMovements موجود بالفعل")
    else:
        bak(API_PATH)
        old_chunk = "  // Alerts\n  getAlerts:"
        new_chunk = "  // Movements\n  getMovements: (params) => api.get('/inventory/movements/', { params }),\n\n  // Alerts\n  getAlerts:"
        if old_chunk in api_src:
            api_src = api_src.replace(old_chunk, new_chunk)
            with open(API_PATH,"w",encoding="utf-8") as f: f.write(api_src)
            print("  ✅ getMovements أُضيف لـ api.js")
        else:
            print("  ⚠️  أضف getMovements يدوياً في inventoryAPI داخل api.js")

print("\n⚙️  Migrations...")
try:
    for cmd in [["python","manage.py","makemigrations","inventory"],["python","manage.py","migrate"]]:
        r = subprocess.run(cmd, cwd=BE, capture_output=True, text=True)
        out = (r.stdout+r.stderr).strip()
        print("  " + out[-300:] if out else "  OK")
except Exception as ex:
    print(f"  ❌ {ex}")
    print("  شغّل يدوياً: cd pos_backend && python manage.py makemigrations inventory && python manage.py migrate")

print("""
🎉  اكتمل!
  cd pos_backend  && python manage.py runserver
  cd pos_frontend && npm run dev
""")
