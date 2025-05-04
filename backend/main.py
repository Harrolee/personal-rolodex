from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from app.tasks.audio_tasks import process_audio_task
from celery.result import AsyncResult

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Personal Rolodex Backend is running."}

@app.post("/process_audio/")
def process_audio(file: UploadFile = File(...)):
    audio_bytes = file.file.read()
    task = process_audio_task.apply_async(args=[audio_bytes])
    return {"task_id": task.id}

@app.get("/task_status/{task_id}")
def get_task_status(task_id: str):
    result = AsyncResult(task_id)
    if result.state == "PENDING":
        return {"status": "PENDING"}
    elif result.state == "FAILURE":
        return {"status": "FAILURE", "error": str(result.info)}
    elif result.state == "SUCCESS":
        return {"status": "SUCCESS", "result": result.result}
    else:
        return {"status": result.state}
