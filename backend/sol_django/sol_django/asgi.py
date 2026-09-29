"""
ASGI config for SOL AI project.
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sol_django_dir = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(sol_django_dir) not in sys.path:
    sys.path.insert(0, str(sol_django_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sol_django.settings')

from django.core.asgi import get_asgi_application
application = get_asgi_application()
