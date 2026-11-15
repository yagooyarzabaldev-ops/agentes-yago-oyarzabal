from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import AppError


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def file_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


class Store:
    def __init__(self, runtime):
        self.root = Path(runtime)
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, source TEXT UNIQUE, version INTEGER NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS publications(job TEXT, platform TEXT, body TEXT NOT NULL, PRIMARY KEY(job, platform));
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            ''')

    @contextlib.contextmanager
    def connect(self):
        db = sqlite3.connect(self.root / 'marketing.sqlite3', timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextlib.contextmanager
    def lock(self, job_id):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', job_id):
            raise AppError('Identificador inválido.')
        directory = self.root / 'locks'
        directory.mkdir(exist_ok=True)
        with (directory / (job_id + '.lock')).open('a+b') as stream:
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                # Consultar el tamaño evita leer un byte bloqueado por otro proceso.
                if os.fstat(stream.fileno()).st_size == 0:
                    stream.write(b'0')
                    stream.flush()
                stream.seek(0)
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    raise AppError('Esta operación ya está en curso en otro proceso.') from None
                try:
                    yield
                finally:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise AppError('Esta operación ya está en curso en otro proceso.') from None
                try:
                    yield
                finally:
                    fcntl.flock(stream, fcntl.LOCK_UN)

    def create(self, idea, source=None, video_format='editorial'):
        if video_format not in ('editorial', 'roulette'):
            raise AppError('Formato desconocido.')
        job = {'id': uuid.uuid4().hex[:12], 'version': 0, 'idea': idea, 'state': 'brief',
               'video_format': video_format,
               'created_at': now(), 'agents': {}, 'approval': None, 'video': None, 'feedback': []}
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if source:
                existing = db.execute('SELECT body FROM jobs WHERE source=?', (source,)).fetchone()
                if existing:
                    return json.loads(existing[0])
            db.execute('INSERT INTO jobs VALUES(?,?,?,?)', (job['id'], source, 0, json.dumps(job)))
        return job

    def get(self, job_id):
        with self.connect() as db:
            row = db.execute('SELECT body FROM jobs WHERE id=?', (job_id,)).fetchone()
        if not row:
            raise AppError('No existe ese trabajo. Usá list para ver los identificadores.')
        return json.loads(row[0])

    def list(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT body FROM jobs ORDER BY rowid')]

    def save(self, job):
        previous = job['version']
        updated = dict(job, version=previous + 1, updated_at=now())
        with self.connect() as db:
            changed = db.execute('UPDATE jobs SET version=?,body=? WHERE id=? AND version=?',
                                 (previous + 1, json.dumps(updated), job['id'], previous)).rowcount
        if changed != 1:
            raise AppError('El trabajo cambió en otro proceso. Volvé a abrirlo.')
        job.update(updated)

    def artifact_dir(self, job):
        directory = self.root / 'jobs' / job['id']
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def publication(self, job_id, platform):
        with self.connect() as db:
            row = db.execute('SELECT body FROM publications WHERE job=? AND platform=?', (job_id, platform)).fetchone()
        return json.loads(row[0]) if row else None

    def put_publication(self, job_id, platform, record):
        with self.connect() as db:
            db.execute('INSERT INTO publications VALUES(?,?,?) ON CONFLICT(job,platform) DO UPDATE SET body=excluded.body',
                       (job_id, platform, json.dumps(record)))

    def assert_editable(self, job_id):
        with self.connect() as db:
            if db.execute('SELECT 1 FROM publications WHERE job=?', (job_id,)).fetchone():
                raise AppError('Este trabajo tiene una publicación iniciada. Creá otro para una nueva versión.')

    def meta(self, key, value=None):
        with self.connect() as db:
            if value is not None:
                db.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, json.dumps(value)))
            row = db.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None
