"""Small explicit-timeline compositor extracted from the direct-office reel.

Supports reviewed capture crops, a wide view over its blurred source, animated
image inserts, four visible cut covers, alpha callouts and ASS captions. It does
not capture the office, invent states, align speech, select crops or mix music.
An existing picture can be reused when only captions/callouts change; AAC can be
copied from a previous export. All source paths are relative to the plan JSON.
"""
import argparse
from pathlib import Path
import shutil

from common import digest, input_file, number, output_path, probe, read_json, resolve, run, stream, write_json


def validate_scenes(scenes, fps):
    if not scenes:
        raise ValueError("No scenes")
    end, frame = 0.0, 0
    for scene in scenes:
        start, stop = number(scene["start"], "scene start"), number(scene["end"], "scene end")
        if abs(start - end) > 1e-6 or stop <= start or round(stop * fps) <= frame:
            raise ValueError("Scenes must start at zero, be contiguous and last at least one frame")
        frame, end = round(stop * fps), stop
    return frame


def crop_filter(crop, source_width, source_height):
    w, h, x, y = crop
    if any(int(v) != v for v in crop) or min(w, h) <= 0 or min(x, y) < 0 or x + w > source_width or y + h > source_height:
        raise ValueError("Crop is outside the source frame")
    return f"crop={w}:{h}:{x}:{y}"


def insert_filter(width, height, frames, fps, motion):
    n = max(frames - 1, 1)
    z, x, y = "1.08", "iw/2-iw/zoom/2", "ih/2-ih/zoom/2"
    if motion == "orbit":
        x, y = f"(iw-iw/zoom)*(0.5+0.3*sin(on/{n}*1.6))", f"(ih-ih/zoom)*(0.5+0.2*cos(on/{n}*1.6))"
    elif motion == "truck":
        x = f"(iw-iw/zoom)*(0.1+0.8*on/{n})"
    elif motion == "push":
        z = f"1.02+0.10*on/{n}"
    elif motion == "pull":
        z = f"1.12-0.10*on/{n}"
    elif motion == "rise":
        y = f"(ih-ih/zoom)*(0.8-0.6*on/{n})"
    else:
        raise ValueError("Image motion must be orbit, truck, push, pull or rise")
    return (f"scale={2*width}:{2*height}:force_original_aspect_ratio=increase,crop={2*width}:{2*height},"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={fps},setsar=1,format=yuv420p")


def transition_frame(kind, progress, width, height):
    from PIL import Image, ImageDraw
    if kind not in {"wipe", "iris", "doors", "state"}:
        raise ValueError("Transition must be wipe, iris, doors or state")
    im = Image.new("RGBA", (width, height))
    d = ImageDraw.Draw(im)
    closure = min(1, 1.25 * (1 - abs(2 * progress - 1)))
    if kind == "wipe":
        x = round((-1.4 + 2.4 * progress) * width)
        d.rectangle((x, 0, x + 1.4 * width, height), fill="#c99bff")
        d.rectangle((x + 1.35 * width, 0, x + 1.4 * width, height), fill="#91e2c0")
    elif kind == "iris":
        im = Image.new("RGBA", (width, height), "#0a0b10")
        d = ImageDraw.Draw(im)
        radius = round(max(width, height) * 1.2 * (1 - closure))
        cx, cy = width / 2, height * 760 / 1920
        if radius:
            d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=(0, 0, 0, 0), outline="#ffb35e", width=max(1, round(width * 22/1080)))
    elif kind == "doors":
        size = round(width / 2 * closure)
        d.rectangle((0, 0, size, height), fill="#c99bff")
        d.rectangle((width-size, 0, width, height), fill="#91e2c0")
    else:
        x = round((-1720 + 3000 * progress) * width / 1080)
        d.polygon([(x, 0), (x+1740*width/1080, 0), (x+1490*width/1080, height), (x-250*width/1080, height)],
                  fill="#ff937e" if progress < .5 else "#91e2c0")
    return im


