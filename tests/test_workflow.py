import copy
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from marketing.agents import Agents, Workflow, approved, validate_script, validate_roulette
from marketing.config import AppError, Config
from marketing.media import aligned_words, escape_ass
from marketing.net import Http
from marketing.publish import Publisher, public_url
from marketing.store import Store, digest, file_digest
from marketing.telegram import Telegram


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / 'examples/demo.json').read_text(encoding='utf-8'))


class FakeAgents:
    def __init__(self):
        self.calls = []

    def run(self, role, context, schema):
        self.calls.append(role)
        if role == '01-trend-hunter':
            return {'mode': 'evergreen', 'formats': [{'hook': 'Idea', 'rationale': 'Ejemplo', 'original_sound': 'Original', 'roulette_adaptation': '8 opciones'}] * 5}
        if role == '02-guionista':
            return copy.deepcopy(EXAMPLE['script'])
        if role in EXAMPLE['agents']:
            return copy.deepcopy(EXAMPLE['agents'][role])
        return {'summary': 'Plan de prueba', 'items': ['Usar el guion aprobado.']}


class FakeHttp:
    def __init__(self, json_results=(), request_results=()):
        self.json_results = list(json_results)
        self.request_results = list(request_results)
        self.calls = []
        self.remote_hash = ''

    def json(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        result = self.json_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        result = self.request_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def remote_digest(self, url):
        return self.remote_hash


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Config(ROOT, env={'OPENAI_API_KEY': 'test-only-not-a-credential',
            'YOUTUBE_CHANNEL_ID': 'channel-123', 'INSTAGRAM_USER_ID': '123456',
            'INSTAGRAM_ACCESS_TOKEN': 'test-only', 'INSTAGRAM_API_VERSION': 'v24.0',
            'TELEGRAM_CHAT_ID': '100', 'TELEGRAM_USER_ID': '200', 'TELEGRAM_BOT_TOKEN': 'fake-token'})
        self.config.runtime = Path(self.temp.name)
        self.store = Store(self.config.runtime)
        self.agents = FakeAgents()
        self.workflow = Workflow(self.config, self.store, self.agents)

    def drafted(self):
        job = self.store.create('Consultas para una pyme', video_format='roulette')
        return self.workflow.draft(job['id'])

    def ready(self):
        job = self.drafted()
        self.workflow.approve(job['id'], digest(job['script'])[:16])
        job = self.workflow.produce(job['id'])
        path = self.config.runtime / (job['id'] + '.mp4')
        path.write_bytes(b'fake-video-for-protocol-tests')
        job.update(state='ready', video={'path': str(path), 'sha256': file_digest(path),
            'script_hash': digest(job['script']), 'synthetic_voice': False})
        self.store.save(job)
        return job


class WorkflowTests(Fixture):
    def test_week_import_is_idempotent_and_does_not_approve(self):
        first = self.workflow.import_week(ROOT / 'content/semana-1.md')
        second = self.workflow.import_week(ROOT / 'content/semana-1.md')
        self.assertEqual(len(first), 7)
        self.assertEqual([j['id'] for j in first], [j['id'] for j in second])
        self.assertTrue(all(j['state'] == 'brief' and j['approval'] is None for j in first))
        self.assertEqual(self.agents.calls, [])

    def test_production_cannot_bypass_approval(self):
        job = self.drafted()
        before = list(self.agents.calls)
        with self.assertRaises(AppError):
            self.workflow.produce(job['id'])
        self.assertEqual(before, self.agents.calls)

    def test_stale_hash_cannot_approve(self):
        job = self.drafted()
        with self.assertRaises(AppError):
            self.workflow.approve(job['id'], 'stale')
        self.assertEqual(self.store.get(job['id'])['state'], 'awaiting_approval')

    def test_claims_need_explicit_review(self):
        job = self.drafted()
        job['script']['claims_to_verify'] = ['Dato cuantitativo sin fuente']
        self.store.save(job)
        script_hash = digest(job['script'])[:16]
        with self.assertRaises(AppError):
            self.workflow.approve(job['id'], script_hash)
        self.workflow.approve(job['id'], script_hash, claims_reviewed=True)

    def test_resume_production_does_not_call_completed_roles_again(self):
        job = self.drafted()
        self.workflow.approve(job['id'], digest(job['script'])[:16])
        self.workflow.produce(job['id'])
        calls = list(self.agents.calls)
        self.workflow.produce(job['id'])
        self.assertEqual(calls, self.agents.calls)

    def test_revision_invalidates_approval_and_video(self):
        job = self.ready()
        revised = self.workflow.revise(job['id'], 'Cambiá el gancho')
        self.assertIsNone(revised['approval'])
        self.assertIsNone(revised['video'])
        self.assertNotIn('script', revised)
        self.assertEqual(revised['state'], 'brief')

    def test_direct_script_change_breaks_approval(self):
        job = self.ready()
        job['script']['title'] = 'Otro título'
        with self.assertRaises(AppError):
            approved(job)

    def test_compare_and_swap_prevents_lost_updates(self):
        job = self.store.create('Idea')
        stale = copy.deepcopy(job)
        self.store.save(job)
        with self.assertRaises(AppError):
            self.store.save(stale)

    def test_process_lock_prevents_concurrent_operation(self):
        with self.store.lock('test'):
            with self.assertRaises(AppError):
                with self.store.lock('test'):
                    self.fail('No debe adquirir dos veces el lock')

    def test_bad_duration_rejected(self):
        script = copy.deepcopy(EXAMPLE['script'])
        script['segments'][0]['seconds'] = 100
        with self.assertRaises(AppError):
            validate_script(script)

    def test_roulette_probabilities_match_equal_sectors(self):
        roulette = copy.deepcopy(EXAMPLE['agents']['03-roulette-master'])
        roulette['options'][0]['probability'] = 80
        with self.assertRaises(AppError):
            validate_roulette(roulette)

    def test_missing_key_does_not_call_network(self):
        http = FakeHttp()
        with self.assertRaises(AppError):
            Agents(Config(ROOT, env={}), http).run('02-guionista', {}, {'type': 'object'})
        self.assertEqual(http.calls, [])

    def test_incomplete_model_output_does_not_become_script(self):
        http = FakeHttp([{'status': 'incomplete', 'output': []}])
        with self.assertRaises(AppError):
            Agents(self.config, http).run('02-guionista', {}, {'type': 'object'})

    def test_model_refusal_is_not_parsed_as_output(self):
        http = FakeHttp([{'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'refusal'}]}]}])
        with self.assertRaises(AppError):
            Agents(self.config, http).run('02-guionista', {}, {'type': 'object'})

    def test_secret_not_in_http_error(self):
        http = Http()
        error = urllib.error.HTTPError('https://example.test/SECRET', 401, 'SECRET', {}, io.BytesIO(b'SECRET'))
        with patch.object(http.opener, 'open', side_effect=error):
            with self.assertRaises(AppError) as caught:
                http.json('GET', 'https://example.test')
        self.assertNotIn('SECRET', str(caught.exception))

    def test_quota_error_is_distinct_from_temporary_rate_limit(self):
        for code in ('insufficient_quota', 'rate_limit_exceeded'):
            with self.subTest(code=code):
                http = Http()
                error = urllib.error.HTTPError('https://example.test', 429, 'error', {},
                    io.BytesIO(json.dumps({'error': {'code': code, 'message': 'SECRET'}}).encode()))
                with patch.object(http.opener, 'open', side_effect=error), self.assertRaises(AppError) as caught:
                    http.json('GET', 'https://example.test')
                self.assertIn(code, str(caught.exception))
                self.assertNotIn('SECRET', str(caught.exception))

    def test_specific_billing_codes_take_precedence_over_quota_type(self):
        for code in ('credit_balance_exhausted', 'organization_spend_limit_exceeded',
                     'project_spend_limit_exceeded', 'organization_usage_limit_exceeded'):
            with self.subTest(code=code):
                http = Http()
                error = urllib.error.HTTPError('https://api.openai.com/v1/responses', 429, 'error', {},
                    io.BytesIO(json.dumps({'error': {'code': code, 'type': 'insufficient_quota',
                                                    'message': 'SECRET'}}).encode()))
                with patch.object(http.opener, 'open', side_effect=error) as call, self.assertRaises(AppError) as caught:
                    http.json('POST', 'https://api.openai.com/v1/responses', data={})
                self.assertIn(code, str(caught.exception))
                self.assertNotIn('insufficient_quota', str(caught.exception))
                self.assertNotIn('SECRET', str(caught.exception))
                self.assertEqual(call.call_count, 1)

    def test_unknown_code_falls_back_to_recognized_error_type(self):
        http = Http()
        error = urllib.error.HTTPError('https://api.openai.com/v1/responses', 429, 'error', {},
            io.BytesIO(b'{"error":{"code":"future_quota_code","type":"insufficient_quota","message":"SECRET"}}'))
        with patch.object(http.opener, 'open', side_effect=error), self.assertRaises(AppError) as caught:
            http.json('POST', 'https://api.openai.com/v1/responses', data={})
        self.assertIn('insufficient_quota', str(caught.exception))
        self.assertNotIn('SECRET', str(caught.exception))

    def test_malformed_error_bodies_preserve_safe_http_error(self):
        for body in (b'not JSON: SECRET', b'[]', b'{"error":"SECRET"}', b'{"error":{"code":[],"type":{}}}'):
            with self.subTest(body=body):
                http = Http()
                error = urllib.error.HTTPError('https://api.openai.com/v1/responses', 429, 'error', {}, io.BytesIO(body))
                with patch.object(http.opener, 'open', side_effect=error), self.assertRaises(AppError) as caught:
                    http.json('POST', 'https://api.openai.com/v1/responses', data={})
                self.assertIn('HTTP 429', str(caught.exception))
                self.assertNotIn('SECRET', str(caught.exception))

    def test_media_text_cannot_inject_ass_tags(self):
        self.assertEqual(escape_ass(r'{\pos(0,0)}hola'), 'pos(0,0)hola')

    def test_timestamp_alignment_yields_word_boundaries(self):
        words = aligned_words({'characters': list('Hola IA'), 'character_start_times_seconds': list(range(7)),
                               'character_end_times_seconds': list(range(1, 8))})
        self.assertEqual(words, [{'text': 'Hola', 'start': 0, 'end': 4}, {'text': 'IA', 'start': 5, 'end': 7}])


class PublishingTests(Fixture):
    def setUp(self):
        super().setUp()
        patcher = patch('marketing.publish.verify_video', return_value={'seconds': 40})
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch('marketing.publish.YouTubeAuth.token', return_value='test-token')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_wrong_confirmation_does_not_call_provider(self):
        job = self.ready()
        http = FakeHttp()
        with self.assertRaises(AppError):
            Publisher(self.config, self.store, http).publish(job['id'], 'youtube', 'bad')
        self.assertEqual(http.calls, [])

    def test_changed_video_invalidates_preview(self):
        job = self.ready()
        Path(job['video']['path']).write_bytes(b'changed')
        with self.assertRaises(AppError):
            Publisher(self.config, self.store).preview(job['id'], 'youtube')

    def test_existing_hashtags_are_not_appended_again(self):
        job = self.ready()
        copy = job['agents']['06-thumbnail-copy']
        copy.update(instagram_caption='Demo #IA #Automatización',
                    youtube_description='Demo #IA #Automatización',
                    hashtags=['#ia', '#Automatización', '#Negocios', '#NEGOCIOS'])
        job['video']['synthetic_voice'] = True
        self.store.save(job)
        publisher = Publisher(self.config, self.store)
        for platform, field in [('youtube', 'description'), ('instagram', 'caption')]:
            with self.subTest(platform=platform):
                preview = publisher.preview(job['id'], platform, video_url='https://example.test/reel.mp4')
                self.assertEqual(preview[field], 'Demo #IA #Automatización\n\n#Negocios\n\nVoz generada con IA.')

    def test_instagram_counts_hashtags_in_the_rendered_caption(self):
        job = self.ready()
        copy = job['agents']['06-thumbnail-copy']
        copy.update(instagram_caption='Demo ' + ' '.join('#tag' + str(i) for i in range(30)),
                    hashtags=['#extra'])
        self.store.save(job)
        with self.assertRaisesRegex(AppError, '30 hashtags'):
            Publisher(self.config, self.store).preview(job['id'], 'instagram', video_url='https://example.test/reel.mp4')

    def test_wrong_channel_stops_before_upload(self):
        job = self.ready()
        http = FakeHttp([{'items': [{'id': 'another-channel'}]}])
        publisher = Publisher(self.config, self.store, http)
        preview = publisher.preview(job['id'], 'youtube')
        with self.assertRaises(AppError):
            publisher.publish(job['id'], 'youtube', preview['confirmation'])
        self.assertIsNone(self.store.publication(job['id'], 'youtube'))

    def test_ambiguous_channel_identity_cannot_upload(self):
        job = self.ready()
        http = FakeHttp([{'items': [{'id': 'channel-123'}, {'id': 'another-channel'}]}])
        publisher = Publisher(self.config, self.store, http)
        preview = publisher.preview(job['id'], 'youtube')
        with self.assertRaises(AppError):
            publisher.publish(job['id'], 'youtube', preview['confirmation'])
        self.assertIsNone(self.store.publication(job['id'], 'youtube'))

    def test_youtube_upload_is_idempotent_and_private_by_default(self):
        job = self.ready()
        http = FakeHttp([{'items': [{'id': 'channel-123'}]}], [
            (200, {'location': 'https://www.googleapis.com/upload/session'}, b''),
            (308, {}, b''), (201, {}, b'{"id":"abcdefghijk"}')])
        publisher = Publisher(self.config, self.store, http)
        preview = publisher.preview(job['id'], 'youtube')
        first = publisher.publish(job['id'], 'youtube', preview['confirmation'])
        second = publisher.publish(job['id'], 'youtube', preview['confirmation'])
        self.assertEqual(first, second)
        self.assertEqual(first['state'], 'uploaded')
        self.assertEqual(http.calls[1][2]['data']['status']['privacyStatus'], 'private')
        self.assertNotIn('upload_url', first)
        self.assertEqual(len(http.calls), 4)

    def test_lost_youtube_final_response_reconciles_same_session(self):
        job = self.ready()
        http = FakeHttp([{'items': [{'id': 'channel-123'}]}, {'items': [{'id': 'channel-123'}]}], [
            (200, {'Location': 'https://www.googleapis.com/upload/session'}, b''), (308, {}, b''),
            AppError('timeout'), (200, {}, b'{"id":"abcdefghijk"}')])
        publisher = Publisher(self.config, self.store, http)
        preview = publisher.preview(job['id'], 'youtube')
        with self.assertRaises(AppError):
            publisher.publish(job['id'], 'youtube', preview['confirmation'])
        self.assertEqual(self.store.publication(job['id'], 'youtube')['state'], 'unknown')
        receipt = publisher.publish(job['id'], 'youtube', preview['confirmation'])
        self.assertEqual(receipt['state'], 'uploaded')
        self.assertEqual(len([c for c in http.calls if c[0] == 'POST']), 1)

    def test_changed_visibility_does_not_reuse_old_confirmation(self):
        job = self.ready()
        http = FakeHttp()
        publisher = Publisher(self.config, self.store, http)
        preview = publisher.preview(job['id'], 'youtube')
        with self.assertRaises(AppError):
            publisher.publish(job['id'], 'youtube', preview['confirmation'], privacy='public')
        self.assertEqual(http.calls, [])

    def test_instagram_requires_identical_remote_video(self):
        job = self.ready()
        http = FakeHttp([{'user_id': '123456'}])
        http.remote_hash = 'different'
        publisher = Publisher(self.config, self.store, http)
        preview = publisher.preview(job['id'], 'instagram', video_url='https://example.test/reel.mp4')
        with self.assertRaises(AppError):
            publisher.publish(job['id'], 'instagram', preview['confirmation'], video_url=preview['video_url'])
        self.assertIsNone(self.store.publication(job['id'], 'instagram'))

    def test_instagram_resumes_same_container_then_publishes_once(self):
        job = self.ready()
        http = FakeHttp([{'user_id': '123456'}, {'id': '999'}, {'user_id': '123456'},
                         {'status_code': 'FINISHED'}, {'id': '888'}, {'permalink': 'https://www.instagram.com/reel/example/'}])
        http.remote_hash = job['video']['sha256']
        publisher = Publisher(self.config, self.store, http)
        preview = publisher.preview(job['id'], 'instagram', video_url='https://example.test/reel.mp4')
        call = lambda: publisher.publish(job['id'], 'instagram', preview['confirmation'], video_url=preview['video_url'])
        self.assertEqual(call()['state'], 'processing')
        record = self.store.publication(job['id'], 'instagram')
        record['next_check_at'] = 0
        self.store.put_publication(job['id'], 'instagram', record)
        self.assertEqual(call()['state'], 'published')
        self.assertEqual(call()['remote_id'], '888')
        self.assertEqual(len([c for c in http.calls if c[0] == 'POST' and c[1].endswith('/media')]), 1)
        self.assertEqual(len([c for c in http.calls if c[1].endswith('/media_publish')]), 1)

    def test_unknown_instagram_publish_does_not_repeat_post(self):
        job = self.ready()
        http = FakeHttp([{'user_id': '123456'}, {'id': '999'}, {'user_id': '123456'},
                         {'status_code': 'FINISHED'}, AppError('timeout'), {'user_id': '123456'}])
        http.remote_hash = job['video']['sha256']
        publisher = Publisher(self.config, self.store, http)
        preview = publisher.preview(job['id'], 'instagram', video_url='https://example.test/reel.mp4')
        call = lambda: publisher.publish(job['id'], 'instagram', preview['confirmation'], video_url=preview['video_url'])
        call()
        record = self.store.publication(job['id'], 'instagram')
        record['next_check_at'] = 0
        self.store.put_publication(job['id'], 'instagram', record)
        with self.assertRaises(AppError):
            call()
        with self.assertRaises(AppError):
            call()
        self.assertEqual(len([c for c in http.calls if c[1].endswith('/media_publish')]), 1)

    def test_instagram_read_failure_preserves_container_for_retry(self):
        job = self.ready()
        http = FakeHttp([{'user_id': '123456'}, {'id': '999'}, {'user_id': '123456'}, AppError('timeout')])
        http.remote_hash = job['video']['sha256']
        publisher = Publisher(self.config, self.store, http)
        preview = publisher.preview(job['id'], 'instagram', video_url='https://example.test/reel.mp4')
        call = lambda: publisher.publish(job['id'], 'instagram', preview['confirmation'], video_url=preview['video_url'])
        call()
        record = self.store.publication(job['id'], 'instagram')
        record['next_check_at'] = 0
        self.store.put_publication(job['id'], 'instagram', record)
        with self.assertRaises(AppError):
            call()
        record = self.store.publication(job['id'], 'instagram')
        self.assertEqual(record['state'], 'processing')
        self.assertEqual(record['container_id'], '999')

    def test_demo_cannot_publish(self):
        job = self.ready()
        job['demo'] = True
        self.store.save(job)
        with self.assertRaises(AppError):
            Publisher(self.config, self.store).preview(job['id'], 'youtube')

    def test_publication_blocks_editing_original_job(self):
        job = self.ready()
        self.store.put_publication(job['id'], 'youtube', {'state': 'unknown'})
        with self.assertRaises(AppError):
            self.workflow.revise(job['id'], 'Cambiar')

    def test_private_instagram_urls_rejected(self):
        for url in ('http://example.test/a', 'https://127.0.0.1/a', 'https://localhost/a', 'https://user:pass@example.test/a'):
            with self.subTest(url=url), self.assertRaises(AppError):
                public_url(url)


class TelegramTests(Fixture):
    def pending(self):
        job = self.drafted()
        script_hash = digest(job['script'])[:16]
        job['telegram'] = {'hash': script_hash, 'message_id': 300, 'chat': '100', 'user': '200'}
        self.store.save(job)
        query = {'data': f"yes:{job['id']}:{script_hash}", 'from': {'id': 200},
                 'message': {'message_id': 300, 'chat': {'id': 100}}}
        return job, query

    def test_other_user_cannot_approve(self):
        job, query = self.pending()
        query['from']['id'] = 999
        result = Telegram(self.config, self.store, FakeHttp()).handle(query)
        self.assertEqual(result, 'No autorizado.')
        self.assertEqual(self.store.get(job['id'])['state'], 'awaiting_approval')

    def test_stale_callback_cannot_approve(self):
        job, query = self.pending()
        self.workflow.revise(job['id'], 'Otro guion')
        Telegram(self.config, self.store, FakeHttp()).handle(query)
        self.assertEqual(self.store.get(job['id'])['state'], 'brief')

    def test_valid_callback_approves_only_current_script(self):
        job, query = self.pending()
        Telegram(self.config, self.store, FakeHttp()).handle(query)
        updated = self.store.get(job['id'])
        self.assertEqual(updated['state'], 'approved')
        self.assertEqual(updated['approval']['actor'], 'telegram:200')
        self.assertIsNone(updated['video'])


if __name__ == '__main__':
    unittest.main()
