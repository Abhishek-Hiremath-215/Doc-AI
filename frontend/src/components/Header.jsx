// components/Header.jsx
import React from 'react';
import { Brain, X, Menu, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';

function Header({ setShowSidebar, showSidebar, user }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    toast.success('✅ Logged out successfully');
    navigate('/login');
  };

  return (
    <header className="bg-white shadow p-4 flex items-center justify-between">
      {/* === Branding === */}
      <div className="flex items-center space-x-2">
        <Brain className="text-blue-600 w-6 h-6" />
        <h1 className="text-lg font-bold tracking-tight">AI Assistant</h1>
      </div>

      {/* === Actions === */}
      <div className="flex items-center space-x-4">
        {user && (
          <span className="text-sm text-gray-600 truncate max-w-xs hidden sm:inline">
            {user.email} ({user.role})
          </span>
        )}

        {/* Sidebar toggle */}
        <button
          onClick={() => setShowSidebar(!showSidebar)}
          aria-label={showSidebar ? "Close sidebar" : "Open sidebar"}
          className="text-gray-500 hover:text-black transition"
        >
          {showSidebar ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        {/* Logout */}
        <button
          onClick={handleLogout}
          aria-label="Logout"
          className="text-gray-500 hover:text-red-600 flex items-center transition"
        >
          <LogOut className="w-5 h-5 mr-1" />
          <span className="text-sm hidden sm:inline">Logout</span>
        </button>
      </div>
    </header>
  );
}

export default Header;
