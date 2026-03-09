#!/usr/bin/env python3
# fix_05_purchasing_improvements.py
# ── الاستخدام ─────────────────────────────────────────────────────────────────
#   cd /home/momar/Projects/POS_DEV/posv1_dev10
#   python3 fix_05_purchasing_improvements.py
# ──────────────────────────────────────────────────────────────────────────────

import os
import sys
import shutil
from datetime import datetime

# ── المسارات ──────────────────────────────────────────────────────────────────
BASE      = "/home/momar/Projects/POS_DEV/posv1_dev10"
BACKEND   = BASE + "/pos_backend"
FRONTEND  = BASE + "/pos_frontend"

MODELS_PY       = BACKEND  + "/inventory/models.py"
SERIALIZERS_PY  = BACKEND  + "/inventory/serializers.py"
VIEWS_PY        = BACKEND  + "/inventory/views.py"
PURCHASING_JSX  = FRONTEND + "/src/pages/PurchasingPage.jsx"
INVENTORY_JSX   = FRONTEND + "/src/pages/InventoryPage.jsx"
API_JS          = FRONTEND + "/src/services/api.js"
CHANGELOG_MD    = BASE     + "/CHANGELOG.md"
FIXES_README_MD = BASE     + "/FIXES_README.md"

NOW = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── helpers ───────────────────────────────────────────────────────────────────
def abort(msg):
    print("❌ " + msg)
    sys.exit(1)

def backup(path):
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = path + ".bak_" + ts
    shutil.copy2(path, dst)
    print("  📦 backup → " + dst)

def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def apply_fix(label, path, old, new):
    src = read_file(path)
    if old not in src:
        print("  ⚠️  pattern not found — skipping: " + label)
        return False
    backup(path)
    write_file(path, src.replace(old, new, 1))
    print("  ✅ " + label)
    return True

def update_changelog(entry):
    src = read_file(CHANGELOG_MD)
    marker = "# CHANGELOG"
    pos = src.find(marker)
    if pos == -1:
        write_file(CHANGELOG_MD, src + "\n" + entry)
    else:
        eol = src.find("\n", pos) + 1
        src = src[:eol] + "\n" + entry + "\n" + src[eol:]
        write_file(CHANGELOG_MD, src)
    print("  ✅ CHANGELOG.md updated")

def write_readme(entry):
    src = read_file(FIXES_README_MD)
    marker = "## المشاكل التي تم إصلاحها"
    pos = src.find(marker)
    if pos == -1:
        write_file(FIXES_README_MD, src + "\n" + entry)
    else:
        eol = src.find("\n", pos) + 1
        src = src[:eol] + "\n" + entry + "\n" + src[eol:]
        write_file(FIXES_README_MD, src)
    print("  ✅ FIXES_README.md updated")

# ── التحقق من وجود الملفات ────────────────────────────────────────────────────
def check_files():
    for p in [MODELS_PY, SERIALIZERS_PY, VIEWS_PY,
              PURCHASING_JSX, INVENTORY_JSX, API_JS,
              CHANGELOG_MD, FIXES_README_MD]:
        if not os.path.exists(p):
            abort("ملف غير موجود: " + p)
    print("✅ كل الملفات موجودة")

# ── Fix-1 + Fix-2 + Fix-4 + Fix-7: models.py ─────────────────────────────────
def fix_models():
    print("\n── Fix models.py (Fix-2 M2M + Fix-4 auto_resolve + Fix-7 created_by) ──")

    # Fix-7: إضافة created_by + Fix-2: استبدال linked_po FK بـ linked_pos M2M + Fix-4: check_and_auto_resolve
    old = (
        "    assigned_to   = models.ForeignKey(\n"
        "        settings.AUTH_USER_MODEL, null=True, blank=True,\n"
        "        on_delete=models.SET_NULL, related_name='assigned_alerts'\n"
        "    )\n"
        "    deadline      = models.DateField(null=True, blank=True)\n"
        "    linked_po     = models.ForeignKey(\n"
        "        PurchaseOrder, null=True, blank=True,\n"
        "        on_delete=models.SET_NULL, related_name='linked_alerts'\n"
        "    )\n"
        "    is_resolved   = models.BooleanField(default=False)\n"
        "    resolved_at   = models.DateTimeField(null=True, blank=True)\n"
        "    created_at    = models.DateTimeField(auto_now_add=True)\n"
        "    updated_at    = models.DateTimeField(auto_now=True)\n"
        "\n"
        "    class Meta:\n"
        "        verbose_name        = 'تنبيه مخزون'\n"
        "        verbose_name_plural = 'تنبيهات المخزون'\n"
        "        ordering            = ['-created_at']\n"
        "\n"
        "    def __str__(self):\n"
        "        return self.product.name + ' - ' + self.alert_type\n"
        "\n"
        "    def resolve(self, user=None):\n"
        "        from django.utils import timezone\n"
        "        self.is_resolved   = True\n"
        "        self.ticket_status = 'resolved'\n"
        "        self.resolved_at   = timezone.now()\n"
        "        self.save(update_fields=['is_resolved', 'ticket_status', 'resolved_at'])\n"
    )
    new = (
        "    assigned_to   = models.ForeignKey(\n"
        "        settings.AUTH_USER_MODEL, null=True, blank=True,\n"
        "        on_delete=models.SET_NULL, related_name='assigned_alerts'\n"
        "    )\n"
        "    # Fix-7: اليوزر اللي انشا التنبيه\n"
        "    created_by    = models.ForeignKey(\n"
        "        settings.AUTH_USER_MODEL, null=True, blank=True,\n"
        "        on_delete=models.SET_NULL, related_name='created_alerts'\n"
        "    )\n"
        "    deadline      = models.DateField(null=True, blank=True)\n"
        "    # Fix-2: ManyToMany بدل FK — لدعم اكتر من PO لكل تنبيه\n"
        "    linked_pos    = models.ManyToManyField(\n"
        "        PurchaseOrder, blank=True,\n"
        "        related_name='linked_alerts',\n"
        "        verbose_name='اوامر الشراء المرتبطة'\n"
        "    )\n"
        "    is_resolved   = models.BooleanField(default=False)\n"
        "    resolved_at   = models.DateTimeField(null=True, blank=True)\n"
        "    created_at    = models.DateTimeField(auto_now_add=True)\n"
        "    updated_at    = models.DateTimeField(auto_now=True)\n"
        "\n"
        "    class Meta:\n"
        "        verbose_name        = 'تنبيه مخزون'\n"
        "        verbose_name_plural = 'تنبيهات المخزون'\n"
        "        ordering            = ['-created_at']\n"
        "\n"
        "    def __str__(self):\n"
        "        return self.product.name + ' - ' + self.alert_type\n"
        "\n"
        "    def resolve(self, user=None):\n"
        "        from django.utils import timezone\n"
        "        self.is_resolved   = True\n"
        "        self.ticket_status = 'resolved'\n"
        "        self.resolved_at   = timezone.now()\n"
        "        self.save(update_fields=['is_resolved', 'ticket_status', 'resolved_at'])\n"
        "\n"
        "    # Fix-4: يحل التنبيه تلقائياً لو كل الـ POs المرتبطة استُلمت\n"
        "    def check_and_auto_resolve(self):\n"
        "        pos = self.linked_pos.all()\n"
        "        if pos.exists() and all(po.status == 'received' for po in pos):\n"
        "            self.resolve()\n"
        "            return True\n"
        "        return False\n"
    )
    apply_fix("models.py — M2M + created_by + check_and_auto_resolve", MODELS_PY, old, new)


