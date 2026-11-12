# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [2.0.2] - Unreleased

### Fixed
- Thumbnails were silently not generated on Pillow 8.0 – 9.0. The code used `Image.Resampling`, which only exists from Pillow 9.1, and the error was only logged. The field now picks the LANCZOS filter in a way that works on every supported Pillow version.

### Added
- CI test matrix on GitHub Actions covering Python 3.9 – 3.14, Django 3.2 – 6.x and Pillow 8.4 – latest.
- Regression test for Pillow versions without `Image.Resampling`.
- `llms.txt` with a compact integration guide for AI coding assistants.
- README visuals: a "how it works" diagram and a real fit-vs-fill comparison.

### Changed
- `pytest.ini` puts the repository root on the import path, so `pytest` works from a fresh clone.
- Package metadata: clearer description, keywords, Django 6.0/6.1 and Python 3.13/3.14 classifiers, documentation and changelog links.

## [2.0.1] - 2026-08-30

### Fixed
- A cache miss (restart, eviction, per-process cache) no longer counts as a changed source, so thumbnails are not regenerated needlessly ([#9](https://github.com/itsmahadi007/django_advance_thumbnail/issues/9)).

## Earlier releases

**January 2026 (2.0)**
- `resize_method` option: `fit` (default) or `fill` / `cover` for exact, center-cropped dimensions ([#4](https://github.com/itsmahadi007/django_advance_thumbnail/issues/4)).
- Thread safe under multi-threaded and parallel servers: recursion is prevented with an instance flag instead of disconnecting signals ([#7](https://github.com/itsmahadi007/django_advance_thumbnail/issues/7)).
- **Breaking:** `source_field` is required and options are validated at startup (`ImproperlyConfigured`); `regenerate_thumbnails()` returns `(count, errors)`. See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md).
- Test suite.

**July 2025**
- `generate_thumbnails` and `regenerate_thumbnails` management commands.
- Regeneration when `size` changes; no regeneration on every save ([#6](https://github.com/itsmahadi007/django_advance_thumbnail/issues/6)).
- WebP with an alpha channel ([#5](https://github.com/itsmahadi007/django_advance_thumbnail/issues/5)).

**June 2024 (1.0.1 – 1.0.2)**
- EXIF orientation handling and improved thumbnail generation.

[2.0.2]: https://github.com/itsmahadi007/django_advance_thumbnail/compare/v2.0.1...HEAD
[2.0.1]: https://github.com/itsmahadi007/django_advance_thumbnail/releases/tag/v2.0.1
