"""Observe project-scoped Codex lifecycle metadata without exporting chat content.

The JSONL rollout format is an observed local interface, not a guaranteed API.
Unknown records are ignored. A recent lifecycle signal proves recent activity,
not a continuously alive model process; silent sessions become stale after 90s.
"""
from __future__ import annotations

import json
import re
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path


STALE_SECONDS = 90
DISCOVERY_SECONDS = 10
HISTORICAL_DISCOVERY_SECONDS = 60
ROLE_IDS = {
    '00-orquestador', '01-trend-hunter', '02-guionista', '03-roulette-master',
    '04-director-visual', '05-voz', '06-thumbnail-copy', '07-analista',
    '08-publicador', '09-montaje', '10-musica', '11-control-calidad',
    '12-referencias', '13-motion',
}
ROLE_ALIASES = {
    'motion_oficina': '13-motion', 'monitor_datos': '11-control-calidad',
    'observador_codex': '07-analista',
}
SKILL_PATHS = {
    'sites': '/sites/skill.md', 'imagegen': '/imagegen/skill.md',
    'motion-graphics': '/motion-graphics-reels/skill.md',
    'editar-reels': '/editar-reels-claude/skill.md',
    'watch': '/watch/skill.md', 'built-in-browser': '/built-in-browser/skill.md',
    'openai-docs': '/openai-docs/skill.md',
}
TOOL_TASKS = {
    'exec': 'Usando herramientas del proyecto',
    'exec_command': 'Ejecutando un comando del proyecto',
    'apply_patch': 'Editando archivos del proyecto',
    'spawn_agent': 'Asignando trabajo a un especialista',
    'followup_task': 'Coordinando un especialista',
    'send_message': 'Coordinando el equipo',
    'wait_agent': 'Esperando a un especialista',
    'write_stdin': 'Consultando un proceso en ejecución',
    'wait': 'Esperando una herramienta',
    'js': 'Revisando la interfaz en el navegador',
    'imagegen': 'Generando o editando una imagen',
}
_CACHES = {}
_CACHE_LOCK = threading.Lock()


