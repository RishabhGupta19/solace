import io

import cloudinary.uploader
import cloudinary.utils
import requests
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.cache import cache
from PIL import Image, ImageOps


cipher = Fernet(settings.GALLERY_ENCRYPTION_KEY)


def upload_encrypted(file_obj):
    file_obj.seek(0)
    image = Image.open(file_obj)
    # Preserve EXIF orientation by applying rotation before conversion
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=75, optimize=True)
    encrypted = cipher.encrypt(buffer.getvalue())

    payload = io.BytesIO(encrypted)
    payload.name = "gallery-photo.enc"

    result = cloudinary.uploader.upload(
        payload,
        resource_type="raw",
        folder="gallery/encrypted",
    )
    return result["public_id"]


def get_decrypted_photo(public_id):
    cache_key = f"photo:{public_id}"
    try:
        cached = cache.get(cache_key)
        if cached:
            return cached
    except Exception:
        cached = None

    url = cloudinary.utils.cloudinary_url(public_id, resource_type="raw")[0]
    encrypted = requests.get(url, timeout=30).content
    raw = cipher.decrypt(encrypted)
    try:
        cache.set(cache_key, raw, timeout=3600)
    except Exception:
        pass
    return raw