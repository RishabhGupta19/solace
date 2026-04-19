import os
import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .models import GalleryPhoto

# Lazy-loaded Cloudinary uploader (same pattern as chat/views.py)
_cloudinary_uploader = None


def _get_cloudinary_uploader():
    global _cloudinary_uploader
    if _cloudinary_uploader is not None:
        return _cloudinary_uploader
    import cloudinary.uploader as cloudinary_uploader
    _cloudinary_uploader = cloudinary_uploader
    return _cloudinary_uploader


def _serialize_photo(photo):
    return {
        "id": str(photo.id),
        "couple_id": photo.couple_id,
        "uploaded_by": photo.uploaded_by,
        "image_url": photo.image_url,
        "note": photo.note,
        "created_at": photo.created_at.isoformat() if photo.created_at else None,
    }


class GalleryListCreateView(APIView):
    """
    GET  — list all photos for the authenticated user's couple.
    POST — upload a new photo to Cloudinary and save metadata.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        user = request.user
        couple_id = getattr(user, "couple_id", None) or str(user.id)
        photos = GalleryPhoto.objects(couple_id=couple_id).order_by("-created_at")
        return Response({"photos": [_serialize_photo(p) for p in photos]})

    def post(self, request):
        user = request.user
        couple_id = getattr(user, "couple_id", None) or str(user.id)

        file = request.FILES.get("image") or request.FILES.get("file")
        if not file:
            return Response({"error": "No file provided"}, status=400)

        # Validate file type
        allowed = ("image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif")
        if file.content_type not in allowed:
            return Response({"error": "Invalid file type"}, status=400)

        # Validate file size (10 MB)
        max_size = 10 * 1024 * 1024
        if file.size > max_size:
            return Response({"error": "File too large (max 10MB)"}, status=400)

        # Check Cloudinary is available
        if not os.getenv("CLOUDINARY_URL", ""):
            return Response({"error": "CLOUDINARY_URL is not configured"}, status=500)

        try:
            cloudinary_uploader = _get_cloudinary_uploader()
        except Exception as e:
            return Response({"error": f"Cloudinary SDK not available: {e}"}, status=500)

        # Upload to Cloudinary
        try:
            unique_id = f"gallery/{couple_id}/{int(time.time())}_{str(user.id)[-6:]}"
            result = cloudinary_uploader.upload(
                file,
                public_id=unique_id,
                folder="gallery",
                overwrite=True,
                resource_type="image",
            )
            image_url = result.get("secure_url") or result.get("url")
            public_id = result.get("public_id")
        except Exception as e:
            return Response({"error": f"Cloudinary upload failed: {e}"}, status=500)

        # Save to MongoDB
        photo = GalleryPhoto(
            couple_id=couple_id,
            uploaded_by=str(user.id),
            image_url=image_url,
            cloudinary_public_id=public_id,
        )
        photo.save()

        return Response(_serialize_photo(photo), status=201)


class GalleryDeleteView(APIView):
    """DELETE — remove a photo (Cloudinary + MongoDB)."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, photo_id):
        user = request.user
        couple_id = getattr(user, "couple_id", None) or str(user.id)

        try:
            photo = GalleryPhoto.objects.get(id=photo_id, couple_id=couple_id)
        except GalleryPhoto.DoesNotExist:
            return Response({"error": "Photo not found"}, status=404)

        # Only the uploader may delete
        if photo.uploaded_by != str(user.id):
            return Response({"error": "Only the uploader can delete this photo"}, status=403)

        # Delete from Cloudinary
        if photo.cloudinary_public_id:
            try:
                cloudinary_uploader = _get_cloudinary_uploader()
                cloudinary_uploader.destroy(photo.cloudinary_public_id, resource_type="image")
            except Exception:
                pass  # non-fatal

        photo.delete()
        return Response({"message": "Photo deleted"})


class GalleryNoteView(APIView):
    """PUT — update or clear the note on a photo."""
    permission_classes = [IsAuthenticated]

    def put(self, request, photo_id):
        user = request.user
        couple_id = getattr(user, "couple_id", None) or str(user.id)

        try:
            photo = GalleryPhoto.objects.get(id=photo_id, couple_id=couple_id)
        except GalleryPhoto.DoesNotExist:
            return Response({"error": "Photo not found"}, status=404)

        note = request.data.get("note")
        photo.note = note if note else None
        photo.save()

        return Response(_serialize_photo(photo))
