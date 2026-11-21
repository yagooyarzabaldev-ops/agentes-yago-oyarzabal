"""Export alternating camera and full-screen V9 with the minimal house mix."""
from pathlib import Path
import json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v9';E=ROOT/'entregas/construccion-v9'
P=json.loads((D/'params.json').read_text(encoding='utf-8'));OUT=E/'Sistemas_con_IA_Yago_v9.mp4'
def run(args):
 r=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace')
 if r.returncode:raise RuntimeError(r.stderr[-5000:])
 return r
fc='[0:v]tpad=stop_mode=clone:stop_duration=2,pad=1080:1920:0:0:color=black[base];[base][1:v]overlay=0:0:format=auto,format=yuv420p[v]'
print('Composing V9 camera blocks and full-screen visuals with original microphone and minimal house...',flush=True)
run(['ffmpeg','-hide_banner','-loglevel','error','-filter_complex_threads','3','-i',D/'camara.mp4','-i',D/'graficos.mov','-i',D/'master.wav','-filter_complex',fc,'-map','[v]','-map','2:a:0','-t',P['duration'],'-r','30','-c:v','h264_qsv','-global_quality','18','-preset','medium','-c:a','aac','-b:a','256k','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart','-y',OUT])
plan={'input':str(D/'camara.mp4'),'output':str(OUT),'profile':'1080p','fps':30,'segments':[{'start':0,'end':P['duration']}],'audio':{'lufs':-14,'true_peak':-2.3},'composition':{'layout':'alternating split-screen camera and full-screen visuals','split_y':960,'camera_visible_seconds':P['camera_visible_seconds'],'camera_ranges':P['camera_ranges'],'camera_audio':False,'microphone':P['source_audio'],'template':'content/construccion/escena_v9.html','image_count':len(P['assets']),'scenes':len(P['shots']),'music':'original minimal house, 120 BPM'}}
(D/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
for source,target in [('subs.srt','subtitulos.srt'),('transcripcion-editada.txt','transcripcion-editada.txt'),('audio-procedencia.json','audio-procedencia.json'),('revision-layout.json','revision-layout.json'),('revision-variedad.json','revision-variedad.json'),('revision-cortes.json','revision-cortes.json'),('revision-voz-identica.json','revision-voz-identica.json'),('revision-sincronizacion.json','revision-sincronizacion.json'),('revision-camara-identica.json','revision-camara-identica.json')]:shutil.copyfile(D/source,E/target)
shutil.copyfile(D/'revision-visibilidad.json',E/'revision-visibilidad.json')
run(['ffmpeg','-v','error','-ss','5.8','-i',OUT,'-frames:v','1','-q:v','2','-y',E/'portada.jpg'])
run(['ffmpeg','-v','error','-i',OUT,'-t','17.1','-vf','scale=540:960','-c:v','h264_qsv','-global_quality','20','-c:a','aac','-b:a','160k','-movflags','+faststart','-y',E/'Avance_17s.mp4'])
shutil.copyfile(ROOT/'content/construccion/copy-publicacion-v9.md',E/'copy-publicacion.md')
shutil.copyfile(ROOT/'content/construccion/assets-v8/procedencia.json',E/'imagenes-procedencia.json')
print(json.dumps({'output':str(OUT),'duration':P['duration'],'size_bytes':OUT.stat().st_size,'music':'house 120 BPM'}),flush=True)
