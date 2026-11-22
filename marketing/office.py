"""Project observatory: read-only local data and real execution event streaming."""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
STAGES = ['00-orquestador', '01-trend-hunter', '02-guionista', '12-referencias',
          '05-voz', '04-director-visual', '13-motion', '09-montaje', '10-musica',
          '06-thumbnail-copy', '11-control-calidad']
# Curated descriptions summarize the versioned contracts, not an execution log.
ROLES = {
    '00-orquestador': ('Gerencia', 'Estrategia', '#b6a2ff', 'Convierte la idea en un brief y coordina la producción.', ['Idea de Yago', 'Perfil editorial'], ['Brief editorial', 'Decisiones y coordinación']),
    '01-trend-hunter': ('Investigación', 'Estrategia', '#b6a2ff', 'Propone enfoques evergreen y distingue hechos de hipótesis.', ['Brief', 'Evidencia disponible'], ['Cinco enfoques', 'Ganchos y fundamento']),
    '02-guionista': ('Guion', 'Estrategia', '#b6a2ff', 'Escribe el relato en español argentino y conserva la voz real.', ['Brief', 'Investigación', 'Transcripción disponible'], ['Guion segmentado', 'Duración justificada', 'Afirmaciones por revisar']),
    '03-roulette-master': ('Ruleta', 'Especiales', '#94a3b8', 'Prepara la ruleta histórica únicamente cuando se solicita.', ['Pedido explícito', 'Tema'], ['Ocho opciones', 'Probabilidades y acciones']),
    '04-director-visual': ('Dirección visual', 'Estudio visual', '#71d6b4', 'Desarrolla el guion en escenas con imágenes, objetos y movimiento.', ['Guion aprobado', 'Referencias'], ['Storyboard cronometrado', 'Plan de imágenes y transiciones']),
    '05-voz': ('Voz', 'Producción', '#ffb97b', 'Planifica limpieza y sincronía preservando acento y sentido.', ['Grabación real', 'Transcripción medida'], ['Mapa de cortes', 'Voz limpia y tiempos por palabra']),
    '06-thumbnail-copy': ('Copy y portada', 'Entrega', '#f6a1bb', 'Prepara portada y textos coherentes con el video.', ['Guion', 'Dirección visual'], ['Copy para redes', 'Propuestas de portada']),
    '07-analista': ('Análisis', 'Estrategia', '#b6a2ff', 'Convierte métricas aportadas en mejoras concretas del próximo guion.', ['Métricas aportadas por Yago'], ['Cambios por métrica', 'Nuevo gancho']),
    '08-publicador': ('Publicación', 'Entrega', '#f6a1bb', 'Prepara el envío a la cuenta y visibilidad expresamente autorizadas.', ['MP4 revisado', 'Paquete confirmado', 'Cuenta y visibilidad'], ['Comprobante de subida', 'Estado de publicación']),
    '09-montaje': ('Montaje', 'Producción', '#ffb97b', 'Integra voz, cámara, imágenes, motion y subtítulos.', ['Voz', 'Storyboard', 'Motion'], ['Plan de montaje', 'MP4 y subtítulos', 'Proyecto editable']),
    '10-musica': ('Música', 'Producción', '#ffb97b', 'Compone Chicago house minimal sin bajo y mezcla con la voz al frente.', ['Duración', 'Narrativa', 'Voz'], ['Arreglo', 'Instrumental y stems', 'Mezcla y mediciones']),
    '11-control-calidad': ('Calidad', 'Entrega', '#f6a1bb', 'Revisa el plan y exige verificar el export real antes de aprobarlo.', ['Plan', 'Export y evidencias'], ['Observaciones', 'Correcciones con timecode', 'Revisión técnica y perceptual']),
    '12-referencias': ('Referencias', 'Estudio visual', '#71d6b4', 'Investiga el lenguaje visual y registra la procedencia de recursos.', ['Guion', 'Biblioteca de referencias'], ['Mapa idea a recurso', 'Prompts y procedencia']),
    '13-motion': ('Motion', 'Estudio visual', '#71d6b4', 'Diseña animación de objetos y texto con profundidad.', ['Storyboard', 'Recursos'], ['Capas y acciones', 'Timing', 'Transiciones y renders']),
}
STATE_LABELS = {
    'brief': 'Brief pendiente', 'awaiting_approval': 'Guion para revisión',
    'awaiting_revision_review': 'Revisión pendiente', 'approved': 'Guion aprobado',
    'production_ready': 'Plan listo; render pendiente', 'demo': 'Demo histórica',
    'video_ready': 'Video adjunto', 'published': 'Publicación registrada',
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_text(value, limit=200):
    """Export compact labels only, redacting obvious credential-like strings."""
    if not isinstance(value, str):
        return ''
    value = value.splitlines()[0] if value.splitlines() else ''
    value = re.sub(r'(?i)(?:sk-[\w-]+|bearer\s+\S+|(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S+)', '[dato omitido]', value)
    return value.strip()[:limit]


def skill_inventory(skill_paths=None):
    paths = skill_paths if skill_paths is not None else {
        'editar-reels': Path('D:/Herramientas/marketing/skills/editar-reels-claude/SKILL.md'),
        'motion-graphics': Path('D:/Herramientas/marketing/skills/motion-graphics-reels/SKILL.md'),
        'imagegen': Path.home() / '.codex/skills/.system/imagegen/SKILL.md',
        'watch': Path.home() / '.codex/plugins/cache/claude-video/watch/0.3.2/skills/watch/SKILL.md',
    }
    definitions = [
        ('editar-reels', 'Editar reels', 'Montaje, cortes, subtítulos y export con FFmpeg y Python.', ['05-voz', '09-montaje', '10-musica', '11-control-calidad']),
        ('motion-graphics', 'Motion graphics', 'Animación HTML/CSS y render de overlays con transparencia.', ['04-director-visual', '09-montaje', '13-motion']),
        ('imagegen', 'ImageGen', 'Creación y edición de imágenes guiadas por referencias.', ['04-director-visual', '06-thumbnail-copy', '12-referencias']),
        ('watch', 'Watch', 'Inspección de video, fotogramas y transcripción.', ['05-voz', '09-montaje', '11-control-calidad']),
    ]
    return [{'id': sid, 'name': name, 'description': desc, 'agent_ids': ids,
             'available': bool(paths.get(sid) and Path(paths[sid]).is_file()),
             'relationship': 'disponible', 'linked_automatically': False,
             'note': 'Herramienta pertinente para este rol; la CLI no la carga ni la asigna automáticamente.'}
            for sid, name, desc, ids in definitions]


def read_jobs(root):
    """Never construct Store: its initialization creates tables/directories."""
    path = root / 'runtime/marketing.sqlite3'
    if not path.is_file():
        return [], ['Todavía no existe una base local de trabajos.']
    try:
        db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)
        try:
            db.execute('PRAGMA query_only=ON')
            rows = db.execute('SELECT body FROM jobs ORDER BY rowid').fetchall()
        finally:
            db.close()
    except sqlite3.Error:
        return [], ['No se pudo leer la base local; el monitor no modifica ni repara sus datos.']
    jobs, warnings = [], []
    for row in rows:
        try:
            data = json.loads(row[0])
            if isinstance(data, dict):
                jobs.append(data)
            else:
                warnings.append('Se omitió un registro de trabajo inválido.')
        except (TypeError, ValueError):
            warnings.append('Se omitió un registro de trabajo inválido.')
    return jobs, warnings


