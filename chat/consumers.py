import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from urllib.parse import parse_qs
from couples.models import CoupleLink
from auth_app.models import User
from notifications import send_push_notification


class CalmChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.couple_id = self.scope["url_route"]["kwargs"]["couple_id"]
        self.room_group_name = f"calm_{self.couple_id}"

        # Fetch and cache user role at connection time from JWT token
        self.user_role = await self.get_role_from_token()

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get("type") == "seen":
            await self.mark_messages_seen(data.get("message_ids", []))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "messages_seen",
                    "message_ids": data.get("message_ids", []),
                    "seen_by": self.user_id,
                }
            )
            return
        if data.get("type") == "seen":
            await self.mark_messages_seen(data.get("message_ids", []))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "messages_seen",
                    "message_ids": data.get("message_ids", []),
                    "seen_by": self.user_id,
                }
            )
            return

        # Handle typing indicator
        if data.get("type") == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "typing_indicator", "channel": self.channel_name}
            )
            return

        text = data.get("text", "").strip()
        sender_name = data.get("sender_name", "")

        if not text:
            return

        # Always use role from connection token, not from message payload
        sender_role = self.user_role or data.get("sender_role", "")

        message = await self.save_message(text, sender_role)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "id": str(message.id),
                "text": text,
                "sender": "user",
                "sender_role": sender_role,
                "sender_id": self.user_id,
                "sender_name": sender_name,
                "timestamp": message.timestamp.isoformat(),
            }
        )

    async def messages_seen(self, event):
        await self.send(text_data=json.dumps({
            "type": "seen",
            "message_ids": event["message_ids"],
            "seen_by": event["seen_by"],
        }))

    @database_sync_to_async
    def mark_messages_seen(self, message_ids):
        from chat.models import Message
        from datetime import datetime
        Message.objects(
            id__in=message_ids,
            user_id__ne=self.user_id  # only mark partner's messages
        ).update(seen=True, seen_at=datetime.utcnow())
    async def messages_seen(self, event):
        await self.send(text_data=json.dumps({
            "type": "seen",
            "message_ids": event["message_ids"],
            "seen_by": event["seen_by"],
        }))

    @database_sync_to_async
    def mark_messages_seen(self, message_ids):
        from chat.models import Message
        from datetime import datetime
        Message.objects(
            id__in=message_ids,
            user_id__ne=self.user_id  # only mark partner's messages
        ).update(seen=True, seen_at=datetime.utcnow())
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "id": event["id"],
            "text": event["text"],
            "sender": event["sender"],
            "sender_role": event["sender_role"],
            "sender_id": event.get("sender_id", ""),
            "sender_name": event["sender_name"],
            "timestamp": event["timestamp"],
        }))
    
    async def voice(self, event):
        """Handle voice messages sent via channel layer group_send with type 'voice'.

        This prevents Channels from raising "No handler for message type voice"
        if other parts of the system publish voice events.
        """
        await self.send(text_data=json.dumps({
            "type": "voice",
            "id": event.get("id", ""),
            "url": event.get("url", ""),
            "sender_id": event.get("sender_id", ""),
            "sender_name": event.get("sender_name", ""),
            "timestamp": event.get("timestamp", ""),
        }))
    async def connect(self):
        self.couple_id = self.scope["url_route"]["kwargs"]["couple_id"]
        self.room_group_name = f"calm_{self.couple_id}"
        self.user_role = await self.get_role_from_token()
        self.user_id = await self.get_user_id_from_token()  # ← add this
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
    async def typing_indicator(self, event):
        # Send typing event to everyone except the sender
        if event.get("channel") != self.channel_name:
            await self.send(text_data=json.dumps({"type": "typing"}))
    @database_sync_to_async
    def get_user_id_from_token(self):
        try:
            query_string = self.scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            token = params.get("token", [None])[0]
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
            token = params.get("token", [None])[0]
            if not token:
                return ""
            from auth_app.utils import decode_token
            from auth_app.models import User
            payload = decode_token(token)
            user = User.objects.get(id=payload["user_id"])
            return user.role or ""
        except Exception:
            return ""

    @database_sync_to_async
    def save_message(self, text, sender_role):
        from chat.models import Message
        msg = Message(
            couple_id=self.couple_id,
            user_id=self.user_id,
            sender="user",
            sender_role=sender_role,
            text=text,
            mode="calm",
        )
        msg.save()
        try:
            link = CoupleLink.objects.get(id=self.couple_id)
            partner_id = link.partner_id if link.creator_id == self.user_id else link.creator_id
            if partner_id:
                partner = User.objects.get(id=partner_id)
                if partner.fcm_token:
                    send_push_notification(
                        partner.fcm_token,
                        title="New message 💬",
                        body=text[:50],
                    )
        except Exception as e:
            print(f"Notification error: {e}")
        return msg
