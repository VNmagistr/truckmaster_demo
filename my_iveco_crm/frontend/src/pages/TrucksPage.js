import React, { useState, useEffect } from 'react';
import {
    Container, Typography, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Paper, Button, Box, Dialog, DialogTitle, 
    DialogContent, DialogActions, TextField, Select, MenuItem, 
    FormControl, InputLabel, IconButton, CircularProgress
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';

const API_URL = 'http://127.0.0.1:8000/api';

export default function TrucksPage() { 
    const [trucks, setTrucks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [open, setOpen] = useState(false);
    const [clients, setClients] = useState([]);
    const [baseModels, setBaseModels] = useState([]);
    const [editingTruck, setEditingTruck] = useState(null);
    const [formData, setFormData] = useState({});
    
    // НОВЕ: Стан для індикатора завантаження даних для модального вікна
    const [modalLoading, setModalLoading] = useState(false);

    const fetchData = async () => {
        setLoading(true);
        try {
            // Завантажуємо довідники один раз при завантаженні сторінки
            const [clientsRes, modelsRes] = await Promise.all([
                fetch(`${API_URL}/clients/`),
                fetch(`${API_URL}/base-models/`)
            ]);
            const clientsData = await clientsRes.json();
            const modelsData = await modelsRes.json();
            setClients(clientsData);
            setBaseModels(modelsData);
            // Завантажуємо список вантажівок
            await fetchTrucks();
        } catch (error) { console.error("Помилка завантаження довідників!", error); } 
        finally { setLoading(false); }
    };

    const fetchTrucks = async () => {
        try {
            const trucksRes = await fetch(`${API_URL}/trucks/`);
            const trucksData = await trucksRes.json();
            setTrucks(trucksData);
        } catch(error) { console.error("Помилка завантаження вантажівок!", error); }
    };

    useEffect(() => { fetchData(); }, []);

    // ЗМІНЕНО: Функція тепер асинхронна і завантажує дані перед відкриттям
    const handleOpenModal = async (truck = null) => {
        setEditingTruck(truck);
        if (truck) {
            // Якщо редагуємо, показуємо індикатор завантаження і робимо запит
            setModalLoading(true);
            setOpen(true);
            try {
                const response = await fetch(`${API_URL}/trucks/${truck.id}/`);
                const truckDetails = await response.json();
                setFormData(truckDetails); // Заповнюємо форму повними даними з API
            } catch (error) {
                console.error("Помилка завантаження деталей вантажівки!", error);
            } finally {
                setModalLoading(false);
            }
        } else {
            // Якщо створюємо, просто відкриваємо з порожніми даними
            setFormData({
                specific_model_name: '', license_plate: '', full_vin: '',
                year_of_manufacture: new Date().getFullYear(), current_mileage: '', client: '',
                base_model: '', transmission_type: 'manual', emission_standard: 'unknown',
            });
            setOpen(true);
        }
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
                fetchTrucks(); // Оновлюємо ТІЛЬКИ список вантажівок
            } else {
                const errorData = await response.json();
                alert(`Помилка: ${JSON.stringify(errorData)}`);
            }
        } catch (error) { console.error("Помилка мережі:", error); }
    };

    const handleDelete = async (id) => {
        if (window.confirm("Ви впевнені, що хочете видалити цю вантажівку?")) {
            try {
                const response = await fetch(`${API_URL}/trucks/${id}/`, { method: 'DELETE' });
                if (response.ok) {
                    fetchTrucks(); // Оновлюємо ТІЛЬКИ список вантажівок
                } else { alert('Не вдалося видалити вантажівку.'); }
            } catch (error) { console.error("Помилка мережі:", error); }
        }
    };

    return (
        <Container style={{ marginTop: '2rem' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h4">Вантажівки</Typography>
                <Button variant="contained" color="primary" onClick={() => handleOpenModal(null)}>
                    Додати вантажівку
                </Button>
            </Box>

            {loading ? ( <CircularProgress /> ) : (
                <TableContainer component={Paper}>
                    {/* ...Таблиця залишається без змін... */}
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell><b>Модель</b></TableCell>
                                <TableCell><b>Держ. номер</b></TableCell>
                                <TableCell><b>Власник</b></TableCell>
                                <TableCell><b>Пробіг (км)</b></TableCell>
                                <TableCell><b>Стандарт</b></TableCell>
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
                                    <TableCell>{truck.emission_standard}</TableCell>
                                    <TableCell align="right">
                                        <IconButton onClick={() => handleOpenModal(truck)}>
                                            <EditIcon />
                                        </IconButton>
                                        <IconButton onClick={() => handleDelete(truck.id)}>
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
                    {/* ЗМІНЕНО: Показуємо завантажувач, поки отримуємо деталі */}
                    {modalLoading ? <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box> : (
                        <>
                            {/* Поля форми тепер також включають transmission_type і emission_standard */}
                            <TextField autoFocus margin="dense" name="specific_model_name" label="Точна назва моделі" type="text" fullWidth variant="standard" value={formData.specific_model_name || ''} onChange={handleInputChange} />
                            <TextField margin="dense" name="license_plate" label="Державний номер" type="text" fullWidth variant="standard" value={formData.license_plate || ''} onChange={handleInputChange} />
                            <TextField margin="dense" name="full_vin" label="Повний VIN-код" type="text" fullWidth variant="standard" value={formData.full_vin || ''} onChange={handleInputChange} />
                            <TextField margin="dense" name="year_of_manufacture" label="Рік випуску" type="number" fullWidth variant="standard" value={formData.year_of_manufacture || ''} onChange={handleInputChange} />
                            <TextField margin="dense" name="current_mileage" label="Поточний пробіг" type="number" fullWidth variant="standard" value={formData.current_mileage || ''} onChange={handleInputChange} />
                            
                            <FormControl fullWidth margin="dense" variant="standard">
                                <InputLabel>Клієнт</InputLabel>
                                <Select name="client" value={formData.client || ''} onChange={handleInputChange}>
                                    {clients.map(client => <MenuItem key={client.id} value={client.id}>{client.name} {client.surname}</MenuItem>)}
                                </Select>
                            </FormControl>

                            <FormControl fullWidth margin="dense" variant="standard">
                                <InputLabel>Базова модель</InputLabel>
                                <Select name="base_model" value={formData.base_model || ''} onChange={handleInputChange}>
                                    {baseModels.map(model => <MenuItem key={model.id} value={model.id}>{model.name}</MenuItem>)}
                                </Select>
                            </FormControl>

                            <FormControl fullWidth margin="dense" variant="standard">
                                <InputLabel>Тип КПП</InputLabel>
                                <Select name="transmission_type" value={formData.transmission_type || 'manual'} onChange={handleInputChange}>
                                    <MenuItem value="manual">Механічна</MenuItem>
                                    <MenuItem value="automatic">Автоматична</MenuItem>
                                    <MenuItem value="robot">Робот</MenuItem>
                                </Select>
                            </FormControl>

                            <FormControl fullWidth margin="dense" variant="standard">
                                <InputLabel>Стандарт викидів</InputLabel>
                                <Select name="emission_standard" value={formData.emission_standard || 'unknown'} onChange={handleInputChange}>
                                    <MenuItem value="unknown">Не вказано</MenuItem>
                                    <MenuItem value="euro3">Євро-3</MenuItem>
                                    <MenuItem value="euro4">Євро-4</MenuItem>
                                    <MenuItem value="euro5">Євро-5</MenuItem>
                                    <MenuItem value="euro6">Євро-6</MenuItem>
                                </Select>
                            </FormControl>
                        </>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseModal}>Скасувати</Button>
                    <Button onClick={handleFormSubmit} disabled={modalLoading}>Зберегти</Button>
                </DialogActions>
            </Dialog>
        </Container>
    );
}