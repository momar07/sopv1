#!/usr/bin/env python3
# fix_return_price.py — إصلاح خطأ 400: price مطلوب

import shutil
from pathlib import Path

BASE = Path(__file__).parent
FILE = BASE / 'pos_backend/sales/serializers_returns.py'

print('\n=== fix_return_price.py ===\n')

if not FILE.exists():
    print(f'[error] الملف مش موجود: {FILE}')
    exit(1)

content = FILE.read_text(encoding='utf-8')

# ─── الإصلاح: price يبقى required=False + write_only=True ───────────────────
OLD = '''class ReturnItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='sale_item.product_name', read_only=True
    )
    sale_item_id = serializers.UUIDField(write_only=True)

    class Meta:
        model  = ReturnItem
        fields = [
            'id', 'sale_item_id', 'product', 'product_name',
            'quantity', 'price', 'subtotal', 'created_at',
        ]
        read_only_fields = ['id', 'subtotal', 'created_at', 'product']'''

NEW = '''class ReturnItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='sale_item.product_name', read_only=True
    )
    sale_item_id = serializers.UUIDField(write_only=True)

    # ✅ price اختياري عند الإنشاء — الـ backend يأخذه من sale_item.price
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False,
        write_only=True,
    )

    class Meta:
        model  = ReturnItem
        fields = [
            'id', 'sale_item_id', 'product', 'product_name',
            'quantity', 'price', 'subtotal', 'created_at',
        ]
        read_only_fields = ['id', 'subtotal', 'created_at', 'product']'''

if OLD in content:
    shutil.copy(FILE, str(FILE) + '.bak')
    content = content.replace(OLD, NEW)
    FILE.write_text(content, encoding='utf-8')
    print('[ok] تم إصلاح ReturnItemSerializer — price أصبح required=False')
else:
    print('[warn] النص القديم مش موجود بالظبط — هنجرب fallback...')

    # fallback: ابحث عن أي تعريف للـ class وأضف price يدوياً
    if 'sale_item_id = serializers.UUIDField(write_only=True)' in content and \
       'price = serializers.DecimalField' not in content:

        shutil.copy(FILE, str(FILE) + '.bak')
        content = content.replace(
            'sale_item_id = serializers.UUIDField(write_only=True)',
            'sale_item_id = serializers.UUIDField(write_only=True)\n\n'
            '    # ✅ price اختياري — الـ backend يأخذه من sale_item.price\n'
            '    price = serializers.DecimalField(\n'
            '        max_digits=10, decimal_places=2,\n'
            '        required=False,\n'
            '        write_only=True,\n'
            '    )'
        )
        FILE.write_text(content, encoding='utf-8')
        print('[ok] تم التعديل عبر fallback')
    else:
        print('[error] تعذر التعديل التلقائي — عدّل يدوياً (راجع التعليمات أدناه)')

print('''
=== Done ===

لو السكريبت نجح: أعد تشغيل الـ backend:
  cd pos_backend && python3 manage.py runserver

لو فشل السكريبت، أضف السطور دي يدوياً في serializers_returns.py
بعد السطر:  sale_item_id = serializers.UUIDField(write_only=True)

    price = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False,
        write_only=True,
    )
''')
