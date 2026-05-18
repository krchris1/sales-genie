"""
Commercial detection prototype.

Reads an audio file (WAV/FLAC/OGG via libsndfile) and emits a JSON timeline
describing where the detector thinks ads are, plus a list of mute/unmute
events that can later be sent to a TV (Roku ECP, Fire TV ADB, etc.).

Heuristic, audio-only. See README in repo for the path to a real classifier.
"""

import argparse
import json
import sys

import numpy as np
import soundfile as sf


TARGET_SR = 16_000
FRAME_MS = 20
HOP_MS = 10
SILENCE_MIN_MS = 250
AD_LENGTHS_SEC = (15, 30, 60)
AD_LENGTH_TOLERANCE_SEC = 2.5
MIN_SEGMENT_SEC = 0.5
AD_POD_MIN_SEC = 45
AD_POD_MAX_SEC = 240


def load_mono(path: str) -> tuple[np.ndarray, int]:
    audio, sr = sf.read(path, always_2d=False)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        # Naive linear resample. Fine here because downstream features are
        # frame-RMS energy, not anything pitch-sensitive.
        n_out = int(round(len(audio) * TARGET_SR / sr))
        audio = np.interp(
            np.linspace(0, len(audio) - 1, n_out),
            np.arange(len(audio)),
            audio,
        )
        sr = TARGET_SR
    return audio.astype(np.float32), sr


