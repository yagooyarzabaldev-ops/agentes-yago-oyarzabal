"""Original score, voice mix, export and reproducible delivery for the construction reel."""
from pathlib import Path
import json, math, re, shutil, subprocess, sys, wave
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'runtime/construccion-v1'
E=ROOT/'entregas/construccion-v1'
E.mkdir(parents=True,exist_ok=True)
P=json.loads((D/'params.json').read_text(encoding='utf-8'))
duration=round(P['duration']*30)/30
RATE=48000

def run(cmd):
 p=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,encoding='utf-8',errors='replace')
 if p.returncode:raise RuntimeError(p.stderr[-4500:])
 return p

def normalization(path,target=-14,peak=-1.7):
 p=run(['ffmpeg','-hide_banner','-nostats','-i',path,'-vn','-af',f'loudnorm=I={target}:TP={peak}:LRA=7:print_format=json','-f','null','-'])
 m=json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}',p.stderr,re.S).group())
 return (f'loudnorm=I={target}:TP={peak}:LRA=7:'
  f'measured_I={m["input_i"]}:measured_TP={m["input_tp"]}:'
  f'measured_LRA={m["input_lra"]}:measured_thresh={m["input_thresh"]}:'
  f'offset={m["target_offset"]}:linear=true')

def write_wav(path,signal):
 with wave.open(str(path),'wb') as f:
  f.setparams((2,2,RATE,0,'NONE','not compressed'))
  f.writeframes((np.clip(signal,-.98,.98)*32767).astype('<i2').tobytes())

def audio():
 n=math.ceil(duration*RATE);score=np.zeros((n,2),np.float64);rng=np.random.default_rng(141126)
 def note(at,dur,freq,gain,kind='pad',pan=0):
  off=round(at*RATE);length=min(round(dur*RATE),n-off)
  if length<=0:return
  t=np.arange(length)/RATE;u=t/dur
  if kind=='pad':
   env=np.minimum(t/.7,1)*np.minimum((dur-t)/.8,1)
   y=(np.sin(2*np.pi*freq*t)+.25*np.sin(2*np.pi*freq*2.003*t))*.8*env
  elif kind=='pluck':
   env=np.minimum(t/.008,1)*np.exp(-t*5)*np.minimum((dur-t)/.15,1)
   y=(np.sin(2*np.pi*freq*t)+.18*np.sin(2*np.pi*freq*2*t))*env
  elif kind=='kick':
   y=np.sin(2*np.pi*(48*t+1.3*(1-np.exp(-t*35))))*np.exp(-t*25)
  elif kind=='hat':
   noise=rng.uniform(-1,1,length);y=(noise-np.roll(noise,1))*.5*np.exp(-t*150)
  elif kind=='whoosh':
   noise=rng.uniform(-1,1,length);noise=np.convolve(noise,np.ones(9)/9,mode='same')
   y=noise*np.sin(np.pi*u)**2
  else:y=np.sin(2*np.pi*freq*t)*np.sin(np.pi*u)**2
  score[off:off+length,0]+=y*gain*math.cos((pan+1)*math.pi/4)
  score[off:off+length,1]+=y*gain*math.sin((pan+1)*math.pi/4)
 bpm=102;beat=60/bpm
 # Dm9 / Bbmaj7 / Fmaj9 / C(add9), eight beats per chord.
 chords=[[146.832,220,261.626,329.628],[116.541,174.614,220,293.665],
         [130.813,174.614,220,329.628],[130.813,195.998,261.626,293.665]]
 for bar in range(math.ceil(duration/(beat*8))):
  chord=chords[bar%4];at=bar*beat*8
  for i,f in enumerate(chord):note(at,beat*8+.65,f,.027,'pad',-.65+i*.43)
 for k in range(math.ceil(duration/beat)):
  at=k*beat;ch=chords[(k//8)%4]
  note(at,.25,48,.058 if k%4==0 else .029,'kick')
  note(at+beat*.5,.06,0,.018,'hat',.4 if k%2 else -.4)
  note(at,.7,ch[(k*3)%4]*2,.025,'pluck',-.35 if k%2 else .35)
 for i,p in enumerate(P['paragraphs']):
  if i:note(max(0,p['start']-.12),.35,0,.11,'whoosh',-.3 if i%2 else .3)
  note(p['start']+.15,.32,659.255 if i%2 else 523.251,.025,'bell',.25)
 # Gentle resolved chord under the closing sentence.
 for i,f in enumerate([146.832,220,293.665,349.228]):note(duration-3,3,f,.025,'pad',-.5+i/3)
 times=np.arange(n)/RATE
 fade=np.minimum(times/.65,1)*np.clip((duration-times)/1.0,0,1)
 score*=fade[:,None]
 write_wav(D/'musica-original.wav',score)
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'voz.m4a','-af',
  'highpass=f=75,lowpass=f=11500,acompressor=threshold=0.20:ratio=2:attack=8:release=110:makeup=1.2',
  '-c:a','pcm_s16le','-ar',RATE,'-y',D/'voz-eq.wav'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'voz-eq.wav','-af',normalization(D/'voz-eq.wav',-16,-3),
  '-c:a','pcm_s16le','-ar',RATE,'-y',D/'voz-normalizada.wav'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'musica-original.wav','-af',normalization(D/'musica-original.wav',-31,-9),
  '-c:a','pcm_s16le','-ar',RATE,'-y',D/'musica-normalizada.wav'])
 fc=f'[0:a]apad,atrim=duration={duration},asplit=2[v][sc];[1:a][sc]sidechaincompress=threshold=0.035:ratio=4:attack=18:release=220[m];[v][m]amix=inputs=2:normalize=0:duration=first[a]'
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'voz-normalizada.wav','-i',D/'musica-normalizada.wav',
  '-filter_complex',fc,'-map','[a]','-ar',RATE,'-c:a','pcm_s24le','-y',D/'mezcla.wav'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'mezcla.wav','-af',normalization(D/'mezcla.wav'),
  '-c:a','pcm_s24le','-ar',RATE,'-y',D/'master.wav'])
 (D/'audio-procedencia.json').write_text(json.dumps({'voice':'es-AR-TomasNeural','synthetic':True,'cloned':False,
  'music':'Composición instrumental generada localmente con síntesis sinusoidal y ruido determinista',
  'seed':141126,'bpm':bpm,'chords':['Dm9','Bbmaj7','Fmaj9','C(add9)'],'third_party_recordings':False,
  'ducking':True,'target_lufs':-14,'target_true_peak':-1.7},ensure_ascii=False,indent=2),encoding='utf-8')
 print('Voz y música originales mezcladas; master listo.',flush=True)

