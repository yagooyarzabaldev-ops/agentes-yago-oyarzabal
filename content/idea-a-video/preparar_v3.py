"""Replace the rejected orange fountain-pen artwork in both appearances."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
B=Path(__file__).resolve().parent
D=ROOT/'runtime/idea-a-video-v3';E=ROOT/'entregas/idea-a-video-v3'
D.mkdir(parents=True,exist_ok=True);E.mkdir(parents=True,exist_ok=True)
P=json.loads((B/'params-v2.json').read_text(encoding='utf-8'))
P['assets'].pop('script')
P['assets']['script_glass']='assets/script-glass.png'
changed=[]
for shot in P['shots']:
    if shot['image_id']=='script':
        shot['image_id']='script_glass';changed.append([shot['start'],shot['end']])
assert changed==[[18,20],[24,26]]
assert len(P['assets'])==14
assert all(shot['image_id']!='script' for shot in P['shots'])
P['version']=3
hashes={key:hashlib.sha256((B/file).read_bytes()).hexdigest() for key,file in P['assets'].items()}
assert len(set(hashes.values()))==14
(B/'params-v3.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(D/'params.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copy2(ROOT/'runtime/idea-a-video-v2/plan.json',D/'plan.json')
for file in ['House_Idea_a_Video.wav','House_Idea_a_Video.m4a','procedencia-instrumental.json','subtitulos-guia.srt','guion-para-grabar.txt']:
    shutil.copy2(ROOT/'entregas/idea-a-video-v2'/file,E/file)
production=json.loads((B/'produccion-v2.json').read_text(encoding='utf-8'))
production.update(status='visual_preview_in_production_waiting_for_recording',version=3,
                  new_images_this_revision=1,image_asset_sha256=hashes,
                  feedback='Replace the rejected fountain pen on orange background with a cinematic glass manuscript scene.',
                  replaced_image='assets/script.png',replacement_image='assets/script-glass.png',changed_ranges=changed)
production.pop('preview_file',None)
(B/'produccion-v3.json').write_text(json.dumps(production,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'duration':P['duration'],'distinct_images':14,'replaced_ranges':changed}))
