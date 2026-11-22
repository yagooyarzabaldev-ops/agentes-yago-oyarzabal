"""Stage authorized media through the logged-in Composio CLI, without publishing.

Only public CLI/meta-tool interfaces are used; this module never reads credentials.
Payloads (including base64), responses and signed URLs stay in private runtime files.
The workbench receives 256 KiB chunks, verifies SHA-256, then uses its documented
upload_local_file helper. A complete HTTPS download verifies the resulting object.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid


ROOT = Path(__file__).resolve().parents[1]
COMPOSIO_ROOT = Path('D:/Herramientas/marketing/composio')
CHUNK_BYTES = 256 * 1024
MARKER = 'MARKETING_FILE_RESULT '
MEDIA_TYPES = {'.mp4': 'video/mp4', '.jpg': 'image/jpeg',
               '.jpeg': 'image/jpeg', '.png': 'image/png'}


class StagingError(RuntimeError):
    """A safe diagnostic: detailed tool responses belong only in runtime."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Restrict POSIX permissions. Windows inherits the user's runtime directory ACL.
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    if os.name != 'nt':
        path.chmod(0o600)


def _private_runtime(path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to((ROOT / 'runtime').resolve()):
        raise StagingError('The runtime directory must be inside this project runtime/.')
    return resolved


def _source_metadata(path):
    source = Path(path).resolve(strict=True)
    mime = MEDIA_TYPES.get(source.suffix.lower())
    if not source.is_file() or mime is None:
        raise StagingError('Only an explicitly selected MP4, JPEG or PNG file can be staged.')
    with source.open('rb') as stream:
        header = stream.read(16)
    valid = ((mime == 'video/mp4' and header[4:8] == b'ftyp') or
             (mime == 'image/jpeg' and header.startswith(b'\xff\xd8\xff')) or
             (mime == 'image/png' and header.startswith(b'\x89PNG\r\n\x1a\n')))
    if not valid:
        raise StagingError('The selected media does not match its file extension.')
    return source, {'source_path': str(source), 'sha256': sha256_file(source),
                    'bytes': source.stat().st_size, 'mime_type': mime}


def _extract_marker(document):
    """Read our explicit result from the CLI's JSON/text envelope, never eval it."""
    found = []

    def visit(value):
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str):
            # Nested JSON envelopes occur in meta-tool results.
            try:
                nested = json.loads(value)
            except (ValueError, TypeError):
                nested = None
            if isinstance(nested, (dict, list)):
                visit(nested)
                return
            for line in value.splitlines():
                if not line.startswith(MARKER):
                    continue
                try:
                    result = json.loads(line[len(MARKER):])
                except ValueError:
                    continue
                if isinstance(result, dict) and result not in found:
                    found.append(result)

    visit(document)
    if len(found) != 1:
        raise StagingError('Workbench did not return one unambiguous staging result; inspect private logs.')
    return found[0]


