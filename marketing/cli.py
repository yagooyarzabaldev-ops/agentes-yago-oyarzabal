from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agents import Workflow
from .config import AppError, Config
from .media import attach, render, synthesize
from .net import Http
from .publish import Publisher, YouTubeAuth
from .store import Store, digest
from .telegram import Telegram
from .style import load_style, video_format


def output(value):
    print(json.dumps(value, ensure_ascii=False, indent=2) if not isinstance(value, str) else value)


def parser():
    app = argparse.ArgumentParser(description='Agentes para Shorts y Reels de @yago.oyarzabal')
    commands = app.add_subparsers(dest='command', required=True)
    for name in ('doctor', 'check-openai', 'list', 'youtube-login', 'demo', 'menu', 'style'):
        commands.add_parser(name)
    new = commands.add_parser('new', help='Guardar una idea, sin llamadas a la API')
    new.add_argument('idea')
    new.add_argument('--format', choices=('editorial', 'roulette'), default='editorial')
    week = commands.add_parser('import-week', help='Importar los siete briefs, sin aprobarlos ni generar con IA')
    week.add_argument('--file', default='content/semana-1.md')
    for name in ('show', 'draft', 'produce', 'voice', 'export', 'telegram-request'):
        cmd = commands.add_parser(name)
        cmd.add_argument('job')
    approval = commands.add_parser('approve')
    approval.add_argument('job')
    approval.add_argument('--hash', required=True, help='Huella de la versión mostrada por show')
    approval.add_argument('--claims-reviewed', action='store_true')
    revise = commands.add_parser('revise')
    revise.add_argument('job')
    revise.add_argument('feedback')
    render_cmd = commands.add_parser('render')
    render_cmd.add_argument('job')
    render_cmd.add_argument('--background', help='Video propio usado de fondo; también puede aportar la voz')
    render_cmd.add_argument('--audio', help='Narración grabada del guion aprobado')
    render_cmd.add_argument('--winner', type=int, required=True, help='Opción 0–7 coherente con el guion; giro visual simulado')
    attach_cmd = commands.add_parser('attach-video')
    attach_cmd.add_argument('job')
    attach_cmd.add_argument('file')
    attach_cmd.add_argument('--synthetic-voice', action='store_true')
    for name in ('preview', 'publish'):
        cmd = commands.add_parser(name)
        cmd.add_argument('job')
        cmd.add_argument('platform', choices=('youtube', 'instagram'))
        cmd.add_argument('--privacy', choices=('private', 'unlisted', 'public'), default='private', help='YouTube; Instagram siempre es público')
        cmd.add_argument('--video-url', default='', help='Instagram: URL HTTPS pública del mismo MP4')
        if name == 'publish':
            cmd.add_argument('--confirm', required=True, help='Huella del paquete mostrado por preview')
    reconcile = commands.add_parser('reconcile')
    reconcile.add_argument('job')
    reconcile.add_argument('platform', choices=('youtube', 'instagram'))
    reconcile.add_argument('--remote-id', required=True, help='ID que comprobaste en tu cuenta tras un intento incierto')
    analysis = commands.add_parser('analyze')
    analysis.add_argument('job')
    analysis.add_argument('--metrics', required=True, help='JSON con retencion_3s, retencion_50pct, comentarios y compartidos')
    telegram = commands.add_parser('telegram-poll')
    telegram.add_argument('--watch', action='store_true', help='Mantener recepción por long polling; Ctrl+C para terminar')
    return app


def summary(job):
    return {'id': job['id'], 'estado': job['state'], 'idea': job['idea'].splitlines()[0]}


def demo(config, store):
    example = json.loads((config.root / 'examples/demo.json').read_text(encoding='utf-8'))
    job = store.create('DEMO LOCAL — no publicable', source='builtin-demo-v1', video_format='roulette')
    with store.lock(job['id']):
        job.update(script=example['script'], agents=example['agents'], state='demo', demo=True)
        store.save(job)
    path = render(config, store, job['id'], demo=True, winner=0)
    return {'id': job['id'], 'video': str(path), 'preview': str(path.with_name('preview.jpg')),
            'nota': 'Vista de prueba sin narración, sin llamadas externas y bloqueada para publicación.'}


