from __future__ import annotations

import base64
import json
import math
import random
import re
import shutil
import struct
import subprocess
import zlib
import wave
from array import array
from pathlib import Path

from .agents import approved, validate_roulette, validate_script
from .config import AppError
from .net import Http
from .store import digest, file_digest, write_json
from .style import video_format


def command(args, cwd=None):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    except FileNotFoundError:
        raise AppError(f'Falta {args[0]} en PATH.') from None
    except subprocess.TimeoutExpired:
        raise AppError('La operación de video superó diez minutos; no se marcó como lista.') from None
    if result.returncode:
        raise AppError(f'{args[0]} falló: {result.stderr[-1800:]}')
    return result.stdout


def probe(path):
    return json.loads(command(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))


def video_info(path):
    data = probe(path)
    video = next((s for s in data.get('streams', []) if s['codec_type'] == 'video'), {})
    audio = next((s for s in data.get('streams', []) if s['codec_type'] == 'audio'), {})
    fps_parts = video.get('avg_frame_rate', '0/1').split('/')
    fps = int(fps_parts[0]) / max(int(fps_parts[-1]), 1)
    return {'width': video.get('width'), 'height': video.get('height'), 'video_codec': video.get('codec_name'),
            'audio_codec': audio.get('codec_name'), 'fps': fps,
            'seconds': float(data.get('format', {}).get('duration', 0)), 'bytes': Path(path).stat().st_size}


def verify_video(path):
    info = video_info(path)
    if (info['width'], info['height']) != (1080, 1920) or info['video_codec'] != 'h264' or info['audio_codec'] != 'aac':
        raise AppError('El video debe ser 1080×1920 con H.264 y audio AAC.')
    if not 34.95 <= info['seconds'] <= 90.1 or not any(abs(info['fps'] - n) < 0.1 for n in (30, 60)):
        raise AppError('El video debe durar 35–90 segundos y tener 30 o 60 fps.')
    if info['bytes'] > 100 * 1024 * 1024:
        raise AppError('Esta versión admite videos de hasta 100 MiB.')
    return info


def ass_time(seconds):
    centis = round(seconds * 100)
    return f'{centis // 360000}:{centis // 6000 % 60:02}:{centis // 100 % 60:02}.{centis % 100:02}'


def escape_ass(text):
    return text.replace('\\', '').replace('{', '').replace('}', '').replace('\n', ' ').replace('\r', ' ')


def ass_file(job, duration, path, words=None, demo=False):
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,66,&H00FFFFFF,&H0000D5FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,90,90,340,1
Style: Title,Arial,55,&H00FFFFFF,&H0000D5FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,8,90,90,225,1
Style: Small,Arial,29,&H0000D5FF,&H0000D5FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,0,8,80,80,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events = []
    def event(start, end, text, style='Default', tags=''):
        events.append(f'Dialogue: 0,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{tags}{text}')
    event(0, duration, '@yago.oyarzabal  /  IA PARA NEGOCIOS', 'Small')
    event(0, duration, escape_ass(job['script']['title']), 'Title')
    if demo:
        event(0, duration, 'VISTA DE PRUEBA · SIN NARRACIÓN', 'Small', '{\\an2\\pos(540,1770)}')
    elif job.get('audio', {}).get('synthetic'):
        event(0, duration, 'VOZ GENERADA CON IA', 'Small', '{\\an2\\pos(540,1770)}')
    total = sum(s['seconds'] for s in job['script']['segments'])
    cursor = 0
    for segment in job['script']['segments']:
        length = duration * segment['seconds'] / total
        event(max(8, cursor), cursor + length, escape_ass(segment['screen']).upper(), 'Title',
              '{\\an5\\pos(540,1020)\\fs64\\c&H00D5FF&}') if cursor + length > 8 else None
        if not words:
            chunks = [segment['spoken'].split()[i:i+5] for i in range(0, len(segment['spoken'].split()), 5)]
            for i, chunk in enumerate(chunks):
                colored = [escape_ass(x) for x in chunk]
                colored[-1] = '{\\c&H00D5FF&}' + colored[-1]
                event(cursor + length*i/len(chunks), cursor + length*(i+1)/len(chunks), ' '.join(colored),
                      tags='{\\fscx100\\fscy100\\t(0,180,\\fscx105\\fscy105)}')
        cursor += length
    if words:
        for index in range(0, len(words), 5):
            chunk = words[index:index+5]
            for active, word in enumerate(chunk):
                end = chunk[active+1]['start'] if active + 1 < len(chunk) else word['end']
                text = ' '.join(('{\\c&H00D5FF&}' if i == active else '{\\c&HFFFFFF&}') + escape_ass(w['text'])
                                for i, w in enumerate(chunk))
                event(word['start'], min(end, duration), text)
    path.write_text(header + '\n'.join(events) + '\n', encoding='utf-8')


