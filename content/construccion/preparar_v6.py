from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v6';D.mkdir(parents=True,exist_ok=True)
(ROOT/'entregas/construccion-v6').mkdir(parents=True,exist_ok=True)
P=json.loads((ROOT/'runtime/construccion-v5/params.json').read_text(encoding='utf-8'))
(D/'params.json').write_text(json.dumps(P,ensure_ascii=False,indent=2),encoding='utf-8')
for f in ['subs.srt','transcripcion-editada.txt','revision-cortes.json','revision-voz-identica.json','audio-procedencia.json']:
 shutil.copyfile(ROOT/'runtime/construccion-v5'/f,D/f)
a=json.loads((ROOT/'content/construccion/assets-v6/procedencia.json').read_text(encoding='utf-8'))
for item in a['assets']:shutil.copyfile(item['source'],ROOT/'content/construccion/assets-v6'/item['file'])
print(json.dumps({'duration':P['duration'],'shots':len(P['shots']),'transitions':len(P['transitions']),'audio':'AAC de V5 sin recodificar'},ensure_ascii=False))
