"""
Django settings for SOL AI project.

Stateless REST API backend for SOL AI (Tamil Lexical & Morphological Intelligence Engine).
Preserves existing HTTP API contract and environment configuration.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent.parent

# Ensure project root and sol_django directory are on sys.path
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load .env configuration from repo root
env_path = REPO_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Security Settings
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-sol-ai-dev-secret-key-change-in-production"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

allowed_hosts_raw = os.environ.get("DJANGO_ALLOWED_HOSTS", "*")
if allowed_hosts_raw == "*":
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_raw.split(",") if h.strip()]

# Application definition
INSTALLED_APPS = [
    "corsheaders",
    "api.apps.ApiConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "sol_django.urls"

TEMPLATES = []

WSGI_APPLICATION = "sol_django.wsgi.application"
ASGI_APPLICATION = "sol_django.asgi.application"

# No Django ORM database needed for linguistic intelligence.
# All linguistic resources are accessed directly via specialized domain adapters.
DATABASES = {}

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Disable automatic slash appending to prevent unwanted redirects on POST requests
APPEND_SLASH = False

# CORS Configuration
# Enables browser access (Next.js at localhost:3000) and Chrome Extension origins
CORS_ALLOW_ALL_ORIGINS = os.environ.get("CORS_ALLOW_ALL", "True").lower() in ("true", "1", "yes")
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^chrome-extension://.*$",
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
]
CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "OPTIONS",
    "HEAD",
]
CORS_ALLOW_HEADERS = [
    "content-type",
    "authorization",
]

# SOL AI LLM / Provider Environment Configuration
SOL_LLM_PROVIDER = os.environ.get("SOL_LLM_PROVIDER", "mock")
SOL_GEMINI_MODEL = os.environ.get("SOL_GEMINI_MODEL", "gemini-3.6-flash")
SOL_GROQ_MODEL = os.environ.get("SOL_GROQ_MODEL", "qwen/qwen3.8-27b")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
