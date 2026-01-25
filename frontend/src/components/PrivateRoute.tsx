import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useStore } from '@/app/store';
import { ShieldAlert, Loader2 } from 'lucide-react';

interface PrivateRouteProps {
  children: React.ReactElement;
  requiredRole?: string;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children, requiredRole }) => {
  const { token, user } = useStore();
  const location = useLocation();
  const [isHydrating, setIsHydrating] = useState(true);

  useEffect(() => {
    // Check if hydration is needed
    // If token is missing in store but exists in localStorage, we are likely hydrating
    const storedToken = localStorage.getItem('token');
    if (storedToken && !token) {
      // Allow a brief moment for store to update
      const timer = setTimeout(() => {
        setIsHydrating(false);
      }, 500); // 500ms timeout for hydration
      return () => clearTimeout(timer);
    } else {
      setIsHydrating(false);
    }
  }, [token]);

  // If loading/hydrating, show spinner
  if (isHydrating && localStorage.getItem('token') && !token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
      </div>
    );
  }

  // If not authenticated (and validly so), redirect to login
  if (!token || !user) {
    // Double check localStorage to avoid false positives during rapid reloads
    if (localStorage.getItem('token')) {
      // If token exists in storage but not in state after timeout, 
      // it might be invalid/stale, but let's show loader just in case 
      // rather than redirecting immediately to avoid loops.
      // However, if we reached here, isHydrating is false.
      // So we assume it's a broken state -> redirect (login will fix it or clear it).
      // Actually, let's trust the store state now.
    }
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If role requirement is not met
  if (requiredRole && user.role !== requiredRole) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
        <div className="bg-white p-8 rounded-2xl shadow-xl text-center max-w-md w-full border border-gray-100">
          <div className="bg-red-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6">
            <ShieldAlert className="text-red-500 w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
          <p className="text-gray-600 mb-6">
            You don't have permission to access the admin area. Please sign in with an administrator account.
          </p>
          <button
            onClick={() => {
              useStore.getState().logout();
            }}
            className="w-full bg-gray-900 text-white py-3 rounded-xl font-semibold hover:bg-gray-800 transition"
          >
            Sign in as Admin
          </button>
          <a href="/" className="block mt-4 text-sm text-gray-500 hover:text-gray-900">
            Return to Homepage
          </a>
        </div>
      </div>
    );
  }

  return children;
};

export default PrivateRoute;
