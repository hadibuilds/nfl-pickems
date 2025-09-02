# nfl_pickems/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

# Always point at the unified settings module.
# The settings file itself reads DJANGO_ENV to decide dev/prod behavior.
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "nfl_pickems.settings"),
)

application = get_wsgi_application()
