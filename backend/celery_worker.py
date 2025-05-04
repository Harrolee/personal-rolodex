from app.celery_config import celery_app

# Import tasks here to ensure they are registered with the worker
# from app.services.audio_tasks import process_audio_task

if __name__ == "__main__":
    celery_app.start()
