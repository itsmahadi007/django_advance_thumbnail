# Django Advance Thumbnail - Usage Guide

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

## Basic Usage

```python
from django.db import models
from django_advance_thumbnail import AdvanceThumbnailField

class MyModel(models.Model):
    image = models.ImageField(upload_to='images/')
    thumbnail = AdvanceThumbnailField(
        source_field='image',
        upload_to='thumbnails/',
        size=(300, 300),
        null=True,
        blank=True,
    )
```

A thumbnail of `image` is automatically created and saved to `thumbnail` whenever `image` is uploaded or changed. If `image` is deleted, `thumbnail` is deleted as well.

## Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `source_field` | str | - | **Yes** | Name of the source ImageField |
| `size` | tuple | `(300, 300)` | No | Thumbnail dimensions (width, height) |
| `resize_method` | str | `'fit'` | No | How to resize: `'fit'`, `'fill'`, or `'cover'` |
| `force_regenerate` | bool | `False` | No | Regenerate thumbnail on every save |

## Resize Methods

### `fit` (default)

Maintains aspect ratio. The thumbnail fits within the specified size but may be smaller in one dimension.

```python
thumbnail = AdvanceThumbnailField(
    source_field='image',
    size=(150, 150),
    resize_method='fit',
)
```

**Examples:**
- 400x100 image → 150x37 (width limited)
- 100x400 image → 37x150 (height limited)
- 300x300 image → 150x150 (square stays square)

### `fill` / `cover`

Guarantees exact dimensions by scaling and cropping. Use when you need thumbnails to be exactly the specified size.

```python
thumbnail = AdvanceThumbnailField(
    source_field='image',
    size=(150, 150),
    resize_method='fill',
)
```

**Examples:**
- 400x100 image → 150x150 (crops width)
- 100x400 image → 150x150 (crops height)
- 300x300 image → 150x150

### Using Constants

```python
from django_advance_thumbnail import (
    AdvanceThumbnailField,
    RESIZE_FIT,
    RESIZE_FILL,
    RESIZE_COVER,  # alias for RESIZE_FILL
)

thumbnail = AdvanceThumbnailField(
    source_field='image',
    size=(200, 200),
    resize_method=RESIZE_FILL,
)
```

## Smart Regeneration

By default, thumbnails are only regenerated when necessary:

- Source image changes (name, size, or content)
- `size` parameter is modified
- `resize_method` parameter is modified
- Thumbnail file doesn't exist

```python
class MyModel(models.Model):
    image = models.ImageField(upload_to='images/')
    thumbnail = AdvanceThumbnailField(
        source_field='image',
        size=(300, 300),  # Efficient - only regenerates when needed
    )
```

## Force Regeneration

Use `force_regenerate=True` only when you need thumbnails regenerated on every model save:

```python
thumbnail = AdvanceThumbnailField(
    source_field='image',
    size=(300, 300),
    force_regenerate=True,  # Not recommended for production
)
```

**Warning:** This impacts performance as it processes images on every save.

## Multiple Thumbnails

You can have multiple thumbnail fields from the same source:

```python
class Product(models.Model):
    image = models.ImageField(upload_to='products/')

    # Small for listings
    thumbnail_small = AdvanceThumbnailField(
        source_field='image',
        upload_to='thumbnails/small/',
        size=(100, 100),
        resize_method='fit',
    )

    # Medium for cards
    thumbnail_medium = AdvanceThumbnailField(
        source_field='image',
        upload_to='thumbnails/medium/',
        size=(300, 300),
        resize_method='fill',
    )

    # Large for detail pages
    thumbnail_large = AdvanceThumbnailField(
        source_field='image',
        upload_to='thumbnails/large/',
        size=(600, 600),
        resize_method='fill',
    )
```

## Management Commands

### Generate Thumbnails

Generate thumbnails for existing images (use when adding field to existing models):

```bash
# All models with AdvanceThumbnailField
python manage.py generate_thumbnails

# Specific model
python manage.py generate_thumbnails --model myapp.MyModel

# Specific field
python manage.py generate_thumbnails --model myapp.MyModel --field thumbnail

# Force regenerate existing thumbnails
python manage.py generate_thumbnails --force

# Preview without changes
python manage.py generate_thumbnails --dry-run
```

### Regenerate Thumbnails

Regenerate thumbnails after changing `size` or `resize_method`:

```bash
# Detect and regenerate changed configurations
python manage.py regenerate_thumbnails

# Force regenerate all thumbnails
python manage.py regenerate_thumbnails --force

# Specific model
python manage.py regenerate_thumbnails --model myapp.MyModel

# Clear cache to force detection
python manage.py regenerate_thumbnails --clear-cache

# Preview
python manage.py regenerate_thumbnails --dry-run
```

## Common Use Cases

### Adding Thumbnail Field to Existing Model

1. Add the field:
   ```python
   class Article(models.Model):
       title = models.CharField(max_length=200)
       image = models.ImageField(upload_to='articles/')
       thumbnail = AdvanceThumbnailField(
           source_field='image',
           upload_to='thumbnails/',
           size=(300, 300),
           null=True,
           blank=True,
       )
   ```

2. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. Generate thumbnails for existing images:
   ```bash
   python manage.py generate_thumbnails --model myapp.Article
   ```

### Changing Thumbnail Size

1. Update the size:
   ```python
   thumbnail = AdvanceThumbnailField(
       source_field='image',
       size=(400, 400),  # Changed from (300, 300)
   )
   ```

2. Regenerate:
   ```bash
   python manage.py regenerate_thumbnails --model myapp.Article
   ```

### Switching from `fit` to `fill`

1. Update the resize method:
   ```python
   thumbnail = AdvanceThumbnailField(
       source_field='image',
       size=(150, 150),
       resize_method='fill',  # Changed from 'fit'
   )
   ```

2. Regenerate:
   ```bash
   python manage.py regenerate_thumbnails --model myapp.Article
   ```

## Performance Tips

- Use smart regeneration (default) - avoids unnecessary processing
- Run management commands during off-peak hours for bulk operations
- Use `--dry-run` first to estimate scope
- Configure Django's cache framework for efficient change detection
- Avoid `force_regenerate=True` in production

## Thread Safety

Version 2.0+ is fully thread-safe for multi-threaded web servers (gunicorn, uwsgi, etc.). Thumbnail generation uses instance-level flags instead of global signal manipulation.

## Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png) - with transparency handling
- WebP (.webp)

RGBA images are automatically converted to RGB when saving as JPEG.

## Contact

- Email: [mh@mahadihassan.com](mailto:mh@mahadihassan.com)
- GitHub: [@itsmahadi007](https://github.com/itsmahadi007)
- LinkedIn: [Mahadi Hassan](https://linkedin.com/in/mahadi-hassan-4a2239154/)
- Web: [mahadihassan.com](https://mahadihassan.com)
