"""Local production helpers. No downloads, API calls or implicit publication."""
from pathlib import Path
import hashlib
import json
import math
import subprocess


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def resolve(base, value):
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (Path(base) / path).resolve()


def output_path(path, overwrite=False):
    path = Path(path).resolve()
    if path.exists() and not overwrite:
        raise ValueError(f"Output exists: {path}. Use a new path or --overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def number(value, name, minimum=0):
    value = float(value)
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return value


def run(command, *, cwd=None, data=None, log=None):
    result = subprocess.run([str(x) for x in command], cwd=cwd, input=data, capture_output=True)
    if log:
        Path(log).write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[-4000:])
    return result.stdout


def probe(path, ffprobe="ffprobe"):
    return json.loads(run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", path]))


def stream(info, codec_type):
    return next(s for s in info["streams"] if s["codec_type"] == codec_type)


def input_file(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"Missing input: {path}")
    return path
