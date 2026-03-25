

import firebase_admin
from firebase_admin import credentials, messaging
import os
import json

if not firebase_admin._apps:
    creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

    if creds_json:
        cred = credentials.Certificate(json.loads(creds_json))
    elif creds_path:
        cred = credentials.Certificate(creds_path)
    else:
        cred = None

    if cred:
        firebase_admin.initialize_app(cred)


def send_push_notification(fcm_token: str, title: str, body: str):
    if not firebase_admin._apps:
        print("Firebase not initialized — skipping notification")
        return
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
                    icon="/icon-192.png",
                ),
                fcm_options=messaging.WebpushFCMOptions(link="/")
            ),
            token=fcm_token,
        )
        response = messaging.send(message)
        print(f"Notification sent: {response}")
    except Exception as e:
        print(f"Notification failed: {e}")