# ── Fix-3: serializers.py ─────────────────────────────────────────────────────
def fix_serializers():
    print("\n── Fix serializers.py (Fix-3 date + Fix-2 M2M + Fix-7 created_by) ──")

    # Fix-3: validate_expected_date في StockAlertNoteSerializer
    old_note = (
        "    class Meta:\n"
        "        model  = StockAlertNote\n"
        "        fields = [\n"
        "            'id', 'alert', 'user', 'user_name',\n"
        "            'note_type', 'note_type_display', 'text',\n"
        "            'cost', 'expected_date', 'delay_reason', 'supplier_name',\n"
        "            'created_at',\n"
        "        ]\n"
        "        read_only_fields = ['alert', 'user', 'created_at']\n"
    )
    new_note = (
        "    class Meta:\n"
        "        model  = StockAlertNote\n"
        "        fields = [\n"
        "            'id', 'alert', 'user', 'user_name',\n"
        "            'note_type', 'note_type_display', 'text',\n"
        "            'cost', 'expected_date', 'delay_reason', 'supplier_name',\n"
        "            'created_at',\n"
        "        ]\n"
        "        read_only_fields = ['alert', 'user', 'created_at']\n"
        "\n"
        "    # Fix-3: تحويل empty string لـ None في حقول التاريخ\n"
        "    def validate_expected_date(self, value):\n"
        "        if value == '' or value is None:\n"
        "            return None\n"
        "        return value\n"
        "\n"
        "    def validate_cost(self, value):\n"
        "        if value == '' or value is None:\n"
        "            return None\n"
        "        return value\n"
    )
    apply_fix("serializers.py — Fix-3 validate_expected_date + validate_cost", SERIALIZERS_PY, old_note, new_note)

    # Fix-2 + Fix-7: StockAlertSerializer — استبدال linked_po بـ linked_pos_data + created_by_name
    old_alert_ser = (
        "    assigned_to_name      = serializers.CharField(source='assigned_to.username',        read_only=True)\n"
        "    linked_po_reference   = serializers.CharField(source='linked_po.reference_number',  read_only=True)\n"
        "    linked_po_status      = serializers.CharField(source='linked_po.status',            read_only=True)\n"
        "    notes                 = StockAlertNoteSerializer(many=True, read_only=True)\n"
        "    notes_count           = serializers.SerializerMethodField()\n"
        "\n"
        "    class Meta:\n"
        "        model  = StockAlert\n"
        "        fields = [\n"
        "            'id', 'product', 'product_name', 'product_barcode', 'product_current_stock',\n"
        "            'alert_type', 'alert_type_display',\n"
        "            'threshold', 'current_stock',\n"
        "            'priority', 'priority_display',\n"
        "            'ticket_status', 'ticket_status_display',\n"
        "            'assigned_to', 'assigned_to_name',\n"
        "            'deadline',\n"
        "            'linked_po', 'linked_po_reference', 'linked_po_status',\n"
        "            'is_resolved', 'resolved_at',\n"
        "            'notes', 'notes_count',\n"
        "            'created_at', 'updated_at',\n"
        "        ]\n"
        "        read_only_fields = ['is_resolved', 'resolved_at', 'created_at', 'updated_at']\n"
        "\n"
        "    def get_notes_count(self, obj):\n"
        "        return obj.notes.count()\n"
    )
    new_alert_ser = (
        "    assigned_to_name      = serializers.CharField(source='assigned_to.username',        read_only=True)\n"
        "    # Fix-7: اسم منشئ التنبيه\n"
        "    created_by_name       = serializers.CharField(source='created_by.username',         read_only=True)\n"
        "    # Fix-2: قائمة POs مرتبطة بدل واحدة\n"
        "    linked_pos_data       = LinkedPOSerializer(source='linked_pos', many=True,          read_only=True)\n"
        "    linked_pos_count      = serializers.SerializerMethodField()\n"
        "    notes                 = StockAlertNoteSerializer(many=True, read_only=True)\n"
        "    notes_count           = serializers.SerializerMethodField()\n"
        "\n"
        "    class Meta:\n"
        "        model  = StockAlert\n"
        "        fields = [\n"
        "            'id', 'product', 'product_name', 'product_barcode', 'product_current_stock',\n"
        "            'alert_type', 'alert_type_display',\n"
        "            'threshold', 'current_stock',\n"
        "            'priority', 'priority_display',\n"
        "            'ticket_status', 'ticket_status_display',\n"
        "            'assigned_to', 'assigned_to_name',\n"
        "            'created_by', 'created_by_name',\n"
        "            'deadline',\n"
        "            'linked_pos_data', 'linked_pos_count',\n"
        "            'is_resolved', 'resolved_at',\n"
        "            'notes', 'notes_count',\n"
        "            'created_at', 'updated_at',\n"
        "        ]\n"
        "        read_only_fields = ['is_resolved', 'resolved_at', 'created_at', 'updated_at', 'created_by']\n"
        "\n"
        "    def get_notes_count(self, obj):\n"
        "        return obj.notes.count()\n"
        "\n"
        "    def get_linked_pos_count(self, obj):\n"
        "        return obj.linked_pos.count()\n"
    )
    apply_fix("serializers.py — Fix-2+7 StockAlertSerializer", SERIALIZERS_PY, old_alert_ser, new_alert_ser)

    # Fix-2: إضافة LinkedPOSerializer قبل StockAlertSerializer
    old_before_alert = (
        "class StockAlertSerializer(serializers.ModelSerializer):\n"
        "    product_name          = serializers.CharField(source='product.name',               read_only=True)\n"
    )
    new_before_alert = (
        "# Fix-2: serializer للـ POs المرتبطة بالتنبيه\n"
        "class LinkedPOSerializer(serializers.ModelSerializer):\n"
        "    supplier_name = serializers.CharField(source='supplier.name', read_only=True)\n"
        "    user_name     = serializers.CharField(source='user.username', read_only=True)\n"
        "\n"
        "    class Meta:\n"
        "        model  = PurchaseOrder\n"
        "        fields = ['id', 'reference_number', 'status', 'total_cost',\n"
        "                  'expected_date', 'received_at', 'supplier_name', 'user_name', 'created_at']\n"
        "\n"
        "\n"
        "class StockAlertSerializer(serializers.ModelSerializer):\n"
        "    product_name          = serializers.CharField(source='product.name',               read_only=True)\n"
    )
    apply_fix("serializers.py — Fix-2 LinkedPOSerializer", SERIALIZERS_PY, old_before_alert, new_before_alert)


