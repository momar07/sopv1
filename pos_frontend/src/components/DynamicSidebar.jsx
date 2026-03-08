import { Link, useLocation } from 'react-router-dom';
import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useReturnsBadge } from '../context/ReturnsBadgeContext';

// ─── build tree from flat sidebar list ───────────────────────────────────────
function buildTree(items) {
  const map = {};
  const roots = [];

  // أول مرور: ننشئ كل node مع children فاضي
  items.forEach((item) => {
    map[item.key] = { ...item, children: [] };
  });

  // تاني مرور: نربط كل child بـ parent بتاعه
  items.forEach((item) => {
    if (item.parent_key && map[item.parent_key]) {
      map[item.parent_key].children.push(map[item.key]);
    } else {
      roots.push(map[item.key]);
    }
  });

  // ترتيب كل مستوى بـ order
  const sortByOrder = (arr) =>
    [...arr].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));

  roots.forEach((r) => {
    r.children = sortByOrder(r.children);
  });

  return sortByOrder(roots);
}

// ─── fallback icon ───────────────────────────────────────────────────────────
function fallbackIcon(item) {
  const k = String(item?.key  || '').toLowerCase();
  const p = String(item?.path || '').toLowerCase();
  if (k.includes('dashboard')   || p.includes('dashboard'))     return 'fas fa-chart-line';
  if (k.includes('pos')         || p.includes('/pos'))          return 'fas fa-cash-register';
  if (k.includes('operations')  || p.includes('operations'))    return 'fas fa-receipt';
  if (k.includes('returns')     || p.includes('returns'))       return 'fas fa-rotate-left';
  if (k.includes('customers')   || p.includes('customers'))     return 'fas fa-users';
  if (k.includes('inventory')   || p.includes('inventory'))     return 'fas fa-warehouse';
  if (k.includes('financial')   || p.includes('financial'))     return 'fas fa-chart-bar';
  if (k.includes('cash')        || p.includes('cash-register')) return 'fas fa-coins';
  if (k.includes('users')       || p.includes('/users'))        return 'fas fa-user-cog';
  if (k.includes('settings')    || p.includes('settings'))      return 'fas fa-sliders-h';
  if (k.includes('sales')       || k.includes('section'))       return 'fas fa-layer-group';
  return 'fas fa-circle';
}

