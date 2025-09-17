import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Drawer, List, ListItem, ListItemText, Toolbar, Box, Button, Typography } from '@mui/material';
import { useAuth } from '../context/AuthContext';

const drawerWidth = 240;

export default function Navbar() {
    const { user, logoutUser } = useAuth();

    return (
        <Drawer variant="permanent" sx={{ width: drawerWidth, flexShrink: 0, [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' }, }}>
            <Toolbar />
            <Box sx={{ overflow: 'auto', display: 'flex', flexDirection: 'column', height: '100%' }}>
                <List sx={{ flexGrow: 1 }}>
                    <ListItem button component={RouterLink} to="/trucks"><ListItemText primary="Вантажівки" /></ListItem>
                    <ListItem button component={RouterLink} to="/clients"><ListItemText primary="Клієнти" /></ListItem>
                    <ListItem button component={RouterLink} to="/orders"><ListItemText primary="Замовлення" /></ListItem>
                </List>
                <Box sx={{ p: 2 }}>
                    <Typography variant="body2">Увійшли як: {user?.username}</Typography>
                    <Button variant="contained" fullWidth onClick={logoutUser} sx={{ mt: 1 }}>
                        Вийти
                    </Button>
                </Box>
            </Box>
        </Drawer>
    );
}