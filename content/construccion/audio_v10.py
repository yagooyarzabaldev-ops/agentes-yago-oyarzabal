"""Original minimal house with swing, section changes and timed clarification breaks."""
from pathlib import Path
import hashlib,json,math,re,subprocess,wave
import numpy as np
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v10';P=json.loads((D/'params.json').read_text(encoding='utf-8'))
SR=48000;DUR=P['duration'];N=round(DUR*SR);rng=np.random.default_rng(101114)
drums=np.zeros((N,2));music=np.zeros((N,2));fx=np.zeros((N,2));events=[]
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
def add(at,duration,gain,kind,freq=55,pan=0,target=None):
 target=drums if target is None else target;start=round(at*SR);count=min(round(duration*SR),N-start)
 if count<1 or start<0:return
 t=np.arange(count)/SR;env=np.minimum(t/.003,1)*np.clip((duration-t)/.02,0,1);noise=rng.normal(0,1,count)
 if kind=='kick':
  phase=2*np.pi*(48*t+2.7*(1-np.exp(-t*40)));y=(np.sin(phase)*np.exp(-t*14)+.028*noise*np.exp(-t*150))*env
 elif kind=='bass':
  phase=2*np.pi*freq*t;cut=np.exp(-t*10);y=(np.sin(phase)+.3*np.sin(phase*2)*cut+.16*np.sin(phase*3)*cut)*env*np.exp(-t*3.5)
 elif kind=='hat':y=(noise-np.roll(noise,1))*.22*np.exp(-t*90)*env
 elif kind=='open':y=(noise-np.roll(noise,2))*.16*np.exp(-t*22)*env
 elif kind=='rim':y=(np.sin(2*np.pi*740*t)+.4*np.sin(2*np.pi*1260*t)+.25*noise)*np.exp(-t*100)*env
 elif kind=='clap':
  env2=sum(np.where(t>=a,np.exp(-np.maximum(t-a,0)*v),0) for a,v in [(0,190),(.011,150),(.024,32)]);y=(noise-np.roll(noise,1))*.11*env2*env
 elif kind=='shaker':y=(noise-np.roll(noise,1))*.12*np.sin(np.pi*np.minimum(t/duration,1))**2*env
 elif kind=='pluck':
  phase=2*np.pi*freq*t;y=(np.sin(phase+1.2*np.sin(phase*2.003)*np.exp(-t*10))+.1*np.sin(phase*3))*env*np.exp(-t*5.8)
 elif kind=='click':y=(np.sin(2*np.pi*1800*t)+noise*.2)*np.exp(-t*170)*env
 else:
  y=np.convolve(noise,np.ones(15)/15,'same')*np.sin(np.pi*t/duration)**2
 if kind in ['bass','pluck']:
  beatphase=(t+at)%.5;y*=.45+.55*(1-np.exp(-beatphase*15))
 target[start:start+count,0]+=gain*y*math.cos((pan+1)*math.pi/4)
 target[start:start+count,1]+=gain*y*math.sin((pan+1)*math.pi/4)
 if at<DUR:events.append({'at':round(at,4),'kind':kind,'gain':gain})

