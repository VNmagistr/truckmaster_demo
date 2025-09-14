import React, { useState, useEffect } from 'react';
import {
    Container, Typography, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Paper, Button, Box, Dialog, DialogTitle, 
    DialogContent, DialogActions, TextField, Select, MenuItem, 
    FormControl, InputLabel, CircularProgress, Chip
} from '@mui/material';
import { useNavigate } from 'react-router-dom';

const API_URL = 'http://127.0.0.1:8000/api';

export default function OrdersPage() {
    const navigate = useNavigate();
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [open, setOpen] = useState(false);
    const [clients, setClients] = useState([]);
    const [trucks, setTrucks] = useState([]);
    const [formData, setFormData] = useState({});

    const fetchData = async () => {
        setLoading(true);
        try {
            const [ordersRes, clientsRes, trucksRes] = await Promise.all([
                fetch(`${API_URL}/service-orders/`),
                fetch(`${API_URL}/clients/`),
                fetch(`${API_URL}/trucks/`)
            ]);
            const ordersData = await ordersRes.json();
            const clientsData = await clientsRes.json();
            const trucksData = await trucksRes.json();
            setOrders(ordersData);
            setClients(clientsData);
            setTrucks(trucksData);
        } catch (error) {
            console.error("Помилка завантаження даних!", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleOpenModal = () => {
        setFormData({
            status: 'new',
            description: '',
            client: '',
            truck: ''
        });
        setOpen(true);
    };

    const handleCloseModal = () => setOpen(false);

    // ЗМІНЕНО: Ця функція тепер стала "розумнішою"
    const handleInputChange = (event) => {
        const { name, value } = event.target;

        // Якщо ми змінюємо клієнта, потрібно скинути вибраний автомобіль,
        // оскільки старий вибір може вже не належати новому клієнту.
        if (name === 'client') {
            setFormData(prevState => ({ 
                ...prevState, 
                client: value, 
                truck: '' // Скидаємо вибір вантажівки
            }));
        } else {
            setFormData(prevState => ({ ...prevState, [name]: value }));
        }
    };

    const handleFormSubmit = async () => {
        try {
            const response = await fetch(`${API_URL}/service-orders/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            });
            if (response.ok) {
                handleCloseModal();
                fetchData();
            } else {
                const errorData = await response.json();
                alert(`Помилка: ${JSON.stringify(errorData)}`);
            }
        } catch (error) {
            console.error("Помилка мережі:", error);
        }
    };

    const getStatusChipColor = (status) => {
        switch (status.toLowerCase()) {
            case 'нове': return 'primary';
            case 'в роботі': return 'warning';
            case 'завершено': return 'success';
            case 'скасовано': return 'default';
            default: return 'default';
        }
    };

    // НОВЕ: Створюємо відфільтрований список вантажівок прямо перед рендерингом
    const filteredTrucks = formData.client 
        ? trucks.filter(truck => truck.client_id === formData.client)
        : [];

    return (
        <Container style={{ marginTop: '2rem' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h4">Замовлення-наряди</Typography>
                <Button variant="contained" color="primary" onClick={handleOpenModal}>
                    Створити замовлення
                </Button>
            </Box>

            {loading ? ( <CircularProgress /> ) : (
                <TableContainer component={Paper}>
                    {/* ... Таблиця з замовленнями без змін ... */}
                    <Table>
                        <TableHead><TableRow><TableCell><b>№</b></TableCell><TableCell><b>Клієнт</b></TableCell><TableCell><b>Автомобіль</b></TableCell><TableCell><b>Дата відкриття</b></TableCell><TableCell><b>Статус</b></TableCell></TableRow></TableHead>
                        <TableBody>
                            {orders.map((order) => (
                                <TableRow   key={order.id} 
                                            hover 
                                            onClick={() => navigate(`/orders/${order.id}`)}
                                            style={{ cursor: 'pointer' }}>
                                    <TableCell>{order.id}</TableCell>
                                    <TableCell>{order.client}</TableCell>
                                    <TableCell>{order.truck}</TableCell>
                                    <TableCell>{new Date(order.start_date).toLocaleDateString()}</TableCell>
                                    <TableCell><Chip label={order.status} color={getStatusChipColor(order.status)} /></TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}

            <Dialog open={open} onClose={handleCloseModal} fullWidth maxWidth="sm">
                <DialogTitle>Створити нове замовлення-наряд</DialogTitle>
                <DialogContent>
                    <FormControl fullWidth margin="dense" variant="standard">
                        <InputLabel>Клієнт</InputLabel>
                        <Select name="client" value={formData.client || ''} onChange={handleInputChange}>
                            {clients.map(client => <MenuItem key={client.id} value={client.id}>{client.name} {client.surname}</MenuItem>)}
                        </Select>
                    </FormControl>

                    {/* ЗМІНЕНО: Випадаючий список тепер залежить від вибору клієнта */}
                    <FormControl fullWidth margin="dense" variant="standard" disabled={!formData.client}>
                        <InputLabel>Автомобіль</InputLabel>
                        <Select name="truck" value={formData.truck || ''} onChange={handleInputChange}>
                            {/* Використовуємо ВІДФІЛЬТРОВАНИЙ список */}
                            {filteredTrucks.map(truck => <MenuItem key={truck.id} value={truck.id}>{truck.specific_model_name} ({truck.license_plate})</MenuItem>)}
                        </Select>
                    </FormControl>

                    <TextField margin="dense" name="description" label="Причина звернення / Скарги" type="text" fullWidth multiline rows={4} variant="standard" value={formData.description || ''} onChange={handleInputChange} />

                    <FormControl fullWidth margin="dense" variant="standard">
                        <InputLabel>Статус</InputLabel>
                        <Select name="status" value={formData.status || 'new'} onChange={handleInputChange}>
                            <MenuItem value="new">Нове</MenuItem>
                            <MenuItem value="in_progress">В роботі</MenuItem>
                            <MenuItem value="completed">Завершено</MenuItem>
                            <MenuItem value="canceled">Скасовано</MenuItem>
                        </Select>
                    </FormControl>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseModal}>Скасувати</Button>
                    <Button onClick={handleFormSubmit}>Зберегти</Button>
                </DialogActions>
            </Dialog>
        </Container>
    );
}