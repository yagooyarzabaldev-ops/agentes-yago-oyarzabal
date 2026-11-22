"""Forward sanitized office state to its existing private Site; never source logs."""
from __future__ import annotations

import argparse
import getpass
import json
import os
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .office import ROOT, build_snapshot
from .store import write_json

SITE = 'https://infinite-office-marketing-yago.yagooyarzabal.chatgpt.site'


def relay_once(config, snapshot):
    # Only the established private destination is allowed to receive service access.
    if config.get('url') != SITE:
        raise ValueError('El destino del espejo no coincide con la oficina privada.')
    payload = json.dumps(snapshot, ensure_ascii=False).encode('utf-8')
    request = Request(SITE + '/api/ingest', data=payload, method='POST', headers={
        'Content-Type': 'application/json', 'OAI-Sites-Authorization': 'Bearer ' + config['token'],
    })
    # Never follow a redirect with the service token.
    from urllib.request import HTTPRedirectHandler, build_opener
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    with build_opener(NoRedirect).open(request, timeout=8) as response:
        if response.status != 200:
            raise ValueError('El espejo no confirmó la recepción.')
        receipt = json.load(response)
        if receipt.get('ok') is not True:
            raise ValueError('La respuesta del espejo no es válida.')
        return receipt


def run_relay(root=ROOT, stop=None):
    root = Path(root)
    config_path = root / 'runtime/office-relay.private.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    stop = stop or threading.Event()
    delay = 3
    while not stop.is_set():
        try:
            snapshot = build_snapshot(root)
            receipt = relay_once(config, snapshot)
            write_json(root / 'runtime/office-relay-status.json', {'ok': True, 'updated_at': receipt['received_at']})
            delay = 3
        except Exception as error:
            # Do not serialize exception messages: network exceptions can include URLs/headers.
            write_json(root / 'runtime/office-relay-status.json', {'ok': False, 'error_type': type(error).__name__})
            delay = min(60, delay * 2)
        stop.wait(delay)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'runtime/office-relay.private.json'
    if args.configure:
        config = json.loads(getpass.getpass('Configuración del espejo (entrada oculta): '))
        if config.get('url') != SITE or not isinstance(config.get('token'), str) or not config['token']:
            raise ValueError('Configuración inválida.')
        write_json(path, {'url': SITE, 'token': config['token']})
        print('Acceso privado configurado fuera de Git.')
    elif args.once:
        result = relay_once(json.loads(path.read_text(encoding='utf-8')), build_snapshot(ROOT))
        print(json.dumps({'ok': result.get('ok'), 'received_at': result.get('received_at')}))
    else:
        run_relay()


if __name__ == '__main__':
    main()
