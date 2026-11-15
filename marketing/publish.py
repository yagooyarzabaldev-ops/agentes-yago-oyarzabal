from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import re
import secrets
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from .agents import approved
from .config import AppError
from .media import verify_video
from .net import Http
from .store import digest, file_digest, now, write_json


def bearer(token):
    return {'Authorization': 'Bearer ' + token}


def header(headers, key):
    return next((v for k, v in headers.items() if k.lower() == key.lower()), None)


def social_text(body, hashtags, disclosure=''):
    """Append tags only when they are not already present in the generated copy."""
    present = {tag.casefold() for tag in re.findall(r'(?<!\w)#\w+', body)}
    missing = []
    for tag in hashtags:
        if not isinstance(tag, str) or not re.fullmatch(r'#\w+', tag):
            raise AppError('Cada hashtag debe comenzar con # y no contener espacios.')
        if tag.casefold() not in present:
            missing.append(tag)
            present.add(tag.casefold())
    return body.rstrip() + ('\n\n' + ' '.join(missing) if missing else '') + disclosure


def public_url(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise AppError('Instagram necesita una URL HTTPS pública y directa del MP4.')
    host = parsed.hostname.lower()
    if host == 'localhost' or host.endswith(('.local', '.localhost')):
        raise AppError('La URL de Instagram no puede ser local.')
    try:
        if not ipaddress.ip_address(host).is_global:
            raise AppError('La URL de Instagram no puede ser una dirección privada.')
    except ValueError:
        pass
    return value


class YouTubeAuth:
    def __init__(self, config, http):
        self.config, self.http = config, http
        self.path = config.runtime / 'youtube-token.json'

    def client(self):
        path = self.config.path(self.config.get('YOUTUBE_CLIENT_FILE', 'credentials/youtube-client.json'))
        if not path.is_file():
            raise AppError('Falta el archivo OAuth Desktop de YouTube. Consultá README, sección Conexiones.')
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))['installed']
            return {'client_id': data['client_id'], 'client_secret': data['client_secret']}
        except (KeyError, ValueError):
            raise AppError('El cliente OAuth debe ser de tipo Desktop y contener client_id y client_secret.') from None

    def login(self):
        client = self.client()
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        result = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlsplit(self.path)
                params = urllib.parse.parse_qs(parsed.query)
                valid_state = secrets.compare_digest(params.get('state', [''])[0], state)
                if parsed.path != '/callback' or not valid_state:
                    self.send_error(400, 'Invalid OAuth callback')
                    return
                result.update({k: v[0] for k, v in params.items()})
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write('Respuesta recibida. Volvé a la consola para ver el resultado.'.encode('utf-8'))

            def log_message(self, *args):
                pass

        with HTTPServer(('127.0.0.1', 0), Handler) as server:
            server.timeout = 1
            redirect = f'http://127.0.0.1:{server.server_port}/callback'
            query = urllib.parse.urlencode({**{'client_id': client['client_id']}, 'redirect_uri': redirect,
                'response_type': 'code', 'scope': 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly',
                'access_type': 'offline', 'prompt': 'consent', 'state': state,
                'code_challenge': challenge, 'code_challenge_method': 'S256'})
            if not webbrowser.open('https://accounts.google.com/o/oauth2/v2/auth?' + query):
                raise AppError('No se pudo abrir el navegador para OAuth.')
            deadline = time.monotonic() + 180
            while not result and time.monotonic() < deadline:
                server.handle_request()
        if 'code' not in result:
            raise AppError('La autorización de YouTube se canceló o venció.')
        token = self.http.json('POST', 'https://oauth2.googleapis.com/token', form={**client,
            'grant_type': 'authorization_code', 'code': result['code'], 'code_verifier': verifier, 'redirect_uri': redirect})
        if not token.get('access_token') or not token.get('refresh_token'):
            raise AppError('Google no entregó acceso persistente. Revisá el consentimiento OAuth.')
        token['expires_at'] = time.time() + token.get('expires_in', 3600)
        write_json(self.path, token)
        channels = self.http.json('GET', 'https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true',
                                  headers=bearer(token['access_token']))
        return [{'id': c['id'], 'title': c['snippet']['title']} for c in channels.get('items', [])]

    def token(self):
        if not self.path.is_file():
            raise AppError('Primero conectá YouTube con youtube-login.')
        token = json.loads(self.path.read_text(encoding='utf-8'))
        if token.get('expires_at', 0) < time.time() + 90:
            refreshed = self.http.json('POST', 'https://oauth2.googleapis.com/token', form={**self.client(),
                'grant_type': 'refresh_token', 'refresh_token': token['refresh_token']})
            if not refreshed.get('access_token'):
                raise AppError('Google no renovó el acceso. Volvé a ejecutar youtube-login.')
            token.update(refreshed)
            token['expires_at'] = time.time() + refreshed.get('expires_in', 3600)
            write_json(self.path, token)
        return token['access_token']


