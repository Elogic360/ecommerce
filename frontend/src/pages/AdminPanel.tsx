import React, { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Package,
  ShoppingCart,
  BarChart3,
  Settings,
  Menu,
  LogOut
} from 'lucide-react';
import { useStore } from '@/app/store';

const AdminPanel: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth >= 1024); // Open by default on desktop
  const location = useLocation();
  const { user, logout } = useStore();

  const navigation = [
    { name: 'Dashboard', href: '/admin/dashboard', icon: LayoutDashboard },
    { name: 'Users', href: '/admin/users', icon: Users },
    { name: 'Products', href: '/admin/products', icon: Package },
    { name: 'Orders', href: '/admin/orders', icon: ShoppingCart },
    { name: 'Inventory', href: '/admin/inventory', icon: BarChart3 },
    { name: 'Analytics', href: '/admin/analytics', icon: BarChart3 },
  ];

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="fixed inset-0 bg-black bg-opacity-50" onClick={() => setSidebarOpen(false)} />
        </div>
      )}

      {/* Full-width Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="flex items-center justify-between px-6 py-4">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden text-gray-500 hover:text-gray-700 transition"
            aria-label="Open sidebar menu"
          >
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex-1 lg:flex items-center justify-between">
            <div className="hidden lg:block">
              <h1 className="text-2xl font-bold text-gray-900">
                {navigation.find(nav => nav.href === location.pathname)?.name || 'Dashboard'}
              </h1>
              <p className="text-sm text-gray-500 mt-1">Manage your store efficiently</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="relative">
                <input
                  type="search"
                  placeholder="Search..."
                  className="hidden lg:block w-64 pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                />
                <Settings className="hidden lg:block absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
              </div>
              <div className="flex items-center space-x-2">
                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center shadow-lg lg:hidden">
                  <span className="text-sm font-bold text-white">
                    {user?.username?.charAt(0).toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content area with sidebar below header */}
      <div className="flex flex-col lg:flex-row min-h-[calc(100vh-73px)]">
        {/* Sidebar */}
        <div className={`w-full lg:w-64 bg-gradient-to-b from-slate-900 via-gray-900 to-slate-900 shadow-2xl transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'} transition-all duration-300 ease-in-out flex flex-col border-r border-slate-700/50`}>
          {/* Header */}
          <div className="flex items-center justify-center h-20 px-6 border-b border-slate-700/50 flex-shrink-0 bg-slate-900/80 backdrop-blur-sm">
            <div className="flex items-center space-x-3">
              <div className="relative">
                <div className="w-11 h-11 bg-gradient-to-br from-orange-500 via-red-500 to-pink-600 rounded-xl flex items-center justify-center shadow-lg shadow-orange-500/25">
                  <span className="text-white font-bold text-xl">S</span>
                </div>
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-slate-900 animate-pulse"></div>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight">Neatify</h1>
                <p className="text-xs text-slate-400 font-medium">Admin Panel</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="mt-8 px-4 flex-1">
            <div className="space-y-2">
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`group flex items-center px-4 py-3.5 text-sm font-medium rounded-xl transition-all duration-200 relative overflow-hidden ${
                      isActive
                        ? 'bg-gradient-to-r from-orange-500 to-red-600 text-white shadow-lg shadow-orange-500/30 transform scale-[1.02]'
                        : 'text-slate-300 hover:bg-slate-800/60 hover:text-white hover:shadow-md hover:transform hover:translate-x-1'
                    }`}
                    onClick={() => setSidebarOpen(false)}
                  >
                    {isActive && (
                      <div className="absolute inset-0 bg-gradient-to-r from-orange-500/20 to-red-600/20 animate-pulse"></div>
                    )}
                    <Icon className={`mr-4 h-5 w-5 transition-transform duration-200 ${
                      isActive ? 'scale-110' : 'group-hover:scale-110'
                    }`} />
                    <span className="font-semibold">{item.name}</span>
                    {isActive && (
                      <div className="absolute right-3 w-2 h-2 bg-white rounded-full animate-pulse"></div>
                    )}
                  </Link>
                );
              })}
            </div>

            {/* Divider */}
            <div className="mt-8 mb-6 border-t border-slate-700/50"></div>

            {/* Quick Stats */}
            <div className="bg-slate-800/40 rounded-xl p-4 border border-slate-700/30">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Quick Stats</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-300">Online</span>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                    <span className="text-xs text-green-400 font-medium">Active</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-300">Version</span>
                  <span className="text-xs text-slate-400 font-mono">v2.1.0</span>
                </div>
              </div>
            </div>
          </nav>

          {/* User info and logout */}
          <div className="p-4 border-t border-slate-700/50 bg-slate-900/60 backdrop-blur-sm flex-shrink-0">
            <div className="flex items-center mb-4 p-3 rounded-xl bg-slate-800/40 border border-slate-700/30">
              <div className="flex-shrink-0">
                <div className="h-10 w-10 rounded-full bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center shadow-lg shadow-orange-500/25">
                  <span className="text-sm font-bold text-white">
                    {user?.username?.charAt(0).toUpperCase()}
                  </span>
                </div>
              </div>
              <div className="ml-3 flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">{user?.username}</p>
                <p className="text-xs text-slate-400 truncate">{user?.email}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center w-full px-4 py-3 text-sm text-slate-300 hover:bg-red-600/80 hover:text-white rounded-xl transition-all duration-200 font-medium shadow-lg hover:shadow-red-500/25 hover:transform hover:scale-[1.02]"
            >
              <LogOut className="mr-3 h-4 w-4" />
              Logout
            </button>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 bg-gray-50">
          <div className="py-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <Outlet />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;
