"""Approved editorial profile and deterministic checks for production shot plans."""
from __future__ import annotations

import json
import math
from collections import Counter

from .config import AppError
from .store import digest


def load_style(root):
    return json.loads((root / 'config/video-style.json').read_text(encoding='utf-8-sig'))


def video_format(job):
    # Existing roulette jobs retain their format. New jobs explicitly use editorial.
    return job.get('video_format', 'roulette' if '03-roulette-master' in job.get('agents', {}) else 'editorial')


def pin_style(job, root):
    if 'style' not in job:
        profile = load_style(root)
        job['style'] = {'sha256': digest(profile), 'profile': profile}
    if digest(job['style']['profile']) != job['style']['sha256']:
        raise AppError('El perfil de estilo del trabajo cambió sin versionarse.')
    return job['style']['profile']


def check_shots(plan, duration, style):
    """Validate a plan, never claim to have reviewed pixels or listened to a render."""
    shots = plan['shots']
    if not shots:
        raise AppError('El director visual debe entregar un plan de escenas completo.')
    cursor = camera_seconds = 0.0
    ids, palettes, motions, transitions = [], set(), set(), set()
    image_ids = set()
    minimum_images = style['visuals'].get('minimum_distinct_images')
    previous = None
    for shot in shots:
        start, end = shot['start'], shot['end']
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in (start, end)):
            raise AppError('La escena contiene tiempos inválidos.')
        if abs(start - cursor) > 0.04 or not 0.5 <= end - start <= style['visuals']['max_static_seconds']:
            raise AppError('Las escenas deben cubrir la línea de tiempo sin huecos ni solapes y durar hasta 3 segundos.')
        if any(not shot[key].strip() for key in ('visual_id', 'idea', 'visual', 'animation')):
            raise AppError('Cada escena necesita una idea, un recurso y una animación concretos.')
        if minimum_images is not None:
            kind, image_id = shot.get('asset_type'), shot.get('image_id')
            if kind not in ('image', 'native') or not isinstance(image_id, str):
                raise AppError('Cada escena debe declarar asset_type e image_id del recurso original.')
            image_id = image_id.strip().casefold()
            if kind == 'image':
                if not image_id:
                    raise AppError('Las escenas con imagen necesitan un image_id estable del origen.')
                image_ids.add(image_id)
            elif image_id:
                raise AppError('El motion nativo no cuenta como imagen: image_id debe estar vacío.')
        if previous == shot['visual_id']:
            raise AppError('No repetir el mismo recurso en escenas consecutivas.')
        previous = shot['visual_id']
        ids.append(previous)
        palettes.add(shot['palette'])
        motions.add(shot['motion'])
        transitions.add(shot['transition'])
        if shot['layout'] != 'full':
            camera_seconds += end - start
        if shot['layout'] == 'split_bw' and not shot['aside_reason'].strip():
            raise AppError('El blanco y negro necesita una aclaración real que lo justifique.')
        cursor = end
    if abs(cursor - duration) > 0.05:
        raise AppError('El plan de escenas no cubre la duración del guion aprobado.')
    fraction = camera_seconds / duration
    low, high = style['camera']['fraction_range']
    if not low <= fraction <= high:
        raise AppError('La cámara debe ocupar entre el 40% y el 55% del plan.')
    unique = len(set(ids)) / len(ids)
    v = style['visuals']
    if minimum_images is not None and len(image_ids) < minimum_images:
        raise AppError(f'El plan necesita al menos {minimum_images} imágenes de origen distintas; declara {len(image_ids)}. Recortes, zoom, color y motion nativo no suman imágenes nuevas.')
    if unique < v['minimum_unique_visual_fraction'] or max(Counter(ids).values()) > 2:
        raise AppError('Falta variedad: al menos 80% de recursos únicos y ninguno más de dos veces.')
    if len(palettes) < v['minimum_palette_families'] or len(motions) < v['minimum_motion_families'] or len(transitions) < v['minimum_transition_families']:
        raise AppError('El plan necesita al menos tres familias de color, cuatro movimientos y cuatro transiciones.')
    return {'scope': 'plan_only', 'shots': len(shots), 'camera_fraction': fraction,
            'unique_visual_fraction': unique, 'palette_families': len(palettes),
            'motion_families': len(motions), 'transition_families': len(transitions),
            'planned_distinct_images': len(image_ids) if minimum_images is not None else None,
            'image_asset_review': 'pending',
            'export_review': 'pending', 'listening_review': 'pending'}
