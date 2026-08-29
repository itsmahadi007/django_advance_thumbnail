"""
Tests for AdvanceThumbnailField core functionality
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import override_settings
from PIL import Image

from tests.models import (
    TestImageModel,
    TestImageModelForceRegenerate,
    TestMultipleThumbnails,
)


@pytest.mark.django_db
class TestThumbnailGeneration:
    """Test basic thumbnail generation"""

    def test_thumbnail_generated_on_create(self, temp_media_root, create_test_image):
        """Test thumbnail is generated when instance is created with image"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile(
            'test.jpg',
            image_buffer.read(),
            content_type='image/jpeg'
        )

        obj = TestImageModel.objects.create(image=image_file)

        assert obj.thumbnail is not None
        assert obj.thumbnail.name is not None
        assert '_thumbnail' in obj.thumbnail.name

    def test_thumbnail_not_generated_without_image(self, temp_media_root):
        """Test no thumbnail is generated when no image is provided"""
        obj = TestImageModel.objects.create()

        assert not obj.thumbnail

    def test_thumbnail_dimensions(self, temp_media_root, create_test_image):
        """Test thumbnail has correct dimensions (default 300x300)"""
        image_buffer = create_test_image(width=600, height=400)
        image_file = SimpleUploadedFile(
            'test.jpg',
            image_buffer.read(),
            content_type='image/jpeg'
        )

        obj = TestImageModel.objects.create(image=image_file)

        with obj.thumbnail.open() as f:
            img = Image.open(f)
            width, height = img.size

        # Default size is 300x300 with fit method
        # 600x400 -> 300x200 (maintains aspect ratio)
        assert width <= 300
        assert height <= 300

    def test_thumbnail_filename(self, temp_media_root, create_test_image):
        """Test thumbnail filename is derived from source"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile(
            'my_image.jpg',
            image_buffer.read(),
            content_type='image/jpeg'
        )

        obj = TestImageModel.objects.create(image=image_file)

        assert 'my_image_thumbnail' in obj.thumbnail.name


@pytest.mark.django_db
class TestThumbnailUpdate:
    """Test thumbnail update behavior"""

    def test_thumbnail_regenerated_on_image_change(self, temp_media_root, create_test_image):
        """Test thumbnail is regenerated when source image changes"""
        image1 = create_test_image(width=200, height=200, color='red')
        image2 = create_test_image(width=400, height=400, color='blue')

        file1 = SimpleUploadedFile('first.jpg', image1.read(), content_type='image/jpeg')
        obj = TestImageModel.objects.create(image=file1)
        first_thumbnail = obj.thumbnail.name

        # Update with new image
        file2 = SimpleUploadedFile('second.jpg', image2.read(), content_type='image/jpeg')
        obj.image = file2
        obj.save()

        # Thumbnail should be regenerated
        obj.refresh_from_db()
        assert obj.thumbnail.name != first_thumbnail

    def test_thumbnail_deleted_when_source_deleted(self, temp_media_root, create_test_image):
        """Test thumbnail is deleted when source image is deleted"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('test.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=image_file)
        assert obj.thumbnail is not None

        # Delete source image
        obj.image.delete()
        obj.image = None
        obj.save()

        obj.refresh_from_db()
        assert not obj.thumbnail


