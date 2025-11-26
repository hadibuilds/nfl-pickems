import React, { useState } from "react";
import { Link } from "react-router-dom";

export default function PasswordResetPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const getCookie = (name) => {
    const cookie = document.cookie
      .split('; ')
      .find(row => row.startsWith(name + '='));
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (isSubmitting) return;
    
    setIsSubmitting(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(`${API_BASE}/accounts/api/password-reset/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        credentials: 'include',
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });

      if (response.ok) {
        setMessage("If an account with that email exists, we've sent you a password reset link.");
        setEmail("");
      } else {
        const data = await response.json();
        setError(data.detail || "Failed to send reset email. Please try again.");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full min-h-screen flex items-start justify-center px-6 pb-12" style={{ backgroundColor: '#05060A', paddingTop: 'calc(env(safe-area-inset-top, 0px) + 1.5rem)' }}>
      <div className="w-full max-w-md sm:max-w-lg md:max-w-xl lg:max-w-[40rem] p-8 sm:p-10 rounded-xl shadow-md text-base" style={{ backgroundColor: '#101118' }}>
        <div className="text-center mb-6">
          <h2 className="text-4xl font-bold text-white">Reset Password</h2>
          <p className="mt-2 text-base" style={{ color: '#9ca3af' }}>
            Enter your account email and we'll send you a reset link.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-md" style={{ backgroundColor: '#7f1d1d', border: '1px solid #dc2626' }}>
            <p className="text-sm" style={{ color: '#fca5a5' }}>{error}</p>
          </div>
        )}

        {message && (
          <div className="mb-4 p-3 rounded-md" style={{ backgroundColor: '#065f46', border: '1px solid #059669' }}>
            <p className="text-sm" style={{ color: '#a7f3d0' }}>{message}</p>
          </div>
        )}

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Email address
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isSubmitting}
              autoComplete="email"
              className={`w-full px-4 py-3 rounded-md focus:ring-2 focus:ring-violet-500 outline-none text-base text-white transition ${
                isSubmitting ? 'opacity-50 cursor-not-allowed' : ''
              }`}
              style={{ backgroundColor: '#1f1f1f', border: '1px solid #4b5563' }}
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className={`w-full font-semibold py-3 rounded-md text-base text-white transition ${
              isSubmitting 
                ? 'opacity-50 cursor-not-allowed' 
                : 'hover:bg-violet-700'
            }`}
            style={{ backgroundColor: '#8B5CF6' }}
          >
            {isSubmitting ? (
              <span className="inline-flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" viewBox="0 0 24 24" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8"></path>
                </svg>
                Sending…
              </span>
            ) : (
              'Send Reset Link'
            )}
          </button>
        </form>

        <p className={`text-center text-sm mt-4 ${isSubmitting ? 'opacity-50' : ''}`} style={{ color: '#9ca3af' }}>
          Remember your password?{" "}
          <Link 
            to="/login" 
            className={`hover:underline ${isSubmitting ? 'cursor-not-allowed' : ''}`} 
            style={{ color: '#8B5CF6' }}
            onClick={isSubmitting ? (e) => e.preventDefault() : undefined}
          >
            Back to Login
          </Link>
        </p>
      </div>
    </div>
  );
}