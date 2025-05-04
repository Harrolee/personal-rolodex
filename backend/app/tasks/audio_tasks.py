from app.celery_config import celery_app

@celery_app.task(bind=True)
def process_audio_task(self, audio_bytes: bytes):
    # TODO: Call transcription and extraction services here
    # For now, just return a stub result
    return {
        "status": "success",
        "message": "Audio processed (stub)",
        "transcript": "This is a stub transcript.",
        "kg_update": {}
    }
