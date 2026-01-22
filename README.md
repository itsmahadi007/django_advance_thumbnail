# Django Advance Thumbnail

A Django app that automates thumbnail creation for image fields. It generates, updates, and deletes thumbnails based on the source image with support for custom sizes and resize methods.

## Features

- Automatic thumbnail generation on model save
- Thread-safe for multi-threaded/parallel web servers (gunicorn, uwsgi, etc.)
- Multiple resize methods: `fit` (maintain aspect ratio) or `fill` (exact dimensions)
- Smart regeneration - only regenerates when source image or settings change
- Management commands for bulk operations
- Full Django migrations support

## Installation

```bash
pip install django-advance-thumbnail
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'django_advance_thumbnail',
]
```

## Quick Start

```python
from django.db import models
from django_advance_thumbnail import AdvanceThumbnailField

class Product(models.Model):
    image = models.ImageField(upload_to='products/')
    thumbnail = AdvanceThumbnailField(
        source_field='image',
        upload_to='thumbnails/',
        size=(300, 300),
        null=True,
        blank=True,
    )
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_field` | str | **required** | Name of the source ImageField |
| `size` | tuple | `(300, 300)` | Thumbnail dimensions (width, height) |
| `resize_method` | str | `'fit'` | How to resize: `'fit'`, `'fill'`, or `'cover'` |
| `force_regenerate` | bool | `False` | Regenerate on every save |

## Resize Methods

### `fit` (default)
Maintains aspect ratio. Thumbnail fits within the specified size but may be smaller in one dimension.

```python
# A 400x100 image with size=(150, 150) becomes 150x37
thumbnail = AdvanceThumbnailField(
    source_field='image',
    size=(150, 150),
    resize_method='fit',  # default
)
```

### `fill` / `cover`
Guarantees exact dimensions by cropping. Use this when you need thumbnails to be exactly the specified size.

```python
# A 400x100 image with size=(150, 150) becomes exactly 150x150
thumbnail = AdvanceThumbnailField(
    source_field='image',
    size=(150, 150),
    resize_method='fill',  # guarantees 150x150
)
```

## Usage Examples

### Basic Usage

```python
from django.db import models
from django_advance_thumbnail import AdvanceThumbnailField

class Article(models.Model):
    image = models.ImageField(upload_to='articles/')
    thumbnail = AdvanceThumbnailField(
        source_field='image',
        upload_to='thumbnails/',
        size=(300, 300),
        null=True,
        blank=True,
    )
```

### Multiple Thumbnails

```python
class Product(models.Model):
    image = models.ImageField(upload_to='products/')

    # Small thumbnail for listings (fit mode)
    thumbnail_small = AdvanceThumbnailField(
        source_field='image',
        upload_to='thumbnails/small/',
        size=(100, 100),
        resize_method='fit',
    )

    # Large thumbnail for detail page (exact dimensions)
    thumbnail_large = AdvanceThumbnailField(
        source_field='image',
        upload_to='thumbnails/large/',
        size=(400, 400),
        resize_method='fill',
    )
```

### Using Constants

```python
from django_advance_thumbnail import AdvanceThumbnailField, RESIZE_FIT, RESIZE_FILL

thumbnail = AdvanceThumbnailField(
    source_field='image',
    size=(200, 200),
    resize_method=RESIZE_FILL,
)
```

## Management Commands

### Generate Thumbnails

Generate thumbnails for existing images (use when adding field to existing models):

```bash
# All models
python manage.py generate_thumbnails

# Specific model
python manage.py generate_thumbnails --model myapp.Product

# Force regenerate existing
python manage.py generate_thumbnails --force

# Preview without changes
python manage.py generate_thumbnails --dry-run
```

### Regenerate Thumbnails

Regenerate thumbnails after changing `size` or `resize_method`:

```bash
# Detect and regenerate changed
python manage.py regenerate_thumbnails

# Force regenerate all
python manage.py regenerate_thumbnails --force

# Clear cache first
python manage.py regenerate_thumbnails --clear-cache
```

## Smart Regeneration

Thumbnails are only regenerated when:
- Source image changes
- `size` parameter changes
- `resize_method` parameter changes
- Thumbnail doesn't exist

This is efficient for production - no unnecessary processing.

## Thread Safety

Version 2.0+ is fully thread-safe for multi-threaded web servers like gunicorn and uwsgi. The previous signal disconnect/reconnect pattern has been replaced with instance-level flags.

## Requirements

- Python >= 3.6
- Django >= 3.0
- Pillow >= 8.0.0

## Upgrading to v2.0

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for breaking changes and upgrade instructions.

## Contact

- Email: [mh@mahadihassan.com](mailto:mh@mahadihassan.com)
- GitHub: [@itsmahadi007](https://github.com/itsmahadi007)
- LinkedIn: [Mahadi Hassan](https://linkedin.com/in/mahadi-hassan-4a2239154/)
- Web: [mahadihassan.com](https://mahadihassan.com)

## License

MIT License
