# Jazz Lick Lab — Backend

FastAPI + PostgreSQL + Redis/RQ scaffold for async MP3 processing jobs.

## Stack

| Layer   | Tech                        |
|---------|-----------------------------|
| API     | FastAPI + uvicorn            |
| DB      | PostgreSQL 16               |
| Queue   | Redis 7 + RQ                |
| Storage | Local filesystem (`./data/`) |

## Quick Start

### 1. Copy environment file

```bash
cp .env.example .env
```

The defaults work as-is with Docker Compose — no edits needed for local dev.

### 2. Start all services

```bash
docker compose up --build
```

Wait until the `api` service logs `Application startup complete`.

### 3. Verify health

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

## API Usage

### Upload an MP3

```bash
curl -X POST http://localhost:8000/jobs \
  -F "audio=@/path/to/your/file.mp3" \
  -F "instrument=guitar"
```
curl -X POST http://localhost:8000/jobs \
  -F "audio=@/Users/Kevin/Desktop/Music/trap-158bpm (online-audio-converter.com).mp3" \
  -F "instrument=guitar"

Example response:

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "CREATED",
  "instrument": "guitar",
  "audio_path": "/app/data/3fa85f64-5717-4562-b3fc-2c963f66afa6/audio.mp3",
  "created_at": "2025-01-01T12:00:00",
  "error": null
}
```

### Poll job status

```bash
curl http://localhost:8000/jobs/<job_id>
```

Status flow: `CREATED` → `TRANSCRIBING` → `READY` (or `FAILED` on error).
The stub worker sleeps 3 seconds between `TRANSCRIBING` and `READY`.

## Job Model

| Field        | Type     | Notes                              |
|--------------|----------|------------------------------------|
| `id`         | string   | UUID                               |
| `status`     | string   | CREATED \| TRANSCRIBING \| READY \| FAILED |
| `instrument` | string   | Passed in multipart form           |
| `audio_path` | string   | Absolute path inside container     |
| `created_at` | datetime | UTC, ISO-8601 in responses         |
| `error`      | string?  | Populated on FAILED                |

## Project Layout

```
backend/
  app.py            FastAPI app — startup, router registration
  config.py         Settings read from environment / .env
  database.py       SQLAlchemy engine, session factory, Base
  models.py         Job ORM model
  routes/
    health.py       GET /health
    jobs.py         POST /jobs, GET /jobs/{job_id}
  services/
    storage.py      Write uploaded audio to ./data/{job_id}/audio.mp3
  workers/
    tasks.py        process_job() — stub transcription task
    worker.py       RQ worker entrypoint
  Dockerfile
  requirements.txt
docker-compose.yml
.env.example
data/               Host-mounted volume; job directories created here
```

## Stopping

```bash
docker compose down          # stop containers
docker compose down -v       # stop + delete postgres volume
```
