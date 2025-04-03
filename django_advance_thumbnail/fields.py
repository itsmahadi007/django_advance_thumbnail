import io
import os

from PIL import Image, ImageOps
from django.db.models.fields.files import FieldFile
from django.db import models


class AdvanceThumbnailField(models.ImageField):
    def __init__(self, *args, **kwargs):
        self.source_field_name = kwargs.pop('source_field', None)
        self.size = kwargs.pop('size', (300, 300))
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        models.signals.post_save.connect(self.create_thumbnail, sender=cls)

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

        try:
            with source_field.open() as source_file:
                img = Image.open(source_file)

                # Handle orientation from EXIF data
                img = ImageOps.exif_transpose(img)

                img.thumbnail(self.size)

                filename, extension = os.path.splitext(os.path.basename(source_field.name))
                thumbnail_filename = f"{filename}_thumbnail{extension}"

                thumbnail_io = io.BytesIO()

                # Determine the format based on the file extension, fallback to JPEG if not found
                if extension.lower() in ['.jpg', '.jpeg']:
                    image_format = 'JPEG'
                elif extension.lower() == '.png':
                    image_format = 'PNG'
                else:
                    image_format = 'JPEG'  # Default to JPEG if unsure

                img.save(thumbnail_io, format=image_format)
                thumbnail_io.seek(0)

                thumbnail_file = FieldFile(instance, self, thumbnail_filename)
                thumbnail_file.save(thumbnail_filename, thumbnail_io, save=False)

                instance.__class__.objects.filter(pk=instance.pk).update(**{self.name: thumbnail_file})

        finally:
            pass
