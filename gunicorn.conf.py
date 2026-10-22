"""Gunicorn configuration for Cloud Run production deployment."""
import multiprocessing
import os

# Cloud Run sets PORT env var
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Cloud Run gives 1 vCPU by default; 2-4 workers is optimal
workers = int(os.environ.get("WEB_CONCURRENCY", min(2 * multiprocessing.cpu_count() + 1, 4)))
worker_class = "uvicorn.workers.UvicornWorker"
worker_tmp_dir = "/dev/shm"

# Cloud Run sends SIGTERM, then waits up to 10s before SIGKILL
timeout = 120
graceful_timeout = 30
keep_alive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("PIXORA_LOG_LEVEL", "info").lower()

# Preload app for faster cold starts (important on Cloud Run)
preload_app = True

# Max requests before worker restart (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50
