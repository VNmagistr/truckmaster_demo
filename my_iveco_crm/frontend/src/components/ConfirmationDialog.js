import React from 'react';
import { Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle } from '@mui/material';

export default function ConfirmationDialog({ open, onClose, onConfirm, title, message }) {
    return (
        <Dialog open={open} onClose={onClose}>
            <DialogTitle>{title}</DialogTitle>
            <DialogContent>
                <DialogContentText>{message}</DialogContentText>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Скасувати</Button>
                <Button onClick={onConfirm} autoFocus color="primary">
                    Підтвердити
                </Button>
            </DialogActions>
        </Dialog>
    );
}