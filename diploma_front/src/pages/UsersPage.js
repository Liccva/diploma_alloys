import React from 'react';
import { useAuth } from '../context/AuthContext';

const UsersPage = () => {
  const { role } = useAuth();

  if (role !== 'admin') {
    return (
      <div className="access-denied">
        <h2>Доступ запрещен</h2>
        <p>Только администраторы могут просматривать эту страницу</p>
      </div>
    );
  }

  return (
    <div className="users-page">
      <h1>Управление пользователями</h1>
      <div className="info-message">
        <p>Страница управления пользователями находится в разработке</p>
        <p>Здесь администраторы смогут управлять пользователями системы</p>
      </div>
    </div>
  );
};

export default UsersPage;