def _iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def _epoch(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (ValueError, OverflowError):
        return None


def _path_key(value):
    return str(value or '').replace('\\', '/').rstrip('/').casefold()


def _identifier(value):
    return value if isinstance(value, str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', value) else None


def _metadata(path):
    """Read only the first record and retain an explicit metadata allowlist."""
    try:
        with path.open('rb') as stream:
            raw = stream.readline(2_000_001)
        if len(raw) > 2_000_000 or not raw.endswith(b'\n'):
            return None
        row = json.loads(raw)
    except (OSError, ValueError):
        return None
    if row.get('type') != 'session_meta':
        return None
    payload = row.get('payload')
    if not isinstance(payload, dict):
        return None
    source = payload.get('source')
    spawn = source.get('subagent', {}).get('thread_spawn', {}) if isinstance(source, dict) else {}
    if not isinstance(spawn, dict):
        spawn = {}
    roots = payload.get('runtime_workspace_roots')
    return {
        'id': _identifier(payload.get('id')),
        'cwd': _path_key(payload.get('cwd')),
        'roots': [_path_key(p) for p in roots if isinstance(p, str)] if isinstance(roots, list) else [],
        'parent': _identifier(payload.get('parent_thread_id') or spawn.get('parent_thread_id')),
        'agent_path': payload.get('agent_path') or spawn.get('agent_path'),
        'subagent': payload.get('thread_source') == 'subagent' or bool(spawn),
        'offset': len(raw),
    }


def _role(meta):
    if not meta['subagent']:
        return '00-orquestador'
    path = meta.get('agent_path')
    if not isinstance(path, str):
        return None
    leaf = path.rsplit('/', 1)[-1]
    canonical = leaf.replace('_', '-')
    return canonical if canonical in ROLE_IDS else ROLE_ALIASES.get(leaf)


def _js_code_mask(source):
    """Preserve code offsets while removing strings, templates and comments.

    This is deliberately a conservative lexical filter, not a JS interpreter.
    Template expressions are masked with their template; missed evidence is
    preferable to treating example code or patch content as an invocation.
    """
    masked = list(source)
    index, size = 0, len(source)
    while index < size:
        start = index
        char = source[index]
        if char in ('"', "'", '`'):
            quote = char
            index += 1
            while index < size:
                if source[index] == '\\':
                    index += 2
                elif source[index] == quote:
                    index += 1
                    break
                else:
                    index += 1
        elif source.startswith('//', index):
            index = source.find('\n', index)
            if index < 0:
                index = size
        elif source.startswith('/*', index):
            end = source.find('*/', index + 2)
            index = size if end < 0 else end + 2
        else:
            index += 1
            continue
        for offset in range(start, min(index, size)):
            if source[offset] != '\n':
                masked[offset] = ' '
    return ''.join(masked)


def _shell_statements(command):
    """Split direct statements outside shell strings/comments; stop here-docs."""
    index, start, quote, comment = 0, 0, None, False
    while index < len(command):
        char = command[index]
        if comment:
            if char == '\n':
                comment, start = False, index + 1
        elif quote:
            if char in ('`', '\\'):
                index += 1
            elif char == quote:
                if index + 1 < len(command) and command[index + 1] == quote:
                    index += 1
                else:
                    quote = None
        elif command.startswith(("@'", '@"', '<<'), index):
            return
        elif char in ('"', "'"):
            quote = char
        elif char == '#':
            yield command[start:index]
            comment = True
        elif char in (';', '\n'):
            yield command[start:index]
            start = index + 1
        index += 1
    if not comment and not quote:
        yield command[start:]


def _tool_observation(payload):
    """Reduce a tool call to fixed labels; never retain command arguments."""
    name = str(payload.get('name', ''))
    short = name.rsplit('__', 1)[-1].rsplit('.', 1)[-1]
    task = TOOL_TASKS.get(short, 'Usando una herramienta del proyecto')
    tool_skill = 'imagegen' if short == 'imagegen' else None
    consulted = None
    # The orchestration tool nests calls in source. Only inspect tool *input*,
    # never tool results, user text, agent messages, or reasoning records.
    source = payload.get('input', '') if short == 'exec' else ''
    commands = []
    if short == 'exec_command':
        try:
            args = json.loads(payload.get('arguments', '{}'))
            if isinstance(args, dict) and isinstance(args.get('cmd'), str):
                commands.append(args['cmd'])
        except (ValueError, TypeError):
            pass
    elif isinstance(source, str) and len(source) <= 2_000_000:
        code = _js_code_mask(source)
        if re.search(r'\btools\s*\.\s*apply_patch\s*\(', code):
            task = TOOL_TASKS['apply_patch']
        # A nested call written in orchestration source can be conditional or
        # inside an uncalled function. Only a direct tool record establishes
        # ImageGen execution; source text alone must not turn that skill on.
        # Match literal JSON string values at exec_command's cmd argument.
        # Other dynamically constructed commands intentionally remain unknown.
        for match in re.finditer(r'\btools\s*\.\s*exec_command\s*\(\s*\{\s*cmd\s*:', code):
            try:
                remaining = source[match.end():].lstrip()
                if remaining.startswith('"'):
                    value, _ = json.JSONDecoder().raw_decode(remaining)
                    if isinstance(value, str):
                        commands.append(value)
            except (ValueError, TypeError):
                pass
    for command in commands:
        # Match an actual direct file-read command, rather than a skill path
        # merely mentioned in a prompt, patch, here-string or Python source.
        for statement in _shell_statements(command):
            match = re.match(
                r'\s*(?:Get-Content\s+(?:-LiteralPath\s+)?|cat\s+)'
                r'(?:[\'\"]([^\'\"]+SKILL\.md)[\'\"]|([^\s;\'\"$`*?(){}]+/SKILL\.md)(?=\s|$))',
                statement, re.I)
            if match:
                normalized = _path_key(match.group(1) or match.group(2))
                for sid, suffix in SKILL_PATHS.items():
                    if normalized.endswith(suffix):
                        consulted = sid
    return task, tool_skill, consulted


class _Session:
    def __init__(self, path, meta, role):
        self.path, self.meta, self.role = path, meta, role
        self.offset = meta['offset']
        self.turn = None
        self.run = None
        self.events = deque(maxlen=40)
        self.consulted_skill = None
        self.active_tools = {}
        self.skip_long_record = False

    def _event(self, kind, at):
        if not self.run:
            return
        self.events.append({
            'event_id': f"codex:{self.meta['id']}:{self.offset}:{kind}",
            'run_id': self.run['run_id'], 'agent_id': self.role, 'job_id': None,
            'task': self.run['task'], 'skill_id': self.run['skill_id'],
            'skill_evidence': self.run['skill_evidence'], 'source': 'codex',
            'kind': kind, 'at': _iso(at), 'status': self.run['status'], 'exit_code': None,
        })

    def _consume(self, row):
        kind = row.get('type')
        if kind not in ('event_msg', 'response_item'):
            return
        payload = row.get('payload')
        if not isinstance(payload, dict):
            return
        typ = payload.get('type')
        # Early allowlist excludes reasoning and message content entirely.
        allowed_events = {'task_started', 'task_complete', 'turn_aborted', 'item_completed', 'token_count'}
        allowed_items = {'function_call', 'custom_tool_call', 'function_call_output', 'custom_tool_call_output'}
        if (kind == 'event_msg' and typ not in allowed_events) or (kind == 'response_item' and typ not in allowed_items):
            return
        at = _epoch(row.get('timestamp'))
        if at is None:
            return
        if kind == 'event_msg' and typ == 'task_started':
            turn = _identifier(payload.get('turn_id'))
            if not turn:
                return
            self.turn, self.consulted_skill, self.active_tools = turn, None, {}
            self.run = {
                'run_id': f"codex:{self.meta['id']}:{turn}", 'agent_id': self.role,
                'job_id': None, 'task': 'Organizando el trabajo del proyecto',
                'skill_id': None, 'skill_evidence': None, 'source': 'codex',
                'started_at': _iso(at), 'heartbeat_at': _iso(at), 'finished_at': None,
                'status': 'active', 'recorded_status': 'active',
                'verified_active': False, 'exit_code': None,
                'activity_evidence': 'project_session_lifecycle',
            }
            self._event('started', at)
            return
        if not self.run or self.run['status'] != 'active':
            return
        if kind == 'event_msg' and payload.get('turn_id') not in (None, self.turn):
            return
        self.run['heartbeat_at'] = _iso(at)
        if kind == 'event_msg' and typ in ('task_complete', 'turn_aborted'):
            self.run['status'] = 'completed' if typ == 'task_complete' else 'interrupted'
            self.run['recorded_status'] = self.run['status']
            self.run['finished_at'] = _iso(at)
            self.run['task'] = 'Turno finalizado' if typ == 'task_complete' else 'Turno interrumpido'
            self.active_tools = {}
            self.run['skill_id'] = self.consulted_skill
            self.run['skill_evidence'] = 'instructions_read_in_turn' if self.consulted_skill else None
            self._event(self.run['status'], at)
        elif kind == 'response_item' and typ in ('function_call', 'custom_tool_call'):
            task, tool_skill, consulted = _tool_observation(payload)
            if consulted:
                self.consulted_skill = consulted
            call_id = _identifier(payload.get('call_id'))
            if call_id:
                self.active_tools[call_id] = (task, tool_skill)
            self.run.update(task=task, skill_id=tool_skill or self.consulted_skill,
                            skill_evidence='tool_execution' if tool_skill else 'instructions_read_in_turn' if self.consulted_skill else None)
            self._event('tool_started', at)
        elif kind == 'response_item' and typ in ('function_call_output', 'custom_tool_call_output'):
            call_id = _identifier(payload.get('call_id'))
            self.active_tools.pop(call_id, None)
            # A result closes only its matching call. Simultaneous tools can
            # continue; order is insertion order, not an invented progress rate.
            task, tool_skill = next(reversed(self.active_tools.values())) if self.active_tools else ('Organizando el siguiente paso', None)
            self.run.update(task=task, skill_id=tool_skill or self.consulted_skill,
                            skill_evidence='tool_execution' if tool_skill else 'instructions_read_in_turn' if self.consulted_skill else None)
            self._event('tool_finished', at)

    def read(self):
        try:
            size = self.path.stat().st_size
            if size < self.offset:
                self.offset, self.run, self.turn = self.meta['offset'], None, None
                self.events.clear()
                self.active_tools.clear()
            with self.path.open('rb') as stream:
                stream.seek(self.offset)
                consumed = 0
                while consumed < 8_000_000:
                    line = stream.readline(2_000_001)
                    if not line:
                        break
                    if self.skip_long_record or len(line) > 2_000_000:
                        self.offset += len(line)
                        consumed += len(line)
                        self.skip_long_record = not line.endswith(b'\n')
                        continue
                    if not line.endswith(b'\n'):
                        # An incomplete trailing record may still be written.
                        break
                    self.offset += len(line)
                    consumed += len(line)
                    try:
                        row = json.loads(line)
                        if isinstance(row, dict):
                            self._consume(row)
                    except (ValueError, TypeError):
                        continue
        except OSError:
            return False
        return True


class CodexObserver:
    def __init__(self, root, sessions_dir=None):
        self.root = _path_key(Path(root).resolve())
        self.sessions_dir = Path(sessions_dir or Path.home() / '.codex/sessions')
        self.sessions = {}
        self.metadata = {}
        self.metadata_versions = {}
        self.historical_paths = []
        self.last_discovery = None
        self.last_historical_discovery = None
        self.lock = threading.Lock()

    def _discover(self, now):
        if self.last_discovery is not None and now - self.last_discovery < DISCOVERY_SECONDS:
            return
        self.last_discovery = now
        paths = []
        date = datetime.fromtimestamp(now, timezone.utc)
        for delta in (0, 1):
            day = date - timedelta(days=delta)
            folder = self.sessions_dir / day.strftime('%Y/%m/%d')
            try:
                paths.extend(folder.glob('*.jsonl'))
            except OSError:
                continue
        def mtime(path):
            try:
                return path.stat().st_mtime
            except OSError:
                return 0
        # A resumed chat keeps its original dated rollout directory. Discover
        # older files at startup and at most once per minute; only stat paths
        # here, never parse historical records during this filesystem census.
        if (self.last_historical_discovery is None
                or now - self.last_historical_discovery >= HISTORICAL_DISCOVERY_SECONDS):
            self.last_historical_discovery = now
            try:
                self.historical_paths = sorted(self.sessions_dir.rglob('*.jsonl'),
                                               key=mtime, reverse=True)[:120]
            except OSError:
                pass
        paths = sorted(set(paths) | set(self.historical_paths), key=mtime, reverse=True)[:120]
        for path in paths:
            try:
                stat = path.stat()
                version = (stat.st_size, stat.st_mtime_ns)
            except OSError:
                continue
            # The first discovery can race creation of session_meta. Keep an
            # unsuccessful read cheap, but retry once the file actually changes.
            if (path not in self.metadata
                    or (self.metadata[path] is None and self.metadata_versions.get(path) != version)):
                self.metadata[path] = _metadata(path)
                self.metadata_versions[path] = version
        eligible = {m['id'] for m in self.metadata.values() if m and m['id'] and (m['cwd'] == self.root or self.root in m['roots'])}
        for _ in range(8):
            descendants = {m['id'] for m in self.metadata.values() if m and m['id'] and m['parent'] in eligible}
            if descendants <= eligible:
                break
            eligible |= descendants
        for path, meta in self.metadata.items():
            if meta and meta['id'] in eligible and path not in self.sessions:
                role = _role(meta)
                if role:
                    self.sessions[path] = _Session(path, meta, role)
        self.sessions = {
            p: session for p, session in self.sessions.items()
            if p in paths or (session.run and now - (_epoch(session.run['heartbeat_at']) or 0) < 172800)
        }
        # Bound cached metadata while keeping observed project sessions.
        self.metadata = {p: m for p, m in self.metadata.items() if p in paths or p in self.sessions}
        self.metadata_versions = {p: v for p, v in self.metadata_versions.items() if p in self.metadata}

    def snapshot(self, now=None):
        now = time.time() if now is None else now
        with self.lock:
            self._discover(now)
            runs, events, warnings = [], [], []
            for session in self.sessions.values():
                if not session.read():
                    warnings.append('Una sesión local dejó de estar disponible.')
                if not session.run:
                    continue
                run = dict(session.run)
                age = now - (_epoch(run['heartbeat_at']) or 0)
                if run['status'] == 'active':
                    run['verified_active'] = 0 <= age <= STALE_SECONDS
                    if not run['verified_active']:
                        run['status'] = 'stale'
                        run['task'] = 'Sin señal reciente de la sesión'
                runs.append(run)
                events.extend(dict(e) for e in session.events)
            runs.sort(key=lambda r: r['heartbeat_at'], reverse=True)
            events.sort(key=lambda e: e['at'], reverse=True)
            return {
                'available': bool(self.sessions), 'generated_at': _iso(now),
                'stale_after_seconds': STALE_SECONDS, 'runs': runs[:40], 'events': events[:80],
                'warnings': list(dict.fromkeys(warnings)),
                'scope': 'Sesiones cuyo proyecto coincide y descendientes con rol reconocido.',
                'note': 'Actividad observada en eventos locales. Una skill leída se distingue de una herramienta de skill en ejecución.',
            }


def read_codex_activity(root, sessions_dir=None, now=None):
    key = (_path_key(Path(root).resolve()), str(sessions_dir or Path.home() / '.codex/sessions'))
    with _CACHE_LOCK:
        observer = _CACHES.setdefault(key, CodexObserver(root, sessions_dir))
    return observer.snapshot(now)
