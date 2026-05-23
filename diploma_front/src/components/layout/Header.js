import React from "react";
import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import ThemeToggle from "../common/ThemeToggle";

const Header = () => {
  const { user, logout, isAuthenticated, role } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const isAuthPage = location.pathname === "/login" || location.pathname === "/register";

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="app-header">
      <div className="navbar">
        <Link to={isAuthenticated ? "/dashboard" : "/"} className="navbar-brand">
          Metal Alloys
        </Link>

        <nav className="navbar-menu">
          <ThemeToggle />

          {isAuthenticated ? (
            <>
              {!isAuthPage && (
                <>
                  {role !== "guest" && (
                    <NavLink to="/profile" className="nav-link">
                      Профиль
                    </NavLink>
                  )}
                </>
              )}

              <span className="nav-user">
                {user?.login || user?.firstName || user?.first_name || "Пользователь"}
              </span>
              <span className="nav-user">
                {role === "admin" ? "Администратор" : role === "researcher" ? "Исследователь" : role}
              </span>

              <button className="logout-btn" onClick={handleLogout}>
                Выйти
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="nav-link">
                Вход
              </NavLink>
              <NavLink to="/register" className="nav-link">
                Регистрация
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  );
};

export default Header;