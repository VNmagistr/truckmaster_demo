import React, { createContext, useState, useContext, useCallback } from 'react';
import ConfirmationDialog from '../components/ConfirmationDialog'; // Ми імпортуємо його тут

const ConfirmationContext = createContext();

export const useConfirmation = () => {
    return useContext(ConfirmationContext);
};

export const ConfirmationProvider = ({ children }) => {
    const [options, setOptions] = useState({
        open: false,
        title: '',
        message: '',
        onConfirm: () => {},
    });

    const confirm = useCallback((title, message, onConfirm) => {
        setOptions({
            open: true,
            title,
            message,
            onConfirm,
        });
    }, []);

    const handleClose = () => {
        setOptions((prev) => ({ ...prev, open: false }));
    };

    const handleConfirm = () => {
        if (options.onConfirm) {
            options.onConfirm();
        }
        handleClose();
    };

    const value = { confirm };

    return (
        <ConfirmationContext.Provider value={value}>
            {children}
            <ConfirmationDialog
                open={options.open}
                onClose={handleClose}
                onConfirm={handleConfirm}
                title={options.title}
                message={options.message}
            />
        </ConfirmationContext.Provider>
    );
};