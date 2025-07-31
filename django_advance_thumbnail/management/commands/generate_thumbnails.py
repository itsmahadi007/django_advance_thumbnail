import io
import os
from django.core.management.base import BaseCommand
from django.apps import apps
from django.core.files import File
from PIL import Image, ImageOps
from django_advance_thumbnail.fields import AdvanceThumbnailField


class Command(BaseCommand):
    help = 'Generate thumbnails for existing images in AdvanceThumbnailField fields'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            help='Specify a model in format "app_label.ModelName" to generate thumbnails for specific model only'
        )
        parser.add_argument(
            '--field',
            type=str,
            help='Specify a field name to generate thumbnails for specific field only (use with --model)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regenerate thumbnails even if they already exist'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually generating thumbnails'
        )

    def handle(self, *args, **options):
        model_filter = options.get('model')
        field_filter = options.get('field')
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No thumbnails will be generated'))
        
        models_with_thumbnail_fields = self.get_models_with_thumbnail_fields(model_filter)
        
        if not models_with_thumbnail_fields:
            self.stdout.write(self.style.WARNING('No models found with AdvanceThumbnailField'))
            return
        
        total_processed = 0
        total_generated = 0
        
        for model_class, thumbnail_fields in models_with_thumbnail_fields.items():
            model_name = f"{model_class._meta.app_label}.{model_class.__name__}"
            
            # Filter fields if specified
            if field_filter:
                thumbnail_fields = [f for f in thumbnail_fields if f.name == field_filter]
                if not thumbnail_fields:
                    continue
            
            self.stdout.write(f"\nProcessing model: {model_name}")
            
            for thumbnail_field in thumbnail_fields:
                self.stdout.write(f"  Field: {thumbnail_field.name}")
                
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
                generated = 0
                
                for instance in queryset:
                    total_processed += 1
                    processed += 1
                    
                    source_field = getattr(instance, source_field_name)
                    thumbnail_field_value = getattr(instance, thumbnail_field.name)
                    
                    # Skip if thumbnail exists and not forcing
                    if thumbnail_field_value and not force:
                        continue
                    
                    if dry_run:
                        self.stdout.write(f"    Would generate thumbnail for {instance.pk}")
                        continue
                    
                    try:
                        success = self.generate_thumbnail(instance, thumbnail_field, source_field)
                        if success:
                            generated += 1
                            total_generated += 1
                            self.stdout.write(f"    Generated thumbnail for {instance.pk}")
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"    Error generating thumbnail for {instance.pk}: {str(e)}")
                        )
                
                if not dry_run:
                    self.stdout.write(f"    Generated {generated}/{processed} thumbnails")
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"\nDry run completed. Would process {total_processed} objects."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nCompleted! Generated {total_generated}/{total_processed} thumbnails."))
    
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
    
    def generate_thumbnail(self, instance, thumbnail_field, source_field):
        """Generate thumbnail for a specific instance and field"""
        if not source_field or not source_field.name:
            return False
        
        try:
            with source_field.open() as source_file:
                img = Image.open(source_file)
                
                # Handle orientation from EXIF data
                img = ImageOps.exif_transpose(img)
                
                img.thumbnail(thumbnail_field.size)
                
                filename, extension = os.path.splitext(os.path.basename(source_field.name))
                thumbnail_filename = f"{filename}_thumbnail{extension}"
                
                thumbnail_io = io.BytesIO()
                
                # Determine the format based on the file extension
                if extension.lower() in ['.jpg', '.jpeg']:
                    image_format = 'JPEG'
                elif extension.lower() == '.png':
                    image_format = 'PNG'
                else:
                    image_format = 'JPEG'  # Default to JPEG
                
                img.save(thumbnail_io, format=image_format)
                thumbnail_io.seek(0)
                
                thumbnail_file = File(thumbnail_io, name=thumbnail_filename)
                setattr(instance, thumbnail_field.name, thumbnail_file)
                
                instance.save(update_fields=[thumbnail_field.name])
                return True
                
        except Exception:
            raise
        
        return False