/**
 * Fix-25c: NotificationBell
 * - Badge دايم: totalUnresolved (كل التنبيهات المفتوحة)
 * - Toast: بس لما يكون في تنبيهات جديدة
 */
import React, { useState } from 'react';
import { useAlertPolling } from '../hooks/useAlertPolling';

const priorityColor = {
  critical: 'bg-red-500',
  high:     'bg-orange-500',
  medium:   'bg-yellow-500',
  low:      'bg-blue-400',
};

const priorityLabel = {
  critical: 'حرجة',
  high:     'عالية',
  medium:   'متوسطة',
  low:      'منخفضة',
};

export function NotificationBell({ onNavigateToAlerts }) {
  const [showToast, setShowToast] = useState(false);
  const [toastMsg,  setToastMsg]  = useState('');

  const { totalUnresolved, newCount, topPriority, lastChecked, clearNew } = useAlertPolling({
    enabled: true,
    onNewAlert: ({ count, priority }) => {
      setToastMsg(`🔔 ${count} تنبيه جديد — أولوية ${priorityLabel[priority] || ''}`);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 5000);
    },
  });

  const handleClick = () => {
    clearNew();
    setShowToast(false);
    if (onNavigateToAlerts) onNavigateToAlerts();
  };

  // لون الـ Badge حسب الأولوية
  const badgeColor = priorityColor[topPriority] || 'bg-red-500';

  return (
    <>
      {/* ── Toast للتنبيهات الجديدة فقط ── */}
      {showToast && (
        <div
          onClick={handleClick}
          className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] cursor-pointer
            bg-white border-2 border-orange-300 shadow-2xl rounded-2xl px-5 py-3
            flex items-center gap-3"
          style={{ minWidth: 300 }}>
          <span className="text-2xl animate-bounce">🔔</span>
          <div className="flex-1">
            <p className="font-black text-gray-800 text-sm">{toastMsg}</p>
            <p className="text-xs text-blue-500 mt-0.5 font-bold">اضغط للانتقال للمشتريات ←</p>
          </div>
          <button
            onClick={e => { e.stopPropagation(); setShowToast(false); }}
            className="text-gray-400 hover:text-gray-600 font-black text-xl leading-none">
            ×
          </button>
        </div>
      )}

      {/* ── جرس التنبيهات ── */}
      <button
        onClick={handleClick}
        title={
          totalUnresolved > 0
            ? `${totalUnresolved} تنبيه مفتوح · آخر تحديث: ${lastChecked?.toLocaleTimeString('ar') || '...'}` 
            : 'لا توجد تنبيهات مفتوحة'
        }
        className="relative p-2 rounded-xl hover:bg-gray-100 transition-all duration-200">

        {/* أيقونة الجرس */}
        <span className={`text-xl transition-all ${totalUnresolved > 0 ? 'animate-pulse' : ''}`}>
          🔔
        </span>

        {/* Badge الإجمالي — يظهر دايم لو في تنبيهات مفتوحة */}
        {totalUnresolved > 0 && (
          <span className={`
            absolute -top-1 -right-1 ${badgeColor} text-white
            text-[10px] font-black rounded-full min-w-[18px] h-[18px]
            flex items-center justify-center px-1 shadow-sm
            transition-all duration-300
          `}>
            {totalUnresolved > 99 ? '99+' : totalUnresolved}
          </span>
        )}

        {/* نقطة خضراء لو مافيش تنبيهات */}
        {totalUnresolved === 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-green-400 rounded-full border-2 border-white"></span>
        )}
      </button>
    </>
  );
}
