"""
Tests for resize methods (fit, fill, cover)
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io

from tests.models import TestImageModelFit, TestImageModelFill


@pytest.mark.django_db
class TestResizeMethodFit:
    """Test RESIZE_FIT method - maintains aspect ratio, may be smaller than size"""

    def test_fit_wide_image(self, temp_media_root, create_test_image):
        """Wide image (400x100) with size=(150,150) should become 150x37"""
        image_buffer = create_test_image(width=400, height=100)
        image_file = SimpleUploadedFile(
            'wide.jpg',
            image_buffer.read(),
            content_type='image/jpeg'
        )

        obj = TestImageModelFit.objects.create(image=image_file)

        assert obj.thumbnail is not None
        assert obj.thumbnail.name is not None

        # Open and check dimensions
        with obj.thumbnail.open() as f:
            img = Image.open(f)
            width, height = img.size

        # With fit, aspect ratio is maintained
        # 400x100 -> max 150 width -> 150x37 (150/400 * 100 = 37.5)
        assert width == 150
        assert height <= 150  # Aspect ratio maintained, height will be ~37

    def test_fit_tall_image(self, temp_media_root, create_test_image):
        """Tall image (100x400) with size=(150,150) should become 37x150"""
        image_buffer = create_test_image(width=100, height=400)
        image_file = SimpleUploadedFile(
            'tall.jpg',
            image_buffer.read(),
            content_type='image/jpeg'
        )

        obj = TestImageModelFit.objects.create(image=image_file)

        with obj.thumbnail.open() as f:
            img = Image.open(f)
            width, height = img.size

        # 100x400 -> max 150 height -> 37x150
        assert height == 150
        assert width <= 150

    def test_fit_square_image(self, temp_media_root, create_test_image):
        """Square image (300x300) with size=(150,150) should become 150x150"""
        image_buffer = create_test_image(width=300, height=300)
        image_file = SimpleUploadedFile(
            'square.jpg',
            image_buffer.read(),
            content_type='image/jpeg'
        )

        obj = TestImageModelFit.objects.create(image=image_file)

        with obj.thumbnail.open() as f:
            img = Image.open(f)
            width, height = img.size

        assert width == 150
        assert height == 150


@pytest.mark.django_db
class TestResizeMethodFill:
    """Test RESIZE_FILL method - guarantees exact dimensions by cropping"""

    def test_fill_wide_image_guarantees_dimensions(self, temp_media_root, create_test_image):
        """Wide image with fill should be exactly 150x150"""
        image_buffer = create_test_image(width=400, height=100)
        image_file = SimpleUploadedFile(
            'wide.jpg',
            image_buffer.read(),
            content_type='image/jpeg'
        )

        obj = TestImageModelFill.objects.create(image=image_file)

        with obj.thumbnail.open() as f:
            img = Image.open(f)
            width, height = img.size

        # Fill guarantees exact dimensions
        assert width == 150
        assert height == 150

    def test_fill_tall_image_guarantees_dimensions(self, temp_media_root, create_test_image):
        """Tall image with fill should be exactly 150x150"""
        image_buffer = create_test_image(width=100, height=400)
        image_file = SimpleUploadedFile(
            'tall.jpg',
            image_buffer.read(),
            content_type='image/jpeg'
        )

        obj = TestImageModelFill.objects.create(image=image_file)

        with obj.thumbnail.open() as f:
            img = Image.open(f)
            width, height = img.size

        assert width == 150
        assert height == 150

    def test_fill_square_image(self, temp_media_root, create_test_image):
        """Square image with fill should be exactly 150x150"""
        image_buffer = create_test_image(width=300, height=300)
        image_file = SimpleUploadedFile(
            'square.jpg',
            image_buffer.read(),
            content_type='image/jpeg'
        )

        obj = TestImageModelFill.objects.create(image=image_file)

        with obj.thumbnail.open() as f:
            img = Image.open(f)
            width, height = img.size

        assert width == 150
        assert height == 150

    def test_fill_very_wide_image(self, temp_media_root, create_test_image):
        """Very wide image (800x50) with fill should still be exactly 150x150"""
        image_buffer = create_test_image(width=800, height=50)
        image_file = SimpleUploadedFile(
            'very_wide.jpg',
            image_buffer.read(),
            content_type='image/jpeg'
        )

        obj = TestImageModelFill.objects.create(image=image_file)

        with obj.thumbnail.open() as f:
            img = Image.open(f)
            width, height = img.size

        # This is the key test for the reported issue
        # fill/cover mode guarantees BOTH dimensions meet the minimum
        assert width == 150
        assert height == 150


@pytest.mark.django_db
class TestResizeMethodComparison:
    """Compare fit vs fill behavior"""

    def test_fit_vs_fill_on_extreme_aspect_ratio(self, temp_media_root, create_test_image):
        """Compare fit and fill on extreme aspect ratio image"""
        # Create a very wide image
        image_buffer_fit = create_test_image(width=600, height=100)
        image_buffer_fill = create_test_image(width=600, height=100)

        # Test with fit model
        fit_file = SimpleUploadedFile(
            'fit.jpg',
            image_buffer_fit.read(),
            content_type='image/jpeg'
        )
        obj_fit = TestImageModelFit.objects.create(image=fit_file)

        with obj_fit.thumbnail.open() as f:
            img_fit = Image.open(f)
            fit_width, fit_height = img_fit.size

        # Test with fill model
        fill_file = SimpleUploadedFile(
            'fill.jpg',
            image_buffer_fill.read(),
            content_type='image/jpeg'
        )
        obj_fill = TestImageModelFill.objects.create(image=fill_file)

        with obj_fill.thumbnail.open() as f:
            img_fill = Image.open(f)
            fill_width, fill_height = img_fill.size

        # Fit: maintains ratio, may have one dimension smaller
        # 600x100 -> 150x25 (150/600 * 100 = 25)
        assert fit_width == 150
        assert fit_height < 150  # Will be ~25

        # Fill: guarantees exact dimensions by cropping
        assert fill_width == 150
        assert fill_height == 150
