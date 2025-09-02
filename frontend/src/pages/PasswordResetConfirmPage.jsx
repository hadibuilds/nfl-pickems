import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";

export default function PasswordResetConfirmPage() {
  const { uidb64, token } = useParams();
  const navigate = useNavigate();
  const [passwords, setPasswords] = useState({
    new_password1: "",
    new_password2: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isValidating, setIsValidating] = useState(true);
  const [isValidLink, setIsValidLink] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const getCookie = (name) => {
    const cookie = document.cookie
      .split('; ')
      .find(row => row.startsWith(name + '='));
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : null;
  };

  useEffect(() => {
    const validateToken = async () => {
      try {
        const response = await fetch(`${API_BASE}/accounts/api/password-reset-validate/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
          },
          credentials: 'include',
          body: JSON.stringify({ uid: uidb64, token: token }),
        });

        if (response.ok) {
          setIsValidLink(true);
        } else {
          setIsValidLink(false);
        }
      } catch (err) {
        setIsValidLink(false);
      } finally {
        setIsValidating(false);
      }
    };

    validateToken();
  }, [uidb64, token, API_BASE]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setPasswords(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (isSubmitting) return;
    
    if (passwords.new_password1 !== passwords.new_password2) {
      setError("Passwords don't match.");
      return;
    }
    
    setIsSubmitting(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/accounts/api/password-reset-confirm/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        credentials: 'include',
        body: JSON.stringify({
          uid: uidb64,
          token: token,
          new_password1: passwords.new_password1,
          new_password2: passwords.new_password2,
        }),
      });

      if (response.ok) {
        setMessage("Password updated successfully! Redirecting to login...");
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } else {
        const data = await response.json();
        setError(data.detail || "Failed to update password. Please try again.");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isValidating) {
    return (
      <div className="w-full flex items-start justify-center px-6 pt-20 pb-12" style={{ backgroundColor: '#1E1E20' }}>
        <div className="w-full max-w-md sm:max-w-lg md:max-w-xl lg:max-w-[40rem] p-8 sm:p-10 rounded-xl shadow-md text-base" style={{ backgroundColor: '#2d2d2d' }}>
          <div className="text-center">
            <div className="inline-flex items-center justify-center">
              <svg className="animate-spin h-8 w-8 text-violet-500" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8"></path>
              </svg>
            </div>
            <p className="mt-4 text-white">Validating reset link...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!isValidLink) {
    return (
      <div className="w-full flex items-start justify-center px-6 pt-20 pb-12" style={{ backgroundColor: '#1E1E20' }}>
        <div className="w-full max-w-md sm:max-w-lg md:max-w-xl lg:max-w-[40rem] p-8 sm:p-10 rounded-xl shadow-md text-base" style={{ backgroundColor: '#2d2d2d' }}>
          <div className="text-center mb-6">
            <h2 className="text-4xl font-bold text-white mb-4">Invalid Reset Link</h2>
          </div>
          
          <div className="mb-6 p-3 rounded-md text-center" style={{ backgroundColor: '#7f1d1d', border: '1px solid #dc2626' }}>
            <p className="text-sm" style={{ color: '#fca5a5' }}>This reset link is invalid or has expired.</p>
          </div>
          
          <div className="text-center">
            <Link 
              to="/password-reset" 
              className="inline-block px-5 py-3 rounded-md text-white font-semibold hover:bg-violet-700 transition"
              style={{ backgroundColor: '#8B5CF6' }}
            >
              Request a new link
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full flex items-start justify-center px-6 pt-20 pb-12" style={{ backgroundColor: '#1E1E20' }}>
      <div className="w-full max-w-md sm:max-w-lg md:max-w-xl lg:max-w-[40rem] p-8 sm:p-10 rounded-xl shadow-md text-base" style={{ backgroundColor: '#2d2d2d' }}>
        <div className="text-center mb-6">
          <h2 className="text-4xl font-bold text-white mb-4">Set a New Password</h2>
          <p className="mt-2 text-base" style={{ color: '#9ca3af' }}>
            Please enter and confirm your new password below.
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
            <label htmlFor="new_password1" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              New Password
            </label>
            <input
              type="password"
              name="new_password1"
              id="new_password1"
              value={passwords.new_password1}
              onChange={handleChange}
              disabled={isSubmitting}
              required
              autoComplete="new-password"
              className={`w-full px-4 py-3 rounded-md focus:ring-2 focus:ring-violet-500 outline-none text-base text-white transition ${
                isSubmitting ? 'opacity-50 cursor-not-allowed' : ''
              }`}
              style={{ backgroundColor: '#1f1f1f', border: '1px solid #4b5563' }}
            />
          </div>

          <div>
            <label htmlFor="new_password2" className="block text-sm font-medium mb-1" style={{ color: '#d1d5db' }}>
              Confirm New Password
            </label>
            <input
              type="password"
              name="new_password2"
              id="new_password2"
              value={passwords.new_password2}
              onChange={handleChange}
              disabled={isSubmitting}
              required
              autoComplete="new-password"
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
                Updating…
              </span>
            ) : (
              'Update Password'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}