class WorkbenchClient:
    """Invoke only the official workbench meta-tool, with data in private JSON files."""

    def __init__(self, runtime, session_id=None, *, command=None, runner=None):
        self.runtime = _private_runtime(runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)
        if session_id is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', session_id):
            raise StagingError('Invalid Composio session identifier.')
        self.session_id = session_id
        if command is None:
            executable = COMPOSIO_ROOT / 'composio-windows-x64' / 'composio.exe'
            if not executable.is_file():
                raise StagingError('The official Composio CLI is missing from D:/Herramientas/marketing/composio.')
            command = [str(executable)]
        self.command = list(command)
        self.environment = dict(os.environ)
        self.environment.update(COMPOSIO_CACHE_DIR=str(COMPOSIO_ROOT / 'config'),
                                COMPOSIO_SESSION_DIR=str(COMPOSIO_ROOT / 'sessions'),
                                COMPOSIO_CLI_TELEMETRY_DISABLED='1')
        self.runner = runner or subprocess.run
        self.sequence = 0

    def invoke(self, code, step, metric=''):
        self.sequence += 1
        label = f'{self.sequence:04d}-{step}'
        data_path = self.runtime / f'{label}.request.json'
        payload = {'code_to_execute': code, 'thought': 'Stage and verify an authorized local media file.',
                   'current_step': 'STAGING_MEDIA', 'current_step_metric': metric}
        if self.session_id:
            payload['session_id'] = self.session_id
        _write_json(data_path, payload)
        stdout_path = self.runtime / f'{label}.stdout.json'
        stderr_path = self.runtime / f'{label}.stderr.log'
        try:
            # No shell, no file contents on argv, no credential or environment inspection.
            with stdout_path.open('wb') as out, stderr_path.open('wb') as err:
                result = self.runner(self.command + ['execute', 'COMPOSIO_REMOTE_WORKBENCH',
                                                    '-d', '@' + str(data_path)],
                                     cwd=str(ROOT), env=self.environment,
                                     stdout=out, stderr=err, timeout=210, check=False)
            if result.returncode:
                raise StagingError('Composio execution failed; inspect private runtime logs before retrying.')
            raw = stdout_path.read_text(encoding='utf-8-sig')
            try:
                document = json.loads(raw)
            except ValueError:
                raise StagingError('Composio returned invalid JSON; inspect private runtime logs.') from None
            if isinstance(document, dict) and document.get('successful') is False:
                raise StagingError('Composio reported failure; inspect private runtime logs.')
            return _extract_marker(document)
        except subprocess.TimeoutExpired:
            raise StagingError('Composio timed out; staging status is uncertain. Inspect private logs before retrying.') from None


def _emit_code(expression):
    return f"print({MARKER!r} + json.dumps({expression}, sort_keys=True))\n"


def _initialization_code(remote_path, metadata):
    return ("import json, pathlib\n"
            f"p = pathlib.Path({remote_path!r})\n"
            "p.parent.mkdir(parents=True, exist_ok=True)\n"
            "manifest = p.parent / 'source.json'\n"
            f"expected = {metadata!r}\n"
            "if manifest.exists():\n"
            "    assert json.loads(manifest.read_text()) == expected, 'Transfer identity mismatch'\n"
            "else:\n"
            "    manifest.write_text(json.dumps(expected))\n"
            "if not p.exists():\n"
            "    p.touch(exist_ok=False)\n"
            "assert p.stat().st_size <= expected['bytes'], 'Unexpected remote length'\n" +
            _emit_code("{'stage': 'initialized', 'remote_path': str(p), 'bytes': p.stat().st_size}"))


def _chunk_code(remote_path, offset, chunk, total_bytes):
    params = {'path': remote_path, 'offset': offset, 'total': total_bytes,
              'sha256': hashlib.sha256(chunk).hexdigest(),
              'base64': base64.b64encode(chunk).decode('ascii')}
    return ("import json, pathlib, base64, hashlib\n"
            f"part = {params!r}\n"
            "block = base64.b64decode(part['base64'], validate=True)\n"
            "assert hashlib.sha256(block).hexdigest() == part['sha256'], 'Chunk hash mismatch'\n"
            "assert 0 <= part['offset'] < part['total'], 'Invalid offset'\n"
            "assert part['offset'] + len(block) <= part['total'], 'Chunk exceeds expected file'\n"
            "p = pathlib.Path(part['path'])\n"
            "assert p.stat().st_size >= part['offset'], 'Missing previous chunk'\n"
            "with p.open('r+b') as stream:\n"
            "    stream.seek(part['offset'])\n"
            "    identical = stream.read(len(block)) == block\n"
            "    if not identical:\n"
            "        stream.seek(part['offset'])\n"
            "        stream.write(block)\n"
            "        stream.flush()\n" +
            _emit_code("{'stage': 'chunk', 'offset': part['offset'], 'bytes': len(block), "
                       "'sha256': part['sha256'], 'already_present': identical}"))


