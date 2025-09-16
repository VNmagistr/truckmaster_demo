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

const API_URL = 'http://127.0.0.1:8000/api';

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
            const response = await fetch(`${API_URL}/clients/`);
            const data = await response.json();
            setClients(data);
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
        setFormData(client ? { ...client } : {
            name: '',
            surname: '',
            phone: '',
            email: ''
        });
        setOpen(true);
    };

    const handleCloseModal = () => setOpen(false);

    const handleInputChange = (event) => {
        const { name, value } = event.target;
        setFormData(prevState => ({ ...prevState, [name]: value }));
    };

    const handleFormSubmit = async () => {
        const method = editingClient ? 'PUT' : 'POST';
        const url = editingClient ? `${API_URL}/clients/${editingClient.id}/` : `${API_URL}/clients/`;

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            });
            if (response.ok) {
                handleCloseModal();
                fetchClients();
                showNotification(
                    editingClient ? 'Дані клієнта оновлено!' : 'Клієнта успішно створено!',
                    'success'
                );
            } else {
                const errorData = await response.json();
                showNotification(`Помилка: ${JSON.stringify(errorData)}`, 'error');
            }
        } catch (error) {
            console.error("Помилка мережі:", error);
            showNotification('Помилка мережі', 'error');
        }
    };

    const handleDelete = (id, clientName) => {
        confirm(
            'Підтвердити видалення',
            `Ви впевнені, що хочете видалити клієнта "${clientName}"? Цю дію неможливо буде скасувати.`,
            async () => {
                try {
                    const response = await fetch(`${API_URL}/clients/${id}/`, { method: 'DELETE' });
                    if (response.ok) {
                        fetchClients();
                        showNotification('Клієнта видалено', 'success');
                    } else {
                        const errorData = await response.text();
                        showNotification(`Не вдалося видалити клієнта: ${errorData}`, 'error');
                    }
                } catch (error) {
                    console.error("Помилка мережі:", error);
                    showNotification('Помилка мережі при спробі видалення', 'error');
                }
            }
        );
    };

    return (
        <Container style={{ marginTop: '2rem' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h4">Клієнти</Typography>
                <Button variant="contained" color="primary" onClick={() => handleOpenModal(null)}>
                    Додати клієнта
                </Button>
            </Box>

            {loading ? ( <CircularProgress /> ) : (
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
                                        <IconButton onClick={() => handleOpenModal(client)}>
                                            <EditIcon />
                                        </IconButton>
                                        <IconButton onClick={() => handleDelete(client.id, `${client.name} ${client.surname}`.trim())}>
                                            <DeleteIcon />
                                        </IconButton>
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