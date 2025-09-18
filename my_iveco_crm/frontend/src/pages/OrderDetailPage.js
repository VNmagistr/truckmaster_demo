// frontend/src/pages/OrderDetailPage.js (Фінальна версія з усіма виправленнями)

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Container, Typography, Box, Paper, Grid, List, ListItem,
    ListItemText, Divider, Button, Chip, IconButton, Dialog,
    DialogTitle, DialogContent, DialogActions, TextField, Select,
    MenuItem, FormControl, InputLabel
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { useNotification } from '../context/NotificationContext';
import { useConfirmation } from '../context/ConfirmationContext';
import axiosInstance from '../api/axiosInstance';
import OrderDetailSkeleton from '../components/skeletons/OrderDetailSkeleton';

export default function OrderDetailPage() {
    const { orderId } = useParams();
    const navigate = useNavigate();
    const { showNotification } = useNotification();
    const { confirm } = useConfirmation();

    const [order, setOrder] = useState(null);
    const [loading, setLoading] = useState(true);
    const [employees, setEmployees] = useState([]);
    const [parts, setParts] = useState([]);
    const [openWorkModal, setOpenWorkModal] = useState(false);
    const [editingWork, setEditingWork] = useState(null);
    const [workFormData, setWorkFormData] = useState({});
    const [openPartModal, setOpenPartModal] = useState(false);
    const [currentWorkId, setCurrentWorkId] = useState(null);
    const [editingPart, setEditingPart] = useState(null);
    const [partFormData, setPartFormData] = useState({});

    const fetchPageData = useCallback(async () => {
        try {
            const [orderRes, employeesRes, partsRes] = await Promise.all([
                axiosInstance.get(`/service-orders/${orderId}/`),
                axiosInstance.get('/employees/'),
                axiosInstance.get('/parts/')
            ]);
            if (!orderRes.data) throw new Error('Замовлення не знайдено');
            setOrder(orderRes.data);
            setEmployees(employeesRes.data.results || employeesRes.data);
            setParts(partsRes.data.results || partsRes.data);
        } catch (error) {
            console.error("Помилка завантаження даних!", error);
            showNotification(error.message || "Помилка завантаження даних!", 'error');
            setOrder(null);
        } finally {
            setLoading(false);
        }
    }, [orderId, showNotification]);

    useEffect(() => {
        setLoading(true);
        fetchPageData();
    }, [fetchPageData]);

    const handleOpenWorkModal = (work = null) => {
        setEditingWork(work);
        setWorkFormData(work ? { ...work } : { job_description: '', labor_cost: '', duration_hours: '', employee: '' });
        setOpenWorkModal(true);
    };
    const handleCloseWorkModal = () => setOpenWorkModal(false);
    const handleWorkInputChange = (e) => setWorkFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
    const handleWorkFormSubmit = async () => {
        const method = editingWork ? 'put' : 'post';
        const url = editingWork ? `/service-works/${editingWork.id}/` : `/service-works/`;
        const body = { ...workFormData, service_order: orderId };
        try {
            await axiosInstance[method](url, body);
            handleCloseWorkModal();
            fetchPageData();
            showNotification(editingWork ? 'Роботу оновлено' : 'Роботу додано', 'success');
        } catch (error) { showNotification(`Помилка: ${JSON.stringify(error.response.data)}`, 'error'); }
    };
    const handleDeleteWork = (workId, workDescription) => {
        confirm('Підтвердити видалення', `Ви впевнені, що хочете видалити роботу "${workDescription}"?`,
            async () => {
                try {
                    await axiosInstance.delete(`/service-works/${workId}/`);
                    fetchPageData();
                    showNotification('Роботу видалено', 'success');
                } catch (error) { showNotification('Не вдалося видалити.', 'error'); }
            }
        );
    };
    const handleOpenPartModal = (workId, usedPart = null) => {
        setCurrentWorkId(workId);
        setEditingPart(usedPart);
        setPartFormData(usedPart ? { part: usedPart.part.id, quantity: usedPart.quantity } : { part: '', quantity: 1 });
        setOpenPartModal(true);
    };
    const handleClosePartModal = () => setOpenPartModal(false);
    const handlePartInputChange = (e) => setPartFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
    const handlePartFormSubmit = async () => {
        const method = editingPart ? 'put' : 'post';
        const url = editingPart ? `/used-parts/${editingPart.id}/` : `/used-parts/`;
        const body = { part_id: partFormData.part, quantity: partFormData.quantity, service_work: currentWorkId };
        try {
            await axiosInstance[method](url, body);
            handleClosePartModal();
            fetchPageData();
            showNotification(editingPart ? 'Запчастину оновлено' : 'Запчастину додано', 'success');
        } catch (error) { showNotification(`Помилка: ${JSON.stringify(error.response.data)}`, 'error'); }
    };
    const handleDeletePart = (usedPartId, partName) => {
        confirm('Підтвердити видалення', `Ви впевнені, що хочете видалити запчастину "${partName}" з цієї роботи?`,
            async () => {
                try {
                    await axiosInstance.delete(`/used-parts/${usedPartId}/`);
                    fetchPageData();
                    showNotification('Запчастину видалено', 'success');
                } catch (error) { showNotification('Не вдалося видалити.', 'error'); }
            }
        );
    };

    if (loading) {
        return <OrderDetailSkeleton />;
    }
    
    if (!order) {
        return (
            <Container style={{ marginTop: '2rem' }}>
                <Typography variant="h5" align="center">Не вдалося завантажити дані про замовлення.</Typography>
                <Box textAlign="center" mt={2}><Button variant="contained" onClick={() => navigate('/orders')}>Повернутись до списку</Button></Box>
            </Container>
        );
    }

    return (
        <Container style={{ marginTop: '2rem' }}>
            <Button onClick={() => navigate('/orders')} sx={{ mb: 2 }}>&larr; Назад до списку</Button>
            <Paper sx={{ p: 3 }}>
                <Typography variant="h4" gutterBottom>Замовлення-наряд №{order.id}<Chip label={order.status} color="primary" sx={{ ml: 2 }} /></Typography>
                <Typography variant="h5" color="text.secondary" sx={{ mb: 2 }}>Загальна вартість: {order.total_cost} грн</Typography>
                <Grid container spacing={2} sx={{ mb: 3 }}><Grid item xs={12} md={6}><Typography variant="h6">Клієнт</Typography><Typography>{order.client.name} {order.client.surname}</Typography><Typography color="textSecondary">{order.client.phone}</Typography></Grid><Grid item xs={12} md={6}><Typography variant="h6">Автомобіль</Typography><Typography>{order.truck.specific_model_name} ({order.truck.license_plate})</Typography><Typography color="textSecondary">VIN: {order.truck.last_seven_vin}</Typography></Grid></Grid>
                <Divider sx={{ my: 2 }} />
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}><Typography variant="h5" gutterBottom>Виконані роботи</Typography><Button variant="outlined" startIcon={<AddIcon />} onClick={() => handleOpenWorkModal(null)}>Додати роботу</Button></Box>
                <List>
                    {order.works.map((work, index) => (
                        <React.Fragment key={work.id}>
                            <ListItem secondaryAction={<><IconButton onClick={() => handleOpenWorkModal(work)}><EditIcon /></IconButton><IconButton onClick={() => handleDeleteWork(work.id, work.job_description)}><DeleteIcon /></IconButton></>}>
                                <ListItemText primary={work.job_description} secondary={`Вартість: ${work.labor_cost} грн | Годин: ${work.duration_hours}`} />
                            </ListItem>
                            <List disablePadding sx={{ pl: 4 }}>
                                {work.used_parts.map(up => (
                                    <ListItem key={up.id} sx={{ py: 0 }} secondaryAction={<><IconButton size="small" edge="end" onClick={() => handleOpenPartModal(work.id, up)}><EditIcon fontSize="small" /></IconButton><IconButton size="small" edge="end" onClick={() => handleDeletePart(up.id, up.part.name)}><DeleteIcon fontSize="small" /></IconButton></>}>
                                        <ListItemText primary={`${up.part.name} (x${up.quantity})`} secondary={`Ціна: ${up.part.price} грн/шт.`} sx={{ fontStyle: 'italic' }} />
                                    </ListItem>
                                ))}
                                <ListItem><Button size="small" startIcon={<AddIcon />} onClick={() => handleOpenPartModal(work.id, null)}>Додати запчастину</Button></ListItem>
                            </List>
                            {index < order.works.length - 1 && <Divider component="li" />}
                        </React.Fragment>
                    ))}
                </List>
            </Paper>
            <Dialog open={openWorkModal} onClose={handleCloseWorkModal} fullWidth maxWidth="sm"><DialogTitle>{editingWork ? 'Редагувати роботу' : 'Додати нову роботу'}</DialogTitle><DialogContent><TextField autoFocus margin="dense" name="job_description" label="Опис роботи" type="text" fullWidth variant="standard" value={workFormData.job_description || ''} onChange={handleWorkInputChange} /><TextField margin="dense" name="labor_cost" label="Вартість роботи" type="number" fullWidth variant="standard" value={workFormData.labor_cost || ''} onChange={handleWorkInputChange} /><TextField margin="dense" name="duration_hours" label="Витрачено годин" type="number" fullWidth variant="standard" value={workFormData.duration_hours || ''} onChange={handleWorkInputChange} /><FormControl fullWidth margin="dense" variant="standard"><InputLabel>Виконавець</InputLabel><Select name="employee" value={workFormData.employee || ''} onChange={handleWorkInputChange}>{employees.map(emp => <MenuItem key={emp.id} value={emp.id}>{emp.name}</MenuItem>)}</Select></FormControl></DialogContent><DialogActions><Button onClick={handleCloseWorkModal}>Скасувати</Button><Button onClick={handleWorkFormSubmit}>Зберегти</Button></DialogActions></Dialog>
            <Dialog open={openPartModal} onClose={handleClosePartModal} fullWidth maxWidth="sm"><DialogTitle>{editingPart ? 'Редагувати запчастину' : 'Додати запчастину до роботи'}</DialogTitle><DialogContent><FormControl fullWidth margin="dense" variant="standard" disabled={!!editingPart}><InputLabel>Запчастина</InputLabel><Select name="part" value={partFormData.part || ''} onChange={handlePartInputChange}><MenuItem value="" disabled><em>Виберіть запчастину...</em></MenuItem>{parts.map(p => <MenuItem key={p.id} value={p.id}>{p.name} ({p.sku_code})</MenuItem>)}</Select></FormControl><TextField margin="dense" name="quantity" label="Кількість" type="number" fullWidth variant="standard" value={partFormData.quantity || 1} onChange={handlePartInputChange} /></DialogContent><DialogActions><Button onClick={handleClosePartModal}>Скасувати</Button><Button onClick={handlePartFormSubmit}>Зберегти</Button></DialogActions></Dialog>
        </Container>
    );
}