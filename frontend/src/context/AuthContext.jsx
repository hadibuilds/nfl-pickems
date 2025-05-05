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

    // Clear session-related cookies
    document.cookie = "csrftoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    document.cookie = "sessionid=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";

    // 🔥 Immediately fetch new CSRF token from backend
    await fetch(`${import.meta.env.VITE_API_URL}/accounts/api/csrf/`, {
      credentials: "include",
    });

    // Prevent whoami from running on login page
    localStorage.setItem("justLoggedOut", "true");

    setUserInfo(null);
    window.location.href = "/login";
  } catch (err) {
    console.error("Logout failed:", err);
  }
};
