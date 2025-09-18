import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000/api';

const axiosInstance = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Це "перехоплювач" (interceptor). Він спрацьовує перед кожним запитом.
axiosInstance.interceptors.request.use(
    (config) => {
        // Беремо токени з localStorage
        const tokens = localStorage.getItem('authTokens') 
            ? JSON.parse(localStorage.getItem('authTokens')) 
            : null;

        if (tokens) {
            // Додаємо заголовок авторизації
            config.headers.Authorization = `Bearer ${tokens.access}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export default axiosInstance;