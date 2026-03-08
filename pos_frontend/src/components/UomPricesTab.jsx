
/**
 * UomPricesTab.jsx
 * تبويب "الوحدات والأسعار" داخل ProductModal
 *
 * Props:
 *   form        — كائن الفورم الحالي { base_unit, purchase_unit, ... }
 *   set         — (key, val) => void  لتحديث الفورم
 *   units       — قائمة UnitOfMeasure من API
 *   unitPrices  — [{ unit, unit_name, factor, price, is_auto, is_active }]
 *   onPriceChange — (unitId, field, val) => void
 *   onAddPrice  — (unitId) => void
 *   onRemovePrice — (unitId) => void
 *   isEdit      — bool (هل هو تعديل أم إنشاء جديد)
 */
import { useMemo } from 'react';

const INP = 'w-full border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none ' +
            'focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition bg-white';

export default function UomPricesTab({
  form, set, units = [],
  unitPrices = [], onPriceChange, onAddPrice, onRemovePrice,
  isEdit = false,
}) {
  const activeUnits = useMemo(() => units.filter(u => u.is_active), [units]);

  // الوحدات اللي ممكن نضيفها (مش موجودة في unit_prices)
  const addableUnits = useMemo(() =>
    activeUnits.filter(u => !unitPrices.some(p => p.unit === u.id)),
    [activeUnits, unitPrices]
  );

  return (
    <div className="space-y-5">

      {/* ── الوحدة الأساسية ووحدة الشراء ─────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-bold text-gray-500 mb-1">
            الوحدة الأساسية
            <span className="text-gray-400 font-normal mr-1">(المخزون يُحسب بها)</span>
          </label>
          <select className={INP}
            value={form.base_unit || ''}
            onChange={e => set('base_unit', e.target.value || null)}
          >
            <option value="">— بدون وحدة —</option>
            {activeUnits.map(u => (
              <option key={u.id} value={u.id}>
                {u.name} {u.symbol ? `(${u.symbol})` : ''}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-bold text-gray-500 mb-1">
            وحدة الشراء الافتراضية
            <span className="text-gray-400 font-normal mr-1">(في أوامر الشراء)</span>
          </label>
          <select className={INP}
            value={form.purchase_unit || ''}
            onChange={e => set('purchase_unit', e.target.value || null)}
          >
            <option value="">— نفس الأساسية —</option>
            {activeUnits.map(u => (
              <option key={u.id} value={u.id}>
                {u.name} {u.symbol ? `(${u.symbol})` : ''}
                {u.factor !== '1.0000' && u.factor !== '1' ? ` × ${u.factor}` : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ── أسعار الوحدات (بعد الحفظ فقط) ──────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="font-bold text-gray-700 text-sm">أسعار البيع لكل وحدة</h4>
            <p className="text-xs text-gray-400 mt-0.5">
              السعر التلقائي = سعر البيع × معامل الوحدة
            </p>
          </div>
          {isEdit && addableUnits.length > 0 && (
            <select
              className="border border-blue-200 rounded-xl px-3 py-1.5 text-sm text-blue-700 font-bold bg-blue-50 outline-none cursor-pointer hover:bg-blue-100 transition"
              value=""
              onChange={e => { if (e.target.value) onAddPrice(e.target.value); }}
            >
              <option value="">+ إضافة وحدة</option>
              {addableUnits.map(u => (
                <option key={u.id} value={u.id}>
                  {u.name} (× {u.factor})
                </option>
              ))}
            </select>
          )}
        </div>

        {!isEdit && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 text-sm text-blue-700 font-bold flex items-center gap-2">
            <i className="fas fa-info-circle"></i>
            أسعار الوحدات تُضاف بعد حفظ المنتج — احفظ أولاً ثم عدّل لإضافة أسعار.
          </div>
        )}

        {isEdit && unitPrices.length === 0 && (
          <div className="bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-500 text-center">
            <i className="fas fa-tags ml-2 opacity-50"></i>
            لا توجد وحدات مضافة — اختر وحدة من القائمة أعلاه لإضافتها.
          </div>
        )}

        {isEdit && unitPrices.length > 0 && (
          <div className="space-y-2">
            {/* Header */}
            <div className="grid grid-cols-12 gap-2 px-3 py-1">
              <span className="col-span-3 text-xs font-bold text-gray-400">الوحدة</span>
              <span className="col-span-2 text-xs font-bold text-gray-400 text-center">المعامل</span>
              <span className="col-span-3 text-xs font-bold text-gray-400 text-center">السعر</span>
              <span className="col-span-2 text-xs font-bold text-gray-400 text-center">تلقائي</span>
              <span className="col-span-1 text-xs font-bold text-gray-400 text-center">نشط</span>
              <span className="col-span-1"></span>
            </div>

            {unitPrices.map(up => (
              <div key={up.unit}
                className={`grid grid-cols-12 gap-2 items-center px-3 py-2 rounded-xl border
                  ${up.is_active ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-100 opacity-60'}`}
              >
                {/* اسم الوحدة */}
                <div className="col-span-3">
                  <span className="font-bold text-gray-700 text-sm">{up.unit_name}</span>
                </div>

                {/* المعامل */}
                <div className="col-span-2 text-center">
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-lg font-mono">
                    ×{up.factor}
                  </span>
                </div>

                {/* السعر */}
                <div className="col-span-3">
                  <input
                    type="number" step="0.01" min="0"
                    disabled={up.is_auto}
                    value={up.price}
                    onChange={e => onPriceChange(up.unit, 'price', e.target.value)}
                    className={`w-full border rounded-lg px-2 py-1 text-sm text-center font-bold outline-none transition
                      ${up.is_auto
                        ? 'bg-gray-100 text-gray-500 border-gray-200 cursor-not-allowed'
                        : 'border-blue-300 focus:ring-2 focus:ring-blue-100 text-blue-700'
                      }`}
                  />
                </div>

                {/* تلقائي toggle */}
                <div className="col-span-2 flex justify-center">
                  <button
                    type="button"
                    onClick={() => onPriceChange(up.unit, 'is_auto', !up.is_auto)}
                    className={`w-10 h-5 rounded-full transition relative
                      ${up.is_auto ? 'bg-blue-500' : 'bg-gray-300'}`}
                    title={up.is_auto ? 'تلقائي — اضغط لتعديل يدوي' : 'يدوي — اضغط لتلقائي'}
                  >
                    <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-all
                      ${up.is_auto ? 'right-0.5' : 'left-0.5'}`}
                    />
                  </button>
                </div>

                {/* نشط toggle */}
                <div className="col-span-1 flex justify-center">
                  <input type="checkbox"
                    checked={up.is_active}
                    onChange={e => onPriceChange(up.unit, 'is_active', e.target.checked)}
                    className="w-4 h-4 accent-blue-600 cursor-pointer"
                  />
                </div>

                {/* حذف */}
                <div className="col-span-1 flex justify-center">
                  <button type="button"
                    onClick={() => onRemovePrice(up.unit)}
                    className="text-red-400 hover:text-red-600 transition text-sm"
                    title="حذف"
                  >
                    <i className="fas fa-times"></i>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
