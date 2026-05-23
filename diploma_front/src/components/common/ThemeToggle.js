import React, { useEffect, useState } from 'react';

const ThemeToggle = () => {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <button
      className={`theme-slider ${theme === 'light' ? 'active' : ''}`}
      onClick={toggleTheme}
      title={theme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему'}
      type="button"
    >
      <span className="theme-slider-track">
        <span className="theme-slider-icon sun">☀️</span>
        <span className="theme-slider-icon moon">🌙</span>
        <span className="theme-slider-thumb"></span>
      </span>
    </button>
  );
};

export default ThemeToggle;