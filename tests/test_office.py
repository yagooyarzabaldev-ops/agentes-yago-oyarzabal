import hashlib
import http.client
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from pathlib import Path

from marketing.office import build_snapshot, export_snapshot, make_handler, read_jobs


class OfficeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.telemetry_env = patch.dict(os.environ, {'MARKETING_TELEMETRY_ROOT': str(self.root)})
        self.telemetry_env.start()
        (self.root / 'agents').mkdir()
        (self.root / 'agents/02-guionista.md').write_text('# Guionista\nContrato.', encoding='utf-8')

    def tearDown(self):
        self.telemetry_env.stop()
        self.temp.cleanup()

    def create_db(self, job):
        (self.root / 'runtime').mkdir(exist_ok=True)
        path = self.root / 'runtime/marketing.sqlite3'
        db = sqlite3.connect(path)
        try:
            with db:
                db.execute('CREATE TABLE jobs(body TEXT)')
                db.execute('INSERT INTO jobs VALUES (?)', (json.dumps(job),))
        finally:
            db.close()
        return path

    def test_missing_database_does_not_create_runtime(self):
        result = build_snapshot(self.root, skill_paths={})
        self.assertEqual(result['summary']['jobs_total'], 0)
        self.assertFalse((self.root / 'runtime').exists())
        self.assertEqual(result['agents'][0]['status'], 'sin_registro')

    def test_snapshot_is_read_only_and_does_not_export_private_fields(self):
        path = self.create_db({'id': 'abc123', 'idea': 'Trabajo', 'state': 'brief',
                               'created_at': '2026-11-21T00:00:00Z',
                               'agents': {'02-guionista': {'secret': 'PRIVATE_RESPONSE'}},
                               'credentials': {'api_key': 'PRIVATE_KEY'},
                               'recording': {'path': 'PRIVATE_RECORDING'},
                               'feedback': ['PRIVATE_FEEDBACK']})
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        result = build_snapshot(self.root, skill_paths={})
        after = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.assertNotIn('PRIVATE_', json.dumps(result))
        self.assertEqual(result['agents'][0]['status'], 'sin_telemetria')
        self.assertEqual(result['summary']['active_verified'], 0)
        self.assertFalse(result['source']['heartbeat_available'])

    def test_existing_lock_does_not_imply_running(self):
        self.create_db({'id': 'test', 'state': 'brief', 'agents': {}})
        (self.root / 'runtime/locks').mkdir()
        (self.root / 'runtime/locks/test.lock').write_text('0')
        result = build_snapshot(self.root, skill_paths={})
        self.assertEqual(result['agents'][0]['status'], 'sin_registro')
        self.assertEqual(result['summary']['active_verified'], 0)

    def test_skill_presence_does_not_mean_automatic_link(self):
        skill = self.root / 'SKILL.md'
        skill.write_text('Test skill')
        result = build_snapshot(self.root, skill_paths={'imagegen': skill})
        image = next(s for s in result['skills'] if s['id'] == 'imagegen')
        self.assertTrue(image['available'])
        self.assertFalse(image['linked_automatically'])
        self.assertEqual(result['summary']['skills_linked_automatically'], 0)

    def test_demo_records_are_labeled_separately(self):
        self.create_db({'id': 'demo123', 'idea': 'Ejemplo', 'state': 'demo',
                        'agents': {'02-guionista': {'summary': 'Demo'}}})
        result = build_snapshot(self.root, skill_paths={})
        self.assertTrue(result['jobs'][0]['is_demo'])
        self.assertEqual(result['jobs'][0]['pending_agents'], [])
        self.assertTrue(result['activity'][0]['is_demo'])
        self.assertEqual(result['agents'][0]['demo_records_count'], 1)
        self.assertEqual(result['agents'][0]['production_records_count'], 0)

    def test_snapshot_mode_and_redaction(self):
        self.create_db({'id': 'test', 'idea': 'token=secret-value\nPRIVATE_REST', 'state': 'brief'})
        export = self.root / 'snapshot.json'
        export_snapshot(export, self.root)
        result = json.loads(export.read_text(encoding='utf-8'))
        self.assertEqual(result['source']['mode'], 'snapshot')
        self.assertNotIn('secret-value', export.read_text(encoding='utf-8'))
        self.assertNotIn('PRIVATE_REST', export.read_text(encoding='utf-8'))

    def test_corrupt_database_fails_without_exposing_details(self):
        (self.root / 'runtime').mkdir()
        (self.root / 'runtime/marketing.sqlite3').write_text('private-data not a database')
        jobs, warnings = read_jobs(self.root)
        self.assertEqual(jobs, [])
        self.assertTrue(warnings)
        self.assertNotIn('private-data', str(warnings))

    def test_http_only_serves_site_and_rejects_cross_origin(self):
        site = self.root / 'dist'
        site.mkdir()
        (site / 'index.html').write_text('<h1>Oficina</h1>')
        (self.root / '.env.local').write_text('PRIVATE')
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.root, site))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def request(path, headers=None, method='GET'):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            status, body = response.status, response.read()
            connection.close()
            return status, body
        try:
            self.assertEqual(request('/')[0], 200)
            self.assertEqual(request('/api/office')[0], 200)
            self.assertEqual(request('/../.env.local')[0], 404)
            self.assertEqual(request('/%2e%2e/.env.local')[0], 404)
            self.assertEqual(request('/%5c..%5c.env.local')[0], 404)
            self.assertEqual(request('/api/office', {'Origin': 'https://example.com'})[0], 403)
            self.assertEqual(request('/api/office', {'Host': 'evil.example'})[0], 403)
            self.assertEqual(request('/api/office', {'Host': '['})[0], 403)
            self.assertEqual(request('/%00')[0], 404)
            self.assertEqual(request('/api/office', method='POST')[0], 405)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
