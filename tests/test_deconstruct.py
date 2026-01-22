"""
Tests for deconstruct() method - Django migrations support
"""
import pytest
from django_advance_thumbnail import AdvanceThumbnailField, RESIZE_FIT, RESIZE_FILL


class TestDeconstruct:
    """Test deconstruct() method for Django migrations"""

    def test_deconstruct_with_defaults(self):
        """Test deconstruct with default values"""
        field = AdvanceThumbnailField(source_field='image')
        name, path, args, kwargs = field.deconstruct()

        assert path == 'django_advance_thumbnail.fields.AdvanceThumbnailField'
        assert args == []
        assert kwargs['source_field'] == 'image'
        # Default values should not be included
        assert 'size' not in kwargs
        assert 'resize_method' not in kwargs
        assert 'force_regenerate' not in kwargs

    def test_deconstruct_with_custom_size(self):
        """Test deconstruct with custom size"""
        field = AdvanceThumbnailField(source_field='image', size=(150, 150))
        name, path, args, kwargs = field.deconstruct()

        assert kwargs['source_field'] == 'image'
        assert kwargs['size'] == (150, 150)

    def test_deconstruct_with_resize_method(self):
        """Test deconstruct with non-default resize_method"""
        field = AdvanceThumbnailField(source_field='image', resize_method=RESIZE_FILL)
        name, path, args, kwargs = field.deconstruct()

        assert kwargs['resize_method'] == RESIZE_FILL

    def test_deconstruct_with_force_regenerate(self):
        """Test deconstruct with force_regenerate=True"""
        field = AdvanceThumbnailField(source_field='image', force_regenerate=True)
        name, path, args, kwargs = field.deconstruct()

        assert kwargs['force_regenerate'] is True

    def test_deconstruct_with_all_custom_values(self):
        """Test deconstruct with all custom values"""
        field = AdvanceThumbnailField(
            source_field='profile_image',
            size=(200, 200),
            resize_method=RESIZE_FILL,
            force_regenerate=True,
            upload_to='custom_thumbnails/',
            null=True,
            blank=True,
        )
        name, path, args, kwargs = field.deconstruct()

        assert kwargs['source_field'] == 'profile_image'
        assert kwargs['size'] == (200, 200)
        assert kwargs['resize_method'] == RESIZE_FILL
        assert kwargs['force_regenerate'] is True
        # Standard ImageField kwargs should also be included
        assert kwargs.get('upload_to') == 'custom_thumbnails/'
        assert kwargs.get('null') is True
        assert kwargs.get('blank') is True

    def test_deconstruct_recreate_field(self):
        """Test that field can be recreated from deconstructed values"""
        original = AdvanceThumbnailField(
            source_field='image',
            size=(150, 150),
            resize_method=RESIZE_FILL,
            force_regenerate=True,
        )

        name, path, args, kwargs = original.deconstruct()
        recreated = AdvanceThumbnailField(*args, **kwargs)

        assert recreated.source_field_name == original.source_field_name
        assert recreated.size == original.size
        assert recreated.resize_method == original.resize_method
        assert recreated.force_regenerate == original.force_regenerate
