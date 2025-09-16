import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { NotificationProvider } from './context/NotificationContext';
import { ConfirmationProvider } from './context/ConfirmationContext';
import './index.css';
import App from './App';


const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <NotificationProvider>
      {/* 2. Огортаємо App */}
        <ConfirmationProvider><App /></ConfirmationProvider>
      </NotificationProvider>
    </BrowserRouter>
  </React.StrictMode>
);