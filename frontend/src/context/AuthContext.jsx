import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [userInfo, setUserInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const getCookie = (name) => {
    const value = document.cookie
      .split('; ')
      .find(row => row.startsWith(name + '='));
    return value ? decodeURIComponent(value.split('=')[1]) : null;
  };

  useEffect(() => {
    if (localStorage.getItem("justLoggedOut")) {
      console.log("⏸️ Skipping whoami check due to logout");
      localStorage.removeItem("justLoggedOut");
      setIsLoading(false);
      return;
    }

    const shouldRunAuthCheck =
      !window.location.pathname.startsWith('/login') &&
      !window.location.pathname.startsWith('/signup');

    if (!shouldRunAuthCheck) {
      setIsLoading(false);
      return;
    }

    const csrf = getCookie('csrftoken');
    if (!csrf) {
      setIsLoading(false);
      return;
    }

    fetch(`${import.meta.env.VITE_API_URL}/accounts/api/whoami/`, {
      credentials: 'include',
      headers: { 'X-CSRFToken': csrf },
    })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        setUserInfo(data?.username ? data : null);
        setIsLoading(false);
      })
      .catch(() => {
        setUserInfo(null);
        setIsLoading(false);
      });
  }, []);

  const logout = async () => {
    try {
      console.log("🚪 Logging out...");

      await fetch(`${import.meta.env.VITE_API_URL}/accounts/api/logout/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
      });

      // 💤 Allow time for session to reset before CSRF fetch
      await new Promise(res => setTimeout(res, 100));

      const csrfRes = await fetch(`${import.meta.env.VITE_API_URL}/accounts/api/csrf/`, {
        credentials: 'include',
      });

      const freshCsrf = getCookie('csrftoken');
      console.log("✅ Fetched fresh CSRF after logout:", freshCsrf);

      localStorage.setItem("justLoggedOut", "true");
      setUserInfo(null);
      window.location.href = "/login";
    } catch (err) {
      console.error("❌ Logout error:", err);
    }
  };

  return (
    <AuthContext.Provider value={{ userInfo, setUserInfo, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
