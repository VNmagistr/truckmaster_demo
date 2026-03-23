from django.test import TestCase, RequestFactory
from django.http import HttpResponse

from core.middleware import ModuleMiddleware
from core.models import Module
from core.registry import _REGISTRY, register_module, clear_module_cache

TEST_PREFIX = '/api/test-module/'


def _ok_view(request):
    return HttpResponse('ok', status=200)


class ModuleMiddlewareTest(TestCase):
    """Tests for ModuleMiddleware — URL-level module gating."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ModuleMiddleware(get_response=_ok_view)

        # Register a fake optional module for isolation
        self._original_registry = dict(_REGISTRY)
        register_module({
            'name': 'test_module',
            'label': 'Тестовий модуль',
            'is_core': False,
            'url_prefixes': [TEST_PREFIX],
        })
        clear_module_cache('test_module')

    def tearDown(self):
        # Restore registry to original state
        _REGISTRY.clear()
        _REGISTRY.update(self._original_registry)
        clear_module_cache('test_module')

    def _get(self, path):
        return self.middleware(self.factory.get(path))

    # ── Disabled module ─────────────────────────────────────────────────────

    def test_disabled_module_returns_503(self):
        """Request to a disabled module URL must return 503."""
        Module.objects.create(name='test_module', label='Тестовий модуль', is_enabled=False)
        clear_module_cache('test_module')

        response = self._get(TEST_PREFIX + 'anything/')

        self.assertEqual(response.status_code, 503)

    def test_disabled_module_response_contains_module_name(self):
        """503 response must include module name for frontend error handling."""
        Module.objects.create(name='test_module', label='Тестовий модуль', is_enabled=False)
        clear_module_cache('test_module')

        import json
        data = json.loads(self._get(TEST_PREFIX).content)

        self.assertEqual(data['module'], 'test_module')
        self.assertIn('error', data)

    # ── Enabled module ──────────────────────────────────────────────────────

    def test_enabled_module_passes_request(self):
        """Request to an enabled module URL must pass through."""
        Module.objects.create(name='test_module', label='Тестовий модуль', is_enabled=True)
        clear_module_cache('test_module')

        response = self._get(TEST_PREFIX)

        self.assertEqual(response.status_code, 200)

    def test_unknown_module_passes_request(self):
        """If module is not in DB, it defaults to enabled — request must pass."""
        # No Module record created intentionally
        clear_module_cache('test_module')

        response = self._get(TEST_PREFIX)

        self.assertEqual(response.status_code, 200)

    # ── Core module ─────────────────────────────────────────────────────────

    def test_core_module_always_passes(self):
        """Core modules must never be blocked, even if DB record says disabled."""
        register_module({
            'name': 'test_core',
            'label': 'Тестовий core-модуль',
            'is_core': True,
            'url_prefixes': ['/api/test-core/'],
        })
        Module.objects.create(name='test_core', label='Тестовий core-модуль', is_enabled=False)
        clear_module_cache('test_core')

        response = self._get('/api/test-core/something/')

        self.assertEqual(response.status_code, 200)

    # ── Unrelated URL ───────────────────────────────────────────────────────

    def test_unrelated_url_always_passes(self):
        """URL not matching any module prefix must always pass through."""
        Module.objects.create(name='test_module', label='Тестовий модуль', is_enabled=False)
        clear_module_cache('test_module')

        response = self._get('/api/orders/')

        self.assertEqual(response.status_code, 200)

    def test_partial_prefix_match_does_not_block(self):
        """A URL that only partially matches the prefix must not be blocked."""
        Module.objects.create(name='test_module', label='Тестовий модуль', is_enabled=False)
        clear_module_cache('test_module')

        # '/api/test-module-other/' starts differently from '/api/test-module/'
        response = self._get('/api/test-module-other/')

        self.assertEqual(response.status_code, 200)
