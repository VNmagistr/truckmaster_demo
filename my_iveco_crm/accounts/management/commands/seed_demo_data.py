"""
Management command: seed_demo_data
Генерує демо-дані: 1000 клієнтів, 3000 вантажівок, 5000 замовлень.
"""
import random
import string
from datetime import timedelta, date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from clients.models import Client, IvecoBaseModel, Truck
from orders.models import ServiceOrder, WorkGroup, WorkPrice, ServiceWork


# ── Iveco моделі ────────────────────────────────────────────────────────────

IVECO_BASE_MODELS = [
    'Daily', 'S-Way', 'X-Way', 'Stralis', 'Eurocargo', 'Trakker', 'E-Way',
]

IVECO_SPECIFIC = {
    'Daily':      ['35C15', '35S15', '50C17', '65C17', '70C17', '35C21', '35S21', '50C21'],
    'S-Way':      ['AS440S46T/P', 'AS440S51T/P', 'AT440S46T/P', 'AS260S46Y/P', 'AS480S53T/P'],
    'X-Way':      ['AD260X36H', 'AD260X46H', 'AT260X36H', 'AT260X46H', 'AD410X47T'],
    'Stralis':    ['AS440S46T/P', 'AT440S46T/P', 'AS440S51T/P', 'AD440S46T/P', 'AS440S48T/P'],
    'Eurocargo':  ['ML120E25', 'ML160E25', 'ML180E28', 'ML75E19', 'ML140E28'],
    'Trakker':    ['AT720T47T', 'AD410T47T', 'AD380T38H', 'AT340T45W', 'AD410T48T'],
    'E-Way':      ['AS440S', 'E-Daily 35S', 'E-Daily 50C'],
}

# ── Групи робіт ─────────────────────────────────────────────────────────────

WORK_DATA = [
    ('Двигун', 800, [
        ('Заміна оливи двигуна', '0.50'),
        ('Заміна паливного фільтра', '0.50'),
        ('Діагностика двигуна', '1.00'),
        ('Ремонт турбіни', '4.00'),
        ('Заміна ременя ГРМ', '3.00'),
        ('Промивка системи охолодження', '1.00'),
        ('Заміна прокладки ГБЦ', '6.00'),
    ]),
    ('Трансмісія', 750, [
        ('Заміна оливи КПП', '0.50'),
        ('Ремонт зчеплення', '5.00'),
        ('Регулювання КПП', '2.00'),
        ('Заміна оливи заднього моста', '0.50'),
        ('Ремонт роздаткової коробки', '6.00'),
    ]),
    ('Гальма', 700, [
        ('Заміна гальмівних колодок передніх', '1.00'),
        ('Заміна гальмівних колодок задніх', '1.00'),
        ('Заміна гальмівних дисків', '2.00'),
        ('Прокачка гальмівної системи', '1.00'),
        ('Заміна суппорту', '2.50'),
        ('Регулювання гальм', '0.50'),
    ]),
    ('Підвіска', 700, [
        ('Заміна амортизаторів передніх', '2.00'),
        ('Заміна амортизаторів задніх', '2.00'),
        ('Заміна важелів підвіски', '3.00'),
        ('Регулювання розвал-сходження', '1.00'),
        ('Заміна пружин', '2.00'),
        ('Заміна рульових наконечників', '1.50'),
    ]),
    ('Електрика', 650, [
        ('Діагностика електрики', '1.00'),
        ('Заміна стартера', '2.00'),
        ('Заміна генератора', '2.00'),
        ('Ремонт проводки', '3.00'),
        ('Перепрошивка блоку керування', '1.50'),
    ]),
    ('Кузов', 600, [
        ('Кузовний ремонт', '8.00'),
        ('Заміна скла лобового', '2.00'),
        ('Рихтування', '4.00'),
        ('Зварювальні роботи', '3.00'),
    ]),
    ('Планове ТО', 600, [
        ('Планове ТО (30 000 км)', '2.00'),
        ('Планове ТО (60 000 км)', '3.00'),
        ('Планове ТО (90 000 км)', '2.00'),
        ('Часткове ТО', '1.50'),
        ('Повне ТО', '4.00'),
        ('Передрейсовий огляд', '0.50'),
    ]),
]

# ── Опис проблем ─────────────────────────────────────────────────────────────

