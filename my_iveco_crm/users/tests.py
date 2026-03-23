from django.test import TestCase
from django.contrib.auth.models import User

from inventory.models import Warehouse
from users.models import UserProfile


def make_user(username, role, is_superuser=False):
    user = User.objects.create_user(username=username, password='pass')
    if is_superuser:
        user.is_superuser = True
        user.save(update_fields=['is_superuser'])
    UserProfile.objects.update_or_create(user=user, defaults={'role': role})
    user.profile.refresh_from_db()
    return user.profile


class UserProfileAutoCreationTest(TestCase):
    """UserProfile is created automatically via post_save signal."""

    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(username='newuser', password='pass')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsNotNone(user.profile.pk)

    def test_default_role_is_mechanic(self):
        user = User.objects.create_user(username='newuser', password='pass')
        self.assertEqual(user.profile.role, 'mechanic')

    def test_str_representation(self):
        user = User.objects.create_user(
            username='ivan', password='pass',
            first_name='Іван', last_name='Коваль',
        )
        UserProfile.objects.update_or_create(user=user, defaults={'role': 'mechanic'})
        self.assertIn('Іван Коваль', str(user.profile))
        self.assertIn('Механік', str(user.profile))


class UserProfileRolePropertiesTest(TestCase):
    """Tests for is_*_role properties."""

    # ── is_admin_role ───────────────────────────────────────────────────────

    def test_admin_role_is_admin(self):
        self.assertTrue(make_user('u', 'admin').is_admin_role)

    def test_superuser_is_admin_regardless_of_role(self):
        self.assertTrue(make_user('u', 'mechanic', is_superuser=True).is_admin_role)

    def test_manager_is_not_admin(self):
        self.assertFalse(make_user('u', 'manager').is_admin_role)

    def test_mechanic_is_not_admin(self):
        self.assertFalse(make_user('u', 'mechanic').is_admin_role)

    # ── is_manager_role ─────────────────────────────────────────────────────

    def test_manager_role_is_manager(self):
        self.assertTrue(make_user('u', 'manager').is_manager_role)

    def test_admin_role_is_also_manager(self):
        self.assertTrue(make_user('u', 'admin').is_manager_role)

    def test_superuser_is_manager_regardless_of_role(self):
        self.assertTrue(make_user('u', 'mechanic', is_superuser=True).is_manager_role)

    def test_mechanic_is_not_manager(self):
        self.assertFalse(make_user('u', 'mechanic').is_manager_role)

    # ── other roles ─────────────────────────────────────────────────────────

    def test_mechanic_role(self):
        profile = make_user('u', 'mechanic')
        self.assertTrue(profile.is_mechanic_role)
        self.assertFalse(make_user('u2', 'admin').is_mechanic_role)

    def test_storekeeper_role(self):
        profile = make_user('u', 'storekeeper')
        self.assertTrue(profile.is_storekeeper_role)
        self.assertFalse(make_user('u2', 'mechanic').is_storekeeper_role)

    def test_accountant_role(self):
        profile = make_user('u', 'accountant')
        self.assertTrue(profile.is_accountant_role)
        self.assertFalse(make_user('u2', 'mechanic').is_accountant_role)


class UserProfileWarehouseAccessTest(TestCase):
    """Tests for can_access_warehouse."""

    def setUp(self):
        self.warehouse = Warehouse.objects.create(name='Main', is_default=True)

    def test_admin_can_access_any_warehouse(self):
        self.assertTrue(make_user('u', 'admin').can_access_warehouse(self.warehouse))

    def test_manager_can_access_any_warehouse(self):
        self.assertTrue(make_user('u', 'manager').can_access_warehouse(self.warehouse))

    def test_mechanic_without_assignment_cannot_access(self):
        self.assertFalse(make_user('u', 'mechanic').can_access_warehouse(self.warehouse))

    def test_mechanic_with_assignment_can_access(self):
        profile = make_user('u', 'mechanic')
        profile.warehouses.add(self.warehouse)
        self.assertTrue(profile.can_access_warehouse(self.warehouse))

    def test_storekeeper_with_assignment_can_access(self):
        profile = make_user('u', 'storekeeper')
        profile.warehouses.add(self.warehouse)
        self.assertTrue(profile.can_access_warehouse(self.warehouse))


class UserProfilePermissionsTest(TestCase):
    """Tests for can_view / can_edit / can_create / can_delete per role."""

    def test_admin_can_delete_clients(self):
        self.assertTrue(make_user('u', 'admin').can_delete('clients'))

    def test_manager_cannot_delete_clients(self):
        self.assertFalse(make_user('u', 'manager').can_delete('clients'))

    def test_mechanic_can_view_orders(self):
        self.assertTrue(make_user('u', 'mechanic').can_view('orders'))

    def test_mechanic_cannot_view_financial(self):
        self.assertFalse(make_user('u', 'mechanic').can_view('financial'))

    def test_storekeeper_can_edit_stock(self):
        self.assertTrue(make_user('u', 'storekeeper').can_edit('stock'))

    def test_storekeeper_cannot_edit_clients(self):
        self.assertFalse(make_user('u', 'storekeeper').can_edit('clients'))

    def test_accountant_can_view_financial(self):
        self.assertTrue(make_user('u', 'accountant').can_view('financial'))

    def test_accountant_cannot_edit_orders(self):
        self.assertFalse(make_user('u', 'accountant').can_edit('orders'))

    def test_superuser_can_do_everything(self):
        profile = make_user('u', 'mechanic', is_superuser=True)
        for action in ('view', 'edit', 'create', 'delete'):
            for section in ('clients', 'orders', 'stock', 'financial'):
                self.assertTrue(
                    getattr(profile, f'can_{action}')(section),
                    msg=f'superuser should can_{action}({section})',
                )

    def test_unknown_role_has_no_permissions(self):
        profile = make_user('u', 'mechanic')
        # Manually set a non-existent role bypassing choices validation
        UserProfile.objects.filter(pk=profile.pk).update(role='ghost')
        profile.refresh_from_db()
        self.assertFalse(profile.can_view('clients'))
        self.assertFalse(profile.can_edit('orders'))
