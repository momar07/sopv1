"""
seed_ui_categories.py — يُضيف Categories في UI
"""
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
django.setup()

from ui_builder.models import UiRoute, UiMenuItem, UiAction

MGMT = ["Admins", "Managers"]

# ── Route ─────────────────────────────────────────────────
route, created = UiRoute.objects.update_or_create(
    key="route.categories",
    defaults=dict(
        label="التصنيفات",
        path="/categories",
        component="Categories",
        wrapper="auth",
        required_groups=MGMT,
        order=15,
        is_active=True,
    )
)
print(f"{'✅ أُنشئ' if created else '🔁 حُدِّث'} Route: route.categories → /categories → Categories")

# ── MenuItem (تحت قسم المنتجات) ───────────────────────────
item, created = UiMenuItem.objects.update_or_create(
    key="menu.categories",
    defaults=dict(
        label="التصنيفات",
        path="/categories",
        icon="fa-tags",
        parent_key="menu.products_section",
        order=2,
        required_groups=MGMT,
        is_active=True,
    )
)
print(f"{'✅ أُنشئ' if created else '🔁 حُدِّث'} MenuItem: menu.categories → parent: menu.products_section")

# ── Actions ───────────────────────────────────────────────
for key, label, action_key, variant, order in [
    ("categories.add",    "إضافة فئة", "categories.add",    "primary", 1),
    ("categories.delete", "حذف فئة",   "categories.delete", "danger",  2),
]:
    a, created = UiAction.objects.update_or_create(
        key=key,
        defaults=dict(
            label=label,
            page_key="categories.list",
            action_key=action_key,
            variant=variant,
            required_groups=MGMT,
            order=order,
            is_active=True,
        )
    )
    print(f"{'✅ أُنشئ' if created else '🔁 حُدِّث'} Action: {key}")

print("\n✅ انتهى — أعد تشغيل الـ backend وسجّل دخول من جديد")