PROBLEMS = [
    'Стукіт у двигуні при прогріві',
    'Протікання оливи з двигуна',
    'Не перемикаються передачі',
    'Скрип при гальмуванні',
    'Вібрація на швидкості вище 80 км/год',
    'Перегрів двигуна',
    'Важко запускається двигун',
    'Підвищена витрата пального',
    'Несправність ABS',
    'Підтікання системи охолодження',
    'Плановий огляд та ТО',
    'Заміна зношених деталей підвіски',
    'Несправність пневмопідвіски',
    'Шум при повороті керма',
    'Несправність кондиціонера кабіни',
    'Плановий регламент 30 000 км',
    'Плановий регламент 60 000 км',
    'Заміна ременя ГРМ за регламентом',
    'Несправність DPF фільтра',
    'Передрейсовий технічний огляд',
    'Стрибки обертів двигуна на холостому ходу',
    'Не працює система рекуперації',
    'Підвищений шум гальмівної системи',
    'Зависання коробки передач',
    'Несправність датчика рівня пального',
    'Нестабільна робота гідравліки',
    'Несправність компресора кондиціонера',
    'Заміна зношених гальмівних колодок',
    'Несправність системи AdBlue',
    'Перевірка рульового механізму',
]

RECOMMENDATIONS = [
    'Рекомендуємо заміну повітряного фільтра при наступному ТО.',
    'Перевірте рівень оливи через 5 000 км.',
    'Рекомендуємо планове ТО через 10 000 км.',
    'Стан гальмівних колодок задовільний, заміна через 15 000 км.',
    'Рекомендуємо перевірку ходової частини через 20 000 км.',
    'Замінено оливу, фільтри в нормі.',
    'Рекомендуємо діагностику підвіски при наступному візиті.',
    '',
    '',
    '',  # Порожні для реалістичності
]

# ── Україна: імена, прізвища, міста ──────────────────────────────────────────

FIRST_NAMES = [
    'Олексій', 'Іван', 'Микола', 'Андрій', 'Василь', 'Петро', 'Сергій', 'Олег',
    'Дмитро', 'Юрій', 'Тарас', 'Богдан', 'Ігор', 'Роман', 'Михайло', 'Віктор',
    'Павло', 'Степан', 'Григорій', 'Ярослав', 'Максим', 'Владислав', 'Денис',
    'Наталія', 'Оксана', 'Марія', 'Олена', 'Тетяна', 'Людмила', 'Ірина',
    'Ганна', 'Вікторія', 'Юлія', 'Галина', 'Світлана', 'Надія', 'Лариса',
]

LAST_NAMES = [
    'Коваленко', 'Шевченко', 'Бондаренко', 'Мельник', 'Кравченко', 'Олійник',
    'Ткаченко', 'Іваненко', 'Гончаренко', 'Марченко', 'Тимченко', 'Хоменко',
    'Романенко', 'Савченко', 'Клименко', 'Лисенко', 'Павленко', 'Яценко',
    'Бойко', 'Захаренко', 'Лещенко', 'Руденко', 'Пономаренко', 'Білоус',
    'Дяченко', 'Кириленко', 'Сидоренко', 'Власенко', 'Литвиненко', 'Нечипоренко',
    'Остапенко', 'Приходько', 'Радченко', 'Стець', 'Федоренко', 'Харченко',
    'Цимбалюк', 'Чорновіл', 'Шаповаленко', 'Щербаченко',
]

CITIES = [
    'Київ', 'Харків', 'Одеса', 'Дніпро', 'Запоріжжя', 'Львів', 'Кривий Ріг',
    'Миколаїв', 'Вінниця', 'Херсон', 'Полтава', 'Чернігів', 'Черкаси',
    'Суми', 'Житомир', 'Рівне', 'Івано-Франківськ', 'Тернопіль', 'Хмельницький',
    'Луцьк', 'Ужгород', 'Чернівці', 'Кропивницький', 'Біла Церква',
]

EURO_STANDARDS = ['EURO3', 'EURO4', 'EURO5', 'EURO6']

# Статуси: DONE і CLOSED домінують — реалістично для архіву
ORDER_STATUSES = ['OPEN', 'IN_PROGRESS', 'DONE', 'CLOSED', 'CANCELED']
STATUS_WEIGHTS = [3, 7, 30, 55, 5]


def _rand_vin():
    """Генерує випадковий VIN (17 символів, без I/O/Q)."""
    chars = string.ascii_uppercase.replace('I', '').replace('O', '').replace('Q', '')
    return (
        ''.join(random.choices(chars, k=3))
        + ''.join(random.choices(chars + string.digits, k=6))
        + ''.join(random.choices(chars + string.digits, k=8))
    )


def _rand_plate(used: set) -> str:
    """Генерує унікальний номерний знак у форматі AA0000BB."""
    regions = ['AA', 'AB', 'AC', 'AE', 'AH', 'AI', 'AK', 'AM', 'AO', 'AP',
               'AT', 'AX', 'BA', 'BB', 'BC', 'BE', 'BH', 'BI', 'BK', 'BM',
               'BO', 'BP', 'BT', 'CA', 'CB', 'CE', 'CH', 'CK', 'CM', 'CT']
    suffix_chars = 'ABCEHIKMOPTX'
    for _ in range(10000):
        region = random.choice(regions)
        digits = ''.join(random.choices(string.digits, k=4))
        suffix = ''.join(random.choices(suffix_chars, k=2))
        plate = f'{region}{digits}{suffix}'
        if plate not in used:
            used.add(plate)
            return plate
    raise RuntimeError('Не вдалося згенерувати унікальний номерний знак')


