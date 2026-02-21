"""Minimal MusicXML generator using stdlib xml.etree.ElementTree.

Converts NoteEvent/ChordEvent lists to a MusicXML string suitable for
rendering in MuseScore, Flat.io, or similar score viewers.
"""

import xml.etree.ElementTree as ET
from typing import Literal

from services.theory import parse_chord_root

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GridSize = Literal[8, 16]

# Divisions per beat for each grid: 8th=2, 16th=8 (32nd-note resolution)
_GRID_DIVISIONS: dict[int, int] = {8: 2, 16: 8}

# MIDI pitch class → (step, alter) — prefer flats for jazz
_PITCH_MAP: list[tuple[str, int]] = [
    ("C", 0), ("D", -1), ("D", 0), ("E", -1), ("E", 0), ("F", 0),
    ("F", 1), ("G", 0), ("A", -1), ("A", 0), ("B", -1), ("B", 0),
]

# Duration (in divisions) → (type_name, dotted)
# Grid=16: divisions_per_beat=8, so 8 divs = quarter (32nd-note resolution)
_TYPE_MAP_16: dict[int, tuple[str, bool]] = {
    1: ("32nd", False), 2: ("16th", False), 3: ("16th", True),
    4: ("eighth", False), 6: ("eighth", True), 8: ("quarter", False),
    12: ("quarter", True), 16: ("half", False), 24: ("half", True),
    32: ("whole", False),
}
# Grid=8: divisions_per_beat=2, so 2 divs = quarter
_TYPE_MAP_8: dict[int, tuple[str, bool]] = {
    1: ("eighth", False), 2: ("quarter", False), 3: ("quarter", True),
    4: ("half", False), 6: ("half", True), 8: ("whole", False),
}

_VALID_DURATIONS_16 = sorted(_TYPE_MAP_16.keys())
_VALID_DURATIONS_8 = sorted(_TYPE_MAP_8.keys())

def _get_type_map(grid: int) -> tuple[dict[int, tuple[str, bool]], list[int]]:
    if grid == 8:
        return _TYPE_MAP_8, _VALID_DURATIONS_8
    return _TYPE_MAP_16, _VALID_DURATIONS_16

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

# Klangio colon-style quality → jazz lead-sheet suffix
_KLANGIO_QUALITY: dict[str, str] = {
    "maj": "", "min": "m", "dim": "dim", "aug": "aug",
    "dom": "7", "hdim7": "m7b5", "min7": "m7", "maj7": "maj7",
    "minmaj7": "mMaj7", "dim7": "dim7", "aug7": "aug7",
    "sus4": "sus4", "sus2": "sus2", "min6": "m6", "maj6": "6",
    "9": "9", "min9": "m9", "maj9": "maj9",
    "11": "11", "min11": "m11", "13": "13",
}

# Sharp-root → flat enharmonic (jazz convention: prefer flats)
_ENHARMONIC_FLAT: dict[str, str] = {
    "C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb",
}


def _normalize_chord_symbol(symbol: str) -> str:
    """Normalise Klangio-style 'C:min' → 'Cm', prefer flats."""
    if ":" in symbol:
        root, quality = symbol.split(":", 1)
        suffix = _KLANGIO_QUALITY.get(quality, quality)
        symbol = root + suffix
    # Prefer flat spellings for roots
    for sharp, flat in _ENHARMONIC_FLAT.items():
        if symbol.startswith(sharp):
            symbol = flat + symbol[len(sharp):]
            break
    return symbol


# ---------------------------------------------------------------------------
# Pre-processing: timing cleanup
# ---------------------------------------------------------------------------

def cleanup_notes_for_notation(
    notes: list,
    min_dur: float = 0.06,
    merge_gap: float = 0.06,
    snap_sec: float = 0.02,
) -> list:
    """Clean up raw transcription notes for readable notation.

    - Drop very short notes (< min_dur)
    - Merge adjacent same-pitch notes with tiny gaps
    - Snap start/duration to a fine grid to remove micro-jitter
    """
    from schemas.transcription import NoteEvent

    # Sort by start time, then pitch
    sorted_notes = sorted(notes, key=lambda n: (n.start_sec, n.pitch_midi))

    # Drop tiny notes
    filtered = [n for n in sorted_notes if n.duration_sec >= min_dur]

    # Merge adjacent same-pitch notes
    merged: list[NoteEvent] = []
    for n in filtered:
        if merged:
            prev = merged[-1]
            prev_end = prev.start_sec + prev.duration_sec
            if (
                n.pitch_midi == prev.pitch_midi
                and n.start_sec <= prev_end + merge_gap
            ):
                new_end = max(prev_end, n.start_sec + n.duration_sec)
                merged[-1] = NoteEvent(
                    pitch_midi=prev.pitch_midi,
                    start_sec=prev.start_sec,
                    duration_sec=new_end - prev.start_sec,
                )
                continue
        merged.append(n)

    # Snap to fine grid
    result = []
    for n in merged:
        s = round(n.start_sec / snap_sec) * snap_sec
        d = round(n.duration_sec / snap_sec) * snap_sec
        d = max(snap_sec, d)
        result.append(NoteEvent(pitch_midi=n.pitch_midi, start_sec=s, duration_sec=d))

    # Swallow small gaps: extend previous note to close tiny gaps
    for i in range(len(result) - 1):
        prev_end = result[i].start_sec + result[i].duration_sec
        gap = result[i + 1].start_sec - prev_end
        if 0 < gap < 0.04:
            result[i] = NoteEvent(
                pitch_midi=result[i].pitch_midi,
                start_sec=result[i].start_sec,
                duration_sec=result[i].duration_sec + gap,
            )

    return result


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


