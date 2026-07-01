import os
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module=r"pyannote\.audio\.core\.io")
warnings.filterwarnings("ignore", message=".*[Tt]orchcodec.*", category=UserWarning)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from celery import Celery

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late = True