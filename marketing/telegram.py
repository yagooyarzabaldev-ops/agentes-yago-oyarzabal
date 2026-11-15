from __future__ import annotations

from .agents import Workflow
from .config import AppError
from .net import Http
from .store import digest


class Telegram:
    def __init__(self, config, store, http=None):
        self.config, self.store, self.http = config, store, http or Http()
        self.chat = config.require('TELEGRAM_CHAT_ID')
        self.user = config.require('TELEGRAM_USER_ID')
        self.base = 'https://api.telegram.org/bot' + config.require('TELEGRAM_BOT_TOKEN') + '/'

    def call(self, method, data):
        response = self.http.json('POST', self.base + method, data=data, timeout=40)
        if not response.get('ok'):
            raise AppError('Telegram rechazó la operación. Revisá la conexión del bot.')
        return response.get('result')

    def request(self, job_id):
        with self.store.lock(job_id):
            job = self.store.get(job_id)
            if job['state'] != 'awaiting_approval':
                raise AppError('Solo se envían guiones pendientes de aprobación.')
            if job['script']['claims_to_verify']:
                raise AppError('El guion tiene afirmaciones pendientes. Revisalas y aprobalo por consola o pedí una revisión.')
            script_hash = digest(job['script'])[:16]
            if job.get('telegram', {}).get('hash') == script_hash:
                return {'estado': 'ya_enviado', 'message_id': job['telegram']['message_id']}
            text = job['script']['title'] + '\n\n' + '\n\n'.join(s['spoken'] for s in job['script']['segments'])
            text += f'\n\nTrabajo: {job_id}\nVersión: {script_hash}\n¿Aprobás este guion? SI / NO'
            if len(text) > 4000:
                raise AppError('El guion supera el tamaño de un mensaje; revisalo por consola.')
            result = self.call('sendMessage', {'chat_id': self.chat, 'text': text, 'reply_markup': {'inline_keyboard': [[
                {'text': 'SI, aprobar guion', 'callback_data': f'yes:{job_id}:{script_hash}'},
                {'text': 'NO, revisar', 'callback_data': f'no:{job_id}:{script_hash}'}]]}})
            job['telegram'] = {'hash': script_hash, 'message_id': result['message_id'], 'chat': self.chat, 'user': self.user}
            self.store.save(job)
            return {'estado': 'enviado', 'message_id': result['message_id']}

    def handle(self, query):
        parts = query.get('data', '').split(':')
        message = query.get('message', {})
        if len(parts) != 3 or parts[0] not in ('yes', 'no'):
            return 'Acción no válida.'
        if str(query.get('from', {}).get('id')) != self.user or str(message.get('chat', {}).get('id')) != self.chat:
            return 'No autorizado.'
        action, job_id, script_hash = parts
        job = self.store.get(job_id)
        pending = job.get('telegram', {})
        if (pending.get('hash') != script_hash or pending.get('message_id') != message.get('message_id')
                or pending.get('user') != self.user or pending.get('chat') != self.chat
                or digest(job.get('script'))[:16] != script_hash):
            return 'Esta solicitud ya no corresponde al guion actual.'
        if job['state'] != 'awaiting_approval':
            return 'Esta versión ya recibió una decisión.'
        workflow = Workflow(self.config, self.store)
        if action == 'yes':
            workflow.approve(job_id, script_hash, actor='telegram:' + self.user)
            return 'Guion aprobado. La publicación final se confirma por separado.'
        workflow.revise(job_id, 'Guion rechazado en Telegram. Proponé otro enfoque sin cambiar el tema.')
        return 'Rechazado. Agregá feedback con revise y ejecutá draft para obtener otra versión.'

    def poll(self):
        with self.store.lock('telegram-poll'):
            offset = self.store.meta('telegram_offset') or 0
            updates = self.call('getUpdates', {'offset': offset, 'timeout': 30, 'allowed_updates': ['callback_query']})
            outcomes = []
            for update in updates:
                query = update.get('callback_query')
                if query:
                    try:
                        outcome = self.handle(query)
                    except AppError as exc:
                        outcome = str(exc)
                    self.call('answerCallbackQuery', {'callback_query_id': query['id'], 'text': outcome[:180]})
                    outcomes.append(outcome)
                self.store.meta('telegram_offset', update['update_id'] + 1)
            return outcomes