def _snap_duration(div: int, valid: list[int]) -> int:
    if div <= 0:
        return 1
    return min(valid, key=lambda d: abs(d - div))


def _type_for_duration(div: int, type_map: dict[int, tuple[str, bool]], valid: list[int]) -> tuple[str, bool]:
    if div in type_map:
        return type_map[div]
    return type_map[min(valid, key=lambda d: abs(d - div))]


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
# Beaming
# ---------------------------------------------------------------------------

def _compute_beaming(
    voice_events: list[tuple[int, int]],
    divs_per_beat: int,
    type_map: dict[int, tuple[str, bool]],
    valid: list[int],
) -> dict[int, list[tuple[int, str]]]:
    """Compute beam assignments for notes in a measure.

    voice_events: [(offset_in_measure, clamped_dur_divs), ...] in order.
    Returns dict mapping note offset → [(beam_number, beam_value), ...].
    Only offsets that participate in a beam group are included.
    """
    _beamable = frozenset({"eighth", "16th", "32nd"})
    _sub_beam = frozenset({"16th", "32nd"})

    # Annotate each event
    ann = []
    for off, dur in voice_events:
        tname, _ = _type_for_duration(dur, type_map, valid)
        ann.append({
            "off": off, "dur": dur, "type": tname,
            "beat": off // divs_per_beat,
            "beamable": tname in _beamable,
            "sub": tname in _sub_beam,
        })

    # --- Beam-1 groups: consecutive beamable notes, same beat, no rest gap --
    groups: list[list[int]] = []
    cur: list[int] = []
    for i, ev in enumerate(ann):
        if ev["beamable"]:
            if cur:
                prev = ann[cur[-1]]
                if prev["beat"] == ev["beat"] and prev["off"] + prev["dur"] >= ev["off"]:
                    cur.append(i)
                else:
                    if len(cur) >= 2:
                        groups.append(cur)
                    cur = [i]
            else:
                cur = [i]
        else:
            if len(cur) >= 2:
                groups.append(cur)
            cur = []
    if len(cur) >= 2:
        groups.append(cur)

    result: dict[int, list[tuple[int, str]]] = {}

    for group in groups:
        # Beam 1: begin / continue / end
        for gi, idx in enumerate(group):
            off = ann[idx]["off"]
            if gi == 0:
                result[off] = [(1, "begin")]
            elif gi == len(group) - 1:
                result[off] = [(1, "end")]
            else:
                result[off] = [(1, "continue")]

        # Beam 2: sub-runs of 16th/32nd within the group
        sub_runs: list[list[int]] = []
        cur_sub: list[int] = []
        for gi, idx in enumerate(group):
            if ann[idx]["sub"]:
                cur_sub.append(gi)
            else:
                if cur_sub:
                    sub_runs.append(cur_sub)
                cur_sub = []
        if cur_sub:
            sub_runs.append(cur_sub)

        for run in sub_runs:
            if len(run) >= 2:
                for si, gi in enumerate(run):
                    off = ann[group[gi]]["off"]
                    if si == 0:
                        result[off].append((2, "begin"))
                    elif si == len(run) - 1:
                        result[off].append((2, "end"))
                    else:
                        result[off].append((2, "continue"))
            else:
                gi = run[0]
                off = ann[group[gi]]["off"]
                if gi == 0:
                    result[off].append((2, "forward-hook"))
                else:
                    result[off].append((2, "backward-hook"))

    return result


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
    measure: ET.Element, midi: int, dur_div: int,
    type_map: dict, valid: list, is_chord: bool = False,
    tie_start: bool = False, tie_stop: bool = False,
    beams: list[tuple[int, str]] | None = None,
    staff: int = 1,
) -> None:
    step, alter, octave = _midi_to_pitch(midi)
    type_name, dotted = _type_for_duration(dur_div, type_map, valid)
    note = _sub(measure, "note")
    if is_chord:
        _sub(note, "chord")
    pitch = _sub(note, "pitch")
    _sub(pitch, "step", step)
    if alter != 0:
        _sub(pitch, "alter", str(alter))
    _sub(pitch, "octave", str(octave))
    _sub(note, "duration", str(dur_div))
    _sub(note, "staff", str(staff))
    if tie_stop:
        _sub(note, "tie", type="stop")
    if tie_start:
        _sub(note, "tie", type="start")
    _sub(note, "type", type_name)
    if dotted:
        _sub(note, "dot")
    if beams:
        for beam_num, beam_val in beams:
            _sub(note, "beam", beam_val, number=str(beam_num))
    if tie_start or tie_stop:
        notations = _sub(note, "notations")
        if tie_stop:
            _sub(notations, "tied", type="stop")
        if tie_start:
            _sub(notations, "tied", type="start")