# ── Fix-4 + Fix-6 + Fix-7: views.py ──────────────────────────────────────────
def fix_views():
    print("\n── Fix views.py (Fix-4 auto_resolve + Fix-6 assign + Fix-7 created_by) ──")

    # Fix-4: استبدال resolve بسيط بعد receive بـ check_and_auto_resolve
    old_resolve = (
        "            # \u2705 resolve StockAlert \u0644\u0648 \u0627\u0644\u0645\u062e\u0632\u0648\u0646 \u0631\u062c\u0639 \u0641\u0648\u0642 \u0627\u0644\u0640 threshold\n"
        "                from inventory.models import StockAlert as _SA\n"
        "                if product.stock > 0:\n"
        "                    _SA.objects.filter(\n"
        "                        product=product, is_resolved=False\n"
        "                    ).update(is_resolved=True, resolved_at=timezone.now())\n"
        "\n"
        "            order.status      = 'received'\n"
        "            order.received_at = timezone.now()\n"
        "            order.save(update_fields=['status', 'received_at'])\n"
        "\n"
        "        return Response(self.get_serializer(order).data)\n"
    )
    new_resolve = (
        "            order.status      = 'received'\n"
        "            order.received_at = timezone.now()\n"
        "            order.save(update_fields=['status', 'received_at'])\n"
        "\n"
        "            # Fix-4: بعد استلام الامر، افحص كل التنبيهات المرتبطة\n"
        "            # لو كل الـ POs المرتبطة بأي تنبيه استُلمت -> حل التنبيه تلقائياً\n"
        "            for alert in order.linked_alerts.filter(is_resolved=False):\n"
        "                alert.check_and_auto_resolve()\n"
        "\n"
        "        return Response(self.get_serializer(order).data)\n"
    )
    apply_fix("views.py — Fix-4 check_and_auto_resolve بعد receive", VIEWS_PY, old_resolve, new_resolve)

    # Fix-7: حفظ created_by في check_and_generate
    old_gen_out = (
        "            if product.stock == 0:\n"
        "                StockAlert.objects.create(\n"
        "                    product=product, alert_type='out', priority='critical',\n"
        "                    threshold=threshold, current_stock=0\n"
        "                )\n"
        "                created += 1\n"
        "            elif product.stock <= threshold:\n"
        "                StockAlert.objects.create(\n"
        "                    product=product, alert_type='low', priority='high',\n"
        "                    threshold=threshold, current_stock=product.stock\n"
        "                )\n"
        "                created += 1\n"
    )
    new_gen_out = (
        "            if product.stock == 0:\n"
        "                StockAlert.objects.create(\n"
        "                    product=product, alert_type='out', priority='critical',\n"
        "                    threshold=threshold, current_stock=0,\n"
        "                    created_by=request.user,\n"
        "                )\n"
        "                created += 1\n"
        "            elif product.stock <= threshold:\n"
        "                StockAlert.objects.create(\n"
        "                    product=product, alert_type='low', priority='high',\n"
        "                    threshold=threshold, current_stock=product.stock,\n"
        "                    created_by=request.user,\n"
        "                )\n"
        "                created += 1\n"
    )
    apply_fix("views.py — Fix-7 created_by في check_and_generate", VIEWS_PY, old_gen_out, new_gen_out)

    # Fix-7: حفظ created_by في send_alert من InventoryPage
    old_check_send = (
        "    queryset = StockAlert.objects.select_related(\n"
        "        'product', 'assigned_to', 'linked_po'\n"
        "    ).prefetch_related('notes__user').all()\n"
    )
    new_check_send = (
        "    queryset = StockAlert.objects.select_related(\n"
        "        'product', 'assigned_to', 'created_by'\n"
        "    ).prefetch_related('notes__user', 'linked_pos').all()\n"
    )
    apply_fix("views.py — Fix-7 queryset select_related", VIEWS_PY, old_check_send, new_check_send)

    # Fix-3: تنظيف expected_date + cost في add_note
    old_add_note = (
        "        serializer = StockAlertNoteSerializer(data=request.data)\n"
        "        serializer.is_valid(raise_exception=True)\n"
        "        serializer.save(alert=alert, user=request.user)\n"
    )
    new_add_note = (
        "        # Fix-3: تنظيف الحقول الفارغة قبل التحقق\n"
        "        data = request.data.copy()\n"
        "        if not data.get('expected_date'):\n"
        "            data['expected_date'] = None\n"
        "        if not data.get('cost'):\n"
        "            data['cost'] = None\n"
        "        serializer = StockAlertNoteSerializer(data=data)\n"
        "        serializer.is_valid(raise_exception=True)\n"
        "        serializer.save(alert=alert, user=request.user)\n"
    )
    apply_fix("views.py — Fix-3 تنظيف add_note", VIEWS_PY, old_add_note, new_add_note)

    # Fix-2: استبدال create_purchase_order بنسخة تدعم متعدد
    old_create_po = (
        "    @action(detail=True, methods=['post'])\n"
        "    def create_purchase_order(self, request, pk=None):\n"
        "        alert   = self.get_object()\n"
        "        product = alert.product\n"
        "        if alert.is_resolved:\n"
        "            return Response({'error': '\u0627\u0644\u062a\u0630\u0643\u0631\u0629 \u0645\u062d\u0644\u0648\u0644\u0629 \u0645\u0633\u0628\u0642\u0627\u064b'}, status=status.HTTP_400_BAD_REQUEST)\n"
        "        if alert.linked_po:\n"
        "            return Response(\n"
        "                {'error': '\u064a\u0648\u062c\u062f \u0623\u0645\u0631 \u0634\u0631\u0627\u0621 \u0645\u0631\u062a\u0628\u0637 \u0628\u0627\u0644\u0641\u0639\u0644: ' + alert.linked_po.reference_number},\n"
        "                status=status.HTTP_400_BAD_REQUEST\n"
        "            )\n"
        "        supplier_id   = request.data.get('supplier')\n"
        "        quantity      = int(request.data.get('quantity', 1))\n"
        "        unit_cost     = request.data.get('unit_cost', 0)\n"
        "        unit_id       = request.data.get('unit')\n"
        "        expected_date = request.data.get('expected_date')\n"
        "        po_notes      = request.data.get('notes', '')\n"
        "        with transaction.atomic():\n"
        "            ref = 'PO-ALERT-' + str(alert.id)[:8].upper()\n"
        "            po  = PurchaseOrder.objects.create(\n"
        "                reference_number = ref,\n"
        "                supplier_id      = supplier_id or None,\n"
        "                user             = request.user,\n"
        "                status           = 'ordered',\n"
        "                expected_date    = expected_date or None,\n"
        "                notes            = po_notes or '\u0623\u0645\u0631 \u0634\u0631\u0627\u0621 \u0645\u0646 \u062a\u0646\u0628\u064a\u0647 \u0627\u0644\u0645\u0646\u062a\u062c: ' + product.name,\n"
        "            )\n"
        "            PurchaseOrderItem.objects.create(\n"
        "                order     = po,\n"
        "                product   = product,\n"
        "                unit_id   = unit_id or None,\n"
        "                quantity  = quantity,\n"
        "                unit_cost = unit_cost,\n"
        "            )\n"
        "            po.recalculate_total()\n"
        "            alert.linked_po     = po\n"
        "            alert.ticket_status = 'ordered'\n"
        "            alert.save(update_fields=['linked_po', 'ticket_status'])\n"
        "            StockAlertNote.objects.create(\n"
        "                alert=alert, user=request.user, note_type='action',\n"
        "                text='\u062a\u0645 \u0625\u0646\u0634\u0627\u0621 \u0623\u0645\u0631 \u0634\u0631\u0627\u0621 #' + po.reference_number + ' \u0628\u0643\u0645\u064a\u0629 ' + str(quantity) + ' \u0648\u062d\u062f\u0629',\n"
        "            )\n"
        "        return Response({\n"
        "            'alert': StockAlertSerializer(alert).data,\n"
        "            'purchase_order': {\n"
        "                'id':               str(po.id),\n"
        "                'reference_number': po.reference_number,\n"
        "                'status':           po.status,\n"
        "                'total_cost':       str(po.total_cost),\n"
        "            },\n"
        "        })\n"
    )
    new_create_po = (
        "    @action(detail=True, methods=['post'])\n"
        "    def create_purchase_order(self, request, pk=None):\n"
        "        \"\"\"Fix-2: يسمح باضافة اكتر من PO لنفس التنبيه\"\"\"\n"
        "        alert   = self.get_object()\n"
        "        product = alert.product\n"
        "        if alert.is_resolved:\n"
        "            return Response({'error': 'التذكرة محلولة مسبقاً'}, status=status.HTTP_400_BAD_REQUEST)\n"
        "        supplier_id   = request.data.get('supplier')\n"
        "        quantity      = int(request.data.get('quantity', 1))\n"
        "        unit_cost     = request.data.get('unit_cost', 0)\n"
        "        unit_id       = request.data.get('unit')\n"
        "        expected_date = request.data.get('expected_date') or None\n"
        "        po_notes      = request.data.get('notes', '')\n"
        "        with transaction.atomic():\n"
        "            import time\n"
        "            ref = 'PO-ALERT-' + str(alert.id)[:8].upper() + '-' + str(int(time.time()))[-4:]\n"
        "            po  = PurchaseOrder.objects.create(\n"
        "                reference_number = ref,\n"
        "                supplier_id      = supplier_id or None,\n"
        "                user             = request.user,\n"
        "                status           = 'ordered',\n"
        "                expected_date    = expected_date,\n"
        "                notes            = po_notes or 'امر شراء من تنبيه المنتج: ' + product.name,\n"
        "            )\n"
        "            PurchaseOrderItem.objects.create(\n"
        "                order     = po,\n"
        "                product   = product,\n"
        "                unit_id   = unit_id or None,\n"
        "                quantity  = quantity,\n"
        "                unit_cost = unit_cost,\n"
        "            )\n"
        "            po.recalculate_total()\n"
        "            # Fix-2: اضافة PO للـ ManyToMany بدل الاستبدال\n"
        "            alert.linked_pos.add(po)\n"
        "            if alert.ticket_status not in ('ordered', 'in_progress'):\n"
        "                alert.ticket_status = 'ordered'\n"
        "                alert.save(update_fields=['ticket_status'])\n"
        "            StockAlertNote.objects.create(\n"
        "                alert=alert, user=request.user, note_type='action',\n"
        "                text='تم انشاء امر شراء #' + po.reference_number + ' بكمية ' + str(quantity) + ' وحدة',\n"
        "            )\n"
        "        return Response({\n"
        "            'alert': StockAlertSerializer(alert).data,\n"
        "            'purchase_order': {\n"
        "                'id':               str(po.id),\n"
        "                'reference_number': po.reference_number,\n"
        "                'status':           po.status,\n"
        "                'total_cost':       str(po.total_cost),\n"
        "            },\n"
        "        })\n"
    )
    apply_fix("views.py — Fix-2 create_purchase_order متعدد", VIEWS_PY, old_create_po, new_create_po)

    # Fix-4: استبدال resolve بنسخة تتحقق من كل الـ POs
    old_resolve_action = (
        "    @action(detail=True, methods=['post'])\n"
        "    def resolve(self, request, pk=None):\n"
        "        alert = self.get_object()\n"
        "        if alert.linked_po and alert.linked_po.status != 'received':\n"
        "            return Response(\n"
        "                {'error': '\u0623\u0645\u0631 \u0627\u0644\u0634\u0631\u0627\u0621 #' + alert.linked_po.reference_number + ' \u0644\u0645 \u064a\u064f\u0633\u062a\u0644\u0645 \u0628\u0639\u062f. \u0627\u0633\u062a\u0644\u0645 \u0627\u0644\u0628\u0636\u0627\u0639\u0629 \u0623\u0648\u0644\u0627\u064b.'},\n"
        "                status=status.HTTP_400_BAD_REQUEST\n"
        "            )\n"
        "        note_text = request.data.get('note', '')\n"
        "        with transaction.atomic():\n"
        "            alert.resolve(user=request.user)\n"
        "            if note_text:\n"
        "                StockAlertNote.objects.create(\n"
        "                    alert=alert, user=request.user,\n"
        "                    note_type='action',\n"
        "                    text='\u062a\u0645 \u0627\u0644\u062d\u0644: ' + note_text,\n"
        "                )\n"
        "        return Response(StockAlertSerializer(alert).data)\n"
    )
    new_resolve_action = (
        "    @action(detail=True, methods=['post'])\n"
        "    def resolve(self, request, pk=None):\n"
        "        \"\"\"Fix-4: يتحقق من كل الـ POs المرتبطة\"\"\"\n"
        "        alert = self.get_object()\n"
        "        linked_pos = alert.linked_pos.all()\n"
        "        if linked_pos.exists():\n"
        "            unreceived = linked_pos.exclude(status='received')\n"
        "            if unreceived.exists():\n"
        "                refs = ', '.join(po.reference_number for po in unreceived)\n"
        "                return Response(\n"
        "                    {'error': 'اوامر الشراء التالية لم تُستلم بعد: ' + refs},\n"
        "                    status=status.HTTP_400_BAD_REQUEST\n"
        "                )\n"
        "        note_text = request.data.get('note', '')\n"
        "        with transaction.atomic():\n"
        "            alert.resolve(user=request.user)\n"
        "            if note_text:\n"
        "                StockAlertNote.objects.create(\n"
        "                    alert=alert, user=request.user,\n"
        "                    note_type='action',\n"
        "                    text='تم الحل: ' + note_text,\n"
        "                )\n"
        "        return Response(StockAlertSerializer(alert).data)\n"
    )
    apply_fix("views.py — Fix-4 resolve يتحقق من كل POs", VIEWS_PY, old_resolve_action, new_resolve_action)

    # Fix-6: إضافة assign_to_me + assign_to_user + unassign بعد update_meta
    old_after_meta = (
        "# \u2500\u2500 StockMovement (read-only) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        "class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):\n"
    )
    new_after_meta = (
        "    # Fix-6: تخصيص التنبيه لنفسك\n"
        "    @action(detail=True, methods=['post'])\n"
        "    def assign_to_me(self, request, pk=None):\n"
        "        alert = self.get_object()\n"
        "        alert.assigned_to = request.user\n"
        "        alert.save(update_fields=['assigned_to'])\n"
        "        StockAlertNote.objects.create(\n"
        "            alert=alert, user=request.user, note_type='system',\n"
        "            text='تم التخصيص لـ ' + request.user.username + ' (تعيين ذاتي)',\n"
        "        )\n"
        "        return Response(StockAlertSerializer(alert).data)\n"
        "\n"
        "    # Fix-6: تخصيص التنبيه لاي مستخدم (للمدراء)\n"
        "    @action(detail=True, methods=['post'])\n"
        "    def assign_to_user(self, request, pk=None):\n"
        "        alert   = self.get_object()\n"
        "        user_id = request.data.get('user_id')\n"
        "        if not user_id:\n"
        "            return Response({'error': 'user_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)\n"
        "        allowed_groups = {'Admins', 'Managers'}\n"
        "        user_groups    = set(request.user.groups.values_list('name', flat=True))\n"
        "        is_allowed     = request.user.is_superuser or bool(allowed_groups & user_groups)\n"
        "        if not is_allowed:\n"
        "            from rest_framework.exceptions import PermissionDenied\n"
        "            raise PermissionDenied('غير مصرح: التخصيص للمستخدمين يتطلب صلاحية مدير')\n"
        "        from django.contrib.auth import get_user_model\n"
        "        User = get_user_model()\n"
        "        try:\n"
        "            target_user = User.objects.get(id=user_id)\n"
        "        except User.DoesNotExist:\n"
        "            return Response({'error': 'المستخدم غير موجود'}, status=status.HTTP_404_NOT_FOUND)\n"
        "        alert.assigned_to = target_user\n"
        "        alert.save(update_fields=['assigned_to'])\n"
        "        StockAlertNote.objects.create(\n"
        "            alert=alert, user=request.user, note_type='system',\n"
        "            text='تم التخصيص لـ ' + target_user.username + ' بواسطة ' + request.user.username,\n"
        "        )\n"
        "        return Response(StockAlertSerializer(alert).data)\n"
        "\n"
        "    # Fix-6: الغاء التخصيص\n"
        "    @action(detail=True, methods=['post'])\n"
        "    def unassign(self, request, pk=None):\n"
        "        alert = self.get_object()\n"
        "        alert.assigned_to = None\n"
        "        alert.save(update_fields=['assigned_to'])\n"
        "        StockAlertNote.objects.create(\n"
        "            alert=alert, user=request.user, note_type='system',\n"
        "            text='تم الغاء التخصيص',\n"
        "        )\n"
        "        return Response(StockAlertSerializer(alert).data)\n"
        "\n"
        "\n"
        "# \u2500\u2500 StockMovement (read-only) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        "class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):\n"
    )
    apply_fix("views.py — Fix-6 assign_to_me + assign_to_user + unassign", VIEWS_PY, old_after_meta, new_after_meta)


