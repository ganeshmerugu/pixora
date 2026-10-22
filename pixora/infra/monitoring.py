"""Error monitoring (Sentry) + structured logging (JSON).

Sentry: Set PIXORA_SENTRY_DSN to enable.
Logging: Always active — structured JSON for cloud ingestion.
"""
from __future__ import annotations
import logging
import sys
from typing import Any


def init_sentry():
    from pixora.config.settings import settings
    if not settings.sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=settings.deployment_mode,
        )
        logging.getLogger(__name__).info("Sentry initialized")
    except ImportError:
        logging.getLogger(__name__).debug("sentry-sdk not installed, skipping")


def init_logging():
    from pixora.config.settings import settings

    try:
        from pythonjsonlogger import jsonlogger

        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
        handler.setFormatter(formatter)

        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    except ImportError:
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper(), logging.INFO),
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
        )
