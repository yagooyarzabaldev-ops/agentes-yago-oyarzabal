"""2.4-second synthetic smoke; no personal capture, voice, images, models or network.

Requires existing FFmpeg/ffprobe, NumPy, Pillow, and an explicit installed font.
All generated media stay under .smoke/ (ignored by Git). Exercises a donor splice,
PTS provenance, four real alpha transitions, continuous ASS and unchanged AAC.
"""
import argparse
from pathlib import Path
import sys
import tempfile
import wave

from common import read_json, run, write_json
from voice import build_operations, splice
from captions import continuous_spans, validate_blocks
from assemble import validate_scenes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--font", required=True); p.add_argument("--font-name", default="Segoe UI Black")
    p.add_argument("--ffmpeg", default="ffmpeg"); p.add_argument("--ffprobe", default="ffprobe")
    args = p.parse_args()
    import numpy as np
    from PIL import Image
    base = Path(__file__).resolve().parent
    parent = base / ".smoke"
    parent.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="check-", dir=parent))
    rate = 48000
    signal = (.09*np.sin(2*np.pi*440*np.arange(3*rate)/rate)).astype("float32")
    with wave.open(str(work/"tone.wav"), "wb") as wav:
        wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(rate)
        wav.writeframes(np.column_stack([signal, signal]).__mul__(32767).astype("<i2").tobytes())
    recipe = {"source": "tone.wav", "audio_start_offset": .235708, "ranges": [[0, 1], [1, 2.2]],
              "replacements": [{"target": [.2, .4], "donor": [2.4, 2.7]}], "room_tone": [2.8, 2.9]}
    operations, _ = build_operations(recipe)
    joined, edl = splice(np.column_stack([signal, signal]), operations, rate, .235708)
    assert len(joined) == round(2.4*rate)
    assert abs(edl[1]["audio_source_start"] - 2.635708) < 1e-8
    assert all(a["sample_end"] == b["sample_start"] for a, b in zip(edl, edl[1:]))
    try:
        build_operations({"ranges": [[0, 1]], "speech": [{"start": 0, "end": .2}, {"start": .8, "end": 1}],
                          "replacements": [{"target": [.1, .5], "donor": [.8, 1]}]})
    except ValueError:
        pass
    else:
        raise AssertionError("A donor target crossing a removed silence was accepted")
    write_json(work/"recipe.json", recipe)
    run([sys.executable, base/"voice.py", "render", "--recipe", work/"recipe.json", "--output", work/"voice.wav",
         "--report", work/"edl.json", "--ffmpeg", args.ffmpeg, "--ffprobe", args.ffprobe])
    blocks = [{"start": 0, "end": 2.4, "words": [{"w": "Una", "start": 0, "end": .2},
               {"w": "prueba", "start": .5, "end": .8}, {"w": "local", "start": 1.1, "end": 2.3}]}]
    validate_blocks(blocks)
    assert continuous_spans(blocks[0]) == [(0, .5), (.5, 1.1), (1.1, 2.4)]
    write_json(work/"blocks.json", blocks)
    run([sys.executable, base/"captions.py", "--blocks", work/"blocks.json", "--output", work/"subtitles.ass",
         "--font", args.font, "--font-name", args.font_name, "--font-size", 32, "--width", 360, "--height", 640,
         "--side", 32, "--bottom", 110, "--outline", 2, "--shadow", 1])
    assert "0:00:00.00,0:00:00.50" in (work/"subtitles.ass").read_text(encoding="utf-8-sig")
    run([args.ffmpeg, "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=30:duration=3",
         "-c:v", "libx264", "-threads", 2, "-pix_fmt", "yuv420p", "-y", work/"test-source.mp4"])
    Image.new("RGB", (360, 640), "#91e2c0").save(work/"fixture.png")
    scenes = [{"kind": "capture", "file": "test-source.mp4", "start": 0, "end": .6, "crop": [360, 640, 0, 0]},
              {"kind": "image", "file": "fixture.png", "start": .6, "end": 1.2, "motion": "truck"},
              {"kind": "capture", "file": "test-source.mp4", "start": 1.2, "end": 1.8, "crop": [360, 640, 0, 0], "wide_crop": [360, 200, 0, 0], "wide_y": 170},
              {"kind": "clip", "file": "test-source.mp4", "start": 1.8, "end": 2.4}]
    assert validate_scenes(scenes, 30) == 72
    plan = {"format": {"width": 360, "height": 640, "fps": 30}, "audio": "voice.wav", "ass": "subtitles.ass",
            "scenes": scenes, "transitions": [{"at": t, "duration": .2, "type": k} for t, k in zip([.4, 1, 1.6, 2.2], ["wipe", "iris", "doors", "state"])]}
    write_json(work/"plan.json", plan)
    command = [sys.executable, base/"assemble.py", "--plan", work/"plan.json", "--ffmpeg", args.ffmpeg, "--ffprobe", args.ffprobe]
    run(command + ["--work", work/"render", "--output", work/"first.mp4"])
    run(command + ["--work", work/"recompose", "--output", work/"second.mp4", "--picture", work/"render/picture.mp4",
                   "--audio", work/"first.mp4", "--copy-audio"])
    def audio_hash(file):
        return run([args.ffmpeg, "-v", "error", "-i", file, "-map", "0:a:0", "-c", "copy", "-f", "hash", "-hash", "sha256", "-"]).decode().strip()
    assert audio_hash(work/"first.mp4") == audio_hash(work/"second.mp4")
    report = read_json(work/"second.json")
    assert report["full_decode"] == "passed"
    write_json(work/"result.json", {"ok": True, "seconds": 2.4, "frames": 72, "transitions": 4,
                                    "continuous_captions": True, "aac_identical": True,
                                    "source": "synthetic test patterns and tone; no real office or speech"})
    print(f"SMOKE OK: {work / 'result.json'}")


if __name__ == "__main__":
    main()
