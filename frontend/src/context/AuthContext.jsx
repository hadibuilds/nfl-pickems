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

  const prefetchCSRF = async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/accounts/api/csrf/`, {
        method: 'GET',
        credentials: 'include',
      });
      console.log("✅ Prefetched CSRF:", res.status);
    } catch (err) {
      console.error("❌ Failed to fetch CSRF token:", err);
    }
  };

  const checkWhoAmI = async () => {
    const csrf = getCookie("csrftoken");
    if (!csrf) {
      console.warn("⚠️ Missing CSRF token before /whoami call");
      return;
    }

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/accounts/api/whoami/`, {
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
      await prefetchCSRF(); // always fetch CSRF on first load

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
        console.warn("⚠️ No CSRF token present before whoami call.");
        setIsLoading(false);
        return;
      }

      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL}/accounts/api/whoami/`, {
          credentials: 'include',
          headers: { 'X-CSRFToken': csrf },
        });

        if (res.ok) {
          const data = await res.json();
          setUserInfo(data?.username ? data : null);
        } else {
          setUserInfo(null);
        }
      } catch {
        setUserInfo(null);
      } finally {
        setIsLoading(false);
      }
    };

    init();
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

      console.log("✅ Logged out. Flushing session...");

      // Wait briefly to let session flush
      await new Promise(res => setTimeout(res, 100));

      // Trigger a fresh anonymous session and CSRF
      await prefetchCSRF();

      // Reload into fresh state
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
