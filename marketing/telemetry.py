"""Minimal activity metadata for work that is actually executing.

This database is independent of marketing jobs. It never stores prompts,
responses, exception messages, command lines, environment values or media.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import json
import os
import re
import sqlite3
import subprocess
import threading
import time
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEARTBEAT_INTERVAL_SECONDS = 2
STALE_AFTER_SECONDS = 10
DATABASE_NAME = 'office-activity.sqlite3'
IDENTIFIER = re.compile(r'^[a-zA-Z0-9_.:-]{1,100}$')
_SCHEMA_LOCK = threading.Lock()


def now():
    return datetime.now(timezone.utc).isoformat()


def telemetry_root(root):
    """An explicit override isolates tests and controlled validation runs."""
    return Path(os.environ.get('MARKETING_TELEMETRY_ROOT') or root).resolve()


def brief_text(value, limit=160):
    if not isinstance(value, str):
        return ''
    value = value.splitlines()[0] if value.splitlines() else ''
    value = re.sub(r'(?i)(?:sk-[\w-]+|bearer\s+\S+|(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S+)', '[dato omitido]', value)
    # A credential accidentally pasted as a long unbroken token is not a title.
    value = re.sub(r'\b[A-Za-z0-9_+/=-]{48,}\b', '[dato omitido]', value)
    return ''.join(char for char in value if ord(char) >= 32).strip()[:limit]


def identifier(value, label, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f'{label}: identificador inválido.')
    if brief_text(value) != value:
        raise ValueError(f'{label}: el identificador contiene datos que no deben registrarse.')
    return value


def process_probe(pid):
    """Return (alive, creation identity). Unknown processes are never verified."""
    if not isinstance(pid, int) or pid < 1:
        return False, None
    if os.name == 'nt':
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        kernel.GetProcessTimes.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return (False if ctypes.get_last_error() == 87 else None), None
        try:
            code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                return None, None
            if code.value != 259:  # STILL_ACTIVE
                return False, None
            created, exited, system, user = (wintypes.FILETIME() for _ in range(4))
            if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                          ctypes.byref(system), ctypes.byref(user)):
                return True, None
            return True, 'windows:' + str((created.dwHighDateTime << 32) | created.dwLowDateTime)
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False, None
    except PermissionError:
        return None, None
    except OSError as exc:
        return (False if exc.errno == errno.ESRCH else None), None
    try:
        stat = Path(f'/proc/{pid}/stat').read_text(encoding='ascii')
        fields = stat[stat.rfind(')') + 2:].split()
        if fields[0] == 'Z':
            return False, None
        return True, 'proc:' + fields[19]
    except (OSError, IndexError, ValueError):
        return True, None


def connect(path, read_only=False):
    path = Path(path)
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2) if read_only else sqlite3.connect(path, timeout=2)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA busy_timeout=2000')
    if read_only:
        db.execute('PRAGMA query_only=ON')
    return db


def initialize(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Changing journal mode on a brand-new database can return SQLITE_BUSY
    # immediately: SQLite's busy timeout does not cover every PRAGMA lock
    # upgrade. Serialize threads and retry that idempotent setup across
    # independent CLI processes instead of silently losing their first run.
    with _SCHEMA_LOCK:
        for attempt in range(7):
            try:
                _initialize_once(path)
                return
            except sqlite3.OperationalError as exc:
                code = getattr(exc, 'sqlite_errorcode', 0) & 0xff
                if code not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) or attempt == 6:
                    raise
                time.sleep(min(0.025 * (2 ** attempt), 0.4))


def _initialize_once(path):
    db = connect(path)
    try:
        if db.execute('PRAGMA journal_mode').fetchone()[0].lower() != 'wal':
            db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, job_id TEXT,
                task TEXT NOT NULL, skill_id TEXT, skill_evidence TEXT,
                source TEXT NOT NULL, pid INTEGER NOT NULL, process_identity TEXT,
                started_at TEXT NOT NULL, heartbeat_at TEXT NOT NULL,
                finished_at TEXT, status TEXT NOT NULL, exit_code INTEGER
            );
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL, kind TEXT NOT NULL, at TEXT NOT NULL,
                status TEXT NOT NULL, exit_code INTEGER
            );
            CREATE INDEX IF NOT EXISTS events_run ON events(run_id, event_id);
            CREATE INDEX IF NOT EXISTS runs_started ON runs(started_at);
        ''')
    finally:
        db.close()


class Activity:
    def __init__(self, root, agent_id, task, job_id=None, skill_id=None, source='cli', skill_evidence=None):
        self.path = telemetry_root(root) / 'runtime' / DATABASE_NAME
        self.run_id = uuid.uuid4().hex
        self.agent_id = identifier(agent_id, 'Agente')
        self.job_id = identifier(job_id, 'Trabajo', optional=True)
        self.skill_id = identifier(skill_id, 'Skill', optional=True)
        self.source = identifier(source, 'Origen')
        self.task = brief_text(task) or 'Trabajo en curso'
        self.skill_evidence = brief_text(skill_evidence or 'declared_by_caller') if self.skill_id else None
        self.exit_code = None
        self.available = False
        self._stop = threading.Event()
        self._thread = None
        self._entered = False

    def __enter__(self):
        if self._entered:
            raise RuntimeError('El contexto de actividad no puede reutilizarse.')
        self._entered = True
        _, identity = process_probe(os.getpid())
        try:
            initialize(self.path)
            timestamp = now()
            db = connect(self.path)
            try:
                with db:
                    db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                               (self.run_id, self.agent_id, self.job_id, self.task, self.skill_id,
                                self.skill_evidence, self.source, os.getpid(), identity,
                                timestamp, timestamp, None, 'active', None))
                    db.execute('INSERT INTO events(run_id,kind,at,status) VALUES(?,?,?,?)',
                               (self.run_id, 'started', timestamp, 'active'))
            finally:
                db.close()
            self.available = True
            self._thread = threading.Thread(target=self._pulse, name='office-heartbeat', daemon=True)
            self._thread.start()
        except (OSError, sqlite3.Error):
            warnings.warn('No se pudo registrar la actividad de la oficina; el trabajo continúa.', RuntimeWarning)
        return self

    def _pulse(self):
        while not self._stop.wait(HEARTBEAT_INTERVAL_SECONDS):
            try:
                db = connect(self.path)
                try:
                    with db:
                        db.execute("UPDATE runs SET heartbeat_at=? WHERE run_id=? AND status='active'",
                                   (now(), self.run_id))
                finally:
                    db.close()
            except (OSError, sqlite3.Error):
                # Readers mark stale records instead of inventing activity.
                continue

    def __exit__(self, exc_type, exc_value, traceback):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=4)
        if not self.available:
            return False
        status = 'completed'
        if exc_type is not None:
            status = 'error' if issubclass(exc_type, Exception) else 'interrupted'
        elif self.exit_code not in (None, 0):
            status = 'error'
        timestamp = now()
        try:
            db = connect(self.path)
            try:
                with db:
                    db.execute('UPDATE runs SET status=?,finished_at=?,heartbeat_at=?,exit_code=? WHERE run_id=?',
                               (status, timestamp, timestamp, self.exit_code, self.run_id))
                    db.execute('INSERT INTO events(run_id,kind,at,status,exit_code) VALUES(?,?,?,?,?)',
                               (self.run_id, status, timestamp, status, self.exit_code))
            finally:
                db.close()
        except (OSError, sqlite3.Error):
            warnings.warn('No se pudo registrar el cierre de la actividad; aparecerá sin señal vigente.', RuntimeWarning)
        return False


def activity(root, agent_id, task, job_id=None, skill_id=None, source='cli', skill_evidence=None):
    return Activity(root, agent_id, task, job_id, skill_id, source, skill_evidence)


def effective_run(record, current_time=None, probe_cache=None):
    record = dict(record)
    record['recorded_status'] = record['status']
    record['verified_active'] = False
    record['activity_reason'] = None
    if record['status'] != 'active':
        return record
    cache = probe_cache if probe_cache is not None else {}
    pid = record['pid']
    if pid not in cache:
        cache[pid] = process_probe(pid)
    alive, identity = cache[pid]
    if alive is False or (record.get('process_identity') and identity and identity != record['process_identity']):
        record.update(status='interrupted', activity_reason='process_ended')
        return record
    try:
        heartbeat = datetime.fromisoformat(record['heartbeat_at'])
        age = ((current_time or datetime.now(timezone.utc)) - heartbeat).total_seconds()
    except (ValueError, TypeError):
        age = STALE_AFTER_SECONDS + 1
    record['heartbeat_age_seconds'] = round(age, 2)
    if age > STALE_AFTER_SECONDS or age < -2:
        record.update(status='stale', activity_reason='heartbeat_expired')
    elif alive is not True or not record.get('process_identity') or not identity:
        record.update(status='stale', activity_reason='process_unverified')
    else:
        record['verified_active'] = True
    return record


def read_activity(root=ROOT):
    result = {'available': False, 'generated_at': now(),
              'heartbeat_interval_seconds': HEARTBEAT_INTERVAL_SECONDS,
              'stale_after_seconds': STALE_AFTER_SECONDS, 'runs': [], 'events': [], 'warnings': []}
    path = telemetry_root(root) / 'runtime' / DATABASE_NAME
    if not path.is_file():
        return result
    try:
        db = connect(path, read_only=True)
        try:
            with db:
                rows = db.execute("SELECT * FROM runs ORDER BY status='active' DESC, started_at DESC LIMIT 500").fetchall()
                events = db.execute('''SELECT e.*, r.agent_id, r.job_id, r.task, r.skill_id,
                                              r.skill_evidence, r.source
                                       FROM events e JOIN runs r ON e.run_id=r.run_id
                                       ORDER BY e.event_id DESC LIMIT 200''').fetchall()
        finally:
            db.close()
        cache = {}
        timestamp = datetime.now(timezone.utc)
        result.update(available=True, runs=[effective_run(row, timestamp, cache) for row in rows],
                      events=[dict(row) for row in events])
    except (OSError, sqlite3.Error):
        result['warnings'].append('No se pudo leer el registro de actividad; no hay actividad verificada.')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Registrar la actividad de un comando real sin guardar su contenido.')
    subparsers = parser.add_subparsers(dest='action', required=True)
    run = subparsers.add_parser('run', help='Envolver un comando real y guardar solo su actividad.')
    run.add_argument('--agent', required=True)
    run.add_argument('--task', required=True)
    run.add_argument('--job')
    run.add_argument('--skill')
    run.add_argument('--root', type=Path, default=ROOT)
    run.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('Falta el comando después de --.')
    try:
        scope = activity(args.root, args.agent, args.task, job_id=args.job, skill_id=args.skill,
                         source='local_command', skill_evidence='declared_by_operator' if args.skill else None)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        with scope:
            process = subprocess.Popen(command)
            try:
                scope.exit_code = process.wait()
            except KeyboardInterrupt:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                raise
        return scope.exit_code or 0
    except KeyboardInterrupt:
        return 130
    except OSError:
        print('No se pudo iniciar el comando; el registro no guarda sus argumentos.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