def production_evidence(root):
    """Selected, known manifest fields; no media or private source material."""
    result = []
    relative = 'content/idea-a-video/produccion-v3.json'
    try:
        record = json.loads((root / relative).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        record = {}
    if isinstance(record, dict) and record.get('status') == 'preview_exported_waiting_for_new_recording':
        preview = root / 'entregas/idea-a-video-v3/De_una_idea_a_un_video_V3_14_IMAGENES.mp4'
        result.append({'title': 'De una idea a un video · V3', 'status': 'Grabación pendiente',
                       'detail': 'El manifiesto registra una previsualización de 70 s y 14 imágenes. Faltan la nueva voz/cámara, la sincronía y la revisión final.',
                       'source': relative, 'artifact_present': preview.is_file(),
                       'execution': 'Producción guiada por el asistente; no acredita ejecución separada de los 14 agentes.',
                       'next_step': 'Grabar voz y cámara para completar el reel.'})
    baseline = root / 'production/baseline.json'
    try:
        base = json.loads(baseline.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        base = {}
    if isinstance(base, dict) and base.get('id') == 'sistemas-ia-v10-chicago-02':
        result.append({'title': 'Base de estilo · V10', 'status': 'Estilo aprobado',
                       'detail': 'Chicago sin bajo 02. Aprobación de estilo registrada el 15/11/2026; no autoriza publicar nuevas piezas.',
                       'source': 'production/baseline.json',
                       'artifact_present': (root / 'entregas/chicago-sin-bajo-02/Sistemas_con_IA_Yago_Chicago_sin_bajo_02.mp4').is_file(),
                       'next_step': 'Aplicar el perfil a las próximas piezas.'})
    return result


def build_snapshot(root=ROOT, mode='local', skill_paths=None):
    root = Path(root).resolve()
    skills = skill_inventory(skill_paths)
    raw_jobs, warnings = read_jobs(root)
    contracts = sorted((root / 'agents').glob('*.md'))
    agents = []
    for contract in contracts:
        aid = contract.stem
        if aid not in ROLES:
            continue
        name, department, color, role, inputs, outputs = ROLES[aid]
        heading = contract.read_text(encoding='utf-8-sig').splitlines()[0].lstrip('# ').strip()
        agents.append({'id': aid, 'name': heading, 'short_name': name, 'department': department,
                       'color': color, 'role': role, 'inputs': inputs, 'outputs': outputs,
                       'contract': 'agents/' + contract.name,
                       'status': 'sin_registro', 'status_label': 'Sin registro de ejecución',
                       'activity_summary': 'Contrato disponible; no hay una etapa guardada en la base local.',
                       'last_record_at': None, 'last_job_id': None, 'records_count': 0,
                       'demo_records_count': 0, 'production_records_count': 0,
                       'skills': [s for s in skills if aid in s['agent_ids']]})
    by_id = {a['id']: a for a in agents}
    jobs, activity = [], []
    for raw in raw_jobs:
        jid = safe_text(raw.get('id'), 80)
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', jid):
            warnings.append('Se omitió un trabajo con identificador inválido.')
            continue
        saved = raw.get('agents') if isinstance(raw.get('agents'), dict) else {}
        completed = [aid for aid in saved if aid in by_id]
        title = safe_text(raw.get('script', {}).get('title') if isinstance(raw.get('script'), dict) else '')
        title = title or safe_text(raw.get('idea')) or ('Trabajo ' + jid)
        state = safe_text(raw.get('state'), 60)
        is_demo = bool(raw.get('demo') or state == 'demo')
        at = safe_text(raw.get('updated_at') or raw.get('created_at'), 50) or None
        video_format = raw.get('video_format', 'roulette' if '03-roulette-master' in saved else 'editorial')
        expected = STAGES if video_format == 'editorial' else [
            '00-orquestador', '01-trend-hunter', '02-guionista', '03-roulette-master',
            '04-director-visual', '05-voz', '06-thumbnail-copy']
        pending = [] if is_demo else [aid for aid in expected if aid in by_id and aid not in completed]
        next_step = {
            'brief': 'Preparar o retomar el brief y el guion.',
            'awaiting_approval': 'Revisar el contenido del guion.',
            'awaiting_revision_review': 'Revisar la versión corregida.',
            'approved': 'Preparar el plan de producción.',
            'production_ready': 'Producir los recursos, montar y revisar el export.',
            'demo': 'Demo histórica; no publicable.',
        }.get(state, 'Consultar el estado del trabajo en la CLI.')
        jobs.append({'id': jid, 'title': title, 'state': state,
                     'state_label': STATE_LABELS.get(state, state or 'Estado no registrado'),
                     'created_at': safe_text(raw.get('created_at'), 50) or None,
                     'updated_at': at, 'completed_agents': completed, 'pending_agents': pending,
                     'pending_agents_note': 'Roles del flujo sin etapa guardada; no es una asignación de trabajo.',
                     'video_format': safe_text(video_format, 30),
                     'next_step': next_step, 'video_attached': bool(raw.get('video')),
                     'is_demo': is_demo,
                     'source': 'runtime/marketing.sqlite3',
                     'timing_note': 'La fecha corresponde al trabajo, no al momento individual de cada etapa.'})
        for aid in completed:
            agent = by_id[aid]
            agent['records_count'] += 1
            agent['demo_records_count' if is_demo else 'production_records_count'] += 1
            if not agent['last_record_at'] or (at or '') >= agent['last_record_at']:
                agent.update(status='sin_telemetria', status_label='Etapa guardada · sin telemetría',
                             activity_summary='Último trabajo con etapa guardada: ' + title,
                             last_record_at=at, last_job_id=jid)
            activity.append({'id': jid + ':' + aid, 'agent_id': aid, 'job_id': jid,
                             'title': ('Demo · ' if is_demo else '') + agent['short_name'] + ' · ' + title,
                             'kind': 'etapa_guardada', 'at': at,
                             'is_demo': is_demo,
                             'timing_note': 'Fecha del trabajo; la etapa no tiene una marca de tiempo propia.'})
    jobs.sort(key=lambda j: j['updated_at'] or '', reverse=True)
    activity.sort(key=lambda item: item['at'] or '', reverse=True)
    snapshot = {
        'schema_version': 1, 'generated_at': utc_now(),
        'source': {'mode': mode, 'label': 'Proyecto local' if mode == 'local' else 'Copia del proyecto',
                   'heartbeat_available': False,
                   'notice': 'La CLI guarda etapas y trabajos, pero no emite actividad en vivo por agente. Una etapa guardada no demuestra que el agente esté trabajando ahora.'},
        'summary': {'agents_total': len(agents), 'agents_with_records': sum(a['records_count'] > 0 for a in agents),
                    'jobs_total': len(jobs), 'active_verified': 0,
                    'skills_available': sum(s['available'] for s in skills), 'skills_linked_automatically': 0},
        'agents': agents, 'skills': skills, 'jobs': jobs, 'activity': activity,
        'evidence': production_evidence(root), 'warnings': list(dict.fromkeys(warnings)),
    }
    if mode == 'local':
        attach_live_activity(snapshot, root)
    return snapshot


def attach_live_activity(snapshot, root):
    """Combine independently observed runs; history never becomes a live execution."""
    from .telemetry import read_activity
    from .codex_activity import read_codex_activity
    telemetry = read_activity(root)
    codex = read_codex_activity(root)
    runs = telemetry.get('runs', []) + codex.get('runs', [])
    runs.sort(key=lambda r: r.get('heartbeat_at') or r.get('started_at') or '', reverse=True)
    skills = {s['id']: s['name'] for s in snapshot['skills']}
    skills.update({'sites': 'Sites', 'openai-docs': 'OpenAI Docs', 'built-in-browser': 'Navegador integrado'})
    labels = {'active': 'Trabajando ahora', 'idle': 'En espera', 'completed': 'Trabajo terminado',
              'error': 'Error de ejecución', 'stale': 'Sin señal reciente', 'interrupted': 'Ejecución interrumpida'}
    for agent in snapshot['agents']:
        own = [run for run in runs if run.get('agent_id') == agent['id']]
        active = [run for run in own if run.get('verified_active') and run.get('status') == 'active']
        # A live instrumented command supplies the concrete task. Keep it ahead
        # of generic Codex lifecycle signals while both belong to this role.
        active.sort(key=lambda run: run.get('source') == 'codex')
        current = active[0] if active else own[0] if own else None
        status = 'active' if active else current.get('status', 'idle') if current else 'idle'
        agent.update(live_status=status, live_status_label=labels.get(status, 'En espera'),
                     live_runs=active, last_run=current, current_task=current.get('task') if current else None,
                     current_skill=skills.get(current.get('skill_id'), current.get('skill_id')) if current else None,
                     skill_evidence=current.get('skill_evidence') if current else None)
    snapshot['runs'] = runs[:100]
    snapshot['events'] = sorted(telemetry.get('events', []) + codex.get('events', []),
                                key=lambda e: e.get('at') or '', reverse=True)[:100]
    snapshot['summary']['active_verified'] = sum(a['live_status'] == 'active' for a in snapshot['agents'])
    snapshot['summary']['active_runs'] = sum(bool(r.get('verified_active')) for r in runs)
    snapshot['source'].update(mode='local', heartbeat_available=bool(telemetry.get('available') or codex.get('available')),
                              stream_available=True, notice='Ejecuciones instrumentadas y eventos observados de Codex. Los procesos sin señal reciente no se muestran como activos.',
                              coverage=['CLI de marketing', 'Comandos instrumentados', 'Sesiones Codex de este proyecto'])
    snapshot['warnings'].extend(telemetry.get('warnings', []) + codex.get('warnings', []))


def export_snapshot(destination, root=ROOT):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(build_snapshot(root, mode='snapshot'), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def make_handler(root, site_dir):
    root, site_dir = Path(root).resolve(), Path(site_dir).resolve()

    class OfficeHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Do not print query strings supplied by clients.
            pass

        def send_bytes(self, status, content, content_type):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(content)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            allowed = {'127.0.0.1', 'localhost'}
            try:
                host = urlsplit('http://' + self.headers.get('Host', '')).hostname
            except ValueError:
                host = None
            origin = self.headers.get('Origin')
            if host not in allowed or (origin and origin != f'http://{self.headers.get("Host")}'):
                self.send_bytes(403, b'Forbidden', 'text/plain; charset=utf-8')
                return
            requested = unquote(urlsplit(self.path).path)
            if requested == '/api/events':
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Accel-Buffering', 'no')
                self.end_headers()
                previous = None
                try:
                    while True:
                        snapshot = build_snapshot(root)
                        # Heartbeat changes are valuable: they keep stale detection honest.
                        signature = json.dumps({**snapshot, 'generated_at': None}, sort_keys=True)
                        if signature != previous:
                            payload = json.dumps(snapshot, ensure_ascii=False, separators=(',', ':'))
                            self.wfile.write(('event: office\ndata: ' + payload + '\n\n').encode('utf-8'))
                            previous = signature
                        else:
                            self.wfile.write(('event: heartbeat\ndata: ' + utc_now() + '\n\n').encode('utf-8'))
                        self.wfile.flush()
                        time.sleep(1)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
                return
            if requested == '/api/office':
                body = json.dumps(build_snapshot(root), ensure_ascii=False).encode('utf-8')
                self.send_bytes(200, body, 'application/json; charset=utf-8')
                return
            parts = Path(requested.lstrip('/')).parts
            if (any(part.startswith('.') for part in parts) or '\\' in requested
                    or ':' in requested or any(ord(char) < 32 for char in requested)):
                self.send_bytes(404, b'Not found', 'text/plain; charset=utf-8')
                return
            path = (site_dir / (requested.lstrip('/') or 'index.html')).resolve()
            if not path.is_relative_to(site_dir) or not path.is_file():
                self.send_bytes(404, b'Not found', 'text/plain; charset=utf-8')
                return
            content_type = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
            if content_type.startswith('text/') or path.suffix in ('.js', '.json'):
                content_type += '; charset=utf-8'
            try:
                self.send_bytes(200, path.read_bytes(), content_type)
            except OSError:
                self.send_bytes(404, b'Not found', 'text/plain; charset=utf-8')

        def do_POST(self):
            self.send_bytes(405, b'Read-only monitor', 'text/plain; charset=utf-8')

    return OfficeHandler


def main(argv=None):
    parser = argparse.ArgumentParser(description='Oficina de agentes: monitor local de solo lectura.')
    parser.add_argument('--host', choices=['127.0.0.1', 'localhost'], default='127.0.0.1')
    parser.add_argument('--port', type=int, default=4178)
    parser.add_argument('--site-dir', type=Path, default=ROOT / 'sites/oficina-agentes/dist')
    parser.add_argument('--export', type=Path, help='Exporta una copia resumida y termina.')
    args = parser.parse_args(argv)
    if args.export:
        export_snapshot(args.export)
        print('Copia de la oficina exportada: ' + str(args.export.resolve()))
        return
    if not (args.site_dir / 'index.html').is_file():
        parser.error('La carpeta del sitio no contiene index.html.')
    server = ThreadingHTTPServer((args.host, args.port), make_handler(ROOT, args.site_dir))
    relay_stop = threading.Event()
    if (ROOT / 'runtime/office-relay.private.json').is_file():
        from .office_relay import run_relay
        threading.Thread(target=run_relay, args=(ROOT, relay_stop), daemon=True, name='office-private-relay').start()
    print(f'Oficina local: http://{args.host}:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        relay_stop.set()
        server.server_close()


if __name__ == '__main__':
    main()
