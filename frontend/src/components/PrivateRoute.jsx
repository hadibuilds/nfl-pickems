import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function PrivateRoute({ children }) {
  const { userInfo, isLoading } = useAuth();

  if (isLoading) return null; // or a loading spinner

  if (!userInfo) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