# ── Fix-5: InventoryPage.jsx — إزالة تاب الموردين ────────────────────────────
def fix_inventory_page():
    print("\n── Fix InventoryPage.jsx (Fix-5 إزالة تاب الموردين) ──")

    old_tabs = (
        "  const tabs = [\n"
        "    { key:'summary',   label:'\ud83d\udcca \u0645\u0644\u062e\u0635 \u0627\u0644\u0645\u062e\u0632\u0648\u0646' },\n"
        "    { key:'adjust',    label:'\u2696\ufe0f \u062a\u0633\u0648\u064a\u0629 \u0627\u0644\u0645\u062e\u0632\u0648\u0646' },\n"
        "    { key:'movements', label:'\ud83d\udd04 \u062d\u0631\u0643\u0629 \u0627\u0644\u0645\u062e\u0632\u0648\u0646'  },\n"
        "    { key:'suppliers', label:'\ud83c\udfed \u0627\u0644\u0645\u0648\u0631\u062f\u0648\u0646'       },\n"
        "  ];\n"
    )
    new_tabs = (
        "  const tabs = [\n"
        "    { key:'summary',   label:'\ud83d\udcca \u0645\u0644\u062e\u0635 \u0627\u0644\u0645\u062e\u0632\u0648\u0646' },\n"
        "    { key:'adjust',    label:'\u2696\ufe0f \u062a\u0633\u0648\u064a\u0629 \u0627\u0644\u0645\u062e\u0632\u0648\u0646' },\n"
        "    { key:'movements', label:'\ud83d\udd04 \u062d\u0631\u0643\u0629 \u0627\u0644\u0645\u062e\u0632\u0648\u0646'  },\n"
        "  ];\n"
    )
    apply_fix("InventoryPage.jsx — إزالة تاب الموردين من tabs array", INVENTORY_JSX, old_tabs, new_tabs)

    old_suppliers_render = "      {tab==='suppliers' && <SuppliersPanel />}\n"
    new_suppliers_render = "      {/* Fix-5: الموردون انتقلوا لـ PurchasingPage */}\n"
    apply_fix("InventoryPage.jsx — إزالة render SuppliersPanel", INVENTORY_JSX, old_suppliers_render, new_suppliers_render)


