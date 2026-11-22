import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from marketing.codex_activity import CodexObserver, _tool_observation


class CodexActivityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project'
        self.root.mkdir()
        self.sessions = Path(self.temp.name) / 'sessions'
        self.day = self.sessions / '2026/11/21'
        self.day.mkdir(parents=True)
        self.now = datetime(2026, 11, 21, 23, 0, tzinfo=timezone.utc).timestamp()

    def stamp(self, offset=0):
        return datetime.fromtimestamp(self.now + offset, timezone.utc).isoformat()

    def write(self, path, typ, payload, offset=0):
        with path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'timestamp': self.stamp(offset), 'type': typ, 'payload': payload}) + '\n')

    def session(self, name='root', *, cwd=None, parent=None, agent_path=None):
        path = self.day / (name + '.jsonl')
        meta = {'id': name, 'cwd': str(cwd or self.root), 'base_instructions': {'text': 'NEVER_EXPORT_SECRET'}}
        if parent:
            meta.update(thread_source='subagent', source={'subagent': {'thread_spawn': {'parent_thread_id': parent, 'agent_path': agent_path}}})
        self.write(path, 'session_meta', meta)
        self.write(path, 'event_msg', {'type': 'task_started', 'turn_id': 'turn1'})
        return path

    def test_recent_lifecycle_and_stale_are_distinct(self):
        self.session()
        observer = CodexObserver(self.root, self.sessions)
        result = observer.snapshot(self.now + 1)
        self.assertTrue(result['runs'][0]['verified_active'])
        self.assertEqual(result['runs'][0]['agent_id'], '00-orquestador')
        stale = observer.snapshot(self.now + 91)['runs'][0]
        self.assertFalse(stale['verified_active'])
        self.assertEqual(stale['status'], 'stale')

    def test_incomplete_initial_metadata_is_retried_after_file_changes(self):
        path = self.day / 'partial-metadata.jsonl'
        metadata = json.dumps({'type': 'session_meta', 'payload': {
            'id': 'partial-metadata', 'cwd': str(self.root)}}) + '\n'
        path.write_text(metadata[:30], encoding='utf-8')
        observer = CodexObserver(self.root, self.sessions)
        self.assertEqual(observer.snapshot(self.now)['runs'], [])
        # Finish the same file after discovery, without restarting the observer.
        with path.open('a', encoding='utf-8') as stream:
            stream.write(metadata[30:])
        self.write(path, 'event_msg', {'type': 'task_started', 'turn_id': 'turn1'}, 1)
        runs = observer.snapshot(self.now + 11)['runs']
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['agent_id'], '00-orquestador')
        self.assertTrue(runs[0]['verified_active'])

    def test_recent_activity_in_an_old_rollout_directory_is_discovered(self):
        old_day = self.sessions / '2026/11/18'
        old_day.mkdir(parents=True)
        path = old_day / 'resumed-chat.jsonl'
        self.write(path, 'session_meta', {'id': 'resumed-chat', 'cwd': str(self.root)}, -3 * 86400)
        self.write(path, 'event_msg', {'type': 'task_started', 'turn_id': 'resumed-turn'})
        runs = CodexObserver(self.root, self.sessions).snapshot(self.now + 1)['runs']
        self.assertEqual(len(runs), 1)
        self.assertTrue(runs[0]['verified_active'])

    def test_new_old_directory_is_found_on_bounded_historical_refresh(self):
        observer = CodexObserver(self.root, self.sessions)
        self.assertEqual(observer.snapshot(self.now)['runs'], [])
        old_day = self.sessions / '2026/11/18'
        old_day.mkdir(parents=True)
        path = old_day / 'late-old-chat.jsonl'
        self.write(path, 'session_meta', {'id': 'late-old-chat', 'cwd': str(self.root)}, -3 * 86400)
        self.write(path, 'event_msg', {'type': 'task_started', 'turn_id': 'resumed-turn'}, 1)
        # Ordinary polls need not walk historical directories each time.
        self.assertEqual(observer.snapshot(self.now + 11)['runs'], [])
        runs = observer.snapshot(self.now + 61)['runs']
        self.assertEqual(len(runs), 1)
        self.assertTrue(runs[0]['verified_active'])

    def test_task_complete_and_interrupted(self):
        path = self.session()
        self.write(path, 'event_msg', {'type': 'task_complete', 'turn_id': 'turn1', 'last_agent_message': 'PRIVATE_RESULT'}, 2)
        observer = CodexObserver(self.root, self.sessions)
        run = observer.snapshot(self.now + 3)['runs'][0]
        self.assertEqual(run['status'], 'completed')
        self.assertFalse(run['verified_active'])
        self.write(path, 'event_msg', {'type': 'task_started', 'turn_id': 'turn2'}, 4)
        self.write(path, 'event_msg', {'type': 'turn_aborted', 'turn_id': 'turn2'}, 5)
        self.assertEqual(observer.snapshot(self.now + 6)['runs'][0]['status'], 'interrupted')

    def test_only_project_and_recognized_descendants_are_returned(self):
        self.session()
        self.session('other', cwd=self.root.parent / 'unrelated')
        self.session('child', cwd=self.root.parent / 'visualizations', parent='root', agent_path='/root/motion_oficina')
        self.session('unknown', parent='root', agent_path='/root/unknown_role')
        result = CodexObserver(self.root, self.sessions).snapshot(self.now + 1)
        self.assertEqual({r['agent_id'] for r in result['runs']}, {'00-orquestador', '13-motion'})

    def test_reasoning_prompts_results_and_commands_are_not_exported(self):
        path = self.session()
        for typ in ('reasoning', 'message', 'agent_message'):
            self.write(path, 'response_item', {'type': typ, 'content': 'PRIVATE_CONTENT', 'summary': 'PRIVATE_REASONING'}, 1)
        self.write(path, 'response_item', {'type': 'function_call', 'name': 'exec_command', 'call_id': 'call_a', 'arguments': json.dumps({'cmd': 'echo sk-proj-PRIVATE_TOKEN'})}, 2)
        self.write(path, 'response_item', {'type': 'function_call_output', 'call_id': 'call_a', 'output': 'PRIVATE_RESULT'}, 3)
        encoded = json.dumps(CodexObserver(self.root, self.sessions).snapshot(self.now + 4))
        for private in ('PRIVATE_CONTENT', 'PRIVATE_REASONING', 'PRIVATE_TOKEN', 'PRIVATE_RESULT', 'NEVER_EXPORT_SECRET', str(self.root)):
            self.assertNotIn(private, encoded)

    def test_skill_read_is_not_skill_execution(self):
        path = self.session()
        command = "Get-Content -LiteralPath 'C:/skills/sites/SKILL.md'"
        self.write(path, 'response_item', {'type': 'custom_tool_call', 'name': 'exec', 'call_id': 'call_a', 'input': 'text(await tools.exec_command({cmd:' + json.dumps(command) + '}));'}, 1)
        observer = CodexObserver(self.root, self.sessions)
        run = observer.snapshot(self.now + 2)['runs'][0]
        self.assertEqual(run['skill_id'], 'sites')
        self.assertEqual(run['skill_evidence'], 'instructions_read_in_turn')
        self.write(path, 'response_item', {'type': 'custom_tool_call_output', 'call_id': 'call_a', 'output': 'PRIVATE_SKILL_CONTENT'}, 3)
        self.write(path, 'response_item', {'type': 'function_call', 'name': 'image_gen__imagegen', 'call_id': 'call_b', 'arguments': '{"prompt":"PRIVATE_PROMPT"}'}, 4)
        run = observer.snapshot(self.now + 5)['runs'][0]
        self.assertEqual(run['skill_id'], 'imagegen')
        self.assertEqual(run['skill_evidence'], 'tool_execution')
        self.write(path, 'response_item', {'type': 'custom_tool_call_output', 'call_id': 'call_b', 'output': 'PRIVATE_IMAGE'}, 6)
        run = observer.snapshot(self.now + 7)['runs'][0]
        self.assertEqual(run['skill_id'], 'sites')
        self.assertEqual(run['skill_evidence'], 'instructions_read_in_turn')

    def test_nested_source_does_not_prove_imagegen_execution(self):
        for source in (
            'await tools.image_gen__imagegen({prompt:"example"});',
            'const run=async()=>tools.image_gen__imagegen({});',
            'const text="tools.image_gen__imagegen({})";',
            '// tools.image_gen__imagegen({});',
            '/* tools.image_gen__imagegen({}); */',
            'await tools.apply_patch("+await tools.image_gen__imagegen({});");',
        ):
            with self.subTest(source=source):
                self.assertIsNone(_tool_observation({'name': 'exec', 'input': source})[1])

    def test_unquoted_literal_skill_reads_from_real_agent_commands(self):
        for folder, expected in (
            ('motion-graphics-reels', 'motion-graphics'),
            ('editar-reels-claude', 'editar-reels'),
            ('watch', 'watch'),
        ):
            command = 'Get-Content -LiteralPath D:/Herramientas/marketing/skills/' + folder + '/SKILL.md'
            source = 'text(await tools.exec_command({cmd:' + json.dumps(command) + '}));'
            with self.subTest(folder=folder):
                self.assertEqual(_tool_observation({'name': 'exec', 'input': source})[2], expected)
        for command in (
            'Write-Output Get-Content D:/skills/watch/SKILL.md',
            'Get-Content $skill/watch/SKILL.md',
            '# Get-Content D:/skills/watch/SKILL.md',
        ):
            self.assertIsNone(_tool_observation({'name': 'exec_command', 'arguments': json.dumps({'cmd': command})})[2])

    def test_skill_read_examples_in_strings_comments_and_patches_are_ignored(self):
        invocation = 'tools.exec_command({cmd:' + json.dumps("Get-Content 'C:/skills/sites/SKILL.md'") + '})'
        examples = [
            'const example=' + json.dumps(invocation) + ';',
            '// ' + invocation,
            '/* ' + invocation + ' */',
            'const template=`' + invocation + '`;',
            'await tools.apply_patch(' + json.dumps('*** Begin Patch\n+' + invocation) + ');',
        ]
        for source in examples:
            with self.subTest(source=source):
                self.assertIsNone(_tool_observation({'name': 'exec', 'input': source})[2])
        self.assertEqual(_tool_observation({'name': 'exec', 'input': 'await ' + invocation})[2], 'sites')

    def test_shell_string_or_comment_is_not_a_skill_read(self):
        for command in (
            'Write-Output "example; Get-Content \'C:/skills/sites/SKILL.md\'"',
            "# Get-Content 'C:/skills/sites/SKILL.md'",
            "@'\nGet-Content 'C:/skills/sites/SKILL.md'\n'@",
        ):
            with self.subTest(command=command):
                self.assertIsNone(_tool_observation({'name': 'exec_command', 'arguments': json.dumps({'cmd': command})})[2])

    def test_canonical_underscore_task_names_map_to_known_roles(self):
        self.session()
        for name in ('13_motion', '11_control_calidad', '06_thumbnail_copy'):
            self.session(name, parent='root', agent_path='/root/' + name)
        runs = CodexObserver(self.root, self.sessions).snapshot(self.now + 1)['runs']
        self.assertEqual({r['agent_id'] for r in runs}, {'00-orquestador', '13-motion', '11-control-calidad', '06-thumbnail-copy'})

    def test_partial_record_is_read_only_after_newline_and_cache_is_incremental(self):
        path = self.session()
        observer = CodexObserver(self.root, self.sessions)
        observer.snapshot(self.now + 1)
        old_offset = observer.sessions[path].offset
        row = json.dumps({'timestamp': self.stamp(2), 'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': 'turn1'}})
        with path.open('a', encoding='utf-8') as stream:
            stream.write(row)
        observer.snapshot(self.now + 3)
        self.assertEqual(observer.sessions[path].offset, old_offset)
        with path.open('a', encoding='utf-8') as stream:
            stream.write('\n')
        result = observer.snapshot(self.now + 4)
        self.assertEqual(result['runs'][0]['status'], 'completed')
        self.assertGreater(observer.sessions[path].offset, old_offset)

    def test_other_turn_completion_does_not_stop_current_turn(self):
        path = self.session()
        self.write(path, 'event_msg', {'type': 'task_complete', 'turn_id': 'oldturn'}, 1)
        result = CodexObserver(self.root, self.sessions).snapshot(self.now + 2)
        self.assertTrue(result['runs'][0]['verified_active'])

    def test_oversized_unrelated_record_cannot_block_later_lifecycle_events(self):
        path = self.session()
        self.write(path, 'response_item', {'type': 'reasoning', 'content': 'x' * 2_100_000}, 1)
        self.write(path, 'event_msg', {'type': 'task_complete', 'turn_id': 'turn1'}, 2)
        result = CodexObserver(self.root, self.sessions).snapshot(self.now + 3)
        self.assertEqual(result['runs'][0]['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
