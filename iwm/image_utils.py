from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
import os
import logging

logger = logging.getLogger(__name__)


def optimize_uploaded_image(image_field, max_width=1200, max_height=1200, quality=85):
    """
    Optimize an uploaded image: resize if too large, convert to WebP, compress.

    Returns a new InMemoryUploadedFile in WebP format, or the original if
    conversion fails.

    This function should be called with the raw uploaded file (InMemoryUploadedFile
    or TemporaryUploadedFile).  It is NOT safe to call on a FieldFile that has
    already been committed to storage.
    """
    if not image_field:
        return image_field

    try:
        from PIL import Image

        # Seek to beginning of file in case it has been partially read.
        if hasattr(image_field, 'seek'):
            image_field.seek(0)

        img = Image.open(image_field)
        img.load()

        has_alpha = (
            img.mode in ('RGBA', 'LA')
            or (img.mode == 'P' and 'transparency' in img.info)
        )
        if has_alpha:
            img = img.convert('RGBA')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.LANCZOS)

        output = BytesIO()
        save_kwargs = {'format': 'WebP', 'quality': quality, 'method': 6}
        if has_alpha:
            save_kwargs['lossless'] = False
        img.save(output, **save_kwargs)
        output.seek(0)

        original_name = getattr(image_field, 'name', 'image') or 'image'
        base_name = os.path.basename(original_name)
        name_without_ext = os.path.splitext(base_name)[0]
        new_name = f"{name_without_ext}.webp"

        size = output.getbuffer().nbytes
        return InMemoryUploadedFile(
            output, 'image', new_name, 'image/webp', size, None
        )
    except Exception:
        logger.exception("Image optimization failed; using original.")
        if hasattr(image_field, 'seek'):
            try:
                image_field.seek(0)
            except Exception:
                pass
        return image_field


class WebPImageField(models.ImageField):
    """
    A drop-in replacement for ``ImageField`` that automatically converts every
    uploaded image to WebP format **before** writing it to storage.

    Why ``pre_save()`` is the correct interception layer
    ---------------------------------------------------
    Django's ``FileDescriptor.__get__`` may wrap the raw ``InMemoryUploadedFile``
    (or ``TemporaryUploadedFile``) into a ``FieldFile`` at any point after the
    value is assigned to the model instance (e.g. when admin code reads the
    attribute).  After wrapping, the ``__dict__`` slot contains a ``FieldFile``
    whose ``content_type`` attribute does NOT exist, so any ``hasattr(...,
    'content_type')`` check placed in ``Model.save()`` silently fails and the
    original file is persisted unchanged.

    ``FileField.pre_save()`` is called by Django's ORM during ``Model.save()``
    and is guaranteed to run *before* the file is written to the storage
    backend.  At that point:
    * ``field_file._committed`` is ``False``   (new upload)
    * ``field_file.file``        is the raw uploaded file object

    We intercept here, convert to WebP, replace ``field_file.file`` and
    ``field_file.name`` with the optimised result, then call ``super().pre_save()``
    which writes the (now WebP) content to storage.

    Migrations
    ----------
    ``deconstruct()`` returns ``'django.db.models.ImageField'`` so the database
    schema is identical to a plain ``ImageField`` and **no migration is needed**.
    """

    def __init__(self, *args, webp_max_width=1200, webp_max_height=1200, webp_quality=85, **kwargs):
        self.webp_max_width = webp_max_width
        self.webp_max_height = webp_max_height
        self.webp_quality = webp_quality
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        """
        Convert the uploaded image to WebP before Django writes it to storage.
        """
        # Access through the descriptor to ensure we get a FieldFile object.
        field_file = getattr(model_instance, self.attname)

        # Only process uncommitted (newly uploaded) files.
        if field_file and not field_file._committed:
            # .file holds the original InMemoryUploadedFile / TemporaryUploadedFile.
            uploaded = getattr(field_file, 'file', None)
            if uploaded is not None:
                try:
                    optimized = optimize_uploaded_image(
                        uploaded,
                        max_width=self.webp_max_width,
                        max_height=self.webp_max_height,
                        quality=self.webp_quality,
                    )
                    if optimized is not uploaded:
                        # Successfully converted - replace content and filename.
                        field_file.file = optimized
                        # field_file.name is the bare upload name (no upload_to prefix yet).
                        # generate_filename() will prepend upload_to in super().pre_save().
                        field_file.name = optimized.name  # e.g. 'photo.webp'
                except Exception:
                    logger.exception(
                        "WebP conversion failed in WebPImageField.pre_save(); "
                        "original file will be stored."
                    )

        return super().pre_save(model_instance, add)

    def deconstruct(self):
        """
        Represent this field as a plain ImageField in migrations so that no
        schema migration is generated when switching from ImageField.
        """
        name, path, args, kwargs = super().deconstruct()
        # webp_* params were NOT passed to super().__init__(), so they are
        # not in kwargs already - just redirect the path.
        return name, 'django.db.models.ImageField', args, kwargs
