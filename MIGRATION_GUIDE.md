# Migration Guide

## Version 2.0.0

### Breaking Changes

#### 1. `source_field` is now required

Previously, omitting `source_field` would silently fail. Now it raises `ImproperlyConfigured`:

```python
# v1.x - silently fails
thumbnail = AdvanceThumbnailField()  # No error, but doesn't work

# v2.0 - raises ImproperlyConfigured
thumbnail = AdvanceThumbnailField()  # Error: requires 'source_field' parameter

# Correct usage
thumbnail = AdvanceThumbnailField(source_field='image')
```

#### 2. `regenerate_thumbnails()` return value changed

```python
# v1.x
count = field.regenerate_thumbnails(Model)

# v2.0
count, errors = field.regenerate_thumbnails(Model)
```

#### 3. Parameter validation

Invalid parameters now raise `ImproperlyConfigured` instead of silently failing:

```python
# These now raise errors:
AdvanceThumbnailField(source_field=123)          # Must be string
AdvanceThumbnailField(source_field='img', size='invalid')  # Must be tuple
AdvanceThumbnailField(source_field='img', size=(0, 100))   # Must be positive
AdvanceThumbnailField(source_field='img', resize_method='invalid')  # Must be fit/fill/cover
```

### New Features

#### 1. `resize_method` parameter

Control how images are resized:

```python
from django_advance_thumbnail import AdvanceThumbnailField, RESIZE_FIT, RESIZE_FILL

# fit (default) - maintains aspect ratio, may be smaller than size
thumbnail = AdvanceThumbnailField(
    source_field='image',
    size=(150, 150),
    resize_method='fit',
)
# A 400x100 image becomes 150x37

# fill/cover - exact dimensions by cropping
thumbnail = AdvanceThumbnailField(
    source_field='image',
    size=(150, 150),
    resize_method='fill',
)
# A 400x100 image becomes exactly 150x150
```

#### 2. Thread-safe implementation

The signal disconnect/reconnect pattern has been replaced with instance-level flags. This fixes race conditions in multi-threaded environments (gunicorn, uwsgi, etc.).

**Before (v1.x) - Not thread-safe:**
```python
# Signal disconnected globally, other threads miss events
models.signals.post_save.disconnect(...)
try:
    generate_thumbnail()
finally:
    models.signals.post_save.connect(...)
```

**After (v2.0) - Thread-safe:**
```python
# Flag is per-instance, no global state
if getattr(instance, '_generating_thumbnail', False):
    return
instance._generating_thumbnail = True
try:
    generate_thumbnail()
finally:
    instance._generating_thumbnail = False
```

#### 3. `deconstruct()` method

Full Django migrations support. Field parameters are properly serialized.

#### 4. Improved logging

Silent exception swallowing replaced with proper logging:
- `logger.debug()` for cache operations
- `logger.error()` for thumbnail generation failures

### Upgrading

1. **Update your code** if you use `regenerate_thumbnails()`:
   ```python
   # Before
   count = field.regenerate_thumbnails(Model)

   # After
   count, errors = field.regenerate_thumbnails(Model)
   ```

2. **Check parameter validation**: Ensure all `AdvanceThumbnailField` declarations have valid parameters.

3. **Consider using `resize_method='fill'`** if you need guaranteed dimensions:
   ```python
   thumbnail = AdvanceThumbnailField(
       source_field='image',
       size=(150, 150),
       resize_method='fill',  # Guarantees 150x150
   )
   ```

4. **Run tests** to catch any validation errors.

---

## Version 1.1.0

### New Features

1. **Management Commands**:
   - `generate_thumbnails`: Create thumbnails for existing images
   - `regenerate_thumbnails`: Recreate thumbnails when size parameters change

2. **Automatic Size Change Detection**:
   - Thumbnails are automatically regenerated when size parameters are modified
   - Uses Django's cache framework for efficient detection

3. **Force Regeneration Option**:
   - Added `force_regenerate` parameter to `AdvanceThumbnailField`

### Project Structure Updates

#### Migration from setup.cfg to pyproject.toml

- All package metadata moved from `setup.cfg` to `pyproject.toml`
- Added support for Python 3.11 and 3.12
- Improved build system configuration

### Bug Fixes

1. Fixed queryset filtering logic in management commands
2. Improved error handling for thumbnail generation
3. Enhanced image processing with better format support and transparency handling
4. Cache error resilience - graceful fallback when cache is not configured

---

## Requirements

- Django >= 3.0
- Pillow >= 8.0.0
- Python >= 3.6
