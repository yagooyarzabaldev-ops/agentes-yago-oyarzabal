"""Rebuild V7 timing and inventory without modifying previous deliveries."""
from collections import Counter
from pathlib import Path
import json, shutil

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'runtime/construccion-v7'
D.mkdir(parents=True, exist_ok=True)
(ROOT / 'entregas/construccion-v7').mkdir(parents=True, exist_ok=True)
P = json.loads((ROOT / 'runtime/construccion-v6/params.json').read_text(encoding='utf-8'))
modes = ['depth', 'diagonal', 'iris', 'slats', 'page']
for tr in P['transitions']:
    tr['mode'] = modes[tr['index'] % len(modes)]
(D / 'params.json').write_text(json.dumps(P, ensure_ascii=False, indent=2), encoding='utf-8')
for name in ['subs.srt', 'transcripcion-editada.txt', 'revision-cortes.json', 'revision-voz-identica.json', 'audio-procedencia.json']:
    shutil.copyfile(ROOT / 'runtime/construccion-v6' / name, D / name)

mapping = {'system': 'neural', 'manual': 'manual_ref', 'layers': 'chip_ref',
           'context': 'hub_ref', 'launch': 'launch', 'orchestrate': 'studio_ref',
           'unify': 'flow_ref', 'time': 'time'}
assets_dir = ROOT / 'content/construccion/assets-v7'
provenance = json.loads((assets_dir / 'procedencia.json').read_text(encoding='utf-8'))
selected = [item for item in provenance['assets'] if item['used_in_v7']]
assert len(selected) == 8 and set(mapping.values()) == {a['id'] for a in selected}
for asset in selected:
    target = assets_dir / asset['file']
    if not target.exists():
        shutil.copyfile(asset['source'], target)
scenes = Counter(s['view'] for s in P['shots'] if s['view'] != 'camera')
assert len(scenes) == 13 and all(count == 1 for count in scenes.values())
report = {
    'duration': P['duration'], 'shots': len(P['shots']), 'transitions': len(P['transitions']),
    'camera_shots': sum(s['view'] == 'camera' for s in P['shots']),
    'graphic_scenes': dict(scenes), 'unique_graphic_scenes': True,
    'new_images_count': len(selected), 'scene_image_mapping': mapping,
    'native_graphic_scenes': [s for s in scenes if s not in mapping],
    'palette': ['orange', 'cream', 'charcoal', 'violet', 'dark emerald', 'amber', 'coral'],
    'transition_modes': dict(Counter(t['mode'] for t in P['transitions'])),
    'voice_and_music': 'AAC copied from V6 without reencoding',
    'reference_library': 'content/referencias/diseno-ia/',
    'asset_provenance': 'content/construccion/assets-v7/procedencia.json',
    'animation': 'Perspective card projection, layered light paths and orbits, image camera movement, animated type and transitions. Raster illustrations are still images.'
}
(D / 'revision-variedad.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
