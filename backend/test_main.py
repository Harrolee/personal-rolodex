import io
import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Personal Rolodex Backend is running."}

def test_process_audio_and_task_status():
    # Send a dummy audio file to process_audio
    dummy_audio = io.BytesIO(b"dummy audio data")
    response = client.post(
        "/process_audio/",
        files={"file": ("test.wav", dummy_audio, "audio/wav")}
    )
    assert response.status_code == 200
    assert "task_id" in response.json()
    task_id = response.json()["task_id"]

    # Poll for task status (simulate async completion)
    for _ in range(10):
        status_resp = client.get(f"/task_status/{task_id}")
        assert status_resp.status_code == 200
        status = status_resp.json()["status"]
        if status == "SUCCESS":
            result = status_resp.json()["result"]
            assert result["status"] == "success"
            assert "transcript" in result
            break
        elif status == "FAILURE":
            assert False, f"Task failed: {status_resp.json()}"
        time.sleep(0.5)
    else:
        assert False, "Task did not complete in time"