def _rand_phone(used: set) -> str:
    """Генерує унікальний український номер телефону."""
    prefixes = ['050', '066', '095', '099', '063', '073', '093', '067', '096', '097', '098']
    for _ in range(100000):
        phone = f'+380{random.choice(prefixes)[1:]}{"".join(random.choices(string.digits, k=7))}'
        if phone not in used:
            used.add(phone)
            return phone
    raise RuntimeError('Не вдалося згенерувати унікальний телефон')


def _rand_date_in_range(start: date, end: date):
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


class Command(BaseCommand):
    help = 'Seeds demo data: 1000 clients, 3000 trucks, 5000 orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing demo data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self._clear()

        self.stdout.write('Починаємо генерацію демо-даних...')

        with transaction.atomic():
            base_models = self._create_iveco_models()
            work_prices = self._create_work_groups()
            clients = self._create_clients(1000)
            trucks = self._create_trucks(clients, base_models, 3000)
            self._create_orders(clients, trucks, work_prices, 5000)

        self.stdout.write(self.style.SUCCESS(
            '\n✓ Готово! Створено:\n'
            '  • 1000 клієнтів\n'
            '  • 3000 вантажівок\n'
            '  • 5000 замовлень\n'
        ))

    # ── Очищення ────────────────────────────────────────────────────────────

    def _clear(self):
        self.stdout.write('Видаляємо існуючі демо-дані...')
        ServiceWork.objects.all().delete()
        ServiceOrder.objects.all().delete()
        Truck.objects.all().delete()
        Client.objects.all().delete()
        User.objects.filter(username__startswith='demo_').delete()
        self.stdout.write('  Очищено.')

    # ── Iveco моделі ────────────────────────────────────────────────────────

    def _create_iveco_models(self):
        self.stdout.write('Створюємо базові моделі Iveco...')
        result = []
        for name in IVECO_BASE_MODELS:
            obj, _ = IvecoBaseModel.objects.get_or_create(name=name)
            result.append(obj)
        self.stdout.write(f'  {len(result)} базових моделей.')
        return result

    # ── Групи та прайс робіт ────────────────────────────────────────────────

    def _create_work_groups(self):
        self.stdout.write('Створюємо групи та прайс робіт...')
        prices = []
        for group_name, rate, works in WORK_DATA:
            group, _ = WorkGroup.objects.get_or_create(
                name=group_name,
                defaults={'hourly_rate': Decimal(str(rate))},
            )
            for work_name, hours in works:
                wp, _ = WorkPrice.objects.get_or_create(
                    work_group=group,
                    name=work_name,
                    defaults={'standard_hours': Decimal(hours)},
                )
                prices.append(wp)
        self.stdout.write(f'  {len(prices)} позицій прайсу.')
        return prices

    # ── Клієнти ─────────────────────────────────────────────────────────────

    def _create_clients(self, count: int):
        self.stdout.write(f'Створюємо {count} клієнтів...')
        used_phones = set(Client.objects.values_list('phone', flat=True))
        used_usernames = set(User.objects.values_list('username', flat=True))

        users_to_create = []
        clients_to_create = []

        for i in range(count):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            name = f'{last} {first}'
            phone = _rand_phone(used_phones)
            city = random.choice(CITIES)

            username = f'demo_{i+1:04d}'
            while username in used_usernames:
                username = f'demo_{i+1:04d}_{random.randint(1, 999)}'
            used_usernames.add(username)

            users_to_create.append(User(
                username=username,
                first_name=first,
                last_name=last,
                email=f'{username}@demo.ital-truck.com.ua',
                is_active=True,
            ))
            clients_to_create.append((name, phone, city))

        # Bulk create users
        created_users = User.objects.bulk_create(users_to_create, batch_size=200)

        # Bulk create clients
        client_objs = []
        for user, (name, phone, city) in zip(created_users, clients_to_create):
            client_objs.append(Client(
                user=user,
                name=name,
                phone=phone,
                address=city,
            ))
        Client.objects.bulk_create(client_objs, batch_size=200)

        clients = list(Client.objects.filter(
            user__username__startswith='demo_'
        ).order_by('id'))
        self.stdout.write(f'  {len(clients)} клієнтів створено.')
        return clients

    # ── Вантажівки ──────────────────────────────────────────────────────────

    def _create_trucks(self, clients, base_models, count: int):
        self.stdout.write(f'Створюємо {count} вантажівок...')
        used_vins = set(Truck.objects.values_list('full_vin', flat=True))
        used_plates = set(Truck.objects.values_list('license_plate', flat=True))

        base_model_map = {m.name: m for m in base_models}
        trucks_to_create = []

        for _ in range(count):
            base_name = random.choice(IVECO_BASE_MODELS)
            specific = random.choice(IVECO_SPECIFIC[base_name])
            base_model = base_model_map[base_name]

            vin = _rand_vin()
            while vin in used_vins:
                vin = _rand_vin()
            used_vins.add(vin)

            plate = _rand_plate(used_plates)
            client = random.choice(clients)
            euro = random.choice(EURO_STANDARDS)

            trucks_to_create.append(Truck(
                client=client,
                base_model=base_model,
                specific_model_name=specific,
                full_vin=vin,
                last_seven_vin=vin[-7:],  # вручну, бо bulk_create не викликає save()
                license_plate=plate,
                euro_standard=euro,
            ))

        Truck.objects.bulk_create(trucks_to_create, batch_size=200)
        trucks = list(Truck.objects.filter(
            client__user__username__startswith='demo_'
        ).select_related('client').order_by('id'))
        self.stdout.write(f'  {len(trucks)} вантажівок створено.')
        return trucks

    # ── Замовлення ──────────────────────────────────────────────────────────

    def _create_orders(self, clients, trucks, work_prices, count: int):
        self.stdout.write(f'Створюємо {count} замовлень...')

        start_date = date(2023, 1, 1)
        end_date = date(2024, 12, 31)

        # Попередньо генеруємо дати та призначаємо порядкові номери по дням
        from collections import defaultdict
        date_counters = defaultdict(int)

        orders_to_create = []
        truck_client_map = {t.id: t.client_id for t in trucks}

        for _ in range(count):
            truck = random.choice(trucks)
            client_id = truck_client_map[truck.id]

            # Знаходимо клієнта за id
            order_date = _rand_date_in_range(start_date, end_date)
            date_str = order_date.strftime('%Y%m%d')
            date_counters[date_str] += 1
            order_number = f'SO-{date_str}-{date_counters[date_str]:04d}'

            status = random.choices(ORDER_STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
            mileage = random.randint(50_000, 900_000)
            problem = random.choice(PROBLEMS)
            rec = random.choice(RECOMMENDATIONS)

            created_at = timezone.make_aware(
                timezone.datetime(
                    order_date.year, order_date.month, order_date.day,
                    random.randint(8, 17), random.randint(0, 59),
                )
            )

            # Для CLOSED/DONE призначаємо реалістичну total_cost пізніше
            orders_to_create.append(ServiceOrder(
                order_number=order_number,
                client_id=client_id,
                truck=truck,
                current_mileage=mileage,
                problem_description=problem,
                recommendations=rec,
                status=status,
                total_cost=Decimal('0'),
                created_at=created_at,
            ))

        ServiceOrder.objects.bulk_create(orders_to_create, batch_size=200)
        self.stdout.write('  Замовлення збережено, додаємо роботи...')

        # Додаємо ServiceWork до частини замовлень (DONE/CLOSED/IN_PROGRESS)
        all_orders = list(ServiceOrder.objects.filter(
            order_number__startswith='SO-',
            client__user__username__startswith='demo_',
        ).only('id', 'status', 'total_cost'))

        works_to_create = []
        order_costs = {}  # order_id → total_cost

        billable = [o for o in all_orders if o.status in ('IN_PROGRESS', 'DONE', 'CLOSED')]

        for order in billable:
            num_works = random.randint(1, 4)
            selected = random.sample(work_prices, min(num_works, len(work_prices)))
            order_total = Decimal('0')
            for wp in selected:
                hours = Decimal(str(round(random.uniform(0.5, 6.0) * 2) / 2))  # кратно 0.5
                price = wp.work_group.hourly_rate * hours
                works_to_create.append(ServiceWork(
                    service_order_id=order.id,
                    work=wp,
                    hours_spent=hours,
                    price_at_moment=price,
                ))
                order_total += price
            order_costs[order.id] = order_total

        ServiceWork.objects.bulk_create(works_to_create, batch_size=500)

        # Оновлюємо total_cost одним запитом через bulk_update
        orders_to_update = []
        for order in billable:
            if order.id in order_costs:
                order.total_cost = order_costs[order.id]
                orders_to_update.append(order)

        ServiceOrder.objects.bulk_update(orders_to_update, ['total_cost'], batch_size=200)

        self.stdout.write(f'  {len(all_orders)} замовлень + {len(works_to_create)} виконаних робіт.')
