import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import LoadingSpinner from "../common/LoadingSpinner";

const ProtectedRoute = ({ children, requiredRole }) => {
  const { isAuthenticated, role, loading } = useAuth();

  // Пока идёт восстановление сессии/логин — не редиректим
  if (loading) {
    return <LoadingSpinner />;
  }

  // Если не авторизован — на логин
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Если нужна роль и она не совпала — на главную (или можно на /dashboard)
  if (requiredRole && role !== requiredRole) {
    return <Navigate to="/" replace />;
  }

  return children;
};

export default ProtectedRoute;
