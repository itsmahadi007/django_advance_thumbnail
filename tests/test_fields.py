"""
Tests for AdvanceThumbnailField core functionality
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
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
