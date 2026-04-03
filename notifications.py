
import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
import uuid


def _init_firebase():
    if firebase_admin._apps:
        return True

    creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

    cred = None
    try:
        if creds_json:
            print("Initializing Firebase from JSON in env")
            cred = credentials.Certificate(json.loads(creds_json))
        elif creds_path:
            # Prefer absolute path when possible
            if not os.path.isabs(creds_path):
                creds_path = os.path.join(os.getcwd(), creds_path)
            if not os.path.exists(creds_path):
                print(f"Firebase credentials file not found at {creds_path}")
            else:
                print(f"Initializing Firebase from path: {creds_path}")
                cred = credentials.Certificate(creds_path)
        else:
            print("No Firebase credentials provided (FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH)")

        if cred:
            firebase_admin.initialize_app(cred)
            print("Firebase admin initialized")
            return True
    except Exception as e:
        print(f"Failed to initialize Firebase admin: {e}")

    return False




def send_push_notification(fcm_token: str, title: str, body: str, extra_data: dict = None):
    # Lazy init: retry Firebase setup on every call if not yet initialized.
    # This avoids the race where this module is imported before load_dotenv().
    if not firebase_admin._apps:
        _init_firebase()
    if not firebase_admin._apps:
        print("Firebase not initialized after retry — skipping notification")
        return None
    try:
        frontend_url = os.getenv("FRONTEND_URL", "https://two-hearts-chat.vercel.app").rstrip("/")
        chat_url = f"{frontend_url}/#/chat"
        notification_id = str((extra_data or {}).get("message_id") or uuid.uuid4())

        # Data-only payload for web prevents browser + service worker double-display.
        data = {
            "url": chat_url,
            "title": str(title or "New message"),
            "body": str(body or ""),
            "notification_id": notification_id,
        }
        if extra_data:
            data.update({str(k): str(v) for k, v in extra_data.items()})

        message = messaging.Message(
            data=data,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    sound="default",
                    click_action="FLUTTER_NOTIFICATION_CLICK",
                ),
            ),
            webpush=messaging.WebpushConfig(
                headers={
                    # Collapse retries for same logical notification.
                    "Topic": notification_id,
                },
                fcm_options=messaging.WebpushFCMOptions(
                    link=chat_url
                ) if frontend_url.startswith("https://") else None,
            ),
            token=fcm_token,
        )
        response = messaging.send(message)
        print(f"Notification sent: {response}")
        return response
    except Exception as e:
        print(f"Notification failed: {e}")
        return None
