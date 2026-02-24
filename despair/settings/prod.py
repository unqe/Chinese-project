"""
Production settings for Heroku deployment.
All secrets are loaded from Heroku config vars (environment variables).
"""

import os
from .base import *
from decouple import config
import dj_database_url

DEBUG = False

ALLOWED_HOSTS = [
    ".herokuapp.com",
    "despair.cc",
    "www.despair.cc",
    "localhost",
    "127.0.0.1",
]

# Database from Heroku config var DATABASE_URL
DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

# Security hardening for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Email — console for now (can swap for SendGrid etc later)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
