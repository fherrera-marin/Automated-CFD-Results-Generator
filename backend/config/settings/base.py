from pathlib import Path

import environ

# backend/config/settings/base.py -> backend/config/settings -> backend/config -> backend -> <repo root>
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BACKEND_DIR.parent

env = environ.Env()
environ.Env.read_env(str(REPO_ROOT / ".env"))

SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="dev-insecure-secret-key")
DEBUG = False
ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.runs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL", default=f"sqlite:///{BACKEND_DIR / 'db.sqlite3'}"
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# --- Celery / Redis -----------------------------------------------------
REDIS_URL = env.str("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
# Celery's own built-in default queue is named "celery", not "default" --
# without this, every task not explicitly listed in task_routes (i.e.
# everything except the three *_case tasks) would be queued under "celery",
# which the documented `-Q default,cfd` worker command never listens on.
CELERY_TASK_DEFAULT_QUEUE = "default"

# --- CFD pipeline configuration (see docs/operations.md) ----------------
# Base directory under which every Run gets its own `run_<id>/` simulation
# folder. Defaults to <repo>/data/runs so the existing data/ dir (already
# gitignored) doubles as the simulations workspace.
SIM_BASE_DIR = Path(env.str("SIM_BASE_DIR", default=str(REPO_ROOT / "data" / "runs")))

# Template ("origin") case directory used when a Run doesn't specify its own.
# No safe default: this is machine-specific, so a missing value must be an
# explicit per-Run error rather than a silently wrong path.
DEFAULT_ORIGIN_DIR = env.str("SIM_ORIGIN_DIR", default="")

# Script/batch file that activates the BlueCFD OpenFOAM environment (puts
# blockMesh/snappyHexMesh/simpleFoam/... on PATH) for the current machine.
# Required: there is no portable default, see docs/operations.md.
OPENFOAM_ENV_SCRIPT = env.str("OPENFOAM_ENV_SCRIPT", default="")

FOAMTOVTK_BIN = env.str("FOAMTOVTK_BIN", default="foamtoVTK")

# pvbatch executable from the ParaView installation. Required, no portable
# default.
PVBATCH_BIN = env.str("PVBATCH_BIN", default="")

PARAVIEW_EXPORT_MACRO = Path(
    env.str(
        "PARAVIEW_EXPORT_MACRO",
        default=str(REPO_ROOT / "scripts" / "paraview_export_macro.py"),
    )
)
