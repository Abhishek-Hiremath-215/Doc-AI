// src/hooks/useAuthCheck.js
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// Note: This hook is currently not being used in your App.jsx routing logic.
// The App.jsx directly uses getUserRole() and Navigate components for protection.
// If you intend for this hook to provide global authentication checks,
// you would typically call it within a component that wraps your entire app
// or specific protected routes, or use it to manage a global auth state.

export const useAuthCheck = (requiredRole = null) => {
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login', { replace: true });
      return;
    }

    try {
      // Manual base64 decoding (jwt-decode library is more robust)
      // It's generally better to rely on jwt-decode for full token parsing
      // However, if jwt-decode is not available or you need a fallback:
      const base64 = token.split('.')[1];
      // Pad the base64 string if its length is not a multiple of 4
      const padded = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, '=');
      const decoded = atob(padded.replace(/-/g, '+').replace(/_/g, '/'));
      const payload = JSON.parse(decoded);

      // Expiration check
      const now = Math.floor(Date.now() / 1000);
      if (payload.exp && payload.exp < now) {
        console.warn('Token expired in useAuthCheck. Removing from localStorage.');
        localStorage.removeItem('token');
        navigate('/login', { replace: true });
        return;
      }

      // Role check
      const userRole = payload.role || payload.user_role; // Handle both 'role' and 'user_role'
      if (requiredRole && userRole !== requiredRole) {
        console.warn(`Unauthorized role in useAuthCheck: ${userRole}, required: ${requiredRole}. Redirecting.`);
        // Redirect to a default authenticated page for the user's actual role, or home
        navigate('/home', { replace: true });
      }

    } catch (err) {
      console.error('Invalid token format in useAuthCheck:', err);
      localStorage.removeItem('token');
      navigate('/login', { replace: true });
    }
  }, [navigate, requiredRole]); // Dependencies: re-run effect if navigate or requiredRole changes
};
