// src/App.js
import React, { useEffect, useMemo, useState } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useParams,
  useLocation,
  useNavigate,
  Link,
} from "react-router-dom";

import { AuthProvider, useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/auth/ProtectedRoute";

import { patentService, alloyService, predictionService } from "./services/api";
import LoadingSpinner from "./components/common/LoadingSpinner";

import Header from "./components/layout/Header";
import Sidebar from "./components/layout/Sidebar";
import Footer from "./components/layout/Footer";

import Home from "./pages/Home";
import Login from "./components/auth/Login";
import Register from "./components/auth/Register";
import Dashboard from "./pages/Dashboard";

import AlloysPage from "./pages/AlloysPage";
import AlloyNewPage from "./pages/AlloyNewPage";
import AlloyEditPage from "./pages/AlloyEditPage";
import AlloyDetailsPage from "./pages/AlloyDetailsPage";

import PatentsPage from "./pages/PatentsPage";
import PatentNewPage from "./pages/PatentNewPage";
import PatentEditPage from "./pages/PatentEditPage";
import PatentDetailsPage from "./pages/PatentDetailsPage";

import PredictionsPage from "./pages/PredictionsPage";
import PredictionNewPage from "./pages/PredictionNewPage";
import PredictionEditPage from "./pages/PredictionEditPage";
import PredictionDetailsPage from "./pages/PredictionDetailsPage";

import UsersListPage from "./pages/UsersListPage";
import UserDetailsPage from "./pages/UserDetailsPage";
import UserEditPage from "./pages/UserEditPage";

import ReportsPage from "./pages/ReportsPage";
import AdminPanel from "./pages/AdminPanel";

import "./styles/main.css";

// ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

const normalizeLogin = (s) => String(s || "").trim().toLowerCase();

const roleLower = (role) => String(role || "").trim().toLowerCase();
const isGuestRoleName = (role) => {
  const r = roleLower(role);
  return r === "guest" || r === "гость";
};

// ========== AuthWall (для неавторизованных) ==========
const AuthWall = ({ message }) => {
  return (
    <div className="info-message">
      <p>{message}</p>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 10 }}>
        <Link to="/login" className="btn btn-primary">Войти</Link>
        <Link to="/register" className="btn btn-outline">Регистрация</Link>
      </div>
    </div>
  );
};

// ========== RequireUser ==========
const RequireUser = ({ message, children }) => {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) return <LoadingSpinner />;
  if (!isAuthenticated || !user) return <AuthWall message={message} />;
  return children;
};

// ========== PublicAuthPage ==========
const PublicAuthPage = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) return <LoadingSpinner />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return children;
};

// ========== GuestGate (гость может видеть только ограниченные страницы) ==========
const GuestGate = ({ children }) => {
  const { user, role, isAuthenticated, loading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const currentRole = role ?? user?.role;
  const isGuest = isGuestRoleName(currentRole);

  useEffect(() => {
    if (!isGuest || !isAuthenticated) return;

    const publicPaths = ["/", "/login", "/register"];
    const alloyDetailPattern = /^\/alloys\/\d+\/?$/;
    const patentDetailPattern = /^\/patents\/\d+\/?$/;

    const isAllowed = publicPaths.includes(location.pathname) ||
      alloyDetailPattern.test(location.pathname) ||
      patentDetailPattern.test(location.pathname);

    if (!isAllowed) {
      navigate("/", { replace: true });
    }
  }, [isGuest, isAuthenticated, location.pathname, navigate]);

  if (loading) return <LoadingSpinner />;
  return children;
};

// ========== Guard: редактирование патента ==========
const PatentEditGuard = ({ children }) => {
  const { id } = useParams();
  const { user, role, isAuthenticated, loading } = useAuth();
  const [checking, setChecking] = useState(true);
  const [allowed, setAllowed] = useState(false);

  const isAdmin = role === "admin";
  const isResearcher = role === "researcher";
  const myLogin = normalizeLogin(user?.login);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        setChecking(true);

        if (isAdmin) {
          if (!cancelled) setAllowed(true);
          return;
        }

        if (!isResearcher) {
          if (!cancelled) setAllowed(false);
          return;
        }

        const authorsRes = await patentService.getAuthors(id);
        const authors = authorsRes.data || [];

        const isAuthor = authors.some(author =>
          author.person_id === user?.id ||
          normalizeLogin(author.author_name) === myLogin
        );

        if (!cancelled) setAllowed(isAuthor);
      } catch (error) {
        console.error("PatentEditGuard error:", error);
        if (!cancelled) setAllowed(false);
      } finally {
        if (!cancelled) setChecking(false);
      }
    };

    if (isAuthenticated && user) {
      run();
    } else {
      setChecking(false);
      setAllowed(false);
    }

    return () => { cancelled = true; };
  }, [id, isAdmin, isResearcher, myLogin, user?.id, isAuthenticated]);

  if (loading || checking) return <LoadingSpinner />;
  if (!allowed) return <Navigate to="/patents" replace />;
  return children;
};

