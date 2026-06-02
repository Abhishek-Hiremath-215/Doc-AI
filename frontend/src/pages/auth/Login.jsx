import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser, isDemoMode } from "../../services/api";
import { Eye, EyeOff, Crown, Shield, User, Sparkles } from "lucide-react";
import toast, { Toaster } from "react-hot-toast";
import { useAuth } from "../../context/AuthContext";
import { getDashboardRoute } from "../../utils/roleUtils"; // ✅ ADD: Import helper

function Login() {
  const navigate = useNavigate();
  const { login, loading: loadingAuth } = useAuth();

  const [form, setForm] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleQuickLogin = (email, password) => {
    setForm({ email, password });
    setLoading(true);
    loginUser({ email, password }).then(async ({ access_token }) => {
      if (!access_token) throw new Error("No token returned");
      await login(null, access_token);
      toast.success("🎉 Welcome to the Demo!");
      setTimeout(() => {
        const storedUser = JSON.parse(localStorage.getItem("user"));
        const dashboardRoute = getDashboardRoute(storedUser?.role);
        navigate(dashboardRoute, { replace: true });
      }, 100);
    }).catch(err => {
      const msg = err.response?.data?.detail || err.message || "Login failed";
      toast.error(`❌ ${msg}`);
    }).finally(() => {
      setLoading(false);
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!login) return toast.error("Auth context not ready.");

    setLoading(true);
    try {
      const { access_token } = await loginUser(form);
      if (!access_token) throw new Error("No token returned");
      
      await login(null, access_token);
      toast.success("🎉 Welcome back!");

      // ✅ FIXED: Get user from context after login
      // Wait a moment for user to be loaded in context
      setTimeout(() => {
        const storedUser = JSON.parse(localStorage.getItem("user"));
        const dashboardRoute = getDashboardRoute(storedUser?.role);
        navigate(dashboardRoute, { replace: true });
      }, 100);
      
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Login failed";
      toast.error(`❌ ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  if (loadingAuth) return <p className="text-center mt-20">Loading...</p>;

  return (
    <>
      <Toaster position="top-center" />
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-white rounded-lg shadow p-6">
          <h1 className="text-2xl font-bold text-center mb-6">Welcome Back</h1>
          <form onSubmit={handleSubmit} className="space-y-4">
            <input 
              type="email" 
              name="email" 
              value={form.email} 
              onChange={handleChange} 
              placeholder="Email" 
              required 
              disabled={loading} 
              className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 disabled:opacity-60" 
            />
            <div className="relative">
              <input 
                type={showPassword ? "text" : "password"} 
                name="password" 
                value={form.password} 
                onChange={handleChange} 
                placeholder="Password" 
                required 
                disabled={loading} 
                className="w-full border rounded px-3 py-2 pr-10 focus:ring-2 focus:ring-blue-500 disabled:opacity-60" 
              />
              <button 
                type="button" 
                onClick={() => setShowPassword(!showPassword)} 
                className="absolute right-3 top-2.5"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <button 
              type="submit" 
              disabled={loading || !form.email || !form.password} 
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded disabled:opacity-60"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
          <p className="text-center mt-4 text-gray-600">
            Don&apos;t have an account?{" "}
            <button 
              onClick={() => navigate("/register")} 
              className="text-blue-600 hover:underline" 
              disabled={loading}
            >
              Create account
            </button>
          </p>
          
          {isDemoMode() && (
            <div className="mt-6 border-t border-slate-200 pt-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-3 flex items-center justify-center gap-1">
                <Sparkles className="w-4 h-4 text-emerald-500" />
                Demo Mode Quick Login Accounts
              </h2>
              <div className="grid grid-cols-1 gap-2">
                <button
                  type="button"
                  onClick={() => handleQuickLogin("superadmin@docai.com", "admin123")}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:border-emerald-500 bg-slate-50 hover:bg-emerald-50/20 text-left transition-all duration-200 cursor-pointer"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 bg-red-100 rounded-lg text-red-600">
                      <Crown className="w-4.5 h-4.5" />
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-slate-800">Super Admin</div>
                      <div className="text-[10px] text-slate-500">Full system control, manage organizations</div>
                    </div>
                  </div>
                  <span className="text-[10px] font-medium text-emerald-600 bg-emerald-100 px-1.5 py-0.5 rounded">Quick Login</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin("orgadmin@docai.com", "org123")}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:border-emerald-500 bg-slate-50 hover:bg-emerald-50/20 text-left transition-all duration-200 cursor-pointer"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 bg-blue-100 rounded-lg text-blue-600">
                      <Shield className="w-4.5 h-4.5" />
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-slate-800">Organization Admin</div>
                      <div className="text-[10px] text-slate-500">Manage org users, compliance & documents</div>
                    </div>
                  </div>
                  <span className="text-[10px] font-medium text-emerald-600 bg-emerald-100 px-1.5 py-0.5 rounded">Quick Login</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin("user@docai.com", "user123")}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:border-emerald-500 bg-slate-50 hover:bg-emerald-50/20 text-left transition-all duration-200 cursor-pointer"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 bg-slate-200 rounded-lg text-slate-600">
                      <User className="w-4.5 h-4.5" />
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-slate-800">Regular User</div>
                      <div className="text-[10px] text-slate-500">Upload guidelines, chat with documents</div>
                    </div>
                  </div>
                  <span className="text-[10px] font-medium text-emerald-600 bg-emerald-100 px-1.5 py-0.5 rounded">Quick Login</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default Login;
