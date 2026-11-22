from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path


class AppError(Exception):
    """Error seguro para mostrar en consola, sin credenciales."""


class Config:
    def __init__(self, root: Path | None = None, env: dict | None = None):
        self.root = (root or Path(__file__).resolve().parents[1]).resolve()
        self.values = {}
        local = self.root / '.env.local'
        if env is None and local.is_file():
            for line in local.read_text(encoding='utf-8-sig').splitlines():
                match = re.match(r'^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$', line)
                if match:
                    key, value = match.groups()
                    if value[:1] in ('"', "'") and value[-1:] == value[:1]:
                        value = value[1:-1]
                    self.values[key] = value
        self.values.update(os.environ if env is None else env)
        self.runtime = self.root / 'runtime'

    def get(self, key: str, default: str = '') -> str:
        return self.values.get(key) or default

    def require(self, key: str) -> str:
        value = self.get(key)
        if not value:
            raise AppError(f'Falta configurar {key}. Ejecutá doctor para revisar las conexiones.')
        return value

    def path(self, value: str) -> Path:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (self.root / path).resolve()

    def brand(self) -> dict:
        return json.loads((self.root / 'config/brand-guidelines.json').read_text(encoding='utf-8-sig'))

    def doctor(self) -> dict:
        return {
            'python': 'OK (solo biblioteca estándar)',
            'ffmpeg': bool(shutil.which('ffmpeg')),
            'ffprobe': bool(shutil.which('ffprobe')),
            'openai_configurada': bool(self.get('OPENAI_API_KEY')),
            'modelo': self.get('OPENAI_MODEL', 'gpt-6-luna'),
            'voz_elevenlabs_configurada': all(self.get(k) for k in ('ELEVENLABS_API_KEY', 'ELEVENLABS_VOICE_ID')),
            'youtube_cliente_oauth': self.path(self.get('YOUTUBE_CLIENT_FILE', 'credentials/youtube-client.json')).is_file(),
            'youtube_token_guardado': (self.runtime / 'youtube-token.json').is_file(),
            'youtube_canal_configurado': bool(self.get('YOUTUBE_CHANNEL_ID')),
            'instagram_composio_cli_instalada': Path('D:/Herramientas/marketing/composio/composio-windows-x64/composio.exe').is_file(),
            'telegram_configurado': all(self.get(k) for k in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_USER_ID')),
            'nota': 'Presencia local; no verifica acceso, permisos ni saldo en las cuentas.',
        }
