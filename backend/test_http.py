import io
import time
import requests

# Base URL for the running FastAPI service
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the root health check endpoint."""
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    assert response.json() == {"message": "Personal Rolodex Backend is running."}

def test_process_audio_and_task_status():
    """Test the process_audio endpoint and task_status polling."""
    # Create a dummy audio file
    dummy_audio = io.BytesIO(b"dummy audio data")
    
    # Send it to the process_audio endpoint
    files = {"file": ("test.wav", dummy_audio, "audio/wav")}
    response = requests.post(f"{BASE_URL}/process_audio/", files=files)
    
    assert response.status_code == 200
    assert "task_id" in response.json()
    task_id = response.json()["task_id"]
    
    # Poll for task status
    max_retries = 10
    for _ in range(max_retries):
        status_resp = requests.get(f"{BASE_URL}/task_status/{task_id}")
        assert status_resp.status_code == 200
        status = status_resp.json()["status"]
        
        if status == "SUCCESS":
            result = status_resp.json()["result"]
            assert result["status"] == "success"
            assert "transcript" in result
            print(f"Task completed successfully: {result}")
            return
        elif status == "FAILURE":
            assert False, f"Task failed: {status_resp.json()}"
        
        print(f"Task status: {status} - waiting...")
        time.sleep(0.5)
    
    assert False, f"Task did not complete within {max_retries * 0.5} seconds"

if __name__ == "__main__":
    print("Running health check test...")
    test_health_check()
    print("Health check passed!\n")
    
    print("Running audio processing test...")
    test_process_audio_and_task_status()
    print("Audio processing test passed!") 