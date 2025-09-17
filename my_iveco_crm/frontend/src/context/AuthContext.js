import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import { jwtDecode } from 'jwt-decode';
import { useNavigate } from 'react-router-dom';

const AuthContext = createContext();

export const useAuth = () => {
    return useContext(AuthContext);
};

export const AuthProvider = ({ children }) => {
    // Завантажуємо токени з localStorage при першому завантаженні
    const [authTokens, setAuthTokens] = useState(() => localStorage.getItem('authTokens') ? JSON.parse(localStorage.getItem('authTokens')) : null);
    const [user, setUser] = useState(() => localStorage.getItem('authTokens') ? jwtDecode(localStorage.getItem('authTokens')) : null);
    const [loading, setLoading] = useState(true);

    const navigate = useNavigate();
    const API_URL = 'http://127.0.0.1:8000/api';

    const loginUser = async (username, password) => {
        try {
            const response = await axios.post(`${API_URL}/token/`, {
                username,
                password
            });
            if (response.status === 200) {
                const data = response.data;
                setAuthTokens(data);
                setUser(jwtDecode(data.access));
                localStorage.setItem('authTokens', JSON.stringify(data));
                navigate('/trucks'); // Перенаправляємо на сторінку вантажівок після входу
            }
        } catch (error) {
            console.error('Login Error:', error);
            // Тут можна використати showNotification, якщо передати його в контекст
            alert('Помилка! Неправильний логін або пароль.');
        }
    };

    const logoutUser = () => {
        setAuthTokens(null);
        setUser(null);
        localStorage.removeItem('authTokens');
        navigate('/login');
    };

    // Цей ефект буде перевіряти токен при кожному завантаженні сторінки
    useEffect(() => {
        // Тут можна додати логіку оновлення токену (refresh token)
        // Поки що просто завершуємо завантаження
        setLoading(false);
    }, [authTokens]);

    const contextData = {
        user,
        authTokens,
        loginUser,
        logoutUser,
    };

    return (
        <AuthContext.Provider value={contextData}>
            {loading ? null : children}
        </AuthContext.Provider>
    );
};