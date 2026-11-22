import concurrent.futures
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from marketing.agents import Agents, BRIEF, Workflow
from marketing.config import Config
from marketing.store import Store
from marketing.telemetry import DATABASE_NAME, activity, main, process_probe, read_activity


PROJECT = Path(__file__).resolve().parents[1]


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {'MARKETING_TELEMETRY_ROOT': str(self.root)})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def update_run(self, run_id, **values):
        db = sqlite3.connect(self.root / 'runtime' / DATABASE_NAME)
        try:
            with db:
                columns = ','.join(name + '=?' for name in values)
                db.execute('UPDATE runs SET ' + columns + ' WHERE run_id=?', [*values.values(), run_id])
        finally:
            db.close()

    def config(self):
        (self.root / 'agents').mkdir(exist_ok=True)
        (self.root / 'config').mkdir(exist_ok=True)
        for name in ('00-orquestador', '07-analista'):
            (self.root / f'agents/{name}.md').write_text('# Contrato de prueba', encoding='utf-8')
        for name in ('brand-guidelines.json', 'video-style.json'):
            shutil.copyfile(PROJECT / 'config' / name, self.root / 'config' / name)
        return Config(self.root, env={'OPENAI_API_KEY': 'sk-private-fixture-value'})

    def test_reading_missing_telemetry_creates_nothing(self):
        data = read_activity(self.root)
        self.assertFalse(data['available'])
        self.assertEqual(data['runs'], [])
        self.assertFalse((self.root / 'runtime').exists())

    def test_context_records_real_start_and_completion(self):
        with activity(self.root, '13-motion', 'Render de títulos', job_id='job1') as scope:
            data = read_activity(self.root)
            self.assertTrue(scope.available)
            self.assertEqual(data['runs'][0]['status'], 'active')
            self.assertTrue(data['runs'][0]['verified_active'])
            self.assertEqual(data['runs'][0]['pid'], os.getpid())
            self.assertEqual(data['events'][0]['kind'], 'started')
        final = read_activity(self.root)
        self.assertEqual(final['runs'][0]['status'], 'completed')
        self.assertFalse(final['runs'][0]['verified_active'])
        self.assertIsNotNone(final['runs'][0]['finished_at'])
        self.assertEqual([event['kind'] for event in final['events']], ['completed', 'started'])

    def test_telemetry_storage_failure_does_not_stop_the_real_task(self):
        with patch('marketing.telemetry.initialize', side_effect=sqlite3.OperationalError('PRIVATE_STORAGE_ERROR')):
            with self.assertWarnsRegex(RuntimeWarning, 'el trabajo continúa'):
                with activity(self.root, '13-motion', 'Render') as scope:
                    self.assertFalse(scope.available)
        data = read_activity(self.root)
        self.assertFalse(data['available'])
        self.assertNotIn('PRIVATE_STORAGE_ERROR', json.dumps(data))

    def test_errors_and_interruptions_never_store_exception_text(self):
        for exception in (RuntimeError('PRIVATE_EXCEPTION'), KeyboardInterrupt('PRIVATE_INTERRUPT')):
            with self.assertRaises(type(exception)):
                with activity(self.root, '09-montaje', 'Montar export'):
                    raise exception
        data = read_activity(self.root)
        self.assertEqual({run['status'] for run in data['runs']}, {'error', 'interrupted'})
        self.assertNotIn('PRIVATE_', json.dumps(data))

    def test_expired_heartbeat_never_counts_as_working(self):
        with activity(self.root, '13-motion', 'Render') as scope:
            old = (datetime.now(timezone.utc) - timedelta(seconds=11)).isoformat()
            self.update_run(scope.run_id, heartbeat_at=old)
            run = read_activity(self.root)['runs'][0]
            self.assertEqual(run['status'], 'stale')
            self.assertFalse(run['verified_active'])
            self.assertEqual(run['recorded_status'], 'active')

    def test_dead_or_reused_pid_is_interrupted_even_with_fresh_heartbeat(self):
        with activity(self.root, '13-motion', 'Render'):
            for probe in ((False, None), (True, 'different-process-identity')):
                with patch('marketing.telemetry.process_probe', return_value=probe):
                    run = read_activity(self.root)['runs'][0]
                    self.assertEqual(run['status'], 'interrupted')
                    self.assertFalse(run['verified_active'])

    def test_real_child_process_death_invalidates_fresh_activity(self):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])
        try:
            alive, identity = process_probe(child.pid)
            self.assertTrue(alive)
            self.assertIsNotNone(identity)
            with activity(self.root, '13-motion', 'Validación de proceso') as scope:
                self.update_run(scope.run_id, pid=child.pid, process_identity=identity)
                self.assertTrue(read_activity(self.root)['runs'][0]['verified_active'])
                child.terminate()
                child.wait(timeout=5)
                run = read_activity(self.root)['runs'][0]
                self.assertEqual(run['status'], 'interrupted')
                self.assertFalse(run['verified_active'])
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=5)

    def test_unknown_pid_is_not_verified(self):
        with activity(self.root, '13-motion', 'Render'):
            for probe in ((None, None), (True, None)):
                with patch('marketing.telemetry.process_probe', return_value=probe):
                    run = read_activity(self.root)['runs'][0]
                    self.assertEqual(run['status'], 'stale')
                    self.assertFalse(run['verified_active'])

    def test_heartbeat_updates_only_while_context_is_open(self):
        with patch('marketing.telemetry.HEARTBEAT_INTERVAL_SECONDS', 0.03):
            with activity(self.root, '13-motion', 'Render'):
                first = read_activity(self.root)['runs'][0]['heartbeat_at']
                deadline = time.monotonic() + 2
                current = first
                while current == first and time.monotonic() < deadline:
                    time.sleep(0.04)
                    current = read_activity(self.root)['runs'][0]['heartbeat_at']
                self.assertNotEqual(current, first)
            finished = read_activity(self.root)['runs'][0]['heartbeat_at']
            time.sleep(0.08)
            self.assertEqual(read_activity(self.root)['runs'][0]['heartbeat_at'], finished)

    def test_concurrent_runs_of_same_agent_are_not_overwritten(self):
        start = threading.Barrier(4)
        entered = threading.Barrier(4)
        release = threading.Event()
        def work(index):
            start.wait(timeout=15)
            with activity(self.root, '09-montaje', f'Tarea {index}'):
                entered.wait(timeout=15)
                release.wait(timeout=15)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(work, index) for index in range(3)]
            try:
                start.wait(timeout=15)
                entered.wait(timeout=15)
                data = read_activity(self.root)
                self.assertEqual(len(data['runs']), 3)
                self.assertEqual(len({run['run_id'] for run in data['runs']}), 3)
                self.assertTrue(all(run['verified_active'] for run in data['runs']))
            finally:
                release.set()
            for future in futures:
                future.result(timeout=15)
        self.assertTrue(all(run['status'] == 'completed' for run in read_activity(self.root)['runs']))

    def test_independent_cli_processes_keep_every_run_on_first_database_creation(self):
        children = []
        try:
            for index in range(4):
                children.append(subprocess.Popen([
                    sys.executable, '-m', 'marketing.telemetry', 'run', '--agent', '13-motion',
                    '--task', f'Proceso de validación {index}', '--root', str(self.root), '--',
                    sys.executable, '-c', 'pass'], cwd=PROJECT, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
            for child in children:
                stdout, stderr = child.communicate(timeout=30)
                self.assertEqual(child.returncode, 0, stderr.decode(errors='replace'))
                self.assertNotIn(b'RuntimeWarning', stderr)
            runs = read_activity(self.root)['runs']
            self.assertEqual(len(runs), 4)
            self.assertEqual(len({run['run_id'] for run in runs}), 4)
            self.assertTrue(all(run['status'] == 'completed' for run in runs))
        finally:
            for child in children:
                if child.poll() is None:
                    child.terminate()
                    child.communicate(timeout=5)

    def test_secret_patterns_are_redacted_and_skill_is_only_declared(self):
        with activity(self.root, '13-motion', 'Render token=PRIVATE_TOKEN\nPRIVATE_SECOND_LINE',
                      skill_id='motion-graphics', skill_evidence='declared_by_operator'):
            pass
        data = read_activity(self.root)
        self.assertNotIn('PRIVATE_', json.dumps(data))
        self.assertEqual(data['runs'][0]['skill_id'], 'motion-graphics')
        self.assertEqual(data['runs'][0]['skill_evidence'], 'declared_by_operator')

    def test_command_wrapper_runs_process_and_records_exit_without_command(self):
        command = 'import sys; private_argument = "PRIVATE_COMMAND_CONTENT"; sys.exit(3)'
        code = main(['run', '--agent', '13-motion', '--task', 'Validar proceso local',
                     '--skill', 'motion-graphics', '--root', str(self.root), '--', sys.executable, '-c', command])
        data = read_activity(self.root)
        self.assertEqual(code, 3)
        self.assertEqual(data['runs'][0]['status'], 'error')
        self.assertEqual(data['runs'][0]['exit_code'], 3)
        self.assertEqual(data['runs'][0]['source'], 'local_command')
        self.assertNotIn('PRIVATE_COMMAND_CONTENT', json.dumps(data))
        self.assertNotIn(sys.executable, json.dumps(data))

    def test_agents_instrumentation_uses_contract_without_claiming_skill(self):
        config = self.config()
        root = self.root
        class FakeHttp:
            def json(self, method, url, **kwargs):
                self.input = json.loads(kwargs['data']['input'])
                self.active = read_activity(root)['runs'][0]['verified_active']
                return {'status': 'completed', 'output': [{'type': 'message', 'content': [
                    {'type': 'output_text', 'text': '{"summary":"Plan","items":[]}'}]}]}
        http = FakeHttp()
        context = {'idea': 'PRIVATE_IDEA', '_office_job_id': 'job123'}
        result = Agents(config, http).run('00-orquestador', context, BRIEF)
        data = read_activity(self.root)
        self.assertEqual(result['summary'], 'Plan')
        self.assertTrue(http.active)
        self.assertNotIn('_office_job_id', http.input)
        self.assertIn('_office_job_id', context)  # The caller's context is preserved.
        self.assertIsNone(data['runs'][0]['skill_id'])
        self.assertEqual(data['runs'][0]['job_id'], 'job123')
        self.assertEqual(data['runs'][0]['source'], 'injected_client')
        self.assertNotIn('PRIVATE_IDEA', json.dumps(data))
        self.assertNotIn('sk-private', json.dumps(data))

    def test_api_failure_is_recorded_without_private_error(self):
        class FakeHttp:
            def json(self, *args, **kwargs):
                raise RuntimeError('PRIVATE_HTTP_ERROR')
        with self.assertRaises(RuntimeError):
            Agents(self.config(), FakeHttp()).run('00-orquestador', {}, BRIEF)
        data = read_activity(self.root)
        self.assertEqual(data['runs'][0]['status'], 'error')
        self.assertNotIn('PRIVATE_HTTP_ERROR', json.dumps(data))

    def test_workflow_adds_job_identity_to_telemetry_only(self):
        class FakeHttp:
            def json(self, method, url, **kwargs):
                self.input = json.loads(kwargs['data']['input'])
                return {'status': 'completed', 'output': [{'type': 'message', 'content': [
                    {'type': 'output_text', 'text': '{"changes":[],"new_hook":"Prueba"}'}]}]}
        config = self.config()
        store = Store(config.runtime)
        job = store.create('Idea de prueba')
        http = FakeHttp()
        workflow = Workflow(config, store, Agents(config, http))
        workflow.analyze(job['id'], {'retencion_3s': 20, 'retencion_50pct': 10, 'comentarios': 1, 'compartidos': 2})
        run = read_activity(self.root)['runs'][0]
        self.assertEqual(run['job_id'], job['id'])
        self.assertNotIn('_office_job_id', http.input)


if __name__ == '__main__':
    unittest.main()
