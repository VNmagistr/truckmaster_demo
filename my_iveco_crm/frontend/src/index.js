import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { NotificationProvider } from './context/NotificationContext';
import { ConfirmationProvider } from './context/ConfirmationContext';
import { AuthProvider } from './context/AuthContext';
import './index.css';
import App from './App';


const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <NotificationProvider>
        <ConfirmationProvider>
          {/* 2. Огортаємо App */}
          <AuthProvider>
            <App />
          </AuthProvider>
        </ConfirmationProvider>
      </NotificationProvider>
    </BrowserRouter>
  </React.StrictMode>
);