"""Recorded-voice EDL, local energy/VAD inspection and optional offline ASR.

Times in a recipe are relative to the first decoded audio sample, NOT video PTS.
The source offset is measured and added only to provenance timestamps. Replacements
reuse an explicitly selected donor interval; they never synthesize or accelerate speech.
Editorial word boundaries and acceptable phonetic joins still require review.
"""
import argparse
import os
from pathlib import Path
import re

from common import digest, input_file, number, output_path, probe, read_json, run, stream, write_json


def decode(source, rate, channels, ffmpeg="ffmpeg"):
    import numpy as np
    raw = run([ffmpeg, "-v", "error", "-i", source, "-vn", "-ac", channels,
               "-ar", rate, "-f", "f32le", "-"])
    return np.frombuffer(raw, dtype="<f4").reshape(-1, channels).copy()


def interval(item, name):
    a, b = (number(v, name) for v in item)
    if b <= a:
        raise ValueError(f"Empty/reversed interval: {name}")
    return a, b


def build_operations(recipe):
    """Subtract reviewed silence interiors, then splice whole donor intervals.

    Gap detection does not choose edits by itself: `speech` must be explicitly supplied.
    `room_tone` inserts the selected real ambience between each retained sentence range.
    Replacements crossing a cut fail instead of silently duplicating part of a word.
    """
    if "operations" in recipe:
        if not recipe["operations"]:
            raise ValueError("Empty operations")
        return recipe["operations"], []
    ranges = [interval(v, "ranges") for v in recipe["ranges"]]
    if any(b > c for (_, b), (c, _) in zip(ranges, ranges[1:])):
        raise ValueError("Selected ranges must be ordered and disjoint")
    speech = [interval((v["start"], v["end"]), "speech") for v in recipe.get("speech", [])]
    if any(b > c for (_, b), (c, _) in zip(speech, speech[1:])):
        raise ValueError("Speech intervals must be ordered and disjoint")
    threshold = number(recipe.get("gap_threshold", .30), "gap_threshold")
    pad = number(recipe.get("speech_padding", .09), "speech_padding")
    gaps = [(a[1] + pad, b[0] - pad) for a, b in zip(speech, speech[1:])
            if b[0] - a[1] > max(threshold, 2 * pad)]
    reps = sorted(recipe.get("replacements", []), key=lambda r: r["target"][0])
    for r in reps:
        interval(r["target"], "replacement target")
        interval(r["donor"], "replacement donor")
    if any(a["target"][1] > b["target"][0] for a, b in zip(reps, reps[1:])):
        raise ValueError("Replacement targets overlap")
    operations, used = [], set()
    for index, (start, end) in enumerate(ranges):
        spans = [(start, end)]
        for gs, ge in gaps:
            result = []
            for a, b in spans:
                if ge <= a or gs >= b:
                    result.append((a, b))
                else:
                    if a < gs:
                        result.append((a, min(gs, b)))
                    if ge < b:
                        result.append((max(ge, a), b))
            spans = result
        if not spans:
            continue
        if index and recipe.get("room_tone"):
            a, b = interval(recipe["room_tone"], "room_tone")
            operations.append({"kind": "pause", "start": a, "end": b})
        for a, b in spans:
            cursor = a
            for ri, rep in enumerate(reps):
                rs, re_ = rep["target"]
                if re_ <= a or rs >= b:
                    continue
                if rs < a or re_ > b:
                    raise ValueError("Replacement target intersects a removed interval; review the cuts")
                if cursor < rs:
                    operations.append({"kind": "source", "start": cursor, "end": rs})
                operations.append({"kind": "replacement", "start": rep["donor"][0],
                                   "end": rep["donor"][1], "visual_start": rs, "visual_end": re_})
                used.add(ri)
                cursor = re_
            if cursor < b:
                operations.append({"kind": "source", "start": cursor, "end": b})
    if len(used) != len(reps):
        raise ValueError("A replacement target is outside the retained ranges")
    if not operations:
        raise ValueError("The recipe produces no audio")
    return operations, gaps


