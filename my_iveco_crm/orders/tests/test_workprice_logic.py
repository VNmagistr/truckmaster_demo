from django.test import TestCase
from decimal import Decimal
from orders.models import WorkGroup, WorkPrice


class WorkPriceLogicTest(TestCase):
    """Тести для логіки розрахунку ціни робіт"""
    
    def setUp(self):
        """Створюємо тестові дані"""
        self.work_group = WorkGroup.objects.create(
            name='Двигун',
            hourly_rate=Decimal('600.00')
        )
    
    def test_price_calculation_basic(self):
        """Тест базового розрахунку ціни"""
        work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Заміна оливи',
            standard_hours=Decimal('1.5')
        )
        
        expected_price = Decimal('900.00')  # 1.5 * 600
        self.assertEqual(work.price, expected_price)
    
    def test_price_calculation_property(self):
        """Тест що price є property, а не поле БД"""
        work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Діагностика',
            standard_hours=Decimal('0.5')
        )
        
        # Перевіряємо що price - це property
        self.assertIsInstance(
            type(work).price,
            property
        )
        
        # Перевіряємо розрахунок
        self.assertEqual(work.price, Decimal('300.00'))
    
    def test_price_changes_with_hourly_rate(self):
        """Тест що ціна змінюється при зміні ставки категорії"""
        work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Ремонт',
            standard_hours=Decimal('2.0')
        )
        
        # Початкова ціна: 2.0 * 600 = 1200
        self.assertEqual(work.price, Decimal('1200.00'))
        
        # Змінюємо ставку категорії
        self.work_group.hourly_rate = Decimal('700.00')
        self.work_group.save()
        
        # Оновлюємо work з БД
        work.refresh_from_db()
        
        # Нова ціна: 2.0 * 700 = 1400
        self.assertEqual(work.price, Decimal('1400.00'))
    
    def test_get_calculated_price_method(self):
        """Тест методу get_calculated_price для backward compatibility"""
        work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='ТО',
            standard_hours=Decimal('3.0')
        )
        
        # Метод має повертати те саме що й property
        self.assertEqual(
            work.get_calculated_price(),
            work.price
        )
        self.assertEqual(
            work.get_calculated_price(),
            Decimal('1800.00')  # 3.0 * 600
        )
    
    def test_zero_hours_calculation(self):
        """Тест розрахунку при нульових годинах"""
        work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Консультація',
            standard_hours=Decimal('0')
        )
        
        self.assertEqual(work.price, Decimal('0'))
    
    def test_fractional_hours_calculation(self):
        """Тест розрахунку з дробовими годинами"""
        work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Швидка перевірка',
            standard_hours=Decimal('0.25')  # 15 хвилин
        )
        
        expected_price = Decimal('150.00')  # 0.25 * 600
        self.assertEqual(work.price, expected_price)
    
    def test_str_representation(self):
        """Тест строкового представлення"""
        work = WorkPrice.objects.create(
            work_group=self.work_group,
            name='Заміна фільтрів',
            standard_hours=Decimal('1.0')
        )
        
        expected_str = 'Заміна фільтрів'
        self.assertEqual(str(work), expected_str)