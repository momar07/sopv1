#!/usr/bin/env python3
# fix_06_purchasing_v2.py  —  تعديلات المشتريات (نسخة 2، كاملة وبدون unicode errors)
# القواعد: لا triple-quoted f-string، لا emoji في strings، string concatenation عادي

import os, sys, shutil, re
from datetime import datetime

# ── Constants ──────────────────────────────────────────────────────────────────
BASE      = "/home/momar/Projects/POS_DEV/posv1_dev10"
BACKEND   = BASE + "/pos_backend"
FRONTEND  = BASE + "/pos_frontend/src"
STAMP     = datetime.now().strftime("%Y%m%d_%H%M%S")

CHANGELOG = BACKEND + "/CHANGELOG.md"
README    = BACKEND + "/FIXES_README.md"

# ── Helpers ────────────────────────────────────────────────────────────────────
def abort(msg):
    print("ABORT: " + msg)
    sys.exit(1)

def backup(path):
    bak = path + ".bak_" + STAMP
    shutil.copy2(path, bak)
    print("  backup -> " + bak)

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def apply_fix(label, path, old, new):
    if not os.path.exists(path):
        abort(path + " not found")
    src = read(path)
    if old not in src:
        print("  SKIP (pattern not found): " + label)
        return False
    backup(path)
    write(path, src.replace(old, new, 1))
    print("  OK: " + label)
    return True

def update_changelog(entry):
    if not os.path.exists(CHANGELOG):
        return
    src = read(CHANGELOG)
    if entry[:30] in src:
        return
    write(CHANGELOG, entry + "\n" + src)

def write_readme(lines):
    write(README, "\n".join(lines))

# ── Section 1: models.py — اضافة created_by + linked_pos M2M ──────────────────
def fix_models():
    path = BACKEND + "/inventory/models.py"
    print("\n[models.py]")

    # 1-a: اضافة created_by الى StockAlert
    old = (
        "    is_resolved   = models.BooleanField(default=False)\n"
        "    resolved_at   = models.DateTimeField(null=True, blank=True)\n"
        "    created_at    = models.DateTimeField(auto_now_add=True)\n"
        "    updated_at    = models.DateTimeField(auto_now=True)"
    )
    new = (
        "    created_by    = models.ForeignKey(\n"
        "        settings.AUTH_USER_MODEL, null=True, blank=True,\n"
        "        on_delete=models.SET_NULL, related_name='created_alerts'\n"
        "    )\n"
        "    is_resolved   = models.BooleanField(default=False)\n"
        "    resolved_at   = models.DateTimeField(null=True, blank=True)\n"
        "    created_at    = models.DateTimeField(auto_now_add=True)\n"
        "    updated_at    = models.DateTimeField(auto_now=True)"
    )
    apply_fix("StockAlert.created_by", path, old, new)

    # 1-b: استبدال linked_po FK بـ M2M
    old = (
        "    linked_po     = models.ForeignKey(\n"
        "        PurchaseOrder, null=True, blank=True,\n"
        "        on_delete=models.SET_NULL, related_name='linked_alerts'\n"
        "    )"
    )
    new = (
        "    linked_pos    = models.ManyToManyField(\n"
        "        PurchaseOrder, blank=True,\n"
        "        related_name='linked_alerts'\n"
        "    )"
    )
    apply_fix("StockAlert.linked_po -> linked_pos M2M", path, old, new)

    # 1-c: تحديث دالة resolve لازالة linked_po
    old = (
        "    def resolve(self, user=None):\n"
        "        from django.utils import timezone\n"
        "        self.is_resolved   = True\n"
        "        self.ticket_status = 'resolved'\n"
        "        self.resolved_at   = timezone.now()\n"
        "        self.save(update_fields=['is_resolved', 'ticket_status', 'resolved_at'])"
    )
    new = (
        "    def resolve(self, user=None):\n"
        "        from django.utils import timezone\n"
        "        self.is_resolved   = True\n"
        "        self.ticket_status = 'resolved'\n"
        "        self.resolved_at   = timezone.now()\n"
        "        self.save(update_fields=['is_resolved', 'ticket_status', 'resolved_at'])\n"
        "\n"
        "    def check_and_auto_resolve(self):\n"
        "        \"\"\"يحل التنبيه اوتوماتيك لو كل POs مرتبطة استُلمت\"\"\"\n"
        "        pos = self.linked_pos.all()\n"
        "        if pos.exists() and not pos.exclude(status='received').exists():\n"
        "            self.resolve()"
    )
    apply_fix("StockAlert.check_and_auto_resolve", path, old, new)

