from celery import Celery
import os

# Check if we're in testing mode
testing = os.environ.get('TESTING', 'false').lower() == 'true'

if testing:
    # For testing, use an in-memory broker/backend
    celery_app = Celery(
        'personal_rolodex',
        broker='memory://',
        backend='cache+memory://'
    )
else:
    celery_app = Celery(
        'personal_rolodex',
        broker='redis://localhost:6379/0',
        backend='redis://localhost:6379/0'
    )

# If testing, make all tasks execute synchronously
if testing:
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
