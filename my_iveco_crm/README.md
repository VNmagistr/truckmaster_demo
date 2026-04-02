# TruckMaster — Backend

Django REST API для CRM сервісного центру вантажних автомобілів Iveco («Італ Трак»).

## Стек

- Python 3.12 / Django 5.x
- Django REST Framework + drf-spectacular (OpenAPI)
- PostgreSQL (продакшн) / SQLite (розробка)
- Celery + Redis (фонові задачі)
- JWT-автентифікація (SimpleJWT)

## Запуск локально

```bash
python -m venv venv
source venv/bin/activate  # або venv\Scripts\activate на Windows
pip install -r requirements.txt
cp .env.example .env      # заповнити змінні
python manage.py migrate
python manage.py runserver
```

## API документація

| URL | Опис |
|-----|------|
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | OpenAPI JSON |

## Модулі

| Модуль | Тип | Опис |
|--------|-----|------|
| `accounts` | core | Акаунти, Google Reviews |
| `users` | core | Персонал |
| `clients` | core | Клієнти та їх авто |
| `orders` | core | Наряди-замовлення, ТО-інтервали |
| `inventory` | optional | Склад запчастин |
| `invoices` | optional | Рахунки + Нова Пошта |
| `cabinet` | optional | Особистий кабінет клієнта |
| `bot` | optional | Telegram-бот |
| `appointments` | optional | Запис на сервіс |
| `alpr` | optional | Розпізнавання номерних знаків |
| `maintenance` | optional | Нагадування про ТО |

Вмикати/вимикати модулі: `/admin/core/module/`

## Основні endpoint-и

```
POST   /api/token/                        — авторизація staff
POST   /api/token/refresh/

GET    /api/clients/
GET    /api/orders/
GET    /api/inventory/products/
GET    /api/inventory/warehouses/
POST   /api/inventory/movements/transfer/       — переміщення між складами
POST   /api/inventory/movements/receive_stock/  — надходження на склад
GET    /api/inventory/order-folders/            — списки замовлень
GET    /api/invoices/
GET    /api/appointments/
GET    /api/alpr/arrivals/
GET    /api/modules/
```

## Celery задачі

| Задача | Розклад |
|--------|---------|
| Щоденні нагадування клієнтам | 09:00 |
| Запит пробігу у власників | Пн 10:00 |
| Нагадування про запис | щогодини |
| Авто-закриття нарядів (>7 днів у DONE) | 03:00 |

## Changelog

### v2.6 — 2026-04-02
- **Склад / Оптовий**: поле `warehouse_type` (retail/wholesale/other) на складах; надходження на будь-який склад (`receive_stock`); переміщення між складами (`transfer`) з автоматичним перерахунком `Product.current_stock`
- **Склад / Замовити**: моделі `OrderFolder` + `OrderItem`; bulk-toggle `mark_all_ordered`; toggle окремої позиції
- **Пошук по складу**: `iendswith` → `icontains` для артикулу (шукає по будь-якій частині)

### v2.5 — 2026-03-23
- Особистий кабінет клієнта (cabinet app)
- Підтвердження email клієнта
- ALPR — розпізнавання номерних знаків (пауза)

### v2.4
- Telegram-бот: відстеження відправок Нова Пошта
- Рахунки: авто-завантаження статусу ТТН

### v2.3
- Система модулів (вмикати/вимикати в адмінці)
- Інтервали ТО вантажівок

### v2.2
- Склад запчастин (inventory app)
- Рух товарів, залишки по складах

### v2.1
- Рахунки та Нова Пошта інтеграція

### v2.0
- Наряди-замовлення, роботи, запчастини
- Telegram/WhatsApp сповіщення

### v1.x
- Клієнти, автомобілі, базова авторизація
