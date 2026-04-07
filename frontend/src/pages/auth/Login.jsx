import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser } from "../../services/api";
import { Eye, EyeOff } from "lucide-react";
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
        </div>
      </div>
    </>
  );
}

export default Login;
