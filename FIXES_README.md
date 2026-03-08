# Fix: BarcodePOS - paidAmount / Cart State Persistence Bug

## Date
2026-03-08 13:44

## المشكلة
بعد اتمام عملية البيع في BarcodePOS.jsx، عند الانتقال لصفحة اخرى والرجوع
يظهر الـ paidAmount القديم واحيانا تعود السلة كما كانت.

## السبب الجذري
الـ component يستخدم debounce بـ 5 ثواني (scheduleSave) يستدعي
saveStateNow() بعد كل تغيير في الـ state. عند تنفيذ finalizeSale():

1. يتم reset الـ state في React (setPaidAmount(''), setDiscount(0) ...)
2. لكن saveStateNow محجوز في closure قديم لا يزال يحمل القيم القديمة
3. بعد 5 ثواني من البيع يكتب هذا الـ closure القيم القديمة في localStorage

## الاصلاح المطبق

### Fix 1 - الغاء الـ timer فورا عند بدء finalizeSale
```js
if (saveTimer.current) {
  clearTimeout(saveTimer.current);
  saveTimer.current = null;
}
```

### Fix 2 - كتابة state نظيف في localStorage فورا (success path)
```js
localStorage.setItem(POS_STATE_KEY, JSON.stringify({
  tabs:          cleanTabs,
  activeTabId:   cleanActive,
  discount:      0,
  tax:           0,
  paymentMethod: 'cash',
  paidAmount:    '',
  note:          '',
  savedAt:       Date.now(),
}));
```

### Fix 3 - نفس الاصلاح في الـ offline (catch) path

## الملفات المعدلة
| الملف | التغيير |
|-------|---------|
| pos_frontend/src/pages/BarcodePOS.jsx | اضافة clearTimeout + كتابة cleanState فورا |
| CHANGELOG.md | تحديث تلقائي |
| FIXES_README.md | هذا الملف |

## كيف تتحقق من الاصلاح
1. اضف منتجات واكتب مبلغ مدفوع
2. اضغط بيع
3. انتقل لصفحة اخرى ثم ارجع
4. السلة والـ paidAmount فارغين تماما

## لا تحتاج migrations او اعادة تشغيل backend
فقط: cd pos_frontend && npm run dev