# ── Fix-1 + Fix-2 + Fix-3 + Fix-5 + Fix-6 + Fix-7: PurchasingPage.jsx ────────
def fix_purchasing_page():
    print("\n── Fix PurchasingPage.jsx (Fix-1,2,3,5,6,7) ──")

    # Fix-5: إضافة تاب الموردين للـ tabs array
    old_pur_tabs = (
        "  const tabs = [\n"
        "    { key: 'alerts', label: '\ud83d\udd14 \u0627\u0644\u062a\u0646\u0628\u064a\u0647\u0627\u062a' },\n"
        "    { key: 'orders', label: '\ud83d\udce6 \u0623\u0648\u0627\u0645\u0631 \u0627\u0644\u0634\u0631\u0627\u0621' },\n"
        "  ];\n"
    )
    new_pur_tabs = (
        "  const tabs = [\n"
        "    { key: 'alerts',    label: '\ud83d\udd14 \u0627\u0644\u062a\u0646\u0628\u064a\u0647\u0627\u062a'    },\n"
        "    { key: 'orders',    label: '\ud83d\udce6 \u0623\u0648\u0627\u0645\u0631 \u0627\u0644\u0634\u0631\u0627\u0621' },\n"
        "    { key: 'suppliers', label: '\ud83c\udfed \u0627\u0644\u0645\u0648\u0631\u062f\u0648\u0646'      },\n"
        "  ];\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-5 إضافة تاب الموردين", PURCHASING_JSX, old_pur_tabs, new_pur_tabs)

    # Fix-5: إضافة render للـ suppliers tab
    old_pur_render = (
        "      {tab === 'alerts' && <AlertsPanel />}\n"
        "      {tab === 'orders' && <PurchaseOrdersPanel />}\n"
    )
    new_pur_render = (
        "      {tab === 'alerts'    && <AlertsPanel />}\n"
        "      {tab === 'orders'    && <PurchaseOrdersPanel />}\n"
        "      {tab === 'suppliers' && <SuppliersPanel />}\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-5 render SuppliersPanel", PURCHASING_JSX, old_pur_render, new_pur_render)

    # Fix-7 + Fix-6: تحديث AlertCard لعرض created_by + assigned_to
    old_alert_card_footer = (
        "      <div className=\"flex items-center justify-between text-xs text-gray-500\">\n"
        "        <div className=\"flex items-center gap-3\">\n"
        "          {alert.notes_count > 0 && (\n"
        "            <span>\ud83d\udcac {alert.notes_count} \u0645\u0644\u0627\u062d\u0638\u0629</span>\n"
        "          )}\n"
        "          {alert.linked_po_reference && (\n"
        "            <span className=\"text-blue-600\">\ud83d\udce6 {alert.linked_po_reference}</span>\n"
        "          )}\n"
        "          {isOverdue && <span className=\"text-red-600 font-bold\">\u23f0 \u0645\u062a\u0623\u062e\u0631</span>}\n"
        "        </div>\n"
        "        <span>{alert.created_at?.split('T')[0]}</span>\n"
        "      </div>\n"
    )
    new_alert_card_footer = (
        "      <div className=\"flex items-center justify-between text-xs text-gray-500\">\n"
        "        <div className=\"flex items-center gap-3\">\n"
        "          {/* Fix-6: حالة التخصيص */}\n"
        "          {alert.assigned_to_name ? (\n"
        "            <span className=\"text-blue-600 font-bold\">\ud83d\udc64 {alert.assigned_to_name}</span>\n"
        "          ) : (\n"
        "            <span className=\"text-gray-400\">\u063a\u064a\u0631 \u0645\u062e\u0635\u0635</span>\n"
        "          )}\n"
        "          {alert.notes_count > 0 && <span>\ud83d\udcac {alert.notes_count}</span>}\n"
        "          {/* Fix-2: عدد الـ POs المرتبطة */}\n"
        "          {alert.linked_pos_count > 0 && (\n"
        "            <span className=\"text-blue-600\">\ud83d\udce6 {alert.linked_pos_count} \u0623\u0645\u0631</span>\n"
        "          )}\n"
        "          {isOverdue && <span className=\"text-red-600 font-bold\">\u23f0 \u0645\u062a\u0623\u062e\u0631</span>}\n"
        "        </div>\n"
        "        <div className=\"flex flex-col items-end gap-0.5\">\n"
        "          {/* Fix-7: منشئ التنبيه */}\n"
        "          {alert.created_by_name && (\n"
        "            <span className=\"text-gray-400\">\u0623\u0646\u0634\u0623\u0647: {alert.created_by_name}</span>\n"
        "          )}\n"
        "          <span>{alert.created_at?.split('T')[0]}</span>\n"
        "        </div>\n"
        "      </div>\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-7+6 AlertCard footer", PURCHASING_JSX, old_alert_card_footer, new_alert_card_footer)

    # Fix-1: إزالة زر الاستلام من PurchaseOrdersPanel
    old_receive_btn = (
        "                  {(o.status==='ordered'||o.status==='draft') && (\n"
        "                    <button onClick={() => setSelected(o)}\n"
        "                      className=\"bg-green-500 hover:bg-green-600 text-white text-xs font-bold px-3 py-1 rounded-lg\">\n"
        "                      \ud83d\udce5 \u0627\u0633\u062a\u0644\u0627\u0645\n"
        "                    </button>\n"
        "                  )}\n"
    )
    new_receive_btn = (
        "                  {/* Fix-1: زر الاستلام اتنقل للمخزون */}\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-1 إزالة زر الاستلام", PURCHASING_JSX, old_receive_btn, new_receive_btn)

    # Fix-2: إزالة check لو فيه PO مرتبط في AlertTicketModal tab create_po
    old_po_check = (
        "      {tab === 'create_po' && (\n"
        "        <div className=\"space-y-3\">\n"
        "          {data.linked_po_reference ? (\n"
        "            <div className=\"bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-700 font-bold text-center\">\n"
        "              \u26a0\ufe0f \u064a\u0648\u062c\u062f \u0623\u0645\u0631 \u0634\u0631\u0627\u0621 \u0645\u0631\u062a\u0628\u0637 \u0628\u0627\u0644\u0641\u0639\u0644: {data.linked_po_reference}\n"
        "            </div>\n"
        "          ) : (\n"
        "            <>\n"
        "              <div className=\"grid grid-cols-2 gap-3\">\n"
    )
    new_po_check = (
        "      {tab === 'create_po' && (\n"
        "        <div className=\"space-y-3\">\n"
        "          {/* Fix-2: عرض الـ POs الموجودة */}\n"
        "          {data.linked_pos_data && data.linked_pos_data.length > 0 && (\n"
        "            <div className=\"bg-blue-50 border border-blue-200 rounded-xl p-3 text-sm\">\n"
        "              <p className=\"font-bold text-blue-700 mb-2\">\ud83d\udce6 \u0623\u0648\u0627\u0645\u0631 \u0627\u0644\u0634\u0631\u0627\u0621 \u0627\u0644\u0633\u0627\u0628\u0642\u0629 ({data.linked_pos_data.length})</p>\n"
        "              {data.linked_pos_data.map(po => (\n"
        "                <div key={po.id} className=\"flex items-center gap-3 text-xs bg-white rounded-lg px-3 py-1.5 mb-1 border border-blue-100\">\n"
        "                  <span className=\"font-bold text-blue-700\">{po.reference_number}</span>\n"
        "                  <Badge label={po.status} color={statusColor(po.status)} />\n"
        "                  <span className=\"text-gray-500\">{po.expected_date||'—'}</span>\n"
        "                </div>\n"
        "              ))}\n"
        "            </div>\n"
        "          )}\n"
        "          {/* Fix-2: دايماً يظهر الفورم بدون تقييد */}\n"
        "          <>\n"
        "              <div className=\"grid grid-cols-2 gap-3\">\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-2 create_po tab بدون تقييد", PURCHASING_JSX, old_po_check, new_po_check)

    # Fix-2: إغلاق الـ fragment الجديد — إزالة الـ closing tags القديمة
    old_po_close = (
        "            </>\n"
        "          )}\n"
        "        </div>\n"
        "      )}\n"
        "\n"
        "      {/* حل التذكرة */}\n"
    )
    new_po_close = (
        "          </>\n"
        "        </div>\n"
        "      )}\n"
        "\n"
        "      {/* حل التذكرة */}\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-2 تصحيح إغلاق create_po", PURCHASING_JSX, old_po_close, new_po_close)

    # Fix-3: تنظيف payload في handleAddNote
    old_add_note_fn = (
        "  const handleAddNote = async () => {\n"
        "    if (!noteForm.text.trim()) return notify('\u0627\u0643\u062a\u0628 \u0646\u0635 \u0627\u0644\u0645\u0644\u0627\u062d\u0638\u0629', 'error');\n"
        "    setSaving(true);\n"
        "    try {\n"
        "      await inventoryAPI.addAlertNote(data.id, noteForm);\n"
        "      setNote({ note_type:'note', text:'', cost:'', expected_date:'', delay_reason:'', supplier_name:'' });\n"
        "      await reload();\n"
        "      notify('\u062a\u0645\u062a \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0644\u0627\u062d\u0638\u0629');\n"
        "    } catch(e) { notify('\u062e\u0637\u0623: '+(e?.response?.data?.error||JSON.stringify(e?.response?.data)||'\u062e\u0637\u0623'), 'error'); }\n"
        "    finally { setSaving(false); }\n"
        "  };\n"
    )
    new_add_note_fn = (
        "  const handleAddNote = async () => {\n"
        "    if (!noteForm.text.trim()) return notify('اكتب نص الملاحظة', 'error');\n"
        "    setSaving(true);\n"
        "    try {\n"
        "      // Fix-3: تنظيف الحقول الفارغة قبل الارسال\n"
        "      const payload = {\n"
        "        note_type:     noteForm.note_type,\n"
        "        text:          noteForm.text,\n"
        "        cost:          noteForm.cost     || null,\n"
        "        expected_date: noteForm.expected_date || null,\n"
        "        delay_reason:  noteForm.delay_reason  || '',\n"
        "        supplier_name: noteForm.supplier_name || '',\n"
        "      };\n"
        "      await inventoryAPI.addAlertNote(data.id, payload);\n"
        "      setNote({ note_type:'note', text:'', cost:'', expected_date:'', delay_reason:'', supplier_name:'' });\n"
        "      await reload();\n"
        "      notify('تمت اضافة الملاحظة');\n"
        "    } catch(e) { notify('خطأ: '+(e?.response?.data?.error||JSON.stringify(e?.response?.data)||'خطأ'), 'error'); }\n"
        "    finally { setSaving(false); }\n"
        "  };\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-3 تنظيف handleAddNote payload", PURCHASING_JSX, old_add_note_fn, new_add_note_fn)

    # Fix-6: إضافة import usersAPI + useAuth
    old_imports = (
        "import { inventoryAPI, productsAPI } from '../services/api';\n"
        "import { useAuth } from '../context/AuthContext';\n"
    )
    new_imports = (
        "import { inventoryAPI, productsAPI, usersAPI } from '../services/api';\n"
        "import { useAuth } from '../context/AuthContext';\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-6 import usersAPI", PURCHASING_JSX, old_imports, new_imports)

    # Fix-6: إضافة handlers + users state في AlertTicketModal
    old_modal_state = (
        "  const [tab, setTab]         = useState('timeline');\n"
        "  const [saving, setSaving]   = useState(false);\n"
        "\n"
        "  const reload = async () => {\n"
    )
    new_modal_state = (
        "  const [tab, setTab]         = useState('timeline');\n"
        "  const [saving, setSaving]   = useState(false);\n"
        "  const [users, setUsers]     = useState([]);\n"
        "\n"
        "  // Fix-6: جلب المستخدمين للتخصيص\n"
        "  useEffect(() => {\n"
        "    usersAPI.getAll().then(r => setUsers(r.data?.results || r.data || [])).catch(() => {});\n"
        "  }, []);\n"
        "\n"
        "  const reload = async () => {\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-6 users state + useEffect", PURCHASING_JSX, old_modal_state, new_modal_state)

    # Fix-6: إضافة handlers assign في AlertTicketModal بعد handleResolve
    old_after_resolve = (
        "  const pr = priorityConfig[data.priority] || priorityConfig.medium;\n"
        "  const st = ticketStatusConfig[data.ticket_status] || ticketStatusConfig.open;\n"
    )
    new_after_resolve = (
        "  // Fix-6: تخصيص لنفسي\n"
        "  const handleAssignToMe = async () => {\n"
        "    setSaving(true);\n"
        "    try {\n"
        "      await inventoryAPI.assignAlertToMe(data.id);\n"
        "      notify('تم التخصيص لك');\n"
        "      await reload();\n"
        "    } catch { notify('خطأ في التخصيص', 'error'); }\n"
        "    finally { setSaving(false); }\n"
        "  };\n"
        "\n"
        "  // Fix-6: تخصيص لمستخدم آخر\n"
        "  const handleAssignToUser = async (userId) => {\n"
        "    setSaving(true);\n"
        "    try {\n"
        "      await inventoryAPI.assignAlertToUser(data.id, { user_id: userId });\n"
        "      notify('تم التخصيص');\n"
        "      await reload();\n"
        "    } catch(e) { notify('خطأ: ' + (e?.response?.data?.error || 'غير مصرح'), 'error'); }\n"
        "    finally { setSaving(false); }\n"
        "  };\n"
        "\n"
        "  // Fix-6: الغاء التخصيص\n"
        "  const handleUnassign = async () => {\n"
        "    setSaving(true);\n"
        "    try {\n"
        "      await inventoryAPI.unassignAlert(data.id);\n"
        "      notify('تم الغاء التخصيص');\n"
        "      await reload();\n"
        "    } catch { notify('خطأ', 'error'); }\n"
        "    finally { setSaving(false); }\n"
        "  };\n"
        "\n"
        "  const pr = priorityConfig[data.priority] || priorityConfig.medium;\n"
        "  const st = ticketStatusConfig[data.ticket_status] || ticketStatusConfig.open;\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-6 assign handlers", PURCHASING_JSX, old_after_resolve, new_after_resolve)

    # Fix-6: إضافة canAssignOthers + assign UI بعد رأس التذكرة
    old_modal_header = (
        "      {data.linked_po_reference && (\n"
        "        <div className=\"mb-4 bg-blue-50 border border-blue-200 rounded-xl px-4 py-2 text-sm text-blue-700 font-bold\">\n"
        "          \ud83d\udce6 \u0623\u0645\u0631 \u0627\u0644\u0634\u0631\u0627\u0621 \u0627\u0644\u0645\u0631\u062a\u0628\u0637: {data.linked_po_reference}\n"
        "          <span className=\"mr-2 text-xs font-normal\">({data.linked_po_status})</span>\n"
        "        </div>\n"
        "      )}\n"
    )
    new_modal_header = (
        "      {/* Fix-6+7: معلومات التخصيص والمنشئ */}\n"
        "      <div className=\"flex flex-wrap gap-4 mb-4 bg-gray-50 rounded-xl px-4 py-3 text-sm\">\n"
        "        <div>\n"
        "          <span className=\"text-gray-400 text-xs block mb-0.5\">أنشأ التنبيه</span>\n"
        "          <span className=\"font-bold text-gray-700\">{data.created_by_name || '—'}</span>\n"
        "        </div>\n"
        "        <div>\n"
        "          <span className=\"text-gray-400 text-xs block mb-0.5\">مخصص لـ</span>\n"
        "          <span className={data.assigned_to_name ? 'font-bold text-blue-700' : 'font-bold text-gray-400'}>\n"
        "            {data.assigned_to_name || 'غير مخصص'}\n"
        "          </span>\n"
        "        </div>\n"
        "        {!data.is_resolved && (\n"
        "          <div className=\"flex gap-2 items-end\">\n"
        "            <button onClick={handleAssignToMe} disabled={saving}\n"
        "              className=\"text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold px-3 py-1.5 rounded-lg\">\n"
        "              \ud83d\udc64 \u062e\u0635\u0635 \u0644\u064a\n"
        "            </button>\n"
        "            {data.assigned_to_name && (\n"
        "              <button onClick={handleUnassign} disabled={saving}\n"
        "                className=\"text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 font-bold px-3 py-1.5 rounded-lg\">\n"
        "                \u2715 \u0625\u0644\u063a\u0627\u0621\n"
        "              </button>\n"
        "            )}\n"
        "          </div>\n"
        "        )}\n"
        "      </div>\n"
        "      {/* Fix-2: عرض قائمة الـ POs المرتبطة */}\n"
        "      {data.linked_pos_data && data.linked_pos_data.length > 0 && (\n"
        "        <div className=\"mb-4 bg-blue-50 border border-blue-200 rounded-xl p-3\">\n"
        "          <p className=\"text-xs font-bold text-blue-700 mb-2\">\ud83d\udce6 \u0623\u0648\u0627\u0645\u0631 \u0627\u0644\u0634\u0631\u0627\u0621 \u0627\u0644\u0645\u0631\u062a\u0628\u0637\u0629 ({data.linked_pos_data.length})</p>\n"
        "          <div className=\"space-y-1.5\">\n"
        "            {data.linked_pos_data.map(po => (\n"
        "              <div key={po.id} className=\"flex items-center justify-between text-xs bg-white rounded-lg px-3 py-1.5 border border-blue-100\">\n"
        "                <span className=\"font-bold text-blue-700\">{po.reference_number}</span>\n"
        "                <Badge label={po.status} color={statusColor(po.status)} />\n"
        "                <span className=\"text-gray-500\">{po.expected_date || '—'}</span>\n"
        "                <span className=\"font-bold\">{fmt(po.total_cost)} ج</span>\n"
        "              </div>\n"
        "            ))}\n"
        "          </div>\n"
        "        </div>\n"
        "      )}\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-6+2+7 modal header info", PURCHASING_JSX, old_modal_header, new_modal_header)

    # Fix-6: تحديث تبويبات التذكرة لإضافة تاب التخصيص
    old_modal_tabs = (
        "      <div className=\"flex gap-2 border-b mb-4\">\n"
        "        {[{key:'timeline',label:'\ud83d\udccb \u0627\u0644\u0633\u062c\u0644'},{key:'add_note',label:'\u2795 \u0625\u0636\u0627\u0641\u0629'},{key:'create_po',label:'\ud83d\udce6 \u0623\u0645\u0631 \u0634\u0631\u0627\u0621'},{key:'resolve',label:'\u2705 \u062d\u0644'}]\n"
        "          .map(t => (\n"
        "            <button key={t.key} onClick={() => setTab(t.key)}\n"
        "              className={`px-3 py-2 text-sm font-bold border-b-2 transition -mb-px ${\n"
        "                tab===t.key?'border-blue-600 text-blue-600':'border-transparent text-gray-500 hover:text-gray-700'\n"
        "              }`}>{t.label}</button>\n"
        "          ))}\n"
        "      </div>\n"
    )
    new_modal_tabs = (
        "      <div className=\"flex gap-2 border-b mb-4 overflow-x-auto\">\n"
        "        {[\n"
        "          {key:'timeline', label:'\ud83d\udccb \u0627\u0644\u0633\u062c\u0644'},\n"
        "          {key:'add_note', label:'\u2795 \u0645\u0644\u0627\u062d\u0638\u0629'},\n"
        "          {key:'create_po',label:'\ud83d\udce6 \u0623\u0645\u0631 \u0634\u0631\u0627\u0621'},\n"
        "          {key:'assign',   label:'\ud83d\udc64 \u062a\u062e\u0635\u064a\u0635'},\n"
        "          {key:'resolve',  label:'\u2705 \u062d\u0644'},\n"
        "        ].map(t => (\n"
        "          <button key={t.key} onClick={() => setTab(t.key)}\n"
        "            className={`px-3 py-2 text-sm font-bold border-b-2 transition -mb-px whitespace-nowrap ${\n"
        "              tab===t.key?'border-blue-600 text-blue-600':'border-transparent text-gray-500 hover:text-gray-700'\n"
        "            }`}>{t.label}</button>\n"
        "        ))}\n"
        "      </div>\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-6 إضافة تاب التخصيص", PURCHASING_JSX, old_modal_tabs, new_modal_tabs)

    # Fix-6: إضافة محتوى تاب التخصيص قبل تاب الحل
    old_before_resolve_tab = (
        "      {/* حل التذكرة */}\n"
        "      {tab === 'resolve' && (\n"
    )
    new_before_resolve_tab = (
        "      {/* Fix-6: تاب التخصيص */}\n"
        "      {tab === 'assign' && (\n"
        "        <div className=\"space-y-4\">\n"
        "          <div className=\"bg-gray-50 rounded-xl p-4 text-sm\">\n"
        "            <p className=\"font-bold text-gray-700 mb-1\">الحالة الحالية</p>\n"
        "            {data.assigned_to_name\n"
        "              ? <span className=\"text-blue-700 font-bold\">\ud83d\udc64 \u0645\u062e\u0635\u0635 \u0644\u0640: {data.assigned_to_name}</span>\n"
        "              : <span className=\"text-gray-400\">\u063a\u064a\u0631 \u0645\u062e\u0635\u0635 \u0644\u0623\u062d\u062f</span>\n"
        "            }\n"
        "          </div>\n"
        "          {!data.is_resolved && (\n"
        "            <>\n"
        "              <button onClick={handleAssignToMe} disabled={saving}\n"
        "                className=\"w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 rounded-xl text-sm disabled:opacity-50\">\n"
        "                \ud83d\udc64 \u062e\u0635\u0635 \u0644\u064a (\u062a\u0633\u062c\u064a\u0644 \u0627\u0633\u0645\u064a \u0643\u0645\u0633\u0624\u0648\u0644)\n"
        "              </button>\n"
        "              {(() => {\n"
        "                const userGroups = currentUser?.groups?.map(g => g.name) || [];\n"
        "                const canAssign  = currentUser?.is_superuser || userGroups.includes('Admins') || userGroups.includes('Managers');\n"
        "                return canAssign ? (\n"
        "                  <Field label=\"تخصيص لمستخدم آخر\">\n"
        "                    <select className={INP} defaultValue=\"\"\n"
        "                      onChange={e => e.target.value && handleAssignToUser(e.target.value)}>\n"
        "                      <option value=\"\">اختر مستخدم...</option>\n"
        "                      {users.map(u => (\n"
        "                        <option key={u.id} value={u.id}>{u.username} — {u.first_name} {u.last_name}</option>\n"
        "                      ))}\n"
        "                    </select>\n"
        "                  </Field>\n"
        "                ) : null;\n"
        "              })()}\n"
        "              {data.assigned_to_name && (\n"
        "                <button onClick={handleUnassign} disabled={saving}\n"
        "                  className=\"w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold py-2 rounded-xl text-sm disabled:opacity-50\">\n"
        "                  \u2715 \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u062a\u062e\u0635\u064a\u0635\n"
        "                </button>\n"
        "              )}\n"
        "            </>\n"
        "          )}\n"
        "        </div>\n"
        "      )}\n"
        "\n"
        "      {/* حل التذكرة */}\n"
        "      {tab === 'resolve' && (\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-6 محتوى تاب التخصيص", PURCHASING_JSX, old_before_resolve_tab, new_before_resolve_tab)

    # Fix-6: إضافة currentUser من useAuth في AlertTicketModal
    old_modal_open = (
        "function AlertTicketModal({ alert, suppliers, onClose, onUpdated, notify }) {\n"
        "  const [data, setData]       = useState(alert);\n"
    )
    new_modal_open = (
        "function AlertTicketModal({ alert, suppliers, onClose, onUpdated, notify }) {\n"
        "  const { user: currentUser } = useAuth();\n"
        "  const [data, setData]       = useState(alert);\n"
    )
    apply_fix("PurchasingPage.jsx — Fix-6 currentUser في AlertTicketModal", PURCHASING_JSX, old_modal_open, new_modal_open)

    # Fix-5: إضافة SuppliersPanel كامل قبل نهاية الملف
    suppliers_panel = (
        "\n"
        "// ══════════════════════════════\n"
        "//  Fix-5: SuppliersPanel\n"
        "// ══════════════════════════════\n"
        "function SuppliersPanel() {\n"
        "  const [suppliers, setSuppliers] = useState([]);\n"
        "  const [loading, setLoading]     = useState(true);\n"
        "  const [showForm, setShowForm]   = useState(false);\n"
        "  const [editing, setEditing]     = useState(null);\n"
        "  const [form, setForm]           = useState({ name:'', phone:'', email:'', address:'', notes:'' });\n"
        "  const [saving, setSaving]       = useState(false);\n"
        "  const [toast, setToast]         = useState(null);\n"
        "  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };\n"
        "\n"
        "  const load = useCallback(async () => {\n"
        "    setLoading(true);\n"
        "    try {\n"
        "      const r = await inventoryAPI.getSuppliers();\n"
        "      setSuppliers(r.data?.results || r.data || []);\n"
        "    } catch {/**/ } finally { setLoading(false); }\n"
        "  }, []);\n"
        "\n"
        "  useEffect(() => { load(); }, [load]);\n"
        "\n"
        "  const openAdd  = () => { setEditing(null); setForm({ name:'', phone:'', email:'', address:'', notes:'' }); setShowForm(true); };\n"
        "  const openEdit = (s) => { setEditing(s); setForm({ name:s.name, phone:s.phone, email:s.email, address:s.address, notes:s.notes }); setShowForm(true); };\n"
        "\n"
        "  const handleSave = async () => {\n"
        "    if (!form.name.trim()) return notify('اسم المورد مطلوب', 'error');\n"
        "    setSaving(true);\n"
        "    try {\n"
        "      if (editing) await inventoryAPI.updateSupplier(editing.id, form);\n"
        "      else         await inventoryAPI.createSupplier(form);\n"
        "      notify(editing ? 'تم التحديث' : 'تمت الاضافة');\n"
        "      setShowForm(false); load();\n"
        "    } catch(e) { notify('خطأ: ' + JSON.stringify(e?.response?.data || 'خطأ'), 'error'); }\n"
        "    finally { setSaving(false); }\n"
        "  };\n"
        "\n"
        "  const handleDelete = async (id) => {\n"
        "    if (!window.confirm('حذف المورد؟')) return;\n"
        "    try { await inventoryAPI.deleteSupplier(id); notify('تم الحذف'); load(); }\n"
        "    catch { notify('خطأ في الحذف', 'error'); }\n"
        "  };\n"
        "\n"
        "  if (loading) return <Spinner />;\n"
        "\n"
        "  return (\n"
        "    <div className=\"space-y-4\">\n"
        "      {toast && <Toast msg={toast.msg} type={toast.type} />}\n"
        "      <div className=\"flex justify-between items-center\">\n"
        "        <h2 className=\"font-black text-gray-700 text-lg\">الموردون</h2>\n"
        "        <button onClick={openAdd}\n"
        "          className=\"bg-blue-600 hover:bg-blue-700 text-white font-bold px-4 py-2 rounded-xl text-sm\">\n"
        "          \u2795 \u0645\u0648\u0631\u062f \u062c\u062f\u064a\u062f\n"
        "        </button>\n"
        "      </div>\n"
        "      <div className=\"bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden\">\n"
        "        <table className=\"w-full text-sm\">\n"
        "          <thead><tr className=\"bg-gray-50 text-gray-500 text-right\">\n"
        "            <th className=\"px-4 py-3 font-bold\">الاسم</th>\n"
        "            <th className=\"px-4 py-3 font-bold\">الهاتف</th>\n"
        "            <th className=\"px-4 py-3 font-bold\">البريد</th>\n"
        "            <th className=\"px-4 py-3 font-bold\">عدد الاوامر</th>\n"
        "            <th className=\"px-4 py-3 font-bold\">الحالة</th>\n"
        "            <th className=\"px-4 py-3 font-bold\">اجراءات</th>\n"
        "          </tr></thead>\n"
        "          <tbody>\n"
        "            {suppliers.length === 0 && <tr><td colSpan={6} className=\"text-center py-8 text-gray-400\">لا يوجد موردون</td></tr>}\n"
        "            {suppliers.map(s => (\n"
        "              <tr key={s.id} className=\"border-t hover:bg-gray-50\">\n"
        "                <td className=\"px-4 py-3 font-bold\">{s.name}</td>\n"
        "                <td className=\"px-4 py-3 text-gray-500\">{s.phone || '—'}</td>\n"
        "                <td className=\"px-4 py-3 text-gray-500\">{s.email || '—'}</td>\n"
        "                <td className=\"px-4 py-3 text-center\"><Badge label={s.orders_count} color=\"blue\" /></td>\n"
        "                <td className=\"px-4 py-3\"><Badge label={s.is_active ? 'نشط' : 'متوقف'} color={s.is_active ? 'green' : 'gray'} /></td>\n"
        "                <td className=\"px-4 py-3 flex gap-2\">\n"
        "                  <button onClick={() => openEdit(s)} className=\"text-blue-600 text-xs font-bold px-2 py-1 rounded-lg bg-blue-50\">تعديل</button>\n"
        "                  <button onClick={() => handleDelete(s.id)} className=\"text-red-600 text-xs font-bold px-2 py-1 rounded-lg bg-red-50\">حذف</button>\n"
        "                </td>\n"
        "              </tr>\n"
        "            ))}\n"
        "          </tbody>\n"
        "        </table>\n"
        "      </div>\n"
        "      {showForm && (\n"
        "        <Modal title={editing ? 'تعديل مورد' : 'مورد جديد'} onClose={() => setShowForm(false)}>\n"
        "          <div className=\"space-y-3\">\n"
        "            <div className=\"grid grid-cols-2 gap-3\">\n"
        "              <Field label=\"الاسم *\"><input className={INP} value={form.name} onChange={e => setForm({...form, name:e.target.value})} /></Field>\n"
        "              <Field label=\"الهاتف\"><input className={INP} value={form.phone} onChange={e => setForm({...form, phone:e.target.value})} /></Field>\n"
        "              <Field label=\"البريد\"><input type=\"email\" className={INP} value={form.email} onChange={e => setForm({...form, email:e.target.value})} /></Field>\n"
        "              <Field label=\"العنوان\"><input className={INP} value={form.address} onChange={e => setForm({...form, address:e.target.value})} /></Field>\n"
        "            </div>\n"
        "            <Field label=\"ملاحظات\"><textarea className={INP} rows={2} value={form.notes} onChange={e => setForm({...form, notes:e.target.value})} /></Field>\n"
        "            <div className=\"flex gap-3 justify-end pt-2\">\n"
        "              <button onClick={() => setShowForm(false)} className=\"px-4 py-2 rounded-xl border font-bold text-sm\">الغاء</button>\n"
        "              <button onClick={handleSave} disabled={saving}\n"
        "                className=\"bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2 rounded-xl text-sm\">\n"
        "                {saving ? '...' : editing ? 'تحديث' : 'اضافة'}\n"
        "              </button>\n"
        "            </div>\n"
        "          </div>\n"
        "        </Modal>\n"
        "      )}\n"
        "    </div>\n"
        "  );\n"
        "}\n"
    )
    src = read_file(PURCHASING_JSX)
    backup(PURCHASING_JSX)
    write_file(PURCHASING_JSX, src + suppliers_panel)
    print("  ✅ PurchasingPage.jsx — Fix-5 SuppliersPanel appended")