def frame_rms_db(audio: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    frame = int(sr * FRAME_MS / 1000)
    hop = int(sr * HOP_MS / 1000)
    n = max(0, 1 + (len(audio) - frame) // hop)
    rms = np.empty(n, dtype=np.float32)
    for i in range(n):
        seg = audio[i * hop : i * hop + frame]
        rms[i] = np.sqrt(float(np.mean(seg * seg)) + 1e-12)
    db = 20.0 * np.log10(np.maximum(rms, 1e-7))
    return db, hop


def find_silences(db: np.ndarray, hop: int, sr: int) -> tuple[list[tuple[float, float]], float]:
    # Adaptive threshold so the detector survives recordings at different gains.
    sorted_db = np.sort(db)
    loud_ref = float(np.mean(sorted_db[int(len(db) * 0.4):]))
    threshold = loud_ref - 18.0

    silent = db < threshold
    min_run = int(SILENCE_MIN_MS / HOP_MS)

    runs: list[tuple[float, float]] = []
    in_run = False
    start = 0
    for i, s in enumerate(silent):
        if s and not in_run:
            in_run, start = True, i
        elif not s and in_run:
            in_run = False
            if i - start >= min_run:
                runs.append((start * hop / sr, i * hop / sr))
    if in_run and len(silent) - start >= min_run:
        runs.append((start * hop / sr, len(silent) * hop / sr))
    return runs, threshold


def segments_between(silences: list[tuple[float, float]], total: float) -> list[tuple[float, float]]:
    if not silences:
        return [(0.0, total)] if total > MIN_SEGMENT_SEC else []
    out: list[tuple[float, float]] = []
    cursor = 0.0
    for s, e in silences:
        if s - cursor > MIN_SEGMENT_SEC:
            out.append((cursor, s))
        cursor = e
    if total - cursor > MIN_SEGMENT_SEC:
        out.append((cursor, total))
    return out


def _is_ad_length(dur: float) -> bool:
    return any(abs(dur - L) <= AD_LENGTH_TOLERANCE_SEC for L in AD_LENGTHS_SEC)


def classify(segs: list[tuple[float, float]]) -> list[str]:
    # A lone ad-length segment is ambiguous; promote to "ad" only when 2+ land
    # back-to-back AND the run's total duration matches a real break window.
    # Otherwise a show act that happens to be 60s would also look like an ad.
    flags = [_is_ad_length(e - s) for s, e in segs]
    labels = ["show"] * len(segs)
    i = 0
    while i < len(segs):
        if flags[i]:
            j = i
            while j < len(segs) and flags[j]:
                j += 1
            run_dur = segs[j - 1][1] - segs[i][0]
            if j - i >= 2 and AD_POD_MIN_SEC <= run_dur <= AD_POD_MAX_SEC:
                for k in range(i, j):
                    labels[k] = "ad"
            elif j - i == 1:
                labels[i] = "maybe_ad"
            i = j
        else:
            i += 1
    return labels


def mute_events(segs: list[tuple[float, float]], labels: list[str]) -> list[dict]:
    events: list[dict] = []
    state = "unmute"
    for (s, _), label in zip(segs, labels):
        target = "mute" if label == "ad" else "unmute"
        if target != state:
            events.append({"t": round(s, 2), "action": target})
            state = target
    return events


def cmd_detect(args: argparse.Namespace) -> None:
    audio, sr = load_mono(args.audio)
    db, hop = frame_rms_db(audio, sr)
    silences, threshold = find_silences(db, hop, sr)
    total = len(audio) / sr
    segs = segments_between(silences, total)
    labels = classify(segs)
    result = {
        "duration_sec": round(total, 2),
        "silence_threshold_db": round(threshold, 2),
        "silences": [{"start": round(s, 2), "end": round(e, 2)} for s, e in silences],
        "segments": [
            {"start": round(s, 2), "end": round(e, 2), "duration": round(e - s, 2), "label": label}
            for (s, e), label in zip(segs, labels)
        ],
        "mute_events": mute_events(segs, labels),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


def cmd_synth(args: argparse.Namespace) -> None:
    sr = TARGET_SR
    rng = np.random.default_rng(0)

    def show(dur: float) -> np.ndarray:
        n = int(dur * sr)
        x = rng.standard_normal(n).astype(np.float32) * 0.08
        env = 0.5 + 0.5 * np.sin(2 * np.pi * np.arange(n) / sr * 2.0)
        x *= env.astype(np.float32)
        for _ in range(int(dur / 4)):
            t = int(rng.integers(0, max(1, n - int(0.1 * sr))))
            x[t : t + int(0.08 * sr)] *= 0.02
        return x

    def gap(dur: float) -> np.ndarray:
        n = int(dur * sr)
        return rng.standard_normal(n).astype(np.float32) * 0.0005

    def ad(dur: float) -> np.ndarray:
        n = int(dur * sr)
        t = np.arange(n) / sr
        x = 0.25 * np.sin(2 * np.pi * 440 * t) + 0.15 * np.sin(2 * np.pi * 660 * t)
        x += rng.standard_normal(n) * 0.08
        return x.astype(np.float32)

    parts = [
        show(90),
        gap(0.5),
        ad(30), gap(0.5),
        ad(30), gap(0.5),
        ad(15), gap(0.5),
        show(120),
    ]
    audio = np.concatenate(parts)
    audio = audio / max(1e-6, float(np.max(np.abs(audio)))) * 0.9
    sf.write(args.out, audio, sr)

    boundaries = []
    t = 0.0
    for label, dur in [("show", 90), ("gap", 0.5), ("ad", 30), ("gap", 0.5),
                       ("ad", 30), ("gap", 0.5), ("ad", 15), ("gap", 0.5), ("show", 120)]:
        boundaries.append((label, round(t, 2), round(t + dur, 2)))
        t += dur
    print(f"Wrote {args.out} ({len(audio)/sr:.1f}s)")
    print("Ground truth:")
    for label, s, e in boundaries:
        print(f"  {label:5s} {s:7.2f} -> {e:7.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Commercial detection prototype")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_det = sub.add_parser("detect", help="Analyze an audio file")
    p_det.add_argument("audio", help="Path to WAV/FLAC/OGG audio")
    p_det.set_defaults(fn=cmd_detect)

    p_synth = sub.add_parser("synth", help="Generate a synthetic show+ads+show test file")
    p_synth.add_argument("out", help="Output WAV path")
    p_synth.set_defaults(fn=cmd_synth)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
