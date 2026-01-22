"""
Tests for thread-safety of thumbnail generation
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.signals import post_save

from django_advance_thumbnail.fields import AdvanceThumbnailField
from tests.models import TestImageModel


@pytest.mark.django_db
class TestThreadSafety:
    """Test thread-safety of thumbnail generation"""

    def test_instance_flag_prevents_recursion(self, temp_media_root, create_test_image):
        """Test that _generating_thumbnail flag prevents infinite recursion"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile(
            'test.jpg',
            image_buffer.read(),
            content_type='image/jpeg'
        )

        # Create instance - this should trigger thumbnail generation once
        obj = TestImageModel.objects.create(image=image_file)

        # The flag should be cleared after generation
        assert not getattr(obj, '_generating_thumbnail', False)

        # Thumbnail should exist
        assert obj.thumbnail is not None
        assert obj.thumbnail.name is not None

    def test_instance_flag_is_instance_specific(self, temp_media_root, create_test_image):
        """Test that the flag is on instance, not shared globally"""
        image_buffer1 = create_test_image(width=200, height=200)
        image_buffer2 = create_test_image(width=300, height=300)

        file1 = SimpleUploadedFile('test1.jpg', image_buffer1.read(), content_type='image/jpeg')
        file2 = SimpleUploadedFile('test2.jpg', image_buffer2.read(), content_type='image/jpeg')

        obj1 = TestImageModel.objects.create(image=file1)
        obj2 = TestImageModel.objects.create(image=file2)

        # Both should have thumbnails (flag is per-instance)
        assert obj1.thumbnail is not None
        assert obj2.thumbnail is not None

        # Flags should be cleared
        assert not getattr(obj1, '_generating_thumbnail', False)
        assert not getattr(obj2, '_generating_thumbnail', False)

    def test_signal_remains_connected_during_generation(self, temp_media_root, create_test_image):
        """
        Verify signal stays connected during thumbnail generation.
        The old implementation disconnected the signal, causing race conditions.
        """
        # Find the thumbnail field
        thumbnail_field = None
        for field in TestImageModel._meta.get_fields():
            if isinstance(field, AdvanceThumbnailField):
                thumbnail_field = field
                break

        assert thumbnail_field is not None

        # Create instance - this triggers thumbnail generation
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('test.jpg', image_buffer.read(), content_type='image/jpeg')
        obj = TestImageModel.objects.create(image=image_file)

        # Verify thumbnail was created (signal worked)
        assert obj.thumbnail is not None

        # Create another instance to verify signal still works
        image_buffer2 = create_test_image(width=300, height=300)
        image_file2 = SimpleUploadedFile('test2.jpg', image_buffer2.read(), content_type='image/jpeg')
        obj2 = TestImageModel.objects.create(image=image_file2)

        # Second object should also have thumbnail (signal is still connected)
        assert obj2.thumbnail is not None, "Signal was disconnected and not reconnected!"

    def test_flag_cleared_on_exception(self, temp_media_root, create_test_image, mocker):
        """Test that flag is cleared even if an error occurs during generation"""
        # Mock the _generate_thumbnail_file to raise an exception
        original_generate = AdvanceThumbnailField._generate_thumbnail_file

        def mock_generate(self, instance, source_field):
            raise Exception("Test exception")

        mocker.patch.object(AdvanceThumbnailField, '_generate_thumbnail_file', mock_generate)

        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('test.jpg', image_buffer.read(), content_type='image/jpeg')

        # Should not raise, error is caught and logged
        obj = TestImageModel.objects.create(image=image_file)

        # Flag should still be cleared despite exception
        assert not getattr(obj, '_generating_thumbnail', False)

    def test_multiple_saves_without_image_change(self, temp_media_root, create_test_image):
        """Test that saving multiple times doesn't cause issues"""
        image_buffer = create_test_image()
        image_file = SimpleUploadedFile('test.jpg', image_buffer.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=image_file)
        original_thumbnail = obj.thumbnail.name

        # Save multiple times
        obj.save()
        obj.save()
        obj.save()

        obj.refresh_from_db()
        # Should not raise, thumbnail should still exist
        assert obj.thumbnail is not None

    def test_rapid_sequential_creates(self, temp_media_root, create_test_image):
        """Test creating multiple instances rapidly in sequence"""
        objects = []
        for i in range(10):
            image_buffer = create_test_image(width=100 + i, height=100 + i)
            image_file = SimpleUploadedFile(
                f'rapid_{i}.jpg',
                image_buffer.read(),
                content_type='image/jpeg'
            )
            obj = TestImageModel.objects.create(image=image_file)
            objects.append(obj)

        # All should have thumbnails
        for i, obj in enumerate(objects):
            assert obj.thumbnail is not None, f"Object {i} missing thumbnail"
            assert not getattr(obj, '_generating_thumbnail', False)


@pytest.mark.django_db
class TestNoSignalDisconnect:
    """
    Tests to verify the signal disconnect pattern has been removed.
    The old implementation used signal disconnect/reconnect which caused
    race conditions in multi-threaded environments.
    """

    def test_create_thumbnail_uses_flag_not_disconnect(self, temp_media_root, create_test_image):
        """
        Verify the create_thumbnail method uses instance flag, not signal disconnect.
        """
        # Get the source code of create_thumbnail method
        import inspect
        source = inspect.getsource(AdvanceThumbnailField.create_thumbnail)

        # Should NOT contain actual signal disconnect calls (post_save.disconnect or models.signals...disconnect)
        assert 'post_save.disconnect' not in source, "create_thumbnail should not disconnect signals"
        assert '.disconnect(' not in source, "create_thumbnail should not call disconnect"

        # Should contain the instance flag check
        assert '_generating_thumbnail' in source, "create_thumbnail should use instance flag"

    def test_regenerate_thumbnails_uses_flag(self, temp_media_root, create_test_image):
        """Verify regenerate_thumbnails method uses instance flag"""
        import inspect
        source = inspect.getsource(AdvanceThumbnailField.regenerate_thumbnails)

        # Should contain the instance flag
        assert '_generating_thumbnail' in source, "regenerate_thumbnails should use instance flag"


@pytest.mark.django_db
class TestSequentialOperations:
    """Test sequential operations that simulate concurrent-like behavior"""

    def test_update_image_multiple_times(self, temp_media_root, create_test_image):
        """Test updating image multiple times in sequence"""
        image1 = create_test_image(width=200, height=200, color='red')
        file1 = SimpleUploadedFile('v1.jpg', image1.read(), content_type='image/jpeg')

        obj = TestImageModel.objects.create(image=file1)
        assert obj.thumbnail is not None

        # Update image multiple times
        for i in range(5):
            new_image = create_test_image(width=200 + i * 10, height=200 + i * 10)
            new_file = SimpleUploadedFile(f'v{i+2}.jpg', new_image.read(), content_type='image/jpeg')
            obj.image = new_file
            obj.save()

            obj.refresh_from_db()
            assert obj.thumbnail is not None, f"Thumbnail missing after update {i+1}"

    def test_create_delete_create_cycle(self, temp_media_root, create_test_image):
        """Test create-delete-create cycle"""
        for cycle in range(3):
            image_buffer = create_test_image(width=200 + cycle * 10, height=200 + cycle * 10)
            image_file = SimpleUploadedFile(
                f'cycle_{cycle}.jpg',
                image_buffer.read(),
                content_type='image/jpeg'
            )

            obj = TestImageModel.objects.create(image=image_file)
            assert obj.thumbnail is not None

            # Delete
            obj.delete()
