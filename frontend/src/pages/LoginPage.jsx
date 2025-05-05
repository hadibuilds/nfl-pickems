import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { useAuth } from "../context/AuthContext";

const getCookie = (name) => {
  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith(name + "="));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : null;
};

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

  // CSRF token prefetch
  useEffect(() => {
    fetch(`${API_BASE}/accounts/api/csrf/`, {
      credentials: "include",
    });
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
    <div className="w-full flex items-start justify-center bg-white dark:bg-[#1E1E20] px-6 pt-20 pb-12">
      <div className="w-full max-w-md sm:max-w-lg md:max-w-xl lg:max-w-[40rem] bg-white dark:bg-[#2d2d2d] p-8 sm:p-10 rounded-xl shadow-md text-base">
        <div className="text-center mb-6">
          <h2 className="text-4xl font-bold text-gray-800 dark:text-white">
            Log In <span role="img" aria-label="wave">👋</span>
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mt-2 text-base">
            Access your Pick 'Em League
          </p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="identifier" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Username or Email
            </label>
            <input
              id="identifier"
              name="identifier"
              type="text"
              required
              value={formData.identifier}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 outline-none dark:bg-[#2d2d2d] dark:text-white text-base"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
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
                className="w-full px-4 py-3 pr-10 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 outline-none dark:bg-[#2d2d2d] dark:text-white text-base"
              />
              <div
                onClick={toggleVisibility}
                className="absolute inset-y-0 right-3 flex items-center cursor-pointer text-gray-500 hover:text-gray-300"
              >
                {isVisible ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <label htmlFor="remember" className="flex items-center text-sm text-gray-600 dark:text-gray-400">
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
              className="text-sm text-blue-600 hover:underline ml-4"
            >
              Forgot password?
            </a>
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-md text-base"
          >
            Log In
          </button>
        </form>

        <p className="text-center text-sm text-gray-600 mt-4 dark:text-gray-300">
          Don’t have an account?{" "}
          <Link to="/signup" className="text-blue-600 hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
