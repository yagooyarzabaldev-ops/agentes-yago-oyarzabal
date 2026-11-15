"""Composite the warm editorial V6 and preserve V5's audio payload exactly."""
from pathlib import Path
import hashlib,json,shutil,subprocess

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'runtime/construccion-v6'
E=ROOT/'entregas/construccion-v6'
E.mkdir(parents=True,exist_ok=True)
P=json.loads((D/'params.json').read_text(encoding='utf-8'))
V5=ROOT/'entregas/construccion-v5/Sistemas_con_IA_Yago_v5.mp4'
OUT=E/'Sistemas_con_IA_Yago_v6.mp4'

def run(args):
    r=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if r.returncode:raise RuntimeError(r.stderr[-5000:])
    return r

def enabled(shots):
    return '+'.join(f'gte(t,{s["start"]:.8f})*lt(t,{s["end"]:.8f})' for s in shots) or '0'

close=enabled([s for s in P['shots'] if s['view']=='camera' and s['camera_mode']=='close'])
phone=enabled([s for s in P['shots'] if s['view']=='phone'])
fc=(
    '[0:v]tpad=stop_mode=clone:stop_duration=2.3,split=3[w][c][p];'
    '[w]crop=1080:1138:0:250,scale=972:1024,pad=1080:1920:54:300:color=0xfff0d2[wide];'
    '[c]crop=940:1090:70:268,scale=972:1128,crop=972:1024:0:32,pad=1080:1920:54:300:color=0xfff0d2[close];'
    '[p]crop=640:1138:220:250,scale=420:746,pad=1080:1920:310:590:color=0x292123[phone];'
    f"[wide][close]overlay=0:0:enable='{close}'[cam];"
    f"[cam][phone]overlay=0:0:enable='{phone}'[base];"
    '[base][1:v]overlay=0:0:format=auto,format=yuv420p[v]'
)
print('Composing V6 with original microphone audio and V5 music...',flush=True)
run(['ffmpeg','-hide_banner','-loglevel','error','-filter_complex_threads','3',
     '-i',ROOT/'runtime/construccion-v3/camara.mp4','-i',D/'graficos.mov','-i',V5,
     '-filter_complex',fc,'-map','[v]','-map','2:a:0','-t',P['duration'],'-r','30',
     '-c:v','h264_qsv','-global_quality','18','-preset','medium','-c:a','copy',
     '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart','-y',OUT])
plan={'input':str(ROOT/'runtime/construccion-v3/camara.mp4'),'output':str(OUT),
      'profile':'1080p','fps':30,'segments':[{'start':0,'end':P['duration']}],
      'audio':{'lufs':-14,'true_peak':-2.3},
      'composition':{'camera_audio':False,'microphone':P['source_audio'],'shots':len(P['shots']),
                     'template':'content/construccion/escena_v6.html','phone_original_video':True,
                     'transitions':len(P['transitions']),'theme':'warm editorial paper collage',
                     'audio_copied_without_reencoding_from':str(V5)}}
(D/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
for source,target in [('subs.srt','subtitulos.srt'),('transcripcion-editada.txt','transcripcion-editada.txt'),
                      ('audio-procedencia.json','audio-procedencia.json'),('revision-layout.json','revision-layout.json'),
                      ('revision-variedad.json','revision-variedad.json'),
                      ('revision-cortes.json','revision-cortes.json'),('revision-voz-identica.json','revision-voz-identica.json')]:
    shutil.copyfile(D/source,E/target)

def audio_hash(p):
    r=subprocess.run(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-c:a','copy','-f','adts','-'],capture_output=True,check=True)
    return hashlib.sha256(r.stdout).hexdigest()
original,current=audio_hash(V5),audio_hash(OUT)
report={'ok':original==current,'source':str(V5),'method':'SHA256 of demuxed AAC ADTS bytes',
        'v5_sha256':original,'v6_sha256':current,'reencoded':False}
(E/'revision-audio-identico.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['ok'],'Audio track differs unexpectedly'
run(['ffmpeg','-v','error','-ss','0.8','-i',OUT,'-frames:v','1','-q:v','2','-y',E/'portada.jpg'])
run(['ffmpeg','-v','error','-i',OUT,'-t','17.1','-vf','scale=540:960','-c:v','h264_qsv',
     '-global_quality','20','-c:a','aac','-b:a','160k','-movflags','+faststart','-y',E/'Avance_17s.mp4'])
shutil.copyfile(ROOT/'content/construccion/copy-publicacion-v6.md',E/'copy-publicacion.md')
shutil.copyfile(ROOT/'content/construccion/assets-v6/procedencia.json',E/'imagenes-procedencia.json')
print(json.dumps({'output':str(OUT),'duration':P['duration'],'audio_identical_to_v5':report['ok'],
                  'size_bytes':OUT.stat().st_size}),flush=True)
