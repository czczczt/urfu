"""
Project package init.

Celery is optional for running Django in dev/test environments.
"""

try:
    from .celery import app as celery_app

    __all__ = ("celery_app",)
except ModuleNotFoundError:
    # If `celery` dependency isn't installed, allow Django commands to run.
    __all__ = ()