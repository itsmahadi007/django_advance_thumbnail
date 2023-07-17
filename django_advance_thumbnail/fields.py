import os

from PIL import Image
from django.conf import settings
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
        if not source_field or not source_field.path:
            return

        img = Image.open(source_field.path)
        img.thumbnail(self.size)

        thumbnail_path = os.path.join(os.path.dirname(source_field.path), 'thumbnails')
        os.makedirs(thumbnail_path, exist_ok=True)

        # Split the filename into name and extension, add '_thumbnail' to the name, and join them back together
        filename, extension = os.path.splitext(os.path.basename(source_field.path))
        thumbnail_filename = os.path.join(thumbnail_path, f"{filename}_thumbnail{extension}")

        img.save(thumbnail_filename)

        setattr(instance, self.name, os.path.relpath(thumbnail_filename, start=settings.MEDIA_ROOT))

        # Disconnect the signal before saving
        models.signals.post_save.disconnect(self.create_thumbnail, sender=instance.__class__)

        # Save only the thumbnail field
        instance.save(update_fields=[self.name])

        # Reconnect the signal after saving
        models.signals.post_save.connect(self.create_thumbnail, sender=instance.__class__)
