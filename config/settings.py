import os
from pathlib import Path
from dotenv import load_dotenv
import mongoengine
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "changeme-in-production")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("EMAIL_HOST_USER", "")
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "channels",
    "auth_app",
    "couples",
    "assessment",
    "chat",
    "goals",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
APPEND_SLASH = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── MongoDB Atlas ──────────────────────────────────────────────────────────────

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/ustwo")
mongoengine.connect(host=MONGODB_URI, alias="default")
DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("auth_app.authentication.MongoJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "UNAUTHENTICATED_USER": None,
}

# ── JWT ───────────────────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
JWT_ACCESS_EXPIRY_DAYS = 1
JWT_REFRESH_EXPIRY_DAYS = 30

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ── Groq ──────────────────────────────────────────────────────────────────────
GROQ_KEY = os.getenv("GROQ_KEY", "")

# ── Channels ──────────────────────────────────────────────────────────────────
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# ── Static ────────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
