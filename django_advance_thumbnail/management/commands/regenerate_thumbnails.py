from django.core.management.base import BaseCommand
from django.apps import apps
from django.core.cache import cache
from django_advance_thumbnail.fields import AdvanceThumbnailField


class Command(BaseCommand):
    help = 'Regenerate thumbnails when size parameters have changed'

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
            help='Force regenerate all thumbnails regardless of size changes'
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear size cache to force detection of size changes'
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
            self.stdout.write('Clearing thumbnail size cache...')
            if not dry_run:
                self._clear_thumbnail_cache()
            self.stdout.write(self.style.SUCCESS('Cache cleared.'))
        
        models_with_thumbnail_fields = self.get_models_with_thumbnail_fields(model_filter)
        
        if not models_with_thumbnail_fields:
            self.stdout.write(self.style.WARNING('No models found with AdvanceThumbnailField'))
            return
        
        total_processed = 0
        total_regenerated = 0
        
        for model_class, thumbnail_fields in models_with_thumbnail_fields.items():
            model_name = f"{model_class._meta.app_label}.{model_class.__name__}"
            
            # Filter fields if specified
            if field_filter:
                thumbnail_fields = [f for f in thumbnail_fields if f.name == field_filter]
                if not thumbnail_fields:
                    continue
            
            self.stdout.write(f"\nProcessing model: {model_name}")
            
            for thumbnail_field in thumbnail_fields:
                self.stdout.write(f"  Field: {thumbnail_field.name} (size: {thumbnail_field.size})")
                
                # Check if size has changed
                size_changed = self._has_size_changed(thumbnail_field)
                
                if not force and not size_changed:
                    self.stdout.write(f"    No size change detected, skipping (use --force to regenerate anyway)")
                    continue
                
                if size_changed:
                    self.stdout.write(f"    Size change detected!")
                
                queryset = model_class.objects.all()
                
                # Filter objects that have source images
                source_field_name = thumbnail_field.source_field_name
                # Get objects that have source images (not null and not empty)
                queryset = queryset.filter(**{f"{source_field_name}__isnull": False}).exclude(**{source_field_name: ""})
                
                count = queryset.count()
                self.stdout.write(f"    Found {count} objects with source images")
                
                if count == 0:
                    continue
                
                processed = 0
                regenerated = 0
                
                for instance in queryset:
                    total_processed += 1
                    processed += 1
                    
                    if dry_run:
                        self.stdout.write(f"    Would regenerate thumbnail for {instance.pk}")
                        continue
                    
                    try:
                        # Set force_regenerate temporarily
                        original_force = thumbnail_field.force_regenerate
                        thumbnail_field.force_regenerate = True
                        
                        source_field = getattr(instance, source_field_name)
                        thumbnail_field._generate_thumbnail_file(instance, source_field)
                        
                        # Restore original force setting
                        thumbnail_field.force_regenerate = original_force
                        
                        regenerated += 1
                        total_regenerated += 1
                        self.stdout.write(f"    Regenerated thumbnail for {instance.pk}")
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"    Error regenerating thumbnail for {instance.pk}: {str(e)}")
                        )
                
                if not dry_run:
                    self.stdout.write(f"    Regenerated {regenerated}/{processed} thumbnails")
                    # Update the cache with new size
                    thumbnail_field._store_field_config()
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"\nDry run completed. Would process {total_processed} objects."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nCompleted! Regenerated {total_regenerated}/{total_processed} thumbnails."))
    
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
    
    def _has_size_changed(self, thumbnail_field):
        """Check if the thumbnail field size has changed"""
        if not hasattr(thumbnail_field, '_cache_key'):
            return False
        
        cached_size = cache.get(thumbnail_field._cache_key)
        return cached_size != thumbnail_field.size
    
    def _clear_thumbnail_cache(self):
        """Clear all thumbnail size cache entries"""
        # This is a simple implementation - in production you might want to use
        # a more sophisticated cache key pattern matching
        for model_class in apps.get_models():
            for field in model_class._meta.get_fields():
                if isinstance(field, AdvanceThumbnailField) and hasattr(field, '_cache_key'):
                    cache.delete(field._cache_key)