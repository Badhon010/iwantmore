"""
Django settings for iwantmore project.
"""

from pathlib import Path

from decouple import config
import pymysql
import dj_database_url
from import_export.formats.base_formats import XLSX, CSV, JSON


pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def csv_setting(name, default=""):
    value = config(name, default=default)
    return [item.strip() for item in value.split(",") if item.strip()]


def sanitize_setting_values(values):
    cleaned = []
    for value in values:
        item = value.split("#", 1)[0].strip()
        if item:
            cleaned.append(item)
    return cleaned


SECRET_KEY = config("SECRET_KEY", default="development-secret-key-not-for-production")
PRODUCTION = config("PRODUCTION", cast=bool, default=False)
DEBUG = config("DEBUG", cast=bool, default=not PRODUCTION)

SITE_ID = config("SITE_ID", cast=int, default=1)
GOOGLE_TAG_MANAGER_ID = config("GOOGLE_TAG_MANAGER_ID", default="")
ALLOWED_HOSTS = sanitize_setting_values(
    csv_setting("ALLOWED_HOSTS", default="127.0.0.1,localhost")
)
if not PRODUCTION:
    ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = sanitize_setting_values(csv_setting("CSRF_TRUSTED_ORIGINS"))

EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", cast=int, default=587)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool, default=True)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER or "no-reply@example.com"
)
ADMIN_EMAIL = config("ADMIN_EMAIL", default=DEFAULT_FROM_EMAIL)
ADMINS = [("Store Admin", ADMIN_EMAIL)] if ADMIN_EMAIL else []

if PRODUCTION and SECRET_KEY == "development-secret-key-not-for-production":
    raise ValueError("SECRET_KEY must be set in production.")

if PRODUCTION and not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be configured in production.")


INSTALLED_APPS = [
    "unfold.apps.BasicAppConfig",
    "unfold.contrib.import_export",
    "iwantmore.admin_config.IwantmoreAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_ckeditor_5",
    "import_export",
    "auditlog",
    "iwm",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "iwantmore.urls"

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
                "iwm.context_processors.google_tag_manager",
            ],
        },
    },
]

WSGI_APPLICATION = "iwantmore.wsgi.application"


DATABASE_URL = config("DATABASE_URL", default="")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=60,
        )
    }
else:
    # SAFE LOCAL FALLBACK ONLY
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = config("TIME_ZONE", default="Asia/Dhaka")
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if PRODUCTION
        else "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
WHITENOISE_MANIFEST_STRICT = False
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
LOGIN_URL = "/login/"

SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", cast=bool, default=PRODUCTION)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", cast=bool, default=PRODUCTION)
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", cast=bool, default=PRODUCTION)
SECURE_HSTS_SECONDS = config(
    "SECURE_HSTS_SECONDS", cast=int, default=31536000 if PRODUCTION else 0
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", cast=bool, default=PRODUCTION
)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", cast=bool, default=PRODUCTION)
USE_X_FORWARDED_HOST = config("USE_X_FORWARDED_HOST", cast=bool, default=PRODUCTION)
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if USE_X_FORWARDED_HOST else None
)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "iwm-default-cache",
        "TIMEOUT": 300,
    }
}


AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET", default="")
FACEBOOK_CLIENT_ID = config("FACEBOOK_CLIENT_ID", default="")
FACEBOOK_CLIENT_SECRET = config("FACEBOOK_CLIENT_SECRET", default="")

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    },
    "facebook": {
        "METHOD": "oauth2",
        "SCOPE": ["email", "public_profile"],
    },
}

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS["google"]["APP"] = {
        "client_id": GOOGLE_CLIENT_ID,
        "secret": GOOGLE_CLIENT_SECRET,
    }

if FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS["facebook"]["APP"] = {
        "client_id": FACEBOOK_CLIENT_ID,
        "secret": FACEBOOK_CLIENT_SECRET,
    }

