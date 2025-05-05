import { createContext, useContext, useState, useEffect } from 'react';
import { getCookie } from '../utils/cookies';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [userInfo, setUserInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const API_BASE = import.meta.env.VITE_API_URL;

  const prefetchCSRF = async () => {
    try {
      await fetch(`${API_BASE}/accounts/api/csrf/`, {
        method: 'GET',
        credentials: 'include',
      });
      console.log("✅ CSRF token prefetched");
    } catch (err) {
      console.error("❌ CSRF prefetch failed:", err);
    }
  };

  const checkWhoAmI = async () => {
    const csrf = getCookie("csrftoken");
    if (!csrf) {
      console.warn("⚠️ Missing CSRF token before /whoami call");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/accounts/api/whoami/`, {
        credentials: 'include',
        headers: { 'X-CSRFToken': csrf },
      });

      if (res.ok) {
        const data = await res.json();
        setUserInfo(data?.username ? data : null);
      } else {
        setUserInfo(null);
      }
    } catch (err) {
      console.error("❌ Failed to fetch whoami:", err);
      setUserInfo(null);
    }
  };

  useEffect(() => {
    const init = async () => {
      await prefetchCSRF();

      const isAuthPage =
        window.location.pathname.startsWith("/login") ||
        window.location.pathname.startsWith("/signup");

      if (!isAuthPage) await checkWhoAmI();

      setIsLoading(false);
    };

    init();
  }, []);

  const logout = async () => {
    try {
      await fetch(`${API_BASE}/accounts/api/logout/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
      });

      await new Promise(res => setTimeout(res, 100));
      await prefetchCSRF();

      setUserInfo(null);
      window.location.href = "/login";
    } catch (err) {
      console.error("❌ Logout failed:", err);
    }
  };

  return (
    <AuthContext.Provider value={{ userInfo, setUserInfo, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
