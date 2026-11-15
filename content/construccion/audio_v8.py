"""Original subtle house bed at 120 BPM; unchanged real microphone narration."""
from pathlib import Path
import hashlib,json,math,re,subprocess,wave
import numpy as np
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v8';P=json.loads((D/'params.json').read_text(encoding='utf-8'))
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
beat=.5;roots=[55,43.6535,65.4065,49]
chords=[[220,261.626,329.628,391.995,493.883],[174.614,220,261.626,329.628,391.995],[196,261.626,329.628,391.995,493.883],[195.998,246.942,293.665,391.995,440]]
for bar in range(math.ceil(DUR/2)):
 at=bar*2;group=(bar//4)%4;root=roots[group];ch=chords[group];breakdown=bar in [16,17];energy=.68 if bar<2 else .72 if breakdown else 1
 for p in [0,1,2,3]:add(at+p*beat,.38,48,.22*energy,'kick')
 if not breakdown:
  for p in [1,3]:add(at+p*beat,.17,0,.062,'clap',.06)
  for p in [.5,1.5,2.5,3.5]:add(at+p*beat,.16,0,.043,'hat',.25)
  for k in range(8):add(at+k*.25+.008*(k%2),.045,0,.010 if k%2 else .014,'hat',-.45)
 for p,m,length in [(0,1,.31),(.75,1,.17),(1.5,1.5,.23),(2,1,.3),(2.75,2,.16),(3.5,1.5,.20)]:add(at+p*beat,length,root*m,.12*energy,'bass')
 for p in [.5,2.5,3.25]:
  for i,f in enumerate(ch):add(at+p*beat+i*.004,.65,f,.016,'chord',-.55+i*.275)
 if bar%4==0:
  for i,f in enumerate(ch[:4]):add(at,7.7,f/2,.009,'pad',-.6+i*.4)
 if bar%4==3 and not breakdown:
  for j in range(3):add(at+(3.25+j*.25)*beat,.09,700+j*110,.021,'perc',-.3+j*.3)
t=np.arange(N)/SR;track=np.tanh(track*1.1)/1.1
track*=np.minimum(t/.1,1)[:,None]*np.clip((DUR-t)/1.1,0,1)[:,None]
save(D/'house-original.wav',track)
run(['ffmpeg','-v','error','-i',D/'house-original.wav','-af',norm(D/'house-original.wav',-27,-7),'-ar',SR,'-c:a','pcm_s16le','-y',D/'house-normalizado.wav'])
for tr in P['transitions']:add(max(0,tr['at']-.04),.20,0,.023,'whoosh',.18*math.sin(tr['at']),fx)
save(D/'efectos-v8.wav',fx)
fc=f'[0:a]apad,atrim=duration={DUR},asplit=2[v][sc];[1:a][sc]sidechaincompress=threshold=0.045:ratio=3:attack=12:release=220[m];[v][m][2:a]amix=inputs=3:normalize=0:duration=first[a]'
run(['ffmpeg','-v','error','-i',D/'voz.wav','-i',D/'house-normalizado.wav','-i',D/'efectos-v8.wav','-filter_complex',fc,'-map','[a]','-ar',SR,'-c:a','pcm_s24le','-y',D/'mezcla.wav'])
run(['ffmpeg','-v','error','-i',D/'mezcla.wav','-af',norm(D/'mezcla.wav',-14,-2.3)+',aresample=192000,alimiter=limit=0.749894:level=disabled:latency=1,aresample=48000','-ar',SR,'-c:a','pcm_s24le','-y',D/'master.wav'])
run(['ffmpeg','-v','error','-ss','6','-i',D/'master.wav','-t','14','-c:a','aac','-b:a','192k','-y',D/'escucha-house.m4a'])
report={'narration_source':P['source_audio'],'cleaned_voice_source':'runtime/construccion-v3/voz.wav','narration_unchanged':True,'voice_sha256':hashlib.sha256((D/'voz.wav').read_bytes()).hexdigest(),'speech_speed':1,'synthetic_voice':False,'camera_audio_in_final':False,'music':'Original local synthesis, subtle house, four-on-the-floor, warm ninth chords and soft bass','bpm':120,'music_target_lufs_before_ducking':-27,'ducking':{'threshold':.045,'ratio':3,'attack_ms':12,'release_ms':220},'target_lufs':-14,'sound_effects':'Short quiet original transition whooshes','prior_mix_preserved':False}
(D/'audio-procedencia.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('House master ready; clean microphone stem unchanged.',flush=True)