SOCIALACCOUNT_LOGIN_ON_GET = False

ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory" if PRODUCTION else "optional"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading",
            "|",
            "bold",
            "italic",
            "underline",
            "strikethrough",
            "|",
            "link",
            "insertImage",
            "|",
            "bulletedList",
            "numberedList",
            "|",
            "blockQuote",
            "|",
            "undo",
            "redo",
            "|",
            "fontSize",
            "fontFamily",
            "fontColor",
            "fontBackgroundColor",
            "|",
            "alignment",
            "|",
            "outdent",
            "indent",
            "|",
            "insertTable",
            "mediaEmbed",
            "|",
            "removeFormat",
        ],
        "image": {
            "toolbar": [
                "imageTextAlternative",
                "toggleImageCaption",
                "|",
                "imageStyle:inline",
                "imageStyle:block",
                "imageStyle:side",
                "|",
                "resizeImage",
                "cropImage",
            ]
        },
        "table": {
            "contentToolbar": [
                "tableColumn",
                "tableRow",
                "mergeTableCells",
                "tableProperties",
                "tableCellProperties",
            ]
        },
        "heading": {
            "options": [
                {
                    "model": "paragraph",
                    "title": "Paragraph",
                    "class": "ck-heading_paragraph",
                },
                {
                    "model": "heading1",
                    "view": "h1",
                    "title": "Heading 1",
                    "class": "ck-heading_heading1",
                },
                {
                    "model": "heading2",
                    "view": "h2",
                    "title": "Heading 2",
                    "class": "ck-heading_heading2",
                },
                {
                    "model": "heading3",
                    "view": "h3",
                    "title": "Heading 3",
                    "class": "ck-heading_heading3",
                },
            ]
        },
    }
}

CKEDITOR_5_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
CKEDITOR_5_UPLOAD_PATH = "ckeditor_uploads/"


AUDITLOG_INCLUDE_TRACKING_MODELS = (
    "iwm.Product",
    "iwm.Order",
    "iwm.NewsletterSubscriber",
    "iwm.Coupon",
)

IMPORT_EXPORT_USE_TRANSACTIONS = True
IMPORT_EXPORT_FORMATS = [XLSX, CSV, JSON]


def environment_callback(request):
    from django.conf import settings as _s

    if _s.DEBUG:
        return ["Development", "danger"]
    return ["Production", "success"]


