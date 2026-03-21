from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta

from clients.models import Client, IvecoBaseModel, Truck
from orders.models import (
    ServiceOrder, ServiceWork, WorkGroup, WorkPrice, TruckMaintenanceIntervals
)
from maintenance.models import ServiceType, ServiceReminder


def _make_truck():
    client = Client.objects.create(name='Test Client')
    base_model = IvecoBaseModel.objects.create(name='Daily')
    return Truck.objects.create(
        client=client,
        base_model=base_model,
        specific_model_name='35C15',
        full_vin='ZCFC35A0001234567',
        license_plate='AA1234BB',
    )


class AutoCreateNextReminderTest(TestCase):
    """
    Сигнал maintenance/signals.py: auto_create_next_reminder
    Коли ServiceReminder переводиться в статус 'completed' —
    автоматично створюється наступне нагадування.
    """

    def setUp(self):
        self.truck = _make_truck()
        self.service_type = ServiceType.objects.create(
            name='Заміна оливи двигуна',
            default_interval_km=15000,
            default_interval_months=12,
        )

    def _make_reminder(self, **kwargs):
        defaults = dict(
            truck=self.truck,
            service_type=self.service_type,
            title='Заміна оливи',
            reminder_type='both',
            target_mileage=50000,
            status='pending',
            priority='medium',
        )
        defaults.update(kwargs)
        return ServiceReminder.objects.create(**defaults)

    def test_completing_reminder_creates_next(self):
        """При виконанні нагадування автоматично з'являється нове"""
        reminder = self._make_reminder()
        reminder.status = 'completed'
        reminder.completed_at = timezone.now()
        reminder.save()

        count = ServiceReminder.objects.filter(
            truck=self.truck, service_type=self.service_type, status='pending'
        ).count()
        self.assertEqual(count, 1)

    def test_next_reminder_target_mileage_correct(self):
        """target_mileage наступного = пробіг при виконанні + interval_km"""
        order = ServiceOrder.objects.create(
            client=self.truck.client,
            truck=self.truck,
            current_mileage=85000,
        )
        reminder = self._make_reminder(completed_order=order)
        reminder.status = 'completed'
        reminder.completed_at = timezone.now()
        reminder.save()

        next_r = ServiceReminder.objects.filter(
            truck=self.truck, service_type=self.service_type, status='pending'
        ).first()
        self.assertIsNotNone(next_r)
        self.assertEqual(next_r.target_mileage, 85000 + 15000)

    def test_next_reminder_target_date_correct(self):
        """target_date наступного = дата виконання + interval_months"""
        completed_at = timezone.now()
        reminder = self._make_reminder()
        reminder.status = 'completed'
        reminder.completed_at = completed_at
        reminder.save()

        next_r = ServiceReminder.objects.filter(
            truck=self.truck, service_type=self.service_type, status='pending'
        ).first()
        expected_date = completed_at.date() + relativedelta(months=12)
        self.assertEqual(next_r.target_date, expected_date)

    def test_no_duplicate_if_active_reminder_exists(self):
        """Якщо вже є активне нагадування для авто + типу — дублікат не створюється"""
        self._make_reminder()  # вже існує pending
        reminder2 = self._make_reminder(target_mileage=60000)
        reminder2.status = 'completed'
        reminder2.completed_at = timezone.now()
        reminder2.save()

        count = ServiceReminder.objects.filter(
            truck=self.truck, service_type=self.service_type, status='pending'
        ).count()
        self.assertEqual(count, 1)

    def test_no_next_reminder_without_interval(self):
        """Без інтервалу наступне нагадування не створюється"""
        service_type_no_interval = ServiceType.objects.create(name='Без інтервалу')
        reminder = self._make_reminder(service_type=service_type_no_interval)
        reminder.status = 'completed'
        reminder.completed_at = timezone.now()
        reminder.save()

        count = ServiceReminder.objects.filter(
            truck=self.truck, service_type=service_type_no_interval, status='pending'
        ).count()
        self.assertEqual(count, 0)

    def test_interval_km_on_reminder_takes_priority_over_service_type(self):
        """interval_km на самому нагадуванні має пріоритет над default_interval_km типу ТО"""
        order = ServiceOrder.objects.create(
            client=self.truck.client,
            truck=self.truck,
            current_mileage=50000,
        )
        reminder = self._make_reminder(interval_km=20000, completed_order=order)
        reminder.status = 'completed'
        reminder.completed_at = timezone.now()
        reminder.save()

        next_r = ServiceReminder.objects.filter(
            truck=self.truck, service_type=self.service_type, status='pending'
        ).first()
        self.assertEqual(next_r.target_mileage, 50000 + 20000)

    def test_non_completed_status_does_not_create_next(self):
        """Зміна статусу на 'notified' не створює наступне нагадування"""
        reminder = self._make_reminder()
        reminder.status = 'notified'
        reminder.save()

        count = ServiceReminder.objects.filter(
            truck=self.truck, service_type=self.service_type, status='pending'
        ).count()
        self.assertEqual(count, 0)


