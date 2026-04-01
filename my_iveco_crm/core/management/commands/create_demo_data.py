"""
Management command to populate the database with demo data.
Run: python manage.py create_demo_data
"""
import random
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates demo data: admin user, clients, trucks, orders, works'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo data...')

        self._create_superuser()
        self._create_modules()
        base_models = self._create_base_models()
        work_groups, works = self._create_works()
        clients = self._create_clients()
        trucks = self._create_trucks(clients, base_models)
        self._create_orders(clients, trucks, works)

        self.stdout.write(self.style.SUCCESS('\nDemo data created successfully!'))
        self.stdout.write('Login: http://127.0.0.1:8000/admin/')
        self.stdout.write('  Username: admin')
        self.stdout.write('  Password: demo1234')

    # ------------------------------------------------------------------

    def _create_superuser(self):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@demo.local', 'demo1234',
                                          first_name='Адмін', last_name='Демо')
            self.stdout.write('  [+] Superuser created')
        else:
            self.stdout.write('  [ ] Superuser already exists')

    def _create_modules(self):
        from core.models import Module
        defaults = [
            dict(name='accounts',     label='Акаунти',          is_core=True,  is_enabled=True,  order=1),
            dict(name='users',        label='Користувачі',       is_core=True,  is_enabled=True,  order=2),
            dict(name='clients',      label='Клієнти',           is_core=True,  is_enabled=True,  order=3),
            dict(name='orders',       label='Наряди',            is_core=True,  is_enabled=True,  order=4),
            dict(name='inventory',    label='Склад',             is_core=False, is_enabled=True,  order=5),
            dict(name='maintenance',  label='Регламенти ТО',     is_core=False, is_enabled=True,  order=6),
            dict(name='cabinet',      label='Кабінет клієнта',   is_core=False, is_enabled=True,  order=7),
            dict(name='bot',          label='Telegram-бот',      is_core=False, is_enabled=False, order=8),
            dict(name='appointments', label='Запис на сервіс',   is_core=False, is_enabled=True,  order=9),
            dict(name='alpr',         label='Розпізнавання ном.', is_core=False, is_enabled=False, order=10),
            dict(name='invoices',     label='Рахунки',           is_core=False, is_enabled=True,  order=11),
        ]
        for d in defaults:
            Module.objects.get_or_create(name=d['name'], defaults=d)
        self.stdout.write('  [+] Modules initialized')

    def _create_base_models(self):
        from clients.models import IvecoBaseModel
        names = ['Daily', 'Stralis', 'Trakker', 'S-Way', 'Eurocargo']
        models = []
        for name in names:
            obj, _ = IvecoBaseModel.objects.get_or_create(name=name)
            models.append(obj)
        self.stdout.write(f'  [+] {len(models)} base models')
        return models

    def _create_works(self):
        from orders.models import WorkGroup, WorkPrice
        data = {
            'Технічне обслуговування': {
                'hourly_rate': 600,
                'works': [
                    ('Заміна оливи двигуна', 1.0),
                    ('Заміна масляного фільтра', 0.5),
                    ('Заміна паливного фільтра', 0.5),
                    ('Заміна повітряного фільтра', 0.5),
                    ('Регламентне ТО', 2.0),
                ],
            },
            'Ремонт двигуна': {
                'hourly_rate': 750,
                'works': [
                    ('Діагностика двигуна', 1.0),
                    ('Заміна ременя ГРМ', 3.0),
                    ('Заміна ланцюга ГРМ', 4.0),
                    ('Ремонт паливної системи', 2.5),
                ],
            },
            'Ходова та підвіска': {
                'hourly_rate': 600,
                'works': [
                    ('Заміна гальмівних колодок', 1.5),
                    ('Заміна амортизатора', 2.0),
                    ('Балансування коліс', 0.5),
                    ('Розвал-сходження', 1.0),
                ],
            },
            'Електрика та діагностика': {
                'hourly_rate': 700,
                'works': [
                    ('Комп\'ютерна діагностика', 1.0),
                    ('Заміна акумулятора', 0.5),
                    ('Ремонт генератора', 3.0),
                ],
            },
            'КПП та трансмісія': {
                'hourly_rate': 800,
                'works': [
                    ('Заміна оливи в КПП', 1.0),
                    ('Заміна оливи в задньому мості', 1.5),
                    ('Діагностика трансмісії', 1.0),
                ],
            },
        }
        groups = []
        all_works = []
        for group_name, info in data.items():
            group, _ = WorkGroup.objects.get_or_create(
                name=group_name,
                defaults={'hourly_rate': info['hourly_rate']}
            )
            groups.append(group)
            for work_name, hours in info['works']:
                work, _ = WorkPrice.objects.get_or_create(
                    name=work_name,
                    work_group=group,
                    defaults={'standard_hours': hours}
                )
                all_works.append(work)
        self.stdout.write(f'  [+] {len(groups)} work groups, {len(all_works)} works')
        return groups, all_works

    def _create_clients(self):
        from clients.models import Client
        from django.contrib.auth import get_user_model
        User = get_user_model()

        clients_data = [
            dict(name='ТОВ "Карго Транс"',        phone='+380671234001'),
            dict(name='ФОП Мельник Іван Петрович', phone='+380671234002'),
            dict(name='ТОВ "Укр Логістик"',        phone='+380671234003'),
            dict(name='ФОП Ковальчук Василь',       phone='+380671234004'),
            dict(name='ТОВ "Дніпро-Авто"',         phone='+380671234005'),
        ]
        clients = []
        for i, data in enumerate(clients_data, start=1):
            username = f'client_demo_{i}'
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'first_name': data['name'][:30], 'email': f'{username}@demo.local'}
            )
            client, _ = Client.objects.get_or_create(
                phone=data['phone'],
                defaults={'name': data['name'], 'user': user}
            )
            clients.append(client)
        self.stdout.write(f'  [+] {len(clients)} clients')
        return clients

    def _create_trucks(self, clients, base_models):
        from clients.models import Truck, IvecoBaseModel

        daily   = next((m for m in base_models if m.name == 'Daily'),    base_models[0])
        stralis = next((m for m in base_models if m.name == 'Stralis'),  base_models[0])
        trakker = next((m for m in base_models if m.name == 'Trakker'),  base_models[0])
        sway    = next((m for m in base_models if m.name == 'S-Way'),    base_models[0])

        trucks_data = [
            dict(client=clients[0], base_model=stralis, specific_model_name='Stralis AS 440S48',
                 full_vin='WJMM1BXS0NX123456', license_plate='АА1234ВВ', euro_standard='EURO6'),
            dict(client=clients[0], base_model=stralis, specific_model_name='Stralis AS 440S46',
                 full_vin='WJMM1BXS0NX234567', license_plate='АА5678СС', euro_standard='EURO5'),
            dict(client=clients[1], base_model=daily,   specific_model_name='Daily 35C15',
                 full_vin='ZCFC35B00N1345678', license_plate='ВВ9012КК', euro_standard='EURO6'),
            dict(client=clients[2], base_model=trakker, specific_model_name='Trakker AD 410T50',
                 full_vin='WJMM3BXS0NX456789', license_plate='КК3456МН', euro_standard='EURO5'),
            dict(client=clients[3], base_model=sway,    specific_model_name='S-Way AS 440S53',
                 full_vin='WJMM4BXS0NX567890', license_plate='СС7890РТ', euro_standard='EURO6'),
            dict(client=clients[4], base_model=daily,   specific_model_name='Daily 70C17',
                 full_vin='ZCFC70B00N1678901', license_plate='НН2345УФ', euro_standard='EURO6'),
        ]
        trucks = []
        for data in trucks_data:
            truck, _ = Truck.objects.get_or_create(
                full_vin=data['full_vin'],
                defaults=data
            )
            trucks.append(truck)
        self.stdout.write(f'  [+] {len(trucks)} trucks')
        return trucks

    def _create_orders(self, clients, trucks, works):
        from orders.models import ServiceOrder, ServiceWork, TruckMaintenanceIntervals

        # Знаходимо роботи по назві
        def find_work(name_part):
            for w in works:
                if name_part.lower() in w.name.lower():
                    return w
            return works[0]

        oil_work    = find_work('оливи двигуна')
        filter_work = find_work('масляного фільтра')
        diag_work   = find_work('діагностика двигуна')
        brake_work  = find_work('гальмівних')
        timing_work = find_work('ременя ГРМ')
        gearbox_oil = find_work('оливи в КПП')

        orders_data = [
            # Закрите ТО — Stralis 1
            dict(
                truck=trucks[0], client=clients[0],
                status='CLOSED', current_mileage=312500,
                order_number='НЗ-2025-001',
                problem_description='Планове ТО. Заміна оливи та фільтрів.',
                works_list=[oil_work, filter_work],
                days_ago=45,
            ),
            # Закрите ТО — Stralis 2
            dict(
                truck=trucks[1], client=clients[0],
                status='CLOSED', current_mileage=198700,
                order_number='НЗ-2025-002',
                problem_description='Планове ТО.',
                works_list=[oil_work, filter_work, gearbox_oil],
                days_ago=30,
            ),
            # Виконано — Daily
            dict(
                truck=trucks[2], client=clients[1],
                status='DONE', current_mileage=87300,
                order_number='НЗ-2025-003',
                problem_description='Діагностика. Скарга на нестабільну роботу двигуна.',
                recommendations='Рекомендовано заміну паливних форсунок протягом 5000 км.',
                works_list=[diag_work],
                days_ago=5,
            ),
            # В роботі — Trakker
            dict(
                truck=trucks[3], client=clients[2],
                status='IN_PROGRESS', current_mileage=445200,
                order_number='НЗ-2025-004',
                problem_description='Заміна гальмівних колодок на всіх осях.',
                works_list=[brake_work],
                days_ago=1,
            ),
            # Відкрито — S-Way
            dict(
                truck=trucks[4], client=clients[3],
                status='OPEN', current_mileage=55100,
                order_number='НЗ-2025-005',
                problem_description='Стороннє звук з боку двигуна. Перевірити ремінь ГРМ.',
                works_list=[timing_work],
                days_ago=0,
            ),
            # Відкрито — Daily 2
            dict(
                truck=trucks[5], client=clients[4],
                status='OPEN', current_mileage=133400,
                order_number='НЗ-2025-006',
                problem_description='Планове ТО + діагностика.',
                works_list=[oil_work, filter_work, diag_work],
                days_ago=0,
            ),
        ]

        order_count = 0
        work_count = 0
        for data in orders_data:
            works_list = data.pop('works_list')
            days_ago = data.pop('days_ago')
            created_at = timezone.now() - timedelta(days=days_ago)

            order, created = ServiceOrder.objects.get_or_create(
                order_number=data['order_number'],
                defaults={**data, 'created_at': created_at}
            )
            if created:
                order_count += 1
                for work in works_list:
                    ServiceWork.objects.create(
                        service_order=order,
                        work=work,
                        price_at_moment=work.get_calculated_price(),
                    )
                    work_count += 1
                order.update_total_cost()

        # Інтервали ТО для першого Stralis (на підставі CLOSED ТО)
        truck0 = trucks[0]
        intervals, _ = TruckMaintenanceIntervals.objects.get_or_create(truck=truck0)
        if not intervals.engine_oil_last_km:
            intervals.engine_oil_interval = 15000
            intervals.engine_oil_last_km  = 312500
            intervals.gearbox_oil_interval = 60000
            intervals.gearbox_oil_last_km  = 290000
            intervals.save()

        self.stdout.write(f'  [+] {order_count} orders, {work_count} service works')