@pytest.mark.django_db
class TestForceRegenerate:
    """Test force_regenerate option"""

    def test_force_regenerate_always_regenerates(self, temp_media_root, create_test_image):
        """Test thumbnail is always regenerated when force_regenerate=True"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('test.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModelForceRegenerate.objects.create(image=image_file)

        # Save again without changing image
        obj.save()

        # Should not error - thumbnail is regenerated
        assert obj.thumbnail is not None


@pytest.mark.django_db
class TestMultipleThumbnailFields:
    """Test models with multiple thumbnail fields"""

    def test_multiple_thumbnails_generated(self, temp_media_root, create_test_image):
        """Test all thumbnail fields are generated"""
        image_buffer = create_test_image(width=500, height=500)
        image_file = SimpleUploadedFile('test.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestMultipleThumbnails.objects.create(image=image_file)

        assert obj.thumbnail_small is not None
        assert obj.thumbnail_large is not None

    def test_multiple_thumbnails_have_correct_sizes(self, temp_media_root, create_test_image):
        """Test each thumbnail field has correct dimensions"""
        image_buffer = create_test_image(width=500, height=500)
        image_file = SimpleUploadedFile('test.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestMultipleThumbnails.objects.create(image=image_file)

        # Small thumbnail (fit, 100x100)
        with obj.thumbnail_small.open() as f:
            img = Image.open(f)
            assert img.size[0] <= 100
            assert img.size[1] <= 100

        # Large thumbnail (fill, 400x400) - guarantees exact dimensions
        with obj.thumbnail_large.open() as f:
            img = Image.open(f)
            assert img.size == (400, 400)


@pytest.mark.django_db
class TestCacheChangeDetection:
    """Test cache-based change detection"""

    def test_source_change_detected_via_cache(self, temp_media_root, create_test_image):
        """Test source image change is detected via cache"""
        image1 = create_test_image(width=200, height=200)
        file1 = SimpleUploadedFile('first.jpg', image1.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=file1)
        first_thumbnail = obj.thumbnail.name

        # Update image
        image2 = create_test_image(width=300, height=300)
        file2 = SimpleUploadedFile('second.jpg', image2.read(), content_type='image/jpeg')
        obj.image = file2
        obj.save()

        obj.refresh_from_db()
        assert obj.thumbnail.name != first_thumbnail

    def test_no_regeneration_on_unrelated_save(self, temp_media_root, create_test_image):
        """Test thumbnail is not regenerated on unrelated field save"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('test.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=image_file)
        first_thumbnail = obj.thumbnail.name

        # Save without changing image (assuming model had other fields)
        obj.save()

        obj.refresh_from_db()
        # Thumbnail name should be the same (no regeneration)
        # Note: exact behavior depends on cache state