def splice(audio, operations, rate, offset, fade_ms=5):
    import numpy as np
    chunks, edl, position = [], [], 0
    for op in operations:
        if op["kind"] not in {"source", "replacement", "pause"}:
            raise ValueError("Unknown EDL operation")
        a, b = interval((op["start"], op["end"]), "operation")
        ia, ib = round(a * rate), round(b * rate)
        if ia < 0 or ib > len(audio) or ib <= ia:
            raise ValueError("EDL interval is outside decoded audio or shorter than a sample")
        chunk = audio[ia:ib].copy()
        fade = min(round(number(fade_ms, "fade_ms") * rate / 1000), len(chunk) // 2)
        if fade:
            chunk[:fade] *= np.linspace(0, 1, fade)[:, None]
            chunk[-fade:] *= np.linspace(1, 0, fade)[:, None]
        va, vb = interval((op.get("visual_start", a), op.get("visual_end", b)), "visual source")
        edl.append({"kind": op["kind"], "source_start": va + offset, "source_end": vb + offset,
                    "audio_source_start": ia / rate + offset, "audio_source_end": ib / rate + offset,
                    "timeline_start": position / rate, "timeline_end": (position + len(chunk)) / rate,
                    "sample_start": position, "sample_end": position + len(chunk)})
        position += len(chunk)
        chunks.append(chunk)
    return np.concatenate(chunks).astype("<f4"), edl


def render(args):
    recipe = read_json(args.recipe)
    source = input_file(Path(args.recipe).resolve().parent / recipe["source"])
    out = output_path(args.output, args.overwrite)
    report = output_path(args.report, args.overwrite)
    if out == source or report in {source, out, Path(args.recipe).resolve()}:
        raise ValueError("Inputs and outputs must be distinct")
    info = probe(source, args.ffprobe)
    offset = float(recipe.get("audio_start_offset", stream(info, "audio").get("start_time", 0)))
    operations, gaps = build_operations(recipe)
    audio = decode(source, args.rate, 2, args.ffmpeg)
    joined, edl = splice(audio, operations, args.rate, offset, args.fade_ms)
    filters = f"highpass=f={args.highpass},loudnorm=I={args.lufs}:TP={args.peak}:LRA=7:print_format=json"
    run([args.ffmpeg, "-hide_banner", "-y", "-f", "f32le", "-ar", args.rate, "-ac", 2, "-i", "-",
         "-af", filters, "-ar", args.rate, "-c:a", "pcm_s24le", out],
        data=joined.tobytes(), log=out.with_suffix(".log"))
    write_json(report, {"source": str(source), "source_sha256": digest(source), "source_audio_start_offset": offset,
                       "clock": "recipe=decoded first sample; source timestamps=container PTS",
                       "operations": edl, "removed_silence_interiors": gaps, "duration_seconds": len(joined) / args.rate,
                       "speech_speed": 1.0, "synthetic_audio": False, "perceptual_listening": False,
                       "asr_status": "pending", "output_sha256": digest(out), "output_info": probe(out, args.ffprobe)})
    print(f"Rendered {len(joined) / args.rate:.6f}s / {len(edl)} operations; review joins and final ASR.")


def analyze(args):
    import numpy as np
    out = output_path(args.output, args.overwrite)
    audio = decode(input_file(args.source), 16000, 1, args.ffmpeg).ravel()
    count = len(audio) // 160
    if not count:
        raise ValueError("Audio shorter than one 10ms window")
    db = 20 * np.log10(np.maximum(np.sqrt(np.mean(audio[:count*160].reshape(-1, 160) ** 2, axis=1)), 1e-8))
    spans, start = [], None
    for i, low in enumerate(list(db < args.threshold) + [False]):
        if low and start is None:
            start = i
        elif not low and start is not None:
            if (i - start) * .01 >= args.minimum:
                spans.append({"start": start * .01, "end": i * .01})
            start = None
    result = {"clock": "decoded first sample", "low_energy": spans, "threshold_dbfs": args.threshold,
              "rms_quantiles_db": {str(q): float(np.quantile(db, q)) for q in [.05, .1, .5, .9]},
              "automatic_cuts_applied": False}
    if args.vad:
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        from faster_whisper.vad import get_speech_timestamps, VadOptions
        speech = get_speech_timestamps(audio, VadOptions(threshold=.35, min_speech_duration_ms=100,
                                      min_silence_duration_ms=150, speech_pad_ms=35), sampling_rate=16000)
        result["speech"] = [{"start": s["start"] / 16000, "end": s["end"] / 16000} for s in speech]
    write_json(out, result)
    print(f"{len(spans)} low-energy intervals proposed; no audio changed.")


def transcribe(args):
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    from faster_whisper import WhisperModel
    model_path = Path(args.model).resolve()
    if not model_path.is_dir():
        raise ValueError("--model must be an existing local model directory")
    out = output_path(args.output, args.overwrite)
    audio = decode(input_file(args.source), 16000, 1, args.ffmpeg).ravel()
    model = WhisperModel(str(model_path), device="cpu", compute_type="int8", cpu_threads=args.threads, local_files_only=True)
    segments, _ = model.transcribe(audio, language=args.language, beam_size=5, word_timestamps=True,
                                   vad_filter=False, condition_on_previous_text=False)
    words = [{"w": w.word.strip(), "start": w.start, "end": w.end, "probability": w.probability}
             for s in segments for w in (s.words or [])]
    text = " ".join(w["w"] for w in words)
    checks = [{"pattern": p, "expected_present": True, "ok": bool(re.search(p, text, re.I))} for p in args.expect]
    checks += [{"pattern": p, "expected_present": False, "ok": not bool(re.search(p, text, re.I))} for p in args.reject]
    write_json(out, {"words": words, "duration_seconds": len(audio) / 16000,
                     "checks": checks, "source_sha256": digest(args.source), "perceptual_listening": False})
    print(f"Local ASR: {len(words)} words; {len(checks)} explicit lexical checks.")
    if not all(c["ok"] for c in checks):
        raise SystemExit("ASR checks failed; inspect the saved report and the audio joins.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("render", help="Render a reviewed EDL using real recorded intervals")
    r.add_argument("--recipe", required=True); r.add_argument("--output", required=True); r.add_argument("--report", required=True)
    r.add_argument("--rate", type=int, default=48000); r.add_argument("--fade-ms", type=float, default=5)
    r.add_argument("--highpass", type=float, default=70); r.add_argument("--lufs", type=float, default=-16)
    r.add_argument("--peak", type=float, default=-3); r.add_argument("--ffprobe", default="ffprobe")
    r.set_defaults(action=render)
    a = sub.add_parser("analyze", help="Propose low-energy intervals; optional installed local Silero VAD")
    a.add_argument("--source", required=True); a.add_argument("--output", required=True)
    a.add_argument("--threshold", type=float, default=-35); a.add_argument("--minimum", type=float, default=.30)
    a.add_argument("--vad", action="store_true"); a.set_defaults(action=analyze)
    t = sub.add_parser("transcribe", help="Independent local ASR of the final edited WAV")
    t.add_argument("--source", required=True); t.add_argument("--output", required=True); t.add_argument("--model", required=True)
    t.add_argument("--language", default="es"); t.add_argument("--threads", type=int, default=4)
    t.add_argument("--expect", action="append", default=[]); t.add_argument("--reject", action="append", default=[])
    t.set_defaults(action=transcribe)
    for child in (r, a, t):
        child.add_argument("--ffmpeg", default="ffmpeg"); child.add_argument("--overwrite", action="store_true")
    args = p.parse_args()
    args.action(args)


if __name__ == "__main__":
    main()
