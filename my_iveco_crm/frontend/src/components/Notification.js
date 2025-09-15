import React from 'react';
import { Snackbar, Alert } from '@mui/material';
import { useNotification } from '../context/NotificationContext';

export default function Notification() {
    const { notification, hideNotification } = useNotification();

    return (
        <Snackbar
            open={notification.open}
            autoHideDuration={6000} // 6 секунд
            onClose={hideNotification}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
            <Alert
                onClose={hideNotification}
                severity={notification.severity}
                sx={{ width: '100%' }}
            >
                {notification.message}
            </Alert>
        </Snackbar>
    );
}
