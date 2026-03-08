# seed_ui_data.py  ·  يُشغَّل داخل Django shell
# python manage.py shell < seed_ui_data.py

import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
django.setup()

from users.models import UiRoute, UiMenuItem, UiAction

# ── مسح البيانات القديمة ─────────────────────────────────────────────────────
print("🗑️  حذف البيانات القديمة ...")
UiAction.objects.all().delete()
UiMenuItem.objects.all().delete()
UiRoute.objects.all().delete()
print("   ✅  تم الحذف")

# ── الـ Groups المسموح لهم ──────────────────────────────────────────────────
ALL    = ["Admins", "Managers", "Cashiers", "Accountants"]
ADMINS = ["Admins"]
MGMT   = ["Admins", "Managers"]
SALES  = ["Admins", "Managers", "Cashiers"]
INV    = ["Admins", "Managers"]

# ── UiRoute ──────────────────────────────────────────────────────────────────
print("\n📍 إنشاء الـ Routes ...")

routes = [
    dict(key="route.dashboard",       label="لوحة التحكم",    path="/dashboard",      component="DashboardPage",      wrapper="auth", required_groups=ALL),
    dict(key="route.products",        label="المنتجات",        path="/products",       component="ProductsPage",       wrapper="auth", required_groups=MGMT),
    dict(key="route.customers",       label="العملاء",         path="/customers",      component="CustomersPage",      wrapper="auth", required_groups=SALES),
    dict(key="route.sales",           label="المبيعات",        path="/sales",          component="SalesPage",          wrapper="auth", required_groups=MGMT),
    dict(key="route.barcode_pos",     label="نقطة البيع",      path="/pos",            component="BarcodePOS",         wrapper="auth", required_groups=SALES),
    dict(key="route.inventory",       label="المخزون",         path="/inventory",      component="InventoryPage",      wrapper="auth", required_groups=INV),
    dict(key="route.purchase_orders", label="أوامر الشراء",    path="/purchase-orders",component="PurchaseOrdersPage", wrapper="auth", required_groups=INV),
    dict(key="route.suppliers",       label="الموردون",        path="/suppliers",      component="SuppliersPage",      wrapper="auth", required_groups=INV),
    dict(key="route.cash_register",   label="الخزنة",          path="/cash-register",  component="CashRegisterPage",   wrapper="auth", required_groups=MGMT),
    dict(key="route.users",           label="المستخدمون",      path="/users",          component="UsersPage",          wrapper="auth", required_groups=ADMINS),
    dict(key="route.settings",        label="الإعدادات",       path="/settings",       component="SettingsPage",       wrapper="auth", required_groups=ADMINS),
    dict(key="route.returns",         label="المرتجعات",       path="/returns",        component="ReturnsPage",        wrapper="auth", required_groups=SALES),
    dict(key="route.units",           label="وحدات القياس",    path="/units",          component="UnitsPage",          wrapper="auth", required_groups=MGMT),
    dict(key="route.login",           label="تسجيل الدخول",   path="/login",          component="LoginPage",          wrapper="guest",required_groups=[]),
]

for r in routes:
    obj, created = UiRoute.objects.get_or_create(
        key=r["key"],
        defaults=dict(
            label=r["label"],
            path=r["path"],
            component=r["component"],
            wrapper=r["wrapper"],
            required_groups=r["required_groups"],
        )
    )
    status = "✅ created" if created else "⏭️  exists"
    print(f"   {status}  {r['key']}")

# ── UiMenuItem ───────────────────────────────────────────────────────────────
print("\n📂 إنشاء الـ Sidebar items ...")

