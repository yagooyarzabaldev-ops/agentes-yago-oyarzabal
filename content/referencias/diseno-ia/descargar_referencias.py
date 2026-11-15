"""Restore the captured image selection or verify its SHA256 hashes.

Uses only the Python standard library. The dynamic Pinterest search is not
rerun: manifest.json identifies the exact images selected for this snapshot.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
import argparse
import hashlib
import json

BASE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verificar', action='store_true', help='Check files without network access')
    args = parser.parse_args()
    manifest = json.loads((BASE / 'manifest.json').read_text(encoding='utf-8'))
    checks = []
    for item in manifest['assets']:
        try:
            dest = (BASE / item['file']).resolve()
            if not dest.is_relative_to(BASE):
                raise ValueError('Image destination must stay inside the reference folder')
            if not dest.exists() and not args.verificar:
                url = item['image_url']
                host = urlsplit(url)
                if host.scheme != 'https' or host.hostname not in {'i.pinimg.com', 'images.rawpixel.com'}:
                    raise ValueError('Unexpected source; inspect the manifest before downloading')
                with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as response:
                    data = response.read(15 * 1024 * 1024 + 1)
                if len(data) > 15 * 1024 * 1024:
                    raise ValueError('Image exceeds the reference download limit')
                if hashlib.sha256(data).hexdigest() != item['sha256']:
                    raise ValueError('Remote image changed; original snapshot was not overwritten')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            data = dest.read_bytes()
            ok = len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
            checks.append({'id': item['id'], 'ok': ok, 'bytes': len(data)})
            print(f"{'OK' if ok else 'ERROR'} {item['file']}")
        except Exception as exc:
            checks.append({'id': item['id'], 'ok': False, 'error': str(exc)})
            print(f"ERROR {item['id']}: {exc}")
    report = {'ok': all(c['ok'] for c in checks), 'count': len(checks), 'checks': checks}
    (BASE / 'verificacion.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
