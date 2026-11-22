from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from marketing.composio_instagram import InstagramPublisher, main, private_path
from marketing.composio_files import StagingError
from marketing.config import AppError
from marketing.store import file_digest, write_json


class FakeCLI:
    def __init__(self, package):
        self.package = package
        self.calls = []
        self.identity = {'user_id': '12345', 'username': 'example.creator', 'account_type': 'MEDIA_CREATOR'}
        self.fail_create = False
        self.fail_publish = False
        self.bad_metadata = False
        self.container_status = 'FINISHED'

    def proxy(self, account, version, resource, method='GET', body=None):
        self.calls.append((resource, method, body))
        if resource.startswith('me?'):
            return self.identity
        if resource == '12345/media':
            if self.fail_create:
                raise AppError('Lost create response')
            return {'id': '111'}
        if resource == '12345/media_publish':
            if self.fail_publish:
                raise AppError('Lost publish response')
            return {'id': '222'}
        if resource.startswith('111?'):
            return {'status_code': self.container_status}
        if resource.startswith('222?'):
            return {'id': '222', 'username': 'example.creator', 'caption': 'Mismatch' if self.bad_metadata else 'Copy aprobado.',
                    'media_product_type': 'REELS', 'is_ai_generated': True, 'is_shared_to_feed': True,
                    'permalink': 'https://www.instagram.com/reel/example/'}
        raise AssertionError(resource)

    @property
    def writes(self):
        return [call for call in self.calls if call[1] != 'GET']


class ComposioInstagramTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(patch.stopall)
        patch('marketing.composio_instagram.PROJECT_ROOT', self.root).start()
        patch('marketing.composio_instagram.verify_video', return_value={'width': 1080}).start()
        self.delivery = self.root / 'entregas/example'
        self.delivery.mkdir(parents=True)
        (self.delivery / 'video.mp4').write_bytes(b'Approved MP4 bytes')
        (self.delivery / 'cover.jpg').write_bytes(b'Approved JPEG bytes')
        (self.delivery / 'copy.txt').write_text('Copy aprobado.\n', encoding='utf-8')
        self.package = {'video': str(self.delivery / 'video.mp4'), 'cover': str(self.delivery / 'cover.jpg'),
                        'caption_file': str(self.delivery / 'copy.txt'), 'account': 'example',
                        'instagram_user_id': '12345', 'username': 'example.creator', 'is_ai_generated': True,
                        'share_to_feed': True, 'audio_name': 'Original user music'}
        self.cli = FakeCLI(self.package)
        self.state = self.root / 'runtime/publish/state.json'
        self.publisher = InstagramPublisher(self.package, self.state, cli=self.cli, stager=self.stage)
        self.download = patch('marketing.composio_instagram.verify_download', return_value={'verified': True}).start()

    def stage(self, source, runtime):
        file = Path(source)
        return {'status': 'verified', 'sha256': file_digest(file), 'bytes': file.stat().st_size,
                's3_url': 'https://files.example.com/' + file.name}

    def fingerprint(self):
        return self.publisher.snapshot()['fingerprint']

    def record(self):
        return json.loads(self.state.read_text(encoding='utf-8'))

    def test_check_reads_identity_without_creating_media(self):
        checked = self.publisher.check()
        self.assertEqual(checked['state'], 'checked')
        self.assertFalse(checked['publication_performed'])
        self.assertEqual(len(checked['fingerprint']), 64)
        self.assertEqual(self.cli.writes, [])
        self.assertFalse(self.state.exists())

    def test_wrong_account_blocks_upload_and_publication(self):
        self.cli.identity['username'] = 'different.person'
        with self.assertRaisesRegex(AppError, 'no corresponde'):
            self.publisher.publish(self.fingerprint())
        self.assertEqual(self.cli.writes, [])
        self.download.assert_not_called()

    def test_changed_package_invalidates_authorization(self):
        approved = self.fingerprint()
        (self.delivery / 'copy.txt').write_text('Changed copy', encoding='utf-8')
        with self.assertRaisesRegex(AppError, 'huella'):
            self.publisher.publish(approved)
        self.assertEqual(self.cli.calls, [])

    def test_existing_delivery_receipt_prevents_duplicate_with_new_state(self):
        write_json(self.delivery / 'publicacion-instagram.json', {'status': 'published_verified',
                   'final_sha256': file_digest(self.package['video']), 'published_url': 'https://www.instagram.com/reel/existing/'})
        result = self.publisher.publish(self.fingerprint())
        self.assertEqual(result['state'], 'already_published')
        self.assertEqual(self.cli.calls, [])
        self.assertFalse(self.state.exists())

    def test_different_delivery_version_requires_resolution(self):
        write_json(self.delivery / 'publicacion-instagram.json', {'status': 'published_verified', 'final_sha256': 'different'})
        with self.assertRaisesRegex(AppError, 'otra versión'):
            self.publisher.publish(self.fingerprint())
        self.assertEqual(self.cli.calls, [])

    def test_lost_create_response_is_durable_and_not_retried(self):
        self.cli.fail_create = True
        with self.assertRaisesRegex(AppError, 'Lost create'):
            self.publisher.publish(self.fingerprint())
        self.assertEqual(self.record()['state'], 'create_unknown')
        self.cli.fail_create = False
        with self.assertRaisesRegex(AppError, 'incierto'):
            self.publisher.publish(self.fingerprint())
        self.assertEqual(len(self.cli.writes), 1)

    def test_two_steps_create_then_publish_preserve_ai_cover_and_audio(self):
        confirmation = self.fingerprint()
        created = self.publisher.publish(confirmation)
        self.assertEqual(created['state'], 'processing')
        self.assertEqual(created['container_id'], '111')
        body = self.cli.writes[0][2]
        self.assertTrue(body['is_ai_generated'])
        self.assertTrue(body['share_to_feed'])
        self.assertEqual(body['audio_name'], 'Original user music')
        self.assertTrue(body['cover_url'].endswith('cover.jpg'))
        published = self.publisher.publish(confirmation)
        self.assertEqual(published['state'], 'published_verified')
        self.assertEqual(published['publication_attempts'], 1)
        self.publisher.publish(confirmation)
        self.assertEqual(len(self.cli.writes), 2)

    def test_lost_publish_response_blocks_retry_but_allows_verified_reconciliation(self):
        confirmation = self.fingerprint()
        self.publisher.publish(confirmation)
        self.cli.fail_publish = True
        with self.assertRaisesRegex(AppError, 'Lost publish'):
            self.publisher.publish(confirmation)
        self.assertEqual(self.record()['state'], 'publish_unknown')
        self.cli.fail_publish = False
        with self.assertRaisesRegex(AppError, 'incierto'):
            self.publisher.publish(confirmation)
        self.assertEqual(self.publisher.status('222')['state'], 'published_verified')
        self.assertEqual(len(self.cli.writes), 2)

    def test_verification_failure_keeps_remote_id_and_does_not_republish(self):
        confirmation = self.fingerprint()
        self.publisher.publish(confirmation)
        self.cli.bad_metadata = True
        with self.assertRaisesRegex(AppError, 'metadata'):
            self.publisher.publish(confirmation)
        self.assertEqual(self.record()['state'], 'published')
        self.assertEqual(self.record()['media_id'], '222')
        self.cli.bad_metadata = False
        self.assertEqual(self.publisher.publish(confirmation)['state'], 'published_verified')
        self.assertEqual(len(self.cli.writes), 2)

    def test_in_progress_and_status_do_not_publish(self):
        confirmation = self.fingerprint()
        self.publisher.publish(confirmation)
        self.cli.container_status = 'IN_PROGRESS'
        self.publisher.publish(confirmation)
        self.assertEqual(self.publisher.status()['container_status'], 'IN_PROGRESS')
        self.assertEqual(len(self.cli.writes), 1)

    def test_expired_container_not_recreated(self):
        confirmation = self.fingerprint()
        self.publisher.publish(confirmation)
        self.cli.container_status = 'EXPIRED'
        with self.assertRaisesRegex(AppError, 'venció'):
            self.publisher.publish(confirmation)
        with self.assertRaisesRegex(AppError, 'fallido'):
            self.publisher.publish(confirmation)
        self.assertEqual(len(self.cli.writes), 1)

    def test_stage_url_content_must_match_approved_file(self):
        self.download.side_effect = StagingError('Download checksum differs')
        with self.assertRaisesRegex(AppError, 'archivo aprobado'):
            self.publisher.publish(self.fingerprint())
        self.assertEqual(self.cli.writes, [])

    def test_state_cannot_be_reused_for_changed_package(self):
        self.publisher.publish(self.fingerprint())
        self.package['audio_name'] = 'Different audio name'
        with self.assertRaisesRegex(AppError, 'paquete cambió'):
            self.publisher.publish(self.fingerprint())
        self.assertEqual(len(self.cli.writes), 1)

    def test_new_runtime_cannot_bypass_uncertain_attempt(self):
        confirmation = self.fingerprint()
        self.cli.fail_create = True
        with self.assertRaises(AppError):
            self.publisher.publish(confirmation)
        other = InstagramPublisher(self.package, self.root / 'runtime/other/state.json', cli=self.cli, stager=self.stage)
        with self.assertRaisesRegex(AppError, 'otro estado'):
            other.publish(confirmation)
        self.assertEqual(len(self.cli.writes), 1)

    def test_new_runtime_returns_existing_publication(self):
        confirmation = self.fingerprint()
        self.publisher.publish(confirmation)
        self.publisher.publish(confirmation)
        other = InstagramPublisher(self.package, self.root / 'runtime/other/state.json', cli=self.cli, stager=self.stage)
        self.assertEqual(other.publish(confirmation)['state'], 'already_published')
        self.assertEqual(len(self.cli.writes), 2)

    def test_receipts_must_remain_in_private_directories(self):
        with self.assertRaisesRegex(AppError, 'runtime'):
            private_path(self.root / 'production/private-receipt.json')

    def test_cli_check_preserves_emoji_with_windows_legacy_stdout(self):
        raw = io.BytesIO()
        output = io.TextIOWrapper(raw, encoding='cp1252')
        with patch('marketing.composio_instagram.load_package', return_value={}), \
             patch('marketing.composio_instagram.InstagramPublisher') as publisher, \
             patch('sys.stdout', output):
            publisher.return_value.check.return_value = {'state': 'checked', 'caption': 'Agentes 👀'}
            result = main(['check', 'unused.json', '--state', str(self.state)])
            output.flush()
            value = json.loads(raw.getvalue().decode('cp1252'))
        self.assertEqual(result, 0)
        self.assertEqual(value['caption'], 'Agentes 👀')
        output.close()


if __name__ == '__main__':
    unittest.main()
