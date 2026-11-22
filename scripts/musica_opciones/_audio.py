"""Local FFmpeg helpers shared by the comparison and technical review CLIs."""
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def run(args, log=None):
    result = subprocess.run([str(a) for a in args], capture_output=True)
    if log:
        Path(log).write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', 'replace')[-3000:])
    return result


def ffmpeg(*args, log=None):
    return run(['ffmpeg', '-hide_banner', '-nostdin', *args], log=log)


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', path]).stdout)


def duration(path, kind='audio'):
    info = probe(path)
    streams = [s for s in info['streams'] if s['codec_type'] == kind]
    if not streams:
        raise ValueError(f'{path}: no {kind} stream')
    value = float(streams[0].get('duration') or info['format']['duration'])
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{path}: invalid duration')
    return value


def child(root, name):
    """Resolve relative artifact paths without letting a manifest escape its folder."""
    root = Path(root).resolve()
    if Path(name).is_absolute():
        raise ValueError('Artifact filenames must be relative')
    result = (root / name).resolve()
    if not result.is_relative_to(root):
        raise ValueError('Artifact path escapes its directory')
    return result


def new_directory(path):
    path = Path(path)
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError(f'Output directory must be new or empty: {path}')
    path.mkdir(parents=True, exist_ok=True)
    return path


def measure(path, target=-14.4, peak=-2.5, log=None, start=None, seconds=None):
    filters = []
    if start is not None:
        filters.append(f'atrim=start={start}' + (f':duration={seconds}' if seconds is not None else ''))
    filters.append(f'loudnorm=I={target}:TP={peak}:LRA=8:print_format=json')
    result = ffmpeg('-nostats', '-i', path, '-vn', '-af',
                    ','.join(filters), '-f', 'null', '-', log=log)
    match = re.search(rb'\{[^{}]*"input_i"[^{}]*\}', result.stderr, re.S)
    if not match:
        raise ValueError(f'No loudness result: {path}')
    metrics = json.loads(match.group())
    if not all(math.isfinite(float(metrics[k])) for k in ('input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset')):
        raise ValueError(f'Cannot normalize silent or invalid audio: {path}')
    return metrics


def normalize(source, destination, target, peak, log_dir):
    metrics = measure(source, target, peak, log_dir / (destination.stem + '-before.log'))
    filt = (f'loudnorm=I={target}:TP={peak}:LRA=8:measured_I={metrics["input_i"]}:'
            f'measured_TP={metrics["input_tp"]}:measured_LRA={metrics["input_lra"]}:'
            f'measured_thresh={metrics["input_thresh"]}:offset={metrics["target_offset"]}:linear=true')
    ffmpeg('-v', 'error', '-n', '-i', source, '-af', filt, '-ar', '48000', '-ac', '2',
           '-c:a', 'pcm_s24le', destination, log=log_dir / (destination.stem + '-normalize.log'))
    return measure(destination, target, peak, log_dir / (destination.stem + '-after.log'))


def strict_decode(path, log=None):
    ffmpeg('-v', 'error', '-xerror', '-err_detect', 'explode', '-i', path, '-f', 'null', '-', log=log)


def video_hash(path):
    """Hash copied video packets; convert H264/HEVC to a stable Annex B stream."""
    stream = next(s for s in probe(path)['streams'] if s['codec_type'] == 'video')
    bsf = {'h264': 'h264_mp4toannexb', 'hevc': 'hevc_mp4toannexb'}.get(stream['codec_name'])
    args = ['-v', 'error', '-i', path, '-map', '0:v:0', '-c:v', 'copy']
    if bsf:
        args += ['-bsf:v', bsf]
    return ffmpeg(*args, '-f', 'hash', '-hash', 'sha256', '-').stdout.decode().strip()
