# django_advance_thumbnail Usage Guide

## Installation

To install django_advance_thumbnail, you can use pip:

```bash
pip install django_advance_thumbnail
```

# Basic Usage

The `django_advance_thumbnail` package provides a `AdvanceThumbnailField` that you can use in your Django models. This
field automatically creates a thumbnail for an image field whenever the image is uploaded or changed.

Here's a basic example of how to use the `AdvanceThumbnailField` in a model:

```python
from django.db import models

from django_advance_thumbnail import AdvanceThumbnailField


class MyModel(models.Model):
    image = models.ImageField(upload_to='images/', null=True, blank=True)
    thumbnail = AdvanceThumbnailField(source_field='image', upload_to='thumbnails/', null=True, blank=True,
                                      size=(300, 300))

```

In this example, a thumbnail of `image` will be automatically created and saved to `thumbnail` whenever `image` is uploaded or changed. If `image` is deleted, `thumbnail` will be deleted as well.
The `size` parameter is optional and defaults to `(300, 300)`. It determines the size of the thumbnail if specified.

# Contact

For any questions or feedback, feel free to reach out:

- Email: [mh@mahadihassan.com](mailto:mh@mahadihassan.com), [me.mahadi10@gmail.com](mailto:me.mahadi10@gmail.com)
- Github: [@itsmahadi007](https://github.com/itsmahadi007)
- Linkedin: [Mahadi Hassan](https://linkedin.com/in/mahadi-hassan-4a2239154/)
- Web: [mahadihassan.com](https://mahadihassan.com)
