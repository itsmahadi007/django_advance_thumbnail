"""
Pillow compatibility.

``Image.Resampling`` only exists in Pillow >= 9.1, but the package supports
Pillow >= 8.0. Thumbnails must still be generated when it is missing.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from tests.models import TestImageModelFill, TestImageModelFit


class _ImageWithoutResampling:
    """PIL.Image as Pillow 8.x/9.0 exposes it: LANCZOS exists, Resampling does not."""

    def __getattr__(self, name):
        if name == "Resampling":
            raise AttributeError(name)
        return getattr(Image, name)


@pytest.fixture
def old_pillow(monkeypatch):
    # Patch only the package's view of PIL.Image; Pillow itself uses Resampling internally.
    monkeypatch.setattr("django_advance_thumbnail.fields.Image", _ImageWithoutResampling())


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model, expected_sizes",
    [(TestImageModelFit, {(150, 37), (150, 38)}), (TestImageModelFill, {(150, 150)})],
)
def test_thumbnail_generated_without_image_resampling(
    old_pillow, temp_media_root, create_test_image, model, expected_sizes
):
    upload = SimpleUploadedFile("wide.jpg", create_test_image(400, 100).read(), content_type="image/jpeg")

    obj = model.objects.create(image=upload)
    obj.refresh_from_db()

    assert obj.thumbnail, "thumbnail was not generated on Pillow without Image.Resampling"
    with obj.thumbnail.open() as fh:
        assert Image.open(fh).size in expected_sizes  # 37.5 rounds either way across Pillow versions
