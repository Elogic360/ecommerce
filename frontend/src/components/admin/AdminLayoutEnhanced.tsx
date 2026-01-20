/**
 * AdminLayout - Enhanced admin layout with collapsible sidebar
 */
import React, { useState, useEffect } from 'react';
import { Link, NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import clsx from 'clsx';
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  Users,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  ChevronLeft,
  Bell,
  Search,
  User,
  Boxes,
  Tags,
} from 'lucide-react';
import { useStore } from '@/app/store';
import { useAdminStore } from '@/stores/adminStore';
import Toast from './Toast';
import ConfirmDialog from './ConfirmDialog';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  exact?: boolean;
  badge?: number;
}

const navItems: NavItem[] = [
  { path: '/admin', label: 'Dashboard', icon: <LayoutDashboard className="h-5 w-5" />, exact: true },
  { path: '/admin/products', label: 'Products', icon: <Package className="h-5 w-5" /> },
  { path: '/admin/orders', label: 'Orders', icon: <ShoppingCart className="h-5 w-5" /> },
  { path: '/admin/users', label: 'Users', icon: <Users className="h-5 w-5" /> },
  { path: '/admin/inventory', label: 'Inventory', icon: <Boxes className="h-5 w-5" /> },
  { path: '/admin/categories', label: 'Categories', icon: <Tags className="h-5 w-5" /> },
  { path: '/admin/analytics', label: 'Analytics', icon: <BarChart3 className="h-5 w-5" /> },
];

const bottomNavItems: NavItem[] = [
  { path: '/admin/settings', label: 'Settings', icon: <Settings className="h-5 w-5" /> },
];

export default function AdminLayoutEnhanced() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useStore();
  const { ui, toggleSidebar, toggleSidebarCollapse, showConfirmDialog, hideConfirmDialog, hideToast } = useAdminStore();

  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Check if user is admin
  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/login');
    }
  }, [user, navigate]);

  // Close mobile sidebar on route change
  useEffect(() => {
    if (window.innerWidth < 1024) {
      useAdminStore.getState().setSidebarOpen(false);
    }
  }, [location.pathname]);

  const handleLogout = () => {
    showConfirmDialog({
      title: 'Logout',
      message: 'Are you sure you want to log out?',
      confirmLabel: 'Logout',
      cancelLabel: 'Cancel',
      variant: 'warning',
      onConfirm: () => {
        hideConfirmDialog();
        logout();
        navigate('/login');
      },
      onCancel: hideConfirmDialog,
    });
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // Global search functionality
      console.log('Search:', searchQuery);
      setSearchOpen(false);
      setSearchQuery('');
    }
  };

  // Get current page title
  const getCurrentPageTitle = () => {
    const item = [...navItems, ...bottomNavItems].find(
      (item) => item.exact ? location.pathname === item.path : location.pathname.startsWith(item.path)
    );
    return item?.label || 'Admin';
  };

  if (!user || user.role !== 'admin') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900">
        <div className="text-slate-400">Checking authentication...</div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-slate-900">
      {/* Sidebar Backdrop (mobile) */}
      {ui.sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-slate-800 bg-slate-900 transition-all duration-300 lg:relative',
          ui.sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
          ui.sidebarCollapsed ? 'lg:w-20' : 'lg:w-64',
          'w-64'
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b border-slate-800 px-4">
          {!ui.sidebarCollapsed && (
            <Link to="/admin" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500">
                <Package className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-bold text-white">Neatify</span>
            </Link>
          )}
          <button
            onClick={toggleSidebarCollapse}
            className="hidden rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white lg:block"
            aria-label="Collapse sidebar"
          >
            <ChevronLeft className={clsx('h-5 w-5 transition', ui.sidebarCollapsed && 'rotate-180')} />
          </button>
          <button
            onClick={toggleSidebar}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-4">
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  end={item.exact}
                  className={({ isActive }) =>
                    clsx(
                      'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
                      isActive
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                    )
                  }
                  title={ui.sidebarCollapsed ? item.label : undefined}
                >
                  {item.icon}
                  {!ui.sidebarCollapsed && (
                    <>
                      <span>{item.label}</span>
                      {item.badge !== undefined && item.badge > 0 && (
                        <span className="ml-auto rounded-full bg-emerald-500 px-2 py-0.5 text-xs text-white">
                          {item.badge}
                        </span>
                      )}
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Bottom nav */}
        <div className="border-t border-slate-800 p-4">
          <ul className="space-y-1">
            {bottomNavItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    clsx(
                      'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
                      isActive
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                    )
                  }
                  title={ui.sidebarCollapsed ? item.label : undefined}
                >
                  {item.icon}
                  {!ui.sidebarCollapsed && <span>{item.label}</span>}
                </NavLink>
              </li>
            ))}
            <li>
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-400 transition hover:bg-red-500/10 hover:text-red-400"
                title={ui.sidebarCollapsed ? 'Logout' : undefined}
              >
                <LogOut className="h-5 w-5" />
                {!ui.sidebarCollapsed && <span>Logout</span>}
              </button>
            </li>
          </ul>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-800 bg-slate-900/95 px-4 backdrop-blur-sm lg:px-6">
          <div className="flex items-center gap-4">
            <button
              onClick={toggleSidebar}
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
              aria-label="Open sidebar"
            >
              <Menu className="h-5 w-5" />
            </button>
            <h1 className="text-lg font-semibold text-white">{getCurrentPageTitle()}</h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Search */}
            {searchOpen ? (
              <form onSubmit={handleSearch} className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search..."
                  autoFocus
                  className="w-64 rounded-xl border border-slate-600 bg-slate-800 py-2 pl-10 pr-4 text-sm text-white placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <button
                  type="button"
                  onClick={() => {
                    setSearchOpen(false);
                    setSearchQuery('');
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                  aria-label="Close search"
                >
                  <X className="h-4 w-4" />
                </button>
              </form>
            ) : (
              <button
                onClick={() => setSearchOpen(true)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
                aria-label="Search"
              >
                <Search className="h-5 w-5" />
              </button>
            )}

            {/* Notifications */}
            <button
              className="relative rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5" />
              <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-red-500" />
            </button>

            {/* User menu */}
            <div className="flex items-center gap-3 border-l border-slate-700 pl-3">
              <div className="hidden text-right sm:block">
                <p className="text-sm font-medium text-white">{user.full_name || user.username}</p>
                <p className="text-xs text-slate-400">{user.role}</p>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500/20">
                <User className="h-5 w-5 text-emerald-400" />
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>

      {/* Toast */}
      <Toast
        open={ui.toast.open}
        message={ui.toast.message}
        type={ui.toast.type}
        onClose={hideToast}
      />

      {/* Confirm Dialog */}
      <ConfirmDialog
        open={ui.confirmDialog.open}
        title={ui.confirmDialog.title}
        message={ui.confirmDialog.message}
        confirmLabel={ui.confirmDialog.confirmLabel}
        cancelLabel={ui.confirmDialog.cancelLabel}
        variant={ui.confirmDialog.variant}
        onConfirm={ui.confirmDialog.onConfirm || (() => {})}
        onClose={ui.confirmDialog.onCancel || hideConfirmDialog}
      />
    </div>
  );
}
