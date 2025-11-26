import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { useAuthWithNavigation } from "../hooks/useAuthWithNavigation";
import { getCookie } from "../utils/cookies";

export default function SignUpPage() {
  const { setUserInfo, navigate } = useAuthWithNavigation();

  const [isVisible, setIsVisible] = useState(false);
  const [isConfirmVisible, setIsConfirmVisible] = useState(false);
  const [isSigningUp, setIsSigningUp] = useState(false); // ✅ prevent double submit + drive UI
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    inviteCode: "",
  });
  const [error, setError] = useState("");

  const API_BASE = import.meta.env.VITE_API_URL;

  useEffect(() => {
    fetch(`${API_BASE}/accounts/api/csrf/`, { credentials: "include" });
  }, []);

  const toggleVisibility = () => !isSigningUp && setIsVisible(!isVisible);
  const toggleConfirmVisibility = () => !isSigningUp && setIsConfirmVisible(!isConfirmVisible);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (error) setError("");
  };

  const validateForm = () => {
    if (!formData.firstName.trim()) {
      setError("First name is required");
      return false;
    }
    if (!formData.username.trim()) {
      setError("Username is required");
      return false;
    }
    if (!formData.email.trim()) {
      setError("Email is required");
      return false;
    }
    if (formData.password.length < 5) {
      setError("Password must be at least 5 characters long");
      return false;
    }
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return false;
    }
    if (!formData.inviteCode.trim()) {
      setError("Invite code is required");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isSigningUp) return; // ✅ guard: ignore double submit
    setError("");

    if (!validateForm()) return;

    try {
      setIsSigningUp(true); // ✅ lock UI

      // Ensure fresh CSRF token before POST
      await fetch(`${API_BASE}/accounts/api/csrf/`, { credentials: "include" });

      const res = await fetch(`${API_BASE}/accounts/api/register/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          first_name: formData.firstName,
          last_name: formData.lastName,
          username: formData.username,
          email: formData.email,
          password: formData.password,
          inviteCode: formData.inviteCode,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setUserInfo(data); // Log in after signup
        navigate("/");
      } else {
        setError(data.detail || "Signup failed.");
        console.error("Signup error:", data);
      }
    } catch (err) {
      console.error("Network error:", err);
      setError("Network error. Please try again.");
    } finally {
      setIsSigningUp(false); // ✅ release UI on completion/error
    }
  };

  return (
    <div className="w-full min-h-screen flex items-start justify-center px-6 pb-12" style={{ backgroundColor: '#05060A', paddingTop: 'calc(env(safe-area-inset-top, 0px) + 1.5rem)' }}>
      <div className="w-full max-w-md sm:max-w-lg md:max-w-xl lg:max-w-[40rem] p-8 sm:p-10 rounded-xl shadow-md text-base" style={{ backgroundColor: '#101118' }}>
        <div className="text-center mb-6">
          <h2 className="text-4xl font-bold text-white">Sign Up</h2>
          <p className="mt-2 text-base" style={{ color: '#9ca3af' }}>
            Join the Pickems.fun community!
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-md" style={{ backgroundColor: '#7f1d1d', border: '1px solid #dc2626' }}>
            <p className="text-sm" style={{ color: '#fca5a5' }}>{error}</p>
          </div>
        )}

        <form className="space-y-5" onSubmit={handleSubmit}>
          {/* First Name - Required */}
          <div>
            <label htmlFor="firstName" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              First Name *
            </label>
            <input
              id="firstName"
              name="firstName"
              type="text"
              required
              disabled={isSigningUp} // ✅ disable while pending
              value={formData.firstName}
              onChange={handleChange}
              className={`w-full px-4 py-3 rounded-md focus:ring-2 outline-none text-base text-white ${
                isSigningUp ? 'opacity-50 cursor-not-allowed' : 'focus:ring-violet-500'
              }`}
              style={{ backgroundColor: '#1f1f1f', border: '1px solid #4b5563' }}
            />
          </div>

          {/* Last Name - Optional */}
          <div>
            <label htmlFor="lastName" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Last Name
            </label>
            <input
              id="lastName"
              name="lastName"
              type="text"
              disabled={isSigningUp}
              value={formData.lastName}
              onChange={handleChange}
              className={`w-full px-4 py-3 rounded-md focus:ring-2 outline-none text-base text-white ${
                isSigningUp ? 'opacity-50 cursor-not-allowed' : 'focus:ring-violet-500'
              }`}
              style={{ backgroundColor: '#1f1f1f', border: '1px solid #4b5563' }}
            />
          </div>

          {/* Username */}
          <div>
            <label htmlFor="username" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Username *
            </label>
            <input
              id="username"
              name="username"
              type="text"
              required
              disabled={isSigningUp}
              value={formData.username}
              onChange={handleChange}
              autocomplete="username"
              className={`w-full px-4 py-3 rounded-md focus:ring-2 outline-none text-base text-white ${
                isSigningUp ? 'opacity-50 cursor-not-allowed' : 'focus:ring-violet-500'
              }`}
              style={{ backgroundColor: '#1f1f1f', border: '1px solid #4b5563' }}
            />
          </div>

          {/* Email */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Email *
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              disabled={isSigningUp}
              value={formData.email}
              onChange={handleChange}
              className={`w-full px-4 py-3 rounded-md focus:ring-2 outline-none text-base text-white ${
                isSigningUp ? 'opacity-50 cursor-not-allowed' : 'focus:ring-violet-500'
              }`}
              style={{ backgroundColor: '#1f1f1f', border: '1px solid #4b5563' }}
            />
          </div>

          {/* Password */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Password *
            </label>
            <div className="relative">
              <input
                id="password"
                name="password"
                type={isVisible ? "text" : "password"}
                required
                disabled={isSigningUp}
                value={formData.password}
                onChange={handleChange}
                autocomplete="new-password"
                className={`w-full px-4 py-3 pr-10 rounded-md focus:ring-2 outline-none text-base text-white ${
                  isSigningUp ? 'opacity-50 cursor-not-allowed' : 'focus:ring-violet-500'
                }`}
                style={{ backgroundColor: '#1f1f1f', border: '1px solid #4b5563' }}
              />
              <div
                onClick={toggleVisibility}
                className={`absolute inset-y-0 right-3 flex items-center ${
                  isSigningUp ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:text-gray-300'
                }`}
                style={{ color: '#9ca3af' }}
              >
                {isVisible ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
              </div>
            </div>
          </div>

          {/* Confirm Password */}
          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Confirm Password *
            </label>
            <div className="relative">
              <input
                id="confirmPassword"
                name="confirmPassword"
                type={isConfirmVisible ? "text" : "password"}
                required
                disabled={isSigningUp}
                value={formData.confirmPassword}
                onChange={handleChange}
                autocomplete="new-password"
                className={`w-full px-4 py-3 pr-10 rounded-md focus:ring-2 outline-none text-base text-white ${
                  formData.confirmPassword && formData.password !== formData.confirmPassword
                    ? 'focus:ring-red-500 border-red-500'
                    : 'focus:ring-violet-500'
                } ${isSigningUp ? 'opacity-50 cursor-not-allowed' : ''}`}
                style={{
                  backgroundColor: '#1f1f1f',
                  border:
                    formData.confirmPassword && formData.password !== formData.confirmPassword
                      ? '1px solid #dc2626'
                      : '1px solid #4b5563',
                }}
              />
              <div
                onClick={toggleConfirmVisibility}
                className={`absolute inset-y-0 right-3 flex items-center ${
                  isSigningUp ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:text-gray-300'
                }`}
                style={{ color: '#9ca3af' }}
              >
                {isConfirmVisible ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
              </div>
            </div>
            {formData.confirmPassword && formData.password !== formData.confirmPassword && (
              <p className="text-xs mt-1" style={{ color: '#fca5a5' }}>
                Passwords do not match
              </p>
            )}
          </div>

          {/* Invite Code */}
          <div>
            <label htmlFor="inviteCode" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Invite Code *
            </label>
            <input
              id="inviteCode"
              name="inviteCode"
              type="text"
              required
              disabled={isSigningUp}
              value={formData.inviteCode}
              onChange={handleChange}
              className={`w-full px-4 py-3 rounded-md focus:ring-2 outline-none text-base text-white ${
                isSigningUp ? 'opacity-50 cursor-not-allowed' : 'focus:ring-violet-500'
              }`}
              style={{ backgroundColor: '#1f1f1f', border: '1px solid #4b5563' }}
            />
          </div>

          <button
            type="submit"
            disabled={isSigningUp} // ✅ main protection
            className={`w-full font-semibold py-3 rounded-md text-base text-white transition ${
              isSigningUp ? 'opacity-50 cursor-not-allowed bg-violet-500' : 'hover:bg-violet-700 bg-violet-600'
            }`}
            style={{ backgroundColor: '#8B5CF6' }}
          >
            {isSigningUp ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" viewBox="0 0 24 24" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8"></path>
                </svg>
                Creating account…
              </span>
            ) : (
              'Sign Up'
            )}
          </button>
        </form>

        <p className={`text-center text-sm mt-4 ${isSigningUp ? 'opacity-50' : ''}`} style={{ color: '#9ca3af' }}>
          Already have an account?{" "}
          <Link
            to="/login"
            className={`hover:underline ${isSigningUp ? 'cursor-not-allowed' : ''}`}
            style={{ color: '#8B5CF6' }}
            onClick={isSigningUp ? (e) => e.preventDefault() : undefined} // ✅ avoid navigation during submit
          >
            Log In
          </Link>
        </p>
      </div>
    </div>
  );
}
