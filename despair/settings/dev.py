"""
Development settings — uses local .env file for secrets.
"""

from .base import *
from decouple import config
import dj_database_url

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Use the Neon PostgreSQL database from .env
DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

# Show emails in the console during development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
