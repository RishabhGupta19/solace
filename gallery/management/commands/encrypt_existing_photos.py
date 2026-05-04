import io

import cloudinary.uploader
import requests
from django.core.management.base import BaseCommand

from gallery.models import GalleryPhoto
from gallery.utils import upload_encrypted


def _legacy_public_id(image_url):
    if not image_url or "/upload/" not in image_url:
        return None
    suffix = image_url.split("/upload/", 1)[1].split("?", 1)[0]
    if "/" in suffix and suffix.split("/", 1)[0].startswith("v"):
        suffix = suffix.split("/", 1)[1]
    return suffix.rsplit(".", 1)[0]


class Command(BaseCommand):
    help = "Re-encrypt existing gallery photos and move them to encrypted raw Cloudinary storage."

    def handle(self, *args, **options):
        updated = 0
        skipped = 0

        for photo in GalleryPhoto.objects:
            source_url = photo.image_url or None
            if not source_url or source_url.startswith("/gallery/photo/"):
                skipped += 1
                continue

            try:
                response = requests.get(source_url, timeout=30)
                response.raise_for_status()
                file_obj = io.BytesIO(response.content)
                file_obj.name = "legacy-gallery-photo"
                new_public_id = upload_encrypted(file_obj)

                old_public_id = photo.cloudinary_public_id or _legacy_public_id(source_url)
                if old_public_id:
                    try:
                        cloudinary.uploader.destroy(old_public_id, resource_type="image")
                    except Exception:
                        pass

                photo.cloudinary_public_id = new_public_id
                photo.image_url = f"/gallery/photo/{photo.id}/"
                photo.save()
                updated += 1
            except Exception as exc:
                skipped += 1
                self.stderr.write(f"Failed to encrypt photo {photo.id}: {exc}")

        self.stdout.write(self.style.SUCCESS(f"Encrypted {updated} photos; skipped {skipped}."))