import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function PrivateRoute() {
    const { user } = useAuth();

    if (!user) {
        // Якщо користувач не увійшов, перенаправляємо на сторінку логіну
        return <Navigate to="/login" />;
    }

    // Якщо увійшов - показуємо сторінку, на яку він хотів потрапити
    return <Outlet />;
}