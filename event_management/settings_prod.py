"""
Production settings for EventEase.
"""

from decouple import config

from .settings import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
