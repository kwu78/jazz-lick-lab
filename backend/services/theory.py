import re

# Pitch-class map: note name -> semitone offset from C
PITCH_CLASS = {
    "C": 0, "C#": 1, "Db": 1,
    "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "E#": 5,
    "F": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8,
    "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11, "B#": 0,
}

# Canonical sharp/flat spelling for transposed roots (prefer flats for jazz)
SEMITONE_TO_NAME = [
    "C", "Db", "D", "Eb", "E", "F",
    "F#", "G", "Ab", "A", "Bb", "B",
]

# Regex: root is a capital letter optionally followed by # or b
_ROOT_RE = re.compile(r"^([A-G][#b]?)")


def parse_key(key: str) -> int:
    """Return semitone value (0-11) for a key string like 'C', 'F#', 'Bb'.

    Raises ValueError if the key is not recognized.
    """
    if key not in PITCH_CLASS:
        raise ValueError(f"Unknown key: {key!r}")
    return PITCH_CLASS[key]


def semitone_interval(source_key: str, target_key: str) -> int:
    """Return the signed semitone interval from source to target (0-11)."""
    return (parse_key(target_key) - parse_key(source_key)) % 12


def parse_chord_root(symbol: str) -> str | None:
    """Extract the root note from a chord symbol like 'Dm7', 'F#7', 'Bbmaj7'.

    Returns None if no valid root is found.
    """
    m = _ROOT_RE.match(symbol)
    return m.group(1) if m else None


def transpose_chord_symbol(symbol: str, interval: int) -> str:
    """Transpose a chord symbol by a semitone interval.

    Keeps quality/extensions unchanged; only the root is transposed.
    """
    m = _ROOT_RE.match(symbol)
    if not m:
        return symbol  # can't parse root, return as-is

    old_root = m.group(1)
    old_semitone = PITCH_CLASS.get(old_root)
    if old_semitone is None:
        return symbol

    new_semitone = (old_semitone + interval) % 12
    new_root = SEMITONE_TO_NAME[new_semitone]
    return new_root + symbol[len(old_root):]
