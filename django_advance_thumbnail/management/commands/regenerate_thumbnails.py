import logging
from django.core.management.base import BaseCommand
from django.apps import apps
from django.core.cache import cache
from django_advance_thumbnail.fields import AdvanceThumbnailField

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Regenerate thumbnails when size or resize_method parameters have changed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            help='Specify a model in format "app_label.ModelName" to regenerate thumbnails for specific model only'
        )
        parser.add_argument(
            '--field',
            type=str,
            help='Specify a field name to regenerate thumbnails for specific field only (use with --model)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regenerate all thumbnails regardless of config changes'
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear config cache to force detection of changes'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually regenerating thumbnails'
        )

    def handle(self, *args, **options):
        model_filter = options.get('model')
        field_filter = options.get('field')
        force = options.get('force', False)
        clear_cache = options.get('clear_cache', False)
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No thumbnails will be regenerated'))

        if clear_cache:
            self.stdout.write('Clearing thumbnail config cache...')
            if not dry_run:
                self._clear_thumbnail_cache()
            self.stdout.write(self.style.SUCCESS('Cache cleared.'))

        models_with_thumbnail_fields = self.get_models_with_thumbnail_fields(model_filter)

        if not models_with_thumbnail_fields:
            self.stdout.write(self.style.WARNING('No models found with AdvanceThumbnailField'))
            return

        total_processed = 0
        total_regenerated = 0
        total_errors = 0

        for model_class, thumbnail_fields in models_with_thumbnail_fields.items():
            model_name = f"{model_class._meta.app_label}.{model_class.__name__}"

            # Filter fields if specified
            if field_filter:
                thumbnail_fields = [f for f in thumbnail_fields if f.name == field_filter]
                if not thumbnail_fields:
                    continue

            self.stdout.write(f"\nProcessing model: {model_name}")

            for thumbnail_field in thumbnail_fields:
                resize_info = f"size={thumbnail_field.size}, method={thumbnail_field.resize_method}"
                self.stdout.write(f"  Field: {thumbnail_field.name} ({resize_info})")

                # Check if config has changed
                config_changed = self._has_config_changed(thumbnail_field)

                if not force and not config_changed:
                    self.stdout.write(f"    No config change detected, skipping (use --force to regenerate anyway)")
                    continue

                if config_changed:
                    self.stdout.write(f"    Config change detected!")

                queryset = model_class.objects.all()

                # Filter objects that have source images
                source_field_name = thumbnail_field.source_field_name
                # Get objects that have source images (not null and not empty)
                queryset = queryset.filter(
                    **{f"{source_field_name}__isnull": False}
                ).exclude(**{source_field_name: ""})

                count = queryset.count()
                self.stdout.write(f"    Found {count} objects with source images")

                if count == 0:
                    continue

                processed = 0
                regenerated = 0
                errors = 0

                for instance in queryset:
                    total_processed += 1
                    processed += 1

                    if dry_run:
                        self.stdout.write(f"    Would regenerate thumbnail for {instance.pk}")
                        continue

                    try:
                        # Set flag to prevent signal handler from interfering
                        instance._generating_thumbnail = True

                        source_field = getattr(instance, source_field_name, None)
                        thumbnail_field._generate_thumbnail_file(instance, source_field)

                        regenerated += 1
                        total_regenerated += 1
                        self.stdout.write(f"    Regenerated thumbnail for {instance.pk}")

                    except Exception as e:
                        errors += 1
                        total_errors += 1
                        self.stdout.write(
                            self.style.ERROR(f"    Error regenerating thumbnail for {instance.pk}: {str(e)}")
                        )
                        logger.error(f"Error regenerating thumbnail for {model_name} pk={instance.pk}: {e}")
                    finally:
                        instance._generating_thumbnail = False

                if not dry_run:
                    self.stdout.write(f"    Regenerated {regenerated}/{processed} thumbnails")
                    if errors:
                        self.stdout.write(self.style.WARNING(f"    {errors} errors occurred"))
                    # Update the cache with new config
                    thumbnail_field._store_field_config()

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"\nDry run completed. Would process {total_processed} objects."))
        else:
            msg = f"\nCompleted! Regenerated {total_regenerated}/{total_processed} thumbnails."
            if total_errors:
                msg += f" ({total_errors} errors)"
            self.stdout.write(self.style.SUCCESS(msg))

    def get_models_with_thumbnail_fields(self, model_filter=None):
        """Get all models that have AdvanceThumbnailField fields"""
        models_with_fields = {}

        for model_class in apps.get_models():
            if model_filter:
                model_name = f"{model_class._meta.app_label}.{model_class.__name__}"
                if model_name != model_filter:
                    continue

            thumbnail_fields = []
            for field in model_class._meta.get_fields():
                if isinstance(field, AdvanceThumbnailField):
                    thumbnail_fields.append(field)

            if thumbnail_fields:
                models_with_fields[model_class] = thumbnail_fields

        return models_with_fields

    def _has_config_changed(self, thumbnail_field):
        """Check if the thumbnail field config has changed"""
        if not hasattr(thumbnail_field, '_cache_key'):
            return False

        cached_config = cache.get(thumbnail_field._cache_key)
        current_config = {
            'size': thumbnail_field.size,
            'resize_method': thumbnail_field.resize_method,
        }
        return cached_config != current_config

    def _clear_thumbnail_cache(self):
        """Clear all thumbnail config cache entries"""
        for model_class in apps.get_models():
            for field in model_class._meta.get_fields():
                if isinstance(field, AdvanceThumbnailField) and hasattr(field, '_cache_key'):
                    cache.delete(field._cache_key)