def _finalization_code(remote_path, expected_sha256, expected_bytes):
    return ("import json, pathlib, hashlib\n"
            f"p = pathlib.Path({remote_path!r})\n"
            "digest = hashlib.sha256()\n"
            "with p.open('rb') as stream:\n"
            "    for block in iter(lambda: stream.read(1048576), b''):\n"
            "        digest.update(block)\n"
            f"assert p.stat().st_size == {expected_bytes}, 'Remote length mismatch'\n"
            f"assert digest.hexdigest() == {expected_sha256!r}, 'Remote SHA256 mismatch'\n"
            "receipt = p.parent / 'upload-receipt.json'\n"
            "if receipt.exists():\n"
            "    uploaded = json.loads(receipt.read_text())\n"
            "else:\n"
            "    uploaded, upload_error = upload_local_file(str(p))\n"
            "    assert not upload_error, 'Composio artifact upload failed'\n"
            "    assert isinstance(uploaded, dict), 'Unexpected upload response'\n"
            "    receipt.write_text(json.dumps(uploaded))\n" +
            _emit_code("{'stage': 'uploaded', 'sha256': digest.hexdigest(), "
                       "'bytes': p.stat().st_size, 'upload': uploaded}"))


def _https_url(url, *, resolve=True):
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.fragment or parsed.port not in (None, 443)):
            raise ValueError()
        if resolve:
            addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                raise ValueError()
        return parsed.hostname
    except (ValueError, OSError, TypeError):
        raise StagingError('Artifact URL must use public HTTPS without embedded credentials.') from None


class _PublicRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _https_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def verify_download(url, target, expected_sha256, expected_bytes):
    """Verify HTTPS accessibility and exact contents, not just Content-Length/HEAD."""
    host = _https_url(url)
    digest = hashlib.sha256()
    received = 0
    started = time.monotonic()
    try:
        with build_opener(_PublicRedirects()).open(
                Request(url, headers={'User-Agent': 'InfiniteProcess-MediaQA/1'}), timeout=45) as response:
            final_host = _https_url(response.geturl())
            with Path(target).open('wb') as stream:
                while True:
                    block = response.read(min(1024 * 1024, expected_bytes + 1 - received))
                    if not block:
                        break
                    received += len(block)
                    if received > expected_bytes or time.monotonic() - started > 300:
                        raise StagingError('HTTPS download exceeded its expected size or time limit.')
                    digest.update(block)
                    stream.write(block)
        if received != expected_bytes or digest.hexdigest() != expected_sha256:
            raise StagingError('HTTPS download differs from the selected local file.')
        return {'sha256': digest.hexdigest(), 'bytes': received, 'verified_at': _now(),
                'host': host, 'final_host': final_host}
    except StagingError:
        raise
    except Exception:
        raise StagingError('HTTPS download failed. Its temporary URL remains only in the private receipt.') from None


