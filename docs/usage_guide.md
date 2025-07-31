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

## Advanced Features

### Smart Regeneration (Default Behavior)

By default, the field intelligently regenerates thumbnails only when necessary:

```python
class MyModel(models.Model):
    image = models.ImageField(upload_to='images/', null=True, blank=True)
    thumbnail = AdvanceThumbnailField(
        source_field='image', 
        upload_to='thumbnails/', 
        null=True, 
        blank=True,
        size=(300, 300)  # Automatically detects changes
    )
```

**Thumbnails are regenerated only when:**
- The source image file changes (name, size, or content)
- The thumbnail size parameter is modified
- The thumbnail file doesn't exist

### Force Regeneration (Override)

Use `force_regenerate=True` sparingly, only when you need thumbnails regenerated on every model save:

```python
class MyModel(models.Model):
    image = models.ImageField(upload_to='images/', null=True, blank=True)
    thumbnail = AdvanceThumbnailField(
        source_field='image', 
        upload_to='thumbnails/', 
        null=True, 
        blank=True,
        size=(300, 300),
        force_regenerate=True  # Not recommended for production
    )
```

**Note:** `force_regenerate=True` can impact performance as it processes images on every save, regardless of whether the source image changed.

### Automatic Size Change Detection

The field automatically detects when the `size` parameter has been changed and regenerates existing thumbnails accordingly. This is useful when you need to update thumbnail sizes in production.

## Management Commands

### Generate Thumbnails for Existing Images

When you add `AdvanceThumbnailField` to an existing model in production, you can generate thumbnails for all existing images using the `generate_thumbnails` management command:

```bash
# Generate thumbnails for all models with AdvanceThumbnailField
python manage.py generate_thumbnails

# Generate thumbnails for a specific model
python manage.py generate_thumbnails --model myapp.MyModel

# Generate thumbnails for a specific field in a model
python manage.py generate_thumbnails --model myapp.MyModel --field thumbnail

# Force regenerate thumbnails even if they already exist
python manage.py generate_thumbnails --force

# Dry run to see what would be done without actually generating thumbnails
python manage.py generate_thumbnails --dry-run
```

### Regenerate Thumbnails After Size Changes

When you change the `size` parameter of an `AdvanceThumbnailField`, you can regenerate all existing thumbnails with the new size using the `regenerate_thumbnails` management command:

```bash
# Regenerate thumbnails for fields where size has changed
python manage.py regenerate_thumbnails

# Force regenerate all thumbnails regardless of size changes
python manage.py regenerate_thumbnails --force

# Regenerate thumbnails for a specific model
python manage.py regenerate_thumbnails --model myapp.MyModel

# Regenerate thumbnails for a specific field
python manage.py regenerate_thumbnails --model myapp.MyModel --field thumbnail

# Clear the size cache to force detection of size changes
python manage.py regenerate_thumbnails --clear-cache

# Dry run to see what would be done
python manage.py regenerate_thumbnails --dry-run
```

## Use Cases

### Adding Thumbnail Field to Existing Production Model

1. Add the `AdvanceThumbnailField` to your model:
   ```python
   class Article(models.Model):
       title = models.CharField(max_length=200)
       image = models.ImageField(upload_to='articles/', null=True, blank=True)
       # Add this field
       thumbnail = AdvanceThumbnailField(
           source_field='image', 
           upload_to='thumbnails/', 
           null=True, 
           blank=True,
           size=(300, 300)
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

### Changing Thumbnail Size in Production

1. Update the size in your model:
   ```python
   thumbnail = AdvanceThumbnailField(
       source_field='image', 
       upload_to='thumbnails/', 
       null=True, 
       blank=True,
       size=(400, 400)  # Changed from (300, 300)
   )
   ```

2. Regenerate thumbnails with new size:
   ```bash
   python manage.py regenerate_thumbnails --model myapp.Article
   ```

## Performance Considerations

- Thumbnail generation happens automatically on model save, which may impact performance for large images
- Use the management commands during off-peak hours for bulk operations
- Consider using `--dry-run` first to estimate the scope of work
- The size change detection uses Django's cache framework, ensure your cache is properly configured

# Contact

For any questions or feedback, feel free to reach out:

- Email: [mh@mahadihassan.com](mailto:mh@mahadihassan.com), [me.mahadi10@gmail.com](mailto:me.mahadi10@gmail.com)
- Github: [@itsmahadi007](https://github.com/itsmahadi007)
- Linkedin: [Mahadi Hassan](https://linkedin.com/in/mahadi-hassan-4a2239154/)
- Web: [mahadihassan.com](https://mahadihassan.com)
