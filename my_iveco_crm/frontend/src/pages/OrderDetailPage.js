import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Container, Typography, Box, Paper, CircularProgress, Grid, 
    List, ListItem, ListItemText, Divider, Button, Chip
} from '@mui/material';

const API_URL = 'http://127.0.0.1:8000/api';

export default function OrderDetailPage() {
    const { orderId } = useParams(); // Отримуємо ID з URL
    const navigate = useNavigate();
    const [order, setOrder] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchOrderDetails = async () => {
            setLoading(true);
            try {
                const response = await fetch(`${API_URL}/service-orders/${orderId}/`);
                const data = await response.json();
                setOrder(data);
            } catch (error) {
                console.error("Помилка завантаження деталей замовлення!", error);
            } finally {
                setLoading(false);
            }
        };
        fetchOrderDetails();
    }, [orderId]);

    if (loading) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}><CircularProgress /></Box>;
    }

    if (!order) {
        return <Typography variant="h5" align="center" mt={4}>Замовлення не знайдено</Typography>;
    }

    return (
        <Container style={{ marginTop: '2rem' }}>
            <Button onClick={() => navigate('/orders')} sx={{ mb: 2 }}>
                &larr; Назад до списку
            </Button>
            <Paper sx={{ p: 3 }}>
                <Typography variant="h4" gutterBottom>
                    Замовлення-наряд №{order.id}
                    <Chip label={order.status} color="primary" sx={{ ml: 2 }} />
                </Typography>
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={6}>
                        <Typography variant="h6">Клієнт</Typography>
                        <Typography>{order.client.name} {order.client.surname}</Typography>
                        <Typography color="textSecondary">{order.client.phone}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                        <Typography variant="h6">Автомобіль</Typography>
                        <Typography>{order.truck.specific_model_name} ({order.truck.license_plate})</Typography>
                        <Typography color="textSecondary">WIN-код: {order.truck.last_seven_vin}</Typography>
                    </Grid>
                </Grid>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h5" gutterBottom>Виконані роботи</Typography>
                <List>
                    {order.works && order.works.map((work, index) => (
                        <React.Fragment key={work.id}>
                            <ListItem>
                                <ListItemText 
                                    primary={work.job_description}
                                    secondary={`Вартість: ${work.labor_cost} грн`}
                                />
                            </ListItem>
                            {work.used_parts.length > 0 && (
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
                                </List>
                            )}
                            {index < order.works.length - 1 && <Divider component="li" />}
                        </React.Fragment>
                    ))}
                </List>
            </Paper>
        </Container>
    );
}