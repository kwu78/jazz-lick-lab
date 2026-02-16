import json
import os
import uuid
import zipfile
from datetime import datetime, timezone

from schemas.practice_pack import KeyEntry, PracticePackArtifact
from schemas.transcription import NoteEvent, ChordEvent
from services.musicxml import generate_musicxml
from services.theory import (
    SEMITONE_TO_NAME,
    parse_chord_root,
    semitone_interval,
    transpose_chord_symbol,
)


ALL_KEYS = list(SEMITONE_TO_NAME)


def build_practice_pack(
    job_id: str,
    selection_id: str,
    notes: list[NoteEvent],
    chords: list[ChordEvent],
    offset_sec: float,
    data_dir: str,
    target_keys: list[str] | None = None,
    include_original: bool = True,
    bpm: float = 120.0,
    time_signature: str = "4/4",
) -> PracticePackArtifact:
    """Generate per-key JSON files, a manifest, and a ZIP archive."""

    # Infer source key from first chord root
    if not chords:
        source_key = "C"
    else:
        root = parse_chord_root(chords[0].symbol)
        source_key = root if root else "C"

    # Determine which keys to include
    if target_keys is None:
        keys_to_generate = list(ALL_KEYS)
    else:
        keys_to_generate = list(target_keys)

    # Ensure original key is present when include_original is True
    if include_original and source_key not in keys_to_generate:
        keys_to_generate.insert(0, source_key)

    artifact_id = str(uuid.uuid4())
    pack_dir = os.path.join(data_dir, "practice_packs", job_id, artifact_id)
    os.makedirs(pack_dir, exist_ok=True)

    key_entries: list[KeyEntry] = []

    for key in keys_to_generate:
        interval = semitone_interval(source_key, key)

        # Transpose notes (apply display-time offset)
        transposed_notes = [
            NoteEvent(
                pitch_midi=n.pitch_midi + interval,
                start_sec=n.start_sec - offset_sec,
                duration_sec=n.duration_sec,
            )
            for n in notes
        ]

        # Transpose chords (apply display-time offset)
        transposed_chords = [
            ChordEvent(
                symbol=transpose_chord_symbol(c.symbol, interval),
                start_sec=c.start_sec - offset_sec,
                end_sec=(c.end_sec - offset_sec) if c.end_sec is not None else None,
            )
            for c in chords
        ]

        safe_key = key.replace("#", "sharp").replace("b", "flat")
        file_name = f"{safe_key}.json"
        musicxml_file_name = f"{safe_key}.musicxml"

        entry = KeyEntry(
            key=key,
            interval_semitones=interval,
            notes=transposed_notes,
            chords=transposed_chords,
            file_name=file_name,
            musicxml_file_name=musicxml_file_name,
        )
        key_entries.append(entry)

        # Write per-key JSON file
        file_path = os.path.join(pack_dir, file_name)
        with open(file_path, "w") as f:
            json.dump(entry.model_dump(), f, indent=2)

        # Write per-key MusicXML file
        mxml_str = generate_musicxml(
            transposed_notes, transposed_chords,
            bpm=bpm, time_signature=time_signature,
        )
        mxml_path = os.path.join(pack_dir, musicxml_file_name)
        with open(mxml_path, "w", encoding="utf-8") as f:
            f.write(mxml_str)

    # Write manifest
    manifest = {
        "artifact_id": artifact_id,
        "job_id": job_id,
        "selection_id": selection_id,
        "source_key": source_key,
        "keys": [e.model_dump() for e in key_entries],
    }
    manifest_path = os.path.join(pack_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Create ZIP archive
    zip_path = os.path.join(pack_dir, "practice_pack.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in key_entries:
            zf.write(os.path.join(pack_dir, entry.file_name), arcname=entry.file_name)
            zf.write(
                os.path.join(pack_dir, entry.musicxml_file_name),
                arcname=entry.musicxml_file_name,
            )
        zf.write(manifest_path, arcname="manifest.json")

    return PracticePackArtifact(
        artifact_id=artifact_id,
        job_id=job_id,
        selection_id=selection_id,
        source_key=source_key,
        keys_included=[e.key for e in key_entries],
        dir_path=pack_dir,
        zip_path=zip_path,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
