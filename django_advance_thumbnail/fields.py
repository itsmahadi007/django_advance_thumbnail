import io
import os

from PIL import Image
from django.core.files import File
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
            # Disconnect the signal before creating and saving the thumbnail
        models.signals.post_save.disconnect(self.create_thumbnail, sender=instance.__class__)

        try:
            with source_field.open() as source_file:
                img = Image.open(source_file)
                img.thumbnail(self.size)

                filename, extension = os.path.splitext(os.path.basename(source_field.name))
                thumbnail_filename = f"{filename}_thumbnail{extension}"

                thumbnail_io = io.BytesIO()
                img.save(thumbnail_io, format=img.format)
                thumbnail_io.seek(0)

                thumbnail_file = File(thumbnail_io, name=thumbnail_filename)
                setattr(instance, self.name, thumbnail_file)

                instance.save(update_fields=[self.name])

        finally:
            # Reconnect the signal after saving
            models.signals.post_save.connect(self.create_thumbnail, sender=instance.__class__)
