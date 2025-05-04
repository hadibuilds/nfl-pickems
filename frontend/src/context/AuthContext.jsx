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
    const csrf = getCookie('csrftoken');
    if (!csrf) {
      setIsLoading(false);
      return;
    }

    fetch('http://localhost:8000/accounts/api/whoami/', {
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
      await fetch('http://localhost:8000/accounts/api/logout/', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
      });
    } catch (err) {
      console.error('Logout failed:', err);
    } finally {
      setUserInfo(null);
    }
  };

  return (
    <AuthContext.Provider value={{ userInfo, setUserInfo, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
