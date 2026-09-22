# TruckMaster CRM

CRM system for an Iveco heavy truck service center **"Ital Truck"**.

**Production:** [https://ital-truck.com.ua](https://ital-truck.com.ua) | **API:** [https://api.ital-truck.com.ua](https://api.ital-truck.com.ua)

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

- Client card with contacts, notes, linked vehicles; internal notes visible in order detail
- Truck registry: VIN, license plate, model, Euro standard, transmission type, mileage; internal notes visible in order detail
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
- **QR Codes** — `/go/<slug>/` short links with click counter, QR generation and download from admin panel, enable/disable toggle from CRM frontend (disabled codes show a stub page)
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
POST          /api/orders/{id}/apply_maintenance_set/
GET           /api/orders/{id}/maintenance-countdown/
GET           /api/orders/last-mileage/

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

# Backups
GET/POST      /api/backups/
GET           /api/backups/{filename}/download/
DELETE        /api/backups/{filename}/
POST          /api/backups/restore/

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

# QR Codes (Short Links)
GET           /api/shortlinks/
POST          /api/shortlinks/{id}/toggle/

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
    shortlinks/                      # QR codes with short URL redirects

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

### v2.25 -- 2026-09-22
- **Fix belts maintenance keyword matching**: `apply_maintenance_set` with `belts` category failed to find WorkPrice, MaintenanceRule, and kit filters because keyword `'ремен'` does not match Ukrainian word form `'ремнів'`; added `'ремн'` as universal substring, added `'ролик'` to WorkPrice search, and fixed category label to "Заміна ремнів, роликів"

### v2.24 -- 2026-09-21
- **Ownership history on truck detail page**: truck detail API now returns `ownership_history` (previous owners, license plates, change dates) as nested data; frontend displays it in a new "Ownership history" tab with linked client names and formatted timestamps

### v2.23 -- 2026-09-21
- **Fix maintenance countdown showing both KPP and AKPP rows**: order detail maintenance table now uses `truck.transmission_type` as the primary source for determining gearbox type, showing only the relevant row (КПП or АКПП); falls back to interval-based detection only when transmission type is not set on the truck profile

### v2.22 -- 2026-09-11
- **Fix maintenance kit autocomplete for belts/chains**: admin autocomplete for kit filter parts now includes belt, roller, tensioner, chain, and sprocket products — previously only oil filters, drain plug washers, and gaskets were selectable, making it impossible to add belt/chain parts to maintenance templates

### v2.21 -- 2026-09-11
- **Notes for trucks and clients**: new `notes` text field on Truck and Client models; notes are displayed in the order detail page (split into two columns — truck notes on the left, owner notes on the right), truck detail page, and client detail page; editable via truck and client forms

### v2.20 -- 2026-09-09
- **Fix rear axle oil keyword matching**: `apply_maintenance_set` with `rear_axle_oil` category no longer picks unrelated works like "Демонтаж/монтаж задніх коліс"; keyword priority reordered (`міст` first), and wheel-related works excluded from both rule and WorkPrice lookups

### v2.19 -- 2026-09-07
- **Gearbox oil fix for manual transmission**: `apply_maintenance_set` with `gearbox_oil` category now correctly picks КПП (manual) rule and work instead of АКПП (automatic) when the truck has manual transmission; `is_auto_gearbox` detection moved before keyword lookup, and АКПП results are excluded for manual trucks

### v2.17 -- 2026-08-18
- **QR code toggle**: enable/disable QR codes from the CRM frontend (`GET /api/shortlinks/`, `POST /api/shortlinks/{id}/toggle/`); disabled codes show a branded stub page instead of redirecting

### v2.16 -- 2026-08-13
- **Maintenance set — category-specific parts**: `apply_maintenance_set` now accepts a `category` parameter (engine_oil / gearbox_oil / rear_axle_oil / belts / chains) and adds only the relevant oil and filters for that category instead of always adding engine oil + all filters; auto-detects automatic/robotic transmission for gearbox category
- **Smart filter classification**: 3-level filtering prevents wrong parts in maintenance sets — excludes by `service_type`, by FK oil fields on the kit, and by product name keywords (belts/rollers/chains); same logic applied to both `apply_maintenance_set` view and `auto_add_maintenance_kit` signal
- **Fix duplicate parts**: copper drain plug washer and similar parts no longer added twice when applying a maintenance set

### v2.15 -- 2026-08-13
- Scheduled maintenance dropdown with 5 categories replacing single "Add maintenance set" button
- Per-order postpone in stale orders reminder (3 / 7 / 14 / 30 days)

### v2.14 -- 2026-07-28
- Database backup/restore from frontend (BackupPage)
- Snooze for stale orders reminder (1 hour / 3 hours / 1 day)

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
