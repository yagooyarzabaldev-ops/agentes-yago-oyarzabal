"""Offline regression tests for the Composio media staging boundary."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from marketing import composio_files as files


class ComposioFileTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.patch = patch.object(files, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def fixture(self, size=files.CHUNK_BYTES + 77):
        path = self.root / 'video.mp4'
        path.write_bytes(b'\x00\x00\x00\x18ftypisom' + bytes(range(256)) * (size // 256 + 1))
        return path

    def execute_code(self, code, extra=None):
        output = io.StringIO()
        with redirect_stdout(output):
            exec(code, {'upload_local_file': (extra or {}).get('upload_local_file')})
        return files._extract_marker({'data': {'stdout': output.getvalue()}})

    def test_repeated_offset_is_idempotent_and_bad_gap_is_rejected(self):
        source = self.fixture()
        raw = source.read_bytes()
        target = self.root / 'remote' / 'video.mp4'
        meta = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        self.execute_code(files._initialization_code(str(target), meta))
        first = raw[:files.CHUNK_BYTES]
        code = files._chunk_code(str(target), 0, first, len(raw))
        self.assertFalse(self.execute_code(code)['already_present'])
        self.assertTrue(self.execute_code(code)['already_present'])
        self.assertEqual(target.read_bytes(), first)
        with self.assertRaisesRegex(AssertionError, 'Missing previous'):
            self.execute_code(files._chunk_code(str(target), files.CHUNK_BYTES + 1, b'x', len(raw)))
        self.execute_code(files._chunk_code(str(target), files.CHUNK_BYTES, raw[files.CHUNK_BYTES:], len(raw)))
        self.assertEqual(target.read_bytes(), raw)

    def test_final_hash_failure_prevents_upload_and_success_is_checkpointed(self):
        source = self.fixture(100)
        uploads = []
        def upload(path):
            uploads.append(path)
            return {'s3_url': 'https://storage.example/object?secret=private', 's3key': 'object'}, None
        with self.assertRaisesRegex(AssertionError, 'SHA256'):
            self.execute_code(files._finalization_code(str(source), '0' * 64, source.stat().st_size),
                              {'upload_local_file': upload})
        self.assertEqual(uploads, [])
        code = files._finalization_code(str(source), files.sha256_file(source), source.stat().st_size)
        self.assertEqual(self.execute_code(code, {'upload_local_file': upload})['stage'], 'uploaded')
        self.execute_code(code, {'upload_local_file': upload})
        self.assertEqual(uploads, [str(source)], 'A saved upload receipt must prevent a duplicate upload')

    def test_cli_uses_private_json_not_payload_arguments_and_keeps_logs(self):
        commands = []
        def runner(command, **kwargs):
            commands.append(command)
            payload_path = Path(kwargs['cwd']) / command[-1][1:]
            payload = json.loads(payload_path.read_text())
            self.assertEqual(payload['session_id'], 'test_session')
            self.assertIn('PRIVATE_BASE64', payload['code_to_execute'])
            result = {'successful': True, 'data': {'stdout': files.MARKER + '{"ok": true}\n'}}
            kwargs['stdout'].write(json.dumps(result).encode())
            return subprocess.CompletedProcess(command, 0)
        client = files.WorkbenchClient(self.root / 'runtime' / 'test', 'test_session',
                                       command=['trusted-cli'], runner=runner)
        self.assertEqual(client.invoke('PRIVATE_BASE64', 'chunk'), {'ok': True})
        self.assertNotIn('PRIVATE_BASE64', ' '.join(commands[0]))
        self.assertEqual(commands[0][1:3], ['execute', 'COMPOSIO_REMOTE_WORKBENCH'])

    def test_cli_timeout_is_not_replayed_and_diagnostic_does_not_leak(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            raise subprocess.TimeoutExpired(command, 210, output='private payload')
        client = files.WorkbenchClient(self.root / 'runtime' / 'test', command=['trusted-cli'], runner=runner)
        with self.assertRaises(files.StagingError) as failure:
            client.invoke('PRIVATE_BASE64', 'upload')
        self.assertEqual(len(calls), 1)
        self.assertNotIn('private payload', str(failure.exception))
        self.assertNotIn('PRIVATE_BASE64', str(failure.exception))

    def test_envelopes_are_parsed_but_ambiguous_results_are_rejected(self):
        nested = json.dumps({'results': [{'stdout': files.MARKER + '{"bytes": 123}\n'}]})
        self.assertEqual(files._extract_marker({'data': nested}), {'bytes': 123})
        with self.assertRaises(files.StagingError):
            files._extract_marker({'stdout': files.MARKER + '{}\n' + files.MARKER + '{"bytes": 1}\n'})
        with self.assertRaises(files.StagingError):
            files._extract_marker({'stderr': 'execution failed'})

    def test_media_and_runtime_guards_reject_before_remote_calls(self):
        secret = self.root / 'settings.json'
        secret.write_text('{"not_a_real_key":"private"}')
        with self.assertRaises(files.StagingError):
            files.stage_file(secret, self.root / 'runtime')
        fake = self.root / 'renamed.jpg'
        fake.write_text('not an image')
        with self.assertRaises(files.StagingError):
            files.stage_file(fake, self.root / 'runtime')
        with self.assertRaises(files.StagingError):
            files.stage_file(self.fixture(), self.root / 'sources')
        self.assertFalse((self.root / 'runtime').exists())

    def test_url_guards_reject_credentials_insecure_and_private_targets(self):
        for url in ('http://storage.example/file', 'https://user:pass@storage.example/file',
                    'https://storage.example:8443/file', 'https://storage.example/file#fragment'):
            with self.subTest(url=url), self.assertRaises(files.StagingError):
                files._https_url(url, resolve=False)
        private_answer = [(2, 1, 6, '', ('127.0.0.1', 443))]
        with patch.object(files.socket, 'getaddrinfo', return_value=private_answer):
            with self.assertRaises(files.StagingError):
                files._https_url('https://storage.example/file')

    def test_full_download_verifies_hash_and_limits_size(self):
        original = b'authorized bytes'
        class Response(io.BytesIO):
            def geturl(self):
                return 'https://storage.example/file?signature=private'
        class Opener:
            def __init__(self, body):
                self.body = body
            def open(self, *args, **kwargs):
                return Response(self.body)
        target = self.root / 'download.bin'
        with patch.object(files, '_https_url', return_value='storage.example'):
            with patch.object(files, 'build_opener', return_value=Opener(original)):
                result = files.verify_download('https://storage.example/file', target,
                                               hashlib.sha256(original).hexdigest(), len(original))
                self.assertEqual(result['bytes'], len(original))
                self.assertEqual(target.read_bytes(), original)
            with patch.object(files, 'build_opener', return_value=Opener(original + b'extra')):
                with self.assertRaisesRegex(files.StagingError, 'expected size'):
                    files.verify_download('https://storage.example/file', target, '0' * 64, len(original))
            with patch.object(files, 'build_opener', return_value=Opener(b'x' * len(original))):
                with self.assertRaisesRegex(files.StagingError, 'differs'):
                    files.verify_download('https://storage.example/file', target, '0' * 64, len(original))

    def test_complete_transfer_and_source_change_guard(self):
        source = self.fixture()
        root = self.root
        uploads = []
        namespace = '/mnt/files/marketing-staging'
        remote = str(root / 'sandbox').replace('\\', '/')
        outer = self
        class LocalClient:
            def __init__(self, runtime, session_id):
                pass
            def invoke(self, code, step, metric=''):
                code = code.replace(namespace, remote)
                def upload(path):
                    uploads.append(Path(path))
                    return {'s3_url': 'https://storage.example/file?signature=private', 's3key': 'sample'}, None
                result = outer.execute_code(code, {'upload_local_file': upload})
                if 'remote_path' in result:
                    result['remote_path'] = result['remote_path'].replace('\\', '/').replace(remote, namespace)
                return result
        def verify(url, target, digest, size):
            actual = uploads[-1].read_bytes()
            self.assertEqual(hashlib.sha256(actual).hexdigest(), digest)
            self.assertEqual(len(actual), size)
            return {'sha256': digest, 'bytes': size, 'host': 'storage.example'}
        receipt = files.stage_file(source, root / 'runtime', client_factory=LocalClient, download_verifier=verify)
        self.assertEqual(receipt['status'], 'verified')
        self.assertFalse(receipt['publishes_to_apps'])
        self.assertEqual(json.loads(Path(receipt['receipt_path']).read_text())['sha256'], files.sha256_file(source))
        uploads.clear()
        def mutate(done, total):
            if done == total:
                source.write_bytes(source.read_bytes() + b'changed')
        with self.assertRaisesRegex(files.StagingError, 'source changed'):
            files.stage_file(source, root / 'runtime', client_factory=LocalClient,
                             download_verifier=verify, progress=mutate)
        self.assertEqual(uploads, [])

    def test_console_summary_does_not_expose_signed_url(self):
        result = {'status': 'verified', 'receipt_path': 'runtime/private/receipt.json',
                  'sha256': 'a' * 64, 'bytes': 33, 's3_url': 'https://storage.example/file?signature=private',
                  'download_verification': {'host': 'storage.example'}}
        output = io.StringIO()
        with patch.object(files, 'stage_file', return_value=result), redirect_stdout(output):
            files.main(['--file', 'video.mp4', '--runtime', 'runtime/test'])
        summary = json.loads(output.getvalue())
        self.assertEqual(summary['host'], 'storage.example')
        self.assertNotIn('signature', output.getvalue())
        self.assertNotIn('https:', output.getvalue())


if __name__ == '__main__':
    unittest.main()
