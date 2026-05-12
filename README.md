# TruckMaster CRM

CRM-система для сервісного центру вантажних автомобілів Iveco **"Італ Трак"**.

**Demo:** [http://137.184.31.33](http://137.184.31.33) | **Admin:** [http://137.184.31.33/admin/](http://137.184.31.33/admin/) (admin / admin)

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.11, Django 5, Django REST Framework, PostgreSQL |
| Frontend | React 18, Vite, Ant Design 5, Zustand, Recharts |
| Auth | Simple JWT (роздільна авторизація staff / клієнтів) |
| Background | Celery + Redis, django-celery-beat |
| Bot | python-telegram-bot (async) |
| Docs | drf-spectacular (OpenAPI / Swagger / ReDoc) |
| PWA | vite-plugin-pwa, Service Worker, offline fallback |
| i18n | react-i18next (UK / EN) |

---

## Modules

TruckMaster побудований на модульній архітектурі -- кожен функціональний блок можна увімкнути або вимкнути через адмін-панель без зміни коду.

| Module | Опис | Core |
|--------|------|:----:|
| **accounts** | Авторизація staff (JWT), реєстрація, профіль | Yes |
| **clients** | Клієнти, автомобілі, історія власності | Yes |
| **orders** | Наряди-замовлення, роботи, фото ремонту | Yes |
| **inventory** | Склад запчастин, закупівлі, переміщення | -- |
| **invoices** | Рахунки, інтеграція з Новою Поштою | -- |
| **maintenance** | Нагадування про планове ТО | -- |
| **cabinet** | Особистий кабінет клієнта | -- |
| **bot** | Telegram-бот для клієнтів та адмінів | -- |
| **appointments** | Онлайн-запис на сервіс | -- |
| **alpr** | Розпізнавання номерних знаків (камера) | -- |

Core-модулі завжди активні. Optional-модулі вмикаються в `/admin/core/module/` з перевіркою залежностей.

---

## Features

### Клієнти та автомобілі

- Картка клієнта з контактами, нотатками, прив'язаними авто
- Реєстр вантажівок: VIN, держномер, модель, євростандарт, тип КПП, пробіг
- Каталог базових моделей Iveco
- Індивідуальні налаштування доступу до функцій (кабінет, бот, сповіщення)
- Історія власності та зміни держномерів
- Soft-delete з причиною видалення та аудитом
- Імпорт клієнтів з XLSX

### Наряди-замовлення

- Повний цикл: Відкритий -> В роботі -> Виконано -> Закритий / Скасований
- Роботи в наряді: прайс-лист, погодинна ставка, прив'язка до механіка
- Автопідказка запчастин з попередніх нарядів на те ж авто з такою ж роботою
- Фото ремонту (до/після) з bulk-завантаженням
- Inline-редагування номера наряду та дати закриття
- Автоматичне закриття нарядів в статусі "Виконано" старше 1 тижня (Celery)
- Нагадування про наряди, що довго перебувають "В роботі" (модалка на сторінці замовлень)
- Soft-delete з обов'язковим зазначенням причини
- Аудит переходів статусів

### Регламентне ТО

- Інтервали обслуговування для кожної вантажівки: моторна олива, КПП, задній міст, ремені, ланцюги
- Два режими відліку: за пробігом (км) або за мотогодинами
- Еталонні шаблони регламенту за комбінацією (базова модель + євростандарт + тип КПП)
- Комплект ТО: мастила (з кількістю) + фільтри (з інтервалами заміни)
- Автоматичне заповнення інтервалів і комплекту при додаванні авто
- Ручне застосування еталону з повним перезаписом
- Автооновлення `last_km` при завершенні наряду (за ключовими словами роботи)
- Знімок попередніх значень для можливості відкату
- Нагадування ТО з пріоритетами (low / medium / high / critical)
- Конфігуровані правила нагадувань за пробігом і датою

### Склад та запчастини

- Мультисклад: роздрібний, оптовий, інший
- Картка товару: артикул, штрих-код, бренд, ціна продажу, собівартість
- Рух товарів: надходження, витрата, переміщення, повернення, списання, коригування
- Залишки по складах з резервуванням
- Повний цикл закупівлі: папки замовлень -> замовлення -> отримання -> оприбуткування
- Масове оприбуткування всіх позицій папки одним запитом
- Пошук товарів по артикулу з автопідстановкою ціни закупівлі
- Сповіщення про товари, що закінчуються
- Облік використаних запчастин у нарядах

### Рахунки та Нова Пошта

- Створення рахунків з позиціями для клієнта
- Типи доставки: самовивіз, відправка
- Інтеграція з API Нової Пошти: трекінг декларацій в реальному часі
- Відправка ТТН клієнту через Telegram / WhatsApp
- Публічне відстеження за номером декларації
- Журнал видачі запчастин водіям

### Telegram-бот

**Для клієнтів:**
- Авторизація через номер телефону
- "Мої автомобілі" -- підменю з історією ремонтів, регламентними роботами, залишком до ТО
- Перевірка статусу наряду
- "Мої відправки" -- трекінг декларацій Нової Пошти
- Налаштування нагадувань про ТО
- Щотижневий запит пробігу у власників (автоматичний Celery task)

**Для адмінів:**
- Пошук авто та клієнтів
- Завантаження фото ремонту до нарядів (з вибором типу фото)
- Статистика
- Реєстр невідомих номерів (номери, які шукали, але не знайшли в базі)

**Технічні деталі:**
- Модульна структура хендлерів
- Логування всіх повідомлень
- Ролі: guest, driver, owner, admin
- Автосинхронізація прив'язки авто для власників через сигнали

### Особистий кабінет клієнта

- Окрема авторизація (JWT) -- незалежна від staff
- Реєстрація з обов'язковою верифікацією email
- Дашборд з оглядом
- Список авто клієнта з деталями
- Перегляд нарядів і фото ремонту
- Профіль і налаштування
- Доступ контролюється через `ClientFeature`

### Онлайн-запис на сервіс

- Бронювання з вибором дати, часу, типу послуги
- Статуси: очікує, підтверджено, скасовано, завершено, не з'явився
- Автоматичні нагадування (щогодинний Celery task)
- Конвертація запису в наряд-замовлення

### ALPR (розпізнавання номерних знаків)

- Інтеграція з камерою на в'їзді
- Автоматичне зіставлення з базою авто / клієнтів / записів
- Журнал заїздів з рівнем впевненості
- Білий список (ігнорування службових авто)
- Сповіщення в Telegram staff-чат

### Лендінг (публічна сторінка)

- Hero-секція з CTA
- Галерея моделей Iveco (S-Way, X-Way, eDaily, Daily 4x4, S-Way Electric)
- Переваги сервісу
- FAQ з розгортанням
- Відгуки з Google Places (зірки, текст, авторство) -- кеш 24 год
- Контактна форма з honeypot-захистом від спаму
- Карта та контакти (кілька операторів)

### Додаткові можливості

- **i18n** -- повна локалізація українською та англійською (react-i18next)
- **PWA** -- встановлення на мобільний/десктоп, офлайн-підтримка, Service Worker
- **QR / Short Links** -- `/go/<slug>/` з лічильником переходів
- **Дашборд** -- ключові метрики (клієнти, авто, наряди, виручка за місяць/рік), графіки
- **Аудит** -- журнал дій користувачів (створення, зміна, видалення, перегляд, експорт)
- **Модульна система** -- увімкнення/вимкнення функціоналу без деплою

---

## API

Повна документація доступна після запуску:

| URL | Формат |
|-----|--------|
| `GET /api/docs/` | Swagger UI |
| `GET /api/redoc/` | ReDoc |
| `GET /api/schema/` | OpenAPI JSON |

### Основні ендпоінти

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
| `send-daily-reminders` | 09:00 daily | Нагадування клієнтам про ТО |
| `ask-owners-for-mileage` | Mon 10:00 | Запит пробігу у власників через бот |
| `send-appointment-reminders` | Hourly | Нагадування про записи на сервіс |
| `auto-close-done-orders` | 03:00 daily | Автозакриття нарядів >1 тижня в DONE |

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
