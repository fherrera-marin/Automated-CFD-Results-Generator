from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False
CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[])
