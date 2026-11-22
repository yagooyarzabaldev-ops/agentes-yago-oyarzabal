"""Large ASS/SRT captions: 2–4-word blocks, active word, no internal blank gaps.

Words must be aligned to the FINAL edited audio. This tool performs no semantic
correction. It measures the supplied font, rejects over-wide two-line blocks and
keeps each active word until the next word starts (last word until block end).
"""
import argparse
from pathlib import Path

from common import digest, number, output_path, read_json, write_json


def timecode(t, ass=False):
    scale = 100 if ass else 1000
    tick = round(t * scale)
    seconds, fraction = divmod(tick, scale)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02}:{s:02}.{fraction:02}" if ass else f"{h:02}:{m:02}:{s:02},{fraction:03}"


def group_words(words, duration):
    groups, batch = [], []
    for w in words:
        batch.append(w)
        if len(batch) >= 3 or (len(batch) >= 2 and w["w"].endswith((",", ".", "?", "!"))):
            groups.append(batch)
            batch = []
    if batch:
        if len(batch) == 1 and groups and len(groups[-1]) < 4:
            groups[-1].extend(batch)
        else:
            groups.append(batch)
    result = []
    for i, group in enumerate(groups):
        limit = groups[i+1][0]["start"] if i+1 < len(groups) else duration
        end = min(limit, group[-1]["end"] + .12)
        result.append({"start": group[0]["start"], "end": end, "words": group})
    return result


def validate_blocks(blocks):
    if not blocks:
        raise ValueError("No caption blocks")
    previous_end = 0
    for b in blocks:
        a, end = number(b["start"], "block start"), number(b["end"], "block end")
        if a < previous_end - 1e-6 or end <= a or not 2 <= len(b["words"]) <= 4:
            raise ValueError("Blocks must be ordered, disjoint, positive and contain 2–4 words")
        previous_end = end
        starts = [number(w["start"], "word start") for w in b["words"]]
        if starts[0] < a - 1e-6 or starts[-1] >= end or any(x >= y for x, y in zip(starts, starts[1:])):
            raise ValueError("Word starts must increase within the block")
        for w in b["words"]:
            if not str(w["w"]).strip() or "\n" in w["w"]:
                raise ValueError("Words cannot be empty or contain newlines")


def continuous_spans(block):
    words = block["words"]
    spans = [(block["start"] if i == 0 else w["start"],
              words[i+1]["start"] if i+1 < len(words) else block["end"])
             for i, w in enumerate(words)]
    if any(round(a * 100) >= round(b * 100) for a, b in spans):
        raise ValueError("An active-word interval disappears at ASS centisecond precision")
    return spans


def layout(words, font, maximum):
    width = lambda values: font.getlength(" ".join(values))
    if width(words) <= maximum:
        return len(words)
    split = min(range(1, len(words)), key=lambda i: max(width(words[:i]), width(words[i:])))
    if max(width(words[:split]), width(words[split:])) > maximum:
        raise ValueError("Caption exceeds two lines: regroup words or choose a measured font size")
    return split


def render(args):
    from PIL import ImageFont
    source = Path(args.blocks or args.words).resolve()
    data = read_json(source)
    blocks = data if args.blocks else group_words(data["words"], number(data["duration_seconds"], "duration"))
    validate_blocks(blocks)
    out = output_path(args.output, args.overwrite)
    srt = output_path(out.with_suffix(".srt"), args.overwrite)
    report = output_path(out.with_suffix(".json"), args.overwrite)
    if source in {out, srt, report} or out.suffix.lower() != ".ass":
        raise ValueError("Use a distinct .ass output basename")
    font = ImageFont.truetype(args.font, args.font_size)
    maximum = args.width - 2 * (args.side + args.outline + args.shadow)
    bottom = args.height - args.bottom - args.outline - args.shadow
    if maximum <= 0 or bottom <= 2 * args.font_size:
        raise ValueError("Invalid safe area")
    if any(c in args.font_name for c in ",\n\r"):
        raise ValueError("Invalid ASS font name")
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {args.width}
PlayResY: {args.height}
ScaledBorderAndShadow: yes
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{args.font_name},{args.font_size},&H00EDF6FF,&H00EDF6FF,&H00100B0A,&HA0100B0A,1,0,0,0,100,100,0,0,1,{args.outline},{args.shadow},2,{args.side},{args.side},{args.bottom},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events, cues, coverage = [], [], []
    for i, b in enumerate(blocks):
        words = [w["w"].upper().replace("\\", "＼").replace("{", "｛").replace("}", "｝") for w in b["words"]]
        split = layout(words, font, maximum)
        spans = continuous_spans(b)
        for active, (start, end) in enumerate(spans):
            text = ""
            for k, word in enumerate(words):
                if k:
                    text += "\\N" if k == split else " "
                text += ("{\\c&HC0E291&}" if k == active else "{\\c&HEDF6FF&}") + word
            events.append(f"Dialogue: 2,{timecode(start, True)},{timecode(end, True)},Caption,,0,0,0,,{{\\an2\\pos({args.width//2},{bottom})}}{text}\n")
        plain = " ".join(w["w"] for w in b["words"][:split])
        if split < len(words):
            plain += "\n" + " ".join(w["w"] for w in b["words"][split:])
        cues.append(f"{i+1}\n{timecode(b['start'])} --> {timecode(b['end'])}\n{plain}\n")
        coverage.append({"start": b["start"], "end": b["end"], "active_spans": spans, "lines": 1 if split == len(words) else 2})
    out.write_text(header + "".join(events), encoding="utf-8-sig")
    srt.write_text("\n".join(cues), encoding="utf-8")
    write_json(report, {"source_sha256": digest(source), "font_file_sha256": digest(args.font), "font_name": args.font_name,
                        "font_size": args.font_size, "blocks": coverage, "internal_gaps": 0,
                        "ass_sha256": digest(out), "review_status": "layout measured; exported video must be inspected"})
    print(f"{len(blocks)} continuous blocks / {len(events)} active-word events")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--blocks"); g.add_argument("--words")
    p.add_argument("--output", required=True); p.add_argument("--font", required=True)
    p.add_argument("--font-name", default="Segoe UI Black"); p.add_argument("--font-size", type=int, default=100)
    p.add_argument("--width", type=int, default=1080); p.add_argument("--height", type=int, default=1920)
    p.add_argument("--side", type=int, default=95); p.add_argument("--bottom", type=int, default=370)
    p.add_argument("--outline", type=int, default=6); p.add_argument("--shadow", type=int, default=3)
    p.add_argument("--overwrite", action="store_true")
    render(p.parse_args())


if __name__ == "__main__":
    main()
