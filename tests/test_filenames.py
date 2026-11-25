"""
Thumbnail file names. Two thumbnail fields of the same image must never share a
file name: storage that overwrites same-named files (S3 in django-storages, by
default) would otherwise make both fields point at whichever file was written last.
"""
import os

import pytest
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from tests.models import TestImageModel, TestMultipleThumbnails, TestTwoThumbnailsOneFolder


def thumb_size(obj, name):
    with getattr(obj, name).open() as f:
        return Image.open(f).size


def upload(buffer, name='photo.jpg'):
    return SimpleUploadedFile(name, buffer.read(), content_type='image/jpeg')


@pytest.mark.django_db
class TestThumbnailFilenames:

    def test_two_fields_in_one_folder_keep_their_own_files(self, temp_media_root, create_test_image):
        obj = TestTwoThumbnailsOneFolder.objects.create(image=upload(create_test_image(400, 300)))
        obj.refresh_from_db()

        assert obj.thumbnail.name != obj.cart_thumbnail.name
        assert thumb_size(obj, 'thumbnail') == (150, 113)
        assert thumb_size(obj, 'cart_thumbnail') == (50, 50)

    def test_field_named_thumbnail_keeps_its_filename(self, temp_media_root, create_test_image):
        obj = TestImageModel.objects.create(image=upload(create_test_image(400, 300)))

        assert os.path.basename(obj.thumbnail.name) == 'photo_thumbnail.jpg'

    def test_cold_cache_save_does_not_rebuild_a_named_thumbnail(self, temp_media_root, create_test_image, mocker):
        obj = TestTwoThumbnailsOneFolder.objects.create(image=upload(create_test_image(400, 300)))
        obj.refresh_from_db()
        field = TestTwoThumbnailsOneFolder._meta.get_field('cart_thumbnail')
        spy = mocker.spy(field, '_generate_thumbnail_file')

        cache.clear()   # restart, eviction or another worker
        obj.save()

        assert spy.call_count == 0

    def test_cold_cache_save_keeps_a_legacy_named_thumbnail(self, temp_media_root, create_test_image):
        """Thumbnails made before 2.0.3 are named <stem>_thumbnail whatever the field is called."""
        obj = TestMultipleThumbnails.objects.create(image=upload(create_test_image(400, 300)))
        storage = obj.thumbnail_large.storage
        with obj.thumbnail_large.open() as f:
            legacy = storage.save('test_thumbnails/large/photo_thumbnail.jpg', ContentFile(f.read()))
        TestMultipleThumbnails.objects.filter(pk=obj.pk).update(thumbnail_large=legacy)

        cache.clear()
        obj.refresh_from_db()
        obj.save()

        obj.refresh_from_db()
        assert obj.thumbnail_large.name == legacy
