# Jazz Lick Lab

A transcription and practice tool for jazz musicians. Upload a recording, get an AI-powered transcription with chord recognition, then select licks to view as sheet music, analyze, and get coaching advice.

## Screenshots

### Waveform & Settings Calibration

![Waveform and Settings](screenshots/music.png)

Interactive waveform with region selection, beat grid overlay, and settings (tap tempo, offset, time signature).

### Score Preview

![Score Preview](screenshots/Scoring.png)

MusicXML score rendered in-browser. Supports key transposition, zoom, and notes beaming.

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
infrastructure/    AWS CDK v2 (TypeScript)
docker-compose.yml Postgres, Redis, API, Worker
```

## Features

- Audio upload with Klangio transcription (notes, chords, source separation, beat tracking)
- Grand staff notation (treble + bass clefs) with automatic staff assignment
- Score preview with key transposition, zoom, and chord symbol alignment
- Chord symbol normalization (Klangio format → standard notation)
- Source separation A/B toggle (original vs isolated stem playback)
- Settings calibration (tap tempo, set-to-playhead offset, time signature)
- Lick analysis (chord tone / tension / passing tone breakdown)
- AI coaching (rule-based default, optional LLM via Anthropic API)
- Practice pack generation with transposition to all 12 keys (MusicXML + ZIP download)
- Consistent score rendering between preview and practice pack views

## Quick Start (Local)

### Prerequisites

- Docker & Docker Compose
- Node.js 22+ (for frontend dev server)
- A [Klangio](https://klangio.com) API key

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

Optional — for LLM-powered coaching:

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
VITE_API_URL=http://localhost:8000 npm run dev
```

### 4. Use it

1. Upload an audio file on the home page
2. Wait for transcription to complete
3. Select a region on the waveform to isolate a lick
4. Adjust BPM/offset using tap tempo or auto-detected values
5. View the score preview, transpose keys
6. Generate a practice pack to get the lick in all 12 keys
7. Check the analysis and coaching panels for practice advice

## AWS Deployment

The `infrastructure/` directory contains an AWS CDK v2 stack that deploys:

- **VPC** with public/private subnets and NAT gateway
- **ECS Fargate** for API and Worker services
- **RDS PostgreSQL** and **ElastiCache Redis**
- **EFS** shared filesystem for audio/artifact storage
- **ALB** for API load balancing
- **CloudFront + S3** for frontend hosting (proxies `/jobs/*` to ALB)
- **Secrets Manager** for API keys

### Deploy

```bash
cd infrastructure
npm install
npx cdk deploy
```

After deployment, build and push backend images to ECR, upload the frontend to S3, and set API keys in Secrets Manager.

## Possible Improvements

- Improve accuracy of the transcription
- Detect and notate swing 8ths
- Split polyphonic passages into separate voices
- Mobile layout — responsive design for tablet/phone use
