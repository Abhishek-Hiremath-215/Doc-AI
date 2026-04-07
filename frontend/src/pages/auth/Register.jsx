import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import toast, { Toaster } from "react-hot-toast";
import { registerUser } from "../../services/api";
import { useAuth } from "../../context/AuthContext";

const Register = () => {
  const [email, setEmail] = useState("");
  const [organizationId, setOrganizationId] = useState(""); // optional
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const navigate = useNavigate();
  const { login } = useAuth();

  const validatePassword = (pass) => pass.length >= 8;

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validatePassword(password)) {
      toast.error("Password must be at least 8 characters long");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      // ✅ backend returns user + token
      const { user, token } = await registerUser({
        email,
        password,
        organization_id: organizationId || null,
      });

      login(user, token); // auto-login
      toast.success("🎉 Account created successfully!");
      setTimeout(() => navigate("/home"), 1000);
    } catch (err) {
      const errorMessage =
        err.response?.data?.detail || "Registration failed. Try again.";
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Toaster position="top-center" />
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-white rounded-lg shadow p-6">
          <h1 className="text-2xl font-bold text-center mb-6">
            Create Account
          </h1>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
              disabled={loading}
              className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
            />

            {/* Org ID (optional, later dropdown) */}
            <input
              type="text"
              value={organizationId}
              onChange={(e) => setOrganizationId(e.target.value)}
              placeholder="Organization ID (optional)"
              disabled={loading}
              className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
            />

            {/* Password */}
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
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
                {showPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
            {password && (
              <p
                className={`text-xs ${
                  validatePassword(password)
                    ? "text-green-600"
                    : "text-red-500"
                }`}
              >
                {validatePassword(password)
                  ? "✓ Strong password"
                  : "✗ At least 8 characters required"}
              </p>
            )}

            {/* Confirm Password */}
            <div className="relative">
              <input
                type={showConfirmPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm Password"
                required
                disabled={loading}
                className="w-full border rounded px-3 py-2 pr-10 focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-2.5"
              >
                {showConfirmPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
            {confirmPassword && (
              <p
                className={`text-xs ${
                  password === confirmPassword
                    ? "text-green-600"
                    : "text-red-500"
                }`}
              >
                {password === confirmPassword
                  ? "✓ Passwords match"
                  : "✗ Passwords do not match"}
              </p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={
                loading || !email || !password || !confirmPassword || password !== confirmPassword
              }
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded disabled:opacity-60"
            >
              {loading ? "Creating Account..." : "Create Account"}
            </button>
          </form>

          <p className="text-center mt-4 text-gray-600">
            Already have an account?{" "}
            <button
              onClick={() => navigate("/login")}
              className="text-blue-600 hover:underline"
              disabled={loading}
            >
              Sign in
            </button>
          </p>
        </div>
      </div>
    </>
  );
};

export default Register;
