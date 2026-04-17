"""Спільні утиліти для bot handlers."""

_AWAITING_KEYS = (
    'awaiting_mileage_truck_id',
    'awaiting_maintenance_mileage_truck_id',
    'awaiting_truck',
    'awaiting_client',
    'awaiting_order',
    'awaiting_photo_order',
)


def clear_awaiting_states(user_data: dict) -> None:
    """Скидає всі стани очікування введення перед встановленням нового."""
    for key in _AWAITING_KEYS:
        user_data.pop(key, None)
