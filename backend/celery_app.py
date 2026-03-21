from celery import Celery

celery = Celery(
    "gv_bot",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

# ВАЖНО: регистрация tasks
import tasks
