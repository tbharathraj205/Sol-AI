"""
Django AppConfig for SOL AI API.
"""

import os
from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        """
        Application ready hook.

        SOL AI uses a lazy process-local service registry (SOLServiceRegistry)
        to prevent unnecessary initialization overhead during tests, migrations,
        and administrative CLI commands.

        Eager pre-warming can optionally be enabled by setting SOL_PREWARM_ON_STARTUP=true.
        """
        if os.environ.get("SOL_PREWARM_ON_STARTUP", "").lower() in ("true", "1", "yes"):
            # Only pre-warm in the worker process (avoiding reload watcher parent process)
            if os.environ.get("RUN_MAIN") == "true" or not os.environ.get("DJANGO_AUTORELOAD"):
                from .services import SOLServiceRegistry
                print("Pre-warming SOL AI Retrieval Engine (eager mode)...")
                SOLServiceRegistry.get_instance().get_engine()
