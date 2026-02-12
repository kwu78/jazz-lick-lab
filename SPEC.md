# Jazz Lick Lab — Hybrid AI Jazz Analysis & Practice Engine (MVP+)

---

# 1. Vision

Jazz Lick Lab transforms real recordings into structured, theory-aware practice material.

Upload a recording → Transcribe instrument → Detect chords → Select a lick →  
Analyze functional harmony → Generate coaching insights → Practice in 12 keys.

This system combines:

• Modern music AI (Klangio transcription + chord detection)  
• Deterministic symbolic music theory engine  
• LLM-based coaching grounded in structured analysis  

The goal is not just transcription — but **musical intelligence + pedagogy**.

---

# 2. Core Principles

1. AI for perception (audio → notes/chords)
2. Deterministic rules for theory analysis
3. LLM only for explanation, never for core truth
4. Human-in-the-loop editing
5. Fast shipping (local storage)
6. Clean architecture for scaling

---

# 3. MVP Scope

## Required Features

### 3.1 Instrument-Level Transcription
- User uploads MP3
- User selects target instrument
- Backend submits to Klangio
- Retrieve:
  - Note events
  - Chord detection
- Normalize to internal schema

### 3.2 Chord Editing
- Auto-fill chords from Klangio
- Allow user to edit chords (bar-level UI)
- Edited chords override detected chords

### 3.3 Alignment
- User inputs BPM
- User sets offset slider (bar 1 beat 1)
- Notes aligned to bar/beat
- Chords mapped per bar

### 3.4 Manual Lick Selection
- User highlights note range
- Save selection as start_idx/end_idx

### 3.5 Functional Lick Analysis (Symbolic Engine)

Given selected lick:

Compute:

- Functional progression (ii–V–I, V–I, iiø–V–i)
- Key center inference
- Resolution target note
- Tension classification (9, b9, #11, b13 etc.)
- Chord-tone coverage %
- Guide-tone coverage %
- Bar span

Return structured analysis JSON.

### 3.6 LLM Coaching Layer (Grounded)

Input:
- Structured analysis JSON
- User instrument
- Skill level

Output:
- Summary explanation
- Why it works
- 3–4 practice steps
- Variation idea
- Listening tip

LLM MUST:
- Only use structured data provided
- Not invent new chords or notes

### 3.7 12-Key Practice Pack

For selected lick:
- Transpose notes
- Transpose chord roots
- Generate MusicXML per key
- Generate MIDI per key
- Bundle into ZIP

---

# 4. Non-Goals (MVP)

- No automatic lick detection
- No corpus-wide lick search
- No advanced form parsing (AABA, repeats)
- No S3 yet (local only)
- No automatic key detection (optional future)

---

# 5. Architecture

## Frontend
- React.js
- Sheet rendering
- Chord editor
- Lick selection
- Analysis panel
- Coaching panel
- Practice pack download

## Backend
- FastAPI
- Postgres (metadata)
- Redis (job queue)
- Worker (Celery or RQ)

## Storage (MVP)
Local filesystem:

./data/{job_id}/
    audio.mp3
    transcription.json
    chords.json
    sheet.musicxml
    analysis.json
    practice_pack.zip

Abstract behind Storage interface for future S3.

---

# 6. Data Models

## Job
- id
- status: CREATED | TRANSCRIBING | READY | FAILED
- instrument
- bpm
- offset_sec
- created_at
- error

## NoteEvent
- start_sec
- end_sec
- midi
- velocity
- bar
- beat

## ChordEvent
- bar
- chord_symbol

## Selection
- start_idx
- end_idx
- chords
- bar_span

## FunctionalAnalysis
- function_label (e.g. "ii–V–I in C")
- key_center
- resolution_note
- resolution_role (3rd, 7th, etc.)
- tensions_used
- chord_tone_coverage
- guide_tone_coverage
- bar_span

## CoachingResponse
- summary
- why_it_works
- practice_steps[]
- variation_idea
- listening_tip

## PracticePack
- job_id
- keys[]
- zip_url

---

# 7. Theory Engine Specification

## 7.1 Chord Parser

Parse:
- Root (A–G with #/b)
- Quality (maj7, m7, 7, ø7, dim7, 6, sus)
- Extensions (9, 11, 13)
- Alterations (b9, #9, #11, b13, alt)

Output:
Chord object with:
- root pitch class
- chord tones set
- tension set

## 7.2 Functional Pattern Detection

Detect:

- Major ii–V–I
- Minor iiø–V–i
- V–I
- ii–V

Use:
- Root motion
- Quality pattern
- Resolution chord type

Infer key center from final resolution.

## 7.3 Resolution Target Detection

Score final notes by:
- Is chord tone
- Is 3rd or 7th
- Is longest duration
- Is on strong beat

Pick highest scoring note.

## 7.4 Tension Classification

For each note:
- Compare pitch class to:
  - chord tones
  - available tensions
- Record tension types used

Focus on dominant chords first.

## 7.5 Coverage Metrics

Compute:
- chord-tone coverage %
- guide-tone coverage %

---

# 8. LLM Coaching Layer

## Input
- FunctionalAnalysis JSON
- Instrument
- Skill level

## Output Structure
- 3-sentence summary
- Why it works
- 3–4 practice steps
- 1 variation idea
- 1 listening tip

## Guardrails
- Only reference provided analysis data
- No hallucinated chords/notes
- Deterministic analysis always displayed as ground truth

---

# 9. API Endpoints

POST /jobs  
GET /jobs/{id}  
POST /jobs/{id}/settings  
GET /jobs/{id}/notes  
GET /jobs/{id}/chords  
PUT /jobs/{id}/chords  
POST /jobs/{id}/selection  
GET /jobs/{id}/analysis  
GET /jobs/{id}/coaching  
POST /jobs/{id}/practice-pack  

---

# 10. Observability

Structured logs:
- job_id
- stage
- instrument
- transcription latency
- processing latency

---

# 11. Testing Requirements

Unit tests:
- chord parsing
- transposition
- ii–V–I detection
- resolution detection
- tension classification

Integration test:
- Mock Klangio
- Full pipeline run

---

# 12. Demo Deliverables

- Example audio
- Screenshot:
  - Sheet
  - Lick selection
  - Functional analysis panel
  - Coaching panel
- 60–90 sec demo video
- Architecture diagram in README

---

# 13. Future Extensions

- Automatic lick detection
- Lick similarity clustering
- Roman numeral abstraction layer
- Style classification
- S3 storage
- Tempo auto-detection
- Corpus-wide lick mining
