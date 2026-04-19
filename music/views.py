from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from mongoengine.errors import NotUniqueError
from .models import SavedSong


def _serialize(song):
    return {
        "id":           str(song.id),
        "videoId":      song.video_id,
        "title":        song.title,
        "channelTitle": song.channel_title,
        "thumbnail":    song.thumbnail,
        "audioUrl":     song.audio_url or "",
        "savedAt":      song.saved_at.isoformat(),
        "savedBy":      song.saved_by,
    }


class MusicLibraryView(APIView):
    """GET  /api/music/library  — return couple's saved songs
       POST /api/music/library  — save a song"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        couple_id = user.couple_id or str(user.id)
        songs = SavedSong.objects(couple_id=couple_id)
        return Response({"songs": [_serialize(s) for s in songs]})

    def post(self, request):
        user = request.user
        couple_id = user.couple_id or str(user.id)

        video_id      = request.data.get("videoId", "").strip()
        title         = request.data.get("title", "").strip()
        channel_title = request.data.get("channelTitle", "").strip()
        thumbnail     = request.data.get("thumbnail", "").strip()
        audio_url     = request.data.get("audioUrl", "").strip()

        if not video_id or not title:
            return Response({"error": "videoId and title are required"}, status=400)

        try:
            song = SavedSong(
                couple_id=couple_id,
                saved_by=str(user.id),
                video_id=video_id,
                title=title,
                channel_title=channel_title,
                thumbnail=thumbnail,
                audio_url=audio_url,
            )
            song.save()
            return Response(_serialize(song), status=201)
        except NotUniqueError:
            # Already saved — return 200 with existing record
            existing = SavedSong.objects(couple_id=couple_id, video_id=video_id).first()
            return Response(_serialize(existing), status=200)


class MusicSongDetailView(APIView):
    """DELETE /api/music/library/<video_id> — remove a song"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, video_id):
        user = request.user
        couple_id = user.couple_id or str(user.id)

        song = SavedSong.objects(couple_id=couple_id, video_id=video_id).first()
        if not song:
            return Response({"error": "Song not found"}, status=404)

        song.delete()
        return Response({"message": "Removed from library"})
