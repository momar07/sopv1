"""
seed_ui_uom.py — يُضيف وحدات القياس في UI
"""
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
django.setup()

from ui_builder.models import UiRoute, UiMenuItem, UiAction

MGMT = ["Admins", "Managers"]

# Route
route, created = UiRoute.objects.update_or_create(
    key="route.units",
    defaults=dict(
        label="وحدات القياس",
        path="/units",
        component="UnitsOfMeasure",
        wrapper="auth",
        required_groups=MGMT,
        order=16,
        is_active=True,
    )
)
print(f"{'✅ أُنشئ' if created else '🔁 حُدِّث'} Route: route.units → /units → UnitsOfMeasure")

# MenuItem تحت قسم المنتجات
item, created = UiMenuItem.objects.update_or_create(
    key="menu.units",
    defaults=dict(
        label="وحدات القياس",
        path="/units",
        icon="fa-ruler",
        parent_key="menu.products_section",
        order=3,
        required_groups=MGMT,
        is_active=True,
    )
)
print(f"{'✅ أُنشئ' if created else '🔁 حُدِّث'} MenuItem: menu.units → parent: menu.products_section")

# Actions
for key, label, action_key, variant, order in [
    ("units.add",    "إضافة وحدة", "units.add",    "primary", 1),
    ("units.delete", "حذف وحدة",   "units.delete", "danger",  2),
]:
    a, created = UiAction.objects.update_or_create(
        key=key,
        defaults=dict(
            label=label,
            page_key="units.list",
            action_key=action_key,
            variant=variant,
            required_groups=MGMT,
            order=order,
            is_active=True,
        )
    )
    print(f"{'✅ أُنشئ' if created else '🔁 حُدِّث'} Action: {key}")

print("\n✅ انتهى — أعد تشغيل الـ backend وسجّل دخول من جديد")