def assemble(args):
    plan_file = Path(args.plan).resolve()
    plan, base = read_json(plan_file), plan_file.parent
    width, height, fps = (int(plan.get("format", {}).get(k, v)) for k, v in (("width", 1080), ("height", 1920), ("fps", 30)))
    if min(width, height, fps) <= 0 or width % 2 or height % 2:
        raise ValueError("Use positive, even output dimensions and positive integer fps")
    frame_count = validate_scenes(plan["scenes"], fps)
    duration = frame_count / fps
    work = Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    out = output_path(args.output, args.overwrite)
    report = output_path(out.with_suffix(".json"), args.overwrite)
    audio = input_file(resolve(base, args.audio or plan["audio"]))
    ass = input_file(resolve(base, args.ass or plan["ass"])) if args.ass or plan.get("ass") else None
    sources = [input_file(resolve(base, s["file"])) for s in plan["scenes"]]
    if out in {audio, ass, *sources, plan_file} or report in {audio, ass, *sources, plan_file}:
        raise ValueError("Inputs and outputs must be distinct")
    ainfo = probe(audio, args.ffprobe)
    astream = stream(ainfo, "audio")
    if float(astream.get("duration", ainfo["format"]["duration"])) < duration - 1 / fps:
        raise ValueError("Audio is shorter than the picture; review the timeline")
    if args.copy_audio and astream["codec_name"] != "aac":
        raise ValueError("--copy-audio requires an AAC source")
    source_evidence = [{"file": str(p), "sha256": digest(p)} for p in dict.fromkeys(sources)]
    enc = ["-an", "-r", fps, "-c:v", "libx264", "-threads", args.threads, "-preset", "veryfast", "-crf", args.crf, "-pix_fmt", "yuv420p"]
    if args.picture:
        picture = input_file(args.picture)
        pi = probe(picture, args.ffprobe)
        ps = stream(pi, "video")
        rate = ps["avg_frame_rate"].split("/")
        if (ps["width"], ps["height"]) != (width, height) or abs(float(rate[0])/float(rate[1]) - fps) > .001 or int(ps.get("nb_frames", 0)) != frame_count:
            raise ValueError("Reused picture dimensions, fps or frame count differ from the plan")
    else:
        paths = []
        for i, (scene, source) in enumerate(zip(plan["scenes"], sources)):
            dest = work / f"scene-{i:03}.mp4"
            frames = round(scene["end"] * fps) - round(scene["start"] * fps)
            kind = scene["kind"]
            if kind == "image":
                command = ["-i", source, "-vf", insert_filter(width, height, frames, fps, scene["motion"])]
            elif kind in {"capture", "clip"}:
                source_info = stream(probe(source, args.ffprobe), "video")
                if any(abs(s.get("rotation", 0)) > .01 for s in source_info.get("side_data_list", [])):
                    raise ValueError("Normalize source rotation before measuring a capture crop")
                crop = scene.get("crop", [source_info["width"], source_info["height"], 0, 0])
                cf = crop_filter(crop, source_info["width"], source_info["height"])
                graph = f"[0:v]setpts=PTS-STARTPTS,fps={fps},{cf},scale={width}:{height}:flags=lanczos,setsar=1,format=yuv420p[v]"
                if "wide_crop" in scene:
                    wide = scene["wide_crop"]
                    wf = crop_filter(wide, source_info["width"], source_info["height"])
                    fh, y = round(width * wide[1] / wide[0]), int(scene.get("wide_y", 330))
                    if y < 0 or y + fh > height:
                        raise ValueError("Wide shot is outside output frame")
                    graph = (f"[0:v]setpts=PTS-STARTPTS,fps={fps},split=2[b][f];[b]{cf},scale={width}:{height},gblur=sigma=24[bg];"
                             f"[f]{wf},scale={width}:{fh}[fg];[bg][fg]overlay=0:{y},setsar=1,format=yuv420p[v]")
                command = ["-ss", number(scene.get("source_start", 0), "source_start"), "-i", source,
                           "-filter_complex_threads", 1, "-filter_complex", graph, "-map", "[v]"]
            else:
                raise ValueError("Scene kind must be capture, clip or image")
            run([args.ffmpeg, "-hide_banner", "-loglevel", "error", *command, "-frames:v", frames, *enc, "-y", dest], log=work/f"scene-{i:03}.log")
            if int(stream(probe(dest, args.ffprobe), "video").get("nb_frames", 0)) != frames:
                raise ValueError("Source ended before the requested scene length")
            paths.append(dest)
        concat = work / "concat.txt"
        concat.write_text("".join("file '" + p.as_posix().replace("'", "'\\''") + "'\n" for p in paths), encoding="utf-8")
        picture = work / "picture.mp4"
        run([args.ffmpeg, "-v", "error", "-f", "concat", "-safe", 0, "-i", concat, "-c", "copy", "-y", picture])
    layers = []
    for i, tr in enumerate(plan.get("transitions", [])):
        frames = round(number(tr.get("duration", .4), "transition duration") * fps)
        start = round(number(tr["at"], "transition cut") * fps) / fps - frames / fps / 2
        if frames < 2 or start < 0 or start + frames / fps > duration:
            raise ValueError("Transition must contain at least two frames and fit within the picture")
        folder = work / f"transition-{i:03}"
        folder.mkdir(exist_ok=True)
        for n in range(frames):
            transition_frame(tr["type"], (n+.5)/frames, width, height).save(folder/f"{n:04}.png")
        movie = folder / "cover.mov"
        run([args.ffmpeg, "-v", "error", "-framerate", fps, "-i", folder/"%04d.png", "-frames:v", frames,
             "-c:v", "prores_ks", "-threads", args.threads, "-profile:v", 4, "-pix_fmt", "yuva444p10le", "-y", movie])
        layers.append((movie, start, frames/fps))
    for layer in plan.get("overlays", []):
        file = input_file(resolve(base, layer["file"]))
        start, length = number(layer["start"], "overlay start"), number(layer["duration"], "overlay duration")
        info = probe(file, args.ffprobe)
        vs = stream(info, "video")
        if length <= 0 or start + length > duration + 1e-6 or float(info["format"]["duration"]) < length - 1/fps:
            raise ValueError("Overlay length is outside source or timeline")
        if (vs["width"], vs["height"]) != (width, height):
            raise ValueError("Alpha overlays must match the output dimensions")
        layers.append((file, start, length))
    inputs = ["-i", picture, "-i", audio]
    graph, previous = [], "0:v"
    for i, (file, start, length) in enumerate(layers):
        inputs += ["-i", file]
        graph += [f"[{i+2}:v]trim=duration={length},setpts=PTS-STARTPTS+{start}/TB[l{i}]",
                  f"[{previous}][l{i}]overlay=0:0:eof_action=pass:repeatlast=0:enable='between(t,{start},{start+length})'[v{i}]"]
        previous = f"v{i}"
    subtitle_filter = ""
    if ass:
        target = work / "captions.ass"
        if target.resolve() != ass:
            shutil.copy2(ass, target)
        subtitle_filter = "ass=captions.ass,"
    graph.append(f"[{previous}]{subtitle_filter}format=yuv420p[final]")
    audio_encode = ["-c:a", "copy"] if args.copy_audio else ["-c:a", "aac", "-b:a", "192k"]
    run([args.ffmpeg, "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex_threads", 1,
         "-filter_complex", ";".join(graph), "-map", "[final]", "-map", "1:a:0", "-t", duration,
         "-c:v", "libx264", "-threads", args.threads, "-preset", "veryfast", "-crf", args.crf,
         "-pix_fmt", "yuv420p", "-r", fps, *audio_encode, "-movflags", "+faststart", "-y", out], cwd=work, log=work/"final.log")
    run([args.ffmpeg, "-v", "error", "-i", out, "-f", "null", "-"], log=work/"decode.log")
    info = probe(out, args.ffprobe)
    if int(stream(info, "video").get("nb_frames", 0)) != frame_count:
        raise ValueError("Final frame count differs from timeline")
    write_json(report, {"file": str(out), "sha256": digest(out), "info": info, "plan": plan,
                        "source_evidence": source_evidence, "audio_file_sha256": digest(audio),
                        "aac_stream_copy": args.copy_audio, "picture_sha256": digest(picture),
                        "caption_sha256": digest(ass) if ass else None,
                        "image_distinct_source_hashes": len({digest(p) for p, s in zip(sources, plan["scenes"]) if s["kind"] == "image"}),
                        "full_decode": "passed", "visual_review": "pending", "perceptual_listening": False})
    print(f"Rendered {frame_count} frames / {duration:.6f}s; final visual and audio review pending.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", required=True); p.add_argument("--work", required=True); p.add_argument("--output", required=True)
    p.add_argument("--audio"); p.add_argument("--ass"); p.add_argument("--picture", help="Reuse verified picture, e.g. previous work/picture.mp4")
    p.add_argument("--copy-audio", action="store_true"); p.add_argument("--overwrite", action="store_true")
    p.add_argument("--ffmpeg", default="ffmpeg"); p.add_argument("--ffprobe", default="ffprobe")
    p.add_argument("--threads", type=int, default=2); p.add_argument("--crf", type=int, default=19)
    assemble(p.parse_args())


if __name__ == "__main__":
    main()
