# Migration Guide

## Version 1.1.0 Changes

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

This version migrates from the legacy `setup.cfg` configuration to the modern `pyproject.toml` standard.

**What changed:**
- All package metadata moved from `setup.cfg` to `pyproject.toml`
- Added support for Python 3.11 and 3.12
- Improved build system configuration

**For developers:**
- The old `setup.cfg` file can be safely removed after migration
- Build commands remain the same: `python -m build`
- All functionality is preserved

### Bug Fixes

1. **Fixed queryset filtering logic** in management commands
2. **Improved error handling** for thumbnail generation
3. **Enhanced image processing** with better format support and transparency handling
4. **Cache error resilience** - graceful fallback when cache is not configured

### Usage Examples

```bash
# Generate thumbnails for all existing images
python manage.py generate_thumbnails

# Generate thumbnails for specific model
python manage.py generate_thumbnails --model MyApp.MyModel

# Regenerate thumbnails after size changes
python manage.py regenerate_thumbnails

# Force regeneration of all thumbnails
python manage.py regenerate_thumbnails --force
```

### Breaking Changes

None. This version is fully backward compatible.

### Requirements

- Django >= 3.0
- Pillow >= 8.0.0
- Python >= 3.6