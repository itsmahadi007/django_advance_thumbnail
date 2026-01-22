"""
Tests for parameter validation in AdvanceThumbnailField
"""
import pytest
from django.core.exceptions import ImproperlyConfigured
from django_advance_thumbnail import AdvanceThumbnailField


class TestParameterValidation:
    """Test parameter validation in __init__"""

    def test_missing_source_field_raises_error(self):
        """source_field is required"""
        with pytest.raises(ImproperlyConfigured) as exc_info:
            AdvanceThumbnailField()
        assert "requires 'source_field' parameter" in str(exc_info.value)

    def test_source_field_must_be_string(self):
        """source_field must be a string"""
        with pytest.raises(ImproperlyConfigured) as exc_info:
            AdvanceThumbnailField(source_field=123)
        assert "'source_field' must be a string" in str(exc_info.value)

    def test_size_must_be_tuple_or_list(self):
        """size must be tuple or list"""
        with pytest.raises(ImproperlyConfigured) as exc_info:
            AdvanceThumbnailField(source_field='image', size='invalid')
        assert "'size' must be a tuple or list" in str(exc_info.value)

    def test_size_must_have_two_elements(self):
        """size must have exactly 2 elements"""
        with pytest.raises(ImproperlyConfigured) as exc_info:
            AdvanceThumbnailField(source_field='image', size=(100,))
        assert "'size' must have exactly 2 elements" in str(exc_info.value)

        with pytest.raises(ImproperlyConfigured) as exc_info:
            AdvanceThumbnailField(source_field='image', size=(100, 200, 300))
        assert "'size' must have exactly 2 elements" in str(exc_info.value)

    def test_size_elements_must_be_integers(self):
        """size elements must be integers"""
        with pytest.raises(ImproperlyConfigured) as exc_info:
            AdvanceThumbnailField(source_field='image', size=(100.5, 200))
        assert "'size' elements must be integers" in str(exc_info.value)

        with pytest.raises(ImproperlyConfigured) as exc_info:
            AdvanceThumbnailField(source_field='image', size=('100', 200))
        assert "'size' elements must be integers" in str(exc_info.value)

    def test_size_must_be_positive(self):
        """size dimensions must be positive"""
        with pytest.raises(ImproperlyConfigured) as exc_info:
            AdvanceThumbnailField(source_field='image', size=(0, 200))
        assert "'size' dimensions must be positive" in str(exc_info.value)

        with pytest.raises(ImproperlyConfigured) as exc_info:
            AdvanceThumbnailField(source_field='image', size=(100, -50))
        assert "'size' dimensions must be positive" in str(exc_info.value)

    def test_invalid_resize_method(self):
        """resize_method must be valid"""
        with pytest.raises(ImproperlyConfigured) as exc_info:
            AdvanceThumbnailField(source_field='image', resize_method='invalid')
        assert "'resize_method' must be one of" in str(exc_info.value)

    def test_valid_parameters_no_error(self):
        """Valid parameters should not raise errors"""
        # Default size
        field = AdvanceThumbnailField(source_field='image')
        assert field.source_field_name == 'image'
        assert field.size == (300, 300)
        assert field.resize_method == 'fit'
        assert field.force_regenerate is False

        # Custom size as tuple
        field = AdvanceThumbnailField(source_field='image', size=(150, 150))
        assert field.size == (150, 150)

        # Custom size as list (should be converted to tuple)
        field = AdvanceThumbnailField(source_field='image', size=[200, 200])
        assert field.size == (200, 200)
        assert isinstance(field.size, tuple)

        # All resize methods
        for method in ['fit', 'fill', 'cover']:
            field = AdvanceThumbnailField(source_field='image', resize_method=method)
            assert field.resize_method == method

        # Force regenerate
        field = AdvanceThumbnailField(source_field='image', force_regenerate=True)
        assert field.force_regenerate is True
