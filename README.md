# Django Advance Thumbnail

Django Advance Thumbnail is a Django app that automates thumbnail creation for image fields. It generates, updates, and deletes thumbnails based on the source image, and allows custom thumbnail sizes.

## Installation

1. Install the package using pip:

```bash
pip install django_advance_thumbnail
```

2. Add `django_advance_thumbnail` to your `INSTALLED_APPS` in `settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'django_advance_thumbnail',
    # ...
]
```

## Usage
Here's a basic example of how to use the `AdvanceDJThumbnailField` in a model:

Here's a basic example of how to use the `AdvanceDJThumbnailField` in a model:

```python
from django.db import models
from django_advance_thumbnail import AdvanceDJThumbnailField

class MyModel(models.Model):
    image = models.ImageField(upload_to='images/', null=True, blank=True)
    thumbnail = AdvanceDJThumbnailField(source_field='image', upload_to='thumbnails/', null=True, blank=True, size=(300, 300)) 
```

In this example, `AdvanceDJThumbnailField` is used to create a `thumbnail` from the `image` field. Whenever an image is uploaded or updated, a corresponding thumbnail is automatically generated and stored in the `thumbnail` field. The thumbnail's dimensions are determined by the optional `size` parameter, which defaults to `(300, 300)` if not specified.

This setup ensures that the lifecycle of the thumbnail is tied to its source image. If the source image is deleted, the associated thumbnail is also removed. This seamless synchronization simplifies image management in your Django models.


# Contact
For any questions or feedback, feel free to reach out:
- Email: [mh@mahadihassan.com](mailto:mh@mahadihassan.com), [me.mahadi10@gmail.com](mailto:me.mahadi10@gmail.com)
- Github: [@itsmahadi007](https://github.com/itsmahadi007)
- Linkedin: [Mahadi Hassan](https://linkedin.com/in/mahadi-hassan-4a2239154/)
- Web: [mahadihassan.com](https://mahadihassan.com)

# Credits
This package was created by Mahadi Hassan. Special thanks to the Django and Python communities for their invaluable resources and support.

