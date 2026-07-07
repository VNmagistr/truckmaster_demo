# TruckMaster — Backend

Django REST API for an Iveco heavy truck service center CRM ("Ital Truck").

## Stack

- Python 3.12 / Django 5.x
- Django REST Framework + drf-spectacular (OpenAPI)
- PostgreSQL (production) / SQLite (development)
- Celery + Redis (background tasks)
- JWT authentication (SimpleJWT)

## Local Setup

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env      # fill in variables
python manage.py migrate
python manage.py runserver
```

## API Documentation

| URL | Description |
|-----|-------------|
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | OpenAPI JSON |

## Modules

| Module | Type | Description |
|--------|------|-------------|
| `accounts` | core | Accounts, Google Reviews |
| `users` | core | Staff |
| `clients` | core | Clients and their vehicles |
| `orders` | core | Service orders, maintenance intervals |
| `inventory` | optional | Spare parts warehouse |
| `invoices` | optional | Invoices + Nova Poshta |
| `cabinet` | optional | Client personal portal |
| `bot` | optional | Telegram bot |
| `appointments` | optional | Service booking |
| `alpr` | optional | License plate recognition |
| `maintenance` | optional | Maintenance reminders |

Toggle modules: `/admin/core/module/`

## Main Endpoints

```
POST   /api/token/                        — Staff auth
POST   /api/token/refresh/

GET    /api/clients/
GET    /api/orders/
GET    /api/inventory/products/
GET    /api/inventory/warehouses/
POST   /api/inventory/movements/transfer/       — Transfer between warehouses
POST   /api/inventory/movements/receive_stock/  — Incoming stock
GET    /api/inventory/order-folders/            — Order lists
GET    /api/invoices/
GET    /api/appointments/
GET    /api/alpr/arrivals/
GET    /api/modules/
```

## Celery Tasks

| Task | Schedule |
|------|----------|
| Daily reminders for clients | 09:00 |
| Request mileage from owners | Mon 10:00 |
| Booking reminders | Hourly |
| Auto-close orders (>7 days in DONE) | 03:00 |

## Changelog

### v2.6 — 2026-04-02
- **Inventory / Wholesale**: `warehouse_type` field (retail/wholesale/other) on warehouses; incoming stock to any warehouse (`receive_stock`); transfer between warehouses (`transfer`) with automatic `Product.current_stock` recalculation
- **Inventory / Order**: `OrderFolder` + `OrderItem` models; bulk-toggle `mark_all_ordered`; individual item toggle
- **Product search**: `iendswith` → `icontains` for article number (searches any part)

### v2.5 — 2026-03-23
- Client personal portal (cabinet app)
- Client email verification
- ALPR — license plate recognition (paused)

### v2.4
- Telegram bot: Nova Poshta shipment tracking
- Invoices: auto-load tracking number status

### v2.3
- Module system (toggle in admin)
- Truck maintenance intervals

### v2.2
- Spare parts warehouse (inventory app)
- Stock movements, stock levels by warehouse

### v2.1
- Invoices and Nova Poshta integration

### v2.0
- Service orders, work items, spare parts
- Telegram/WhatsApp notifications

### v1.x
- Clients, vehicles, basic authorization
