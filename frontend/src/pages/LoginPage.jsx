/*
 * Enhanced Login Page Component
 * Prevents double-click with disabled button during login
 * Uses enhanced AuthContext for additional protection
 */

import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { useAuthWithNavigation } from "../hooks/useAuthWithNavigation";
import { getCookie } from "../utils/cookies";

export default function LoginPage() {
  const { loginAndRedirect, isLoggingIn } = useAuthWithNavigation(); // ← Use isLoggingIn from context
  const [isVisible, setIsVisible] = useState(false);
  const [formData, setFormData] = useState({
    identifier: "",
    password: "",
    remember: false,
  });

  const API_BASE = import.meta.env.VITE_API_URL;

  useEffect(() => {
    const fetchCSRF = async () => {
      try {
        await fetch(`${API_BASE}/accounts/api/csrf/`, {
          credentials: "include",
        });
      } catch (err) {
        console.error("Failed to prefetch CSRF on login:", err);
      }
    };

    fetchCSRF();
    localStorage.removeItem("justLoggedOut");
  }, []);

  const toggleVisibility = () => setIsVisible(!isVisible);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // ✅ PROTECTION: Don't submit if already logging in
    if (isLoggingIn) {
      return;
    }

    try {
      // Use the combined auth + navigation function
      const result = await loginAndRedirect({
        identifier: formData.identifier,
        password: formData.password,
      }, '/'); // Redirect to home page on success

      // Only show error if login failed (success is handled automatically)
      if (!result.success) {
        alert(result.error);
      }
    } catch (err) {
      alert("Network error. Please try again.");
      console.error("Login error:", err);
    }
  };

  return (
    <div
      className="w-full min-h-screen flex items-start justify-center px-6 pb-12 auth-page-padding"
      style={{ backgroundColor: '#05060A' }}
    >
      <div className="w-full max-w-md sm:max-w-lg md:max-w-xl lg:max-w-[40rem] p-8 sm:p-10 rounded-xl shadow-md text-base" style={{ backgroundColor: '#101118' }}>
        <div className="text-center mb-6">
          <h2 className="text-4xl font-bold text-white">
            Log In
          </h2>
          <p className="mt-2 text-base" style={{ color: '#9ca3af' }}>
            Access Pickems.fun
          </p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="identifier" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Username or Email
            </label>
            <input
              id="identifier"
              name="identifier"
              type="text"
              required
              value={formData.identifier}
              onChange={handleChange}
              disabled={isLoggingIn} // ✅ Disable input during login
              autocomplete="username"
              className={`w-full px-4 py-3 rounded-md focus:ring-2 focus:ring-violet-500 outline-none text-base text-white transition ${
                isLoggingIn ? 'opacity-50 cursor-not-allowed' : ''
              }`}
              style={{ 
                backgroundColor: '#1f1f1f',
                border: '1px solid #4b5563'
              }}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                name="password"
                type={isVisible ? "text" : "password"}
                required
                value={formData.password}
                onChange={handleChange}
                disabled={isLoggingIn} // Disable input during login
                autocomplete="current-password"
                className={`w-full px-4 py-3 pr-10 rounded-md focus:ring-2 focus:ring-violet-500 outline-none text-base text-white transition ${
                  isLoggingIn ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                style={{ 
                  backgroundColor: '#1f1f1f',
                  border: '1px solid #4b5563'
                }}
              />
              <div
                onClick={isLoggingIn ? undefined : toggleVisibility} // Disable eye toggle during login
                className={`absolute inset-y-0 right-3 flex items-center ${
                  isLoggingIn ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:text-gray-300'
                }`}
                style={{ color: '#9ca3af' }}
              >
                {isVisible ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <label htmlFor="remember" className={`flex items-center text-sm ${isLoggingIn ? 'opacity-50' : ''}`} style={{ color: '#9ca3af' }}>
              <input
                id="remember"
                name="remember"
                type="checkbox"
                checked={formData.remember}
                onChange={handleChange}
                disabled={isLoggingIn} // Disable checkbox during login
                className="mr-2"
              />
              Remember me
            </label>
            <Link
              to="/password-reset"
              className={`text-sm hover:underline ml-4 ${isLoggingIn ? 'opacity-50 cursor-not-allowed' : ''}`}
              style={{ color: '#8B5CF6' }}
              onClick={isLoggingIn ? (e) => e.preventDefault() : undefined}
            >
              Forgot password?
            </Link>
          </div>

          <button
            type="submit"
            disabled={isLoggingIn} // Disable button during login
            className={`w-full font-semibold py-3 rounded-md text-base text-white transition ${
              isLoggingIn 
                ? 'opacity-50 cursor-not-allowed bg-violet-500' 
                : 'hover:bg-violet-700 bg-violet-600'
            }`}
            style={{ backgroundColor: isLoggingIn ? '#8B5CF6' : '#8B5CF6' }}
          >
            {isLoggingIn ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Logging in...
              </span>
            ) : (
              'Log In'
            )}
          </button>
        </form>

        <p className={`text-center text-sm mt-4 ${isLoggingIn ? 'opacity-50' : ''}`} style={{ color: '#9ca3af' }}>
          Don't have an account?{" "}
          <Link 
            to="/signup" 
            className={`hover:underline ${isLoggingIn ? 'cursor-not-allowed' : ''}`} 
            style={{ color: '#8B5CF6' }}
            onClick={isLoggingIn ? (e) => e.preventDefault() : undefined} // Disable signup link during login
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}