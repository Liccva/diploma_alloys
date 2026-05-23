import React from 'react';
import { useLocation } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import Sidebar from './components/Sidebar';
import { useAuth } from './context/AuthContext';

const Layout = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  const noSidebarRoutes = ['/login', '/register'];
  const showSidebar = isAuthenticated && !noSidebarRoutes.includes(location.pathname);

  return (
    <div className="page-wrapper">
      <Header />
      <div className="industrial-grid"></div>
      <div style={{ display: 'flex' }}>
        {showSidebar && <Sidebar />}
        <main className={showSidebar ? "main-content" : "main-content-full"}>
          {children}
        </main>
      </div>
      <Footer />
    </div>
  );
};

export default Layout;