# ── Section 2: serializers.py — تحديث linked_po -> linked_pos + created_by ────
def fix_serializers():
    path = BACKEND + "/inventory/serializers.py"
    print("\n[serializers.py]")

    # 2-a: استبدال linked_po fields في StockAlertSerializer
    old = (
        "    linked_po_reference   = serializers.CharField(source='linked_po.reference_number',  read_only=True)\n"
        "    linked_po_status      = serializers.CharField(source='linked_po.status',            read_only=True)"
    )
    new = (
        "    linked_po_reference   = serializers.SerializerMethodField()\n"
        "    linked_po_status      = serializers.SerializerMethodField()\n"
        "    linked_pos_data       = serializers.SerializerMethodField()\n"
        "    created_by_name       = serializers.CharField(source='created_by.username', read_only=True)"
    )
    apply_fix("StockAlertSerializer: linked_po -> linked_pos fields", path, old, new)

    # 2-b: تحديث fields list في StockAlertSerializer Meta
    old = (
        "            'linked_po', 'linked_po_reference', 'linked_po_status',\n"
        "            'is_resolved', 'resolved_at',\n"
        "            'notes', 'notes_count',\n"
        "            'created_at', 'updated_at',"
    )
    new = (
        "            'linked_pos', 'linked_po_reference', 'linked_po_status', 'linked_pos_data',\n"
        "            'created_by', 'created_by_name',\n"
        "            'is_resolved', 'resolved_at',\n"
        "            'notes', 'notes_count',\n"
        "            'created_at', 'updated_at',"
    )
    apply_fix("StockAlertSerializer Meta fields: linked_pos", path, old, new)

    # 2-c: اضافة SerializerMethodFields بعد get_notes_count
    old = "    def get_notes_count(self, obj):\n        return obj.notes.count()"
    new = (
        "    def get_notes_count(self, obj):\n"
        "        return obj.notes.count()\n"
        "\n"
        "    def get_linked_po_reference(self, obj):\n"
        "        first = obj.linked_pos.order_by('-created_at').first()\n"
        "        return first.reference_number if first else None\n"
        "\n"
        "    def get_linked_po_status(self, obj):\n"
        "        first = obj.linked_pos.order_by('-created_at').first()\n"
        "        return first.status if first else None\n"
        "\n"
        "    def get_linked_pos_data(self, obj):\n"
        "        return [\n"
        "            {'id': str(po.id), 'reference_number': po.reference_number,\n"
        "             'status': po.status, 'expected_date': str(po.expected_date) if po.expected_date else None,\n"
        "             'total_cost': str(po.total_cost)}\n"
        "            for po in obj.linked_pos.order_by('-created_at')\n"
        "        ]"
    )
    apply_fix("StockAlertSerializer: get_linked_pos_data method", path, old, new)

    # 2-d: اضافة validate_expected_date في StockAlertNoteSerializer
    old = (
        "        read_only_fields = ['alert', 'user', 'created_at']\n"
        "\nclass StockAlertSerializer"
    )
    new = (
        "        read_only_fields = ['alert', 'user', 'created_at']\n"
        "\n"
        "    def validate_expected_date(self, value):\n"
        "        if value:\n"
        "            from datetime import date\n"
        "            if isinstance(value, str):\n"
        "                from datetime import datetime as dt\n"
        "                value = dt.strptime(value, '%Y-%m-%d').date()\n"
        "            if value < date.today():\n"
        "                raise serializers.ValidationError('التاريخ لا يمكن ان يكون في الماضي')\n"
        "        return value\n"
        "\nclass StockAlertSerializer"
    )
    apply_fix("StockAlertNoteSerializer: validate_expected_date", path, old, new)

