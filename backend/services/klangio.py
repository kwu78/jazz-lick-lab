import logging

logger = logging.getLogger(__name__)


def transcribe(audio_path: str, instrument: str) -> dict:
    """Transcribe audio to notes and chords.

    Currently returns mock data. Will be replaced with real
    Klangio API integration.
    """
    logger.info(
        "Transcribing audio_path=%s instrument=%s (mock)", audio_path, instrument
    )

    return {
        "notes": [
            {"pitch_midi": 60, "start_sec": 0.0, "duration_sec": 0.5},
            {"pitch_midi": 62, "start_sec": 0.5, "duration_sec": 0.5},
        ],
        "chords": [
            {"symbol": "Dm7", "start_sec": 0.0, "end_sec": 2.0},
            {"symbol": "G7", "start_sec": 2.0, "end_sec": None},
        ],
    }
