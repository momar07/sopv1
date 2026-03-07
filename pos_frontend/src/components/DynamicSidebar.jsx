import { Link, useLocation } from 'react-router-dom';
import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useReturnsBadge } from '../context/ReturnsBadgeContext';

export default function DynamicSidebar() {
  const location  = useLocation();
  const { ui, isAdmin, isManager } = useAuth();
  const { pending, approved }      = useReturnsBadge();

  const items = ui?.sidebar || [];

  const [collapsed, setCollapsed] = React.useState(() => {
    try { return localStorage.getItem('pos_sidebar_collapsed_v2') === '1'; }
    catch { return false; }
  });

  React.useEffect(() => {
    try { localStorage.setItem('pos_sidebar_collapsed_v2', collapsed ? '1' : '0'); }
    catch {}
  }, [collapsed]);

  const isActive = (path) => location.pathname === path;

  const fallbackIconByKeyOrPath = (item) => {
    const k = String(item?.key || '').toLowerCase();
    const p = String(item?.path || '').toLowerCase();
    if (k.includes('dashboard')  || p.includes('dashboard'))    return 'fas fa-chart-line';
    if (k.includes('pos')        || p === '/' || p.includes('/pos')) return 'fas fa-cash-register';
    if (k.includes('products')   || p.includes('products'))     return 'fas fa-boxes-stacked';
    if (k.includes('customers')  || p.includes('customers'))    return 'fas fa-users';
    if (k.includes('operations') || p.includes('operations'))   return 'fas fa-receipt';
    if (k.includes('returns')    || p.includes('returns'))      return 'fas fa-rotate-left';
    if (k.includes('reports')    || p.includes('reports'))      return 'fas fa-file-invoice';
    if (k.includes('cash')       || p.includes('cash-register'))return 'fas fa-money-bill-wave';
    if (k.includes('inventory')  || p.includes('inventory'))    return 'fas fa-warehouse';
    if (k.includes('users')      || p.includes('/users'))       return 'fas fa-user-cog';
    if (k.includes('performance')|| p.includes('performance'))  return 'fas fa-trophy';
    if (k.includes('settings')   || p.includes('settings'))     return 'fas fa-gear';
    return 'fas fa-circle';
  };

  // هل المستخدم يرى badges المرتجعات؟
  const isAdminVal   = typeof isAdmin   === 'function' ? isAdmin()   : !!isAdmin;
  const isManagerVal = typeof isManager === 'function' ? isManager() : !!isManager;
  const canSeeBadge  = isAdminVal || isManagerVal;

  const isReturnItem = (item) =>
    String(item?.path || '').includes('returns') ||
    String(item?.key  || '').toLowerCase().includes('return');

  return (
    <aside
      className={`bg-gray-800 text-white ${collapsed ? 'w-20' : 'w-64'} h-full p-4 overflow-y-auto flex flex-col transition-all duration-200`}
      aria-label="Sidebar"
    >
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className={`text-2xl font-bold ${collapsed ? 'text-center w-full' : ''}`}>
          <i className="fas fa-store ml-2"></i>
          {!collapsed && 'POS'}
        </div>
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="text-gray-200 hover:text-white p-2 rounded-lg hover:bg-gray-700 transition-colors"
          title={collapsed ? 'توسيع القائمة' : 'تصغير القائمة'}
          type="button"
        >
          <i className={`fas ${collapsed ? 'fa-angle-left' : 'fa-angle-right'}`}></i>
        </button>
      </div>

      {/* Menu */}
      <nav className="space-y-2 flex-1">
        {items.map((item) => {
          const active  = isActive(item.path);
          const iconCls = (item.icon && String(item.icon).includes('fa'))
            ? item.icon
            : fallbackIconByKeyOrPath(item);

          // حساب الـ badge لعنصر المرتجعات
          const showBadge   = canSeeBadge && isReturnItem(item);
          const badgeCount  = showBadge ? (pending + approved) : 0;
          const badgeCls    = pending > 0
            ? 'bg-red-500'       // أحمر لو فيه pending
            : 'bg-orange-400';   // برتقالي لو فيه approved بس

          return (
            <Link
              key={item.key || item.path}
              to={item.path}
              title={collapsed ? item.label : undefined}
              className={`relative flex items-center p-3 rounded-lg transition-colors ${
                active ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              } ${collapsed ? 'justify-center' : ''}`}
            >
              <i className={`${iconCls} ${collapsed ? '' : 'ml-3'}`}></i>
              {!collapsed && <span className="font-medium flex-1">{item.label}</span>}

              {/* Badge */}
              {showBadge && badgeCount > 0 && (
                <span className={`${badgeCls} text-white text-xs font-bold rounded-full min-w-[20px] h-5 flex items-center justify-center px-1 ${collapsed ? 'absolute top-1 right-1' : ''}`}>
                  {badgeCount > 99 ? '99+' : badgeCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="pt-4 border-t border-gray-700 text-xs text-gray-400">
        {!collapsed ? 'Dynamic UI' : 'UI'}
      </div>
    </aside>
  );
}