// ========== Guard: редактирование сплава ==========
const AlloyEditGuard = ({ children }) => {
  const { id } = useParams();
  const { user, role, isAuthenticated, loading } = useAuth();
  const [checking, setChecking] = useState(true);
  const [allowed, setAllowed] = useState(false);

  const isAdmin = role === "admin";
  const isResearcher = role === "researcher";
  const myLogin = normalizeLogin(user?.login);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        setChecking(true);

        if (isAdmin) {
          if (!cancelled) setAllowed(true);
          return;
        }

        if (!isResearcher) {
          if (!cancelled) setAllowed(false);
          return;
        }

        const alloyRes = await alloyService.getById(id);
        const alloy = alloyRes.data;

        if (!alloy || !alloy.created_by_id) {
          if (!cancelled) setAllowed(false);
          return;
        }

        setAllowed(alloy.created_by_id === user?.id);
      } catch (error) {
        console.error("AlloyEditGuard error:", error);
        if (!cancelled) setAllowed(false);
      } finally {
        if (!cancelled) setChecking(false);
      }
    };

    if (isAuthenticated && user) {
      run();
    } else {
      setChecking(false);
      setAllowed(false);
    }

    return () => { cancelled = true; };
  }, [id, isAdmin, isResearcher, user?.id, isAuthenticated]);

  if (loading || checking) return <LoadingSpinner />;
  if (!allowed) return <Navigate to="/alloys" replace />;
  return children;
};

// ========== Guard: доступ к прогнозу ==========
const PredictionAccessGuard = ({ children }) => {
  const { id } = useParams();
  const { user, role, isAuthenticated, loading } = useAuth();
  const [checking, setChecking] = useState(true);
  const [allowed, setAllowed] = useState(false);

  const isAdmin = role === "admin";
  const isResearcher = role === "researcher";

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        setChecking(true);

        if (isAdmin) {
          if (!cancelled) setAllowed(true);
          return;
        }

        if (!isResearcher) {
          if (!cancelled) setAllowed(false);
          return;
        }

        const res = await predictionService.getById(id);
        const prediction = res.data;

        if (!prediction) {
          if (!cancelled) setAllowed(false);
          return;
        }

        setAllowed(prediction.person_id === user?.id);
      } catch (error) {
        console.error("PredictionAccessGuard error:", error);
        if (!cancelled) setAllowed(false);
      } finally {
        if (!cancelled) setChecking(false);
      }
    };

    if (isAuthenticated && user) {
      run();
    } else {
      setChecking(false);
      setAllowed(false);
    }

    return () => { cancelled = true; };
  }, [id, isAdmin, isResearcher, user?.id, isAuthenticated]);

  if (loading || checking) return <LoadingSpinner />;
  if (!allowed) return <Navigate to="/predictions" replace />;
  return children;
};

