import React, { useState, useEffect } from 'react';
import {
    Container, Typography, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Paper, AppBar, Toolbar, Button, Box,
    Dialog, DialogTitle, DialogContent, DialogActions, TextField,
    Select, MenuItem, FormControl, InputLabel
} from '@mui/material';

// URL нашого API
const API_URL = 'http://127.0.0.1:8000/api';

function App() {
    const [trucks, setTrucks] = useState([]);
    const [loading, setLoading] = useState(true);
    // Стан для керування модальним вікном
    const [open, setOpen] = useState(false);

    // Стани для довідників, які ми завантажимо для випадаючих списків
    const [clients, setClients] = useState([]);
    const [baseModels, setBaseModels] = useState([]);

    // Стан для даних нової вантажівки
    const [newTruck, setNewTruck] = useState({
        specific_model_name: '',
        license_plate: '',
        full_vin: '',
        year_of_manufacture: '',
        current_mileage: '',
        client: '',
        base_model: '',
        transmission_type: 'manual',
        emission_standard: 'unknown',
    });

    // Функція для завантаження даних
    const fetchData = async () => {
        setLoading(true);
        try {
            const [trucksRes, clientsRes, modelsRes] = await Promise.all([
                fetch(`${API_URL}/trucks/`),
                fetch(`${API_URL}/clients/`),
                fetch(`${API_URL}/base-models/`)
            ]);
            const trucksData = await trucksRes.json();
            const clientsData = await clientsRes.json();
            const modelsData = await modelsRes.json();

            setTrucks(trucksData);
            setClients(clientsData);
            setBaseModels(modelsData);
        } catch (error) {
            console.error("Помилка завантаження даних!", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleClickOpen = () => setOpen(true);
    const handleClose = () => setOpen(false);

    // Функція, що оновлює стан нової вантажівки при зміні полів форми
    const handleInputChange = (event) => {
        const { name, value } = event.target;
        setNewTruck(prevState => ({ ...prevState, [name]: value }));
    };

    // Функція для відправки даних на сервер
    const handleFormSubmit = async () => {
        try {
            const response = await fetch(`${API_URL}/trucks/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newTruck),
            });
            if (response.ok) {
                handleClose(); // Закриваємо вікно
                fetchData(); // Оновлюємо список вантажівок
            } else {
                const errorData = await response.json();
                console.error("Помилка при створенні вантажівки:", errorData);
                alert(`Помилка: ${JSON.stringify(errorData)}`);
            }
        } catch (error) {
            console.error("Помилка мережі:", error);
        }
    };

    return (
        <div>
            <AppBar position="static">
                <Toolbar>
                    <Typography variant="h6">CRM для СТО Iveco</Typography>
                </Toolbar>
            </AppBar>

            <Container style={{ marginTop: '2rem' }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h4">Список вантажівок</Typography>
                    {/* Наша нова кнопка */}
                    <Button variant="contained" color="primary" onClick={handleClickOpen}>
                        Додати вантажівку
                    </Button>
                </Box>

                {loading ? ( <Typography>Завантаження даних...</Typography> ) : (
                    <TableContainer component={Paper}>
                        <Table>
                            <TableHead>
                                <TableRow>
                                    <TableCell><b>Модель</b></TableCell>
                                    <TableCell><b>Держ. номер</b></TableCell>
                                    <TableCell><b>Власник</b></TableCell>
                                    <TableCell><b>Пробіг (км)</b></TableCell>
                                    <TableCell><b>Стандарт</b></TableCell>
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
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                )}
            </Container>

            {/* Модальне вікно для створення нової вантажівки */}
            <Dialog open={open} onClose={handleClose}>
                <DialogTitle>Додати нову вантажівку</DialogTitle>
                <DialogContent>
                    <TextField autoFocus margin="dense" name="specific_model_name" label="Точна назва моделі" type="text" fullWidth variant="standard" onChange={handleInputChange} />
                    <TextField margin="dense" name="license_plate" label="Державний номер" type="text" fullWidth variant="standard" onChange={handleInputChange} />
                    <TextField margin="dense" name="full_vin" label="Повний VIN-код" type="text" fullWidth variant="standard" onChange={handleInputChange} />
                    <TextField margin="dense" name="year_of_manufacture" label="Рік випуску" type="number" fullWidth variant="standard" onChange={handleInputChange} />
                    <TextField margin="dense" name="current_mileage" label="Поточний пробіг" type="number" fullWidth variant="standard" onChange={handleInputChange} />

                    <FormControl fullWidth margin="dense" variant="standard">
                        <InputLabel>Клієнт</InputLabel>
                        <Select name="client" value={newTruck.client} onChange={handleInputChange}>
                            {clients.map(client => <MenuItem key={client.id} value={client.id}>{client.name} {client.surname}</MenuItem>)}
                        </Select>
                    </FormControl>

                    <FormControl fullWidth margin="dense" variant="standard">
                        <InputLabel>Базова модель</InputLabel>
                        <Select name="base_model" value={newTruck.base_model} onChange={handleInputChange}>
                            {baseModels.map(model => <MenuItem key={model.id} value={model.id}>{model.name}</MenuItem>)}
                        </Select>
                    </FormControl>

                    {/* Додайте інші поля (transmission_type, emission_standard) аналогічно, якщо потрібно */}

                </DialogContent>
                <DialogActions>
                    <Button onClick={handleClose}>Скасувати</Button>
                    <Button onClick={handleFormSubmit}>Зберегти</Button>
                </DialogActions>
            </Dialog>
        </div>
    );
}

export default App;