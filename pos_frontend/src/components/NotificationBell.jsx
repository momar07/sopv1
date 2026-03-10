/**
 * Fix-25: NotificationBell — جرس التنبيهات في الـ Navbar
 */
import React, { useState } from 'react';
import { useAlertPolling } from '../hooks/useAlertPolling';

const priorityColor = {
  critical: 'bg-red-500',
  high:     'bg-orange-500',
  medium:   'bg-yellow-500',
  low:      'bg-blue-400',
};

export function NotificationBell({ onNavigateToAlerts }) {
  const [showToast, setShowToast] = useState(false);
  const [toastMsg,  setToastMsg]  = useState('');

  const { unreadCount, topPriority, lastChecked, clearUnread } = useAlertPolling({
    enabled: true,
    onNewAlert: ({ count, priority }) => {
      const priorityLabel = { critical:'حرجة', high:'عالية', medium:'متوسطة', low:'منخفضة' };
      setToastMsg(`🔔 ${count} تنبيه جديد — أولوية ${priorityLabel[priority] || ''}`);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 5000);
    },
  });

  const handleClick = () => {
    clearUnread();
    if (onNavigateToAlerts) onNavigateToAlerts();
  };

  const badgeColor = priorityColor[topPriority] || 'bg-red-500';

  return (
    <>
      {/* Toast notification */}
      {showToast && (
        <div
          onClick={() => { setShowToast(false); handleClick(); }}
          className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] cursor-pointer
            bg-white border border-orange-200 shadow-2xl rounded-2xl px-5 py-3
            flex items-center gap-3 animate-bounce"
          style={{ minWidth: 280 }}>
          <span className="text-2xl">🔔</span>
          <div>
            <p className="font-black text-gray-800 text-sm">{toastMsg}</p>
            <p className="text-xs text-gray-400 mt-0.5">اضغط للانتقال للمشتريات</p>
          </div>
          <button onClick={e => { e.stopPropagation(); setShowToast(false); }}
            className="text-gray-400 hover:text-gray-600 font-black text-lg mr-auto">×</button>
        </div>
      )}

      {/* Bell button */}
      <button
        onClick={handleClick}
        title={lastChecked ? `آخر تحديث: ${lastChecked.toLocaleTimeString('ar')}` : 'التنبيهات'}
        className="relative p-2 rounded-xl hover:bg-gray-100 transition">
        <span className="text-xl">🔔</span>
        {unreadCount > 0 && (
          <span className={`absolute -top-1 -right-1 ${badgeColor} text-white
            text-[10px] font-black rounded-full min-w-[18px] h-[18px]
            flex items-center justify-center px-1`}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
    </>
  );
}
