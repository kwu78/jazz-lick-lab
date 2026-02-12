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
            {"pitch": 60, "start": 0.0, "duration": 0.5},
            {"pitch": 62, "start": 0.5, "duration": 0.5},
        ],
        "chords": [
            {"symbol": "Dm7", "start": 0.0},
            {"symbol": "G7", "start": 2.0},
        ],
    }
