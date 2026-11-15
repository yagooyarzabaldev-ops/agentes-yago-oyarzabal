from pathlib import Path
import json,math,re,shutil,subprocess,sys,wave
import numpy as np
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v2';E=ROOT/'entregas/construccion-v2';E.mkdir(parents=True,exist_ok=True)
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
 n=math.ceil(duration*RATE);music=np.zeros((n,2));rng=np.random.default_rng(141127)
 def note(at,dur,freq,gain,kind='pad',pan=0):
  off=round(at*RATE);count=min(round(dur*RATE),n-off)
  if count<1:return
  t=np.arange(count)/RATE;u=t/dur
  if kind=='pad':y=(np.sin(2*np.pi*freq*t)+.18*np.sin(2*np.pi*freq*2.004*t))*np.minimum(t/.5,1)*np.minimum((dur-t)/.6,1)
  elif kind=='pluck':y=np.sin(2*np.pi*freq*t)*np.minimum(t/.008,1)*np.exp(-t*5)*np.minimum((dur-t)/.1,1)
  elif kind=='kick':y=np.sin(2*np.pi*(47*t+1.6*(1-np.exp(-t*28))))*np.exp(-t*26)
  elif kind=='hat':y=rng.uniform(-1,1,count)*np.exp(-t*110)
  else:y=np.convolve(rng.uniform(-1,1,count),np.ones(11)/11,mode='same')*np.sin(np.pi*u)**2
  music[off:off+count,0]+=gain*y*math.cos((pan+1)*math.pi/4);music[off:off+count,1]+=gain*y*math.sin((pan+1)*math.pi/4)
 beat=60/102;chords=[[146.832,220,261.626,329.628],[116.541,174.614,220,293.665],[130.813,174.614,220,329.628],[130.813,195.998,261.626,293.665]]
 for bar in range(math.ceil((duration-2.2)/(beat*8))):
  for i,f in enumerate(chords[bar%4]):note(bar*beat*8,beat*8+.45,f,.022,'pad',-.6+i*.4)
 for k in range(math.ceil(P['voice_end']/beat)):
  t=k*beat;c=chords[(k//8)%4];note(t,.25,47,.05 if k%2==0 else .025,'kick');note(t+beat/2,.07,0,.012,'hat',.4 if k%2 else -.4);note(t,.65,c[k%4]*2,.019,'pluck',-.25 if k%2 else .25)
 for i,s in enumerate(P['shots']):
  if i and s['view']!='camera':note(max(0,s['start']-.10),.3,0,.10,'whoosh',-.3 if i%2 else .3)
 for i,f in enumerate([146.832,220,293.665,349.228]):note(P['voice_end'],2.2,f,.045,'pad',-.6+i*.4)
 t=np.arange(n)/RATE;music*=np.minimum(t/.35,1)[:,None]*np.clip((duration-t)/.75,0,1)[:,None]
 with wave.open(str(D/'musica-efectos.wav'),'wb') as f:
  f.setparams((2,2,RATE,0,'NONE','not compressed'));f.writeframes((np.clip(music,-.95,.95)*32767).astype('<i2').tobytes())
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'microfono-editado.wav',
  '-af','highpass=f=75,lowpass=f=12500,afftdn=nf=-32:tn=1,acompressor=threshold=0.18:ratio=2.2:attack=6:release=110:makeup=1.25',
  '-ar',RATE,'-c:a','pcm_s24le','-y',D/'microfono-limpio.wav'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'microfono-limpio.wav','-af',normalize(D/'microfono-limpio.wav',-16,-3),'-ar',RATE,'-c:a','pcm_s24le','-y',D/'voz.wav'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'musica-efectos.wav','-af',normalize(D/'musica-efectos.wav',-31,-8),'-ar',RATE,'-c:a','pcm_s24le','-y',D/'musica-normalizada.wav'])
 fc=f'[0:a]apad,atrim=duration={duration},asplit=2[v][s];[1:a][s]sidechaincompress=threshold=0.035:ratio=4:attack=15:release=200[m];[v][m]amix=inputs=2:normalize=0:duration=first[a]'
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'voz.wav','-i',D/'musica-normalizada.wav','-filter_complex',fc,'-map','[a]','-ar',RATE,'-c:a','pcm_s24le','-y',D/'mezcla.wav'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'mezcla.wav','-af',normalize(D/'mezcla.wav')+',aresample=192000,alimiter=limit=0.749894:level=disabled:latency=1,aresample=48000','-ar',RATE,'-c:a','pcm_s24le','-y',D/'master.wav'])
 (D/'audio-procedencia.json').write_text(json.dumps({'narration_source':P['source_audio'],'camera_audio_in_final':False,'synthetic_voice':False,'cloning':False,'speech_speed':1,'music':'Local original synthesis','seed':141127,'ducking':True,'target_lufs':-14},ensure_ascii=False,indent=2),encoding='utf-8')
 print('Mezcla final lista: narración únicamente del WAV del micrófono.',flush=True)
def video():
 close=[s for s in P['shots'] if s['view']=='camera' and s['camera_mode']=='close']
 enable='+'.join(f'between(t,{s["start"]:.6f},{s["end"]:.6f})' for s in close) or '0'
 # A second framing is cropped from the same synchronized shot; speech remains at original speed.
 fc=f'[0:v]tpad=stop_mode=clone:stop_duration=2.3,split=2[wide][c];[c]crop=960:1706:60:90,scale=1080:1920[close];[wide][close]overlay=0:0:enable=\'{enable}\'[cam];[cam][1:v]overlay=0:0:format=auto,format=yuv420p[v]'
 out=E/'IA_de_la_idea_a_la_practica_Yago_v2.mp4'
 run(['ffmpeg','-hide_banner','-loglevel','error','-filter_complex_threads','3','-i',D/'camara.mp4','-i',D/'graficos.mov','-i',D/'master.wav',
  '-filter_complex',fc,'-map','[v]','-map','2:a','-t',duration,'-r','30','-c:v','h264_qsv','-global_quality','18','-preset','medium',
  '-c:a','aac','-b:a','256k','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart','-y',out])
 plan={'input':str(D/'camara.mp4'),'output':str(out),'profile':'1080p','fps':30,'segments':[{'start':0,'end':duration}],
  'audio':{'lufs':-14,'true_peak':-2.3},'composition':{'camera_audio':False,'microphone':P['source_audio'],'shots':len(P['shots']),'template':'content/construccion/escena_v2.html'}}
 (D/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
 for source,target in [('subs.srt','subtitulos.srt'),('transcripcion-editada.txt','transcripcion-editada.txt'),('audio-procedencia.json','audio-procedencia.json')]:shutil.copyfile(D/source,E/target)
 run(['ffmpeg','-hide_banner','-loglevel','error','-ss','0.8','-i',out,'-frames:v','1','-q:v','2','-y',E/'portada.jpg'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',out,'-t','19.46','-vf','scale=540:960','-c:v','h264_qsv','-global_quality','20','-c:a','aac','-b:a','160k','-movflags','+faststart','-y',E/'Avance_19s.mp4'])
 print(str(out),flush=True)
if '--audio-only' in sys.argv:audio()
else:
 if not (D/'master.wav').exists():audio()
 video()
