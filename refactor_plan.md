# Refactor Plan: Streamlit + FastAPI + Celery

## Overview
This plan outlines the steps to refactor the current Streamlit-based application into a two-service architecture:
- **Backend:** FastAPI service (with Celery for async/background processing)
- **Frontend:** Streamlit app (communicates with backend via HTTP)

---

## 1. Backend (FastAPI + Celery)

### a. Project Setup
- Create a new FastAPI project (e.g., in a `backend/` directory).
- Install dependencies: `fastapi`, `uvicorn`, `celery`, `redis` (or `rabbitmq`), `pydantic`, etc.
- Set up Celery worker and broker (e.g., Redis).

### b. Move and Adapt Code
- Move all code from `src/` (models, services, persistence, kg_utils, etc.) into the backend project.
- Refactor as needed to remove Streamlit dependencies and make functions/classes importable by FastAPI and Celery.

### c. API Endpoints
- `/process_audio/` (POST): Accepts audio file, enqueues Celery task, returns task ID.
- `/task_status/{task_id}` (GET): Returns status/result of the processing task.
- `/knowledge_graph/` (GET/POST): For loading/saving the knowledge graph (optional, if needed by FE).

### d. Celery Task
- Implement a Celery task that:
  - Receives audio bytes
  - Runs transcription, extraction, and KG update logic
  - Stores or returns results

---

## 2. Frontend (Streamlit)

### a. Remove Direct Backend Logic
- Remove all direct imports/use of `src/` code.
- Only communicate with backend via HTTP (using `requests` or `httpx`).

### b. Update `core_processing.py`
- Refactor to:
  - Send audio to `/process_audio/` endpoint
  - Poll `/task_status/{task_id}` for results
  - Display results in the UI

### c. Session State
- Use Streamlit session state to manage task status, results, and UI state.

---

## 3. Task Flow

1. User uploads/records audio in Streamlit.
2. Streamlit sends audio to FastAPI (`/process_audio/`).
3. FastAPI enqueues Celery task and returns a task ID.
4. Streamlit polls `/task_status/{task_id}` until complete.
5. When done, Streamlit fetches and displays the result.

---

## 4. Optional Enhancements
- Add authentication between FE and BE.
- Use WebSockets for real-time updates (optional).
- Add endpoints for querying/updating the knowledge graph from the FE.

---

## 5. Testing & Deployment
- Test end-to-end locally.
- Deploy backend and frontend as separate services (Docker recommended).
