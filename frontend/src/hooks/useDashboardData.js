// hooks/useDashboardData.js
import { useState, useEffect } from 'react';

const useDashboardData = (userInfo) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const getCsrfToken = () => {
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='));
    return cookieValue ? decodeURIComponent(cookieValue.split('=')[1]) : null;
  };

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/predictions/api/dashboard/', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setDashboardData(data);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!userInfo?.username) return;
    fetchDashboardData();
  }, [userInfo?.username]);

  return { dashboardData, loading, error, refetch: fetchDashboardData };
};

export default useDashboardData;