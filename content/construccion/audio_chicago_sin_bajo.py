"""Original Chicago-inspired piano/organ house audition, with no bass instrument."""
from pathlib import Path
import collections,hashlib,json,math,re,subprocess,wave
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'runtime/chicago-sin-bajo';E=ROOT/'entregas/chicago-sin-bajo'
D.mkdir(parents=True,exist_ok=True);E.mkdir(parents=True,exist_ok=True)
P=json.loads((ROOT/'runtime/construccion-v10/params.json').read_text(encoding='utf-8'))
SR=48000;DUR=P['duration'];N=round(SR*DUR);BPM=120;BEAT=.5
rng=np.random.default_rng(1114120)
drums=np.zeros((N,2),dtype=np.float32);keys=np.zeros_like(drums);events=[]

def run(args):
 r=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace')
 if r.returncode:raise RuntimeError(r.stderr[-5000:])
 return r

def measure(file):
 r=run(['ffmpeg','-hide_banner','-nostats','-i',file,'-vn','-af','loudnorm=I=-14:TP=-3:LRA=8:print_format=json','-f','null','-'])
 return json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}',r.stderr,re.S).group())

def loudnorm(file,target,peak):
 r=run(['ffmpeg','-hide_banner','-nostats','-i',file,'-vn','-af',f'loudnorm=I={target}:TP={peak}:LRA=8:print_format=json','-f','null','-'])
 x=json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}',r.stderr,re.S).group())
 return f'loudnorm=I={target}:TP={peak}:LRA=8:measured_I={x["input_i"]}:measured_TP={x["input_tp"]}:measured_LRA={x["input_lra"]}:measured_thresh={x["input_thresh"]}:offset={x["target_offset"]}:linear=true'

def wav(file,data):
 with wave.open(str(file),'wb') as f:
  f.setparams((2,2,SR,0,'NONE','not compressed'))
  f.writeframes((np.clip(data,-.99,.99)*32767).astype('<i2').tobytes())

def put(at,signal,gain,pan,kind,target,note=None):
 start=round(at*SR)
 if start<0 or start>=N:return
 count=min(len(signal),N-start);sig=signal[:count]*gain
 target[start:start+count,0]+=sig*math.cos((pan+1)*math.pi/4)
 target[start:start+count,1]+=sig*math.sin((pan+1)*math.pi/4)
 events.append(dict(at=round(at,5),kind=kind,note=note,gain=round(gain,5)))

def percussion(kind,at,gain,pan=0):
 length={'kick':.24,'clap':.19,'hat':.075,'open_hat':.22,'rim':.065,'shaker':.09}[kind]
 t=np.arange(round(length*SR))/SR;noise=rng.normal(0,1,len(t));edge=np.minimum(t/.001,1)*np.minimum((length-t)/.012,1)
 high=(noise-np.roll(noise,1))*.5
 if kind=='kick':
  # Short kick, not a tuned or sustained sub-bass voice.
  phase=2*np.pi*(64*t+2.0*(1-np.exp(-t*42)))
  y=(np.sin(phase)*np.exp(-t*23)+.035*high*np.exp(-t*180))*edge
 elif kind=='clap':
  env=sum(np.where(t>=a,np.exp(-np.maximum(t-a,0)*d),0) for a,d in [(0,250),(.011,200),(.024,30)])
  y=(high*.52+np.sin(2*np.pi*190*t)*.05)*env*edge
 elif kind in ['hat','open_hat']:
  metal=sum(np.sign(np.sin(2*np.pi*f*t)) for f in [421,587,833,1177,1723,2491])/6
  metal=metal-np.roll(metal,2);env=np.exp(-t*(100 if kind=='hat' else 22))
  y=(high*.34+metal*.12)*env*edge
 elif kind=='rim':y=(np.sin(2*np.pi*870*t)+.35*np.sin(2*np.pi*1320*t))*np.exp(-t*95)*edge
 else:y=high*np.sin(np.pi*t/length)**2*edge*.35
 put(at,y,gain,pan,kind,drums)