class Publisher:
    def __init__(self, config, store, http=None):
        self.config, self.store, self.http = config, store, http or Http()

    def preview(self, job_id, platform, privacy='private', video_url=''):
        if platform not in ('youtube', 'instagram') or privacy not in ('private', 'unlisted', 'public'):
            raise AppError('Destino o visibilidad inválidos.')
        job = self.store.get(job_id)
        if job.get('demo'):
            raise AppError('Una demostración no se puede publicar.')
        approved(job)
        video = job.get('video')
        if not video or job['state'] != 'ready':
            raise AppError('Primero renderizá o adjuntá el video final.')
        if video['script_hash'] != digest(job['script']) or file_digest(video['path']) != video['sha256']:
            raise AppError('El video cambió o no corresponde al guion aprobado.')
        verify_video(video['path'])
        copy = job['agents'].get('06-thumbnail-copy')
        if not copy:
            raise AppError('Falta preparar el copy con produce.')
        disclosure = '\n\nVoz generada con IA.' if video.get('synthetic_voice') else ''
        snapshot = {'job': job_id, 'platform': platform, 'video_sha256': video['sha256'],
                    'script_sha256': digest(job['script']), 'local_video': video['path']}
        if platform == 'youtube':
            title = copy['youtube_title']
            description = social_text(copy['youtube_description'], copy['hashtags'], disclosure)
            if not 1 <= len(title) <= 100 or len(description.encode('utf-8')) > 5000 or '<' in title or '>' in title:
                raise AppError('Título o descripción de YouTube fuera de los límites admitidos.')
            snapshot.update(target=self.config.require('YOUTUBE_CHANNEL_ID'), privacy=privacy,
                            title=title, description=description, made_for_kids=False)
        else:
            caption = social_text(copy['instagram_caption'], copy['hashtags'], disclosure)
            if len(caption) > 2200 or len(re.findall(r'(?<!\w)#\w+', caption)) > 30:
                raise AppError('El caption completo de Instagram supera 2200 caracteres o 30 hashtags.')
            version = self.config.require('INSTAGRAM_API_VERSION')
            if not re.fullmatch(r'v\d+\.\d+', version):
                raise AppError('INSTAGRAM_API_VERSION debe tener el formato vNN.0.')
            snapshot.update(target=self.config.require('INSTAGRAM_USER_ID'), caption=caption,
                            video_url=public_url(video_url), api_version=version, privacy='public')
        snapshot['confirmation'] = digest(snapshot)[:20]
        return snapshot

    def publish(self, job_id, platform, confirmation, privacy='private', video_url=''):
        with self.store.lock(job_id):
            snapshot = self.preview(job_id, platform, privacy, video_url)
            if not secrets.compare_digest(snapshot['confirmation'], confirmation):
                raise AppError('La confirmación no coincide con el video, copy, cuenta o visibilidad actuales. Repetí preview.')
            record = self.store.publication(job_id, platform)
            if record and record['fingerprint'] != digest(snapshot):
                raise AppError('Ya hay una publicación iniciada con otros datos. No se creará un duplicado.')
            if record and record['state'] in ('published', 'uploaded'):
                return self.receipt(record)
            if platform == 'youtube':
                token = YouTubeAuth(self.config, self.http).token()
                identity = self.http.json('GET', 'https://www.googleapis.com/youtube/v3/channels?part=id&mine=true', headers=bearer(token))
                if [c['id'] for c in identity.get('items', [])] != [snapshot['target']]:
                    raise AppError('El token de YouTube no corresponde al canal confirmado.')
            else:
                token = self.config.require('INSTAGRAM_ACCESS_TOKEN')
                identity = self.http.json('GET', f"https://graph.instagram.com/{snapshot['api_version']}/me?fields=user_id,username", headers=bearer(token))
                if str(identity.get('user_id', '')) != snapshot['target']:
                    raise AppError('El token de Instagram no corresponde a la cuenta confirmada.')
                if not record and self.http.remote_digest(snapshot['video_url']) != snapshot['video_sha256']:
                    raise AppError('El MP4 de la URL pública no coincide con el archivo revisado.')
            if not record:
                record = {'fingerprint': digest(snapshot), 'state': 'reserved', 'started_at': now(),
                          'platform': platform, 'target': snapshot['target']}
                self.store.put_publication(job_id, platform, record)
            elif record['state'] in ('unknown', 'reserved', 'publishing', 'failed') and not (platform == 'youtube' and record.get('upload_url')):
                raise AppError('Hay un intento sin resultado confirmable. Usá reconcile con el ID remoto; no se repetirá la publicación.')
            try:
                if platform == 'youtube':
                    self._youtube(snapshot, record, token)
                else:
                    self._instagram(snapshot, record, token)
            except Exception:
                if platform == 'instagram' and record['state'] == 'processing' and record.get('container_id'):
                    # Consultar estado no publica. Un fallo de lectura permite volver a consultar.
                    record['next_check_at'] = time.time() + 60
                elif record['state'] not in ('uploaded', 'published', 'failed'):
                    record['state'] = 'unknown'
                self.store.put_publication(job_id, platform, record)
                raise
            return self.receipt(record)

    @staticmethod
    def receipt(record):
        return {k: v for k, v in record.items() if k in ('state', 'platform', 'target', 'remote_id', 'url', 'next_check_at', 'started_at', 'finished_at')}

    def _youtube(self, snap, record, token):
        save = lambda: self.store.put_publication(snap['job'], 'youtube', record)
        from pathlib import Path
        video = Path(snap['local_video'])
        size = video.stat().st_size
        if not record.get('upload_url'):
            _, headers, _ = self.http.request('POST', 'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status&notifySubscribers=false',
                headers={**bearer(token), 'X-Upload-Content-Length': str(size), 'X-Upload-Content-Type': 'video/mp4'},
                data={'snippet': {'title': snap['title'], 'description': snap['description'], 'categoryId': '27'},
                      'status': {'privacyStatus': snap['privacy'], 'selfDeclaredMadeForKids': snap['made_for_kids']}})
            upload_url = header(headers, 'Location') or ''
            parsed = urllib.parse.urlsplit(upload_url)
            if parsed.scheme != 'https' or parsed.hostname not in ('www.googleapis.com', 'youtube.googleapis.com'):
                raise AppError('YouTube no devolvió una URL de subida válida.')
            record.update(upload_url=upload_url, state='uploading')
            save()
        # Consultar la misma sesión recupera incluso una respuesta final perdida.
        status, headers, body = self.http.request('PUT', record['upload_url'],
            headers={**bearer(token), 'Content-Range': f'bytes */{size}', 'Content-Length': '0'}, body=b'', accepted=(308,))
        if status in (200, 201):
            self._youtube_done(record, body)
            save()
            return
        offset = self._offset(headers, size)
        with video.open('rb') as stream:
            while offset < size:
                stream.seek(offset)
                chunk = stream.read(8 * 1024 * 1024)
                end = offset + len(chunk) - 1
                status, headers, body = self.http.request('PUT', record['upload_url'],
                    headers={**bearer(token), 'Content-Type': 'video/mp4', 'Content-Length': str(len(chunk)),
                             'Content-Range': f'bytes {offset}-{end}/{size}'}, body=chunk, timeout=120, accepted=(308,))
                if status in (200, 201):
                    self._youtube_done(record, body)
                    save()
                    return
                next_offset = self._offset(headers, size)
                if next_offset <= offset:
                    raise AppError('La subida no avanzó. Se conserva la misma sesión para consultarla después.')
                offset = next_offset
        raise AppError('YouTube aún no confirmó el video completo. Repetí el comando para consultar la misma sesión.')

    @staticmethod
    def _offset(headers, size):
        value = header(headers, 'Range')
        if not value:
            return 0
        match = re.fullmatch(r'bytes=0-(\d+)', value)
        if not match or not 0 < int(match[1]) + 1 <= size:
            raise AppError('YouTube devolvió un rango de subida inválido.')
        return int(match[1]) + 1

    @staticmethod
    def _youtube_done(record, body):
        try:
            remote_id = json.loads(body)['id']
        except (ValueError, KeyError):
            raise AppError('YouTube no confirmó el identificador del video.') from None
        if not re.fullmatch(r'[a-zA-Z0-9_-]{11}', remote_id):
            raise AppError('YouTube devolvió un ID de video inválido.')
        record.update(state='uploaded', remote_id=remote_id, url='https://youtu.be/' + remote_id, finished_at=now())

    def _instagram(self, snap, record, token):
        base = 'https://graph.instagram.com/' + snap['api_version']
        save = lambda: self.store.put_publication(snap['job'], 'instagram', record)
        if not record.get('container_id'):
            response = self.http.json('POST', base + '/' + snap['target'] + '/media', headers=bearer(token),
                data={'media_type': 'REELS', 'video_url': snap['video_url'], 'caption': snap['caption'], 'share_to_feed': True})
            if not str(response.get('id', '')).isdigit():
                raise AppError('Instagram no confirmó el contenedor.')
            record.update(container_id=str(response['id']), state='processing', next_check_at=time.time() + 60)
            save()
            return
        if time.time() < record.get('next_check_at', 0):
            return
        response = self.http.json('GET', base + '/' + record['container_id'] + '?fields=status_code', headers=bearer(token))
        status = response.get('status_code')
        if status == 'IN_PROGRESS':
            record['next_check_at'] = time.time() + 60
            save()
            return
        if status in ('ERROR', 'EXPIRED'):
            record['state'] = 'failed'
            save()
            raise AppError('Instagram rechazó el contenedor o dejó que venciera. No se creó otro automáticamente.')
        if status != 'FINISHED':
            raise AppError('El contenedor no está listo o ya fue publicado; reconciliá antes de continuar.')
        record['state'] = 'publishing'
        save()
        result = self.http.json('POST', base + '/' + snap['target'] + '/media_publish', headers=bearer(token),
                                data={'creation_id': record['container_id']})
        if not str(result.get('id', '')).isdigit():
            raise AppError('Instagram no devolvió el ID de publicación. Se bloquean reintentos para evitar duplicados.')
        record.update(state='published', remote_id=str(result['id']), finished_at=now())
        save()
        # La consulta del permalink no debe convertir una publicación confirmada en desconocida.
        try:
            media = self.http.json('GET', base + '/' + record['remote_id'] + '?fields=permalink', headers=bearer(token))
            record['url'] = media.get('permalink', '')
            save()
        except AppError:
            pass

    def reconcile(self, job_id, platform, remote_id):
        with self.store.lock(job_id):
            record = self.store.publication(job_id, platform)
            if not record:
                raise AppError('No hay un intento de publicación para reconciliar.')
            if record['state'] in ('published', 'uploaded'):
                return self.receipt(record)
            if platform == 'youtube':
                if not re.fullmatch(r'[a-zA-Z0-9_-]{11}', remote_id):
                    raise AppError('ID de YouTube inválido.')
                token = YouTubeAuth(self.config, self.http).token()
                result = self.http.json('GET', 'https://www.googleapis.com/youtube/v3/videos?part=snippet,status&id=' + remote_id,
                                        headers=bearer(token))
                items = result.get('items', [])
                if len(items) != 1 or items[0]['snippet']['channelId'] != record['target']:
                    raise AppError('El video no pertenece al canal del intento original.')
                record.update(state='uploaded', url='https://youtu.be/' + remote_id)
            else:
                if not remote_id.isdigit():
                    raise AppError('ID de Instagram inválido.')
                base = 'https://graph.instagram.com/' + self.config.require('INSTAGRAM_API_VERSION')
                token = self.config.require('INSTAGRAM_ACCESS_TOKEN')
                result = self.http.json('GET', base + '/' + remote_id + '?fields=owner,permalink', headers=bearer(token))
                if str(result.get('owner', {}).get('id', '')) != record['target']:
                    raise AppError('La publicación no pertenece a la cuenta del intento original.')
                record.update(state='published', url=result.get('permalink', ''))
            record.update(remote_id=remote_id, finished_at=now(), reconciled_by='operator')
            self.store.put_publication(job_id, platform, record)
            return self.receipt(record)
