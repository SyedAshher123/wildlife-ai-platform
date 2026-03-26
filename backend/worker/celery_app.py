"""Celery application configuration for async ML processing.

Celery is optional for local development. If it's not installed, we provide a
minimal stub so worker task modules can still be imported and local fallback
processing can run.
"""

from typing import Any, Callable

try:
    from celery import Celery  # type: ignore

    celery_app = Celery(
        "wildlife_worker",
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/1",
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_routes={
            "backend.worker.tasks.process_image_task": {"queue": "ml"},
            "backend.worker.tasks.process_batch_task": {"queue": "ml"},
        },
    )

    celery_app.autodiscover_tasks(["backend.worker"])
except ModuleNotFoundError:
    class _DummyConf:
        def update(self, **_: Any) -> None:
            return

    class _DummyCelery:
        conf = _DummyConf()

        def autodiscover_tasks(self, *_: Any, **__: Any) -> None:
            return

        def task(self, *_: Any, **__: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                return fn
            return _decorator

    celery_app = _DummyCelery()
