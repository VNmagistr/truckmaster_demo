import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Container, Typography, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Paper, Button, Box, Dialog, DialogTitle, 
    DialogContent, DialogActions, TextField, Select, MenuItem, 
    FormControl, InputLabel, CircularProgress, Chip
} from '@mui/material';
import { useNotification } from '../context/NotificationContext';

const API_URL = 'http://127.0.0.1:8000/api';

export default function OrdersPage() {
    const navigate = useNavigate();
    const { showNotification } = useNotification();
    
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [open, setOpen] = useState(false);
    
    // Довідники для форми
    const [clients, setClients] = useState([]);
    const [trucks, setTrucks] = useState([]);

    const [formData, setFormData] = useState({});

    const fetchData = useCallback(async () => {
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
            showNotification('Помилка завантаження даних!', 'error');
        } finally {
            setLoading(false);
        }
    }, [showNotification]);

    useEffect(() => {
        setLoading(true);
        fetchData();
    }, [fetchData]);

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

    const handleInputChange = (event) => {
        const { name, value } = event.target;
        if (name === 'client') {
            setFormData(prevState => ({ 
                ...prevState, 
                client: value, 
                truck: ''
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
                showNotification('Замовлення успішно створено!', 'success');
            } else {
                const errorData = await response.json();
                showNotification(`Помилка: ${JSON.stringify(errorData)}`, 'error');
            }
        } catch (error) {
            console.error("Помилка мережі:", error);
            showNotification('Помилка мережі при створенні замовлення', 'error');
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
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell><b>№</b></TableCell>
                                <TableCell><b>Клієнт</b></TableCell>
                                <TableCell><b>Автомобіль</b></TableCell>
                                <TableCell><b>Дата відкриття</b></TableCell>
                                <TableCell><b>Статус</b></TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {orders.map((order) => (
                                <TableRow 
                                    key={order.id} 
                                    hover 
                                    onClick={() => navigate(`/orders/${order.id}`)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <TableCell>{order.id}</TableCell>
                                    <TableCell>{order.client}</TableCell>
                                    <TableCell>{order.truck}</TableCell>
                                    <TableCell>{new Date(order.start_date).toLocaleDateString()}</TableCell>
                                    <TableCell>
                                        <Chip label={order.status} color={getStatusChipColor(order.status)} />
                                    </TableCell>
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
                    <FormControl fullWidth margin="dense" variant="standard" disabled={!formData.client}>
                        <InputLabel>Автомобіль</InputLabel>
                        <Select name="truck" value={formData.truck || ''} onChange={handleInputChange}>
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
