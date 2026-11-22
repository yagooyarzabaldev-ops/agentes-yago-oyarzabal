import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from marketing.office import attach_live_activity, build_snapshot


class LiveOfficeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root/'agents').mkdir()
        (self.root/'agents/13-motion.md').write_text('# Motion', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_activity_merges_without_turning_history_into_live_state(self):
        snapshot = build_snapshot(self.root, mode='snapshot', skill_paths={})
        runs = [{'run_id':'one','agent_id':'13-motion','task':'Render local','skill_id':None,
                 'status':'active','verified_active':True,'source':'cli','started_at':'2026-11-21T20:00:00Z'},
                {'run_id':'two','agent_id':'13-motion','task':'Otra tarea','skill_id':'motion-graphics',
                 'skill_evidence':'declared_by_operator','status':'active','verified_active':True,
                 'source':'local_command','started_at':'2026-11-21T20:01:00Z'}]
        with patch('marketing.telemetry.read_activity', return_value={'available':True,'runs':runs}), patch('marketing.codex_activity.read_codex_activity', return_value={'available':False}):
            attach_live_activity(snapshot, self.root)
        self.assertEqual(snapshot['summary']['active_verified'], 1)
        self.assertEqual(snapshot['summary']['active_runs'], 2)
        self.assertEqual(snapshot['agents'][0]['current_skill'], 'Motion graphics')
        self.assertEqual(snapshot['agents'][0]['status'], 'sin_registro')

    def test_stale_never_counts_as_working(self):
        snapshot=build_snapshot(self.root, mode='snapshot', skill_paths={})
        with patch('marketing.telemetry.read_activity',return_value={'available':True,'runs':[{'agent_id':'13-motion','status':'stale','verified_active':False,'task':'Sin señal'}]}), patch('marketing.codex_activity.read_codex_activity',return_value={'available':False}):
            attach_live_activity(snapshot,self.root)
        self.assertEqual(snapshot['summary']['active_verified'],0)
        self.assertEqual(snapshot['agents'][0]['live_status'],'stale')

    def test_real_command_task_stays_visible_until_command_finishes(self):
        snapshot = build_snapshot(self.root, mode='snapshot', skill_paths={})
        command = {'agent_id': '13-motion', 'source': 'local_command', 'status': 'active',
                   'verified_active': True, 'task': 'Renderizando video', 'skill_id': 'motion-graphics',
                   'heartbeat_at': '2026-11-21T20:00:00Z'}
        codex = {'agent_id': '13-motion', 'source': 'codex', 'status': 'active',
                 'verified_active': True, 'task': 'Organizando el siguiente paso',
                 'heartbeat_at': '2026-11-21T20:00:01Z'}
        with patch('marketing.telemetry.read_activity', return_value={'runs': [command]}), patch('marketing.codex_activity.read_codex_activity', return_value={'runs': [codex]}):
            attach_live_activity(snapshot, self.root)
            self.assertEqual(snapshot['agents'][0]['current_task'], 'Renderizando video')
            self.assertEqual(snapshot['agents'][0]['current_skill'], 'Motion graphics')
            command.update(status='completed', verified_active=False)
            attach_live_activity(snapshot, self.root)
            self.assertEqual(snapshot['agents'][0]['current_task'], 'Organizando el siguiente paso')

    def test_snapshot_export_does_not_claim_live_observation(self):
        with patch('marketing.telemetry.read_activity',side_effect=AssertionError('Should not observe runtime')):
            snapshot=build_snapshot(self.root,mode='snapshot',skill_paths={})
        self.assertEqual(snapshot['source']['mode'],'snapshot')
        self.assertNotIn('live_status',snapshot['agents'][0])


if __name__=='__main__':
    unittest.main()
