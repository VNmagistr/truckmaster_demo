import React, { useState, useEffect, useCallback } from 'react';
import {
    Container, Typography, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Paper, Button, Box, Dialog, DialogTitle, 
    DialogContent, DialogActions, TextField, Select, MenuItem, 
    FormControl, InputLabel, IconButton, CircularProgress
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { useNotification } from '../context/NotificationContext';
import { useConfirmation } from '../context/ConfirmationContext';

const API_URL = 'http://127.0.0.1:8000/api';

export default function TrucksPage() {
    const { showNotification } = useNotification();
    const { confirm } = useConfirmation();

    const [trucks, setTrucks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [open, setOpen] = useState(false);
    const [editingTruck, setEditingTruck] = useState(null);
    const [formData, setFormData] = useState({});
    
    // Довідники для форми
    const [clients, setClients] = useState([]);
    const [baseModels, setBaseModels] = useState([]);

    const fetchData = useCallback(async () => {
    try {
        const [trucksRes, clientsRes, modelsRes] = await Promise.all([
            fetch(`${API_URL}/trucks/`),
            fetch(`${API_URL}/clients/`),
            fetch(`${API_URL}/base-models/`)
        ]);

        const trucksData = await trucksRes.json();
        const clientsData = await clientsRes.json();
        const modelsData = await modelsRes.json();

        // --- НОВА НАДІЙНА ЛОГІКА ---
        // Перевіряємо, чи є поле .results і чи це масив (для пагінації)
        if (trucksData && Array.isArray(trucksData.results)) {
            setTrucks(trucksData.results);
        } 
        // Інакше перевіряємо, чи це просто масив
        else if (Array.isArray(trucksData)) {
            setTrucks(trucksData);
        }

        // Повторюємо ту ж логіку для клієнтів
        if (clientsData && Array.isArray(clientsData.results)) {
            setClients(clientsData.results);
        } else if (Array.isArray(clientsData)) {
            setClients(clientsData);
        }

        // І для моделей
        if (modelsData && Array.isArray(modelsData.results)) {
            setBaseModels(modelsData.results);
        } else if (Array.isArray(modelsData)) {
            setBaseModels(modelsData);
        }
        // --- КІНЕЦЬ НОВОЇ ЛОГІКИ ---

    } catch (error) {
        console.error("Помилка завантаження даних!", error);
        showNotification("Помилка завантаження даних!", 'error');
    } finally {
        setLoading(false);
    }
}, [showNotification]);

    useEffect(() => {
        setLoading(true);
        fetchData();
    }, [fetchData]);

    const handleOpenModal = async (truck = null) => {
        setEditingTruck(truck);
        if (truck) {
            try {
                const response = await fetch(`${API_URL}/trucks/${truck.id}/`);
                const truckDetails = await response.json();
                setFormData(truckDetails);
            } catch (error) {
                showNotification("Помилка завантаження деталей вантажівки!", 'error');
            }
        } else {
            setFormData({
                specific_model_name: '', license_plate: '', full_vin: '',
                year_of_manufacture: new Date().getFullYear(), current_mileage: '', client: '',
                base_model: '', transmission_type: 'manual', emission_standard: 'unknown',
            });
        }
        setOpen(true);
    };

    const handleCloseModal = () => setOpen(false);

    const handleInputChange = (event) => {
        const { name, value } = event.target;
        setFormData(prevState => ({ ...prevState, [name]: value }));
    };

    const handleFormSubmit = async () => {
        const method = editingTruck ? 'PUT' : 'POST';
        const url = editingTruck ? `${API_URL}/trucks/${editingTruck.id}/` : `${API_URL}/trucks/`;
        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json', },
                body: JSON.stringify(formData),
            });
            if (response.ok) {
                handleCloseModal();
                fetchData();
                showNotification(editingTruck ? 'Вантажівку оновлено!' : 'Вантажівку створено!', 'success');
            } else {
                const errorData = await response.json();
                showNotification(`Помилка: ${JSON.stringify(errorData)}`, 'error');
            }
        } catch (error) {
            console.error("Помилка мережі:", error);
            showNotification('Помилка мережі', 'error');
        }
    };

    const handleDelete = (id, truckName) => {
        confirm(
            'Підтвердити видалення',
            `Ви впевнені, що хочете видалити вантажівку "${truckName}"?`,
            async () => {
                try {
                    const response = await fetch(`${API_URL}/trucks/${id}/`, { method: 'DELETE' });
                    if (response.ok) {
                        fetchData();
                        showNotification('Вантажівку видалено', 'success');
                    } else {
                        const errorData = await response.text();
                        showNotification(`Не вдалося видалити: ${errorData}`, 'error');
                    }
                } catch (error) {
                    console.error("Помилка мережі:", error);
                    showNotification('Помилка мережі при видаленні', 'error');
                }
            }
        );
    };

    return (
        <Container style={{ marginTop: '2rem' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h4">Вантажівки</Typography>
                <Button variant="contained" color="primary" onClick={() => handleOpenModal(null)}>
                    Додати вантажівку
                </Button>
            </Box>

            {loading ? <CircularProgress /> : (
                <TableContainer component={Paper}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell><b>Модель</b></TableCell>
                                <TableCell><b>Держ. номер</b></TableCell>
                                <TableCell><b>Власник</b></TableCell>
                                <TableCell><b>Пробіг (км)</b></TableCell>
                                <TableCell align="right"><b>Дії</b></TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {trucks.map((truck) => (
                                <TableRow key={truck.id}>
                                    <TableCell>{truck.specific_model_name}</TableCell>
                                    <TableCell>{truck.license_plate}</TableCell>
                                    <TableCell>{truck.client}</TableCell>
                                    <TableCell>{truck.current_mileage}</TableCell>
                                    <TableCell align="right">
                                        <IconButton onClick={() => handleOpenModal(truck)}>
                                            <EditIcon />
                                        </IconButton>
                                        <IconButton onClick={() => handleDelete(truck.id, `${truck.specific_model_name} (${truck.license_plate})`)}>
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
                <DialogTitle>{editingTruck ? 'Редагувати вантажівку' : 'Додати нову вантажівку'}</DialogTitle>
                <DialogContent>
                    <TextField autoFocus margin="dense" name="specific_model_name" label="Точна назва моделі" type="text" fullWidth variant="standard" value={formData.specific_model_name || ''} onChange={handleInputChange} />
                    <TextField margin="dense" name="license_plate" label="Державний номер" type="text" fullWidth variant="standard" value={formData.license_plate || ''} onChange={handleInputChange} />
                    <TextField margin="dense" name="full_vin" label="Повний VIN-код" type="text" fullWidth variant="standard" value={formData.full_vin || ''} onChange={handleInputChange} />
                    <TextField margin="dense" name="year_of_manufacture" label="Рік випуску" type="number" fullWidth variant="standard" value={formData.year_of_manufacture || ''} onChange={handleInputChange} />
                    <TextField margin="dense" name="current_mileage" label="Поточний пробіг" type="number" fullWidth variant="standard" value={formData.current_mileage || ''} onChange={handleInputChange} />
                    <FormControl fullWidth margin="dense" variant="standard"><InputLabel>Клієнт</InputLabel><Select name="client" value={formData.client || ''} onChange={handleInputChange}>{clients.map(client => <MenuItem key={client.id} value={client.id}>{client.name} {client.surname}</MenuItem>)}</Select></FormControl>
                    <FormControl fullWidth margin="dense" variant="standard"><InputLabel>Базова модель</InputLabel><Select name="base_model" value={formData.base_model || ''} onChange={handleInputChange}>{baseModels.map(model => <MenuItem key={model.id} value={model.id}>{model.name}</MenuItem>)}</Select></FormControl>
                    <FormControl fullWidth margin="dense" variant="standard"><InputLabel>Тип КПП</InputLabel><Select name="transmission_type" value={formData.transmission_type || 'manual'} onChange={handleInputChange}><MenuItem value="manual">Механічна</MenuItem><MenuItem value="automatic">Автоматична</MenuItem><MenuItem value="robot">Робот</MenuItem></Select></FormControl>
                    <FormControl fullWidth margin="dense" variant="standard"><InputLabel>Стандарт викидів</InputLabel><Select name="emission_standard" value={formData.emission_standard || 'unknown'} onChange={handleInputChange}><MenuItem value="unknown">Не вказано</MenuItem><MenuItem value="euro3">Євро-3</MenuItem><MenuItem value="euro4">Євро-4</MenuItem><MenuItem value="euro5">Євро-5</MenuItem><MenuItem value="euro6">Євро-6</MenuItem></Select></FormControl>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseModal}>Скасувати</Button>
                    <Button onClick={handleFormSubmit}>Зберегти</Button>
                </DialogActions>
            </Dialog>
        </Container>
    );
}