# ── Section 3: views.py — كل التعديلات ────────────────────────────────────────
def fix_views():
    path = BACKEND + "/inventory/views.py"
    print("\n[views.py]")

    # 3-a: تحديث queryset في StockAlertViewSet لإزالة linked_po
    old = (
        "    queryset = StockAlert.objects.select_related(\n"
        "        'product', 'assigned_to', 'linked_po'\n"
        "    ).prefetch_related('notes__user').all()"
    )
    new = (
        "    queryset = StockAlert.objects.select_related(\n"
        "        'product', 'assigned_to', 'created_by'\n"
        "    ).prefetch_related('notes__user', 'linked_pos').all()"
    )
    apply_fix("StockAlertViewSet: queryset linked_po->linked_pos", path, old, new)

    # 3-b: تحديث filterset_fields لإزالة linked_po
    old = "    filterset_fields   = ['alert_type', 'is_resolved', 'product', 'priority', 'ticket_status']"
    new = (
        "    filterset_fields   = ['alert_type', 'is_resolved', 'product', 'priority', 'ticket_status']\n"
        "    search_fields      = ['product__name']"
    )
    apply_fix("StockAlertViewSet: add search_fields", path, old, new)

    # 3-c: تحديث check_and_generate لاضافة created_by
    old = (
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
        "                created += 1"
    )
    new = (
        "            if product.stock == 0:\n"
        "                StockAlert.objects.create(\n"
        "                    product=product, alert_type='out', priority='critical',\n"
        "                    threshold=threshold, current_stock=0,\n"
        "                    created_by=request.user\n"
        "                )\n"
        "                created += 1\n"
        "            elif product.stock <= threshold:\n"
        "                StockAlert.objects.create(\n"
        "                    product=product, alert_type='low', priority='high',\n"
        "                    threshold=threshold, current_stock=product.stock,\n"
        "                    created_by=request.user\n"
        "                )\n"
        "                created += 1"
    )
    apply_fix("check_and_generate: created_by=request.user", path, old, new)

    # 3-d: تحديث create_purchase_order لدعم M2M (linked_pos) بدلاً من FK
    old = (
        "            alert.linked_po     = po\n"
        "            alert.ticket_status = 'ordered'\n"
        "            alert.save(update_fields=['linked_po', 'ticket_status'])"
    )
    new = (
        "            alert.linked_pos.add(po)\n"
        "            alert.ticket_status = 'ordered'\n"
        "            alert.save(update_fields=['ticket_status'])"
    )
    apply_fix("create_purchase_order: linked_pos.add(po)", path, old, new)

    # 3-e: تحديث create_purchase_order لازالة قيد وجود linked_po واحد
    old = (
        "        if alert.linked_po:\n"
        "            return Response(\n"
        "                {'error': 'يوجد أمر شراء مرتبط بالفعل: ' + alert.linked_po.reference_number},\n"
        "                status=status.HTTP_400_BAD_REQUEST\n"
        "            )"
    )
    new = "        # السماح بأوامر شراء متعددة للتنبيه الواحد"
    apply_fix("create_purchase_order: remove single-PO restriction", path, old, new)

    # 3-f: تحديث resolve لفحص كل linked_pos
    old = (
        "        if alert.linked_po and alert.linked_po.status != 'received':\n"
        "            return Response(\n"
        "                {'error': 'أمر الشراء #' + alert.linked_po.reference_number + ' لم يُستلم بعد. استلم البضاعة أولاً.'},\n"
        "                status=status.HTTP_400_BAD_REQUEST\n"
        "            )"
    )
    new = (
        "        unrcvd = alert.linked_pos.exclude(status='received').exclude(status='cancelled')\n"
        "        if unrcvd.exists():\n"
        "            refs = ', '.join(p.reference_number for p in unrcvd)\n"
        "            return Response(\n"
        "                {'error': 'بعض أوامر الشراء لم تُستلم بعد: ' + refs},\n"
        "                status=status.HTTP_400_BAD_REQUEST\n"
        "            )"
    )
    apply_fix("resolve: check all linked_pos", path, old, new)

    # 3-g: تحديث receive في PurchaseOrderViewSet لحل كل التنبيهات المرتبطة
    old = (
        "                # \u2705 resolve StockAlert \u0644\u0648 \u0627\u0644\u0645\u062e\u0632\u0648\u0646 \u0631\u062c\u0639 \u0641\u0648\u0642 \u0627\u0644\u0640 threshold\n"
        "                from inventory.models import StockAlert as _SA\n"
        "                if product.stock > 0:\n"
        "                    _SA.objects.filter(\n"
        "                        product=product, is_resolved=False\n"
        "                    ).update(is_resolved=True, resolved_at=timezone.now())"
    )
    new = (
        "                # auto-resolve alerts linked to this PO after stock update\n"
        "                from inventory.models import StockAlert as _SA\n"
        "                if product.stock > 0:\n"
        "                    _SA.objects.filter(\n"
        "                        product=product, is_resolved=False\n"
        "                    ).update(is_resolved=True,\n"
        "                             ticket_status='resolved',\n"
        "                             resolved_at=timezone.now())"
    )
    apply_fix("receive: update ticket_status on auto-resolve", path, old, new)

    # 3-h: اضافة assign actions بعد update_meta
    old = (
        "    @action(detail=True, methods=['patch'])\n"
        "    def update_meta(self, request, pk=None):\n"
        "        alert   = self.get_object()\n"
        "        allowed = ['priority', 'assigned_to', 'deadline', 'ticket_status']\n"
        "        for field in allowed:\n"
        "            if field in request.data:\n"
        "                setattr(alert, field, request.data[field] or None)\n"
        "        alert.save()\n"
        "        return Response(StockAlertSerializer(alert).data)\n"
        "\n# \u2500\u2500 StockMovement"
    )
    new = (
        "    @action(detail=True, methods=['patch'])\n"
        "    def update_meta(self, request, pk=None):\n"
        "        alert   = self.get_object()\n"
        "        allowed = ['priority', 'assigned_to', 'deadline', 'ticket_status']\n"
        "        for field in allowed:\n"
        "            if field in request.data:\n"
        "                setattr(alert, field, request.data[field] or None)\n"
        "        alert.save()\n"
        "        return Response(StockAlertSerializer(alert).data)\n"
        "\n"
        "    @action(detail=True, methods=['post'])\n"
        "    def assign_to_me(self, request, pk=None):\n"
        "        alert = self.get_object()\n"
        "        alert.assigned_to = request.user\n"
        "        alert.save(update_fields=['assigned_to'])\n"
        "        StockAlertNote.objects.create(\n"
        "            alert=alert, user=request.user, note_type='system',\n"
        "            text='تم تخصيص التذكرة لـ ' + request.user.username,\n"
        "        )\n"
        "        return Response(StockAlertSerializer(alert).data)\n"
        "\n"
        "    @action(detail=True, methods=['post'])\n"
        "    def assign_to_user(self, request, pk=None):\n"
        "        from django.contrib.auth import get_user_model\n"
        "        User = get_user_model()\n"
        "        user_id = request.data.get('user_id')\n"
        "        if not user_id:\n"
        "            return Response({'error': 'user_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)\n"
        "        try:\n"
        "            target = User.objects.get(id=user_id)\n"
        "        except User.DoesNotExist:\n"
        "            return Response({'error': 'المستخدم غير موجود'}, status=status.HTTP_400_BAD_REQUEST)\n"
        "        # فقط المدير يقدر يخصص لآخرين\n"
        "        allowed_groups = {'Admins', 'Managers'}\n"
        "        user_groups    = set(request.user.groups.values_list('name', flat=True))\n"
        "        if not request.user.is_superuser and not (allowed_groups & user_groups):\n"
        "            from rest_framework.exceptions import PermissionDenied\n"
        "            raise PermissionDenied('فقط المدير يمكنه تخصيص التذكرة لمستخدم آخر')\n"
        "        alert.assigned_to = target\n"
        "        alert.save(update_fields=['assigned_to'])\n"
        "        StockAlertNote.objects.create(\n"
        "            alert=alert, user=request.user, note_type='system',\n"
        "            text='تم تخصيص التذكرة لـ ' + target.username,\n"
        "        )\n"
        "        return Response(StockAlertSerializer(alert).data)\n"
        "\n"
        "    @action(detail=True, methods=['post'])\n"
        "    def unassign(self, request, pk=None):\n"
        "        alert = self.get_object()\n"
        "        alert.assigned_to = None\n"
        "        alert.save(update_fields=['assigned_to'])\n"
        "        StockAlertNote.objects.create(\n"
        "            alert=alert, user=request.user, note_type='system',\n"
        "            text='تم الغاء تخصيص التذكرة',\n"
        "        )\n"
        "        return Response(StockAlertSerializer(alert).data)\n"
        "\n# -- StockMovement"
    )
    apply_fix("views.py: assign_to_me / assign_to_user / unassign actions", path, old, new)

