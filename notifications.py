

import firebase_admin
from firebase_admin import credentials, messaging
import os
import json


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


def send_push_notification(fcm_token: str, title: str, body: str):
    if not firebase_admin._apps:
        print("Firebase not initialized — skipping notification")
        return None
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
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
                    icon=f"{os.getenv('FRONTEND_URL', 'https://two-hearts-chat.vercel.app')}/icon-192.png",
                ),
                # Only include a link if a secure FRONTEND_URL is provided
                **({
                    'fcm_options': messaging.WebpushFCMOptions(link=frontend)
                } if (frontend := os.getenv('FRONTEND_URL', '').strip()).lower().startswith('https://') else {}),
            ),
            token=fcm_token,
        )
        response = messaging.send(message)
        print(f"Notification sent: {response}")
        return response
    except Exception as e:
        print(f"Notification failed: {e}")
        return None
