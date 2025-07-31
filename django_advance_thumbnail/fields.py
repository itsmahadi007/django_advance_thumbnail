import io
import os

from PIL import Image, ImageOps
from django.core.files import File
from django.db import models
from django.core.cache import cache


class AdvanceThumbnailField(models.ImageField):
    def __init__(self, *args, **kwargs):
        self.source_field_name = kwargs.pop('source_field', None)
        self.size = kwargs.pop('size', (300, 300))
        self.force_regenerate = kwargs.pop('force_regenerate', False)
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        models.signals.post_save.connect(self.create_thumbnail, sender=cls)
        # Store the field configuration for size change detection
        self._cache_key = f"thumbnail_field_{cls._meta.app_label}_{cls._meta.model_name}_{name}_size"
        # Only store config if cache is available
        try:
            self._store_field_config()
        except Exception:
            # Cache might not be configured, that's okay
            pass

    def pre_save(self, model_instance, add):
        file = super().pre_save(model_instance, add)
        source_field = getattr(model_instance, self.source_field_name)
        if not source_field:
            file.delete(save=False)
        return file

    def create_thumbnail(self, instance, **kwargs):
        source_field = getattr(instance, self.source_field_name)
        if not source_field or not source_field.name:
            return

        # Check if source image has changed or if we need to regenerate due to size change
        source_changed = self._has_source_image_changed(instance)
        size_changed = self._should_regenerate_thumbnail(instance)
        should_regenerate = self.force_regenerate or source_changed or size_changed
        
        # Skip if thumbnail exists and no regeneration needed
        current_thumbnail = getattr(instance, self.name)
        if current_thumbnail and not should_regenerate:
            return

        # Disconnect the signal before creating and saving the thumbnail
        models.signals.post_save.disconnect(self.create_thumbnail, sender=instance.__class__)

        try:
            self._generate_thumbnail_file(instance, source_field)
            # Store the current source image info for future change detection
            self._store_source_image_info(instance, source_field)
        finally:
            # Reconnect the signal after saving
            models.signals.post_save.connect(self.create_thumbnail, sender=instance.__class__)
    
    def _store_field_config(self):
        """Store the current field configuration in cache for size change detection"""
        try:
            cache.set(self._cache_key, self.size, timeout=None)
        except Exception:
            # Cache might not be configured, silently fail
            pass
    
    def _should_regenerate_thumbnail(self, instance):
        """Check if thumbnail should be regenerated due to size change"""
        try:
            cached_size = cache.get(self._cache_key)
            if cached_size != self.size:
                # Size has changed, update cache and return True
                self._store_field_config()
                return True
        except Exception:
            # Cache might not be configured, assume no regeneration needed
            pass
        return False
    
    def _has_source_image_changed(self, instance):
        """Check if the source image has changed since last thumbnail generation"""
        source_field = getattr(instance, self.source_field_name)
        if not source_field or not source_field.name:
            return False
            
        # Create cache key for source image info
        source_cache_key = f"thumbnail_source_{instance.__class__._meta.app_label}_{instance.__class__._meta.model_name}_{instance.pk}_{self.name}"
        
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
            
        except Exception:
            # If cache fails, assume image has changed to be safe
            return True
    
    def _store_source_image_info(self, instance, source_field):
        """Store current source image info for change detection"""
        if not source_field or not source_field.name:
            return
            
        source_cache_key = f"thumbnail_source_{instance.__class__._meta.app_label}_{instance.__class__._meta.model_name}_{instance.pk}_{self.name}"
        
        try:
            source_info = {
                'name': source_field.name,
                'size': source_field.size if hasattr(source_field, 'size') else None,
            }
            cache.set(source_cache_key, source_info, timeout=None)
        except Exception:
            # Cache might not be configured, silently fail
            pass
    
    def _generate_thumbnail_file(self, instance, source_field):
        """Generate the actual thumbnail file"""
        if not source_field or not hasattr(source_field, 'open'):
            return
            
        try:
            with source_field.open() as source_file:
                img = Image.open(source_file)

                # Handle orientation from EXIF data
                img = ImageOps.exif_transpose(img)

                # Create a copy to avoid modifying the original
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

                instance.save(update_fields=[self.name])
        except Exception as e:
            # Log the error but don't raise to avoid breaking the save process
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating thumbnail for {instance.__class__.__name__} {instance.pk}: {str(e)}")
            raise
    
    def regenerate_thumbnails(self, model_class, force=False):
        """Regenerate thumbnails for all instances of a model"""
        queryset = model_class.objects.all()
        
        # Filter objects that have source images
        source_field_name = self.source_field_name
        # Get objects that have source images (not null and not empty)
        queryset = queryset.filter(**{f"{source_field_name}__isnull": False}).exclude(**{source_field_name: ""})
        
        count = 0
        for instance in queryset:
            source_field = getattr(instance, source_field_name)
            thumbnail_field_value = getattr(instance, self.name)
            
            # Skip if thumbnail exists and not forcing
            if thumbnail_field_value and not force:
                continue
            
            try:
                self._generate_thumbnail_file(instance, source_field)
                count += 1
            except Exception:
                continue
        
        return count