UNFOLD = {
    "SITE_TITLE": "IWantMore",
    "SITE_HEADER": "IWantMore Admin",
    "SITE_SYMBOL": "shopping_bag",
    "SITE_URL": "/",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": "iwantmore.settings.environment_callback",
    "STYLES": [
        lambda request: "/static/css/admin_custom.css",
    ],
    "SCRIPTS": [
        lambda request: "/static/js/admin_custom.js",
    ],
    "LOGIN": {
        "image": lambda request: "/static/imgs/iwm.png",
    },
    "COLORS": {
        "primary": {
            "50": "255 242 245",
            "100": "255 226 233",
            "200": "255 196 210",
            "300": "255 162 182",
            "400": "255 127 163",
            "500": "255 111 145",
            "600": "235 79 114",
            "700": "204 46 80",
            "800": "166 32 62",
            "900": "131 22 47",
            "950": "77 10 26",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Dashboard",
                "separator": False,
                "items": [
                    {
                        "title": "Overview",
                        "icon": "dashboard",
                        "link": "/admin/",
                    },
                    {
                        "title": "Analytics",
                        "icon": "bar_chart",
                        "link": "/admin/analytics/",
                    },
                    {
                        "title": "Alerts",
                        "icon": "notifications_active",
                        "link": "/admin/alerts/",
                        "badge": "iwm.admin._unread_alerts_badge",
                    },
                ],
            },
            {
                "title": "Catalog",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Products",
                        "icon": "inventory_2",
                        "link": "/admin/iwm/product/",
                        "badge": "iwm.admin._low_stock_badge",
                    },
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": "/admin/iwm/category/",
                    },
                    {
                        "title": "Subcategories",
                        "icon": "folder_open",
                        "link": "/admin/iwm/subcategory/",
                    },
                    {
                        "title": "Homepage Sliders",
                        "icon": "view_carousel",
                        "link": "/admin/iwm/slider/",
                    },
                    {
                        "title": "Colors",
                        "icon": "palette",
                        "link": "/admin/iwm/color/",
                    },
                    {
                        "title": "Sizes",
                        "icon": "straighten",
                        "link": "/admin/iwm/size/",
                    },
                    {
                        "title": "Tags",
                        "icon": "sell",
                        "link": "/admin/iwm/tag/",
                    },
                ],
            },
            {
                "title": "Orders",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "All Orders",
                        "icon": "shopping_cart",
                        "link": "/admin/iwm/order/",
                    },
                    {
                        "title": "Order Items",
                        "icon": "receipt_long",
                        "link": "/admin/iwm/orderitem/",
                    },
                    {
                        "title": "Addresses",
                        "icon": "location_on",
                        "link": "/admin/iwm/address/",
                    },
                ],
            },
            {
                "title": "Customers & Marketing",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "people",
                        "link": "/admin/auth/user/",
                    },
                    {
                        "title": "Newsletter",
                        "icon": "email",
                        "link": "/admin/iwm/newslettersubscriber/",
                    },
                    {
                        "title": "Coupons",
                        "icon": "confirmation_number",
                        "link": "/admin/iwm/coupon/",
                    },
                    {
                        "title": "Promo Banners",
                        "icon": "campaign",
                        "link": "/admin/iwm/promobanner/",
                    },
                ],
            },
            {
                "title": "Content",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Reviews",
                        "icon": "star_rate",
                        "link": "/admin/iwm/review/",
                    },
                    {
                        "title": "Feature Reasons",
                        "icon": "auto_awesome",
                        "link": "/admin/iwm/featurereason/",
                    },
                    {
                        "title": "Product Images",
                        "icon": "photo_library",
                        "link": "/admin/iwm/productcolorimage/",
                    },
                ],
            },
            {
                "title": "System",
                "separator": True,
                "collapsible": True,
                "items": [
                    # AQ5: Removed "Admin Alerts" duplicate — kept only "Alerts" under Dashboard
                    {
                        "title": "Groups",
                        "icon": "shield",
                        "link": "/admin/auth/group/",
                    },
                    {
                        "title": "Clear Cache",
                        "icon": "delete_sweep",
                        "link": "/admin/clear-cache/",
                        "badge": lambda request: "⚠️",
                    },
                ],
            },
        ],
    },
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "ignore_devserver_tls_noise": {
            "()": "iwm.logging_filters.IgnoreDevserverTLSNoise",
        },
    },
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(name)s %(message)s",
        },
        "simple": {
            "format": "%(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "filters": ["ignore_devserver_tls_noise"],
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "django.log"),
            "formatter": "verbose",
            "filters": ["ignore_devserver_tls_noise"],
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "iwm": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


"""
DEVELOPER DOCUMENTATION: ENVIRONMENT VARIABLES & SETUP
-------------------------------------------------------------------------
This project relies on environment variables for sensitive configurations 
(Database credentials, Secret Keys, API tokens). 

The actual '.env' file containing production/local secrets is excluded 
from the Git repository via '.gitignore' to protect credentials.

HOW TO SET UP LOCAL ENVIRONMENT VARIABLES:
1. Locate the '.env.example' file in the root directory.
2. Duplicate or rename a copy of that file to exactly '.env'.
3. Open '.env' and replace the placeholder values (e.g., your_gemini_api_key) 
   with your actual local credentials.
4. Ensure your local '.env' file is NEVER staged or committed to Git.

Dependencies used to parse these variables:
- django-environ (or python-dotenv)
-------------------------------------------------------------------------

# ==============================================================================
# ENVIRONMENT VARIABLES TEMPLATE (.env.example)
# Duplicate this file, rename it to '.env', and fill in your local credentials.
# DO NOT commit the actual '.env' file to version control.
# ==============================================================================

# Database Configuration
DB_NAME=your_database_name
DB_USER=root
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=3306

# Django Security & Core Settings
SECRET_KEY=django-insecure-generate-a-unique-secret-key-for-production
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
PRODUCTION=False
SECURE_SSL_REDIRECT=False

# Email Configuration (SMTP)
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_app_password

# Google OAuth Credentials
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Facebook OAuth Credentials
FACEBOOK_CLIENT_ID=your_facebook_app_id
FACEBOOK_CLIENT_SECRET=your_facebook_app_secret

# AI & Third-Party APIs
GEMINI_API_KEY=your_gemini_api_key

# Google Tag Manager
GOOGLE_TAG_MANAGER_ID =GTM-XXXXXXX
"""
