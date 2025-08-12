import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { useAuth } from "../context/AuthContext";
import { getCookie } from "../utils/cookies";

export default function LoginPage() {
  const { setUserInfo } = useAuth();
  const navigate = useNavigate();
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
        const res = await fetch(`${API_BASE}/accounts/api/csrf/`, {
          credentials: "include",
        });
        console.log("✅ CSRF prefetched on login:", res.status);
      } catch (err) {
        console.error("❌ Failed to prefetch CSRF on login:", err);
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

    try {
      const res = await fetch(`${API_BASE}/accounts/api/login/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          identifier: formData.identifier,
          password: formData.password,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        setUserInfo(data);
        navigate("/");
      } else {
        alert(data.detail || "Login failed");
      }
    } catch (err) {
      alert("Network error. Please try again.");
      console.error("Login error:", err);
    }
  };

  return (
    <div className="w-full flex items-start justify-center px-6 pt-20 pb-12" style={{ backgroundColor: '#1E1E20' }}>
      <div className="w-full max-w-md sm:max-w-lg md:max-w-xl lg:max-w-[40rem] p-8 sm:p-10 rounded-xl shadow-md text-base" style={{ backgroundColor: '#2d2d2d' }}>
        <div className="text-center mb-6">
          <h2 className="text-4xl font-bold text-white">
            Log In
          </h2>
          <p className="mt-2 text-base" style={{ color: '#9ca3af' }}>
            Access your Pick 'Em League
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
              className="w-full px-4 py-3 rounded-md focus:ring-2 focus:ring-violet-500 outline-none text-base text-white"
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
                className="w-full px-4 py-3 pr-10 rounded-md focus:ring-2 focus:ring-violet-500 outline-none text-base text-white"
                style={{ 
                  backgroundColor: '#1f1f1f',
                  border: '1px solid #4b5563'
                }}
              />
              <div
                onClick={toggleVisibility}
                className="absolute inset-y-0 right-3 flex items-center cursor-pointer hover:text-gray-300"
                style={{ color: '#9ca3af' }}
              >
                {isVisible ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <label htmlFor="remember" className="flex items-center text-sm" style={{ color: '#9ca3af' }}>
              <input
                id="remember"
                name="remember"
                type="checkbox"
                checked={formData.remember}
                onChange={handleChange}
                className="mr-2"
              />
              Remember me
            </label>
            <a
              href={`${API_BASE}/accounts/api/password-reset/`}
              className="text-sm hover:underline ml-4"
              style={{ color: '#8B5CF6' }}
            >
              Forgot password?
            </a>
          </div>

          <button
            type="submit"
            className="w-full font-semibold py-3 rounded-md text-base text-white hover:bg-violet-700 transition"
            style={{ backgroundColor: '#8B5CF6' }}
          >
            Log In
          </button>
        </form>

        <p className="text-center text-sm mt-4" style={{ color: '#9ca3af' }}>
          Don't have an account?{" "}
          <Link to="/signup" className="hover:underline" style={{ color: '#8B5CF6' }}>
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}