# ── Section 4: api.js — اضافة endpoints الـ assign ───────────────────────────
def fix_api_js():
    path = FRONTEND + "/services/api.js"
    print("\n[api.js]")

    old = "  resolveAlert:           (id, data) => api.post"
    if old not in read(path):
        print("  SKIP: resolveAlert line not found, trying alternate")
        return

    old = (
        "  resolveAlert:           (id, data) => api.post(`/inventory/alerts/${id}/resolve/`, data),"
    )
    new = (
        "  resolveAlert:           (id, data) => api.post(`/inventory/alerts/${id}/resolve/`, data),\n"
        "  assignAlertToMe:        (id)        => api.post(`/inventory/alerts/${id}/assign_to_me/`),\n"
        "  assignAlertToUser:      (id, data)  => api.post(`/inventory/alerts/${id}/assign_to_user/`, data),\n"
        "  unassignAlert:          (id)        => api.post(`/inventory/alerts/${id}/unassign/`),"
    )
    apply_fix("api.js: assign endpoints", path, old, new)

# ── Section 5: PurchasingPage.jsx — كل التعديلات ──────────────────────────────
def fix_purchasing_page():
    path = FRONTEND + "/pages/PurchasingPage.jsx"
    print("\n[PurchasingPage.jsx]")

    # 5-a: اضافة تاب الموردين
    old = (
        "  const tabs = [\n"
        "    { key: 'alerts', label: '\ud83d\udd14 \u0627\u0644\u062a\u0646\u0628\u064a\u0647\u0627\u062a' },\n"
        "    { key: 'orders', label: '\ud83d\udce6 \u0623\u0648\u0627\u0645\u0631 \u0627\u0644\u0634\u0631\u0627\u0621' },\n"
        "  ];"
    )
    new = (
        "  const tabs = [\n"
        "    { key: 'alerts',    label: '\\uD83D\\uDD14 \\u0627\\u0644\\u062A\\u0646\\u0628\\u064A\\u0647\\u0627\\u062A' },\n"
        "    { key: 'orders',    label: '\\uD83D\\uDCE6 \\u0623\\u0648\\u0627\\u0645\\u0631 \\u0627\\u0644\\u0634\\u0631\\u0627\\u0621' },\n"
        "    { key: 'suppliers', label: '\\uD83C\\uDFED \\u0627\\u0644\\u0645\\u0648\\u0631\\u062F\\u0648\\u0646' },\n"
        "  ];"
    )

    src = read(path)
    # استخدام regex بدلاً من literal match لتجنب مشاكل الـ encoding في الملف
    pattern = r"const tabs = \[\s*\{[^}]+key: 'alerts'[^}]+\},\s*\{[^}]+key: 'orders'[^}]+\},\s*\];"
    replacement = (
        "const tabs = [\n"
        "    { key: 'alerts',    label: '\uD83D\uDD14 \u0627\u0644\u062A\u0646\u0628\u064A\u0647\u0627\u062A' },\n"
        "    { key: 'orders',    label: '\uD83D\uDCE6 \u0623\u0648\u0627\u0645\u0631 \u0627\u0644\u0634\u0631\u0627\u0621' },\n"
        "    { key: 'suppliers', label: '\uD83C\uDFED \u0627\u0644\u0645\u0648\u0631\u062F\u0648\u0646' },\n"
        "  ];"
    )
    if re.search(pattern, src):
        backup(path)
        src = re.sub(pattern, replacement, src, count=1)
        write(path, src)
        print("  OK: tabs array — added suppliers tab")
    else:
        print("  SKIP: tabs pattern not found (regex)")

    # 5-b: اضافة render لتاب الموردين بعد orders
    old = "      {tab === 'orders' && <PurchaseOrdersPanel />}"
    new = (
        "      {tab === 'orders' && <PurchaseOrdersPanel />}\n"
        "      {tab === 'suppliers' && <SuppliersPanel />}"
    )
    apply_fix("PurchasingPage: render SuppliersPanel", path, old, new)

    # 5-c: ازالة زر الاستلام من PurchaseOrdersPanel
    old = (
        "                  {(o.status==='ordered'||o.status==='draft') && (\n"
        "                    <button onClick={() => setSelected(o)}\n"
        "                      className=\"bg-green-500 hover:bg-green-600 text-white text-xs font-bold px-3 py-1 rounded-lg\">\n"
        "                      \ud83d\udce5 \u0627\u0633\u062a\u0644\u0627\u0645\n"
        "                    </button>\n"
        "                  )}"
    )
    new = "                  {/* زر الاستلام أُزيل — الاستلام يتم عبر المخزون */}"
    apply_fix("PurchasingPage: remove receive button from table", path, old, new)

    # 5-d: ازالة ReceiveModal render من PurchaseOrdersPanel
    old = (
        "      {selected && (\n"
        "        <ReceiveModal order={selected} onClose={() => setSelected(null)} onReceive={handleReceive} />\n"
        "      )}"
    )
    new = "      {/* ReceiveModal removed — receiving handled in inventory section */}"
    apply_fix("PurchasingPage: remove ReceiveModal render", path, old, new)

    # 5-e: تحديث create_po tab لدعم multiple POs
    old = (
        "          {data.linked_po_reference ? (\n"
        "            <div className=\"bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-700 font-bold text-center\">\n"
        "              \u26a0\ufe0f \u064a\u0648\u062c\u062f \u0623\u0645\u0631 \u0634\u0631\u0627\u0621 \u0645\u0631\u062a\u0628\u0637 \u0628\u0627\u0644\u0641\u0639\u0644: {data.linked_po_reference}\n"
        "            </div>\n"
        "          ) : ("
    )
    new = (
        "          {data.linked_pos_data && data.linked_pos_data.length > 0 && (\n"
        "            <div className=\"mb-3 bg-blue-50 border border-blue-200 rounded-xl p-3\">\n"
        "              <p className=\"text-xs font-bold text-blue-700 mb-2\">عروض الشراء المرتبطة ({data.linked_pos_data.length}):</p>\n"
        "              {data.linked_pos_data.map(po => (\n"
        "                <div key={po.id} className=\"flex justify-between text-xs text-blue-600 py-1 border-t border-blue-100\">\n"
        "                  <span className=\"font-bold\">{po.reference_number}</span>\n"
        "                  <span>{po.status}</span>\n"
        "                  {po.expected_date && <span>{po.expected_date}</span>}\n"
        "                </div>\n"
        "              ))}\n"
        "            </div>\n"
        "          )}\n"
        "          {("
    )
    apply_fix("AlertTicketModal: create_po tab — show multiple POs", path, old, new)

    # 5-f: اضافة قسم التخصيص في AlertTicketModal header
    old = (
        "      {data.linked_po_reference && (\n"
        "        <div className=\"mb-4 bg-blue-50 border border-blue-200 rounded-xl px-4 py-2 text-sm text-blue-700 font-bold\">\n"
        "          \ud83d\udce6 \u0623\u0645\u0631 \u0627\u0644\u0634\u0631\u0627\u0621 \u0627\u0644\u0645\u0631\u062a\u0628\u0637: {data.linked_po_reference}\n"
        "          <span className=\"mr-2 text-xs font-normal\">({data.linked_po_status})</span>\n"
        "        </div>\n"
        "      )}"
    )
    new = (
        "      {data.linked_pos_data && data.linked_pos_data.length > 0 && (\n"
        "        <div className=\"mb-4 bg-blue-50 border border-blue-200 rounded-xl px-4 py-2 text-sm text-blue-700 font-bold\">\n"
        "          عروض الشراء المرتبطة: {data.linked_pos_data.length} عرض\n"
        "        </div>\n"
        "      )}\n"
        "      <AssignSection data={data} onUpdated={onUpdated} notify={notify} />"
    )
    apply_fix("AlertTicketModal: header linked_pos + AssignSection", path, old, new)

    # 5-g: اضافة AssignSection component قبل PurchaseOrdersPanel
    old = "// ══════════════════════════════\n//  PurchaseOrdersPanel\n// ══════════════════════════════"
    new = (
        "// ══════════════════════════════\n"
        "//  AssignSection\n"
        "// ══════════════════════════════\n"
        "function AssignSection({ data, onUpdated, notify }) {\n"
        "  const { user } = useAuth();\n"
        "  const [users, setUsers] = React.useState([]);\n"
        "  const [loadingUsers, setLoadingUsers] = React.useState(false);\n"
        "  const [saving, setSaving] = React.useState(false);\n"
        "  const [selUser, setSelUser] = React.useState('');\n"
        "\n"
        "  const isManager = user?.is_superuser ||\n"
        "    (user?.groups || []).some(g => g === 'Admins' || g === 'Managers');\n"
        "\n"
        "  React.useEffect(() => {\n"
        "    if (isManager) {\n"
        "      setLoadingUsers(true);\n"
        "      import('../services/api').then(m => {\n"
        "        (m.usersAPI || m.default?.usersAPI || { getAll: () => Promise.resolve({ data: [] }) })\n"
        "          .getAll().then(r => {\n"
        "            setUsers(r.data?.results || r.data || []);\n"
        "          }).finally(() => setLoadingUsers(false));\n"
        "      });\n"
        "    }\n"
        "  }, [isManager]);\n"
        "\n"
        "  const handleAssignMe = async () => {\n"
        "    setSaving(true);\n"
        "    try {\n"
        "      await inventoryAPI.assignAlertToMe(data.id);\n"
        "      notify('تم تخصيص التذكرة لك');\n"
        "      onUpdated();\n"
        "    } catch { notify('خطأ في التخصيص', 'error'); }\n"
        "    finally { setSaving(false); }\n"
        "  };\n"
        "\n"
        "  const handleAssignUser = async () => {\n"
        "    if (!selUser) return notify('اختر مستخدم', 'error');\n"
        "    setSaving(true);\n"
        "    try {\n"
        "      await inventoryAPI.assignAlertToUser(data.id, { user_id: selUser });\n"
        "      notify('تم التخصيص');\n"
        "      onUpdated();\n"
        "    } catch { notify('خطأ', 'error'); }\n"
        "    finally { setSaving(false); }\n"
        "  };\n"
        "\n"
        "  const handleUnassign = async () => {\n"
        "    setSaving(true);\n"
        "    try {\n"
        "      await inventoryAPI.unassignAlert(data.id);\n"
        "      notify('تم الغاء التخصيص');\n"
        "      onUpdated();\n"
        "    } catch { notify('خطأ', 'error'); }\n"
        "    finally { setSaving(false); }\n"
        "  };\n"
        "\n"
        "  return (\n"
        "    <div className=\"mb-4 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3\">\n"
        "      <p className=\"text-xs font-bold text-gray-500 mb-2\">التخصيص</p>\n"
        "      <div className=\"flex items-center gap-2 flex-wrap\">\n"
        "        {data.assigned_to_name ? (\n"
        "          <>\n"
        "            <span className=\"text-sm font-bold text-blue-700\">مخصص لـ: {data.assigned_to_name}</span>\n"
        "            {(isManager || data.assigned_to === user?.id) && (\n"
        "              <button onClick={handleUnassign} disabled={saving}\n"
        "                className=\"text-xs bg-red-100 hover:bg-red-200 text-red-700 font-bold px-2 py-1 rounded-lg\">\n"
        "                الغاء التخصيص\n"
        "              </button>\n"
        "            )}\n"
        "          </>\n"
        "        ) : (\n"
        "          <span className=\"text-sm text-gray-400\">غير مخصص لاحد</span>\n"
        "        )}\n"
        "        <button onClick={handleAssignMe} disabled={saving}\n"
        "          className=\"text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 font-bold px-2 py-1 rounded-lg\">\n"
        "          تخصيص لي\n"
        "        </button>\n"
        "        {isManager && (\n"
        "          <div className=\"flex items-center gap-1\">\n"
        "            <select className=\"text-xs border border-gray-200 rounded-lg px-2 py-1\"\n"
        "              value={selUser} onChange={e => setSelUser(e.target.value)}>\n"
        "              <option value=\"\">اختر مستخدم...</option>\n"
        "              {users.map(u => <option key={u.id} value={u.id}>{u.username}</option>)}\n"
        "            </select>\n"
        "            <button onClick={handleAssignUser} disabled={saving || !selUser}\n"
        "              className=\"text-xs bg-purple-100 hover:bg-purple-200 text-purple-700 font-bold px-2 py-1 rounded-lg\">\n"
        "              تخصيص\n"
        "            </button>\n"
        "          </div>\n"
        "        )}\n"
        "      </div>\n"
        "    </div>\n"
        "  );\n"
        "}\n"
        "\n"
        "// ══════════════════════════════\n"
        "//  SuppliersPanel\n"
        "// ══════════════════════════════\n"
        "function SuppliersPanel() {\n"
        "  const [suppliers, setSuppliers] = React.useState([]);\n"
        "  const [loading, setLoading]     = React.useState(true);\n"
        "  const [toast, setToast]         = React.useState(null);\n"
        "  const [showForm, setShowForm]   = React.useState(false);\n"
        "  const [editing, setEditing]     = React.useState(null);\n"
        "  const notify = (msg, type='success') => { setToast({msg,type}); setTimeout(()=>setToast(null),3500); };\n"
        "\n"
        "  const load = React.useCallback(async () => {\n"
        "    setLoading(true);\n"
        "    try {\n"
        "      const r = await inventoryAPI.getSuppliers();\n"
        "      setSuppliers(r.data?.results || r.data || []);\n"
        "    } catch { /**/ } finally { setLoading(false); }\n"
        "  }, []);\n"
        "\n"
        "  React.useEffect(() => { load(); }, [load]);\n"
        "\n"
        "  const handleSave = async (form) => {\n"
        "    try {\n"
        "      if (editing) {\n"
        "        await inventoryAPI.updateSupplier(editing.id, form);\n"
        "        notify('تم التعديل');\n"
        "      } else {\n"
        "        await inventoryAPI.createSupplier(form);\n"
        "        notify('تم الاضافة');\n"
        "      }\n"
        "      setShowForm(false); setEditing(null); load();\n"
        "    } catch { notify('خطأ', 'error'); }\n"
        "  };\n"
        "\n"
        "  if (loading) return <Spinner />;\n"
        "  return (\n"
        "    <div className=\"space-y-4\">\n"
        "      {toast && <Toast msg={toast.msg} type={toast.type} />}\n"
        "      <div className=\"flex justify-between items-center\">\n"
        "        <h2 className=\"font-black text-gray-700 text-lg\">الموردون</h2>\n"
        "        <button onClick={() => { setEditing(null); setShowForm(true); }}\n"
        "          className=\"bg-blue-600 hover:bg-blue-700 text-white font-bold px-4 py-2 rounded-xl text-sm\">\n"
        "          اضافة مورد\n"
        "        </button>\n"
        "      </div>\n"
        "      <div className=\"bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden\">\n"
        "        <table className=\"w-full text-sm\">\n"
        "          <thead><tr className=\"bg-gray-50 text-gray-500 text-right\">\n"
        "            <th className=\"px-4 py-3 font-bold\">الاسم</th>\n"
        "            <th className=\"px-4 py-3 font-bold\">الهاتف</th>\n"
        "            <th className=\"px-4 py-3 font-bold\">البريد</th>\n"
        "            <th className=\"px-4 py-3 font-bold\">الطلبات</th>\n"
        "            <th className=\"px-4 py-3 font-bold\">اجراءات</th>\n"
        "          </tr></thead>\n"
        "          <tbody>\n"
        "            {suppliers.length === 0 && <tr><td colSpan={5} className=\"text-center py-8 text-gray-400\">لا يوجد موردون</td></tr>}\n"
        "            {suppliers.map(s => (\n"
        "              <tr key={s.id} className=\"border-t hover:bg-gray-50\">\n"
        "                <td className=\"px-4 py-3 font-bold\">{s.name}</td>\n"
        "                <td className=\"px-4 py-3\">{s.phone || '-'}</td>\n"
        "                <td className=\"px-4 py-3\">{s.email || '-'}</td>\n"
        "                <td className=\"px-4 py-3\">{s.orders_count}</td>\n"
        "                <td className=\"px-4 py-3\">\n"
        "                  <button onClick={() => { setEditing(s); setShowForm(true); }}\n"
        "                    className=\"text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold px-2 py-1 rounded-lg\">\n"
        "                    تعديل\n"
        "                  </button>\n"
        "                </td>\n"
        "              </tr>\n"
        "            ))}\n"
        "          </tbody>\n"
        "        </table>\n"
        "      </div>\n"
        "      {showForm && (\n"
        "        <SupplierFormModal\n"
        "          initial={editing}\n"
        "          onClose={() => { setShowForm(false); setEditing(null); }}\n"
        "          onSave={handleSave}\n"
        "        />\n"
        "      )}\n"
        "    </div>\n"
        "  );\n"
        "}\n"
        "\n"
        "function SupplierFormModal({ initial, onClose, onSave }) {\n"
        "  const [form, setForm] = React.useState(\n"
        "    initial ? { ...initial } : { name:'', phone:'', email:'', address:'', notes:'' }\n"
        "  );\n"
        "  const [saving, setSaving] = React.useState(false);\n"
        "  const handleSave = async () => {\n"
        "    if (!form.name.trim()) return;\n"
        "    setSaving(true);\n"
        "    await onSave(form);\n"
        "    setSaving(false);\n"
        "  };\n"
        "  return (\n"
        "    <Modal title={initial ? 'تعديل مورد' : 'اضافة مورد'} onClose={onClose}>\n"
        "      <div className=\"space-y-3\">\n"
        "        <Field label=\"الاسم *\"><input className={INP} value={form.name} onChange={e=>setForm({...form,name:e.target.value})} /></Field>\n"
        "        <Field label=\"الهاتف\"><input className={INP} value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})} /></Field>\n"
        "        <Field label=\"البريد\"><input className={INP} value={form.email} onChange={e=>setForm({...form,email:e.target.value})} /></Field>\n"
        "        <Field label=\"العنوان\"><textarea className={INP} rows={2} value={form.address} onChange={e=>setForm({...form,address:e.target.value})} /></Field>\n"
        "        <Field label=\"ملاحظات\"><textarea className={INP} rows={2} value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})} /></Field>\n"
        "        <div className=\"flex gap-3 justify-end pt-2\">\n"
        "          <button onClick={onClose} className=\"px-4 py-2 rounded-xl border font-bold text-sm\">الغاء</button>\n"
        "          <button onClick={handleSave} disabled={saving || !form.name.trim()}\n"
        "            className=\"bg-blue-600 hover:bg-blue-700 text-white font-bold px-5 py-2 rounded-xl text-sm disabled:opacity-50\">\n"
        "            {saving ? '...' : 'حفظ'}\n"
        "          </button>\n"
        "        </div>\n"
        "      </div>\n"
        "    </Modal>\n"
        "  );\n"
        "}\n"
        "\n"
        "// ══════════════════════════════\n"
        "//  PurchaseOrdersPanel\n"
        "// ══════════════════════════════"
    )
    apply_fix("PurchasingPage: AssignSection + SuppliersPanel components", path, old, new)

    # 5-h: اضافة created_by في AlertCard
    old = "        <span>{alert.created_at?.split('T')[0]}</span>"
    new = (
        "        <span>{alert.created_at?.split('T')[0]}</span>\n"
        "        {alert.created_by_name && (\n"
        "          <span className=\"text-gray-400\">| انشأه: {alert.created_by_name}</span>\n"
        "        )}"
    )
    apply_fix("AlertCard: show created_by_name", path, old, new)

    # 5-i: تحديث api.js لاضافة createSupplier و updateSupplier لو مش موجودين
    api_path = FRONTEND + "/services/api.js"
    src = read(api_path)
    if "createSupplier" not in src:
        old_api = "  getSuppliers:           () => api.get('/inventory/suppliers/'),"
        new_api = (
            "  getSuppliers:           ()        => api.get('/inventory/suppliers/'),\n"
            "  createSupplier:         (data)    => api.post('/inventory/suppliers/', data),\n"
            "  updateSupplier:         (id,data) => api.patch(`/inventory/suppliers/${id}/`, data),"
        )
        apply_fix("api.js: createSupplier + updateSupplier", api_path, old_api, new_api)

