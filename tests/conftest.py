"""
Pytest configuration and fixtures for django_advance_thumbnail tests
"""
import io
import os
import shutil
import tempfile

import django
import pytest
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')


def pytest_configure():
    """Configure Django settings before running tests"""
    django.setup()


@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    """Setup the test database"""
    from django.core.management import call_command
    with django_db_blocker.unblock():
        call_command('migrate', '--run-syncdb', verbosity=0)


@pytest.fixture
def temp_media_root(settings, tmp_path):
    """Create a temporary media root for tests"""
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.fixture
def create_test_image():
    """Factory fixture to create test images with specified dimensions"""
    def _create_image(width=400, height=300, color='red', format='JPEG'):
        img = Image.new('RGB', (width, height), color=color)
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        buffer.seek(0)
        buffer.name = f'test_image_{width}x{height}.jpg'
        return buffer
    return _create_image


@pytest.fixture
def create_rgba_image():
    """Factory fixture to create RGBA test images (PNG with transparency)"""
    def _create_image(width=400, height=300):
        img = Image.new('RGBA', (width, height), color=(255, 0, 0, 128))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        buffer.name = f'test_image_{width}x{height}.png'
        return buffer
    return _create_image


@pytest.fixture
def create_wide_image(create_test_image):
    """Create a wide landscape image (400x100)"""
    return create_test_image(width=400, height=100)


@pytest.fixture
def create_tall_image(create_test_image):
    """Create a tall portrait image (100x400)"""
    return create_test_image(width=100, height=400)


@pytest.fixture
def create_square_image(create_test_image):
    """Create a square image (300x300)"""
    return create_test_image(width=300, height=300)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test"""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()
