import React from 'react';
import { Box, Typography, Button, Grid, Container, AppBar, Toolbar, IconButton } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import FacebookIcon from '@mui/icons-material/Facebook';
import InstagramIcon from '@mui/icons-material/Instagram';
import YouTubeIcon from '@mui/icons-material/YouTube';
import heroCarImage from '../assets/Sway.png'; // Переконайтесь, що назва файлу правильна

export default function HomePage() {
    return (
        <Box>
            {/* Шапка для головної сторінки */}
            <AppBar position="static" color="transparent" elevation={0} sx={{ padding: '0 5%' }}>
                <Toolbar>
                    <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
                        WELCOME TO TRUCKMASTER
                    </Typography>
                    {/* <Button color="inherit">About us</Button>
                    <Button color="inherit">Cars of the month</Button>
                    <Button color="inherit">Pricing</Button> */}
                    <Button color="inherit" component={RouterLink} to="/trucks">
                       Our CRM
                    </Button>
                    <Box sx={{ flexGrow: 1, textAlign: 'right' }}>
                        <IconButton><FacebookIcon sx={{ color: '#f0c419' }} /></IconButton>
                        <IconButton><InstagramIcon sx={{ color: '#f0c419' }} /></IconButton>
                        <IconButton><YouTubeIcon sx={{ color: '#f0c419' }} /></IconButton>
                    </Box>
                </Toolbar>
            </AppBar>

            {/* Головна секція */}
            <Box sx={{ backgroundColor: 'white', py: 8 }}>
                <Container>
                    <Grid container alignItems="center" spacing={4}>
                        <Grid item xs={12} md={6}>
                            
                            <Typography variant="h1" sx={{ fontWeight: 'bold', fontSize: { xs: '4rem', md: '6rem' }, color: '#f0c419', lineHeight: 1.1 }}>
                                CAR
                            </Typography>
                            <Typography variant="h1" sx={{ fontWeight: 'bold', fontSize: { xs: '4rem', md: '6rem' }, color: '#f0c419', lineHeight: 1.1, mb: 4 }}>
                                RENTAL
                            </Typography>
                            <Box>
                                <Button variant="contained" size="large" sx={{ mr: 2, borderRadius: '20px', px: 4 }}>
                                    Learn More
                                </Button>
                                <Button variant="text" size="large" sx={{ color: '#f0c419', fontWeight: 'bold' }}>
                                    Pricing &gt;
                                </Button>
                            </Box>
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Box component="img" src={heroCarImage} alt="Car" sx={{ width: '100%', height: 'auto' }}/>
                        </Grid>
                    </Grid>
                </Container>
            </Box>
        </Box>
    );
}