# ── Section 6: InventoryPage.jsx — ازالة SuppliersPanel ──────────────────────
def fix_inventory_page():
    path = FRONTEND + "/pages/InventoryPage.jsx"
    print("\n[InventoryPage.jsx]")

    src = read(path)

    # ازالة تاب الموردين من الـ tabs array
    pattern_tab = r"\s*\{[^}]*key:\s*['\"]suppliers['\"][^}]*\},"
    if re.search(pattern_tab, src):
        backup(path)
        src = re.sub(pattern_tab, "", src, count=1)
        write(path, src)
        print("  OK: removed suppliers tab from InventoryPage tabs array")
    else:
        print("  SKIP: suppliers tab not found in InventoryPage (already removed or different pattern)")

    # ازالة render لـ SuppliersPanel
    for old in [
        "{tab==='suppliers' && <SuppliersPanel />}",
        "{tab === 'suppliers' && <SuppliersPanel />}",
    ]:
        if old in read(path):
            write(path, read(path).replace(old, ""))
            print("  OK: removed SuppliersPanel render from InventoryPage")
            break

# ── Section 7: CHANGELOG + README ─────────────────────────────────────────────
def fix_docs():
    print("\n[docs]")
    today = datetime.now().strftime("%Y-%m-%d")
    entry = "- " + today + ": Fix-06 — purchasing improvements (7 changes)."
    update_changelog(entry)

    lines = [
        "# FIXES README",
        "",
        "## Fix-06 — Purchasing Improvements",
        "**Date:** " + today,
        "",
        "### Changes Applied:",
        "1. **Remove receive button** from PurchaseOrdersPanel (receiving is done via Inventory section).",
        "2. **Multiple purchase quotes** per alert — removed single-PO restriction; StockAlert.linked_po FK replaced with linked_pos M2M.",
        "3. **Date validation fix** in StockAlertNoteSerializer.validate_expected_date — prevents past dates.",
        "4. **Auto-resolve alert** when all linked POs are received (check_and_auto_resolve + ticket_status update in receive action).",
        "5. **Suppliers tab** moved from InventoryPage to PurchasingPage (tab 3).",
        "6. **Assignment feature** — AssignSection component: assign-to-me / assign-to-user (manager only) / unassign; unassigned alerts show 'not assigned to anyone'.",
        "7. **created_by field** added to StockAlert model; shown in AlertCard and passed via check_and_generate.",
        "",
        "### Files Modified:",
        "- pos_backend/inventory/models.py",
        "- pos_backend/inventory/serializers.py",
        "- pos_backend/inventory/views.py",
        "- pos_frontend/src/services/api.js",
        "- pos_frontend/src/pages/PurchasingPage.jsx",
        "- pos_frontend/src/pages/InventoryPage.jsx",
        "",
        "### Migration Required:",
        "```bash",
        "cd " + BACKEND,
        "python manage.py makemigrations inventory --name fix06_created_by_linked_pos_m2m",
        "python manage.py migrate inventory",
        "```",
    ]
    write_readme(lines)
    print("  OK: CHANGELOG + README updated")

# ── main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("fix_06_purchasing_v2.py — started at " + STAMP)
    print("=" * 60)

    if not os.path.isdir(BACKEND):
        abort("BACKEND dir not found: " + BACKEND)
    if not os.path.isdir(FRONTEND):
        abort("FRONTEND dir not found: " + FRONTEND)

    fix_models()
    fix_serializers()
    fix_views()
    fix_api_js()
    fix_purchasing_page()
    fix_inventory_page()
    fix_docs()

    print("\n" + "=" * 60)
    print("DONE. Next steps:")
    print("  cd " + BACKEND)
    print("  python manage.py makemigrations inventory --name fix06_created_by_linked_pos_m2m")
    print("  python manage.py migrate inventory")
    print("=" * 60)

if __name__ == "__main__":
    main()
