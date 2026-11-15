"""Original mic narration unchanged; original groove with intentional breaks and foley."""
from pathlib import Path
import json,math,re,subprocess,wave
import numpy as np
from musica_v3 import build_score
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v5';P=json.loads((D/'params.json').read_text(encoding='utf-8'));SR=48000
def run(args):
 r=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace')
 if r.returncode:raise RuntimeError(r.stderr[-4000:])
 return r
def norm(path,target,peak):
 r=run(['ffmpeg','-hide_banner','-nostats','-i',path,'-vn','-af',f'loudnorm=I={target}:TP={peak}:LRA=7:print_format=json','-f','null','-'])
 x=json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}',r.stderr,re.S).group())
 return f'loudnorm=I={target}:TP={peak}:LRA=7:measured_I={x["input_i"]}:measured_TP={x["input_tp"]}:measured_LRA={x["input_lra"]}:measured_thresh={x["input_thresh"]}:offset={x["target_offset"]}:linear=true'
def save(path,y):
 with wave.open(str(path),'wb') as f:
  f.setparams((2,2,SR,0,'NONE','not compressed'));f.writeframes((np.clip(y,-.98,.98)*32767).astype('<i2').tobytes())
build_score({**P,'shots':[]},D/'groove-original.wav')
run(['ffmpeg','-v','error','-i',D/'groove-original.wav','-af',norm(D/'groove-original.wav',-26.5,-6),'-ar',SR,'-c:a','pcm_s16le','-y',D/'groove-normalizado.wav'])
with wave.open(str(D/'groove-normalizado.wav'),'rb') as f:music=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(float).reshape(-1,2)/32768
n=round(P['duration']*SR);music=music[:n];t=np.arange(n)/SR;gain=np.ones(n)
for a,b in P['music_breaks']:
 fade=.045
 dip=np.minimum(np.clip((t-a)/fade,0,1),np.clip((b-t)/fade,0,1));gain*=1-.96*dip
music*=gain[:,None];save(D/'musica-v5.wav',music)
fx=np.zeros((n,2));rng=np.random.default_rng(141150)
def effect(at,kind):
 length={'click':.075,'tap':.13,'paper':.27,'open':.38,'send':.22,'resolve':.85,'type':.4}[kind]
 count=round(length*SR);tt=np.arange(count)/SR;q=tt/length;noise=rng.normal(0,1,count)
 if kind=='click':y=(.08*np.sin(2*np.pi*1150*tt)+.045*noise)*np.exp(-tt*95)
 elif kind=='tap':y=.15*(np.sin(2*np.pi*210*tt)+.3*np.sin(2*np.pi*470*tt))*np.exp(-tt*36)
 elif kind=='paper':y=.07*np.convolve(noise,np.ones(5)/5,'same')*np.sin(np.pi*q)**1.8
 elif kind=='open':y=.11*np.convolve(noise,np.ones(11)/11,'same')*np.sin(np.pi*q)**2+.04*np.sin(2*np.pi*(100*tt+130*tt*tt))*np.sin(np.pi*q)**2
 elif kind=='send':y=.085*np.sin(2*np.pi*(420*tt+1700*tt*tt))*np.exp(-tt*18)
 elif kind=='resolve':y=sum(.026*np.sin(2*np.pi*f*tt)*np.exp(-tt*5) for f in [261.626,329.628,391.995,523.252])
 else:
  y=np.zeros(count)
  for j in range(6):
   pulse=tt-j*.055;y+=np.where(pulse>=0,.055*np.sin(2*np.pi*1250*np.maximum(pulse,0))*np.exp(-np.maximum(pulse,0)*145),0)
 y*=np.minimum(tt/.003,1)*np.minimum((length-tt)/.018,1)
 start=round(at*SR);m=min(count,n-start);pan=.2*math.sin(at)
 fx[start:start+m,0]+=y[:m]*math.cos((pan+1)*math.pi/4);fx[start:start+m,1]+=y[:m]*math.sin((pan+1)*math.pi/4)
for ev in P['sound_events']:effect(ev['at'],ev['kind'])
save(D/'efectos-v5.wav',fx)
fc=f'[0:a]apad,atrim=duration={P["duration"]},asplit=2[v][s];[1:a][s]sidechaincompress=threshold=0.06:ratio=3:attack=10:release=140[m];[v][m][2:a]amix=inputs=3:normalize=0:duration=first[a]'
run(['ffmpeg','-v','error','-i',D/'voz.wav','-i',D/'musica-v5.wav','-i',D/'efectos-v5.wav','-filter_complex',fc,'-map','[a]','-ar',SR,'-c:a','pcm_s24le','-y',D/'mezcla.wav'])
run(['ffmpeg','-v','error','-i',D/'mezcla.wav','-af',norm(D/'mezcla.wav',-14,-2.3)+',aresample=192000,alimiter=limit=0.749894:level=disabled:latency=1,aresample=48000','-ar',SR,'-c:a','pcm_s24le','-y',D/'master.wav'])
(D/'audio-procedencia.json').write_text(json.dumps({'narration_source':P['source_audio'],'cleaned_voice_source':'runtime/construccion-v3/voz.wav','narration_unchanged':True,'speech_speed':1,'synthetic_voice':False,'cloning':False,'camera_audio_in_final':False,'music':'Original local synthesis, funk/electronic 114 BPM','foley':'Original local synthesis','sound_events':P['sound_events'],'music_breaks':P['music_breaks'],'ducking':True,'target_lufs':-14},ensure_ascii=False,indent=2),encoding='utf-8')
print('V5 audio ready; original microphone narration unchanged.',flush=True)
