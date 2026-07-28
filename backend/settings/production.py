from .base import *
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(os.path.join(PROJECT_DIR, "settings", ".env"))

DEBUG = False
SECRET_KEY = os.environ.get("SECRET_KEY")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h.strip()]

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS if host != "*"
] + [
    f"http://{host}" for host in ALLOWED_HOSTS if host != "*"
]

# Performance: Logging (Agar error terlihat di 'docker logs')
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

WAGTAILADMIN_BASE_URL = os.environ.get(
    "WAGTAILADMIN_BASE_URL",
    "https://ks3.claverio.com",
)


# Performance: Compression
MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",  # Enable compression
] + MIDDLEWARE

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL") #HTTPS

# Performance: S3 Cache Control
# Static files (hashed via ManifestStaticStorage) = 1 year immutable
# Media files (non-hashed) = 1 week with revalidation
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=31536000, immutable, public",
}

STATICFILES_DIRS = []

STATIC_ROOT = os.path.join(BASE_DIR, "static")

# Static and Media URLs
STATIC_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/static/"
MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/media/"

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "location": "media",
            "default_acl": "public-read",
            "object_parameters": {
                "CacheControl": "max-age=604800, public, must-revalidate",
            },
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "location": "static",
            "default_acl": "public-read",
            "object_parameters": {
                "CacheControl": "max-age=31536000, immutable, public",
            },
        },
    },
}


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
    }
}


try:
    from .local import *
except ImportError:
    pass