// ─── SidebarItem — يعرض node واحد (مع children لو section) ───────────────────
function SidebarItem({ node, collapsed, depth = 0 }) {
  const location  = useLocation();
  const { pending, approved } = useReturnsBadge();
  const { isAdmin, isManager } = useAuth();

  const isAdminVal   = typeof isAdmin   === 'function' ? isAdmin()   : !!isAdmin;
  const isManagerVal = typeof isManager === 'function' ? isManager() : !!isManager;
  const canSeeBadge  = isAdminVal || isManagerVal;

  const isReturnNode = (n) =>
    String(n?.path || '').includes('returns') ||
    String(n?.key  || '').toLowerCase().includes('return');

  const hasChildren = node.children && node.children.length > 0;
  const isSection   = hasChildren || !node.path;

  // تحديد الـ active state
  const isActivePath = (path) => !!path && location.pathname === path;
  const isActiveSection = hasChildren &&
    node.children.some((c) => isActivePath(c.path));

  const [open, setOpen] = React.useState(() => isActiveSection);

  // لما الـ route يتغير، افتح الـ section لو فيه child active
  React.useEffect(() => {
    if (hasChildren && node.children.some((c) => isActivePath(c.path))) {
      setOpen(true);
    }
  }, [location.pathname]);

  const iconCls = (node.icon && String(node.icon).includes('fa'))
    ? node.icon
    : fallbackIcon(node);

  // ── Section (parent بدون path أو عنده children) ──────────────────────────
  if (isSection) {
    return (
      <div className="space-y-1">
        {/* Section header */}
        <button
          onClick={() => setOpen((v) => !v)}
          className={`w-full flex items-center p-3 rounded-lg transition-colors text-gray-300 hover:bg-gray-700 hover:text-white ${
            isActiveSection ? 'text-blue-400' : ''
          } ${collapsed ? 'justify-center' : ''}`}
          title={collapsed ? node.label : undefined}
          type="button"
        >
          <i className={`${iconCls} ${collapsed ? '' : 'ml-3'}`}></i>
          {!collapsed && (
            <>
              <span className="font-medium flex-1 text-right">{node.label}</span>
              <i className={`fas fa-chevron-${open ? 'up' : 'down'} text-xs text-gray-400`}></i>
            </>
          )}
        </button>

        {/* Children */}
        {!collapsed && open && (
          <div className="mr-4 border-r border-gray-600 pr-2 space-y-1">
            {node.children.map((child) => (
              <SidebarItem
                key={child.key}
                node={child}
                collapsed={false}
                depth={depth + 1}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── Link عادي ──────────────────────────────────────────────────────────────
  const active      = isActivePath(node.path);
  const showBadge   = canSeeBadge && isReturnNode(node);
  const badgeCount  = showBadge ? (pending + approved) : 0;
  const badgeCls    = pending > 0 ? 'bg-red-500' : 'bg-orange-400';

  return (
    <Link
      to={node.path}
      title={collapsed ? node.label : undefined}
      className={`relative flex items-center p-3 rounded-lg transition-colors ${
        active
          ? 'bg-blue-600 text-white'
          : 'text-gray-300 hover:bg-gray-700 hover:text-white'
      } ${collapsed ? 'justify-center' : ''}`}
    >
      <i className={`${iconCls} ${collapsed ? '' : 'ml-3'}`}></i>
      {!collapsed && (
        <span className="font-medium flex-1">{node.label}</span>
      )}
      {showBadge && badgeCount > 0 && (
        <span
          className={`${badgeCls} text-white text-xs font-bold rounded-full min-w-[20px] h-5 flex items-center justify-center px-1 ${
            collapsed ? 'absolute top-1 right-1' : ''
          }`}
        >
          {badgeCount > 99 ? '99+' : badgeCount}
        </span>
      )}
    </Link>
  );
}

// ─── DynamicSidebar ──────────────────────────────────────────────────────────
export default function DynamicSidebar() {
  const { ui, logout } = useAuth();

  const [collapsed, setCollapsed] = React.useState(() => {
    try { return localStorage.getItem('pos_sidebar_collapsed_v2') === '1'; }
    catch { return false; }
  });

  React.useEffect(() => {
    try { localStorage.setItem('pos_sidebar_collapsed_v2', collapsed ? '1' : '0'); }
    catch {}
  }, [collapsed]);

  // بناء الـ tree من الـ flat list اللي بيجي من الـ backend
  const flatItems = ui?.sidebar || [];
  const tree      = React.useMemo(() => buildTree(flatItems), [flatItems]);

  return (
    <aside
      className={`bg-gray-800 text-white ${
        collapsed ? 'w-20' : 'w-64'
      } h-full flex flex-col transition-all duration-200 overflow-hidden`}
      aria-label="Sidebar"
    >
      {/* Header */}
      <div className="p-4 mb-2 flex items-center justify-between border-b border-gray-700">
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
      <nav className="flex-1 overflow-y-auto p-4 space-y-1">
        {tree.map((node) => (
          <SidebarItem
            key={node.key}
            node={node}
            collapsed={collapsed}
          />
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700">
        <button
          onClick={logout}
          className={`w-full flex items-center p-3 rounded-lg text-red-400 hover:bg-red-900 hover:text-red-200 transition-colors ${
            collapsed ? 'justify-center' : ''
          }`}
          title={collapsed ? 'تسجيل الخروج' : undefined}
          type="button"
        >
          <i className={`fas fa-sign-out-alt ${collapsed ? '' : 'ml-3'}`}></i>
          {!collapsed && <span className="font-medium">تسجيل الخروج</span>}
        </button>
      </div>
    </aside>
  );
}
