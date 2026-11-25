"""
Changing ``size`` or ``resize_method`` and then running ``regenerate_thumbnails``
must rebuild the stored thumbnails, even after a restart (the field writes its
current config to the cache when the model loads, so the cache cannot tell what
the old config was).
"""
import io

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image

from django_advance_thumbnail import RESIZE_FILL, RESIZE_FIT
from tests.models import TestImageModelFill, TestImageModelFit


def thumb_size(obj, name='thumbnail'):
    with getattr(obj, name).open() as f:
        return Image.open(f).size


def upload(buffer, name='photo.jpg'):
    return SimpleUploadedFile(name, buffer.read(), content_type='image/jpeg')


@pytest.fixture
def reconfigure():
    """Change a thumbnail field's config as if the code changed and the app restarted."""
    changed = []

    def _reconfigure(model, size=None, resize_method=None, name='thumbnail'):
        field = model._meta.get_field(name)
        changed.append((field, field.size, field.resize_method))
        if size is not None:
            field.size = size
        if resize_method is not None:
            field.resize_method = resize_method
        cache.clear()                 # restart: a process-local cache starts empty
        field._store_field_config()   # what contribute_to_class does when the model loads
        return field

    yield _reconfigure
    for field, size, method in changed:
        field.size, field.resize_method = size, method


def regenerate(*args):
    out = io.StringIO()
    call_command('regenerate_thumbnails', *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
class TestRegenerateAfterConfigChange:

    def test_size_change_is_rebuilt(self, temp_media_root, create_test_image, reconfigure):
        obj = TestImageModelFit.objects.create(image=upload(create_test_image(400, 300)))
        assert thumb_size(obj) == (150, 113)

        reconfigure(TestImageModelFit, size=(80, 80))
        regenerate()

        obj.refresh_from_db()
        assert thumb_size(obj) == (80, 60)

    def test_fit_to_fill_is_rebuilt(self, temp_media_root, create_test_image, reconfigure):
        obj = TestImageModelFit.objects.create(image=upload(create_test_image(400, 300)))

        reconfigure(TestImageModelFit, resize_method=RESIZE_FILL)
        regenerate()

        obj.refresh_from_db()
        assert thumb_size(obj) == (150, 150)

    def test_fill_to_fit_is_rebuilt(self, temp_media_root, create_test_image, reconfigure):
        obj = TestImageModelFill.objects.create(image=upload(create_test_image(400, 300)))
        assert thumb_size(obj) == (150, 150)

        reconfigure(TestImageModelFill, resize_method=RESIZE_FIT)
        regenerate()

        obj.refresh_from_db()
        assert thumb_size(obj) == (150, 113)

    def test_field_method_rebuilds_stale_thumbnails(self, temp_media_root, create_test_image, reconfigure):
        obj = TestImageModelFit.objects.create(image=upload(create_test_image(400, 300)))

        field = reconfigure(TestImageModelFit, size=(80, 80))
        count, errors = field.regenerate_thumbnails(TestImageModelFit)

        assert (count, errors) == (1, [])
        obj.refresh_from_db()
        assert thumb_size(obj) == (80, 60)


@pytest.mark.django_db
class TestRegenerateSkipsUpToDateThumbnails:

    def test_unchanged_config_is_left_alone(self, temp_media_root, create_test_image):
        obj = TestImageModelFit.objects.create(image=upload(create_test_image(400, 300)))
        before = obj.thumbnail.name

        regenerate()

        obj.refresh_from_db()
        assert obj.thumbnail.name == before

    def test_source_smaller_than_size_is_left_alone(self, temp_media_root, create_test_image):
        obj = TestImageModelFit.objects.create(image=upload(create_test_image(100, 80)))
        assert thumb_size(obj) == (100, 80)   # fit never upscales
        before = obj.thumbnail.name

        regenerate()

        obj.refresh_from_db()
        assert obj.thumbnail.name == before

    def test_exif_rotated_source_is_left_alone(self, temp_media_root):
        img = Image.new('RGB', (400, 300), 'blue')
        exif = Image.Exif()
        exif[0x0112] = 6   # rotate 90: stored 400x300, shown 300x400
        buf = io.BytesIO()
        img.save(buf, format='JPEG', exif=exif.tobytes())
        buf.seek(0)
        obj = TestImageModelFit.objects.create(image=upload(buf, 'phone.jpg'))
        assert thumb_size(obj) == (112, 150)
        before = obj.thumbnail.name

        regenerate()

        obj.refresh_from_db()
        assert obj.thumbnail.name == before
