import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import blackLogo from "../assets/pickem2_black.png";
import whiteLogo from "../assets/pickem2_white.png";

export default function Navbar({ userInfo, onLogout, isOpen, setIsOpen }) {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await onLogout();
    navigate("/login");
    setIsOpen(false);
  };

  return (
    <nav className="fixed top-0 left-0 w-full z-50 bg-white/70 dark:bg-[#1E1E20]/70 backdrop-blur-lg shadow-sm transition-colors duration-300 h-[64px] sm:h-[72px]">
      <div className="flex items-center justify-between px-3 py-2 max-w-7xl mx-auto h-full">
        <Link to="/">
          <img
            src={blackLogo}
            alt="Pick Em Logo-Black"
            className="h-28 sm:h-28 object-contain dark:hidden"
          />
          <img
            src={whiteLogo}
            alt="Pick Em Logo-White"
            className="h-28 sm:h-28 object-contain hidden dark:inline"
          />
        </Link>

        {/* Pill-style Auth Buttons for Unauthenticated Users */}
        {!userInfo && location.pathname === "/signup" && (
          <Link
            to="/login"
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-2xl bg-gray-100 dark:bg-[#2d2d2d] text-gray-800 dark:text-white font-medium text-sm hover:bg-gray-200 dark:hover:bg-[#3a3a3a] transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
            </svg>
            <span>Login</span>
          </Link>
        )}

        {!userInfo && location.pathname === "/login" && (
          <Link
            to="/signup"
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-2xl bg-violet-100 text-violet-700 font-medium text-sm hover:bg-violet-200 transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Sign Up</span>
          </Link>
        )}

        {/* Desktop Links */}
        {userInfo && (
          <div className="hidden md:flex items-center space-x-10">
            <Link to="/" className="text-gray-700 dark:text-gray-200 hover:text-[#5F5F5F]">Home</Link>
            <Link to="/standings" className="text-gray-700 dark:text-gray-200 hover:text-[#5F5F5F]">Standings</Link>
            <button
              onClick={handleLogout}
              className="text-gray-700 dark:text-gray-200 hover:text-red-500 bg-transparent border-none outline-none px-0 py-0 leading-none"
            >
              Logout
            </button>
          </div>
        )}

        {/* Hamburger menu for mobile — only for logged-in users */}
        {userInfo && (
          <div className="md:hidden">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="relative z-50 flex flex-col justify-center items-center bg-transparent border-none outline-none p-2 focus:outline-none focus:ring-0"
            >
              <span className={`h-0.5 w-6 bg-gray-700 dark:bg-white transition-all duration-300 ease-in-out ${isOpen ? "rotate-45 translate-y-1.5" : "-translate-y-1.5"}`} />
              <span className={`h-0.5 w-6 my-0.5 bg-gray-700 dark:bg-white transition-all duration-300 ease-in-out ${isOpen ? "opacity-0" : "opacity-100"}`} />
              <span className={`h-0.5 w-6 bg-gray-700 dark:bg-white transition-all duration-300 ease-in-out ${isOpen ? "-rotate-45 -translate-y-1.5" : "translate-y-1.5"}`} />
            </button>
          </div>
        )}
      </div>

      {/* Push Sidebar */}
      <div className={`fixed top-0 right-0 h-full w-64 z-40 transition-transform duration-300 transform bg-white dark:bg-[#1E1E20] md:hidden ${isOpen ? "translate-x-0" : "translate-x-full"}`}>
        <div className="flex flex-col items-center justify-start pt-20 space-y-6">
          {userInfo && (
            <Link to="/" onClick={() => setIsOpen(false)} className="text-xl text-gray-700 dark:text-gray-200 hover:text-[#5F5F5F]">Home</Link>
          )}
          {userInfo && (
            <Link to="/standings" onClick={() => setIsOpen(false)} className="text-xl text-gray-700 dark:text-gray-200 hover:text-[#5F5F5F]">Standings</Link>
          )}
          {!userInfo && location.pathname !== "/login" && (
            <Link to="/login" onClick={() => setIsOpen(false)} className="text-xl text-gray-700 dark:text-gray-200 hover:text-[#5F5F5F]">Login</Link>
          )}
          {!userInfo && location.pathname !== "/signup" && (
            <Link to="/signup" onClick={() => setIsOpen(false)} className="text-xl text-gray-700 dark:text-gray-200 hover:text-[#5F5F5F]">Sign Up</Link>
          )}
          {userInfo && (
            <button onClick={handleLogout} className="text-xl text-gray-700 dark:text-gray-200 hover:text-red-500 bg-transparent border-none outline-none">Logout</button>
          )}
        </div>
      </div>
    </nav>
  );
}
