# nfl_pickems/asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "nfl_pickems.settings"),
)

application = get_asgi_application()
