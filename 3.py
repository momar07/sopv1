#!/usr/bin/env python3
# fix_complete_return.py
# يضيف الحركتين الماليه والمخزون عند إكمال المرتجع

import shutil
from pathlib import Path

BASE = Path(__file__).parent
VIEWS_FILE = BASE / 'pos_backend/sales/views_returns.py'
MODELS_FILE = BASE / 'pos_backend/sales/models_cashregister.py'

def backup(path):
    if path.exists():
        shutil.copy(path, str(path) + '.bak')
        print(f'  [backup] {path.name}.bak')

def write(path, content):
    backup(path)
    path.write_text(content, encoding='utf-8')
    print(f'  [ok]     {path}')

# ═══════════════════════════════════════════════════════
# 1. models_cashregister.py
#    إضافة 'return' لـ TRANSACTION_TYPES في CashTransaction
# ═══════════════════════════════════════════════════════
print('\n=== 1. patching models_cashregister.py ===')

if not MODELS_FILE.exists():
    print(f'  [error] {MODELS_FILE} not found')
else:
    content = MODELS_FILE.read_text(encoding='utf-8')

    OLD_TYPES = """    TRANSACTION_TYPES = [
        ('deposit',    'إيداع'),
        ('withdrawal', 'سحب'),
        ('adjustment', 'تعديل'),
    ]"""

    NEW_TYPES = """    TRANSACTION_TYPES = [
        ('deposit',    'إيداع'),
        ('withdrawal', 'سحب'),
        ('adjustment', 'تعديل'),
        ('return',     'مرتجع'),   # ✅ حركة رد مبلغ للعميل
    ]"""

    if "'return'" in content:
        print('  [skip] return type already exists')
    elif OLD_TYPES in content:
        backup(MODELS_FILE)
        content = content.replace(OLD_TYPES, NEW_TYPES)
        MODELS_FILE.write_text(content, encoding='utf-8')
        print('  [ok]  added return to TRANSACTION_TYPES')
    else:
        print('  [warn] could not find TRANSACTION_TYPES — add manually')

# ═══════════════════════════════════════════════════════
# 2. views_returns.py — complete() مع الحركتين
# ═══════════════════════════════════════════════════════
print('\n=== 2. patching views_returns.py ===')

VIEWS_CONTENT = '''from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
