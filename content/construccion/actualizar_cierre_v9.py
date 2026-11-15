"""Replace only the 54 outro frames in the already rendered ProRes overlay."""
from pathlib import Path
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'runtime/construccion-v9'
manifest = D / 'concat-cierre.txt'
manifest.write_text("file 'graficos.mov'\noutpoint 65.3\nfile 'cierre.mov'\n", encoding='utf-8')
revised = D / 'graficos-revisados.mov'
subprocess.run(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(manifest), '-map', '0:v', '-c', 'copy', '-y', str(revised)], check=True)
probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=nb_frames,duration,width,height,pix_fmt', '-of', 'json', str(revised)], text=True))['streams'][0]
assert int(probe['nb_frames']) == 2013, probe
assert abs(float(probe['duration']) - 67.1) < 0.001, probe
assert (probe['width'], probe['height']) == (1080, 1920), probe
os.replace(revised, D / 'graficos.mov')
(D / 'revision-cierre.json').write_text(json.dumps({'ok': True, 'replaced_from': 65.3, 'outro_frames': 54, 'stream': probe}, indent=2), encoding='utf-8')
print(json.dumps(probe))
