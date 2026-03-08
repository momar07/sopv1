#!/usr/bin/env python3
# =============================================================
# fix_barcode_pos_state.py
# اصلاح: paidAmount والـ cart يرجعوا بعد عملية البيع
# =============================================================

import os
import re
import shutil
from datetime import datetime

# ── المسارات ──────────────────────────────────────────────────
BASE      = "/home/momar/Projects/POS_DEV/posv1_dev10"
TARGET    = os.path.join(BASE, "pos_frontend/src/pages/BarcodePOS.jsx")
CHANGELOG = os.path.join(BASE, "CHANGELOG.md")
README    = os.path.join(BASE, "FIXES_README.md")
# ─────────────────────────────────────────────────────────────

CHANGE_MSG = "اصلاح: paidAmount والـ cart يرجعوا بعد البيع (BarcodePOS persistence bug)"


# ── Helpers ───────────────────────────────────────────────────
def abort(msg):
    print("\n❌  " + msg)
    raise SystemExit(1)


def backup(path):
    bak = path + ".bak"
    shutil.copy2(path, bak)
    print("   💾  backup → " + bak)


def update_changelog(msg):
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = "\n## [" + now + "] " + msg + "\n"
    try:
        txt = open(CHANGELOG, encoding="utf-8").read()
        new = re.sub(r"(---\s*\n)", r"\1" + entry, txt, count=1)
        open(CHANGELOG, "w", encoding="utf-8").write(new)
        print("   📝  CHANGELOG updated")
    except Exception as e:
        print("   ⚠️   CHANGELOG skipped: " + str(e))


