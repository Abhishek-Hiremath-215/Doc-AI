import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ProtectedRoute from "./routes/ProtectedRoute";
import { Toaster } from "react-hot-toast";

// Auth
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";

// User
import HomePage from "./pages/user/HomePage";

// Admin
import AdminDashboard from "./pages/admin/AdminDashboard";
import ManageOrganizations from "./pages/admin/ManageOrganizations";
import OrgDashboard from "./pages/admin/OrgDashboard";

// Super Admin
import SuperAdminDashboard from "./pages/super-admin/SuperAdminDashboard";

// Shared
import Profile from "./pages/shared/Profile";

function RoleBasedRedirect() {
  const { user } = useAuth();
  
  if (!user) return <Navigate to="/login" replace />;

  // ✅ FIXED: Match your backend role names
  switch (user.role) {
    case "superadmin":
      return <Navigate to="/super-admin/dashboard" replace />;
    case "orgadmin":
      return <Navigate to="/org/dashboard" replace />;
    case "user":
      return <Navigate to="/home" replace />;
    default:
      console.warn(`Unknown user role: ${user.role}`);
      return <Navigate to="/login" replace />;
  }
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* ✅ Root redirect */}
          <Route path="/" element={<RoleBasedRedirect />} />

          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* User Routes */}
          <Route
            path="/home"
            element={
              <ProtectedRoute allowedRoles={["user", "orgadmin", "superadmin"]}>
                <HomePage />
              </ProtectedRoute>
            }
          />

          {/* Organization Admin Routes */}
          <Route
            path="/org/dashboard"
            element={
              <ProtectedRoute allowedRoles={["orgadmin", "superadmin"]}>
                <OrgDashboard />
              </ProtectedRoute>
            }
          />

          {/* ✅ FIXED: Remove admin routes since you only have user, orgadmin, superadmin */}

          {/* Super Admin Routes */}
          <Route
            path="/super-admin/dashboard"
            element={
              <ProtectedRoute allowedRoles={["superadmin"]}>
                <SuperAdminDashboard />
              </ProtectedRoute>
            }
          />

          {/* Shared Routes */}
          <Route
            path="/profile"
            element={
              <ProtectedRoute allowedRoles={["user", "orgadmin", "superadmin"]}>
                <Profile />
              </ProtectedRoute>
            }
          />

          {/* Unauthorized Route */}
          <Route
            path="/unauthorized"
            element={
              <div className="flex items-center justify-center h-screen">
                <div className="text-center">
                  <h1 className="text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
                  <p className="text-gray-600 mb-4">You don't have permission to access this page.</p>
                  <button
                    onClick={() => window.history.back()}
                    className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                  >
                    Go Back
                  </button>
                </div>
              </div>
            }
          />

          {/* Catch-all - Role-based redirect */}
          <Route path="*" element={<RoleBasedRedirect />} />
        </Routes>
        <Toaster position="top-right" />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
