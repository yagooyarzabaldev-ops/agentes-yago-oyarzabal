from pathlib import Path
import hashlib,json,shutil,subprocess

ROOT=Path(__file__).resolve().parents[2]; D=ROOT/'runtime/construccion-v4'; E=ROOT/'entregas/construccion-v4'
P=json.loads((D/'params.json').read_text(encoding='utf-8'))
V3=ROOT/'entregas/construccion-v3/IA_sin_tantas_vueltas_Yago_v3.mp4'
OUT=E/'IA_sin_tantas_vueltas_Yago_v4.mp4'
def run(args):
 r=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace')
 if r.returncode:raise RuntimeError(r.stderr[-4500:])
 return r
close=[s for s in P['shots'] if s['view']=='camera' and s['camera_mode']=='close']
enable='+'.join(f'gte(t,{s["start"]:.8f})*lt(t,{s["end"]:.8f})' for s in close)
fc=f'[0:v]tpad=stop_mode=clone:stop_duration=2.3,split=2[wide][c];[c]crop=960:1706:60:90,scale=1080:1920[close];[wide][close]overlay=0:0:enable=\'{enable}\'[cam];[cam][1:v]overlay=0:0:format=auto,format=yuv420p[v]'
run(['ffmpeg','-hide_banner','-loglevel','error','-filter_complex_threads','3','-i',ROOT/'runtime/construccion-v3/camara.mp4','-i',D/'graficos.mov','-i',V3,'-filter_complex',fc,'-map','[v]','-map','2:a:0','-t',P['duration'],'-r','30','-c:v','h264_qsv','-global_quality','18','-preset','medium','-c:a','copy','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart','-y',OUT])
plan={'input':str(ROOT/'runtime/construccion-v3/camara.mp4'),'output':str(OUT),'profile':'1080p','fps':30,'segments':[{'start':0,'end':P['duration']}],'audio':{'lufs':-14,'true_peak':-2.3},'composition':{'camera_audio':False,'microphone':P['source_audio'],'shots':len(P['shots']),'template':'content/construccion/escena_v4.html'}}
(D/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
for source,target in [('subs.srt','subtitulos.srt'),('transcripcion-editada.txt','transcripcion-editada.txt'),('audio-procedencia.json','audio-procedencia.json'),('revision-variedad.json','revision-variedad.json'),('revision-layout.json','revision-layout.json'),('revision-cortes.json','revision-cortes.json')]:
 shutil.copyfile(D/source,E/target)
# Confirm V3's cleaned voice/music AAC payload is retained exactly.
def audio_hash(p):
 r=subprocess.run(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-c:a','copy','-f','adts','-'],capture_output=True,check=True)
 return hashlib.sha256(r.stdout).hexdigest()
original,current=audio_hash(V3),audio_hash(OUT)
report={'ok':original==current,'source':str(V3),'method':'SHA256 of demuxed AAC ADTS bytes','v3_sha256':original,'v4_sha256':current,'reencoded':False}
(E/'revision-audio-identico.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['ok'],'Audio track differs unexpectedly'
run(['ffmpeg','-hide_banner','-loglevel','error','-ss','0.8','-i',OUT,'-frames:v','1','-q:v','2','-y',E/'portada.jpg'])
run(['ffmpeg','-hide_banner','-loglevel','error','-i',OUT,'-t','17.1','-vf','scale=540:960','-c:v','h264_qsv','-global_quality','20','-c:a','aac','-b:a','160k','-movflags','+faststart','-y',E/'Avance_17s.mp4'])
shutil.copyfile(ROOT/'content/construccion/copy-publicacion-v4.md',E/'copy-publicacion.md')
print(json.dumps({'output':str(OUT),'audio_identical_to_v3':report['ok'],'size_bytes':OUT.stat().st_size}),flush=True)
