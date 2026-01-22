import io
import logging
import os

from PIL import Image, ImageOps
from django.core.files import File
from django.db import models
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

# Valid resize methods
RESIZE_FIT = 'fit'  # Maintain aspect ratio, fit within size (default, may be smaller)
RESIZE_FILL = 'fill'  # Fill exact size, crop excess (guarantees exact dimensions)
RESIZE_COVER = 'cover'  # Scale to cover size, then crop center (alias for fill)
VALID_RESIZE_METHODS = (RESIZE_FIT, RESIZE_FILL, RESIZE_COVER)


class AdvanceThumbnailField(models.ImageField):
    """
    Custom ImageField that automatically generates thumbnails from a source image.

    Thread-safe implementation using instance-level flags instead of signal disconnection.

    Parameters:
        source_field (str): Required. Name of the source ImageField.
        size (tuple): Thumbnail dimensions (width, height). Default: (300, 300)
        resize_method (str): How to resize the image:
            - 'fit': Maintain aspect ratio, fit within size (may be smaller than size)
            - 'fill'/'cover': Fill exact size by cropping (guarantees exact dimensions)
        force_regenerate (bool): Regenerate on every save. Default: False
    """

    def __init__(self, *args, **kwargs):
        self.source_field_name = kwargs.pop('source_field', None)
        self.size = kwargs.pop('size', (300, 300))
        self.resize_method = kwargs.pop('resize_method', RESIZE_FIT)
        self.force_regenerate = kwargs.pop('force_regenerate', False)

        # Validate parameters
        self._validate_parameters()

        super().__init__(*args, **kwargs)

    def _validate_parameters(self):
        """Validate field parameters"""
        # Validate source_field
        if self.source_field_name is None:
            raise ImproperlyConfigured(
                "AdvanceThumbnailField requires 'source_field' parameter"
            )

        if not isinstance(self.source_field_name, str):
            raise ImproperlyConfigured(
                f"'source_field' must be a string, got {type(self.source_field_name).__name__}"
            )

        # Validate size
        if not isinstance(self.size, (tuple, list)):
            raise ImproperlyConfigured(
                f"'size' must be a tuple or list, got {type(self.size).__name__}"
            )

        if len(self.size) != 2:
            raise ImproperlyConfigured(
                f"'size' must have exactly 2 elements (width, height), got {len(self.size)}"
            )

        width, height = self.size
        if not isinstance(width, int) or not isinstance(height, int):
            raise ImproperlyConfigured(
                "'size' elements must be integers"
            )

        if width <= 0 or height <= 0:
            raise ImproperlyConfigured(
                "'size' dimensions must be positive integers"
            )

        # Ensure size is a tuple
        self.size = tuple(self.size)

        # Validate resize_method
        if self.resize_method not in VALID_RESIZE_METHODS:
            raise ImproperlyConfigured(
                f"'resize_method' must be one of {VALID_RESIZE_METHODS}, got '{self.resize_method}'"
            )

    def deconstruct(self):
        """Support for Django migrations"""
        name, path, args, kwargs = super().deconstruct()

        # Always include source_field (required)
        kwargs['source_field'] = self.source_field_name

        # Only include non-default values
        if self.size != (300, 300):
            kwargs['size'] = self.size

        if self.resize_method != RESIZE_FIT:
            kwargs['resize_method'] = self.resize_method

        if self.force_regenerate:
            kwargs['force_regenerate'] = self.force_regenerate

        return name, path, args, kwargs

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        models.signals.post_save.connect(self.create_thumbnail, sender=cls)
        # Store the field configuration for size change detection
        self._cache_key = f"thumbnail_field_{cls._meta.app_label}_{cls._meta.model_name}_{name}_size"
        # Only store config if cache is available
        try:
            self._store_field_config()
        except Exception as e:
            logger.debug(f"Could not store field config in cache: {e}")

    def pre_save(self, model_instance, add):
        file = super().pre_save(model_instance, add)
        source_field = getattr(model_instance, self.source_field_name, None)
        if not source_field:
            file.delete(save=False)
        return file

    def create_thumbnail(self, instance, **kwargs):
        """
        Signal handler for post_save. Thread-safe using instance-level flag.
        """
        # Thread-safe recursion prevention using instance attribute
        # This replaces the problematic signal disconnect/reconnect pattern
        if getattr(instance, '_generating_thumbnail', False):
            return

        source_field = getattr(instance, self.source_field_name, None)
        if not source_field or not source_field.name:
            return

        # Check if source image has changed or if we need to regenerate due to size change
        source_changed = self._has_source_image_changed(instance)
        size_changed = self._should_regenerate_thumbnail(instance)
        should_regenerate = self.force_regenerate or source_changed or size_changed

        # Skip if thumbnail exists and no regeneration needed
        current_thumbnail = getattr(instance, self.name, None)
        if current_thumbnail and not should_regenerate:
            return

        # Set flag to prevent recursion (thread-safe: flag is on instance, not global)
        instance._generating_thumbnail = True

        try:
            self._generate_thumbnail_file(instance, source_field)
            # Store the current source image info for future change detection
            self._store_source_image_info(instance, source_field)
        except Exception as e:
            logger.error(
                f"Error generating thumbnail for {instance.__class__.__name__} "
                f"(pk={instance.pk}): {e}"
            )
        finally:
            # Always clear the flag
            instance._generating_thumbnail = False

    def _store_field_config(self):
        """Store the current field configuration in cache for size change detection"""
        try:
            config = {
                'size': self.size,
                'resize_method': self.resize_method,
            }
            cache.set(self._cache_key, config, timeout=None)
        except Exception as e:
            logger.debug(f"Could not store field config in cache: {e}")

    def _should_regenerate_thumbnail(self, instance):
        """Check if thumbnail should be regenerated due to size or method change"""
        try:
            cached_config = cache.get(self._cache_key)
            current_config = {
                'size': self.size,
                'resize_method': self.resize_method,
            }

            if cached_config != current_config:
                # Config has changed, update cache and return True
                self._store_field_config()
                return True
        except Exception as e:
            logger.debug(f"Could not check field config from cache: {e}")
        return False

    def _has_source_image_changed(self, instance):
        """Check if the source image has changed since last thumbnail generation"""
        source_field = getattr(instance, self.source_field_name, None)
        if not source_field or not source_field.name:
            return False

        # Create cache key for source image info
        source_cache_key = self._get_source_cache_key(instance)

        try:
            # Get current source image info
            current_info = {
                'name': source_field.name,
                'size': source_field.size if hasattr(source_field, 'size') else None,
            }

            # Get cached source image info
            cached_info = cache.get(source_cache_key)

            # If no cached info exists, this is a new image
            if cached_info is None:
                return True

            # Compare current and cached info
            return current_info != cached_info

        except Exception as e:
            logger.debug(f"Could not check source image from cache: {e}")
            # If cache fails, assume image has changed to be safe
            return True

    def _get_source_cache_key(self, instance):
        """Generate cache key for source image info"""
        return (
            f"thumbnail_source_{instance.__class__._meta.app_label}_"
            f"{instance.__class__._meta.model_name}_{instance.pk}_{self.name}"
        )

    def _store_source_image_info(self, instance, source_field):
        """Store current source image info for change detection"""
        if not source_field or not source_field.name:
            return

        source_cache_key = self._get_source_cache_key(instance)

        try:
            source_info = {
                'name': source_field.name,
                'size': source_field.size if hasattr(source_field, 'size') else None,
            }
            cache.set(source_cache_key, source_info, timeout=None)
        except Exception as e:
            logger.debug(f"Could not store source image info in cache: {e}")

    def _generate_thumbnail_file(self, instance, source_field):
        """Generate the actual thumbnail file"""
        if not source_field or not hasattr(source_field, 'open'):
            return

        with source_field.open() as source_file:
            img = Image.open(source_file)

            # Handle orientation from EXIF data
            img = ImageOps.exif_transpose(img)

            # Resize based on method
            if self.resize_method in (RESIZE_FILL, RESIZE_COVER):
                # Fill/cover: crop to exact dimensions (guarantees size)
                img_copy = ImageOps.fit(img, self.size, Image.Resampling.LANCZOS)
            else:
                # Fit: maintain aspect ratio, fit within size (may be smaller)
                img_copy = img.copy()
                img_copy.thumbnail(self.size, Image.Resampling.LANCZOS)

            filename, extension = os.path.splitext(os.path.basename(source_field.name))
            thumbnail_filename = f"{filename}_thumbnail{extension}"

            thumbnail_io = io.BytesIO()

            # Determine the format based on the file extension, fallback to JPEG if not found
            if extension.lower() in ['.jpg', '.jpeg']:
                image_format = 'JPEG'
            elif extension.lower() == '.png':
                image_format = 'PNG'
            elif extension.lower() == '.webp':
                image_format = 'WEBP'
            else:
                image_format = 'JPEG'  # Default to JPEG if unsure

            # Handle transparency for PNG
            if image_format == 'JPEG' and img_copy.mode in ('RGBA', 'LA', 'P'):
                # Convert RGBA to RGB for JPEG
                background = Image.new('RGB', img_copy.size, (255, 255, 255))
                if img_copy.mode == 'P':
                    img_copy = img_copy.convert('RGBA')
                background.paste(img_copy, mask=img_copy.split()[-1] if img_copy.mode == 'RGBA' else None)
                img_copy = background

            img_copy.save(thumbnail_io, format=image_format, quality=85, optimize=True)
            thumbnail_io.seek(0)

            thumbnail_file = File(thumbnail_io, name=thumbnail_filename)
            setattr(instance, self.name, thumbnail_file)

            # Save with update_fields to prevent full model save
            # The _generating_thumbnail flag prevents recursion
            instance.save(update_fields=[self.name])

    def regenerate_thumbnails(self, model_class, force=False):
        """Regenerate thumbnails for all instances of a model"""
        queryset = model_class.objects.all()

        # Filter objects that have source images
        source_field_name = self.source_field_name
        # Get objects that have source images (not null and not empty)
        queryset = queryset.filter(**{f"{source_field_name}__isnull": False}).exclude(**{source_field_name: ""})

        count = 0
        errors = []
        for instance in queryset:
            source_field = getattr(instance, source_field_name, None)
            thumbnail_field_value = getattr(instance, self.name, None)

            # Skip if thumbnail exists and not forcing
            if thumbnail_field_value and not force:
                continue

            try:
                # Set flag to prevent signal handler from interfering
                instance._generating_thumbnail = True
                self._generate_thumbnail_file(instance, source_field)
                count += 1
            except Exception as e:
                errors.append(f"{instance.__class__.__name__}(pk={instance.pk}): {e}")
                logger.error(f"Error regenerating thumbnail for {instance}: {e}")
            finally:
                instance._generating_thumbnail = False

        if errors:
            logger.warning(f"Thumbnail regeneration completed with {len(errors)} errors")

        return count, errors
