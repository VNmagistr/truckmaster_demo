import React, { useState, useEffect, useCallback } from 'react';
import {
    Container, Typography, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Paper, Button, Box, Dialog, DialogTitle, 
    DialogContent, DialogActions, TextField, IconButton, CircularProgress
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { useNotification } from '../context/NotificationContext';
import { useConfirmation } from '../context/ConfirmationContext';
import axiosInstance from '../api/axiosInstance';

export default function ClientsPage() {
    const { showNotification } = useNotification();
    const { confirm } = useConfirmation();
    const [clients, setClients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [open, setOpen] = useState(false);
    const [editingClient, setEditingClient] = useState(null);
    const [formData, setFormData] = useState({});

    const fetchClients = useCallback(async () => {
        try {
            const response = await axiosInstance.get('/clients/');
            const data = response.data;
            if (data && Array.isArray(data.results)) {
                setClients(data.results);
            } else if (Array.isArray(data)) {
                setClients(data);
            }
        } catch (error) {
            console.error("Помилка завантаження клієнтів!", error);
            showNotification("Помилка завантаження клієнтів!", 'error');
        } finally {
            setLoading(false);
        }
    }, [showNotification]);

    useEffect(() => {
        setLoading(true);
        fetchClients();
    }, [fetchClients]);

    const handleOpenModal = (client = null) => {
        setEditingClient(client);
        setFormData(client ? { ...client } : { name: '', surname: '', phone: '', email: '' });
        setOpen(true);
    };
    const handleCloseModal = () => setOpen(false);
    const handleInputChange = (event) => {
        setFormData(prevState => ({ ...prevState, [event.target.name]: event.target.value }));
    };

    const handleFormSubmit = async () => {
        const method = editingClient ? 'put' : 'post';
        const url = editingClient ? `/clients/${editingClient.id}/` : '/clients/';
        try {
            await axiosInstance[method](url, formData);
            handleCloseModal();
            fetchClients();
            showNotification(editingClient ? 'Дані клієнта оновлено!' : 'Клієнта успішно створено!', 'success');
        } catch (error) {
            console.error("Помилка форми:", error);
            showNotification(`Помилка: ${JSON.stringify(error.response.data)}`, 'error');
        }
    };

    const handleDelete = (id, clientName) => {
        confirm('Підтвердити видалення', `Ви впевнені, що хочете видалити клієнта "${clientName}"?`,
            async () => {
                try {
                    await axiosInstance.delete(`/clients/${id}/`);
                    fetchClients();
                    showNotification('Клієнта видалено', 'success');
                } catch (error) {
                    showNotification('Не вдалося видалити клієнта.', 'error');
                }
            }
        );
    };

    return (
        <Container style={{ marginTop: '2rem' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h4">Клієнти</Typography>
                <Button variant="contained" color="primary" onClick={() => handleOpenModal(null)}>Додати клієнта</Button>
            </Box>
            {loading ? <CircularProgress /> : (
                <TableContainer component={Paper}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell><b>Ім'я / Назва</b></TableCell>
                                <TableCell><b>Прізвище</b></TableCell>
                                <TableCell><b>Телефон</b></TableCell>
                                <TableCell><b>Email</b></TableCell>
                                <TableCell align="right"><b>Дії</b></TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {clients.map((client) => (
                                <TableRow key={client.id}>
                                    <TableCell>{client.name}</TableCell>
                                    <TableCell>{client.surname}</TableCell>
                                    <TableCell>{client.phone}</TableCell>
                                    <TableCell>{client.email}</TableCell>
                                    <TableCell align="right">
                                        <IconButton onClick={() => handleOpenModal(client)}><EditIcon /></IconButton>
                                        <IconButton onClick={() => handleDelete(client.id, `${client.name} ${client.surname}`.trim())}><DeleteIcon /></IconButton>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}
            <Dialog open={open} onClose={handleCloseModal} fullWidth maxWidth="sm">
                <DialogTitle>{editingClient ? 'Редагувати дані клієнта' : 'Додати нового клієнта'}</DialogTitle>
                <DialogContent>
                    <TextField autoFocus margin="dense" name="name" label="Ім'я / Назва компанії" type="text" fullWidth variant="standard" value={formData.name || ''} onChange={handleInputChange} />
                    <TextField margin="dense" name="surname" label="Прізвище" type="text" fullWidth variant="standard" value={formData.surname || ''} onChange={handleInputChange} />
                    <TextField margin="dense" name="phone" label="Телефон" type="text" fullWidth variant="standard" value={formData.phone || ''} onChange={handleInputChange} />
                    <TextField margin="dense" name="email" label="Email" type="email" fullWidth variant="standard" value={formData.email || ''} onChange={handleInputChange} />
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseModal}>Скасувати</Button>
                    <Button onClick={handleFormSubmit}>Зберегти</Button>
                </DialogActions>
            </Dialog>
        </Container>
    );
}