def wheel_image(options, directory):
    size = 640
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            dx, dy = x - size/2, y - size/2
            radius = math.hypot(dx, dy)
            sector = int(((math.atan2(dy, dx) + math.pi/2 + math.pi/8) % (2*math.pi)) / (math.pi/4))
            color = (255, 213, 0, 255) if sector % 2 == 0 else (235, 235, 235, 255)
            raw.extend((0, 0, 0, 0) if radius > size/2-3 else color)
    def chunk(kind, content):
        return struct.pack('!I', len(content)) + kind + content + struct.pack('!I', zlib.crc32(kind + content) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', size, size, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')
    (directory / 'wheel-base.png').write_bytes(png)
    filters = []
    for i, option in enumerate(options):
        (directory / f'label-{i}.txt').write_text(option['label'].replace('\n', ' '), encoding='utf-8')
        angle = -math.pi/2 + i*math.pi/4
        x, y = size/2 + 215*math.cos(angle), size/2 + 215*math.sin(angle)
        filters.append(f'drawtext=font=Arial:textfile=label-{i}.txt:expansion=none:fontsize=22:fontcolor=black:x={x}-tw/2:y={y}-th/2')
    command(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', 'wheel-base.png',
             '-vf', ','.join(filters), '-frames:v', '1', 'wheel.png'], cwd=directory)


def aligned_words(alignment):
    chars, starts, ends = (alignment[k] for k in ('characters', 'character_start_times_seconds', 'character_end_times_seconds'))
    if len(chars) != len(starts) or len(chars) != len(ends):
        raise AppError('La alineación de voz está incompleta.')
    result, current = [], None
    for char, start, end in zip(chars, starts, ends):
        if not (isinstance(start, (int, float)) and isinstance(end, (int, float)) and 0 <= start <= end):
            raise AppError('La alineación de voz tiene tiempos inválidos.')
        if char.isspace():
            if current:
                result.append(current)
                current = None
        elif current:
            current['text'] += char
            current['end'] = end
        else:
            current = {'text': char, 'start': start, 'end': end}
    if current:
        result.append(current)
    if not result:
        raise AppError('No se recibieron palabras alineadas.')
    return result


def sound_effects(path, duration):
    """Whoosh, tick y ding originales, sin audios de terceros."""
    rate = 48000
    samples = array('f', [0]) * math.ceil(duration * rate)
    randomizer = random.Random(24)
    def tone(at, length, frequency, volume, noise=False):
        offset = round(at * rate)
        count = round(length * rate)
        for i in range(min(count, len(samples) - offset)):
            envelope = math.sin(math.pi * i / count) ** 2
            value = randomizer.uniform(-1, 1) if noise else math.sin(2 * math.pi * frequency * i / rate)
            samples[offset + i] += volume * envelope * value
    for index in range(1, int(duration / 2.2)):
        tone(index * 2.2, 0.10, 0, 0.035, noise=True)
    at = 3.0
    while at < 6.85:
        tone(at, 0.025, 1800, 0.08)
        at += 0.07 + (at - 3) * 0.07
    tone(7, 0.45, 1050, 0.10)
    pcm = array('h', (int(max(-1, min(1, value)) * 32767) for value in samples))
    import sys
    if sys.byteorder != 'little':
        pcm.byteswap()
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        stream.writeframes(pcm.tobytes())


def synthesize(config, store, job_id, http=None):
    with store.lock(job_id):
        job = store.get(job_id)
        approved(job)
        store.assert_editable(job_id)
        if job.get('audio'):
            raise AppError('Ya existe voz para esta versión. Se conserva para evitar cargos duplicados.')
        voice = config.require('ELEVENLABS_VOICE_ID')
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', voice):
            raise AppError('ELEVENLABS_VOICE_ID inválido.')
        response = (http or Http()).json('POST', f'https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps',
            headers={'xi-api-key': config.require('ELEVENLABS_API_KEY')}, data={
                'text': ' '.join(s['spoken'] for s in job['script']['segments']),
                'model_id': config.get('ELEVENLABS_MODEL', 'eleven_multilingual_v2')})
        try:
            words = aligned_words(response.get('normalized_alignment') or response['alignment'])
            audio = base64.b64decode(response['audio_base64'], validate=True)
        except (KeyError, ValueError, TypeError):
            raise AppError('La respuesta de voz está incompleta; no se marcó como generada.') from None
        directory = store.artifact_dir(job)
        path = directory / 'voice.mp3'
        path.write_bytes(audio)
        write_json(directory / 'words.json', words)
        job['audio'] = {'path': str(path), 'sha256': file_digest(path), 'script_hash': digest(job['script']),
                        'words': words, 'synthetic': True}
        store.save(job)
        return path


