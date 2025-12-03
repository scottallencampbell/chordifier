import os
import sys
import numpy as np
from dataclasses import dataclass

# Configure librosa to prefer audioread backend (no system libraries needed)
# This is important for serverless environments
os.environ.setdefault("LIBROSA_CACHE_DIR", "/tmp/librosa_cache")

try:
    import librosa as lr
    import librosa.display as lrd
except ImportError as e:
    print(f"CRITICAL: Failed to import librosa: {e}")
    raise
except Exception as e:
    print(f"CRITICAL: Unexpected error importing librosa: {e}")
    raise


@dataclass
class Chord:
    tonic: str
    kind: str
    start: float = 0.0
    duration: float = 0.0


hop_length = 512
magnitude_threshold = 0.25
note_names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]

major_chord = "100010010000"
minor_chord = "100100010000"
sus2_chord = "100001010000"
sus4_chord = "101000010000"
major_7th_chord = "100010010001"
minor_7th_chord = "100100010001"
power_chord = "100000010000"


def rotate(l, n):
    return l[n:] + l[:n]


def build_chord_map(base):
    chord_amp = {}

    for i, note in enumerate(note_names):
        chord_in_key = rotate(base, -i)
        chord_amp[chord_in_key] = note

    return chord_amp


def to_stopwatch(time_in_seconds):
    minutes = time_in_seconds // 60
    seconds = time_in_seconds % 60
    milliseconds = seconds * 1000 % 1000
    return "%02d:%02d.%03d" % (minutes, seconds, milliseconds)


def classify_chord(notes):
    # has to be a power chord at least
    if len(notes) < 2:
        return None

    # get outta here, no jazz chords
    if len(notes) > 6:
        return None

    bits = 0

    for note in list(notes)[:4]:
        bits = bits + 2 ** (11 - note)

    mask = bin(bits)[2:].zfill(12)

    if mask in major_7th_chords:
        return Chord(major_7th_chords[mask], "7th")
    # elif mask in minor_7th_chords:
    #    return Chord(minor_7th_chords[mask], 'minor 7th')
    elif mask in sus2_chords:
        return Chord(sus2_chords[mask], "sus2")
    elif mask in sus4_chords:
        return Chord(sus4_chords[mask], "sus4")
    elif mask in major_chords:
        return Chord(major_chords[mask], "major")
    elif mask in minor_chords:
        return Chord(minor_chords[mask], "minor")
    # elif mask in power_chords:
    #    return Chord(power_chords[mask], 'power')
    else:
        return None


def collapse_chord_progression(chords):
    collapsed = [chords[0]]

    for i, chord in enumerate(chords[1:]):
        last_chord = chords[i - 1]

        if chord.tonic == last_chord.tonic and chord.kind == last_chord.kind:
            continue

        collapsed.append(chord)

    # determine the timespan of each chord
    for i, chord in enumerate(chords[:-1]):
        next_chord = chords[i + 1]
        chord.duration = next_chord.start - chord.start

    return collapsed


def get_raw_chord_progression(chroma, sr):
    chords = []
    from_sec = 0
    to_sec = len(chroma[0]) * hop_length / sr
    last_chord = Chord("", "")
    from_segment = int(from_sec * sr / hop_length)
    to_segment = int(to_sec * sr / hop_length)

    for segment in range(from_segment, to_segment):
        magnitudes = chroma[:, segment]
        sorted_notes = sorted(range(len(magnitudes)), key=lambda i: -magnitudes[i])
        sorted_magnitudes = []
        notes = []

        # build an array of the hightest magnitudes
        for i, note in enumerate(note_names):
            sorted_magnitudes.append(magnitudes[sorted_notes[i]])

        # build an array of notes above the given magnitude threshold
        for i, note in enumerate(note_names):
            if sorted_magnitudes[i] >= magnitude_threshold:
                notes.append(sorted_notes[i])

        chord = classify_chord(notes)

        if chord != None and not (
            last_chord.tonic == chord.tonic and last_chord.kind == chord.kind
        ):
            chord.start = round((segment * hop_length / sr), 3)
            chords.append(chord)
            last_chord = chord

    collapsed = collapse_chord_progression(chords)

    return collapsed


def refine_chord_progression(chords):
    refined = []

    for i, chord in enumerate(chords[:-1]):
        next_chord = chords[i + 1]

        # remove any short 7ths that come before longer majors
        if (
            chord.tonic == next_chord.tonic
            and chord.kind == "7th"
            and next_chord.kind == "major"
            and chord.duration < next_chord.duration
        ):
            continue

        # remove any short minor 7ths that come before longer minors
        if (
            chord.tonic == next_chord.tonic
            and chord.kind == "minor 7th"
            and next_chord.kind == "minor"
            and chord.duration < next_chord.duration
        ):
            continue

        refined.append(chord)

    collapsed = collapse_chord_progression(refined)
    return collapsed


def analyze(audio_path):
    # Use audioread backend which doesn't require system libraries
    # This is important for serverless environments like Vercel
    y, sr = lr.load(audio_path, sr=None, mono=True)
    # split track into harmonic and percussive in order to isolate true tonal frequencies
    y_harm, y_perc = lr.effects.hpss(y)
    # add margin to ^^^^
    # add filters?

    # cqt seems to work better than fourier
    chroma_cq = lr.feature.chroma_cqt(y=y_harm, sr=sr, hop_length=hop_length)
    # lr.display.specshow(chroma_cq, y_axis='chroma', x_axis='time')

    raw = get_raw_chord_progression(chroma_cq, sr)
    refined = refine_chord_progression(raw)

    return refined


major_chords = build_chord_map(major_chord)
minor_chords = build_chord_map(minor_chord)
major_7th_chords = build_chord_map(major_7th_chord)
minor_7th_chords = build_chord_map(minor_7th_chord)
sus2_chords = build_chord_map(sus2_chord)
sus4_chords = build_chord_map(sus4_chord)
power_chords = build_chord_map(power_chord)