// ========== Not Found ==========
const NotFound = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/" replace />;

  return (
    <div className="not-found-page">
      <h2>404 - Страница не найдена</h2>
      <p>Запрошенная страница не существует.</p>
    </div>
  );
};

// ========== Редиректы для совместимости /profile → /users/{id} ==========
const ProfileRedirect = () => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={`/users/${user.id}`} replace />;
};

const ProfileEditRedirect = () => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={`/users/${user.id}/edit`} replace />;
};

// ========== Компонент Layout ==========
const AppLayout = ({ children }) => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  // Страницы где не нужен сайдбар
  const noSidebarPages = ["/login", "/register"];
  const showSidebar = isAuthenticated && !noSidebarPages.includes(location.pathname);

  return (
    <div className="app-container">
      <Header />
      <div className="main-content">
        {showSidebar && <Sidebar />}
        <div className={showSidebar ? "content-area" : "content-area-full"}>
          {children}
        </div>
      </div>
      <Footer />
    </div>
  );
};

// ========== APP ==========
function App() {
  return (
    <AuthProvider>
      <Router>
        <GuestGate>
          <AppLayout>
            <Routes>
              {/* Публичные маршруты */}
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<PublicAuthPage><Login /></PublicAuthPage>} />
              <Route path="/register" element={<PublicAuthPage><Register /></PublicAuthPage>} />

              {/* Сплавы (неавторизованные видят только детали) */}
              <Route path="/alloys" element={<AlloysPage />} />
              <Route path="/alloys/:id" element={<AlloyDetailsPage />} />

              {/* Патенты (неавторизованные видят только детали) */}
              <Route path="/patents" element={<PatentsPage />} />
              <Route path="/patents/:id" element={<PatentDetailsPage />} />

              {/* Защищенные маршруты */}
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/profile" element={<ProtectedRoute><ProfileRedirect /></ProtectedRoute>} />
              <Route path="/profile/edit" element={<ProtectedRoute><ProfileEditRedirect /></ProtectedRoute>} />

              {/* Alloys create/edit */}
              <Route path="/alloys/new" element={<ProtectedRoute><AlloyNewPage /></ProtectedRoute>} />
              <Route path="/alloys/edit/:id" element={<ProtectedRoute><AlloyEditGuard><AlloyEditPage /></AlloyEditGuard></ProtectedRoute>} />

              {/* Patents create/edit */}
              <Route path="/patents/new" element={<ProtectedRoute><PatentNewPage /></ProtectedRoute>} />
              <Route path="/patents/edit/:id" element={<ProtectedRoute><PatentEditGuard><PatentEditPage /></PatentEditGuard></ProtectedRoute>} />

              {/* Predictions */}
              <Route path="/predictions" element={<ProtectedRoute><PredictionsPage /></ProtectedRoute>} />
              <Route path="/predictions/new" element={<ProtectedRoute><PredictionNewPage /></ProtectedRoute>} />
              <Route path="/predictions/edit/:id" element={<ProtectedRoute><PredictionAccessGuard><PredictionEditPage /></PredictionAccessGuard></ProtectedRoute>} />
              <Route path="/predictions/:id" element={<ProtectedRoute><PredictionAccessGuard><PredictionDetailsPage /></PredictionAccessGuard></ProtectedRoute>} />

              {/* Users */}
              <Route path="/users" element={<ProtectedRoute requiredRole="admin"><UsersListPage /></ProtectedRoute>} />
              <Route path="/users/:id" element={<ProtectedRoute><UserDetailsPage /></ProtectedRoute>} />
              <Route path="/users/:id/edit" element={<ProtectedRoute><UserEditPage /></ProtectedRoute>} />

              {/* Reports */}
              <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />

              {/* Admin */}
              <Route path="/admin" element={<ProtectedRoute requiredRole="admin"><AdminPanel /></ProtectedRoute>} />

              {/* 404 */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </AppLayout>
        </GuestGate>
      </Router>
    </AuthProvider>
  );
}

export default App;