def keyboard(kind,note,at,gate,gain,pan):
 assert note>=60, 'No bass-register keyboard notes in this arrangement'
 length=gate+.20;t=np.arange(round(length*SR))/SR;freq=440*2**((note-69)/12)
 release=np.exp(-np.maximum(t-gate,0)*24)
 if kind=='piano':
  y=np.zeros(len(t));velocity=.65+gain*3
  # Inharmonic, decaying partials and a restrained hammer transient.
  for h in range(1,25):
   amplitude=(h**-1.12)*np.exp(-h/17)
   decay=np.exp(-t*(1.8+h*.64))
   phase=2*np.pi*freq*h*np.sqrt(1+.00006*h*h)*t
   y+=amplitude*decay*(np.sin(phase)+.12*np.sin(phase*1.0018))
  y+=rng.normal(0,1,len(t))*.028*np.exp(-t*110)
  y*=np.minimum(t/.002,1)*release*.45*velocity
 else:
  phase=2*np.pi*freq*t
  y=(np.sin(phase)+.55*np.sin(phase*2)+.22*np.sin(phase*3)+.1*np.sin(phase*4))*.42
  y*=np.minimum(t/.007,1)*np.exp(-t*1.6)*release*(.93+.07*np.sin(2*np.pi*5.3*t))
 # The keyboard itself is high-register and contains no bass-line oscillator.
 put(at,y,gain,pan,kind,keys,note)

