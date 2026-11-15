"""Minimal house: dry kick, sparse bass and hats, no pads or chord progression."""
from pathlib import Path
import hashlib,json,math,re,subprocess,wave
import numpy as np
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v9';P=json.loads((D/'params.json').read_text(encoding='utf-8'))
SR=48000;DUR=P['duration'];N=round(DUR*SR);rng=np.random.default_rng(141180)
track=np.zeros((N,2));fx=np.zeros((N,2))
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
def add(at,length,freq,gain,kind,pan=0,target=None):
 target=track if target is None else target;start=round(at*SR);count=min(round(length*SR),N-start)
 if count<1 or start<0:return
 t=np.arange(count)/SR;env=np.minimum(t/.004,1)*np.clip((length-t)/.025,0,1)
 if kind=='kick':
  phase=2*np.pi*(48*t+2.1*(1-np.exp(-t*35)));y=np.sin(phase)*np.exp(-t*16)+.035*rng.normal(0,1,count)*np.exp(-t*180)
 elif kind=='bass':
  phase=2*np.pi*freq*t;y=(np.sin(phase)+.18*np.sin(2*phase)+.07*np.sin(3*phase))*np.exp(-t*4)*env
 elif kind=='chord':
  phase=2*np.pi*freq*t;y=(np.sin(phase+.55*np.exp(-t*7)*np.sin(phase*2.001))+.13*np.sin(phase*3))*np.exp(-t*2.6)*env
 elif kind=='pad':
  y=(np.sin(2*np.pi*freq*t)+.27*np.sin(2*np.pi*freq*1.003*t))*.5*np.minimum(t/.6,1)*np.clip((length-t)/.7,0,1)
 elif kind=='hat':
  raw=rng.normal(0,1,count);y=(raw-np.roll(raw,1))*.26*np.exp(-t*(30 if length>.1 else 100))*env
 elif kind=='clap':
  raw=rng.normal(0,1,count);raw=raw-np.roll(raw,1);e=sum(np.where(t>=a,np.exp(-np.maximum(t-a,0)*b),0) for a,b in [(0,230),(.012,180),(.024,40)]);y=.22*raw*e*env
 elif kind=='perc':y=(np.sin(2*np.pi*freq*t)+.15*np.sin(2*np.pi*freq*2.6*t))*np.exp(-t*65)*env
 else:y=np.convolve(rng.normal(0,1,count),np.ones(13)/13,'same')*np.sin(np.pi*t/length)**2
 # Gentle pumping of harmony/bass under the regular four-on-the-floor kick.
 if kind in ['chord','pad','bass']:
  beatphase=((t+at)%.5);y*=.58+.42*(1-np.exp(-beatphase*12))
 target[start:start+count,0]+=gain*y*math.cos((pan+1)*math.pi/4)
 target[start:start+count,1]+=gain*y*math.sin((pan+1)*math.pi/4)
beat=.5;event_counts={k:0 for k in ['kick','hat','bass','rim','stab','pad','clap']}
for bar in range(math.ceil(DUR/2)):
 at=bar*2;root=55;breakdown=bar in [16,17];energy=.72 if bar<2 else .78 if breakdown else 1
 for p in [0,1,2,3]:
  add(at+p*beat,.29,48,.20*energy,'kick');event_counts['kick']+=1
 if not breakdown:
  for p in [.5,1.5,2.5,3.5]:
   add(at+p*beat+.009*(bar%2),.075,0,.030 if p in [.5,2.5] else .019,'hat',.25 if p<2 else -.25);event_counts['hat']+=1
  for p in [1,3]:
   add(at+p*beat,.055,710,.023,'perc',-.12);event_counts['rim']+=1
 for p,m,length in [(.5,1,.22),(2,1,.28),(3.5,1.5 if bar%4==3 else 1,.16)]:
  add(at+p*beat,length,root*m,.11*energy,'bass');event_counts['bass']+=1
 # One restrained two-note accent every four bars, with large spaces between.
 if bar%4==2:
  for i,f in enumerate([220,261.626]):add(at+1.25+i*.006,.23,f,.010,'chord',-.3+i*.6)
  event_counts['stab']+=1
t=np.arange(N)/SR;track=np.tanh(track*1.1)/1.1
track*=np.minimum(t/.1,1)[:,None]*np.clip((DUR-t)/1.1,0,1)[:,None]
save(D/'house-original.wav',track)
run(['ffmpeg','-v','error','-i',D/'house-original.wav','-af',norm(D/'house-original.wav',-28,-7),'-ar',SR,'-c:a','pcm_s16le','-y',D/'house-normalizado.wav'])
for i,tr in enumerate(P['transitions']):
 if i%4==0:add(max(0,tr['at']-.04),.16,0,.016,'whoosh',.18*math.sin(tr['at']),fx)
save(D/'efectos-v9.wav',fx)
fc=f'[0:a]apad,atrim=duration={DUR},asplit=2[v][sc];[1:a][sc]sidechaincompress=threshold=0.045:ratio=3:attack=12:release=220[m];[v][m][2:a]amix=inputs=3:normalize=0:duration=first[a]'
run(['ffmpeg','-v','error','-i',D/'voz.wav','-i',D/'house-normalizado.wav','-i',D/'efectos-v9.wav','-filter_complex',fc,'-map','[a]','-ar',SR,'-c:a','pcm_s24le','-y',D/'mezcla.wav'])
run(['ffmpeg','-v','error','-i',D/'mezcla.wav','-af',norm(D/'mezcla.wav',-14,-2.3)+',aresample=192000,alimiter=limit=0.749894:level=disabled:latency=1,aresample=48000','-ar',SR,'-c:a','pcm_s24le','-y',D/'master.wav'])
run(['ffmpeg','-v','error','-ss','6','-i',D/'master.wav','-t','14','-c:a','aac','-b:a','192k','-y',D/'escucha-house.m4a'])
report={'narration_source':P['source_audio'],'cleaned_voice_source':'runtime/construccion-v3/voz.wav','narration_unchanged':True,'voice_sha256':hashlib.sha256((D/'voz.wav').read_bytes()).hexdigest(),'speech_speed':1,'synthetic_voice':False,'camera_audio_in_final':False,'music':'Original local synthesis, minimal house: dry four-on-the-floor kick, sparse bass, closed hats and occasional two-note stab','bpm':120,'music_target_lufs_before_ducking':-28,'ducking':{'threshold':.045,'ratio':3,'attack_ms':12,'release_ms':220},'target_lufs':-14,'sound_effects':'Quiet whoosh on one of every four transitions','arrangement':{'pads':False,'chord_progression':False,'claps':False,'bass_notes_per_bar':3,'hat_hits_per_bar':4,'two_note_stab_every_bars':4},'event_counts':event_counts,'prior_mix_preserved':False}
(D/'audio-procedencia.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('House master ready; clean microphone stem unchanged.',flush=True)