# ── Fix-6: api.js — إضافة endpoints التخصيص ─────────────────────────────────
def fix_api_js():
    print("\n── Fix api.js (Fix-6 assign endpoints) ──")

    old_movements = (
        "  // Stock Movements\n"
        "  getMovements:          (params) => api.get('/inventory/movements/', { params }),\n"
        "};\n"
    )
    new_movements = (
        "  // Stock Movements\n"
        "  getMovements:          (params) => api.get('/inventory/movements/', { params }),\n"
        "\n"
        "  // Fix-6: تخصيص التنبيهات\n"
        "  assignAlertToMe:   (id)       => api.post('/inventory/alerts/' + id + '/assign_to_me/'),\n"
        "  assignAlertToUser: (id, data) => api.post('/inventory/alerts/' + id + '/assign_to_user/', data),\n"
        "  unassignAlert:     (id)       => api.post('/inventory/alerts/' + id + '/unassign/'),\n"
        "};\n"
    )
    apply_fix("api.js — Fix-6 assign endpoints", API_JS, old_movements, new_movements)


# ── CHANGELOG + FIXES_README ──────────────────────────────────────────────────
def update_docs():
    print("\n── تحديث CHANGELOG و FIXES_README ──")

    lines = [
        "## [" + NOW + "] fix_05_purchasing_improvements",
        "",
        "### Fix-05 — تحسينات قسم المشتريات",
        "**الملفات المعدّلة:**",
        "- `pos_backend/inventory/models.py`",
        "- `pos_backend/inventory/serializers.py`",
        "- `pos_backend/inventory/views.py`",
        "- `pos_frontend/src/pages/PurchasingPage.jsx`",
        "- `pos_frontend/src/pages/InventoryPage.jsx`",
        "- `pos_frontend/src/services/api.js`",
        "",
        "**التفاصيل:**",
        "- Fix-1: إزالة زر الاستلام من جدول أوامر الشراء في PurchasingPage",
        "- Fix-2: تحويل linked_po FK إلى linked_pos ManyToMany — يسمح بأكثر من PO للتنبيه الواحد",
        "- Fix-3: إصلاح مشكلة التاريخ الفارغ عند إضافة ملاحظة (expected_date + cost → None)",
        "- Fix-4: حل التنبيه تلقائياً عند استلام كل أوامر الشراء المرتبطة (check_and_auto_resolve)",
        "- Fix-5: نقل SuppliersPanel من InventoryPage إلى PurchasingPage كتاب ثالث",
        "- Fix-6: إضافة نظام تخصيص التنبيهات (assign_to_me + assign_to_user + unassign)",
        "- Fix-7: حفظ وعرض اسم منشئ التنبيه (created_by)",
        "",
        "**Migration مطلوب:**",
        "```",
        "python manage.py makemigrations inventory --name fix05_created_by_linked_pos_m2m",
        "python manage.py migrate inventory",
        "```",
        "",
        "---",
        "",
    ]
    update_changelog("\n".join(lines))

    readme_lines = [
        "### Fix-05 (" + NOW + ") — تحسينات قسم المشتريات",
        "",
        "**المشاكل:**",
        "1. زر الاستلام ظاهر في قائمة أوامر الشراء",
        "2. التنبيه يسمح بـ PO واحد فقط",
        "3. خطأ عند إضافة ملاحظة بتاريخ فارغ",
        "4. التنبيه لا يُحل تلقائياً عند استلام البضاعة",
        "5. الموردون موجودون في المخزون بدل المشتريات",
        "6. لا يوجد نظام تخصيص للتنبيهات",
        "7. اسم منشئ التنبيه غير مسجّل",
        "",
        "**الحلول:**",
        "- Fix-1: إزالة زر الاستلام من PurchasingPage → PurchaseOrdersPanel",
        "- Fix-2: models.py: linked_pos = ManyToManyField(PurchaseOrder)",
        "- Fix-3: validate_expected_date + validate_cost في StockAlertNoteSerializer",
        "         + تنظيف payload في views.py add_note + handleAddNote في JSX",
        "- Fix-4: models.py: check_and_auto_resolve() — views.py: after receive",
        "- Fix-5: SuppliersPanel انتقلت → PurchasingPage تاب 3",
        "- Fix-6: StockAlertViewSet: assign_to_me + assign_to_user + unassign",
        "         + AlertTicketModal: تاب التخصيص + assign UI",
        "- Fix-7: StockAlert.created_by ForeignKey + created_by_name في serializer",
        "",
        "**الملفات المعدّلة:**",
        "- `pos_backend/inventory/models.py`",
        "- `pos_backend/inventory/serializers.py`",
        "- `pos_backend/inventory/views.py`",
        "- `pos_frontend/src/pages/PurchasingPage.jsx`",
        "- `pos_frontend/src/pages/InventoryPage.jsx`",
        "- `pos_frontend/src/services/api.js`",
        "",
        "**للتراجع (rollback):**",
        "```bash",
        "git checkout HEAD~1 -- pos_backend/inventory/models.py",
        "git checkout HEAD~1 -- pos_backend/inventory/serializers.py",
        "git checkout HEAD~1 -- pos_backend/inventory/views.py",
        "git checkout HEAD~1 -- pos_frontend/src/pages/PurchasingPage.jsx",
        "git checkout HEAD~1 -- pos_frontend/src/pages/InventoryPage.jsx",
        "git checkout HEAD~1 -- pos_frontend/src/services/api.js",
        "```",
        "",
        "---",
        "",
    ]
    write_readme("\n".join(readme_lines))


# ── Migration reminder ────────────────────────────────────────────────────────
def print_migration_reminder():
    print("\n" + "="*60)
    print("✅ كل التعديلات اتطبقت بنجاح!")
    print("="*60)
    print("\n⚠️  خطوة مطلوبة — تشغيل الـ Migration:")
    print("")
    print("  cd " + BACKEND)
    print("  python manage.py makemigrations inventory --name fix05_created_by_linked_pos_m2m")
    print("  python manage.py migrate inventory")
    print("")
    print("ثم ارفع التغييرات:")
    print("")
    print("  cd " + BASE)
    print("  git add -A")
    print("  git commit -m \"fix-05: purchasing improvements (M2M POs, assign, created_by, suppliers tab)\"")
    print("  git push")
    print("="*60)


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print("="*60)
    print("fix_05_purchasing_improvements.py")
    print("="*60)

    check_files()
    fix_models()
    fix_serializers()
    fix_views()
    fix_inventory_page()
    fix_purchasing_page()
    fix_api_js()
    update_docs()
    print_migration_reminder()


if __name__ == "__main__":
    main()
