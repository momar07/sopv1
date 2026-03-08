#!/usr/bin/env python3
# fix_finish.py — يكمل اللي وقف: migrations + api.js patch

import os, subprocess, shutil
from pathlib import Path

BASE     = Path(__file__).parent
API_FILE = BASE / 'pos_frontend' / 'src' / 'services' / 'api.js'
MANAGE   = BASE / 'pos_backend' / 'manage.py'

# ─── 1. إضافة getMovements إلى api.js ────────────────────────────────────────
print('\n=== 1. patching api.js ===')

if not API_FILE.exists():
    print(f'[error] {API_FILE} not found')
else:
    content = API_FILE.read_text(encoding='utf-8')

    if 'getMovements' in content:
        print('[skip] getMovements already exists in api.js')
    else:
        # البحث عن السطر الأخير في inventoryAPI قبل القوس الإغلاق
        OLD = "  resolveAlert:          (id)     => api.post(`/inventory/alerts/${id}/resolve/`),"
        NEW = (
            "  resolveAlert:          (id)     => api.post(`/inventory/alerts/${id}/resolve/`),\n\n"
            "  // Stock Movements\n"
            "  getMovements:          (params) => api.get('/inventory/movements/', { params }),"
        )

        if OLD in content:
            shutil.copy(API_FILE, str(API_FILE) + '.bak')
            content = content.replace(OLD, NEW)
            API_FILE.write_text(content, encoding='utf-8')
            print('[ok] api.js patched — getMovements added')
        else:
            # fallback: أضف قبل السطر الأخير في inventoryAPI
            OLD2 = "  resolveAlert:"
            if OLD2 in content:
                shutil.copy(API_FILE, str(API_FILE) + '.bak')
                # أضف السطر بعد آخر resolveAlert
                lines = content.splitlines()
                insert_after = -1
                for i, line in enumerate(lines):
                    if 'resolveAlert:' in line:
                        insert_after = i
                if insert_after >= 0:
                    lines.insert(insert_after + 1,
                        "  getMovements:          (params) => api.get('/inventory/movements/', { params }),")
                    API_FILE.write_text('\n'.join(lines), encoding='utf-8')
                    print('[ok] api.js patched via fallback — getMovements added')
                else:
                    print('[warn] could not patch api.js — see manual fix below')
            else:
                print('[warn] could not patch api.js — add manually (see below)')

# ─── 2. تشغيل migrations بـ python3 ─────────────────────────────────────────
print('\n=== 2. running migrations ===')

if not MANAGE.exists():
    print(f'[error] manage.py not found at {MANAGE}')
else:
    venv_python = BASE / 'pos_backend' / 'venv' / 'bin' / 'python'
    env_python  = BASE / 'env'         / 'bin' / 'python'
    venv2_python= BASE / '.venv'       / 'bin' / 'python'

    # اختار أول python موجود
    python_cmd = 'python3'
    for p in [venv_python, env_python, venv2_python]:
        if p.exists():
            python_cmd = str(p)
            print(f'[info] using virtualenv: {python_cmd}')
            break

    r1 = subprocess.run(
        [python_cmd, str(MANAGE), 'makemigrations', 'inventory'],
        cwd=BASE / 'pos_backend'
    )
    if r1.returncode == 0:
        r2 = subprocess.run(
            [python_cmd, str(MANAGE), 'migrate'],
            cwd=BASE / 'pos_backend'
        )
        if r2.returncode == 0:
            print('[ok] migrations done')
        else:
            print('[error] migrate failed')
    else:
        print('[error] makemigrations failed')

print('\n=== Done ===')
print('Now run:')
print('  cd pos_backend && python3 manage.py runserver')
print('  cd pos_frontend && npm run dev')
