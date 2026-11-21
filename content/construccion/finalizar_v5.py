from pathlib import Path
import json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v5';E=ROOT/'entregas/construccion-v5';E.mkdir(parents=True,exist_ok=True)
P=json.loads((D/'params.json').read_text(encoding='utf-8'));OUT=E/'Sistemas_con_IA_Yago_v5.mp4'
def run(args):
 r=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace')
 if r.returncode:raise RuntimeError(r.stderr[-5000:])
 return r
def enabled(shots):return '+'.join(f'gte(t,{s["start"]:.8f})*lt(t,{s["end"]:.8f})' for s in shots) or '0'
close=enabled([s for s in P['shots'] if s['view']=='camera' and s['camera_mode']=='close'])
phone=enabled([s for s in P['shots'] if s['view']=='phone'])
fc=f'[0:v]tpad=stop_mode=clone:stop_duration=2.3,split=3[wide][c][p];[c]crop=960:1706:60:90,scale=1080:1920[close];[p]crop=640:1138:220:250,scale=420:746,pad=1080:1920:310:590:color=0x091326[phone];[wide][close]overlay=0:0:enable=\'{close}\'[cam];[cam][phone]overlay=0:0:enable=\'{phone}\'[base];[base][1:v]overlay=0:0:format=auto,format=yuv420p[v]'
run(['ffmpeg','-hide_banner','-loglevel','error','-filter_complex_threads','3','-i',ROOT/'runtime/construccion-v3/camara.mp4','-i',D/'graficos.mov','-i',D/'master.wav','-filter_complex',fc,'-map','[v]','-map','2:a','-t',P['duration'],'-r','30','-c:v','h264_qsv','-global_quality','18','-preset','medium','-c:a','aac','-b:a','256k','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart','-y',OUT])
plan={'input':str(ROOT/'runtime/construccion-v3/camara.mp4'),'output':str(OUT),'profile':'1080p','fps':30,'segments':[{'start':0,'end':P['duration']}],'audio':{'lufs':-14,'true_peak':-2.3},'composition':{'camera_audio':False,'microphone':P['source_audio'],'shots':len(P['shots']),'template':'content/construccion/escena_v5.html','phone_original_video':True,'transitions':len(P['transitions'])}}
(D/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
for source,target in [('subs.srt','subtitulos.srt'),('transcripcion-editada.txt','transcripcion-editada.txt'),('audio-procedencia.json','audio-procedencia.json'),('revision-variedad.json','revision-variedad.json'),('revision-layout.json','revision-layout.json'),('revision-cortes.json','revision-cortes.json'),('revision-voz-identica.json','revision-voz-identica.json')]:shutil.copyfile(D/source,E/target)
run(['ffmpeg','-v','error','-ss','0.8','-i',OUT,'-frames:v','1','-q:v','2','-y',E/'portada.jpg'])
run(['ffmpeg','-v','error','-i',OUT,'-t','17.1','-vf','scale=540:960','-c:v','h264_qsv','-global_quality','20','-c:a','aac','-b:a','160k','-movflags','+faststart','-y',E/'Avance_17s.mp4'])
shutil.copyfile(ROOT/'content/construccion/copy-publicacion-v5.md',E/'copy-publicacion.md')
print(json.dumps({'output':str(OUT),'duration':P['duration'],'size_bytes':OUT.stat().st_size}),flush=True)
