from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

from .config import AppError


OPENAI_ERRORS = {
    'credit_balance_exhausted': 'La organización no tiene créditos disponibles para la API. Activá un beneficio elegible o agregá créditos en https://platform.openai.com/settings/organization/billing.',
    'organization_spend_limit_exceeded': 'Se alcanzó el límite de gasto de la organización. Revisá https://platform.openai.com/settings/organization/limits.',
    'project_spend_limit_exceeded': 'Se alcanzó el límite de gasto del proyecto. Revisá los límites de ese proyecto en OpenAI Platform.',
    'organization_usage_limit_exceeded': 'Se alcanzó el límite de uso asignado por OpenAI a la organización. Revisá https://platform.openai.com/settings/organization/limits.',
    'insufficient_quota': 'Revisá el saldo y los límites del proyecto en OpenAI Platform.',
    'rate_limit_exceeded': 'Esperá antes de repetir la solicitud; no se reintentó automáticamente.',
    'slow_down': 'La frecuencia de solicitudes aumentó demasiado rápido. Respetá Retry-After antes de volver a intentar.',
    'server_is_overloaded': 'El modelo está temporalmente sobrecargado. Respetá Retry-After antes de volver a intentar.',
    'model_not_found': 'El modelo configurado no está disponible para este proyecto.',
    'invalid_api_key': 'La credencial no es válida o venció. Revisá la conexión de OpenAI.',
}


def openai_error_code(raw):
    """Preferir el código específico y usar el tipo como respaldo, sin devolver mensajes externos."""
    try:
        error = json.loads(raw).get('error', {})
    except (ValueError, AttributeError, UnicodeError):
        return ''
    if not isinstance(error, dict):
        return ''
    for candidate in (error.get('code'), error.get('type')):
        if isinstance(candidate, str) and candidate in OPENAI_ERRORS:
            return candidate
    return ''


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Http:
    """No reintenta escrituras ni imprime URLs, cuerpos o headers privados."""

    def __init__(self):
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, url, *, headers=None, data=None, body=None, form=None, timeout=90, accepted=()):
        if urllib.parse.urlsplit(url).scheme != 'https':
            raise AppError('Las llamadas externas requieren HTTPS.')
        headers = dict(headers or {})
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        if form is not None:
            body = urllib.parse.urlencode(form).encode('utf-8')
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            response = self.opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code in accepted:
                response = exc
            else:
                code = exc.code
                try:
                    provider_code = openai_error_code(exc.read(16384))
                finally:
                    exc.close()
                if provider_code:
                    raise AppError(f'OpenAI: {provider_code}. {OPENAI_ERRORS[provider_code]}') from None
                hints = {401: 'credencial inválida o vencida', 403: 'acceso o permisos insuficientes',
                         429: 'límite de solicitudes o cuota; verificá la cuenta', 400: 'solicitud rechazada por el proveedor'}
                raise AppError(f'HTTP {code}: {hints.get(code, "error del proveedor")}. No se reintentó la escritura.') from None
        except (OSError, urllib.error.URLError, TimeoutError):
            raise AppError('No se pudo confirmar la respuesta del proveedor. Revisá el estado antes de reintentar.') from None
        with response:
            return response.status, dict(response.headers.items()), response.read()

    def json(self, method, url, **kwargs):
        _, _, raw = self.request(method, url, **kwargs)
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError):
            raise AppError('El proveedor devolvió una respuesta JSON inválida.') from None

    def remote_digest(self, url, max_size=100 * 1024 * 1024):
        # La URL es explícita del operador; no se envía ninguna credencial.
        request = urllib.request.Request(url, method='GET')
        try:
            with self.opener.open(request, timeout=60) as response:
                digest, size = hashlib.sha256(), 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_size:
                        raise AppError('El video remoto supera el límite local de 100 MiB.')
                    digest.update(chunk)
                return digest.hexdigest()
        except (OSError, urllib.error.URLError):
            raise AppError('No se pudo verificar la URL pública del video; usá una URL HTTPS directa.') from None
