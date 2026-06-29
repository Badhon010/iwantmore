from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import os
import logging

logger = logging.getLogger(__name__)


def optimize_uploaded_image(image_field, max_width=1200, max_height=1200, quality=85):
    """
    Optimize an uploaded image: resize if too large, convert to WebP, compress.
    Returns a new InMemoryUploadedFile, or the original if optimization fails.
    Only processes UploadedFile objects (new uploads), not existing FieldFile objects.
    """
    if not image_field:
        return image_field

    if not hasattr(image_field, 'content_type'):
        return image_field

    try:
        from PIL import Image

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
