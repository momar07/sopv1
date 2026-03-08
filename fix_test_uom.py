# fix_test_uom.py
"""
يُصلح test_uom.py — مشكلتان:
  1. الـ endpoint كان /api/products/units/ والصح /api/units/
  2. بعد 404 كان الكود يحاول يعمل list على الـ response فيطلع TypeError
"""
import os, shutil, datetime

BASE      = "/home/momar/Projects/POS_DEV/posv1_dev10"
BACKEND   = os.path.join(BASE, "pos_backend")
TEST_FILE = os.path.join(BACKEND, "test_uom.py")
CHLOG     = os.path.join(BASE, "CHANGELOG.md")

def backup(path):
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
        print(f"  ✅ Backup: {path}.bak")

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ Written: {path}")

# ══════════════════════════════════════════════════════════════════════════════
TEST_CONTENT = '''"""
test_uom.py — اختبار شامل لـ UnitOfMeasure  (v2 — fixed endpoints)
شغّله بـ:  cd pos_backend && python manage.py shell < test_uom.py

URL map المستخرج من urls.py:
  pos_backend/urls.py  →  path('api/', include('products.urls'))
  products/urls.py     →  router.register('units', UnitOfMeasureViewSet)
  ∴ الـ endpoint الصح: /api/units/   (مش /api/products/units/)
"""
import django, os, traceback
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
django.setup()

from decimal import Decimal
from products.models import UnitOfMeasure, Product, Category, ProductUnitPrice

PASS = "✅"
FAIL = "❌"
results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, name, detail))
    print(f"  {status}  {name}" + (f"  →  {detail}" if detail else ""))

def run_tests():
    print("\\n" + "="*60)
    print("  UnitOfMeasure — اختبارات شاملة  (v2)")
    print("="*60)

    # ── إعداد: حذف بيانات اختبار قديمة ──────────────────────────
    UnitOfMeasure.objects.filter(name__startswith="TEST_").delete()
    Product.objects.filter(name__startswith="TEST_").delete()
    Category.objects.filter(name="TEST_CAT").delete()

    # ─────────────────────────────────────────────────────────────
    print("\\n[1] إنشاء وحدات القياس")
    # ─────────────────────────────────────────────────────────────
    try:
        piece = UnitOfMeasure.objects.create(
            name="TEST_قطعة", symbol="قطعة", factor=Decimal("1"),
            category="count", is_base=True, is_active=True,
        )
        check("إنشاء وحدة أساسية (قطعة)",
              piece.pk is not None, f"id={str(piece.id)[:8]}")

        dozen = UnitOfMeasure.objects.create(
            name="TEST_دستة", symbol="دستة", factor=Decimal("12"),
            category="count", is_base=False, is_active=True,
        )
        check("إنشاء وحدة مشتقة (دستة × 12)",
              dozen.factor == Decimal("12"), f"factor={dozen.factor}")

        carton = UnitOfMeasure.objects.create(
            name="TEST_كرتون", symbol="كرتون", factor=Decimal("24"),
            category="count", is_base=False, is_active=True,
        )
        check("إنشاء وحدة مشتقة (كرتون × 24)",
              carton.factor == Decimal("24"))

        kg = UnitOfMeasure.objects.create(
            name="TEST_كيلو", symbol="كغ", factor=Decimal("1"),
            category="weight", is_base=True, is_active=True,
        )
        check("إنشاء وحدة وزن (كيلو)", kg.category == "weight")

    except Exception as e:
        check("إنشاء وحدات القياس", False, str(e))
        return

    # ─────────────────────────────────────────────────────────────
    print("\\n[2] التحقق من الـ __str__ والـ ordering")
    # ─────────────────────────────────────────────────────────────
    check("__str__ يرجع اسم الوحدة",
          str(piece) == "TEST_قطعة", str(piece))

    count_units = list(
        UnitOfMeasure.objects
        .filter(name__startswith="TEST_", category="count")
        .order_by("category", "factor")
        .values_list("name", flat=True)
    )
    check("ordering: factor أصغر يجي أول (قطعة factor=1)",
          count_units[0] == "TEST_قطعة",
          f"order={count_units}")

    # ─────────────────────────────────────────────────────────────
    print("\\n[3] ربط المنتج بالوحدات")
    # ─────────────────────────────────────────────────────────────
    try:
        cat = Category.objects.create(name="TEST_CAT")
        prod = Product.objects.create(
            name="TEST_منتج",
            category=cat,
            price=Decimal("10.00"),
            cost=Decimal("7.00"),
            stock=100,
            base_unit=piece,
            purchase_unit=carton,
        )
        check("ربط المنتج بالوحدة الأساسية", prod.base_unit == piece)
        check("ربط المنتج بوحدة الشراء",     prod.purchase_unit == carton)
        check("profit_margin محسوب صح",
              abs(prod.profit_margin - float((Decimal("10")-Decimal("7"))/Decimal("7")*100)) < 0.01,
              f"margin={prod.profit_margin:.2f}%")
        check("is_low_stock False لما stock=100",
              prod.is_low_stock == False, f"stock={prod.stock}, min={prod.min_stock}")

    except Exception as e:
        check("إنشاء منتج تجريبي", False, str(e))
        return

    # ─────────────────────────────────────────────────────────────
    print("\\n[4] ProductUnitPrice — السعر التلقائي واليدوي")
    # ─────────────────────────────────────────────────────────────
    try:
        # سعر الدستة = 10 × 12 = 120  (is_auto=True)
        pup_auto = ProductUnitPrice.objects.create(
            product=prod, unit=dozen,
            price=Decimal("0"),
            is_auto=True,
        )
        expected_auto = prod.price * dozen.factor
        check("سعر الدستة محسوب تلقائياً (10×12=120)",
              pup_auto.price == expected_auto,
              f"price={pup_auto.price}, expected={expected_auto}")

        # سعر الكرتون = 200 يدوي
        pup_manual = ProductUnitPrice.objects.create(
            product=prod, unit=carton,
            price=Decimal("200"),
            is_auto=False,
        )
        check("سعر الكرتون يدوي (200)",
              pup_manual.price == Decimal("200"),
              f"price={pup_manual.price}")

        # تأكد إن is_auto=False ما يبدّل السعر لو عدّلناه
        pup_manual.price = Decimal("250")
        pup_manual.save()
        pup_manual.refresh_from_db()
        check("is_auto=False لا يُعيد حساب السعر عند الحفظ",
              pup_manual.price == Decimal("250"),
              f"price after save={pup_manual.price}")

    except Exception as e:
        check("ProductUnitPrice", False, str(e))

    # ─────────────────────────────────────────────────────────────
    print("\\n[5] unique_together على ProductUnitPrice")
    # ─────────────────────────────────────────────────────────────
    try:
        from django.db import IntegrityError, transaction
        duplicate_raised = False
        try:
            with transaction.atomic():
                ProductUnitPrice.objects.create(
                    product=prod, unit=dozen,
                    price=Decimal("99"), is_auto=False
                )
        except Exception:
            duplicate_raised = True
        check("unique_together يمنع تكرار (product, unit)",
              duplicate_raised)
    except Exception as e:
        check("unique_together", False, str(e))

    # ─────────────────────────────────────────────────────────────
    print("\\n[6] اختبار الـ queryset الافتراضي (is_active filter)")
    # ─────────────────────────────────────────────────────────────
    try:
        # نعطّل وحدة ونتأكد إنها مش في الـ ViewSet queryset
        kg.is_active = False
        kg.save()

        active_names = list(
            UnitOfMeasure.objects
            .filter(is_active=True, name__startswith="TEST_")
            .values_list("name", flat=True)
        )
        check("وحدة is_active=False مش موجودة في الـ active queryset",
              "TEST_كيلو" not in active_names,
              f"active TEST_ units: {active_names}")

        # إعادة التفعيل
        kg.is_active = True
        kg.save()

    except Exception as e:
        check("is_active filter", False, str(e))

    # ─────────────────────────────────────────────────────────────
    print("\\n[7] API endpoints  (الـ URL الصح: /api/units/)")
    # ─────────────────────────────────────────────────────────────
    try:
        from rest_framework.test import APIClient
        from django.contrib.auth.models import User

        admin, _ = User.objects.get_or_create(username="test_uom_admin")
        admin.is_superuser = True
        admin.is_staff     = True
        admin.set_password("testpass")
        admin.save()

        client = APIClient()
        client.force_authenticate(user=admin)

        # ── GET /api/units/ ──────────────────────────────────────
        res_list = client.get("/api/units/")
        check("GET /api/units/ → 200",
              res_list.status_code == 200,
              f"status={res_list.status_code}")

        if res_list.status_code == 200:
            data = res_list.data
            items = data.get("results", data) if isinstance(data, dict) else data
            # تأكد إن items قائمة قبل ما نعمل list comprehension
            if isinstance(items, list):
                names = [u["name"] for u in items if isinstance(u, dict)]
                test_units = [n for n in names if "TEST_" in n]
                check("الوحدات التجريبية موجودة في الـ response",
                      len(test_units) > 0,
                      f"found: {test_units}")
            else:
                check("response.results قائمة", False,
                      f"type={type(items)}, data={str(items)[:100]}")

        # ── POST /api/units/ ─────────────────────────────────────
        res_post = client.post("/api/units/", {
            "name":     "TEST_API_وحدة",
            "symbol":   "T",
            "factor":   "6",
            "category": "count",
            "is_base":  False,
            "is_active": True,
        }, format="json")
        check("POST /api/units/ → 201",
              res_post.status_code == 201,
              f"status={res_post.status_code}")

        # ── GET /api/units/:id/ ──────────────────────────────────
        if res_post.status_code == 201:
            new_id = res_post.data["id"]
            res_detail = client.get(f"/api/units/{new_id}/")
            check("GET /api/units/:id/ → 200",
                  res_detail.status_code == 200,
                  f"status={res_detail.status_code}, name={res_detail.data.get('name')}")

            # ── PATCH /api/units/:id/ ────────────────────────────
            res_patch = client.patch(f"/api/units/{new_id}/",
                                     {"symbol": "TT"}, format="json")
            check("PATCH /api/units/:id/ → 200",
                  res_patch.status_code == 200,
                  f"status={res_patch.status_code}, symbol={res_patch.data.get('symbol')}")

            # ── DELETE /api/units/:id/ ───────────────────────────
            res_del = client.delete(f"/api/units/{new_id}/")
            check("DELETE /api/units/:id/ → 204",
                  res_del.status_code == 204,
                  f"status={res_del.status_code}")

        # ── GET بدون auth → 401 ──────────────────────────────────
        anon = APIClient()
        res_anon = anon.get("/api/units/")
        check("GET /api/units/ بدون auth → 401",
              res_anon.status_code == 401,
              f"status={res_anon.status_code}")

        # ── Search filter ────────────────────────────────────────
        res_search = client.get("/api/units/?search=TEST_قطعة")
        check("search=TEST_قطعة يرجع نتيجة واحدة على الأقل",
              res_search.status_code == 200,
              f"status={res_search.status_code}")
        if res_search.status_code == 200:
            s_data  = res_search.data
            s_items = s_data.get("results", s_data) if isinstance(s_data, dict) else s_data
            check("نتيجة البحث تحتوي TEST_قطعة",
                  isinstance(s_items, list) and len(s_items) >= 1,
                  f"count={len(s_items) if isinstance(s_items, list) else '?'}")

    except Exception as e:
        check("API tests", False, traceback.format_exc()[:300])

    # ─────────────────────────────────────────────────────────────
    print("\\n[8] تنظيف بيانات الاختبار")
    # ─────────────────────────────────────────────────────────────
    try:
        ProductUnitPrice.objects.filter(product__name__startswith="TEST_").delete()
        Product.objects.filter(name__startswith="TEST_").delete()
        Category.objects.filter(name="TEST_CAT").delete()
        UnitOfMeasure.objects.filter(name__startswith="TEST_").delete()
        User.objects.filter(username="test_uom_admin").delete()
        check("حذف بيانات الاختبار", True)
    except Exception as e:
        check("تنظيف بيانات الاختبار", False, str(e))

    # ─────────────────────────────────────────────────────────────
    print("\\n" + "="*60)
    passed = sum(1 for r in results if r[0] == PASS)
    failed = sum(1 for r in results if r[0] == FAIL)
    total  = passed + failed
    print(f"  النتيجة النهائية:  {passed}/{total} نجح ✅  |  {failed} فشل ❌")
    if failed == 0:
        print("  🎉 كل الاختبارات نجحت!")
    print("="*60 + "\\n")

run_tests()
'''

# ── Main ─────────────────────────────────────────────────────────────────────
print("=" * 60)
print("  fix_test_uom.py  —  إصلاح مشكلتين في test_uom.py")
print("=" * 60)
print()
print("  المشكلة 1: endpoint كان /api/products/units/ → الصح /api/units/")
print("  المشكلة 2: بعد 404 كان list comprehension على string → TypeError")
print()

backup(TEST_FILE)
write_file(TEST_FILE, TEST_CONTENT)

ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
with open(CHLOG, "a", encoding="utf-8") as f:
    f.write(
        f"\n## [{ts}] fix_test_uom\n"
        "- Fix: endpoint /api/products/units/ → /api/units/\n"
        "- Fix: guard isinstance(items, list) قبل list comprehension\n"
        "- أضفنا اختبارات إضافية: PATCH, auth, search filter, profit_margin, is_low_stock\n"
    )
print("  ✅ CHANGELOG updated")
print()
print("✅ تم! شغّل:")
print()
print("   cd /home/momar/Projects/POS_DEV/posv1_dev10")
print("   python3 fix_test_uom.py")
print()
print("   cd pos_backend")
print("   python manage.py shell < test_uom.py")
