import os

from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from .utils import get_decrypted_photo, upload_encrypted
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
        "image_url": _photo_serve_url(photo.id),
        "note": photo.note,
        "created_at": photo.created_at.isoformat() if photo.created_at else None,
    }


def _photo_serve_url(photo_id):
    return f"/api/gallery/photo/{photo_id}/"


def _legacy_public_id(image_url):
    if not image_url or "/upload/" not in image_url:
        return None
    suffix = image_url.split("/upload/", 1)[1].split("?", 1)[0]
    if "/" in suffix and suffix.split("/", 1)[0].startswith("v"):
        suffix = suffix.split("/", 1)[1]
    return suffix.rsplit(".", 1)[0]


class GalleryListCreateView(APIView):
    """
    GET  — list all photos for the authenticated user's couple.
    POST — upload an encrypted photo to Cloudinary and save metadata.
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
            public_id = upload_encrypted(file)
        except Exception as e:
            return Response({"error": f"Cloudinary upload failed: {e}"}, status=500)

        # Save to MongoDB
        photo = GalleryPhoto(
            couple_id=couple_id,
            uploaded_by=str(user.id),
            image_url="",
            cloudinary_public_id=public_id,
        )
        photo.save()
        photo.image_url = _photo_serve_url(photo.id)
        photo.save()

        return Response(_serialize_photo(photo), status=201)


class PhotoServeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, photo_id):
        user = request.user
        couple_id = getattr(user, "couple_id", None) or str(user.id)

        try:
            photo = GalleryPhoto.objects.get(id=photo_id, couple_id=couple_id)
        except GalleryPhoto.DoesNotExist:
            return Response({"error": "Photo not found"}, status=404)

        if not photo.cloudinary_public_id:
            return Response({"error": "Photo is unavailable"}, status=404)

        raw = get_decrypted_photo(photo.cloudinary_public_id)

        def stream():
            for i in range(0, len(raw), 8192):
                yield raw[i : i + 8192]

        return StreamingHttpResponse(stream(), content_type="image/jpeg")


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
        public_id = photo.cloudinary_public_id or _legacy_public_id(photo.image_url)
        if public_id:
            try:
                cloudinary_uploader = _get_cloudinary_uploader()
                resource_type = "raw" if str(photo.image_url or "").startswith("/api/gallery/photo/") else "image"
                cloudinary_uploader.destroy(public_id, resource_type=resource_type)
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
