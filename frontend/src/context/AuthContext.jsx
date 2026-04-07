import { createContext, useContext, useState, useEffect } from "react";
import { getCurrentUser } from "../services/api";
import { toast } from "react-hot-toast";

const AuthContext = createContext({
  user: null,
  login: () => {},
  logout: () => {},
  loading: true,
  refreshUser: () => {},
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      const token = localStorage.getItem("token");
      if (token) {
        try {
          const freshUser = await getCurrentUser();
          if (freshUser) {
            setUser(freshUser); // ✅ Don't normalize - use backend data as-is
            localStorage.setItem("user", JSON.stringify(freshUser));
          } else {
            logout();
          }
        } catch (error) {
          console.error("Failed to load user:", error);
          logout();
        }
      }
      setLoading(false);
    };
    init();
  }, []);

  const login = async (credentials, token) => {
    try {
      localStorage.setItem("token", token);
      await refreshUser();
      return true;
    } catch (error) {
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const freshUser = await getCurrentUser();
      if (freshUser) {
        setUser(freshUser);
        localStorage.setItem("user", JSON.stringify(freshUser));
      } else {
        logout();
      }
    } catch (error) {
      console.error("Failed to refresh user:", error);
      logout();
      throw error;
    }
  };

  // ✅ ADD: Role checking utilities
  const hasRole = (requiredRoles) => {
    if (!user) return false;
    if (Array.isArray(requiredRoles)) {
      return requiredRoles.includes(user.role);
    }
    return user.role === requiredRoles;
  };

  const isAuthenticated = () => {
    return !!user && !!localStorage.getItem("token");
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      login, 
      logout, 
      loading, 
      refreshUser,
      hasRole,
      isAuthenticated
    }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
