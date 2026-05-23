import React from "react";

const Footer = () => {
  const year = new Date().getFullYear();

  return (
    <footer className="app-footer">
      <div className="footer-inner">
        <div className="footer-left"> {year} Metal Alloys</div>
        <div className="footer-right">Система прогнозирования свойств сплавов</div>
      </div>
    </footer>
  );
};

export default Footer;
