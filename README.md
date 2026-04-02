# TruckMaster — Backend

Django REST API для CRM сервісного центру вантажних автомобілів Iveco («Італ Трак»).

## Стек

- Python 3.11 + Django 5 + Django REST Framework
- PostgreSQL
- Celery + Redis (фонові задачі)
- Simple JWT (авторизація)
- drf-spectacular (OpenAPI документація)

## Запуск локально

```bash
cd my_iveco_crm
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Змінні середовища

```env
SECRET_KEY=...
DEBUG=True
DATABASE_URL=postgres://...
REDIS_URL=redis://localhost:6379/0
GOOGLE_PLACES_API_KEY=...
ALPR_API_KEY=...
ALPR_STAFF_CHAT_ID=...
```

## API документація

- `GET /api/docs/` — Swagger UI
- `GET /api/redoc/` — ReDoc
- `GET /api/schema/` — OpenAPI схема

## Модулі

| Модуль | URL-префікс | Core | Опис |
|--------|-------------|------|------|
| accounts | — | ✓ | Авторизація (JWT) |
| users | /api/users/ | ✓ | Персонал |
| clients | /api/clients/ | ✓ | Клієнти та авто |
| orders | /api/orders/ | ✓ | Наряди-замовлення |
| inventory | /api/inventory/ | — | Склад запчастин |
| maintenance | /api/maintenance/ | — | Нагадування ТО |
| cabinet | /api/cabinet/ | — | Кабінет клієнта |
| bot | /api/bot/ | — | Telegram бот |
| appointments | /api/appointments/ | — | Записи на сервіс |
| alpr | /api/alpr/ | — | Розпізнавання номерів |
| invoices | /api/invoices/ | — | Рахунки |

## Склад (inventory app)

### Моделі

| Модель | Опис |
|--------|------|
| `Category` / `SubCategory` | Категорії товарів |
| `Warehouse` | Склад (retail / wholesale / other) |
| `Product` | Товар/запчастина (soft-delete) |
| `StockItem` | Залишок товару на конкретному складі |
| `StockMovement` | Рух товарів (in/out/transfer/adjustment/return/write_off) |
| `UsedPart` | Використана запчастина в наряді |
| `OrderFolder` | Папка списку замовлення (архів) |
| `OrderItem` | Позиція замовлення — повний цикл до оприбуткування |

### OrderItem — цикл замовлення

```
is_ordered=False → (toggle) → is_ordered=True → (receive) → is_received=True
```

Поля `OrderItem`:
- `name`, `quantity`, `unit`, `notes` — базова інформація
- `purchase_price` — ціна закупівлі (фіксується в `StockMovement` при оприбуткуванні)
- `is_ordered`, `ordered_at`, `ordered_by` — статус замовлення
- `is_received`, `received_at`, `received_by` — статус отримання
- `linked_product` → FK до `Product` — зв'язок зі складом

### API ендпоінти (inventory)

```
GET/POST   /api/inventory/order-folders/
POST       /api/inventory/order-folders/{id}/archive/
POST       /api/inventory/order-folders/{id}/unarchive/
POST       /api/inventory/order-folders/{id}/mark_all_ordered/
POST       /api/inventory/order-folders/{id}/unmark_all_ordered/
POST       /api/inventory/order-folders/{id}/receive_all/      ← масове оприбуткування

GET/POST   /api/inventory/order-items/
POST       /api/inventory/order-items/{id}/toggle_ordered/
POST       /api/inventory/order-items/{id}/receive/            ← оприбуткувати одну позицію
GET        /api/inventory/order-items/search_products/?q=...   ← пошук збігів для прив'язки

POST       /api/inventory/movements/transfer/                  ← переміщення між складами
POST       /api/inventory/movements/receive_stock/             ← надходження на склад
```

### receive / receive_all — логіка

`POST /api/inventory/order-items/{id}/receive/`:
- `warehouse_id` (обов'язково), `quantity`, `purchase_price`
- `product_id` — прив'язати до існуючого товару
- або `sku_code` + `product_name` + `unit` — створити новий товар
- Оновлює `StockItem.quantity`, синхронізує `Product.current_stock`, створює `StockMovement(type='in')`

`POST /api/inventory/order-folders/{id}/receive_all/`:
- `warehouse_id` (обов'язково)
- Обробляє всі позиції з `is_ordered=True`, `is_received=False`, `linked_product IS NOT NULL`
- Ціна кожного руху береться з `item.purchase_price`

## Celery — розклад задач

| Задача | Час |
|--------|-----|
| `send-daily-reminders` | 09:00 щодня |
| `ask-owners-for-mileage` | Пн 10:00 |
| `send-appointment-reminders` | Щогодини |
| `auto-close-done-orders` | 03:00 щодня |

## Changelog

### v2.7 — 2026-04-02
- **OrderItem**: поля `is_received`, `received_at`, `received_by`, `linked_product`, `purchase_price`
- **Міграції**: `inventory.0007` (received fields), `inventory.0008` (purchase_price)
- **receive action**: оприбуткування позиції — пошук/створення товару, оновлення StockItem, StockMovement
- **receive_all action**: масове оприбуткування всіх готових позицій папки
- **search_products**: пошук збігів товарів за назвою/артикулом для прив'язки
- **OrderFolder**: поля `is_archived`, `archived_at`; `archive`/`unarchive` actions (міграція `0006`)

### v2.6 — 2026-04-02
- **Warehouse**: поле `warehouse_type` (retail/wholesale/other), міграція `0005`
- **StockMovement.transfer**: переміщення між складами з оновленням обох StockItem
- **StockMovement.receive_stock**: надходження на конкретний склад
- **OrderFolder / OrderItem**: початкова реалізація, міграція `0004`
- **ProductViewSet**: виправлено пошук (`icontains` замість `iendswith`)

### v2.5 — 2026-03-23
- Cabinet app: кабінет клієнта, JWT для клієнтів, ClientFeature

### v2.4
- Invoices: статуси, ТТН Нова Пошта, Telegram/WhatsApp сповіщення

### v2.3
- ALPR: розпізнавання номерів, VehicleArrival, IgnoredVehicle

### v2.2
- Maintenance: ServiceReminder, TruckMaintenanceIntervals, Celery задачі

### v2.1
- Модульна система: Module, ModuleMiddleware, registry з кешем

### v2.0
- Наряди, роботи, запчастини, фото ремонту

### v1.x
- Клієнти, автомобілі, персонал, JWT авторизація
