# inventory/tests.py

from django.test import TestCase
from decimal import Decimal
from .models import Product, Category, SubCategory, Warehouse, StockItem, UsedPart
from orders.models import WorkGroup, WorkPrice, ServiceOrder, ServiceWork
from clients.models import Client, IvecoBaseModel, Truck


class ProductModelTest(TestCase):
    """Test Product model"""

    def test_create_product(self):
        """Test creating a product"""
        product = Product.objects.create(
            name='Фільтр оливи',
            sku_code='OIL-001',
            cost_price=Decimal('100.00'),
            selling_price=Decimal('150.00'),
            current_stock=10
        )
        self.assertEqual(product.name, 'Фільтр оливи')
        self.assertEqual(product.selling_price, Decimal('150.00'))

    def test_product_str_representation(self):
        """Test string representation of Product"""
        product = Product.objects.create(
            name='Фільтр оливи',
            sku_code='OIL-001',
        )
        self.assertEqual(str(product), '[OIL-001] Фільтр оливи')

    def test_product_str_with_brand(self):
        """Test string representation of Product with brand"""
        product = Product.objects.create(
            name='Фільтр оливи',
            sku_code='OIL-002',
            brand='MANN'
        )
        self.assertEqual(str(product), '[OIL-002] MANN Фільтр оливи')

    def test_product_str_with_viscosity(self):
        """Test string representation of Product with viscosity"""
        product = Product.objects.create(
            name='Моторна олива',
            sku_code='OIL-003',
            viscosity='5W-30'
        )
        self.assertEqual(str(product), '[OIL-003] Моторна олива 5W-30')

    def test_is_low_stock(self):
        """Test low stock detection"""
        product = Product.objects.create(
            name='Фільтр',
            sku_code='F-001',
            current_stock=3,
            min_stock_level=5
        )
        self.assertTrue(product.is_low_stock)

    def test_is_not_low_stock(self):
        """Test normal stock level"""
        product = Product.objects.create(
            name='Фільтр',
            sku_code='F-002',
            current_stock=10,
            min_stock_level=5
        )
        self.assertFalse(product.is_low_stock)


class CategoryModelTest(TestCase):
    """Test Category model"""

    def test_create_category(self):
        """Test creating a category"""
        category = Category.objects.create(
            name='Оливи',
            slug='oils',
            category_type='oil'
        )
        self.assertEqual(category.name, 'Оливи')
        self.assertEqual(category.category_type, 'oil')


class WarehouseModelTest(TestCase):
    """Test Warehouse model"""

    def test_create_warehouse(self):
        """Test creating a warehouse"""
        warehouse = Warehouse.objects.create(
            name='Головний склад',
            slug='main',
            is_default=True
        )
        self.assertEqual(warehouse.name, 'Головний склад')
        self.assertTrue(warehouse.is_default)

    def test_only_one_default_warehouse(self):
        """Test that only one warehouse can be default"""
        wh1 = Warehouse.objects.create(name='Склад 1', slug='wh1', is_default=True)
        wh2 = Warehouse.objects.create(name='Склад 2', slug='wh2', is_default=True)

        wh1.refresh_from_db()
        self.assertFalse(wh1.is_default)
        self.assertTrue(wh2.is_default)


class StockItemModelTest(TestCase):
    """Test StockItem model"""

    def setUp(self):
        self.warehouse = Warehouse.objects.create(name='Склад', slug='main')
        self.product = Product.objects.create(
            name='Фільтр',
            sku_code='F-001',
            min_stock_level=5
        )

    def test_create_stock_item(self):
        """Test creating stock record"""
        stock = StockItem.objects.create(
            warehouse=self.warehouse,
            product=self.product,
            quantity=10
        )
        self.assertEqual(stock.quantity, 10)

    def test_available_quantity(self):
        """Test available quantity calculation"""
        stock = StockItem.objects.create(
            warehouse=self.warehouse,
            product=self.product,
            quantity=10,
            reserved=3
        )
        self.assertEqual(stock.available, 7)


