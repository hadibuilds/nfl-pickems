import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { useAuth } from "../context/AuthContext";

const getCookie = (name) => {
  const cookie = document.cookie
    .split("; ")
    .find(row => row.startsWith(name + "="));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : null;
};

export default function SignUpPage() {
  const { setUserInfo } = useAuth();
  const navigate = useNavigate();

  const [isVisible, setIsVisible] = useState(false);
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    inviteCode: "",
  });

  const API_BASE = import.meta.env.VITE_API_URL;

  useEffect(() => {
    fetch(`${API_BASE}/accounts/api/csrf/`, {
      credentials: "include",
    });
  }, []);

  const toggleVisibility = () => setIsVisible(!isVisible);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // Ensure fresh CSRF token before POST
      await fetch(`${API_BASE}/accounts/api/csrf/`, {
        credentials: "include",
      });

      const res = await fetch(`${API_BASE}/accounts/api/register/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify(formData),
      });

      const data = await res.json();
      if (res.ok) {
        setUserInfo(data); // Log in after signup
        navigate("/");
      } else {
        alert(data.detail || "Signup failed.");
        console.error("Signup error:", data);
      }
    } catch (err) {
      console.error("Network error:", err);
    }
  };

  return (
    <div className="w-full flex items-start justify-center px-6 pt-20 pb-12" style={{ backgroundColor: '#1E1E20' }}>
      <div className="w-full max-w-md sm:max-w-lg md:max-w-xl lg:max-w-[40rem] p-8 sm:p-10 rounded-xl shadow-md text-base" style={{ backgroundColor: '#2d2d2d' }}>
        <div className="text-center mb-6">
          <h2 className="text-4xl font-bold text-white">
            Sign Up
          </h2>
          <p className="mt-2 text-base" style={{ color: '#9ca3af' }}>
            Join the Pick 'Em League
          </p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="username" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Username
            </label>
            <input
              id="username"
              name="username"
              type="text"
              required
              value={formData.username}
              onChange={handleChange}
              className="w-full px-4 py-3 rounded-md focus:ring-2 focus:ring-violet-500 outline-none text-base text-white"
              style={{ 
                backgroundColor: '#1f1f1f',
                border: '1px solid #4b5563'
              }}
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              value={formData.email}
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

          <div>
            <label htmlFor="inviteCode" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Invite Code
            </label>
            <input
              id="inviteCode"
              name="inviteCode"
              type="text"
              required
              value={formData.inviteCode}
              onChange={handleChange}
              className="w-full px-4 py-3 rounded-md focus:ring-2 focus:ring-violet-500 outline-none text-base text-white"
              style={{ 
                backgroundColor: '#1f1f1f',
                border: '1px solid #4b5563'
              }}
            />
          </div>

          <button
            type="submit"
            className="w-full font-semibold py-3 rounded-md text-base text-white hover:bg-violet-700 transition"
            style={{ backgroundColor: '#8B5CF6' }}
          >
            Sign Up
          </button>
        </form>

        <p className="text-center text-sm mt-4" style={{ color: '#9ca3af' }}>
          Already have an account?{" "}
          <Link to="/login" className="hover:underline" style={{ color: '#8B5CF6' }}>
            Log In
          </Link>
        </p>
      </div>
    </div>
  );
}