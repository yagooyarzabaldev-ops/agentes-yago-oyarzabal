"""V2: 14 actual image assets, distinct from native motion graphics."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
B=Path(__file__).resolve().parent
D=ROOT/'runtime/idea-a-video-v2';E=ROOT/'entregas/idea-a-video-v2'
D.mkdir(parents=True,exist_ok=True);E.mkdir(parents=True,exist_ok=True)
P=json.loads((B/'params.json').read_text(encoding='utf-8'))
primary={0:'idea',2:'neural',3:'audience',5:'brief',7:'team',9:'script',11:'review',
         14:'direction',15:'storyboard',18:'microphone',21:'edit',23:'music',27:'quality',32:'export'}
hybrids={12:'script',13:'review',17:'team',20:'microphone',24:'storyboard',25:'audience',26:'edit',28:'neural',30:'quality'}
P['assets']={key:f'assets/{key}.png' for key in primary.values()}
asset_ids=set(primary.values())
assert len(asset_ids)==14 and len(asset_ids)>=10
hashes={key:hashlib.sha256((B/P['assets'][key]).read_bytes()).hexdigest() for key in asset_ids}
assert len(set(hashes.values()))==14,'Repeated image bytes must not count as new assets'
for s in P['shots']:
    i=s['index'];key=primary.get(i,hybrids.get(i))
    s['image_id']=key or ''
    s['asset_type']='image' if key else 'native'
    s['image_mode']='hero' if i in primary else 'hybrid' if i in hybrids else 'none'
    s['image_motion']=['push','truck','pull','diagonal','orbit'][i%5]
P['version']=2
P['minimum_distinct_images']=10
P['actual_distinct_images']=len(asset_ids)
P['image_seconds']=sum(s['end']-s['start'] for s in P['shots'] if s['image_id'])
P['style']='infinite-process-editorial-v3'
(B/'params-v2.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(D/'params.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(D/'plan.json').write_text(json.dumps({'profile':'1080p','fps':30,'audio':{'lufs':-17},'scope':'instrumental preview'},indent=2),encoding='utf-8')
for file in ['House_Idea_a_Video.wav','House_Idea_a_Video.m4a','procedencia-instrumental.json','subtitulos-guia.srt','guion-para-grabar.txt']:
    shutil.copy2(ROOT/'entregas/idea-a-video-v1'/file,E/file)
production=json.loads((B/'produccion.json').read_text(encoding='utf-8'))
production.update(status='visual_preview_in_production_waiting_for_recording',style=P['style'],version=2,
                  new_images=14,new_images_this_revision=10,distinct_images=14,image_seconds=P['image_seconds'],
                  image_fraction=P['image_seconds']/P['duration'],minimum_distinct_images=10,
                  image_asset_sha256=hashes,
                  feedback='Minimum 10 distinct images per video, guided by the supplied references. Native graphics do not count.')
production.pop('preview_file',None)
(B/'produccion-v2.json').write_text(json.dumps(production,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'duration':P['duration'],'distinct_images':len(asset_ids),'image_seconds':P['image_seconds'],'scenes':len(P['shots'])}))
