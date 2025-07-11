from celery import Celery
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Broker & backend (can come from your .env)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")

print(f"🔧 Celery Configuration:")
print(f"   - Broker URL: {CELERY_BROKER_URL}")
print(f"   - Result Backend: {CELERY_RESULT_BACKEND}")

celery_app = Celery(
    "socratic",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["tasks"]  # Updated to include tasks module instead of main
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Fix for macOS fork safety issues
    worker_pool="solo",  # Use solo pool instead of prefork on macOS
    worker_concurrency=1,  # Limit concurrency to prevent connection issues
    # Database connection settings
    worker_prefetch_multiplier=1,  # Disable prefetching to prevent connection sharing
    task_acks_late=True,  # Only acknowledge task completion after it's done
    worker_max_tasks_per_child=50,  # Restart workers periodically to clear connections
    # Connection management
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    # Use default queue for all tasks to simplify
    task_default_queue='default',
    # Memory and resource management
    worker_disable_rate_limits=True,
    task_soft_time_limit=1800,  # 30 minutes soft limit
    task_time_limit=2400,      # 40 minutes hard limit
)
