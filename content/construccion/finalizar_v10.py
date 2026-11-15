"""Compose V10 with localized monochrome camera punches and the arranged soundtrack."""
from pathlib import Path
import json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v10';E=ROOT/'entregas/construccion-v10'
P=json.loads((D/'params.json').read_text(encoding='utf-8'));OUT=E/'Sistemas_con_IA_Yago_v10.mp4'
def run(args):
 r=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace')
 if r.returncode:raise RuntimeError(r.stderr[-5000:])
 return r
bw='+'.join(f'between(t,{a:.8f},{b-1/60:.8f})' for a,b in P['bw_ranges'])
fc=f"[0:v]split=2[color][mono];[mono]crop=1000:888:40:24,scale=1080:960,hue=s=0,eq=contrast=1.10:brightness=-0.015[detail];[color][detail]overlay=0:0:enable='{bw}'[camera];[camera]tpad=stop_mode=clone:stop_duration=2,pad=1080:1920:0:0:color=black[base];[base][1:v]overlay=0:0:format=auto,format=yuv420p[v]"
print('Rendering V10: 35 scenes, three monochrome asides, new arranged score.',flush=True)
run(['ffmpeg','-hide_banner','-loglevel','error','-filter_complex_threads','3','-i',D/'camara.mp4','-i',D/'graficos.mov','-i',D/'master.wav','-filter_complex',fc,'-map','[v]','-map','2:a:0','-t',P['duration'],'-r','30','-c:v','h264_qsv','-global_quality','18','-preset','medium','-c:a','aac','-b:a','256k','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart','-y',OUT])
plan={'input':str(D/'camara.mp4'),'output':str(OUT),'profile':'1080p','fps':30,'segments':[{'start':0,'end':P['duration']}],'audio':{'lufs':-14,'true_peak':-2.3},'composition':{'camera_seconds':P['camera_visible_seconds'],'bw_ranges':P['bw_ranges'],'new_images':12,'unique_scenes':len(P['shots']),'template':'content/construccion/escena_v10.html','music':'original arranged minimal house, 120 BPM'}}
(D/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
for source,target in [('subs.srt','subtitulos.srt'),('transcripcion-editada.txt','transcripcion-editada.txt'),('audio-procedencia.json','audio-procedencia.json'),('revision-layout.json','revision-layout.json'),('direccion.json','direccion.json'),('revision-cortes.json','revision-cortes.json'),('revision-voz-identica.json','revision-voz-identica.json'),('revision-sincronizacion.json','revision-sincronizacion.json')]:shutil.copyfile(D/source,E/target)
run(['ffmpeg','-v','error','-ss','5.2','-i',OUT,'-frames:v','1','-q:v','2','-y',E/'portada.jpg'])
run(['ffmpeg','-v','error','-ss','17.1','-i',OUT,'-t','8.4','-vf','scale=540:960','-c:v','h264_qsv','-global_quality','20','-c:a','aac','-b:a','160k','-movflags','+faststart','-y',E/'Muestra_aclaracion.mp4'])
shutil.copyfile(ROOT/'content/construccion/assets-v10/procedencia.json',E/'imagenes-procedencia.json')
shutil.copyfile(ROOT/'content/construccion/copy-publicacion-v10.md',E/'copy-publicacion.md')
print(json.dumps({'output':str(OUT),'duration':P['duration'],'size_bytes':OUT.stat().st_size}),flush=True)
