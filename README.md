# TruckMaster CRM

CRM system for an Iveco heavy truck service center **"Ital Truck"**.

**Demo:** [http://137.184.31.33](http://137.184.31.33) | **Admin:** [http://137.184.31.33/admin/](http://137.184.31.33/admin/) (admin / admin)

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.11, Django 5, Django REST Framework, PostgreSQL |
| Frontend | React 18, Vite, Ant Design 5, Zustand, Recharts |
| Auth | Simple JWT (separate authorization for staff / clients) |
| Background | Celery + Redis, django-celery-beat |
| Bot | python-telegram-bot (async) |
| Docs | drf-spectacular (OpenAPI / Swagger / ReDoc) |
| PWA | vite-plugin-pwa, Service Worker, offline fallback |
| i18n | react-i18next (UK / EN) |

---

## Modules

TruckMaster is built on a modular architecture — each functional block can be enabled or disabled via the admin panel without changing code.

| Module | Description | Core |
|--------|-------------|:----:|
| **accounts** | Staff authorization (JWT), registration, profile | Yes |
| **clients** | Clients, vehicles, ownership history | Yes |
| **orders** | Service orders, work items, repair photos | Yes |
| **inventory** | Spare parts warehouse, purchases, transfers | -- |
| **invoices** | Invoices, Nova Poshta integration | -- |
| **maintenance** | Scheduled maintenance reminders | -- |
| **cabinet** | Client personal portal | -- |
| **bot** | Telegram bot for clients and admins | -- |
| **appointments** | Online service booking | -- |
| **alpr** | License plate recognition (camera) | -- |

Core modules are always active. Optional modules are toggled in `/admin/core/module/` with dependency checks.

---

## Features

### Clients & Vehicles

- Client card with contacts, notes, linked vehicles
- Truck registry: VIN, license plate, model, Euro standard, transmission type, mileage
- Iveco base model catalog
- Individual feature access settings (portal, bot, notifications)
- Ownership history and license plate changes
- Soft-delete with deletion reason and audit trail
- Client import from XLSX

### Service Orders

- Full lifecycle: Open → In Progress → Done → Closed / Canceled
- Work items in order: price list, hourly rate, mechanic assignment
- Auto-suggest parts from previous orders for the same truck with the same work
- Repair photos (before/after) with bulk upload
- Inline editing of order number and close date
- Automatic closing of orders in "Done" status for over 1 week (Celery)
- Stale order reminders for orders in "In Progress" too long (modal on orders page)
- Soft-delete with mandatory reason
- Status transition audit

### Scheduled Maintenance

- Maintenance intervals per truck: engine oil, gearbox, rear axle, belts, chains
- Two tracking modes: by mileage (km) or by engine hours
- Reference templates by combination (base model + Euro standard + transmission type)
- Maintenance kit: oils (with quantities) + filters (with replacement intervals)
- Auto-fill intervals and kit when adding a vehicle
- Manual template application with full overwrite
- Auto-update of `last_km` on order completion (by work type keywords)
- Snapshot of previous values for rollback capability
- Maintenance reminders with priorities (low / medium / high / critical)
- Configurable reminder rules by mileage and date

### Warehouse & Spare Parts

- Multi-warehouse: retail, wholesale, other
- Product card: article number, barcode, brand, sale price, cost price
- Stock movements: incoming, outgoing, transfer, return, write-off, adjustment
- Stock levels by warehouse with reservations
- Full procurement cycle: order folders → orders → receiving → stocking
- Bulk stocking of all folder items in one request
- Product search by article number with auto-fill of purchase price
- Low stock notifications
- Spare parts usage tracking in orders

### Invoices & Nova Poshta

- Invoice creation with line items for clients
- Delivery types: pickup, shipping
- Nova Poshta API integration: real-time shipment tracking
- Send tracking number to client via Telegram / WhatsApp
- Public tracking by declaration number
- Parts issuance log for drivers

### Telegram Bot

**For clients:**
- Authorization via phone number
- "My vehicles" — submenu with repair history, scheduled maintenance, remaining km to service
- Order status check
- "My shipments" — Nova Poshta shipment tracking
- Maintenance reminder settings
- Weekly mileage request for owners (automatic Celery task)

**For admins:**
- Vehicle and client search
- Upload repair photos to orders (with photo type selection)
- Statistics
- Unknown plates registry (plates searched but not found in database)

**Technical details:**
- Modular handler structure
- All messages logged
- Roles: guest, driver, owner, admin
- Auto-sync of vehicle assignments for owners via signals

### Client Portal

- Separate authorization (JWT) — independent from staff
- Registration with mandatory email verification
- Dashboard with overview
- Client's vehicle list with details
- View orders and repair photos
- Profile and settings
- Access controlled via `ClientFeature`

### Online Service Booking

- Booking with date, time, and service type selection
- Statuses: pending, confirmed, canceled, completed, no-show
- Automatic reminders (hourly Celery task)
- Conversion of booking to service order

### ALPR (License Plate Recognition)

- Integration with entry gate camera
- Automatic matching with vehicle / client / booking database
- Arrival log with confidence level
- Whitelist (ignore service vehicles)
- Telegram notifications to staff chat

### Landing Page (Public)

- Hero section with CTA
- Iveco model gallery (S-Way, X-Way, eDaily, Daily 4x4, S-Way Electric)
- Service advantages
- FAQ with expand/collapse
- Google Places reviews (stars, text, author) — 24h cache
- Contact form with honeypot spam protection
- Map and contacts (multiple operators)

### Additional Features

- **i18n** — full localization in Ukrainian and English (react-i18next)
- **PWA** — install on mobile/desktop, offline support, Service Worker
- **QR / Short Links** — `/go/<slug>/` with click counter
- **Dashboard** — key metrics (clients, vehicles, orders, revenue by month/year), charts
- **Audit** — user action log (create, update, delete, view, export)
- **Module system** — enable/disable features without redeployment

---

## API

Full documentation available after launch:

| URL | Format |
|-----|--------|
| `GET /api/docs/` | Swagger UI |
| `GET /api/redoc/` | ReDoc |
| `GET /api/schema/` | OpenAPI JSON |

### Main Endpoints

```
# Auth
POST   /api/token/                  -- Staff JWT login
POST   /api/token/refresh/          -- Refresh token
POST   /api/cabinet/token/          -- Client JWT login
POST   /api/register/               -- Staff registration
POST   /api/cabinet/register/       -- Client self-registration

# Clients & Trucks
GET/POST      /api/clients/
GET/PUT/DEL   /api/clients/{id}/
GET/POST      /api/trucks/
GET/PUT/DEL   /api/trucks/{id}/

# Orders & Work
GET/POST      /api/orders/
GET/PUT       /api/orders/{id}/
GET           /api/orders/stale_in_progress/
GET/POST      /api/service-works/
GET           /api/service-works/{id}/suggest-parts/
POST          /api/repair-photos/bulk_upload/

# Maintenance
GET/POST      /api/maintenance-intervals/
GET/POST      /api/maintenance-templates/
POST          /api/maintenance-templates/{id}/apply-to-truck/{truck_id}/

# Inventory
GET/POST      /api/inventory/products/
POST          /api/inventory/movements/transfer/
POST          /api/inventory/movements/receive_stock/
POST          /api/inventory/order-folders/{id}/receive_all/
POST          /api/inventory/order-items/{id}/receive/

# Invoices
GET/POST      /api/invoices/
POST          /api/invoices/{id}/send_ttn/
GET           /api/invoices/track/{number}/

# Cabinet
GET           /api/cabinet/me/
GET           /api/cabinet/trucks/
GET           /api/cabinet/orders/

# Bot
GET/PATCH/DEL /api/bot/unknown-plates/
GET           /api/bot/statistics/

# ALPR
POST          /api/alpr/event/
GET/POST      /api/alpr/ignored/
GET           /api/alpr/arrivals/

# Modules
GET           /api/modules/
```

---

## Celery Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `send-daily-reminders` | 09:00 daily | Maintenance reminders for clients |
| `ask-owners-for-mileage` | Mon 10:00 | Request mileage from owners via bot |
| `send-appointment-reminders` | Hourly | Service booking reminders |
| `auto-close-done-orders` | 03:00 daily | Auto-close orders >1 week in DONE |

---

## Project Structure

```
truckmaster/                         # Backend repo
  my_iveco_crm/
    my_iveco_crm/                    # Django project settings
      settings.py
      urls.py
      celery_app.py
    core/                            # Module system (registry, middleware)
    accounts/                        # Staff auth, Google Places, contacts
    clients/                         # Client, Truck, IvecoBaseModel
    orders/                          # ServiceOrder, ServiceWork, Maintenance
    inventory/                       # Warehouse, Product, StockMovement
    invoices/                        # Invoice, Nova Poshta integration
    cabinet/                         # Client portal (separate JWT)
    maintenance/                     # ServiceReminder, MaintenanceRule
    bot/                             # Telegram bot (handlers, keyboards, queries)
    appointments/                    # Online booking
    alpr/                            # License plate recognition
    shortlinks/                      # QR / short URL redirects

truckmaster_frontend/                # Frontend repo
  src/
    layouts/                         # MainLayout, AuthLayout, CabinetLayout
    pages/
      welcome/                       # Public landing page
      auth/                          # Staff login
      dashboard/                     # Dashboard with metrics & charts
      orders/                        # Orders CRUD
      clients/                       # Clients CRUD (TBD)
      trucks/                        # Trucks CRUD
      inventory/                     # Stock, purchases, wholesale
      invoices/                      # Invoices + Nova Poshta tracking
      bot/                           # Bot users, messages, unknown plates
      alpr/                          # ALPR arrivals & ignored list
      appointments/                  # Booking management
      cabinet/                       # Client portal (9 pages)
      maintenance/                   # Templates & reminders
    store/                           # Zustand (authStore, cabinetAuthStore, modulesStore)
    api/                             # Axios instances (staff + cabinet)
    locales/                         # i18n (uk.json, en.json)
    assets/                          # Logo, truck images
```

---

## Quick Start

### Backend

```bash
cd my_iveco_crm
python -m venv ../venv
source ../venv/bin/activate        # Windows: ..\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Edit with your settings
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend

```bash
cd truckmaster_frontend
npm install
echo "VITE_API_URL=http://localhost:8000/api" > .env
npm run dev
```

### Telegram Bot

```bash
cd my_iveco_crm
python manage.py runbot
```

### Environment Variables

```env
# Required
SECRET_KEY=...
DATABASE_URL=postgres://user:pass@localhost:5432/truckmaster
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173

# Celery
REDIS_URL=redis://localhost:6379/0

# Telegram Bot
TELEGRAM_BOT_TOKEN=...

# Optional integrations
GOOGLE_PLACES_API_KEY=...
ALPR_API_KEY=...
ALPR_STAFF_CHAT_ID=...

# Email (for client cabinet verification)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=...
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL=...
FRONTEND_URL=https://your-domain.com
```

---

## Design System

| Token | Value | Usage |
|-------|-------|-------|
| Primary | `#f5c518` | Yellow accent, buttons, active states |
| Text | `#1a1a1a` | Primary text, sidebar background |
| Background | `#ffffff` / `#f7f7f7` | Page backgrounds |
| Card accent | `border-top: 4px solid #f5c518` | Cards and forms |
| Header | White + `box-shadow: 0 2px 0 0 #f5c518` | Top navigation |
| Sidebar | Dark `#1a1a1a`, active item yellow | Side navigation |

---

## Changelog

### v2.13 -- 2026-05-12
- Auto-suggest parts from previous orders when adding work
- Search by license plate and pagination in maintenance intervals admin/API
- Stale orders reminder moved to Orders page (shows on every visit)

### v2.12 -- 2026-05-11
- Full i18n localization (Ukrainian / English)
- Honeypot spam protection for contact form
- Maintenance template table width fix

### v2.11
- Maintenance interval templates with oils and filters
- Template-based maintenance kit on frontend
- Auto-fill intervals from template
- Tracking mode (mileage / engine hours)
- Engine hours support for Trakker

### v2.10
- Work cost calculation fix
- Gearbox/automatic gearbox differentiation in maintenance works

### v2.9
- StockService, ALPR debounce, async Telegram messages
- JWT 15min access token
- Client import from XLSX
- Bot refactoring to modular handlers
- N+1 fix in update_total_cost

---

## License

Private. All rights reserved.
