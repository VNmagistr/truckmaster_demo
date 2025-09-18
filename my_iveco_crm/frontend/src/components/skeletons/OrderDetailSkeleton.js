// frontend/src/components/skeletons/OrderDetailSkeleton.js

import React from 'react';
import { Container, Paper, Box, Skeleton, Grid, Divider } from '@mui/material';

export default function OrderDetailSkeleton() {
    return (
        <Container style={{ marginTop: '2rem' }}>
            <Skeleton variant="text" width={120} height={40} sx={{ mb: 2 }} />
            <Paper sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Skeleton variant="text" width="60%" height={48} />
                    <Skeleton variant="rounded" width={80} height={32} sx={{ ml: 2 }} />
                </Box>
                <Skeleton variant="text" width="40%" height={36} sx={{ mb: 2 }} />
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} md={6}>
                        <Skeleton variant="text" width="50%" height={32} />
                        <Skeleton variant="text" width="80%" />
                        <Skeleton variant="text" width="60%" />
                    </Grid>
                    <Grid item xs={12} md={6}>
                        <Skeleton variant="text" width="50%" height={32} />
                        <Skeleton variant="text" width="80%" />
                        <Skeleton variant="text" width="60%" />
                    </Grid>
                </Grid>
                <Divider sx={{ my: 2 }} />
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Skeleton variant="text" width="40%" height={40} />
                    <Skeleton variant="rounded" width={150} height={40} />
                </Box>
                <Box>
                    <Skeleton variant="rounded" width="100%" height={60} sx={{ mt: 1 }} />
                    <Skeleton variant="rounded" width="100%" height={60} sx={{ mt: 1 }} />
                </Box>
            </Paper>
        </Container>
    );
}