class MaintenanceIntervalsOnDoneTest(TestCase):
    """
    Сигнал orders/signals.py: record_status_change → _update_maintenance_intervals
    Коли ServiceOrder переходить у статус DONE — оновлюються TruckMaintenanceIntervals.
    """

    def setUp(self):
        self.truck = _make_truck()
        self.mechanic = User.objects.create_user(username='mechanic', password='pass')

    def _make_order(self, mileage=None):
        return ServiceOrder.objects.create(
            client=self.truck.client,
            truck=self.truck,
            current_mileage=mileage,
            status='IN_PROGRESS',
        )

    def _add_work(self, order, work_name, group_name='Загальні'):
        group = WorkGroup.objects.create(name=group_name, hourly_rate=Decimal('500'))
        price = WorkPrice.objects.create(
            work_group=group, name=work_name, standard_hours=Decimal('1')
        )
        return ServiceWork.objects.create(
            service_order=order, work=price, mechanic=self.mechanic
        )

    def test_engine_oil_last_km_updated_on_done(self):
        """Заміна оливи двигуна → engine_oil_last_km = current_mileage"""
        order = self._make_order(mileage=95000)
        self._add_work(order, 'Заміна оливи в двигуні')

        order.status = ServiceOrder.StatusChoices.DONE
        order.save()

        intervals = TruckMaintenanceIntervals.objects.get(truck=self.truck)
        self.assertEqual(intervals.engine_oil_last_km, 95000)

    def test_gearbox_oil_last_km_updated_on_done(self):
        """Заміна оливи КПП → gearbox_oil_last_km = current_mileage"""
        order = self._make_order(mileage=80000)
        self._add_work(order, 'Заміна оливи КПП')

        order.status = ServiceOrder.StatusChoices.DONE
        order.save()

        intervals = TruckMaintenanceIntervals.objects.get(truck=self.truck)
        self.assertEqual(intervals.gearbox_oil_last_km, 80000)

    def test_no_update_without_mileage(self):
        """Без пробігу інтервали не оновлюються"""
        order = self._make_order(mileage=None)
        self._add_work(order, 'Заміна оливи в двигуні')

        order.status = ServiceOrder.StatusChoices.DONE
        order.save()

        self.assertFalse(TruckMaintenanceIntervals.objects.filter(truck=self.truck).exists())

    def test_no_update_for_non_maintenance_work(self):
        """Звичайна робота (не ТО) — інтервали не чіпаємо"""
        order = self._make_order(mileage=70000)
        self._add_work(order, 'Ремонт бампера')

        order.status = ServiceOrder.StatusChoices.DONE
        order.save()

        self.assertFalse(TruckMaintenanceIntervals.objects.filter(truck=self.truck).exists())

    def test_intervals_reverted_when_status_returns_from_done(self):
        """Якщо статус повертається з DONE — інтервали відновлюються зі знімку"""
        order = self._make_order(mileage=100000)
        self._add_work(order, 'Заміна оливи в двигуні')

        intervals = TruckMaintenanceIntervals.objects.create(
            truck=self.truck, engine_oil_last_km=85000
        )

        order.status = ServiceOrder.StatusChoices.DONE
        order.save()
        intervals.refresh_from_db()
        self.assertEqual(intervals.engine_oil_last_km, 100000)

        order.status = ServiceOrder.StatusChoices.IN_PROGRESS
        order.save()
        intervals.refresh_from_db()
        self.assertEqual(intervals.engine_oil_last_km, 85000)