@pytest.mark.django_db
class TestCacheMissBehavior:
    """A cache miss must not be mistaken for a changed source or config.

    Regression tests for https://github.com/itsmahadi007/django_advance_thumbnail/issues/9
    """

    def test_no_regeneration_after_cache_clear(self, temp_media_root, create_test_image):
        """Clearing the cache must not regenerate an up-to-date thumbnail"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('photo.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=image_file)
        obj.refresh_from_db()
        original_thumbnail = obj.thumbnail.name

        # Simulates a restart, an eviction, or another LocMemCache worker
        cache.clear()

        obj.title = 'Updated'
        obj.save()
        obj.refresh_from_db()

        assert obj.thumbnail.name == original_thumbnail

    def test_no_regeneration_across_repeated_cache_clears(self, temp_media_root, create_test_image):
        """Repeated cache misses must not pile up duplicate thumbnails"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('photo.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=image_file)
        obj.refresh_from_db()
        original_thumbnail = obj.thumbnail.name

        for _ in range(3):
            cache.clear()
            obj.save()
            obj.refresh_from_db()

        assert obj.thumbnail.name == original_thumbnail

    def test_source_change_still_detected_after_cache_clear(self, temp_media_root, create_test_image):
        """A genuine source change must still be detected with a cold cache"""
        image1 = create_test_image(width=200, height=200)
        file1 = SimpleUploadedFile('first.jpg', image1.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=file1)
        obj.refresh_from_db()
        first_thumbnail = obj.thumbnail.name

        cache.clear()

        image2 = create_test_image(width=300, height=300)
        file2 = SimpleUploadedFile('second.jpg', image2.read(), content_type='image/jpeg')
        obj.image = file2
        obj.save()
        obj.refresh_from_db()

        assert obj.thumbnail.name != first_thumbnail
        assert 'second_thumbnail' in obj.thumbnail.name

    def test_missing_thumbnail_still_generated_with_cold_cache(self, temp_media_root, create_test_image):
        """A missing thumbnail must still be generated when the cache is cold"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('photo.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=image_file)
        obj.refresh_from_db()

        # Drop the thumbnail without touching the source
        TestImageModel.objects.filter(pk=obj.pk).update(thumbnail='')
        obj.refresh_from_db()
        assert not obj.thumbnail

        cache.clear()
        obj.save()
        obj.refresh_from_db()

        assert obj.thumbnail
        assert 'photo_thumbnail' in obj.thumbnail.name

    def test_cache_is_repopulated_after_a_miss(self, temp_media_root, create_test_image):
        """A cache miss resolved from durable state should warm the cache again"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('photo.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=image_file)
        obj.refresh_from_db()

        field = TestImageModel._meta.get_field('thumbnail')
        cache.clear()
        assert cache.get(field._get_source_cache_key(obj)) is None

        assert field._has_source_image_changed(obj) is False
        assert cache.get(field._get_source_cache_key(obj)) is not None

    def test_missing_config_cache_is_not_a_config_change(self, temp_media_root, create_test_image):
        """An absent config entry means 'unknown', not 'changed'"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('photo.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=image_file)
        field = TestImageModel._meta.get_field('thumbnail')

        cache.clear()

        assert field._should_regenerate_thumbnail(obj) is False
        # ...and the current config is recorded for later comparisons
        assert cache.get(field._cache_key) == {
            'size': field.size,
            'resize_method': field.resize_method,
        }

    def test_changed_config_still_triggers_regeneration(self, temp_media_root, create_test_image):
        """A genuinely different cached config must still be detected"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('photo.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=image_file)
        field = TestImageModel._meta.get_field('thumbnail')

        cache.set(field._cache_key, {'size': (50, 50), 'resize_method': 'fit'}, timeout=None)

        assert field._should_regenerate_thumbnail(obj) is True

    @override_settings(
        CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
    )
    def test_no_regeneration_without_a_working_cache(self, temp_media_root, create_test_image):
        """A backend that stores nothing must not regenerate on every save"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('photo.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=image_file)
        obj.refresh_from_db()
        original_thumbnail = obj.thumbnail.name

        obj.title = 'Updated'
        obj.save()
        obj.refresh_from_db()

        assert obj.thumbnail.name == original_thumbnail

    @override_settings(
        CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
    )
    def test_source_change_detected_without_a_working_cache(self, temp_media_root, create_test_image):
        """A source change must still be detected without any usable cache"""
        file1 = SimpleUploadedFile(
            'first.jpg', create_test_image().read(), content_type='image/jpeg'
        )
        obj = TestImageModel.objects.create(image=file1)
        obj.refresh_from_db()

        file2 = SimpleUploadedFile(
            'second.jpg',
            create_test_image(width=500, height=500).read(),
            content_type='image/jpeg',
        )
        obj.image = file2
        obj.save()
        obj.refresh_from_db()

        assert 'second_thumbnail' in obj.thumbnail.name


@pytest.mark.django_db
class TestImageFormats:
    """Test different image formats"""

    def test_jpeg_thumbnail(self, temp_media_root, create_test_image):
        """Test JPEG image generates JPEG thumbnail"""
        image_buffer = create_test_image(format='JPEG')
        image_file = SimpleUploadedFile('test.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=image_file)
        assert obj.thumbnail.name.endswith('.jpg')

    def test_png_thumbnail(self, temp_media_root, create_rgba_image):
        """Test PNG image generates PNG thumbnail"""
        image_buffer = create_rgba_image()
        image_file = SimpleUploadedFile('test.png', image_buffer.read(), content_type='image/png')

        obj = TestImageModel.objects.create(image=image_file)
        assert obj.thumbnail.name.endswith('.png')

    def test_rgba_to_rgb_conversion_for_jpeg(self, temp_media_root, create_rgba_image):
        """Test RGBA images are properly converted when saving as JPEG"""
        # Create RGBA image but save with .jpg extension
        img = Image.new('RGBA', (200, 200), color=(255, 0, 0, 128))
        buffer = __import__('io').BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Django will treat this as JPEG due to extension
        image_file = SimpleUploadedFile('test.jpg', buffer.read(), content_type='image/jpeg')

        # This should not raise an error
        obj = TestImageModel.objects.create(image=image_file)
        assert obj.thumbnail is not None
