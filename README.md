# Jazz Lick Lab

A transcription and practice tool for jazz musicians. Upload a recording, get an AI-powered transcription with chord recognition, then select licks to view as sheet music, analyze, and get coaching advice.

## Screenshots

### Waveform & Settings Calibration

![Waveform and Settings](screenshots/music.png)

Interactive waveform with region selection, beat grid overlay, and settings (tap tempo, offset, time signature).

### Score Preview

![Score Preview](screenshots/Scoring.png)

MusicXML score rendered in-browser. Supports key transposition, zoom, and notes beaming. The scoring accuracy still needs to be improved to make the notes look more readable. 

### Analysis & Coaching

![Coaching](screenshots/Coaching.png)

Lick analysis (chord tones, tensions, total notes) with AI-generated coaching: practice steps, variation ideas, and listening tips.

## Architecture

```
frontend/          React + TypeScript + Tailwind CSS (Vite)
backend/           FastAPI + SQLAlchemy + Postgres
  routes/          API endpoints (jobs, health)
  services/        Klangio API, MusicXML generation, music theory, coaching
  workers/         RQ background workers for transcription
  schemas/         Pydantic models
docker-compose.yml Postgres, Redis, API, Worker
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 22+ (for frontend dev server)
- A [Klangio](https://klangio.com) API key (for transcription)

### 1. Clone and configure

```bash
git clone <repo-url> && cd jazz-lick-lab
cp .env.example .env
```

Edit `.env` and add your API keys:

```
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/jazzlicklab
REDIS_URL=redis://redis:6379/0
DATA_DIR=/app/data
KLANGIO_API_TOKEN=<your-klangio-token>
```

Optional — for LLM-powered coaching (defaults to rule-based):

```
COACH_PROVIDER=llm
ANTHROPIC_API_KEY=<your-key>
```

### 2. Start backend services

```bash
docker compose up -d
```

This starts Postgres, Redis, the FastAPI server (port 8000), and the RQ worker.

### 3. Start frontend dev server

```bash
cd frontend
nvm use 22        
npm install
npm run dev       
```

### 4. Use it

1. Upload an audio file on the home page
2. Wait for transcription to complete (Klangio processes notes, chords, beat tracking)
3. Select a region on the waveform to isolate a lick
4. Adjust BPM/offset using tap tempo or auto-detected values
5. View the score preview, transpose keys
6. Check the analysis and coaching panels for practice advice

## Current Status

**Working end-to-end:**

- Audio upload and Klangio transcription (notes + chords + source separation + beat tracking)
- Auto-detection of BPM, time signature, and offset from Klangio MusicInfo
- Settings calibration panel (tap tempo, set-to-playhead offset, time sig dropdown)
- Preliminary preview of the music score 
- Lick analysis (chord tone / tension / passing tone breakdown)
- AI coaching (rule-based default, optional LLM via Anthropic API)
- Practice pack generation (MusicXML export)

## Possible Improvements
- Improve readability of the music score
- Improve accuracy of the transcription
- Align the chords currectly on the score
- Improve chord detections
- Detect and notate swing 8ths
- Split polyphonic passages into separate voices
- Mobile layout — responsive design for tablet/phone use