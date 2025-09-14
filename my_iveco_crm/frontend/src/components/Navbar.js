import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Drawer, List, ListItem, ListItemText, Toolbar, Box } from '@mui/material';

const drawerWidth = 240;

export default function Navbar() {
    return (
        <Drawer
            variant="permanent"
            sx={{
                width: drawerWidth,
                flexShrink: 0,
                [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
            }}
        >
            <Toolbar />
            <Box sx={{ overflow: 'auto' }}>
                <List>
                    <ListItem button component={RouterLink} to="/trucks">
                        <ListItemText primary="Вантажівки" />
                    </ListItem>
                    <ListItem button component={RouterLink} to="/clients">
                        <ListItemText primary="Клієнти" />
                    </ListItem>
                     <ListItem button component={RouterLink} to="/orders">
                        <ListItemText primary="Замовлення" />
                    </ListItem>
                </List>
            </Box>
        </Drawer>
    );
}