# Upper-register inversions: Fm7 / Bbm7 / Ebmaj9 / Abmaj7.
chords=[[65,68,72,75],[65,68,70,73],[67,70,74,77],[67,68,72,75]]
for bar in range(math.ceil(DUR/2)):
 at=bar*2;breakdown=16<=bar<20;intro=bar<2;outro=bar>=32
 energy=.82 if intro else .92 if outro else 1
 if not breakdown:
  for b in range(4):percussion('kick',at+b*BEAT,.31*energy)
 elif bar in [16,18]:percussion('kick',at,.22)
 for b in [1,3]:percussion('clap',at+b*BEAT+.004,.115*(.65 if breakdown else energy),-.07)
 for j in range(8):
  off=j%2;shift=.024 if off else 0
  if breakdown and not off:continue
  percussion('hat',at+j*.25+shift,(.045 if off else .025)*(.65 if breakdown else energy),.24 if off else -.26)
 if not intro and not breakdown:
  for b in [.5,1.5,2.5,3.5]:percussion('open_hat',at+b*BEAT+.018,.060 if b in [1.5,3.5] else .044,.22)
  for j in [3,7,11,15]:percussion('shaker',at+j*.125+.014,.035,(-1)**(j//4)*.4)
 if bar%4 in [1,3]:percussion('rim',at+1.375,.046,-.22)
 if bar%8==7:
  for j,b in enumerate([1.625,1.75,1.875]):percussion('rim',at+b,.032+j*.008,(-1)**j*.32)
 chord=chords[(bar//2)%4]
 if breakdown:
  pattern=[(.25,.46,.065),(1.25,.34,.052)]
 elif intro:
  pattern=[(.0,.25,.070),(.75,.18,.056),(1.5,.22,.065)]
 elif bar%2:
  pattern=[(.0,.22,.080),(.75,.16,.068),(1.375,.19,.072),(1.75,.15,.050)]
 else:
  pattern=[(.0,.20,.080),(.625,.18,.067),(1.0,.15,.055),(1.625,.23,.075)]
 if outro:pattern=pattern[:2]
 for position,gate,gain in pattern:
  for j,note in enumerate(chord):keyboard('piano',note,at+position+j*.002,gate,gain,(-.3+j*.2))
 # A short upper-register organ answers the piano; no left-hand root or bass riff.
 if 2<=bar<32 and bar%2==0:
  for j,note in enumerate([chord[1],chord[2],chord[3]]):
   keyboard('organ',note,at+1.25+j*.003,.22,.026,.24-j*.24)
 # Small octave punctuation on the final beat of an eight-bar phrase.
 if bar%8==7:
  for k,note in enumerate([chord[2]+12,chord[1]+12]):keyboard('piano',note,at+1.5+k*.25,.13,.043,(-1)**k*.28)

# Quiet stereo early reflections, confined to keys, instead of a dense sustained pad.
dry=keys.copy()
for seconds,gain,swap in [(.043,.13,False),(.071,.10,True),(.125,.07,True),(.375,.045,False)]:
 delay=round(seconds*SR);keys[delay:]+=dry[:-delay,::-1] * gain if swap else dry[:-delay]*gain
t=np.arange(N)/SR
fade=np.minimum(t/.012,1)*np.clip((DUR-t)/1.2,0,1)
keys*=fade[:,None];drums*=fade[:,None]
wav(D/'bateria.wav',drums);wav(D/'teclas.wav',keys)
# Remove low keyboard rumble, while keeping a short drum kick as part of the beat.
run(['ffmpeg','-v','error','-i',D/'bateria.wav','-i',D/'teclas.wav','-filter_complex','[1:a]highpass=f=240[hp];[0:a][hp]amix=inputs=2:normalize=0,acompressor=threshold=0.24:ratio=1.6:attack=18:release=110:makeup=1.08[a]','-map','[a]','-ar',SR,'-c:a','pcm_s24le','-y',D/'instrumental-crudo.wav'])
instrumental=E/'House_Chicago_sin_bajo.wav'
run(['ffmpeg','-v','error','-i',D/'instrumental-crudo.wav','-af',loudnorm(D/'instrumental-crudo.wav',-16,-3),'-ar',SR,'-c:a','pcm_s24le','-y',instrumental])
run(['ffmpeg','-v','error','-i',instrumental,'-c:a','aac','-b:a','256k','-movflags','+faststart','-y',E/'House_Chicago_sin_bajo.m4a'])
run(['ffmpeg','-v','error','-ss','8','-i',instrumental,'-t','32','-af','afade=t=in:d=0.06,afade=t=out:st=31:d=1','-c:a','aac','-b:a','256k','-movflags','+faststart','-y',E/'Muestra_32s_Chicago_sin_bajo.m4a'])

# Audition against the accepted picture and untouched microphone stem.
bed=keys+drums
for a,b in P['bw_ranges']:
 depth=np.clip((t-a)/.04,0,1)*np.clip((b-t)/.1,0,1);bed*=1-.78*depth[:,None]
wav(D/'base-reel-cruda.wav',bed)
run(['ffmpeg','-v','error','-i',D/'base-reel-cruda.wav','-af',loudnorm(D/'base-reel-cruda.wav',-25,-7),'-ar',SR,'-c:a','pcm_s24le','-y',D/'base-reel.wav'])
voice=ROOT/'runtime/construccion-v10/voz.wav'
fc=f'[0:a]apad,atrim=duration={DUR},asplit=2[v][sc];[1:a][sc]sidechaincompress=threshold=0.05:ratio=2.7:attack=12:release=180[m];[v][m]amix=inputs=2:normalize=0:duration=first[a]'
run(['ffmpeg','-v','error','-i',voice,'-i',D/'base-reel.wav','-filter_complex',fc,'-map','[a]','-ar',SR,'-c:a','pcm_s24le','-y',D/'mezcla.wav'])
run(['ffmpeg','-v','error','-i',D/'mezcla.wav','-af',loudnorm(D/'mezcla.wav',-14,-3.5),'-ar',SR,'-c:a','pcm_s24le','-y',D/'master.wav'])
run(['ffmpeg','-v','error','-ss','7.333333333','-i',D/'master.wav','-t','32.7','-af','afade=t=out:st=32.5:d=0.2','-c:a','aac','-b:a','256k','-movflags','+faststart','-y',E/'Muestra_con_tu_voz.m4a'])
source=ROOT/'entregas/construccion-v10/Sistemas_con_IA_Yago_v10.mp4'
video=E/'Sistemas_con_IA_Yago_Chicago_sin_bajo.mp4'
run(['ffmpeg','-v','error','-i',source,'-i',D/'master.wav','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','256k','-t',DUR,'-movflags','+faststart','-y',video])
assert not any('bass' in e['kind'] for e in events)
metrics={}
for file in [E/'House_Chicago_sin_bajo.m4a',E/'Muestra_32s_Chicago_sin_bajo.m4a',E/'Muestra_con_tu_voz.m4a',video]:
 m=measure(file);metrics[file.name]={'lufs':float(m['input_i']),'true_peak':float(m['input_tp']),'lra':float(m['input_lra'])}
report={'style':'Original Chicago-inspired house audition','bpm':BPM,'duration':DUR,'bass_instrument':False,'sub_bass':False,'kick':'short percussive kick retained','piano_and_organ':'original additive synthesis, upper-register voicings','minimum_keyboard_midi_note':min(e['note'] for e in events if e['note'] is not None),'third_party_samples':False,'event_counts':dict(collections.Counter(e['kind'] for e in events)),'voice_sha256':hashlib.sha256(voice.read_bytes()).hexdigest(),'picture':'V10 video stream copied without re-encoding','bw_mix_dips':P['bw_ranges'],'metrics':metrics,'review':'technical measurements; subjective listening not performed'}
(E/'procedencia-y-revision.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(D/'eventos.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False),flush=True)