def video():
 out=E/'Como_construimos_el_agente_de_marketing_v1.mp4'
 run(['ffmpeg','-hide_banner','-loglevel','error','-filter_threads','3','-i',D/'graficos.mov','-i',D/'master.wav',
  '-map','0:v','-map','1:a','-t',duration,'-vf','scale=1080:1920:out_color_matrix=bt709,format=yuv420p',
  '-r','30','-c:v','h264_qsv','-global_quality','18','-preset','medium','-c:a','aac','-b:a','256k',
  '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart','-y',out])
 plan={'input':str(D/'graficos.mov'),'output':str(out),'profile':'1080p','fps':30,
  'segments':[{'start':0,'end':duration}],'audio':{'lufs':-14,'true_peak':-1.7},
  'composition':{'template':'content/construccion/escena.html','chapters':9,'synthetic_voice':True}}
 (D/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
 shutil.copyfile(D/'subs.srt',E/'subtitulos.srt')
 shutil.copyfile(ROOT/'content/construccion/guion.txt',E/'guion.txt')
 run(['ffmpeg','-hide_banner','-loglevel','error','-ss','3.3','-i',out,'-frames:v','1','-q:v','2','-y',E/'portada.jpg'])
 run(['ffmpeg','-hide_banner','-loglevel','error','-i',out,'-t','15.7','-vf','scale=540:960',
  '-c:v','h264_qsv','-global_quality','20','-c:a','aac','-b:a','160k','-movflags','+faststart','-y',E/'Avance_16s.mp4'])
 print(str(out),flush=True)

if '--audio-only' in sys.argv:audio()
else:
 if not (D/'master.wav').exists():audio()
 video()
