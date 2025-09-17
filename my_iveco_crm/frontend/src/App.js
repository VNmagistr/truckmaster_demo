import React from 'react';
import { Routes, Route } from 'react-router-dom';
import CrmLayout from './components/CrmLayout'; // Ми винесемо лейаут
import Notification from './components/Notification';
import HomePage from './pages/HomePage';
import TrucksPage from './pages/TrucksPage';
import ClientsPage from './pages/ClientsPage';
import OrdersPage from './pages/OrdersPage';
import OrderDetailPage from './pages/OrderDetailPage';
import LoginPage from './pages/LoginPage'; // Нова сторінка
import PrivateRoute from './components/PrivateRoute'; // Наш захист

function App() {
    return (
        <>
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/" element={<HomePage />} />
                {/* Всі внутрішні маршрути тепер захищені */}
                <Route element={<PrivateRoute />}>
                    <Route path="/trucks" element={<CrmLayout><TrucksPage /></CrmLayout>} />
                    <Route path="/clients" element={<CrmLayout><ClientsPage /></CrmLayout>} />
                    <Route path="/orders" element={<CrmLayout><OrdersPage /></CrmLayout>} />
                    <Route path="/orders/:orderId" element={<CrmLayout><OrderDetailPage /></CrmLayout>} />
                </Route>
            </Routes>
            <Notification />
        </>
    );
}
export default App;