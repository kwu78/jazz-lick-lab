"""Minimal MusicXML generator using stdlib xml.etree.ElementTree.

Converts NoteEvent/ChordEvent lists to a MusicXML string suitable for
rendering in MuseScore, Flat.io, or similar score viewers.
"""

import xml.etree.ElementTree as ET

from services.theory import parse_chord_root

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIVISIONS_PER_BEAT = 4  # 16th-note grid resolution

# MIDI pitch class → (step, alter) — prefer flats for jazz
_PITCH_MAP: list[tuple[str, int]] = [
    ("C", 0), ("D", -1), ("D", 0), ("E", -1), ("E", 0), ("F", 0),
    ("F", 1), ("G", 0), ("A", -1), ("A", 0), ("B", -1), ("B", 0),
]

# Duration (in divisions) → (type_name, dotted)
_TYPE_MAP: dict[int, tuple[str, bool]] = {
    1: ("16th", False), 2: ("eighth", False), 3: ("eighth", True),
    4: ("quarter", False), 6: ("quarter", True), 8: ("half", False),
    12: ("half", True), 16: ("whole", False),
}

_VALID_DURATIONS = sorted(_TYPE_MAP.keys())

# Chord root name → MusicXML (root-step, root-alter)
_ROOT_STEP_ALTER: dict[str, tuple[str, int]] = {
    "C": ("C", 0), "C#": ("C", 1), "Db": ("D", -1),
    "D": ("D", 0), "D#": ("D", 1), "Eb": ("E", -1),
    "E": ("E", 0), "F": ("F", 0), "F#": ("F", 1),
    "Gb": ("G", -1), "G": ("G", 0), "G#": ("G", 1),
    "Ab": ("A", -1), "A": ("A", 0), "A#": ("A", 1),
    "Bb": ("B", -1), "B": ("B", 0),
}

