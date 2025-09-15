import React, { createContext, useState, useContext } from 'react';

const NotificationContext = createContext();

export const useNotification = () => {
    return useContext(NotificationContext);
};

export const NotificationProvider = ({ children }) => {
    const [notification, setNotification] = useState({
        open: false,
        message: '',
        severity: 'info', // 'error', 'warning', 'info', 'success'
    });

    const showNotification = (message, severity = 'success') => {
        setNotification({
            open: true,
            message,
            severity,
        });
    };

    const hideNotification = () => {
        setNotification((prev) => ({ ...prev, open: false }));
    };

    const value = {
        notification,
        showNotification,
        hideNotification,
    };

    return (
        <NotificationContext.Provider value={value}>
            {children}
        </NotificationContext.Provider>
    );
};