def render(config, store, job_id, *, background=None, audio=None, winner=0, demo=False):
    with store.lock(job_id):
        job = store.get(job_id)
        if not demo:
            if video_format(job) != 'roulette':
                raise AppError('render es la plantilla histórica de ruleta. El formato editorial se monta con el plan exportado y se incorpora con attach-video.')
            approved(job)
            store.assert_editable(job_id)
        elif not job.get('demo'):
            raise AppError('Solo un trabajo de demostración admite render sin aprobación.')
        validate_script(job['script'])
        if not 0 <= winner < 8:
            raise AppError('winner debe estar entre 0 y 7.')
        roulette = job['agents'].get('03-roulette-master')
        if not roulette:
            raise AppError('Primero ejecutá produce para preparar la ruleta y el copy.')
        validate_roulette(roulette)
        words = None
        if audio:
            source_audio = Path(audio).resolve()
        elif job.get('audio'):
            voice = job['audio']
            if voice['script_hash'] != digest(job['script']) or file_digest(voice['path']) != voice['sha256']:
                raise AppError('La voz cambió o pertenece a otra versión del guion.')
            source_audio, words = Path(voice['path']), voice['words']
        elif background:
            source_audio = Path(background).resolve()
        elif not demo:
            raise AppError('Indicá --audio, un --background con voz, o generá la voz con voice.')
        else:
            source_audio = None
        duration = sum(s['seconds'] for s in job['script']['segments'])
        if source_audio:
            data = probe(source_audio)
            if not any(s['codec_type'] == 'audio' for s in data.get('streams', [])):
                raise AppError('El archivo indicado no contiene audio.')
            duration = float(data['format']['duration'])
        if not 35 <= duration <= 55:
            raise AppError(f'La narración dura {duration:.1f}s; ajustala a 35–55s antes de renderizar.')
        directory = store.artifact_dir(job)
        ass_file(job, duration, directory / 'subs.ass', words=words, demo=demo)
        wheel_image(roulette['options'], directory)
        sound_effects(directory / 'sfx.wav', duration)
        args = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error']
        if background:
            args += ['-stream_loop', '-1', '-i', str(Path(background).resolve())]
            base = 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30'
        else:
            args += ['-f', 'lavfi', '-i', f'color=c=0x101014:s=1080x1920:r=30:d={duration}']
            base = "drawgrid=width=90:height=90:thickness=1:color=white@0.035,drawbox=x='0':y='0':w=18:h=1920:color=0xFFD500:t=fill"
        args += ['-loop', '1', '-framerate', '30', '-i', 'wheel.png']
        if source_audio:
            args += ['-i', str(source_audio)]
        else:
            args += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
        args += ['-i', 'sfx.wav']
        target_angle = -winner * math.pi/4
        graph = (f'[0:v]{base}[base];'
                 f"[1:v]format=rgba,rotate='if(lt(t,7),pow(7-t,3)*0.22+{target_angle},{target_angle})':c=none[wheel];"
                 "[base][wheel]overlay=220:490:enable='gte(t,3)*lt(t,8)',"
                 "drawbox=x=527:y=470:w=26:h=50:color=white:t=fill:enable='gte(t,3)*lt(t,8)',"
                 "ass=subs.ass[v];[2:a][3:a]amix=inputs=2:duration=first:normalize=0,"
                 "loudnorm=I=-14:TP=-2:LRA=11,aresample=48000,alimiter=limit=0.7:level=false:latency=true[a]")
        args += ['-filter_complex', graph, '-map', '[v]', '-map', '[a]', '-t', str(duration),
                 '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-threads', '2',
                 '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', 'render-tmp.mp4']
        command(args, cwd=directory)
        temporary = directory / 'render-tmp.mp4'
        info = verify_video(temporary)
        output = directory / 'reel.mp4'
        temporary.replace(output)
        job['video'] = {'path': str(output), 'sha256': file_digest(output), 'info': info,
                        'script_hash': digest(job['script']), 'subtitle_timing': 'alineado' if words else 'estimado',
                        'winner': roulette['options'][winner]['label'], 'synthetic_voice': bool(job.get('audio', {}).get('synthetic')) and not audio}
        job['state'] = 'demo' if demo else 'ready'
        store.save(job)
        command(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-ss', '8', '-i', str(output),
                 '-frames:v', '1', str(directory / 'preview.jpg')])
        write_json(directory / 'verification.json', info)
        return output


def attach(store, job_id, source, synthetic_voice=False):
    with store.lock(job_id):
        job = store.get(job_id)
        approved(job)
        store.assert_editable(job_id)
        info = verify_video(source)
        target = store.artifact_dir(job) / 'reel.mp4'
        if Path(source).resolve() != target.resolve():
            shutil.copyfile(source, target)
        job['video'] = {'path': str(target), 'sha256': file_digest(target), 'script_hash': digest(job['script']),
                        'info': info, 'synthetic_voice': synthetic_voice, 'subtitle_timing': 'video aportado'}
        job['state'] = 'ready'
        store.save(job)
        return target