menu_items = [
    # ── الرئيسية (root) ──────────────────────────────────────────────────
    dict(key="menu.home",   label="الرئيسية",   path="/dashboard",      icon="fas fa-home",           parent_key="",              order=1,  required_groups=ALL),
    dict(key="menu.dashboard", label="لوحة التحكم", path="/dashboard",  icon="fas fa-tachometer-alt", parent_key="menu.home",     order=1,  required_groups=ALL),
    dict(key="menu.products",  label="المنتجات",    path="/products",   icon="fas fa-box",            parent_key="menu.home",     order=2,  required_groups=MGMT),

    # ── نقطة البيع ───────────────────────────────────────────────────────
    dict(key="menu.pos_section", label="نقطة البيع",  path="",         icon="fas fa-cash-register",  parent_key="",              order=2,  required_groups=SALES),
    dict(key="menu.barcode_pos", label="نقطة البيع",  path="/pos",     icon="fas fa-barcode",        parent_key="menu.pos_section", order=1, required_groups=SALES),

    # ── المخزون ──────────────────────────────────────────────────────────
    dict(key="menu.inventory_section",label="المخزون",       path="",                 icon="fas fa-warehouse",    parent_key="",                      order=3, required_groups=INV),
    dict(key="menu.inventory",        label="المخزون",       path="/inventory",       icon="fas fa-cubes",        parent_key="menu.inventory_section", order=1, required_groups=INV),
    dict(key="menu.purchase_orders",  label="أوامر الشراء",  path="/purchase-orders", icon="fas fa-file-invoice", parent_key="menu.inventory_section", order=2, required_groups=INV),
    dict(key="menu.suppliers",        label="الموردون",      path="/suppliers",       icon="fas fa-truck",        parent_key="menu.inventory_section", order=3, required_groups=INV),
    dict(key="menu.units",            label="وحدات القياس",  path="/units",           icon="fas fa-ruler",        parent_key="menu.inventory_section", order=4, required_groups=MGMT),

    # ── المبيعات ─────────────────────────────────────────────────────────
    dict(key="menu.sales_section", label="المبيعات",  path="",          icon="fas fa-chart-line",   parent_key="",                   order=4, required_groups=SALES),
    dict(key="menu.sales",         label="المبيعات",  path="/sales",    icon="fas fa-receipt",      parent_key="menu.sales_section", order=1, required_groups=MGMT),
    dict(key="menu.returns",       label="المرتجعات", path="/returns",  icon="fas fa-undo",         parent_key="menu.sales_section", order=2, required_groups=SALES),
    dict(key="menu.customers",     label="العملاء",   path="/customers",icon="fas fa-users",        parent_key="menu.sales_section", order=3, required_groups=SALES),

    # ── الإدارة ───────────────────────────────────────────────────────────
    dict(key="menu.admin_section", label="الإدارة",      path="",                icon="fas fa-cog",      parent_key="",                    order=5, required_groups=MGMT),
    dict(key="menu.cash_register", label="الخزنة",       path="/cash-register",  icon="fas fa-coins",    parent_key="menu.admin_section",  order=1, required_groups=MGMT),
    dict(key="menu.users",         label="المستخدمون",   path="/users",          icon="fas fa-user-cog", parent_key="menu.admin_section",  order=2, required_groups=ADMINS),
    dict(key="menu.settings",      label="الإعدادات",    path="/settings",       icon="fas fa-sliders-h",parent_key="menu.admin_section",  order=3, required_groups=ADMINS),
]

for m in menu_items:
    obj, created = UiMenuItem.objects.get_or_create(
        key=m["key"],
        defaults=dict(
            label=m["label"],
            path=m["path"],
            icon=m["icon"],
            parent_key=m["parent_key"],
            order=m["order"],
            required_groups=m["required_groups"],
        )
    )
    status = "✅ created" if created else "⏭️  exists"
    print(f"   {status}  {m['key']}")

# ── UiAction ─────────────────────────────────────────────────────────────────
print("\n⚡ إنشاء الـ Actions ...")

actions = [
    dict(key="action.products.add",          page_key="route.products",        action_key="products.add",          label="إضافة منتج",     icon="fas fa-plus",  variant="primary"),
    dict(key="action.purchase_orders.add",   page_key="route.purchase_orders", action_key="purchase_orders.add",   label="أمر شراء جديد", icon="fas fa-plus",  variant="primary"),
    dict(key="action.suppliers.add",         page_key="route.suppliers",       action_key="suppliers.add",         label="إضافة مورد",    icon="fas fa-plus",  variant="primary"),
    dict(key="action.customers.add",         page_key="route.customers",       action_key="customers.add",         label="إضافة عميل",    icon="fas fa-plus",  variant="primary"),
    dict(key="action.units.add",             page_key="route.units",           action_key="units.add",             label="إضافة وحدة",    icon="fas fa-plus",  variant="primary"),
    dict(key="action.users.add",             page_key="route.users",           action_key="users.add",             label="إضافة مستخدم",  icon="fas fa-plus",  variant="primary"),
    dict(key="action.cash_register.open",    page_key="route.cash_register",   action_key="cash_register.open",    label="فتح وردية",     icon="fas fa-lock-open", variant="success"),
    dict(key="action.cash_register.close",   page_key="route.cash_register",   action_key="cash_register.close",   label="إغلاق وردية",   icon="fas fa-lock", variant="danger"),
]

for a in actions:
    obj, created = UiAction.objects.get_or_create(
        key=a["key"],
        defaults=dict(
            page_key=a["page_key"],
            action_key=a["action_key"],
            label=a["label"],
            icon=a["icon"],
            variant=a["variant"],
        )
    )
    status = "✅ created" if created else "⏭️  exists"
    print(f"   {status}  {a['key']}")

# ── ملخص ─────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"  Routes  : {UiRoute.objects.count()}")
print(f"  Menu    : {UiMenuItem.objects.count()}")
print(f"  Actions : {UiAction.objects.count()}")
print("="*60)
print("\n🎉  اكتمل الـ seed بنجاح!")
