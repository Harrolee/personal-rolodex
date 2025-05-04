from celery import Celery

celery_app = Celery(
    'personal_rolodex',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)
