import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from urllib.parse import parse_qs
from couples.models import CoupleLink
from auth_app.models import User
from notifications import send_push_notification
from .encryption import decrypt_text


class CalmChatConsumer(AsyncWebsocketConsumer):
    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def connect(self):
        self.couple_id      = self.scope["url_route"]["kwargs"]["couple_id"]
        self.room_group_name = f"calm_{self.couple_id}"

        # Fetch and cache user identity at connection time (from JWT token)
        self.user_role = await self.get_role_from_token()
        self.user_id   = await self.get_user_id_from_token()

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # ── Receive (text frames) ─────────────────────────────────────────────────

    async def receive(self, text_data):
        data = json.loads(text_data)
        print(f"[RECEIVE] user={self.user_id} channel={self.channel_name} type={data.get('type')} text={str(data.get('text',''))[:20]}")

        # Mark messages as seen
        if data.get("type") == "seen":
            await self.mark_messages_seen(data.get("message_ids", []))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type":        "messages_seen",
                    "message_ids": data.get("message_ids", []),
                    "seen_by":     self.user_id,
                }
            )
            return

        # Typing indicator
        if data.get("type") == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "typing_indicator", "channel": self.channel_name}
            )
            return

        # Regular text message
        text = data.get("text", "").strip()
        sender_name = data.get("sender_name", "")
        client_temp_id = data.get("client_temp_id") or data.get("tempId")
        reply_to = data.get("reply_to") if isinstance(data.get("reply_to"), dict) else None

        if not text:
            return

        sender_role = self.user_role or data.get("sender_role", "")
        message = await self.save_message(text, sender_role, reply_to, client_temp_id)

        reply_payload = None
        if getattr(message, "reply_to_id", None) and getattr(message, "reply_to_text", None):
            reply_payload = {
                "id": message.reply_to_id,
                "text": decrypt_text(getattr(message, "reply_to_text", "") or ""),
                "sender_name": getattr(message, "reply_to_sender_name", "") or "",
            }

        reply_to_camel = None
        if getattr(message, "reply_to_message_id", None) and getattr(message, "reply_to_text", None):
            reply_to_camel = {
                "messageId": message.reply_to_message_id,
                "text": decrypt_text(getattr(message, "reply_to_text", "") or ""),
            }

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type":        "chat_message",
                "id":          str(message.id),
                "text":        text,
                "sender":      "user",
                "sender_role": sender_role,
                "sender_id":   self.user_id,
                "sender_name": sender_name,
                "timestamp":   message.timestamp.isoformat(),
                "client_temp_id": client_temp_id,
                "reply_to": reply_payload,
                "replyTo": reply_to_camel,
            }
        )

        # Delay push briefly so real-time "seen" can suppress notification noise.
        asyncio.create_task(self.send_text_push_if_unseen(str(message.id), text))

    # ── Channel layer event handlers ──────────────────────────────────────────

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "id":          event["id"],
            "text":        event["text"],
            "sender":      event["sender"],
            "sender_role": event["sender_role"],
            "sender_id":   event.get("sender_id", ""),
            "sender_name": event["sender_name"],
            "timestamp":   event["timestamp"],
            "client_temp_id": event.get("client_temp_id"),
            "reply_to": event.get("reply_to"),
            "replyTo": event.get("replyTo"),
        }))

    async def voice_message(self, event):
        """Broadcast a voice message to every client in the room."""
        await self.send(text_data=json.dumps({
            "id":          event["id"],
            "type":        "voice",          # frontend uses this to pick VoiceBubble
            "sender":      "user",
            "sender_role": event.get("sender_role", ""),
            "sender_id":   event.get("sender_id", ""),
            "audio_url":   event["audio_url"],
            "duration":    event.get("duration", 0),
            "mode":        event.get("mode", "calm"),
            "timestamp":   event["timestamp"],
            "expires_at":  event.get("expires_at"),
        }))

    async def voice(self, event):
        """Compatibility handler for legacy channel messages using type='voice'."""
        await self.send(text_data=json.dumps({
            "id":          event.get("id", ""),
            "type":        "voice",
            "sender":      "user",
            "sender_role": event.get("sender_role", ""),
            "sender_id":   event.get("sender_id", ""),
            "audio_url":   event.get("audio_url") or event.get("url", ""),
            "duration":    event.get("duration", 0),
            "mode":        event.get("mode", "calm"),
            "timestamp":   event.get("timestamp", ""),
            "expires_at":  event.get("expires_at"),
        }))

    async def messages_seen(self, event):
        await self.send(text_data=json.dumps({
            "type":        "seen",
            "message_ids": event["message_ids"],
            "seen_by":     event["seen_by"],
        }))
    
    async def typing_indicator(self, event):
        # Only forward to other connections, not the sender
        if event.get("channel") != self.channel_name:
            await self.send(text_data=json.dumps({"type": "typing"}))

    # ── DB helpers ────────────────────────────────────────────────────────────

    @database_sync_to_async
    def get_user_id_from_token(self):
        try:
            query_string = self.scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            token  = params.get("token", [None])[0]
            from auth_app.utils import decode_token
            payload = decode_token(token)
            return payload["user_id"]
        except Exception:
            return ""

    @database_sync_to_async
    def get_role_from_token(self):
        try:
            query_string = self.scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            token  = params.get("token", [None])[0]
            if not token:
                return ""
            from auth_app.utils import decode_token
            from auth_app.models import User
            payload = decode_token(token)
            user    = User.objects.get(id=payload["user_id"])
            return user.role or ""
        except Exception:
            return ""

    @database_sync_to_async
    def mark_messages_seen(self, message_ids):
        from chat.models import Message
        from datetime import datetime
        Message.objects(
            id__in=message_ids,
            user_id__ne=self.user_id   # only mark partner's messages
        ).update(seen=True, seen_at=datetime.utcnow())

    @database_sync_to_async
    def is_message_seen(self, message_id):
        from chat.models import Message
        msg = Message.objects(id=message_id).first()
        return bool(getattr(msg, "seen", False)) if msg else False

    async def send_text_push_if_unseen(self, message_id, text):
        # Give receiver a short window to mark as seen while actively chatting.
        await asyncio.sleep(1.5)
        try:
            if await self.is_message_seen(message_id):
                print(f"[PUSH_SKIPPED] seen within delay message_id={message_id}")
                return
        except Exception as e:
            print(f"[PUSH_DELAY_CHECK_ERROR] message_id={message_id} err={e}")
        await self.send_text_push(message_id, text)

    @database_sync_to_async
    def send_text_push(self, message_id, text):
        print(f"[PUSH_ATTEMPT] message_id={message_id} from_user={self.user_id}")
        try:
            link = CoupleLink.objects.get(id=self.couple_id)
            partner_id = link.partner_id if link.creator_id == self.user_id else link.creator_id
            if not partner_id:
                return
            partner = User.objects.get(id=partner_id)
            if not partner.fcm_token:
                return
            notification_key = f"text:{message_id}"
            claimed = User.objects(
                id=partner_id,
                last_notified_message_id__ne=notification_key,
            ).update_one(set__last_notified_message_id=notification_key)
            if claimed:
                print(f"[PUSH_CLAIMED] sending push for message_id={message_id}")
                send_push_notification(
                    partner.fcm_token,
                    title="New message 💬",
                    body=text[:50],
                    extra_data={"message_id": message_id},
                )
            else:
                print(f"[PUSH_SKIPPED] already claimed for message_id={message_id}")
        except Exception as e:
            print(f"Text push error: {e}")

    @database_sync_to_async
    def save_message(self, text, sender_role, reply_to=None, client_temp_id=None):
        from chat.models import Message

        # Idempotency for reconnect/retry: if the same client_temp_id was already
        # persisted for this sender+chat, reuse it so we don't double-notify.
        if client_temp_id:
            existing = Message.objects(
                couple_id=self.couple_id,
                user_id=self.user_id,
                sender="user",
                mode="calm",
                client_temp_id=client_temp_id,
            ).first()
            if existing:
                return existing

        reply_kwargs = {}
        if isinstance(reply_to, dict):
            reply_id = str(reply_to.get("id") or reply_to.get("messageId") or "").strip()
            reply_text = str(reply_to.get("text") or "").strip()
            reply_sender = str(reply_to.get("sender_name") or "").strip()
            if reply_id and reply_text:
                reply_kwargs = {
                    "reply_to_message_id": reply_id,
                    "reply_to_id": reply_id,
                    "reply_to_text": reply_text[:240],
                    "reply_to_sender_name": reply_sender[:60],
                }

        msg = Message(
            couple_id   = self.couple_id,
            user_id     = self.user_id,
            sender      = "user",
            sender_role = sender_role,
            text        = text,
            mode        = "calm",
            client_temp_id = client_temp_id,
            **reply_kwargs,
        )
        msg.save()
        return msg