# Sparse harmony, but a syncopated bass and humanized percussion carry the groove.
for bar in range(math.ceil(DUR/2)):
 at=bar*2;energy=.72 if bar<2 else .85 if bar<7 else 1.0;root=[55,55,65.406,48.999][(bar//4)%4]
 for p in range(4):add(at+p*.5,.32,.25*energy,'kick')
 for p in [1,3]:
  add(at+p*.5+.006,.11,.075*energy,'clap');add(at+p*.5+.012,.05,.041,'rim',pan=-.12)
 for j in range(8):
  swing=.023 if j%2 else 0;gain=(.032 if j%2 else .018)*energy
  add(at+j*.25+swing,.07,gain,'hat',pan=(-1)**j*.28)
 if bar%4 in [1,3]:add(at+1.75+.022,.22,.046*energy,'open',pan=.2)
 if bar>3:
  for j in [1,3,5,7,9,11,13,15]:add(at+j*.125+.016,.065,.017*(.6+(j%4)/5),'shaker',pan=(-1)**(j//2)*.45)
 patterns=[[(.5,1,.2),(1.75,1,.16),(2.5,1.5,.17),(3.5,1,.19)],[(.5,1,.21),(2,1,.16),(2.75,1,.15),(3.5,2,.14)]]
 for b,m,d in patterns[bar%2]:add(at+b*.5+.012,d,.19*energy,'bass',freq=root*m,target=music)
 # Two brief chord stabs and a quiet dotted delay; no sustained pad.
 if bar%2==1:
  for pos in [.75,1.625]:
   for j,ratio in enumerate([4,4*1.189207,6]):
    freq=root*ratio;add(at+pos+j*.006,.42,.020,'pluck',freq=freq,pan=(j-1)*.33,target=music)
    add(at+pos+.375+j*.006,.30,.006,'pluck',freq=freq,pan=-(j-1)*.4,target=music)
 # A compact pick-up at the end of a four-bar phrase.
 if bar%4==3:
  for j,p in enumerate([1.625,1.75,1.875]):add(at+p,.055,.025+j*.008,'rim',pan=-.3+j*.3)

t=np.arange(N)/SR;drum_gain=np.ones(N);music_gain=np.ones(N)
for a,b in P['bw_ranges']:
 # Drums drop out for the actual aside. Bass remains a faint bed under the microphone.
 depth=np.clip((t-a)/.045,0,1)*np.clip((b-t)/.08,0,1)
 drum_gain*=1-.96*depth;music_gain*=1-.72*depth
 add(a,.055,.025,'click',target=fx)
 add(b,.29,.24,'kick');add(b+.25,.12,.045,'open',pan=.15)
for at in P['major_accents']:
 add(max(0,at-.24),.26,.065,'sweep',pan=-.18,target=fx)
 add(at,.09,.031,'rim',pan=.14,target=fx)
 # Reinforce phrase landings that fall away from the global half-second kick grid.
 if abs(at*2-round(at*2))>.05:add(at,.28,.20,'kick')
for i,tr in enumerate(P['transitions']):
 if tr['mode'] in ['fold','particles','slit'] and tr['duration']:
  add(tr['at'],.045,.018,'click',pan=(-1)**i*.35,target=fx)
track=drums*drum_gain[:,None]+music*music_gain[:,None];track=np.tanh(track*1.15)/1.15
fade=np.minimum(t/.045,1)*np.clip((DUR-t)/.8,0,1);track*=fade[:,None];fx*=fade[:,None]
save(D/'house-original.wav',track);save(D/'efectos-v10.wav',fx)
run(['ffmpeg','-v','error','-i',D/'house-original.wav','-af',norm(D/'house-original.wav',-24.5,-6),'-ar',SR,'-c:a','pcm_s16le','-y',D/'house-normalizado.wav'])
fc=f'[0:a]apad,atrim=duration={DUR},asplit=2[v][sc];[1:a][sc]sidechaincompress=threshold=0.055:ratio=2.5:attack=12:release=180[m];[v][m][2:a]amix=inputs=3:normalize=0:duration=first[a]'
run(['ffmpeg','-v','error','-i',D/'voz.wav','-i',D/'house-normalizado.wav','-i',D/'efectos-v10.wav','-filter_complex',fc,'-map','[a]','-ar',SR,'-c:a','pcm_s24le','-y',D/'mezcla.wav'])
run(['ffmpeg','-v','error','-i',D/'mezcla.wav','-af',norm(D/'mezcla.wav',-14,-2.3)+',aresample=192000,alimiter=limit=0.749894:level=disabled:latency=1,aresample=48000','-ar',SR,'-c:a','pcm_s24le','-y',D/'master.wav'])
report={'music':'Original minimal house with swing, syncopated bass, dry claps, sparse minor stabs and dotted delays','method':'local synthesis, no third-party recordings','bpm':120,'music_lufs_before_ducking':-24.5,'voice_source':P['source_audio'],'voice_sha256':hashlib.sha256((D/'voz.wav').read_bytes()).hexdigest(),'narration_unchanged':True,'voice_synthetic':False,'bw_breaks':P['bw_ranges'],'major_visual_audio_accents':P['major_accents'],'transition_ticks':True,'audio_review':'technical measurement; subjective listening not performed','events':events}
(D/'audio-procedencia.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('V10 arranged house and microphone master ready.',flush=True)
