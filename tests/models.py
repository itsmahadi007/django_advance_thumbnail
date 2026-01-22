"""
Test models for django_advance_thumbnail
"""
from django.db import models
from django_advance_thumbnail import AdvanceThumbnailField, RESIZE_FIT, RESIZE_FILL


class TestImageModel(models.Model):
    """Basic test model with default settings"""
    image = models.ImageField(upload_to='test_images/')
    thumbnail = AdvanceThumbnailField(
        source_field='image',
        upload_to='test_thumbnails/',
        null=True,
        blank=True,
    )

    class Meta:
        app_label = 'tests'


class TestImageModelFit(models.Model):
    """Test model with fit resize method"""
    image = models.ImageField(upload_to='test_images/')
    thumbnail = AdvanceThumbnailField(
        source_field='image',
        upload_to='test_thumbnails/',
        size=(150, 150),
        resize_method=RESIZE_FIT,
        null=True,
        blank=True,
    )

    class Meta:
        app_label = 'tests'


class TestImageModelFill(models.Model):
    """Test model with fill resize method (guarantees exact dimensions)"""
    image = models.ImageField(upload_to='test_images/')
    thumbnail = AdvanceThumbnailField(
        source_field='image',
        upload_to='test_thumbnails/',
        size=(150, 150),
        resize_method=RESIZE_FILL,
        null=True,
        blank=True,
    )

    class Meta:
        app_label = 'tests'


class TestImageModelForceRegenerate(models.Model):
    """Test model with force_regenerate enabled"""
    image = models.ImageField(upload_to='test_images/')
    thumbnail = AdvanceThumbnailField(
        source_field='image',
        upload_to='test_thumbnails/',
        size=(200, 200),
        force_regenerate=True,
        null=True,
        blank=True,
    )

    class Meta:
        app_label = 'tests'


class TestMultipleThumbnails(models.Model):
    """Test model with multiple thumbnail fields"""
    image = models.ImageField(upload_to='test_images/')
    thumbnail_small = AdvanceThumbnailField(
        source_field='image',
        upload_to='test_thumbnails/small/',
        size=(100, 100),
        null=True,
        blank=True,
    )
    thumbnail_large = AdvanceThumbnailField(
        source_field='image',
        upload_to='test_thumbnails/large/',
        size=(400, 400),
        resize_method=RESIZE_FILL,
        null=True,
        blank=True,
    )

    class Meta:
        app_label = 'tests'
