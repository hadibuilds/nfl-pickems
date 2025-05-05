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
    // Prevent whoami from triggering after logout redirect
    if (localStorage.getItem("justLoggedOut")) {
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
      await fetch(`${import.meta.env.VITE_API_URL}/accounts/api/logout/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
      });

      // Mark logout to prevent whoami
      localStorage.setItem("justLoggedOut", "true");

      // Manually clear the cookies
      document.cookie = "csrftoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
      document.cookie = "sessionid=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";

      setUserInfo(null);

      // Delay before redirect
      setTimeout(() => {
        window.location.href = "/login";
      }, 300);

    } catch (err) {
      console.error("Logout failed:", err);
    }
  };

  return (
    <AuthContext.Provider value={{ userInfo, setUserInfo, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
