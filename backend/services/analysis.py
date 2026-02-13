from typing import List, Optional

from schemas.transcription import NoteEvent, ChordEvent
from schemas.analysis import CoverageMetrics, IiVIEvent
from services.theory import PITCH_CLASS, parse_chord_root

# Chord-tone sets relative to root (semitone offsets)
_CHORD_TONES = {
    "maj7": {0, 4, 7, 11},
    "min7": {0, 3, 7, 10},
    "dom7": {0, 4, 7, 10},
}

# Tension sets relative to root (semitone offsets)
_TENSIONS = {
    "maj7": {2, 6, 9},       # 9, #11, 13
    "min7": {2, 5, 9},       # 9, 11, 13
    "dom7": {1, 2, 5, 6, 9}, # b9, 9, 11, #11, 13
}


def _chord_quality(symbol: str) -> str:
    """Determine quality bucket from chord symbol suffix."""
    root = parse_chord_root(symbol)
    suffix = symbol[len(root):] if root else symbol

    if "maj" in suffix or "\u0394" in suffix:
        return "maj7"
    if "m" in suffix:
        return "min7"
    if "7" in suffix:
        return "dom7"
    # Default to major triad-ish; treat as maj7 for MVP
    return "maj7"


def _root_semitone(symbol: str) -> Optional[int]:
    """Return root pitch class (0-11) or None."""
    root = parse_chord_root(symbol)
    if root is None:
        return None
    return PITCH_CLASS.get(root)


def classify_note_against_chord(
    note_pitch_midi: int, chord_symbol: str
) -> str:
    """Classify a note as 'chord_tone', 'tension', or 'other'."""
    root_pc = _root_semitone(chord_symbol)
    if root_pc is None:
        return "other"

    quality = _chord_quality(chord_symbol)
    note_pc = note_pitch_midi % 12
    interval = (note_pc - root_pc) % 12

    if interval in _CHORD_TONES[quality]:
        return "chord_tone"
    if interval in _TENSIONS[quality]:
        return "tension"
    return "other"


def _find_active_chord(
    t: float, chords: List[ChordEvent]
) -> Optional[ChordEvent]:
    """Find the chord active at time t.

    A chord is active if chord.start_sec <= t and
    (chord.end_sec is None or chord.end_sec > t).
    """
    for c in reversed(chords):
        if c.start_sec <= t and (c.end_sec is None or c.end_sec > t):
            return c
    return None


def compute_coverage(
    notes: List[NoteEvent], chords: List[ChordEvent]
) -> CoverageMetrics:
    """Compute chord-tone / tension / other coverage metrics."""
    chord_tone_count = 0
    tension_count = 0
    other_count = 0

    sorted_chords = sorted(chords, key=lambda c: c.start_sec)

    for n in notes:
        active = _find_active_chord(n.start_sec, sorted_chords)
        if active is None:
            other_count += 1
            continue

        label = classify_note_against_chord(n.pitch_midi, active.symbol)
        if label == "chord_tone":
            chord_tone_count += 1
        elif label == "tension":
            tension_count += 1
        else:
            other_count += 1

    total = len(notes)
    return CoverageMetrics(
        total_notes=total,
        chord_tone_notes=chord_tone_count,
        tension_notes=tension_count,
        other_notes=other_count,
        chord_tone_pct=round(chord_tone_count / total, 3) if total else 0.0,
        tension_pct=round(tension_count / total, 3) if total else 0.0,
    )


def detect_ii_v_i(chords: List[ChordEvent]) -> List[IiVIEvent]:
    """Detect ii-V-I patterns in consecutive chord triplets."""
    if len(chords) < 3:
        return []

    sorted_chords = sorted(chords, key=lambda c: c.start_sec)
    results: List[IiVIEvent] = []

    for i in range(len(sorted_chords) - 2):
        c1, c2, c3 = sorted_chords[i], sorted_chords[i + 1], sorted_chords[i + 2]

        q1 = _chord_quality(c1.symbol)
        q2 = _chord_quality(c2.symbol)
        q3 = _chord_quality(c3.symbol)

        # Pattern: minor7 -> dominant7 -> major7
        if q1 != "min7" or q2 != "dom7" or q3 != "maj7":
            continue

        r1 = _root_semitone(c1.symbol)
        r2 = _root_semitone(c2.symbol)
        r3 = _root_semitone(c3.symbol)

        if r1 is None or r2 is None or r3 is None:
            continue

        # Root motion: each step is up a 4th / down a 5th (+5 semitones mod 12)
        if (r2 - r1) % 12 != 5:
            continue
        if (r3 - r2) % 12 != 5:
            continue

        end_sec = c3.end_sec if c3.end_sec is not None else c3.start_sec
        key_root = parse_chord_root(c3.symbol)

        results.append(IiVIEvent(
            start_sec=c1.start_sec,
            end_sec=end_sec,
            chords=[c1.symbol, c2.symbol, c3.symbol],
            key_guess=key_root,
        ))

    return results
