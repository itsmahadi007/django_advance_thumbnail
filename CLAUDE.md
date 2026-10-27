# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django Advance Thumbnail is a reusable Django app that automates thumbnail creation for image fields. It provides `AdvanceThumbnailField`, a custom ImageField that automatically generates, updates, and deletes thumbnails based on a source image.

## Build and Development Commands

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install locally for development
pip install -e .

# Run tests
python -m pytest tests/ -v

# Build package
python -m build
```

### Management Commands

```bash
# Generate thumbnails for existing images
python manage.py generate_thumbnails
python manage.py generate_thumbnails --model myapp.MyModel --force

# Regenerate thumbnails after size/method changes
python manage.py regenerate_thumbnails
python manage.py regenerate_thumbnails --model myapp.MyModel --force --clear-cache
```

## Architecture

### Core Component: `AdvanceThumbnailField` (fields.py)

Custom Django ImageField that handles automatic thumbnail generation via `post_save` signals.

**Key parameters:**
- `source_field` (required): Name of the source ImageField
- `size`: Thumbnail dimensions, default `(300, 300)`
- `resize_method`: `'fit'` (default), `'fill'`, or `'cover'`
- `force_regenerate`: Regenerate on every save, default `False`

**Resize methods:**
- `fit`: Maintains aspect ratio, fits within size (may be smaller)
- `fill`/`cover`: Guarantees exact dimensions by cropping

**Signal flow (thread-safe):**
```
Model Save → post_save → create_thumbnail()
  ├→ Check _generating_thumbnail flag (prevents recursion)
  ├→ _has_source_image_changed() (cache-based detection)
  ├→ _should_regenerate_thumbnail() (config change detection)
  └→ _generate_thumbnail_file() (Pillow processing)
```

**Cache keys used:**
- Field config: `thumbnail_field_{app_label}_{model_name}_{field_name}_size`
- Source info: `thumbnail_source_{app_label}_{model_name}_{pk}_{field_name}`

### Management Commands (management/commands/)

- `generate_thumbnails.py`: Creates thumbnails for existing images
- `regenerate_thumbnails.py`: Regenerates thumbnails when config changes

### Image Processing

Uses Pillow with:
- LANCZOS resampling
- EXIF orientation handling via `ImageOps.exif_transpose()`
- `ImageOps.fit()` for fill/cover mode
- Quality 85, optimize enabled
- Supports JPEG, PNG, WebP formats
- Handles RGBA to RGB conversion for JPEG output

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_fields.py -v

# Run with coverage
python -m pytest tests/ --cov=django_advance_thumbnail
```

Test categories:
- `test_fields.py`: Core functionality
- `test_resize_methods.py`: Fit vs fill behavior
- `test_thread_safety.py`: Concurrent operations
- `test_validation.py`: Parameter validation
- `test_deconstruct.py`: Django migrations support

## Dependencies

- Django >=3.0
- Pillow >=8.0.0
- Django cache framework (optional, for change detection)

## Package Configuration

Modern Python packaging via `pyproject.toml`. Build backend: `setuptools.build_meta`.
