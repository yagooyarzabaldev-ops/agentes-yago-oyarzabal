from pathlib import Path
import json,math,re,shutil,subprocess,sys,wave
import numpy as np
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v3';E=ROOT/'entregas/construccion-v3';E.mkdir(parents=True,exist_ok=True)
P=json.loads((D/'params.json').read_text(encoding='utf-8'));duration=P['duration'];RATE=48000
def run(cmd):
 r=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,encoding='utf-8',errors='replace')
 if r.returncode:raise RuntimeError(r.stderr[-3500:])
 return r
def normalize(path,target=-14,peak=-2.3):
 r=run(['ffmpeg','-hide_banner','-nostats','-i',path,'-vn','-af',f'loudnorm=I={target}:TP={peak}:LRA=7:print_format=json','-f','null','-'])
 x=json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}',r.stderr,re.S).group())
 return f'loudnorm=I={target}:TP={peak}:LRA=7:measured_I={x["input_i"]}:measured_TP={x["input_tp"]}:measured_LRA={x["input_lra"]}:measured_thresh={x["input_thresh"]}:offset={x["target_offset"]}:linear=true'
def audio():
 from musica_v3 import build_score
 build_score(P,D/'musica-efectos.wav')
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'microfono-editado.wav',
  '-af','highpass=f=75,lowpass=f=12500,afftdn=nf=-32:tn=1,acompressor=threshold=0.18:ratio=2.2:attack=6:release=110:makeup=1.25',
  '-ar',RATE,'-c:a','pcm_s24le','-y',D/'microfono-limpio.wav'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'microfono-limpio.wav','-af',normalize(D/'microfono-limpio.wav',-16,-3),'-ar',RATE,'-c:a','pcm_s24le','-y',D/'voz.wav'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'musica-efectos.wav','-af',normalize(D/'musica-efectos.wav',-26.5,-6),'-ar',RATE,'-c:a','pcm_s24le','-y',D/'musica-normalizada.wav'])
 fc=f'[0:a]apad,atrim=duration={duration},asplit=2[v][s];[1:a][s]sidechaincompress=threshold=0.06:ratio=3:attack=10:release=140[m];[v][m]amix=inputs=2:normalize=0:duration=first[a]'
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'voz.wav','-i',D/'musica-normalizada.wav','-filter_complex',fc,'-map','[a]','-ar',RATE,'-c:a','pcm_s24le','-y',D/'mezcla.wav'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'mezcla.wav','-af',normalize(D/'mezcla.wav')+',aresample=192000,alimiter=limit=0.749894:level=disabled:latency=1,aresample=48000','-ar',RATE,'-c:a','pcm_s24le','-y',D/'master.wav'])
 (D/'audio-procedencia.json').write_text(json.dumps({'narration_source':P['source_audio'],'camera_audio_in_final':False,'synthetic_voice':False,'cloning':False,'speech_speed':1,'music':'Local original synthesis','seed':141128,'bpm':114,'style':'Groove funk electrónico: bajo sincopado, piano eléctrico y batería','ducking':True,'target_lufs':-14},ensure_ascii=False,indent=2),encoding='utf-8')
 print('Mezcla final lista: narración únicamente del WAV del micrófono.',flush=True)
def video():
 close=[s for s in P['shots'] if s['view']=='camera' and s['camera_mode']=='close']
 enable='+'.join(f'between(t,{s["start"]:.6f},{s["end"]:.6f})' for s in close) or '0'
 # A second framing is cropped from the same synchronized shot; speech remains at original speed.
 fc=f'[0:v]tpad=stop_mode=clone:stop_duration=2.3,split=2[wide][c];[c]crop=960:1706:60:90,scale=1080:1920[close];[wide][close]overlay=0:0:enable=\'{enable}\'[cam];[cam][1:v]overlay=0:0:format=auto,format=yuv420p[v]'
 out=E/'IA_sin_tantas_vueltas_Yago_v3.mp4'
 run(['ffmpeg','-hide_banner','-loglevel','error','-filter_complex_threads','3','-i',D/'camara.mp4','-i',D/'graficos.mov','-i',D/'master.wav',
  '-filter_complex',fc,'-map','[v]','-map','2:a','-t',duration,'-r','30','-c:v','h264_qsv','-global_quality','18','-preset','medium',
  '-c:a','aac','-b:a','256k','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart','-y',out])
 plan={'input':str(D/'camara.mp4'),'output':str(out),'profile':'1080p','fps':30,'segments':[{'start':0,'end':duration}],
  'audio':{'lufs':-14,'true_peak':-2.3},'composition':{'camera_audio':False,'microphone':P['source_audio'],'shots':len(P['shots']),'template':'content/construccion/escena_v3.html'}}
 (D/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
 for source,target in [('subs.srt','subtitulos.srt'),('transcripcion-editada.txt','transcripcion-editada.txt'),('audio-procedencia.json','audio-procedencia.json')]:shutil.copyfile(D/source,E/target)
 run(['ffmpeg','-hide_banner','-loglevel','error','-ss','0.8','-i',out,'-frames:v','1','-q:v','2','-y',E/'portada.jpg'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',out,'-t','16.46','-vf','scale=540:960','-c:v','h264_qsv','-global_quality','20','-c:a','aac','-b:a','160k','-movflags','+faststart','-y',E/'Avance_16s.mp4'])
 print(str(out),flush=True)
if '--audio-only' in sys.argv:audio()
else:
 if not (D/'master.wav').exists():audio()
 video()