# Chord quality suffix → MusicXML <kind> (longest-first to avoid partial match)
_QUALITY_TO_KIND: list[tuple[str, str]] = [
    ("maj7#11", "major-seventh"), ("maj9", "major-ninth"),
    ("maj13", "major-13th"), ("maj7", "major-seventh"),
    ("Maj7", "major-seventh"), ("M7", "major-seventh"),
    ("m7b5", "half-diminished"), ("min7b5", "half-diminished"),
    ("m9", "minor-ninth"), ("min9", "minor-ninth"),
    ("m11", "minor-11th"), ("m7", "minor-seventh"),
    ("min7", "minor-seventh"), ("m6", "minor-sixth"),
    ("m", "minor"), ("min", "minor"),
    ("dim7", "diminished-seventh"), ("dim", "diminished"),
    ("aug7", "augmented-seventh"), ("aug", "augmented"),
    ("sus4", "suspended-fourth"), ("sus2", "suspended-second"),
    ("7#9", "dominant"), ("7b9", "dominant"),
    ("7#11", "dominant"), ("7b5", "dominant"), ("7alt", "dominant"),
    ("9", "dominant-ninth"), ("13", "dominant-13th"),
    ("11", "dominant-11th"), ("7", "dominant"),
    ("6", "major-sixth"), ("", "major"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sub(parent: ET.Element, tag: str, text: str | None = None, **attribs) -> ET.Element:
    el = ET.SubElement(parent, tag, **attribs)
    if text is not None:
        el.text = str(text)
    return el


def _midi_to_pitch(midi: int) -> tuple[str, int, int]:
    """MIDI note number → (step, alter, octave)."""
    step, alter = _PITCH_MAP[midi % 12]
    octave = (midi // 12) - 1
    return step, alter, octave


def _snap_duration(div: int) -> int:
    if div <= 0:
        return 1
    return min(_VALID_DURATIONS, key=lambda d: abs(d - div))


def _type_for_duration(div: int) -> tuple[str, bool]:
    if div in _TYPE_MAP:
        return _TYPE_MAP[div]
    return _TYPE_MAP[min(_VALID_DURATIONS, key=lambda d: abs(d - div))]


def _parse_chord_kind(symbol: str) -> tuple[str, int, str, str]:
    """Parse chord symbol → (root_step, root_alter, kind, quality_text)."""
    root = parse_chord_root(symbol)
    if not root:
        return "C", 0, "other", symbol
    quality = symbol[len(root):]
    sa = _ROOT_STEP_ALTER.get(root)
    if not sa:
        return "C", 0, "other", symbol
    root_step, root_alter = sa
    kind = "major"
    for suffix, k in _QUALITY_TO_KIND:
        if quality == suffix or (suffix and quality.startswith(suffix)):
            kind = k
            break
    return root_step, root_alter, kind, quality


# ---------------------------------------------------------------------------
# XML emitters
# ---------------------------------------------------------------------------

def _emit_harmony(measure: ET.Element, symbol: str) -> None:
    root_step, root_alter, kind, quality_text = _parse_chord_kind(symbol)
    harmony = _sub(measure, "harmony")
    root_el = _sub(harmony, "root")
    _sub(root_el, "root-step", root_step)
    if root_alter != 0:
        _sub(root_el, "root-alter", str(root_alter))
    kind_el = _sub(harmony, "kind", kind)
    if quality_text:
        kind_el.set("text", quality_text)


def _emit_note(
    measure: ET.Element, midi: int, dur_div: int, is_chord: bool = False
) -> None:
    step, alter, octave = _midi_to_pitch(midi)
    type_name, dotted = _type_for_duration(dur_div)
    note = _sub(measure, "note")
    if is_chord:
        _sub(note, "chord")
    pitch = _sub(note, "pitch")
    _sub(pitch, "step", step)
    if alter != 0:
        _sub(pitch, "alter", str(alter))
    _sub(pitch, "octave", str(octave))
    _sub(note, "duration", str(dur_div))
    _sub(note, "type", type_name)
    if dotted:
        _sub(note, "dot")


def _emit_rests(measure: ET.Element, dur_div: int) -> None:
    """Emit one or more rests totalling dur_div divisions."""
    remaining = dur_div
    while remaining > 0:
        best = 1
        for d in reversed(_VALID_DURATIONS):
            if d <= remaining:
                best = d
                break
        type_name, dotted = _type_for_duration(best)
        note = _sub(measure, "note")
        _sub(note, "rest")
        _sub(note, "duration", str(best))
        _sub(note, "type", type_name)
        if dotted:
            _sub(note, "dot")
        remaining -= best


def _emit_rests_with_chords(
    measure: ET.Element,
    start: int,
    duration: int,
    chord_lookup: dict[int, str],
) -> None:
    """Emit rests over [start, start+duration), inserting chord harmonies."""
    end = start + duration
    chord_offsets = sorted(o for o in chord_lookup if start < o < end)

    cursor = start
    for co in chord_offsets:
        if co > cursor:
            _emit_rests(measure, co - cursor)
        _emit_harmony(measure, chord_lookup[co])
        cursor = co

    if cursor < end:
        _emit_rests(measure, end - cursor)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_musicxml(
    notes: list,
    chords: list,
    bpm: float = 120.0,
    time_signature: str = "4/4",
) -> str:
    """Generate a MusicXML string from note and chord events.

    Args:
        notes: List of NoteEvent (pitch_midi, start_sec, duration_sec).
        chords: List of ChordEvent (symbol, start_sec, end_sec).
        bpm: Tempo in beats per minute.
        time_signature: Time signature as "N/D" (e.g. "4/4").

    Returns:
        UTF-8 MusicXML string.
    """
    ts_parts = time_signature.split("/")
    beats_per_measure = int(ts_parts[0])
    beat_type = int(ts_parts[1])
    divs_per_measure = beats_per_measure * DIVISIONS_PER_BEAT
    beat_dur = 60.0 / bpm

    # --- Quantise to grid ---------------------------------------------------
    note_grid: list[tuple[int, int, int]] = []
    for n in notes:
        s = max(0, round(n.start_sec / beat_dur * DIVISIONS_PER_BEAT))
        d = max(1, round(n.duration_sec / beat_dur * DIVISIONS_PER_BEAT))
        note_grid.append((s, d, n.pitch_midi))
    note_grid.sort(key=lambda x: (x[0], x[2]))

    chord_grid: list[tuple[int, str]] = []
    for c in chords:
        s = max(0, round(c.start_sec / beat_dur * DIVISIONS_PER_BEAT))
        chord_grid.append((s, c.symbol))
    chord_grid.sort()

    # --- Determine measure count --------------------------------------------
    max_div = 0
    if note_grid:
        max_div = max(s + d for s, d, _ in note_grid)
    if chord_grid:
        max_div = max(max_div, max(s for s, _ in chord_grid) + 1)
    num_measures = max(1, -(-max_div // divs_per_measure))

    # --- Group events by measure --------------------------------------------
    notes_by_m: dict[int, list[tuple[int, int, int]]] = {}
    for s, d, midi in note_grid:
        mi = s // divs_per_measure
        off = s % divs_per_measure
        d = min(d, divs_per_measure - off)
        notes_by_m.setdefault(mi, []).append((off, d, midi))

    chords_by_m: dict[int, dict[int, str]] = {}
    for s, sym in chord_grid:
        mi = s // divs_per_measure
        off = s % divs_per_measure
        chords_by_m.setdefault(mi, {})[off] = sym

    # --- Build XML tree -----------------------------------------------------
    root = ET.Element("score-partwise", version="4.0")
    part_list = _sub(root, "part-list")
    sp = _sub(part_list, "score-part", id="P1")
    _sub(sp, "part-name", "Music")
    part = _sub(root, "part", id="P1")

    for mi in range(num_measures):
        measure = _sub(part, "measure", number=str(mi + 1))

        # First measure: attributes + tempo
        if mi == 0:
            attrs = _sub(measure, "attributes")
            _sub(attrs, "divisions", str(DIVISIONS_PER_BEAT))
            te = _sub(attrs, "time")
            _sub(te, "beats", str(beats_per_measure))
            _sub(te, "beat-type", str(beat_type))
            cl = _sub(attrs, "clef")
            _sub(cl, "sign", "G")
            _sub(cl, "line", "2")
            direction = _sub(measure, "direction", placement="above")
            dt = _sub(direction, "direction-type")
            metro = _sub(dt, "metronome")
            _sub(metro, "beat-unit", "quarter")
            _sub(metro, "per-minute", str(int(bpm)))
            _sub(direction, "sound", tempo=str(int(bpm)))

        m_notes = notes_by_m.get(mi, [])
        m_chords = chords_by_m.get(mi, {})

        # Group notes by offset
        by_offset: dict[int, list[tuple[int, int]]] = {}
        for off, dur, midi in m_notes:
            by_offset.setdefault(off, []).append((dur, midi))

        # All event positions (notes + chords)
        event_offsets = sorted(set(by_offset.keys()) | set(m_chords.keys()))

        cursor = 0
        for off in event_offsets:
            if off < cursor:
                continue
            if off > cursor:
                _emit_rests_with_chords(measure, cursor, off - cursor, m_chords)
                cursor = off

            if off in m_chords:
                _emit_harmony(measure, m_chords[off])

            if off in by_offset:
                nlist = by_offset[off]
                for i, (dur, midi) in enumerate(nlist):
                    clamped = min(dur, divs_per_measure - off)
                    clamped = _snap_duration(clamped)
                    if clamped > divs_per_measure - off:
                        clamped = max(1, divs_per_measure - off)
                    _emit_note(measure, midi, clamped, is_chord=(i > 0))
                first_dur = min(nlist[0][0], divs_per_measure - off)
                first_dur = _snap_duration(first_dur)
                cursor = min(off + first_dur, divs_per_measure)

        if cursor < divs_per_measure:
            if cursor in m_chords and cursor not in by_offset:
                _emit_harmony(measure, m_chords[cursor])
            _emit_rests_with_chords(measure, cursor, divs_per_measure - cursor, m_chords)

    # --- Serialise ----------------------------------------------------------
    ET.indent(root, space="  ")
    xml_str = ET.tostring(root, encoding="unicode")
    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    doctype = (
        '<!DOCTYPE score-partwise PUBLIC '
        '"-//Recordare//DTD MusicXML 4.0 Partwise//EN" '
        '"http://www.musicxml.org/dtds/partwise.dtd">\n'
    )
    return header + doctype + xml_str
