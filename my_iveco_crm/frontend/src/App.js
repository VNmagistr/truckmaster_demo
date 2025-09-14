import React from 'react';
import { Routes, Route, Link as RouterLink } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Box } from '@mui/material';
import Navbar from './components/Navbar'; // Наше нове меню
import TrucksPage from './pages/TrucksPage'; // Наша нова сторінка
import ClientsPage from './pages/ClientsPage';
import OrdersPage from './pages/OrdersPage';
import OrderDetailPage from './pages/OrderDetailPage';

// Прості сторінки-заглушки
// const ClientsPage = () => <Typography variant="h4" sx={{ m: 4 }}>Сторінка клієнтів</Typography>;
// const OrdersPage = () => <Typography variant="h4" sx={{ m: 4 }}>Сторінка замовлень</Typography>;

function App() {
    return (
        <Box sx={{ display: 'flex' }}>
            {/* Верхня панель */}
            <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
                <Toolbar>
                    <Typography variant="h6" noWrap component="div">
                        TRUCKMASTER CRM
                    </Typography>
                </Toolbar>
            </AppBar>

            {/* Бічна панель навігації */}
            <Navbar />

            {/* Основний контент сторінки */}
            <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
                <Toolbar /> {/* Цей Toolbar потрібен, щоб контент не ховався під AppBar */}
                <Routes>
                    <Route path="/trucks" element={<TrucksPage />} />
                    <Route path="/clients" element={<ClientsPage />} />
                    <Route path="/orders" element={<OrdersPage />} />
                    <Route path="/orders/:orderId" element={<OrderDetailPage />} /> {/* 2. Додаємо */}
                    {/* Маршрут за замовчуванням */}
                    <Route path="/" element={<TrucksPage />} />
                </Routes>
            </Box>
        </Box>
    );
}

export default App;