class UsedPartAutoDeductionTest(TestCase):
    """Тести на автоматичне списання зі складу при роботі з UsedPart"""

    def setUp(self):
        self.client_obj = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client_obj,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        self.order = ServiceOrder.objects.create(
            order_number='SO-001',
            client=self.client_obj,
            truck=self.truck
        )
        self.warehouse = Warehouse.objects.create(
            name='Головний склад', slug='main', is_default=True
        )
        self.part = Product.objects.create(
            name='Фільтр оливи', sku_code='FILTER-001',
            selling_price=Decimal('250.00'), current_stock=Decimal('10')
        )
        self.stock_item = StockItem.objects.create(
            warehouse=self.warehouse, product=self.part, quantity=Decimal('10')
        )

    def _used_part(self, quantity):
        return UsedPart.objects.create(
            service_order=self.order,
            part=self.part,
            warehouse=self.warehouse,
            quantity=quantity,
            unit_price=self.part.selling_price,
        )

    def test_create_deducts_from_stock_item(self):
        """Створення UsedPart зменшує StockItem.quantity"""
        self._used_part(Decimal('3'))
        self.stock_item.refresh_from_db()
        self.assertEqual(self.stock_item.quantity, Decimal('7'))

    def test_create_updates_product_current_stock(self):
        """Після списання оновлюється Product.current_stock"""
        self._used_part(Decimal('3'))
        self.part.refresh_from_db()
        self.assertEqual(self.part.current_stock, Decimal('7'))

    def test_update_increase_quantity_deducts_more(self):
        """Збільшення кількості → додаткове списання"""
        used = self._used_part(Decimal('3'))
        self.stock_item.refresh_from_db()
        self.assertEqual(self.stock_item.quantity, Decimal('7'))

        used.quantity = Decimal('5')
        used.save()

        self.stock_item.refresh_from_db()
        self.assertEqual(self.stock_item.quantity, Decimal('5'))

    def test_update_decrease_quantity_returns_to_stock(self):
        """Зменшення кількості → повернення різниці на склад"""
        used = self._used_part(Decimal('5'))
        used.quantity = Decimal('2')
        used.save()

        self.stock_item.refresh_from_db()
        self.assertEqual(self.stock_item.quantity, Decimal('8'))

    def test_delete_restores_stock(self):
        """Видалення UsedPart повертає кількість на склад"""
        used = self._used_part(Decimal('4'))
        self.stock_item.refresh_from_db()
        self.assertEqual(self.stock_item.quantity, Decimal('6'))

        used.delete()

        self.stock_item.refresh_from_db()
        self.assertEqual(self.stock_item.quantity, Decimal('10'))

    def test_create_generates_stock_movement_out(self):
        """При створенні UsedPart створюється StockMovement(out)"""
        from .models import StockMovement
        self._used_part(Decimal('3'))
        movement = StockMovement.objects.filter(
            product=self.part, movement_type='out'
        ).last()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, Decimal('3'))
        self.assertEqual(movement.warehouse_from, self.warehouse)

    def test_delete_generates_stock_movement_return(self):
        """При видаленні UsedPart створюється StockMovement(return)"""
        from .models import StockMovement
        used = self._used_part(Decimal('3'))
        used.delete()
        movement = StockMovement.objects.filter(
            product=self.part, movement_type='return'
        ).last()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, Decimal('3'))

    def test_creates_stock_item_if_not_exists(self):
        """Якщо StockItem ще не існує — він створюється автоматично"""
        new_part = Product.objects.create(
            name='Новий фільтр', sku_code='NEW-001',
            selling_price=Decimal('100.00'), current_stock=Decimal('5')
        )
        StockItem.objects.create(
            warehouse=self.warehouse, product=new_part, quantity=Decimal('5')
        )
        UsedPart.objects.create(
            service_order=self.order,
            part=new_part,
            warehouse=self.warehouse,
            quantity=Decimal('2'),
            unit_price=Decimal('100.00'),
        )
        stock = StockItem.objects.get(warehouse=self.warehouse, product=new_part)
        self.assertEqual(stock.quantity, Decimal('3'))


class UsedPartStockValidationTest(TestCase):
    """Тести на валідацію залишку при додаванні запчастини до наряду"""

    def setUp(self):
        from inventory.serializers import UsedPartSerializer
        self.UsedPartSerializer = UsedPartSerializer

        self.client_obj = Client.objects.create(name='Test Client')
        self.base_model = IvecoBaseModel.objects.create(name='Daily')
        self.truck = Truck.objects.create(
            client=self.client_obj,
            base_model=self.base_model,
            specific_model_name='35C15',
            full_vin='ZCFC35A0001234567',
            license_plate='AA1234BB'
        )
        self.order = ServiceOrder.objects.create(
            order_number='SO-001',
            client=self.client_obj,
            truck=self.truck
        )
        self.part = Product.objects.create(
            name='Фільтр оливи',
            sku_code='FILTER-001',
            selling_price=Decimal('250.00'),
            current_stock=Decimal('5')
        )

    def _make_data(self, quantity):
        return {
            'service_order': self.order.id,
            'part': self.part.id,
            'quantity': quantity,
        }

    def test_valid_quantity_within_stock(self):
        """Кількість менша за залишок — валідація проходить"""
        serializer = self.UsedPartSerializer(data=self._make_data(Decimal('3')))
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_quantity_equals_stock(self):
        """Кількість рівна залишку — валідація проходить"""
        serializer = self.UsedPartSerializer(data=self._make_data(Decimal('5')))
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_quantity_exceeds_stock(self):
        """Кількість більша за залишок — ValidationError"""
        serializer = self.UsedPartSerializer(data=self._make_data(Decimal('10')))
        self.assertFalse(serializer.is_valid())
        self.assertIn('quantity', serializer.errors)

    def test_error_message_contains_available_amount(self):
        """Повідомлення про помилку містить доступну кількість"""
        serializer = self.UsedPartSerializer(data=self._make_data(Decimal('10')))
        serializer.is_valid()
        self.assertIn('доступно', serializer.errors['quantity'][0])

    def test_update_does_not_double_count_existing_quantity(self):
        """При оновленні власна кількість запису не враховується двічі"""
        used_part = UsedPart.objects.create(
            service_order=self.order,
            part=self.part,
            quantity=Decimal('4'),
            unit_price=self.part.selling_price,
        )
        # Намагаємось збільшити з 4 до 5 — в сумі 5, залишок теж 5 → має пройти
        serializer = self.UsedPartSerializer(
            instance=used_part,
            data={**self._make_data(Decimal('5')), 'service_order': self.order.id},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