def stage_file(file_path, runtime, session_id=None, *, client_factory=WorkbenchClient,
               download_verifier=verify_download, progress=None):
    """Return a private, verified receipt for one media file. Never publish to an app.

    runtime must be beneath this project's runtime directory. Each invocation gets
    an isolated transfer directory; failed/uncertain uploads are never auto-replayed.
    client_factory/download_verifier permit offline transport tests without secrets.
    """
    runtime = _private_runtime(runtime)
    source, metadata = _source_metadata(file_path)
    transfer_id = uuid.uuid4().hex
    work = runtime / transfer_id
    work.mkdir(parents=True, exist_ok=False)
    safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', source.name)[:120]
    remote_path = f'/mnt/files/marketing-staging/{transfer_id}/{safe_name}'
    receipt_path = work / 'receipt.json'
    receipt = {**metadata, 'version': 1, 'status': 'preparing', 'created_at': _now(),
               'transfer_id': transfer_id, 'session_id': session_id, 'remote_path': remote_path,
               'chunk_bytes': CHUNK_BYTES, 'receipt_path': str(receipt_path),
               'publishes_to_apps': False}
    _write_json(receipt_path, receipt)
    try:
        client = client_factory(work / 'calls', session_id)
        initialized = client.invoke(_initialization_code(remote_path, metadata), 'initialize')
        if initialized.get('stage') != 'initialized' or initialized.get('remote_path') != remote_path:
            raise StagingError('Remote transfer initialization could not be confirmed.')
        chunks = (metadata['bytes'] + CHUNK_BYTES - 1) // CHUNK_BYTES
        with source.open('rb') as stream:
            for index in range(chunks):
                chunk = stream.read(CHUNK_BYTES)
                offset = index * CHUNK_BYTES
                result = client.invoke(_chunk_code(remote_path, offset, chunk, metadata['bytes']),
                                       'chunk', f'{index + 1}/{chunks} chunks')
                expected = {'stage': 'chunk', 'offset': offset, 'bytes': len(chunk),
                            'sha256': hashlib.sha256(chunk).hexdigest()}
                if any(result.get(key) != value for key, value in expected.items()):
                    raise StagingError('Remote chunk acknowledgement did not match the selected file.')
                if progress:
                    progress(index + 1, chunks)
        if source.stat().st_size != metadata['bytes'] or sha256_file(source) != metadata['sha256']:
            raise StagingError('The source changed during transfer; artifact upload was stopped.')
        receipt['status'] = 'transferred'
        _write_json(receipt_path, receipt)
        final = client.invoke(_finalization_code(remote_path, metadata['sha256'], metadata['bytes']),
                              'upload', f'{chunks}/{chunks} chunks')
        if (final.get('stage') != 'uploaded' or final.get('sha256') != metadata['sha256']
                or final.get('bytes') != metadata['bytes']):
            raise StagingError('Remote file verification failed.')
        uploaded = final.get('upload')
        if not isinstance(uploaded, dict) or not isinstance(uploaded.get('s3_url'), str):
            raise StagingError('Composio did not return its documented artifact URL.')
        url = uploaded['s3_url']
        _https_url(url, resolve=False)
        receipt.update(status='uploaded_unverified', s3_url=url, s3key=uploaded.get('s3key'),
                       remote_verification={'sha256': final['sha256'], 'bytes': final['bytes']},
                       upload_result=uploaded)
        _write_json(receipt_path, receipt)
        receipt['download_verification'] = download_verifier(
            url, work / ('verified-download' + source.suffix.lower()), metadata['sha256'], metadata['bytes'])
        receipt.update(status='verified', completed_at=_now())
        _write_json(receipt_path, receipt)
        return receipt
    except Exception as exc:
        receipt.update(status='failed', failed_at=_now(),
                       last_completed_status=receipt['status'], error_type=type(exc).__name__)
        _write_json(receipt_path, receipt)
        if isinstance(exc, StagingError):
            raise
        raise StagingError('Staging failed; inspect the private receipt and tool logs.') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', required=True, type=Path)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--session', dest='session_id')
    args = parser.parse_args(argv)
    started = time.monotonic()
    try:
        receipt = stage_file(args.file, args.runtime, args.session_id)
    except (StagingError, OSError) as exc:
        # No exception traceback, tool stderr, payload or signed URL in the console.
        message = str(exc) if isinstance(exc, StagingError) else 'Cannot read the selected media or runtime directory.'
        parser.exit(1, message + '\n')
    print(json.dumps({'status': receipt['status'], 'receipt_path': receipt['receipt_path'],
                      'sha256': receipt['sha256'], 'bytes': receipt['bytes'],
                      'host': receipt['download_verification']['host'],
                      'elapsed_seconds': round(time.monotonic() - started, 2)}))


if __name__ == '__main__':
    main()
