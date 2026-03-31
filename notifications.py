
import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
from urllib.parse import urlparse


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


_init_firebase()


def send_push_notification(fcm_token: str, title: str, body: str, extra_data: dict = None):
    if not firebase_admin._apps:
        print("Firebase not initialized — skipping notification")
        return None
    try:
        # Build webpush config with safe validation of FRONTEND_URL
        frontend = os.getenv('FRONTEND_URL', '').strip()
        parsed = urlparse(frontend) if frontend else None
        icon_url = '/icon-192.png'
        webpush_kwargs = {}

        if parsed and parsed.scheme and parsed.netloc:
            # Use full icon URL only when frontend is a valid absolute URL
            icon_url = f"{frontend.rstrip('/')}/icon-192.png"
            # Only include fcm_options.link when it's HTTPS
            if parsed.scheme.lower() == 'https':
                webpush_kwargs['fcm_options'] = messaging.WebpushFCMOptions(link=frontend)
                print(f"Using secure FRONTEND_URL for webpush link: {frontend}")
            else:
                print(f"FRONTEND_URL is not HTTPS, omitting webpush link: {frontend}")
        else:
            if frontend:
                print(f"FRONTEND_URL looks invalid, omitting webpush link: {frontend}")

        # Use data-only payload for web so the service worker controls display.
        # Keep native android/apns notifications for mobile apps.
        data_payload = {"title": title, "body": body}
        if extra_data:
            # merge additional values like message_id
            data_payload.update({k: str(v) for k, v in (extra_data or {}).items()})

        message = messaging.Message(
            data=data_payload,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    sound="default",
                ),
            ),
            apns=messaging.APNSConfig(
                headers={"apns-priority": "10"},
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(title=title, body=body),
                        sound="default",
                    )
                ),
            ),
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=title,
                    body=body,
                    icon=icon_url,
                ),
                **webpush_kwargs,
            ),
            token=fcm_token,
        )
        response = messaging.send(message)
        print(f"Notification sent: {response}")
        return response
    except Exception as e:
        print(f"Notification failed: {e}")
        return None
