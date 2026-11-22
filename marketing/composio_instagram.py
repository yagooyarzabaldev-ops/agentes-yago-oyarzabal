"""Publish an approved local Reel through Composio, with durable write guards.

No browser, OAuth token extraction, paid generation, or automatic write retries.
See production/COMPOSIO-INSTAGRAM.md for operational limits and authorization.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import subprocess
import sys
import urllib.parse
import uuid
from pathlib import Path

from .config import AppError
from .composio_files import StagingError, stage_file, verify_download
from .media import verify_video
from .store import Store, digest, file_digest, now, write_json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_ROOT = Path('D:/Herramientas/marketing/composio')


def private_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(PROJECT_ROOT / 'runtime'):
        raise AppError('El estado y los comprobantes operativos de Composio deben quedar en runtime/.')
    return path


class ComposioCLI:
    def __init__(self, runtime):
        self.runtime = private_path(runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)

    def proxy(self, account, version, resource, method='GET', body=None):
        if not re.fullmatch(r'v\d+\.\d+', version) or not re.fullmatch(r'(?:me|\d+)(?:/media|/media_publish)?(?:\?fields=[a-z_,]+)?', resource):
            raise AppError('Endpoint de Instagram fuera del contrato admitido.')
        executable = CLI_ROOT / 'composio-windows-x64/composio.exe'
        if not executable.is_file():
            raise AppError('Falta la CLI oficial de Composio. Consultá production/COMPOSIO-INSTAGRAM.md.')
        env = {**os.environ, 'COMPOSIO_CACHE_DIR': str(CLI_ROOT / 'config'),
               'COMPOSIO_SESSION_DIR': str(CLI_ROOT / 'sessions'), 'COMPOSIO_CLI_TELEMETRY_DISABLED': '1'}
        call_id = uuid.uuid4().hex
        args = [str(executable), 'proxy', f'https://graph.instagram.com/{version}/{resource}',
                '--toolkit', 'instagram', '--account', account, '-X', method]
        payload = self.runtime / f'{call_id}-request.json'
        if body is not None:
            write_json(payload, body)
            args.extend(['-H', 'content-type: application/json', '-d', '@' + str(payload)])
        try:
            result = subprocess.run(args, env=env, capture_output=True, text=True, encoding='utf-8',
                                    errors='replace', timeout=180, check=False)
            # Provider errors may echo signed URLs. Keep them in the private log only.
            (self.runtime / f'{call_id}-response.txt').write_text(result.stdout + '\n' + result.stderr, encoding='utf-8')
            if result.returncode:
                raise AppError(f'Composio falló. Revisá el registro privado {call_id}; no se repite el envío.')
            try:
                data = json.loads(result.stdout)
            except ValueError:
                raise AppError(f'Composio devolvió una respuesta no JSON; registro privado {call_id}.') from None
            if not isinstance(data, dict) or data.get('error') or data.get('successful') is False:
                raise AppError(f'Instagram no confirmó la operación; registro privado {call_id}.')
            return data
        except subprocess.TimeoutExpired:
            raise AppError('Composio agotó el tiempo de espera. Consultá el estado; no se repite el envío.') from None
        finally:
            payload.unlink(missing_ok=True)


def load_package(path):
    path = Path(path).resolve()
    package = json.loads(path.read_text(encoding='utf-8-sig'))
    for key in ('video', 'cover', 'caption_file', 'video_stage_receipt', 'cover_stage_receipt', 'existing_receipt'):
        if package.get(key):
            package[key] = str((path.parent / package[key]).resolve())
    return package


class InstagramPublisher:
    def __init__(self, package, state_path, cli=None, stager=None):
        self.package = package
        self.state_path = private_path(state_path)
        self.runtime = self.state_path.parent
        self.cli = cli or ComposioCLI(self.runtime / 'requests')
        self.stager = stager

    def snapshot(self):
        p = self.package
        required = ('video', 'cover', 'caption_file', 'account', 'instagram_user_id', 'username', 'is_ai_generated', 'share_to_feed')
        if any(k not in p for k in required):
            raise AppError('Paquete incompleto: se requieren MP4, portada, copy, cuenta, identidad, etiqueta IA y feed.')
        if not re.fullmatch(r'\d+', str(p['instagram_user_id'])) or not re.fullmatch(r'[\w.]{1,30}', p['username']):
            raise AppError('Identidad de Instagram inválida.')
        if not isinstance(p['account'], str) or not p['account'].strip():
            raise AppError('Falta seleccionar explícitamente la conexión de Composio.')
        if type(p['is_ai_generated']) is not bool or type(p['share_to_feed']) is not bool:
            raise AppError('La etiqueta IA y la opción de feed deben ser booleanos explícitos.')
        if p.get('demo'):
            raise AppError('Los ejemplos o demos no se publican.')
        if not re.fullmatch(r'v\d+\.\d+', p.get('api_version', 'v21.0')):
            raise AppError('Versión de API inválida.')
        for key, suffixes in (('video', ('.mp4',)), ('cover', ('.jpg', '.jpeg'))):
            file = Path(p[key])
            if not file.is_file() or file.suffix.lower() not in suffixes or file.stat().st_size == 0:
                raise AppError(f'Archivo {key} inexistente, vacío o de formato incorrecto.')
        if Path(p['cover']).stat().st_size > 8 * 1024 * 1024:
            raise AppError('La portada JPEG supera 8 MiB.')
        caption = Path(p['caption_file']).read_text(encoding='utf-8-sig').strip()
        if not caption or len(caption) > 2200 or len(re.findall(r'(?<!\w)#\w+', caption)) > 30:
            raise AppError('Copy vacío o fuera de los límites de Instagram.')
        audio_name = p.get('audio_name', '')
        if not isinstance(audio_name, str) or len(audio_name) > 80:
            raise AppError('Nombre de audio inválido.')
        snap = {'account': p['account'], 'instagram_user_id': str(p['instagram_user_id']),
                'username': p['username'], 'video_sha256': file_digest(p['video']),
                'cover_sha256': file_digest(p['cover']), 'caption_file_sha256': file_digest(p['caption_file']),
                'caption': caption, 'audio_name': audio_name, 'is_ai_generated': p['is_ai_generated'],
                'share_to_feed': p['share_to_feed'], 'api_version': p.get('api_version', 'v21.0'),
                'visibility': 'public', 'media_type': 'REELS'}
        snap['fingerprint'] = digest(snap)
        return snap

    def _request(self, snap, resource, method='GET', body=None):
        return self.cli.proxy(snap['account'], snap['api_version'], resource, method, body)

    def _identity(self, snap):
        identity = self._request(snap, 'me?fields=user_id,username,account_type')
        if str(identity.get('user_id')) != snap['instagram_user_id'] or identity.get('username') != snap['username']:
            raise AppError('La conexión de Composio no corresponde a la cuenta del paquete.')
        if identity.get('account_type') not in ('MEDIA_CREATOR', 'BUSINESS'):
            raise AppError('La cuenta conectada no es una cuenta profesional de Instagram.')
        return identity

    def check(self):
        snap = self.snapshot()
        verify_video(self.package['video'])
        self._identity(snap)
        result = {**snap, 'state': 'checked', 'publication_performed': False}
        existing = self._existing(snap)
        if existing:
            result.update(state='already_published', published_url=existing.get('published_url') or existing.get('url'))
        return result

    def _existing(self, snap):
        # Honor the delivered receipt even if a caller selects a new runtime directory.
        paths = [Path(self.package['video']).parent / 'publicacion-instagram.json', self._registry_path(snap)]
        if self.package.get('existing_receipt'):
            paths.append(Path(self.package['existing_receipt']))
        for path in paths:
            if not path.is_file():
                continue
            record = json.loads(path.read_text(encoding='utf-8-sig'))
            if path == self._registry_path(snap) and record.get('state') != 'published_verified':
                # A known ID with pending metadata still needs a read-only verification.
                continue
            if record.get('status', record.get('state')) in ('published', 'published_verified', 'verified', 'uploaded'):
                old_hash = record.get('final_sha256', record.get('video_sha256', record.get('sha256')))
                if old_hash and old_hash != snap['video_sha256']:
                    raise AppError('La carpeta contiene un comprobante de otra versión. Conservá su historial y resolvé el paquete antes de publicar.')
                return record
        return None

    @staticmethod
    def _registry_key(value):
        return digest({'video_sha256': value['video_sha256'], 'target': value['instagram_user_id']})

    def _registry_path(self, value):
        return PROJECT_ROOT / 'runtime/composio-instagram/registry' / (self._registry_key(value) + '.json')

    def _lock(self, snap):
        # Different --state directories cannot race or bypass a previous attempt.
        return Store(PROJECT_ROOT / 'runtime/composio-instagram').lock(self._registry_key(snap))

    def _save(self, record):
        record['updated_at'] = now()
        record['owner_state_path'] = str(self.state_path)
        # This shared registry is authoritative after a crash between the two writes.
        write_json(self._registry_path(record), record)
        write_json(self.state_path, record)

    def _record(self, snap):
        registry_path = self._registry_path(snap)
        path = registry_path if registry_path.is_file() else self.state_path
        if not path.is_file():
            return {'fingerprint': snap['fingerprint'], 'state': 'prepared', 'created_at': now(),
                    'account': snap['account'], 'instagram_user_id': snap['instagram_user_id'],
                    'username': snap['username'], 'video_sha256': snap['video_sha256'],
                    'publication_attempts': 0, 'container_attempts': 0}
        record = json.loads(path.read_text(encoding='utf-8-sig'))
        if record.get('owner_state_path', str(self.state_path)) != str(self.state_path):
            raise AppError('Ya existe un intento de este MP4 y cuenta en otro estado. Reutilizá el estado original; no se creará otro envío.')
        if record.get('fingerprint') != snap['fingerprint']:
            raise AppError('El paquete cambió respecto del intento guardado. No se creará un duplicado.')
        return record

    @staticmethod
    def summary(record):
        keys = ('state', 'fingerprint', 'account', 'username', 'container_id', 'media_id', 'published_url',
                'publication_attempts', 'container_attempts', 'created_at', 'updated_at', 'verification_pending')
        return {k: record[k] for k in keys if k in record}

    def _stage(self, snap, kind):
        if self.package.get(kind + '_stage_receipt'):
            receipt = json.loads(Path(self.package[kind + '_stage_receipt']).read_text(encoding='utf-8-sig'))
        else:
            try:
                receipt = (self.stager or stage_file)(self.package[kind], self.runtime / 'files' / kind)
            except StagingError:
                raise AppError(f'No se pudo preparar {kind} por Composio. Consultá el comprobante privado de carga.') from None
        if receipt.get('status') != 'verified' or receipt.get('sha256') != snap[kind + '_sha256']:
            raise AppError(f'La carga de {kind} no acredita el archivo aprobado.')
        if receipt.get('bytes') != Path(self.package[kind]).stat().st_size:
            raise AppError(f'La carga de {kind} tiene otro tamaño.')
        url = receipt.get('s3_url', '')
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise AppError(f'Composio no devolvió una URL HTTPS válida para {kind}.')
        # Temporary URLs can expire after staging; recheck exact bytes and public redirects.
        target = self.runtime / ('precreate-' + kind + Path(self.package[kind]).suffix)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            verify_download(url, target, snap[kind + '_sha256'], receipt['bytes'])
        except StagingError:
            raise AppError(f'La URL de {kind} no acredita el archivo aprobado o venció; revisá su carga.') from None
        finally:
            target.unlink(missing_ok=True)
        return url

    def _verify(self, snap, record):
        media = self._request(snap, record['media_id'] + '?fields=id,username,caption,permalink,media_product_type,is_ai_generated,is_shared_to_feed')
        expected = {'id': record['media_id'], 'username': snap['username'], 'caption': snap['caption'],
                    'media_product_type': 'REELS', 'is_ai_generated': snap['is_ai_generated'],
                    'is_shared_to_feed': snap['share_to_feed']}
        if any(media.get(k) != v for k, v in expected.items()):
            raise AppError('El medio existe, pero su metadata no coincide con el paquete. Revisá sin volver a publicar.')
        link = urllib.parse.urlsplit(media.get('permalink', ''))
        if link.scheme != 'https' or link.hostname not in ('www.instagram.com', 'instagram.com'):
            raise AppError('Instagram no devolvió un permalink verificable.')
        record.update(state='published_verified', published_url=media['permalink'], verification_pending=False,
                      verification=media, verified_at=now())
        self._save(record)

    def publish(self, confirmation):
        snap = self.snapshot()
        if not hmac.compare_digest(str(confirmation), snap['fingerprint']):
            raise AppError('La autorización no coincide con la huella del paquete. Revisá check y la autorización vigente.')
        with self._lock(snap):
            existing = self._existing(snap)
            if existing:
                return {'state': 'already_published', 'published_url': existing.get('published_url') or existing.get('url'), 'publication_performed': False}
            record = self._record(snap)
            if record['state'] == 'published_verified':
                return self.summary(record)
            if record['state'] in ('create_unknown', 'publish_unknown', 'failed'):
                raise AppError('Hay un envío incierto o fallido. Reconciliá el estado remoto; no se reintenta ni se crea otro contenedor.')
            verify_video(self.package['video'])
            self._identity(snap)
            if record.get('media_id'):
                self._verify(snap, record)
                return self.summary(record)
            if not record.get('container_id'):
                video_url, cover_url = self._stage(snap, 'video'), self._stage(snap, 'cover')
                body = {'media_type': 'REELS', 'video_url': video_url, 'cover_url': cover_url,
                        'caption': snap['caption'], 'share_to_feed': snap['share_to_feed'],
                        'is_ai_generated': snap['is_ai_generated']}
                if snap['audio_name']:
                    body['audio_name'] = snap['audio_name']
                record.update(state='create_unknown', container_attempts=record['container_attempts'] + 1)
                self._save(record)
                result = self._request(snap, snap['instagram_user_id'] + '/media', 'POST', body)
                if not str(result.get('id', '')).isdigit():
                    raise AppError('No se recibió el ID del contenedor. Se bloquean reintentos.')
                record.update(state='processing', container_id=str(result['id']))
                self._save(record)
                return self.summary(record)
            status = self._request(snap, record['container_id'] + '?fields=status_code')
            if status.get('status_code') in ('ERROR', 'EXPIRED'):
                record.update(state='failed')
                self._save(record)
                raise AppError('Instagram rechazó el contenedor o venció. No se creará otro automáticamente.')
            if status.get('status_code') != 'FINISHED':
                if status.get('status_code') != 'IN_PROGRESS':
                    raise AppError('Estado remoto no apto para publicar. Reconciliá antes de continuar.')
                return self.summary(record)
            record.update(state='publish_unknown', publication_attempts=record['publication_attempts'] + 1)
            self._save(record)
            result = self._request(snap, snap['instagram_user_id'] + '/media_publish', 'POST', {'creation_id': record['container_id']})
            if not str(result.get('id', '')).isdigit():
                raise AppError('No se recibió el ID de publicación. Se bloquean reintentos.')
            record.update(state='published', media_id=str(result['id']), verification_pending=True)
            self._save(record)
            self._verify(snap, record)
            return self.summary(record)

    def status(self, media_id=None):
        snap = self.snapshot()
        with self._lock(snap):
            existing = self._existing(snap)
            if existing and media_id is None:
                return {'state': 'already_published', 'published_url': existing.get('published_url') or existing.get('url')}
            if not self.state_path.is_file() and not self._registry_path(snap).is_file():
                raise AppError('No hay un intento registrado para consultar o reconciliar.')
            record = self._record(snap)
            self._identity(snap)
            if media_id:
                if not re.fullmatch(r'\d+', media_id):
                    raise AppError('ID de medio inválido.')
                candidate = {**record, 'media_id': media_id}
                self._verify(snap, candidate)
                return self.summary(candidate)
            if record.get('media_id'):
                self._verify(snap, record)
            elif record.get('container_id'):
                remote = self._request(snap, record['container_id'] + '?fields=status_code')
                return {**self.summary(record), 'container_status': remote.get('status_code')}
            return self.summary(record)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Instagram por Composio, sin interfaz gráfica ni reintentos de envíos inciertos.')
    parser.add_argument('command', choices=('check', 'publish', 'status'))
    parser.add_argument('package', type=Path, help='JSON privado con video, cover, caption_file, account e identidad de destino.')
    parser.add_argument('--state', type=Path, required=True, help='Comprobante privado persistente para este paquete.')
    parser.add_argument('--confirm', help='SHA256 de check correspondiente a la autorización vigente del usuario.')
    parser.add_argument('--media-id', help='Solo status: reconciliar un ID remoto conocido, sin publicar.')
    args = parser.parse_args(argv)
    try:
        publisher = InstagramPublisher(load_package(args.package), args.state)
        if args.command == 'check':
            result = publisher.check()
        elif args.command == 'status':
            result = publisher.status(args.media_id)
        else:
            result = publisher.publish(args.confirm or '')
        # Windows redirected stdout may use cp1252; JSON escapes preserve emojis.
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (AppError, OSError, ValueError, KeyError) as exc:
        # Do not echo provider request bodies, signed URLs, or subprocess commands.
        message = str(exc) if isinstance(exc, AppError) else 'No se pudo leer o validar el paquete o su estado privado.'
        print(message, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