# ── README ────────────────────────────────────────────────────
def write_readme():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Fix: BarcodePOS - paidAmount / Cart State Persistence Bug",
        "",
        "## Date",
        now,
        "",
        "## المشكلة",
        "بعد اتمام عملية البيع في BarcodePOS.jsx، عند الانتقال لصفحة اخرى والرجوع",
        "يظهر الـ paidAmount القديم واحيانا تعود السلة كما كانت.",
        "",
        "## السبب الجذري",
        "الـ component يستخدم debounce بـ 5 ثواني (scheduleSave) يستدعي",
        "saveStateNow() بعد كل تغيير في الـ state. عند تنفيذ finalizeSale():",
        "",
        "1. يتم reset الـ state في React (setPaidAmount(''), setDiscount(0) ...)",
        "2. لكن saveStateNow محجوز في closure قديم لا يزال يحمل القيم القديمة",
        "3. بعد 5 ثواني من البيع يكتب هذا الـ closure القيم القديمة في localStorage",
        "",
        "## الاصلاح المطبق",
        "",
        "### Fix 1 - الغاء الـ timer فورا عند بدء finalizeSale",
        "```js",
        "if (saveTimer.current) {",
        "  clearTimeout(saveTimer.current);",
        "  saveTimer.current = null;",
        "}",
        "```",
        "",
        "### Fix 2 - كتابة state نظيف في localStorage فورا (success path)",
        "```js",
        "localStorage.setItem(POS_STATE_KEY, JSON.stringify({",
        "  tabs:          cleanTabs,",
        "  activeTabId:   cleanActive,",
        "  discount:      0,",
        "  tax:           0,",
        "  paymentMethod: 'cash',",
        "  paidAmount:    '',",
        "  note:          '',",
        "  savedAt:       Date.now(),",
        "}));",
        "```",
        "",
        "### Fix 3 - نفس الاصلاح في الـ offline (catch) path",
        "",
        "## الملفات المعدلة",
        "| الملف | التغيير |",
        "|-------|---------|",
        "| pos_frontend/src/pages/BarcodePOS.jsx | اضافة clearTimeout + كتابة cleanState فورا |",
        "| CHANGELOG.md | تحديث تلقائي |",
        "| FIXES_README.md | هذا الملف |",
        "",
        "## كيف تتحقق من الاصلاح",
        "1. اضف منتجات واكتب مبلغ مدفوع",
        "2. اضغط بيع",
        "3. انتقل لصفحة اخرى ثم ارجع",
        "4. السلة والـ paidAmount فارغين تماما",
        "",
        "## لا تحتاج migrations او اعادة تشغيل backend",
        "فقط: cd pos_frontend && npm run dev",
    ]

    open(README, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("   📄  README → " + README)


# ── التعديلات على الكود ───────────────────────────────────────

# ---------- Fix 1: اضافة clearTimeout ----------
OLD_1 = (
    "    // ✅ هنا — قبل أي حاجة\n"
    "    const closedTabId = activeTabId;"
)

NEW_1 = (
    "    // ✅ هنا — قبل أي حاجة\n"
    "    const closedTabId = activeTabId;\n"
    "\n"
    "    // ✅ FIX-1: الغاء اي debounce timer معلق لمنع كتابة stale state\n"
    "    if (saveTimer.current) {\n"
    "      clearTimeout(saveTimer.current);\n"
    "      saveTimer.current = null;\n"
    "    }"
)

# ---------- Fix 2: استبدال localStorage block في success path ----------
OLD_2 = (
    "      try {\n"
    "        const st = JSON.parse(localStorage.getItem(POS_STATE_KEY) || '{}');\n"
    "        if (st?.tabs) {\n"
    "          if (st.tabs.length > 1) {\n"
    "            st.tabs = st.tabs.filter((t) => t.id !== closedTabId);\n"
    "            st.activeTabId = st.tabs[st.tabs.length - 1]?.id;\n"
    "          } else {\n"
    "            st.tabs = st.tabs.map((t) => ({ ...t, cart: [] }));\n"
    "          }\n"
    "          localStorage.setItem(POS_STATE_KEY, JSON.stringify(st));\n"
    "        }\n"
    "      } catch {}"
)

NEW_2 = (
    "      // ✅ FIX-2: كتابة cleanState فورا لمنع stale closure من الكتابة لاحقا\n"
    "      try {\n"
    "        const st       = JSON.parse(localStorage.getItem(POS_STATE_KEY) || '{}');\n"
    "        let cleanTabs   = Array.isArray(st?.tabs) ? st.tabs : [];\n"
    "        let cleanActive = st?.activeTabId;\n"
    "\n"
    "        if (cleanTabs.length > 1) {\n"
    "          cleanTabs   = cleanTabs.filter((t) => t.id !== closedTabId);\n"
    "          cleanActive = cleanTabs[cleanTabs.length - 1]?.id;\n"
    "        } else {\n"
    "          cleanTabs = cleanTabs.map((t) => ({ ...t, cart: [] }));\n"
    "        }\n"
    "\n"
    "        localStorage.setItem(POS_STATE_KEY, JSON.stringify({\n"
    "          tabs:          cleanTabs,\n"
    "          activeTabId:   cleanActive,\n"
    "          discount:      0,\n"
    "          tax:           0,\n"
    "          paymentMethod: 'cash',\n"
    "          paidAmount:    '',\n"
    "          note:          '',\n"
    "          savedAt:       Date.now(),\n"
    "        }));\n"
    "      } catch {}"
)

# ---------- Fix 3: اضافة cleanState في offline path ----------
OLD_3 = (
    "      setDiscount(0);\n"
    "      setTax(0);\n"
    "      setPaymentMethod('cash');\n"
    "      setPaidAmount('');\n"
    "      setNote('');\n"
    "      closeOrResetAfterSale(closedTabId);\n"
    "\n"
    "      if (lockScanner) setTimeout(() => barcodeRef.current?.focus?.(), 80);\n"
    "    }\n"
    "  }, ["
)

NEW_3 = (
    "      setDiscount(0);\n"
    "      setTax(0);\n"
    "      setPaymentMethod('cash');\n"
    "      setPaidAmount('');\n"
    "      setNote('');\n"
    "      closeOrResetAfterSale(closedTabId);\n"
    "\n"
    "      // ✅ FIX-3: كتابة cleanState فورا (offline path)\n"
    "      try {\n"
    "        const st       = JSON.parse(localStorage.getItem(POS_STATE_KEY) || '{}');\n"
    "        let cleanTabs   = Array.isArray(st?.tabs) ? st.tabs : [];\n"
    "        let cleanActive = st?.activeTabId;\n"
    "\n"
    "        if (cleanTabs.length > 1) {\n"
    "          cleanTabs   = cleanTabs.filter((t) => t.id !== closedTabId);\n"
    "          cleanActive = cleanTabs[cleanTabs.length - 1]?.id;\n"
    "        } else {\n"
    "          cleanTabs = cleanTabs.map((t) => ({ ...t, cart: [] }));\n"
    "        }\n"
    "\n"
    "        localStorage.setItem(POS_STATE_KEY, JSON.stringify({\n"
    "          tabs:          cleanTabs,\n"
    "          activeTabId:   cleanActive,\n"
    "          discount:      0,\n"
    "          tax:           0,\n"
    "          paymentMethod: 'cash',\n"
    "          paidAmount:    '',\n"
    "          note:          '',\n"
    "          savedAt:       Date.now(),\n"
    "        }));\n"
    "      } catch {}\n"
    "\n"
    "      if (lockScanner) setTimeout(() => barcodeRef.current?.focus?.(), 80);\n"
    "    }\n"
    "  }, ["
)


# ── apply_fix ─────────────────────────────────────────────────
def apply_fix():
    if not os.path.isfile(TARGET):
        abort("الملف غير موجود:\n   " + TARGET)

    backup(TARGET)
    src      = open(TARGET, encoding="utf-8").read()
    original = src

    # Fix 1
    if OLD_1 not in src:
        abort("Fix-1: لم اجد نقطة الادراج — تاكد من الكود")
    src = src.replace(OLD_1, NEW_1, 1)
    print("   ✅  Fix-1: clearTimeout اضيف")

    # Fix 2
    if OLD_2 not in src:
        abort("Fix-2: لم اجد localStorage block في success path")
    src = src.replace(OLD_2, NEW_2, 1)
    print("   ✅  Fix-2: cleanState write في success path")

    # Fix 3
    if OLD_3 not in src:
        abort("Fix-3: لم اجد offline reset block")
    src = src.replace(OLD_3, NEW_3, 1)
    print("   ✅  Fix-3: cleanState write في offline path")

    if src == original:
        abort("لم يحدث اي تغيير — ربما الاصلاح مطبق مسبقا")

    open(TARGET, "w", encoding="utf-8").write(src)
    print("   💾  الملف محفوظ: " + TARGET)


# ── main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("=" * 58)
    print("  🔧  fix_barcode_pos_state.py")
    print("=" * 58)

    print("\n[1/3] تطبيق الاصلاحات على BarcodePOS.jsx ...")
    apply_fix()

    print("\n[2/3] كتابة FIXES_README.md ...")
    write_readme()

    print("\n[3/3] تحديث CHANGELOG.md ...")
    update_changelog(CHANGE_MSG)

    print()
    print("=" * 58)
    print("  🎉  تم بنجاح!")
    print()
    print("  الخطوة التالية:")
    print("  cd pos_frontend && npm run dev")
    print()
    print("  للتحقق:")
    print("  1. اضف منتجات + اكتب مبلغ مدفوع")
    print("  2. اضغط بيع")
    print("  3. انتقل لصفحة اخرى وارجع")
    print("  4. ✅ السلة والـ paidAmount فارغين")
    print("=" * 58)
    print()
