import React from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Box, CssBaseline } from '@mui/material';
import Navbar from './components/Navbar';
import Notification from './components/Notification';

// Імпортуємо всі наші сторінки
import HomePage from './pages/HomePage';
import TrucksPage from './pages/TrucksPage';
import ClientsPage from './pages/ClientsPage';
import OrdersPage from './pages/OrdersPage';
import OrderDetailPage from './pages/OrderDetailPage';

// Створюємо компонент для "внутрішнього" інтерфейсу CRM
function CrmLayout({ children }) {
    return (
        <Box sx={{ display: 'flex' }}>
            <CssBaseline />
            <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
                <Toolbar>
                    <Typography variant="h6" noWrap component="div">
                        CRM для СТО Iveco
                    </Typography>
                </Toolbar>
            </AppBar>
            <Navbar />
            <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
                <Toolbar />
                {children}
            </Box>
            <Notification />
        </Box>
    );
}

function App() {
    return (
        <Routes>
            {/* Маршрут для головної сторінки */}
            <Route path="/" element={<HomePage />} />

            {/* Маршрути для внутрішньої частини CRM */}
            <Route path="/trucks" element={<CrmLayout><TrucksPage /></CrmLayout>} />
            <Route path="/clients" element={<CrmLayout><ClientsPage /></CrmLayout>} />
            <Route path="/orders" element={<CrmLayout><OrdersPage /></CrmLayout>} />
            <Route path="/orders/:orderId" element={<CrmLayout><OrderDetailPage /></CrmLayout>} />
        </Routes>
    );
}

export default App;