def menu(config, store):
    print('\nAGENTE MARKETING — Shorts / Reels\n')
    while True:
        print('1 Diagnóstico | 2 Importar semana 1 | 3 Ver trabajos | 4 Crear idea | 5 Demo de video | 6 Trabajar con un video | 0 Salir')
        choice = input('Elegí una opción: ').strip()
        if choice == '0':
            return
        if choice == '1':
            output(config.doctor())
        elif choice == '2':
            output([summary(j) for j in Workflow(config, store).import_week(config.root / 'content/semana-1.md')])
        elif choice == '3':
            output([summary(j) for j in store.list()])
            print('Para avanzar un trabajo, usá los comandos del README con su ID.')
        elif choice == '4':
            idea = input('Tema o idea: ').strip()
            if idea:
                output(summary(store.create(idea)))
        elif choice == '5':
            output(demo(config, store))
        elif choice == '6':
            output([summary(j) for j in store.list()])
            job_id = input('ID del trabajo: ').strip()
            try:
                store.get(job_id)
                work_menu(config, store, job_id)
            except AppError as exc:
                print('ERROR:', exc)


def work_menu(config, store, job_id):
    workflow = Workflow(config, store)
    while True:
        job = store.get(job_id)
        print(f"\nTrabajo {job_id} — {job['state']}")
        print('1 Ver guion | 2 Generar guion | 3 Pedir cambios | 4 Aprobar guion | 5 Preparar producción')
        print('6 Voz sintética opcional | 7 Render ruleta histórico | 8 Adjuntar MP4 final | 9 Revisar/publicar | 10 Exportar plan | 0 Volver')
        choice = input('Elegí una opción: ').strip()
        if choice == '0':
            return
        try:
            if choice == '1':
                output(job.get('script', {'idea': job['idea']}))
            elif choice == '2':
                output(summary(workflow.draft(job_id)))
            elif choice == '3':
                output(summary(workflow.revise(job_id, input('Qué querés cambiar: '))))
            elif choice == '4':
                if 'script' not in job:
                    raise AppError('Primero generá el guion.')
                output(job['script'])
                note = ' y comprobar las afirmaciones pendientes' if job['script']['claims_to_verify'] else ''
                if input(f'Escribí APROBAR después de revisar el guion{note}: ').strip() == 'APROBAR':
                    output(summary(workflow.approve(job_id, digest(job['script'])[:16], claims_reviewed=True)))
            elif choice == '5':
                output(summary(workflow.produce(job_id)))
            elif choice == '6':
                output(str(synthesize(config, store, job_id)))
            elif choice == '7':
                if video_format(job) != 'roulette':
                    raise AppError('El formato editorial usa el plan exportado y montaje con herramientas de producción. Adjuntá su MP4 en opción 8.')
                background = input('Ruta del video de fondo (vacío: plantilla): ').strip().strip('"') or None
                audio = input('Ruta de narración (vacío: voz ya generada o audio del fondo): ').strip().strip('"') or None
                options = job['agents'].get('03-roulette-master', {}).get('options', [])
                output([{'opción': i, 'texto': x['label']} for i, x in enumerate(options)])
                winner = int(input('Resultado de la ruleta coherente con el guion (0–7): '))
                output(str(render(config, store, job_id, background=background, audio=audio, winner=winner)))
            elif choice == '8':
                path = input('Ruta del MP4 final: ').strip().strip('"')
                synthetic = input('¿Tiene voz sintética? Escribí SI o NO: ').strip().upper() == 'SI'
                output(str(attach(store, job_id, config.path(path), synthetic)))
            elif choice == '9':
                platform = input('Destino (youtube o instagram): ').strip().lower()
                privacy = 'public'
                if platform == 'youtube':
                    privacy = input('Visibilidad (private/unlisted/public; vacío: private): ').strip() or 'private'
                video_url = input('URL HTTPS pública del mismo MP4: ').strip() if platform == 'instagram' else ''
                publisher = Publisher(config, store)
                preview = publisher.preview(job_id, platform, privacy, video_url)
                output(preview)
                if input('Revisá el MP4 y el paquete. Para enviarlo ahora, escribí PUBLICAR: ').strip() == 'PUBLICAR':
                    output(publisher.publish(job_id, platform, preview['confirmation'], privacy, video_url))
            elif choice == '10':
                output(str(workflow.export(job)))
        except (AppError, ValueError, OSError) as exc:
            print('ERROR:', str(exc) if isinstance(exc, AppError) else 'Revisá la ruta o el valor ingresado.')


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    args = parser().parse_args(argv)
    config = Config()
    try:
        if args.command == 'style':
            output(load_style(config.root))
            return 0
        if args.command == 'doctor':
            output(config.doctor())
            return 0
        if args.command == 'check-openai':
            result = Http().json('POST', 'https://api.openai.com/v1/responses',
                headers={'Authorization': 'Bearer ' + config.require('OPENAI_API_KEY')},
                data={'model': config.get('OPENAI_MODEL', 'gpt-6-luna'), 'input': 'Respondé solamente OK.',
                      'max_output_tokens': 64, 'store': False})
            if result.get('status') != 'completed':
                raise AppError('La API respondió, pero la prueba no completó su salida.')
            output({'estado': 'conectado', 'modelo': config.get('OPENAI_MODEL', 'gpt-6-luna')})
            return 0
        store = Store(config.runtime)
        workflow = Workflow(config, store)
        cmd = args.command
        if cmd == 'menu':
            menu(config, store)
        elif cmd == 'new':
            if not args.idea.strip():
                raise AppError('La idea no puede estar vacía.')
            output(summary(store.create(args.idea, video_format=args.format)))
        elif cmd == 'import-week':
            output([summary(j) for j in workflow.import_week(config.path(args.file))])
        elif cmd == 'list':
            output([summary(j) for j in store.list()])
        elif cmd == 'show':
            job = store.get(args.job)
            output(job)
            if 'script' in job:
                print('\nHuella para aprobar:', digest(job['script'])[:16])
            for platform in ('youtube', 'instagram'):
                if record := store.publication(args.job, platform):
                    output(Publisher.receipt(record))
        elif cmd == 'draft':
            job = workflow.draft(args.job)
            output(summary(job))
            print('Revisá el guion con: python -m marketing show', args.job)
        elif cmd == 'approve':
            output(summary(workflow.approve(args.job, args.hash, args.claims_reviewed)))
        elif cmd == 'revise':
            output(summary(workflow.revise(args.job, args.feedback)))
        elif cmd == 'produce':
            output(summary(workflow.produce(args.job)))
        elif cmd == 'voice':
            output(str(synthesize(config, store, args.job)))
        elif cmd == 'render':
            output(str(render(config, store, args.job, background=args.background, audio=args.audio, winner=args.winner)))
        elif cmd == 'attach-video':
            output(str(attach(store, args.job, config.path(args.file), args.synthetic_voice)))
        elif cmd == 'export':
            output(str(workflow.export(store.get(args.job))))
        elif cmd in ('preview', 'publish'):
            publisher = Publisher(config, store)
            if cmd == 'preview':
                output(publisher.preview(args.job, args.platform, args.privacy, args.video_url))
            else:
                output(publisher.publish(args.job, args.platform, args.confirm, args.privacy, args.video_url))
        elif cmd == 'reconcile':
            output(Publisher(config, store).reconcile(args.job, args.platform, args.remote_id))
        elif cmd == 'youtube-login':
            with store.lock('youtube-auth'):
                output(YouTubeAuth(config, Http()).login())
            print('Configurá YOUTUBE_CHANNEL_ID con el ID del canal que querés utilizar.')
        elif cmd == 'telegram-request':
            output(Telegram(config, store).request(args.job))
        elif cmd == 'telegram-poll':
            telegram = Telegram(config, store)
            while True:
                output(telegram.poll())
                if not args.watch:
                    break
        elif cmd == 'analyze':
            metrics = json.loads(config.path(args.metrics).read_text(encoding='utf-8-sig'))
            output(workflow.analyze(args.job, metrics))
        elif cmd == 'demo':
            output(demo(config, store))
        return 0
    except (AppError, FileNotFoundError, PermissionError, ValueError, KeyError, OSError) as exc:
        # Nunca imprimir datos arbitrarios de respuestas o archivos de credenciales.
        message = str(exc) if isinstance(exc, AppError) else 'No se pudo leer o procesar un archivo. Revisá las rutas y el formato.'
        print('ERROR:', message, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nOperación interrumpida. Consultá el estado antes de continuar.', file=sys.stderr)
        return 130
