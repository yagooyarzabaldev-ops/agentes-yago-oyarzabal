"""Build an editable 70s animatic. Voice/camera are deliberately pending a new take."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B = Path(__file__).resolve().parent
D = ROOT / 'runtime/idea-a-video-v1'
E = ROOT / 'entregas/idea-a-video-v1'
for folder in (D, E):
    folder.mkdir(parents=True, exist_ok=True)

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

text = (B/'guion-propuesto.md').read_text(encoding='utf-8').split('## Texto para decir\n\n')[1].split('\n## Dirección')[0].strip()
paragraphs = text.split('\n\n')
durations = [6,8,8,5,8,8,5,8,6,5,3]
assert len(paragraphs) == len(durations) and sum(durations) == 70
(B/'guion-grabacion.txt').write_text(text+'\n', encoding='utf-8')
(E/'guion-para-grabar.txt').write_text(text+'\n', encoding='utf-8')
words = []; cursor = 0
for paragraph, duration in zip(paragraphs, durations):
    tokens = paragraph.split(); weights = [max(2, len(t)) + (2 if t[-1] in '.,;:?!' else 0) for t in tokens]
    scale = duration / sum(weights)
    for token, weight in zip(tokens, weights):
        words.append({'w': token, 'start': round(cursor, 4), 'end': round(cursor+weight*scale, 4)})
        cursor += weight*scale
captions = [words[i:i+5] for i in range(0, len(words), 5)]
definitions = [
 ('idea','DE UNA IDEA','A UN VIDEO.','Una idea toma forma','amber'),
 ('message','TODO EMPIEZA','CON ESTO.','Un mensaje concreto','coral'),
 ('spark','LA IDEA','SE PONE EN MARCHA.','Del mensaje al proceso','lime'),
 ('audience','¿A QUIÉN','LE HABLAMOS?','Definir la audiencia','emerald'),
 ('target','¿QUÉ QUERÉS','QUE SE LLEVEN?','Elegir el objetivo','violet'),
 ('intent','UNA IDEA.','UNA INTENCIÓN.','Claridad antes de producir','amber'),
 ('brief','EL CONTEXTO','QUEDA CLARO.','Brief de la pieza','coral'),
 ('orchestrator','CADA AGENTE','TIENE SU PARTE.','La gerencia coordina','emerald'),
 ('approaches','BUSCAR','EL ENFOQUE.','Elegir cómo contarlo','lime'),
 ('script','LA IDEA','YA TIENE GUION.','Ordenar el relato','violet'),
 ('hook','LOS PRIMEROS','SEGUNDOS IMPORTAN.','Encontrar el gancho','amber'),
 ('review','LO LEO.','LO HAGO MÍO.','Revisión de contenido','coral'),
 ('revision','SI NO ENCAJA,','LO CAMBIAMOS.','Volver sobre el guion','violet'),
 ('approved','UNA DIRECCIÓN','PARA PRODUCIR.','Versión revisada','emerald'),
 ('direction','DE LAS FRASES','A LAS ESCENAS.','Dirección visual','violet'),
 ('storyboard','CADA IDEA','TIENE SU PLANO.','Armar el storyboard','amber'),
 ('typography','IMÁGENES.','TEXTO. MOVIMIENTO.','Diseñar la atención','coral'),
 ('motion','LOS ELEMENTOS','SE CONECTAN.','Animar el proceso','emerald'),
 ('mic','MI VOZ.','MI FORMA DE CONTAR.','Grabación real','amber'),
 ('cut','CORTAR EL ERROR.','CONSERVAR LA IDEA.','Limpiar repeticiones','coral'),
 ('sync','VOZ Y CÁMARA,','EN EL MISMO TIEMPO.','Sincronizar las tomas','lime'),
 ('edit','EL RELATO','EN LA LÍNEA DE TIEMPO.','Montaje de la pieza','coral'),
 ('wave','LA VOZ','AL FRENTE.','Mezclar con espacio','violet'),
 ('music','HOUSE SUTIL.','SIN LÍNEA DE BAJO.','Música que acompaña','emerald'),
 ('clarity','¿SE ENTIENDE','LA IDEA?','Revisar el mensaje','amber'),
 ('text','¿SE LEE BIEN','EN EL CELULAR?','Comprobar los textos','lime'),
 ('alignment','QUE TODO','LLEGUE A TIEMPO.','Verificar la sincronía','violet'),
 ('qa','VER. ESCUCHAR.','CORREGIR.','Control del resultado','emerald'),
 ('control','ACÁ SIGO','DECIDIENDO YO.','El criterio es humano','coral'),
 ('human','QUÉ SIRVE.','QUÉ SE CAMBIA.','Revisión humana','amber'),
 ('publishgate','QUÉ ESTÁ LISTO','PARA PUBLICAR.','Decisión de publicación','emerald'),
 ('path','LA IDEA','YA TIENE RECORRIDO.','Una etapa conecta con otra','violet'),
 ('export','UN VIDEO','PARA REVISAR.','Export de la pieza','amber'),
 ('result','ASÍ SE CONSTRUYE','EL RESULTADO.','Guion, producción, revisión','coral'),
 ('cta','¿QUÉ IDEA','HACEMOS VIDEO?','El próximo puede ser el tuyo','emerald'),
]
palette = json.loads((ROOT/'config/video-style.json').read_text(encoding='utf-8'))['visuals']['palette']
shots = [dict(start=i*2,end=(i+1)*2,view=view,title=[a,b],note=note,palette=color,accent=palette[color],index=i,
              mode=['iris','fold','slide','match','slit','trace','cut'][i%7])
         for i,(view,a,b,note,color) in enumerate(definitions)]
camera = [[0,6],[10,16],[22,28],[36,40],[48,52],[56,62],[68,70]]
params = {'duration':70,'fps':30,'bpm':122,'camera_available':False,'preview':True,
          'shots':shots,'captions':captions,'words':words,'camera_ranges':camera,'bw_ranges':[[56,60]],
          'assets':{key:f'assets/{key}.png' for key in ['idea','direction','edit','export']},
          'timing_source':'estimated_from_proposed_script; replace after real recording'}
write(B/'params.json',params);write(D/'params.json',params)
def stamp(value):
    n=round(value*1000);return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'
(E/'subtitulos-guia.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(cap[0]["start"])} --> {stamp(cap[-1]["end"])}\n'+ ' '.join(w['w'] for w in cap) for i,cap in enumerate(captions))+'\n',encoding='utf-8')
write(B/'produccion.json',{'status':'visual_preview_in_production_waiting_for_recording','execution_mode':'assistant-guided production; no separate API agent calls',
 'style':'infinite-process-editorial-v2','duration':70,'script_words':len(words),'scenes':len(shots),'new_images':4,
 'planned_camera_seconds':sum(b-a for a,b in camera),'planned_camera_fraction':sum(b-a for a,b in camera)/70,
 'preview_camera_seconds':0,'voice':'new recording chosen by user; not yet supplied','script_review':'prepared for recording; exact timing pending',
 'stages':['brief','guion','dirección visual','motion','música','previsualización','nueva toma','sincronía y montaje','revisión final'],
 'evidence':['marketing/agents.py: planning stages and saved state','production/ESTILO-Y-FLUJO.md: production tools and review'],
 'pending':['new microphone/camera take','word alignment','final camera composite','voice ducking and listening review'],
 'publication_authorized':False})
print(json.dumps({'duration':70,'words':len(words),'shots':len(shots),'planned_camera_seconds':sum(b-a for a,b in camera)}))
