// frontend/src/pages/OrderDetailPage.js

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Container, Typography, Box, Paper, CircularProgress, Grid, 
    List, ListItem, ListItemText, Divider, Button, Chip, IconButton,
    Dialog, DialogTitle, DialogContent, DialogActions, TextField,
    Select, MenuItem, FormControl, InputLabel
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';

const API_URL = 'http://127.0.0.1:8000/api';

export default function OrderDetailPage() {
    const { orderId } = useParams();
    const navigate = useNavigate();
    const [order, setOrder] = useState(null);
    const [loading, setLoading] = useState(true);

    // Стани для довідників
    const [employees, setEmployees] = useState([]);
    const [parts, setParts] = useState([]);

    // Стани для модального вікна робіт
    const [openWorkModal, setOpenWorkModal] = useState(false);
    const [editingWork, setEditingWork] = useState(null);
    const [workFormData, setWorkFormData] = useState({});

    // Стани для модального вікна запчастин
    const [openPartModal, setOpenPartModal] = useState(false);
    const [currentWorkId, setCurrentWorkId] = useState(null);
    const [partFormData, setPartFormData] = useState({});

    // --- ОСНОВНА ФУНКЦІЯ ЗАВАНТАЖЕННЯ ДАНИХ ---
    const fetchPageData = async () => {
        try {
            const [orderRes, employeesRes, partsRes] = await Promise.all([
                fetch(`${API_URL}/service-orders/${orderId}/`),
                fetch(`${API_URL}/employees/`),
                fetch(`${API_URL}/parts/`)
            ]);
            const orderData = await orderRes.json();
            const employeesData = await employeesRes.json();
            const partsData = await partsRes.json();
            setOrder(orderData);
            setEmployees(employeesData);
            setParts(partsData);
        } catch (error) {
            console.error("Помилка завантаження даних!", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        setLoading(true);
        fetchPageData();
    }, [orderId]);


    // --- ФУНКЦІЇ ДЛЯ КЕРУВАННЯ РОБОТАМИ ---
    const handleOpenWorkModal = (work = null) => {
        setEditingWork(work);
        setWorkFormData(work ? { ...work } : {
            job_description: '',
            labor_cost: 0,
            duration_hours: 0,
            employee: ''
        });
        setOpenWorkModal(true);
    };

    const handleCloseWorkModal = () => setOpenWorkModal(false);

    const handleWorkInputChange = (e) => {
        const { name, value } = e.target;
        setWorkFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleWorkFormSubmit = async () => {
        const method = editingWork ? 'PUT' : 'POST';
        const url = editingWork 
            ? `${API_URL}/service-works/${editingWork.id}/` 
            : `${API_URL}/service-works/`;
        
        const body = {
            ...workFormData,
            service_order: orderId,
        };

        try {
            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (response.ok) {
                handleCloseWorkModal();
                fetchPageData(); // Оновлюємо всю сторінку
            } else {
                const errorData = await response.json();
                alert(`Помилка: ${JSON.stringify(errorData)}`);
            }
        } catch (error) { console.error("Помилка мережі:", error); }
    };

    const handleDeleteWork = async (workId) => {
        if (window.confirm("Ви впевнені, що хочете видалити цю роботу?")) {
            try {
                const response = await fetch(`${API_URL}/service-works/${workId}/`, { method: 'DELETE' });
                if (response.ok) {
                    fetchPageData();
                } else { alert('Не вдалося видалити роботу.'); }
            } catch (error) { console.error("Помилка мережі:", error); }
        }
    };

    // --- ФУНКЦІЇ ДЛЯ КЕРУВАННЯ ЗАПЧАСТИНАМИ ---
    const handleOpenPartModal = (workId) => {
        setCurrentWorkId(workId);
        setPartFormData({ part: '', quantity: 1 });
        setOpenPartModal(true);
    };

    const handleClosePartModal = () => setOpenPartModal(false);

    const handlePartInputChange = (e) => {
        const { name, value } = e.target;
        setPartFormData(prev => ({ ...prev, [name]: value }));
    };

    const handlePartFormSubmit = async () => {
        const body = {
            ...partFormData,
            service_work: currentWorkId,
        };
        try {
            const response = await fetch(`${API_URL}/used-parts/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (response.ok) {
                handleClosePartModal();
                fetchPageData();
            } else {
                const errorData = await response.json();
                alert(`Помилка: ${JSON.stringify(errorData)}`);
            }
        } catch (error) { console.error("Помилка мережі:", error); }
    };


    // --- ЛОГІКА ВІДОБРАЖЕННЯ ---
    if (loading) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}><CircularProgress /></Box>;
    }

    if (!order) {
        return <Typography variant="h5" align="center" sx={{ mt: 4 }}>Замовлення не знайдено</Typography>;
    }

    return (
        <Container style={{ marginTop: '2rem' }}>
            <Button onClick={() => navigate('/orders')} sx={{ mb: 2 }}>
                &larr; Назад до списку
            </Button>
            <Paper sx={{ p: 3 }}>
                <Typography variant="h4" gutterBottom>
                    Замовлення-наряд №{order?.id}
                    <Chip label={order?.status} color="primary" sx={{ ml: 2 }} />
                </Typography>
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={6}>
                        <Typography variant="h6">Клієнт</Typography>
                        <Typography>{order?.client?.name} {order?.client?.surname}</Typography>
                        <Typography color="textSecondary">{order?.client?.phone}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                        <Typography variant="h6">Автомобіль</Typography>
                        <Typography>{order?.truck?.specific_model_name} ({order?.truck?.license_plate})</Typography>
                        <Typography color="textSecondary">VIN: {order?.truck?.last_seven_vin}</Typography>
                    </Grid>
                </Grid>
                <Divider sx={{ my: 2 }} />
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="h5" gutterBottom>Виконані роботи</Typography>
                    <Button variant="outlined" startIcon={<AddIcon />} onClick={() => handleOpenWorkModal(null)}>
                        Додати роботу
                    </Button>
                </Box>
                <List>
                    {order?.works?.map((work, index) => (
                        <React.Fragment key={work.id}>
                            <ListItem
                                secondaryAction={
                                    <>
                                        <IconButton edge="end" aria-label="edit" onClick={() => handleOpenWorkModal(work)}>
                                            <EditIcon />
                                        </IconButton>
                                        <IconButton edge="end" aria-label="delete" onClick={() => handleDeleteWork(work.id)}>
                                            <DeleteIcon />
                                        </IconButton>
                                    </>
                                }
                            >
                                <ListItemText 
                                    primary={work.job_description}
                                    secondary={`Вартість: ${work.labor_cost} грн | Годин: ${work.duration_hours}`}
                                />
                            </ListItem>
                            <List disablePadding sx={{ pl: 4 }}>
                                {work.used_parts.map(up => (
                                    <ListItem key={up.id} sx={{ py: 0 }}>
                                        <ListItemText 
                                            primary={`${up.part.name} (x${up.quantity})`}
                                            secondary={`Ціна: ${up.part.price} грн/шт.`} 
                                            sx={{ fontStyle: 'italic' }}
                                        />
                                    </ListItem>
                                ))}
                                <ListItem>
                                    <Button size="small" startIcon={<AddIcon />} onClick={() => handleOpenPartModal(work.id)}>
                                        Додати запчастину
                                    </Button>
                                </ListItem>
                            </List>
                            {index < order.works.length - 1 && <Divider component="li" />}
                        </React.Fragment>
                    ))}
                </List>
            </Paper>
            
            <Dialog open={openWorkModal} onClose={handleCloseWorkModal} fullWidth maxWidth="sm">
                <DialogTitle>{editingWork ? 'Редагувати роботу' : 'Додати нову роботу'}</DialogTitle>
                <DialogContent>
                    <TextField autoFocus margin="dense" name="job_description" label="Опис роботи" type="text" fullWidth variant="standard" value={workFormData.job_description || ''} onChange={handleWorkInputChange} />
                    <TextField margin="dense" name="labor_cost" label="Вартість роботи" type="number" fullWidth variant="standard" value={workFormData.labor_cost || ''} onChange={handleWorkInputChange} />
                    <TextField margin="dense" name="duration_hours" label="Витрачено годин" type="number" fullWidth variant="standard" value={workFormData.duration_hours || ''} onChange={handleWorkInputChange} />
                    <FormControl fullWidth margin="dense" variant="standard">
                        <InputLabel>Виконавець</InputLabel>
                        <Select name="employee" value={workFormData.employee || ''} onChange={handleWorkInputChange}>
                            {employees.map(emp => <MenuItem key={emp.id} value={emp.id}>{emp.name}</MenuItem>)}
                        </Select>
                    </FormControl>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseWorkModal}>Скасувати</Button>
                    <Button onClick={handleWorkFormSubmit}>Зберегти</Button>
                </DialogActions>
            </Dialog>
        
            <Dialog open={openPartModal} onClose={handleClosePartModal} fullWidth maxWidth="sm">
                <DialogTitle>Додати запчастину до роботи</DialogTitle>
                <DialogContent>
                    <FormControl fullWidth margin="dense" variant="standard">
                        <InputLabel>Запчастина</InputLabel>
                        <Select name="part" value={partFormData.part || ''} onChange={handlePartInputChange}>
                            {parts.map(p => <MenuItem key={p.id} value={p.id}>{p.name} ({p.sku_code})</MenuItem>)}
                        </Select>
                    </FormControl>
                    <TextField margin="dense" name="quantity" label="Кількість" type="number" fullWidth variant="standard" value={partFormData.quantity || 1} onChange={handlePartInputChange} />
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleClosePartModal}>Скасувати</Button>
                    <Button onClick={handlePartFormSubmit}>Додати</Button>
                </DialogActions>
            </Dialog>
        </Container>
    );
}