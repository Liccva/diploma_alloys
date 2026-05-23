import React, { createContext, useState, useContext, useEffect } from "react";
import { authService } from "../services/api";

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const checkAuth = async () => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      setLoading(false);
      setIsAuthenticated(false);
      setUser(null);
      setRole(null);
      return;
    }

    try {
      const userData = await authService.getCurrentUser();

      // Если аккаунт деактивирован — немедленно выходим
      if (userData.is_active === false) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        setUser(null);
        setRole(null);
        setIsAuthenticated(false);
        setLoading(false);
        return;
      }

      setUser(userData);
      setRole(userData.role_name || userData.role || null);
      setIsAuthenticated(true);
    } catch (error) {
      console.error("Auth check failed:", error);
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      setUser(null);
      setRole(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const login = async (loginValue, password) => {
    setLoading(true);
    try {
      const result = await authService.login(loginValue, password);

      // При успехе всегда должен быть success: true
      if (result.success) {
        setUser(result.user);
        setRole(result.user?.role_name || result.user?.role || null);
        setIsAuthenticated(true);
        localStorage.setItem("user", JSON.stringify(result.user));
        return true;
      } else {
        // Этот код не должен выполняться при новой логике,
        // но оставим для совместимости
        throw new Error(result.error || "Ошибка входа");
      }
    } catch (error) {
      console.error("Login error:", error);
      // Пробрасываем ошибку дальше
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await authService.logout();
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setUser(null);
      setRole(null);
      setIsAuthenticated(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const value = {
    user,
    role,
    loading,
    isAuthenticated,
    isAdmin: role === "admin",
    isResearcher: role === "researcher",
    login,
    logout,
    checkAuth,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default useAuth;