def _emit_rests(measure: ET.Element, dur_div: int, type_map: dict, valid: list) -> None:
    """Emit one or more rests totalling dur_div divisions."""
    remaining = dur_div
    while remaining > 0:
        best = 1
        for d in reversed(valid):
            if d <= remaining:
                best = d
                break
        type_name, dotted = _type_for_duration(best, type_map, valid)
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
    type_map: dict,
    valid: list,
) -> None:
    """Emit rests over [start, start+duration), inserting chord harmonies."""
    end = start + duration
    chord_offsets = sorted(o for o in chord_lookup if start < o < end)

    cursor = start
    for co in chord_offsets:
        if co > cursor:
            _emit_rests(measure, co - cursor, type_map, valid)
        _emit_harmony(measure, chord_lookup[co])
        cursor = co

    if cursor < end:
        _emit_rests(measure, end - cursor, type_map, valid)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_musicxml(
    notes: list,
    chords: list,
    bpm: float = 120.0,
    time_signature: str = "4/4",
    grid: int = 16,
    key_sig: str | None = None,
) -> str:
    """Generate a MusicXML string from note and chord events.

    Args:
        notes: List of NoteEvent (pitch_midi, start_sec, duration_sec).
        chords: List of ChordEvent (symbol, start_sec, end_sec).
        bpm: Tempo in beats per minute.
        time_signature: Time signature as "N/D" (e.g. "4/4").
        grid: Quantization grid — 8 (eighth-note) or 16 (sixteenth-note).

    Returns:
        UTF-8 MusicXML string.
    """
    divs_per_beat = _GRID_DIVISIONS.get(grid, 4)
    type_map, valid = _get_type_map(grid)

    ts_parts = time_signature.split("/")
    beats_per_measure = int(ts_parts[0])
    beat_type = int(ts_parts[1])
    divs_per_measure = beats_per_measure * divs_per_beat
    beat_dur = 60.0 / bpm

    # --- Quantise to grid ---------------------------------------------------
    note_grid: list[tuple[int, int, int]] = []
    for n in notes:
        s = max(0, round(n.start_sec / beat_dur * divs_per_beat))
        d = max(1, round(n.duration_sec / beat_dur * divs_per_beat))
        note_grid.append((s, d, n.pitch_midi))
    note_grid.sort(key=lambda x: (x[0], x[2]))

    # --- Determine measure count --------------------------------------------
    max_div = 0
    if note_grid:
        max_div = max(s + d for s, d, _ in note_grid)
    if chords:
        last_chord_div = max(
            max(0, round(c.start_sec / beat_dur * divs_per_beat)) for c in chords
        )
        max_div = max(max_div, last_chord_div + 1)
    num_measures = max(1, -(-max_div // divs_per_measure))

    # --- Group events by measure (split notes across barlines with ties) -----
    notes_by_m: dict[int, list[tuple[int, int, int, bool, bool]]] = {}
    for s, d, midi in note_grid:
        remaining = d
        cur_pos = s
        is_first = True
        while remaining > 0:
            mi = cur_pos // divs_per_measure
            off = cur_pos % divs_per_measure
            space = divs_per_measure - off
            chunk = min(remaining, space)
            is_last = (remaining - chunk) <= 0
            t_start = not is_last
            t_stop = not is_first
            notes_by_m.setdefault(mi, []).append((off, chunk, midi, t_start, t_stop))
            cur_pos += chunk
            remaining -= chunk
            is_first = False

    # --- One chord per measure (greatest overlap wins) -----------------------
    measure_sec = beats_per_measure * beat_dur
    chord_spans: list[tuple[float, float, str]] = []
    for ci, c in enumerate(chords):
        if c.symbol == "N":
            continue
        cs = c.start_sec
        ce = c.end_sec if c.end_sec is not None else (
            chords[ci + 1].start_sec if ci + 1 < len(chords) else cs + measure_sec
        )
        chord_spans.append((cs, ce, _normalize_chord_symbol(c.symbol)))

    chords_by_m: dict[int, dict[int, str]] = {}
    for mi in range(num_measures):
        ms = mi * measure_sec
        me = ms + measure_sec
        best_sym: str | None = None
        best_overlap = 0.0
        for cs, ce, sym in chord_spans:
            overlap = max(0.0, min(ce, me) - max(cs, ms))
            if overlap > best_overlap:
                best_overlap = overlap
                best_sym = sym
        if best_sym is not None:
            chords_by_m[mi] = {0: best_sym}

    # --- Build XML tree -----------------------------------------------------
    root = ET.Element("score-partwise", version="4.0")
    part_list = _sub(root, "part-list")
    pg_start = _sub(part_list, "part-group", type="start", number="1")
    _sub(pg_start, "group-symbol", "brace")
    _sub(pg_start, "group-barline", "yes")
    sp = _sub(part_list, "score-part", id="P1")
    _sub(sp, "part-name", "Music")
    _sub(part_list, "part-group", type="stop", number="1")
    part = _sub(root, "part", id="P1")

    for mi in range(num_measures):
        measure = _sub(part, "measure", number=str(mi + 1))

        # First measure: attributes + tempo
        if mi == 0:
            attrs = _sub(measure, "attributes")
            _sub(attrs, "divisions", str(divs_per_beat))
            if key_sig is not None:
                from services.theory import key_to_fifths
                key_el = _sub(attrs, "key")
                _sub(key_el, "fifths", str(key_to_fifths(key_sig)))
            te = _sub(attrs, "time")
            _sub(te, "beats", str(beats_per_measure))
            _sub(te, "beat-type", str(beat_type))
            _sub(attrs, "staves", "2")
            cl1 = _sub(attrs, "clef", number="1")
            _sub(cl1, "sign", "G")
            _sub(cl1, "line", "2")
            cl2 = _sub(attrs, "clef", number="2")
            _sub(cl2, "sign", "F")
            _sub(cl2, "line", "4")
            direction = _sub(measure, "direction", placement="above")
            dt = _sub(direction, "direction-type")
            metro = _sub(dt, "metronome")
            _sub(metro, "beat-unit", "quarter")
            _sub(metro, "per-minute", str(int(bpm)))
            _sub(direction, "sound", tempo=str(int(bpm)))

        m_notes = notes_by_m.get(mi, [])
        m_chords = chords_by_m.get(mi, {})

        # Group notes by offset
        by_offset: dict[int, list[tuple[int, int, bool, bool]]] = {}
        for off, dur, midi, t_start, t_stop in m_notes:
            by_offset.setdefault(off, []).append((dur, midi, t_start, t_stop))

        # All event positions (notes + chords)
        event_offsets = sorted(set(by_offset.keys()) | set(m_chords.keys()))

        # Pre-compute beaming for this measure
        voice_events: list[tuple[int, int]] = []
        for v_off in sorted(by_offset.keys()):
            nlist_v = by_offset[v_off]
            v_dur = min(nlist_v[0][0], divs_per_measure - v_off)
            v_dur = _snap_duration(v_dur, valid)
            if v_dur > divs_per_measure - v_off:
                v_dur = max(1, divs_per_measure - v_off)
            voice_events.append((v_off, v_dur))
        beam_map = _compute_beaming(voice_events, divs_per_beat, type_map, valid)

        cursor = 0
        for off in event_offsets:
            if off < cursor:
                continue
            if off > cursor:
                _emit_rests_with_chords(measure, cursor, off - cursor, m_chords, type_map, valid)
                cursor = off

            if off in m_chords:
                _emit_harmony(measure, m_chords[off])

            if off in by_offset:
                nlist = by_offset[off]
                beams = beam_map.get(off)
                for i, (dur, midi, t_start, t_stop) in enumerate(nlist):
                    clamped = min(dur, divs_per_measure - off)
                    clamped = _snap_duration(clamped, valid)
                    if clamped > divs_per_measure - off:
                        clamped = max(1, divs_per_measure - off)
                    _emit_note(measure, midi, clamped, type_map, valid,
                               is_chord=(i > 0), tie_start=t_start, tie_stop=t_stop,
                               beams=beams, staff=1 if midi >= 60 else 2)
                first_dur = min(nlist[0][0], divs_per_measure - off)
                first_dur = _snap_duration(first_dur, valid)
                cursor = min(off + first_dur, divs_per_measure)

        if cursor < divs_per_measure:
            if cursor in m_chords and cursor not in by_offset:
                _emit_harmony(measure, m_chords[cursor])
            _emit_rests_with_chords(measure, cursor, divs_per_measure - cursor, m_chords, type_map, valid)

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
