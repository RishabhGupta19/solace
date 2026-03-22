import firebase_admin
from firebase_admin import credentials, messaging
import os

# Initialize Firebase only once
if not firebase_admin._apps:
    cred = credentials.Certificate(
        os.path.join(os.path.dirname(__file__), "firebase-credentials.json")
    )
    firebase_admin.initialize_app(cred)


def send_push_notification(fcm_token: str, title: str, body: str):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=title,
                    body=body,
                    icon="/icon-192.png",
                ),
                fcm_options=messaging.WebpushFCMOptions(
                    link="/"
                )
            ),
            token=fcm_token,
        )
        response = messaging.send(message)
        print(f"Notification sent: {response}")
    except Exception as e:
        print(f"Notification failed: {e}")