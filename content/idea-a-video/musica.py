"""Idea-to-video: new 122 BPM minimal Chicago arrangement; no bass instrument."""
from pathlib import Path
import argparse,collections,hashlib,json,math,re,subprocess,wave
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description='Chicago house original sin línea de bajo; síntesis local y mezcla opcional.')
parser.add_argument('--params',type=Path,default=ROOT/'content/idea-a-video/params.json')
parser.add_argument('--voice',type=Path,default=ROOT/'runtime/idea-a-video-v1/voz.wav')
parser.add_argument('--picture',type=Path,default=ROOT/'runtime/idea-a-video-v1/imagen.mp4')
parser.add_argument('--work',type=Path,default=ROOT/'runtime/idea-a-video-v1/music')
parser.add_argument('--output',type=Path,default=ROOT/'entregas/idea-a-video-v1')
parser.add_argument('--duration',type=float)
parser.add_argument('--seed',type=int,default=1511122)
parser.add_argument('--instrumental-only',action='store_true')
args=parser.parse_args()
if not args.instrumental_only and (not args.voice.is_file() or not args.picture.is_file()):
 parser.error('Se necesitan --voice y --picture locales, o --instrumental-only para crear solo música.')
P=json.loads(args.params.read_text(encoding='utf-8'))
if args.duration is not None:P['duration']=args.duration
if not 10<=P['duration']<=180:parser.error('Duración admitida: 10–180 segundos.')
D=args.work.resolve();E=args.output.resolve()
D.mkdir(parents=True,exist_ok=True);E.mkdir(parents=True,exist_ok=True)
SR=48000;DUR=P['duration'];N=round(SR*DUR);BPM=122;BEAT=60/BPM;BAR=4*BEAT
rng=np.random.default_rng(args.seed)
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
 length={'kick':.24,'clap':.19,'hat':.075,'open_hat':.22,'rim':.065,'shaker':.09,'wood':.08}[kind]
 t=np.arange(round(length*SR))/SR;noise=rng.normal(0,1,len(t));edge=np.minimum(t/.001,1)*np.minimum((length-t)/.012,1)
 high=(noise-np.roll(noise,1))*.5
 if kind=='kick':
  # Short kick, not a tuned or sustained sub-bass voice.
  phase=2*np.pi*(76*t+1.7*(1-np.exp(-t*48)))
  y=(np.sin(phase)*np.exp(-t*29)+.035*high*np.exp(-t*180))*edge
 elif kind=='clap':
  env=sum(np.where(t>=a,np.exp(-np.maximum(t-a,0)*d),0) for a,d in [(0,250),(.011,200),(.022,48)])
  y=(high*.52+np.sin(2*np.pi*190*t)*.05)*env*edge
 elif kind in ['hat','open_hat']:
  metal=sum(np.sign(np.sin(2*np.pi*f*t)) for f in [421,587,833,1177,1723,2491])/6
  metal=metal-np.roll(metal,2);env=np.exp(-t*(100 if kind=='hat' else 22))
  y=(high*.34+metal*.12)*env*edge
 elif kind=='wood':y=(np.sin(2*np.pi*1240*t)+.4*np.sin(2*np.pi*1810*t))*np.exp(-t*76)*edge
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
  y=(np.sin(phase)*.50+.62*np.sin(phase*2)+.27*np.sin(phase*3)+.08*np.sin(phase*5))*.42
  y*=np.minimum(t/.004,1)*np.exp(-t*5.2)*release*(.93+.07*np.sin(2*np.pi*5.3*t))
 # The keyboard itself is high-register and contains no bass-line oscillator.
 put(at,y,gain,pan,kind,keys,note)

# Four upper-register voicings cycle; harmony answers the percussion.
# No piano lead, root-note ostinato, bass oscillator or sub-bass track.
chords=[[67,70,74,77],[65,69,72,76],[64,67,71,76],[67,72,74,79]]
patterns=[[(.5,.11,.052),(2.75,.14,.047)],[(1.25,.12,.050),(3.5,.10,.038)],[(.75,.15,.048),(2.5,.10,.052)],[(1.5,.12,.041),(3.25,.14,.049)]]
for bar in range(math.ceil(DUR/BAR)):
 at=bar*BAR;section=bar//4;breakdown=bar in [7,14,15,28,29,30];intro=bar<2;outro=at>DUR-4
 energy=.84 if intro else .78 if breakdown else .92 if outro else 1
 if not breakdown:
  for b in range(4):percussion('kick',at+b*BEAT,.29*energy)
 elif bar%2==0:percussion('kick',at,.22)
 for b in [1,3]:percussion('clap',at+b*BEAT+.006,.12*energy,-.08)
 # A swung offbeat and restrained ghost notes create the new pocket.
 for j in range(16):
  if j%4==0 or (j%2==0 and breakdown):continue
  if j%2 and (j+bar)%3==0:continue
  shift=.028 if j%2 else .011
  gain=.040 if j%4==2 else .016 if j%4==1 else .024
  percussion('hat',at+j*BEAT/4+shift,gain*energy,(-1)**j*.32)
 if not breakdown:
  for b in [.5,2.5]:percussion('open_hat',at+b*BEAT+.012,.061*energy,.25)
  if bar%2:percussion('open_hat',at+3.5*BEAT+.012,.044,-.22)
 for j in ([3,7,11,15] if not intro else [7,15]):
  percussion('shaker',at+j*BEAT/4+.026,.044*energy,(-1)**(j//4)*.48)
 # Woodblock phrases have four different shapes, with spaces between hits.
 wood_patterns=[[1.5,3.25],[.75,2.5],[1.75,3.5],[.5,2.75]]
 for i,b in enumerate(wood_patterns[bar%4]):percussion('wood',at+b*BEAT+.012,.041*energy,(-1)**i*.28)
 if bar%2:percussion('rim',at+2.75*BEAT+.025,.033,-.3)
 if bar%8==7:
  for i,b in enumerate([3,3.5,3.75]):percussion('rim',at+b*BEAT,.023+i*.009,(-1)**i*.3)
 chord=chords[(bar//4)%4]
 phrase=[(.5,.40,.042),(2.5,.32,.045)] if breakdown else patterns[bar%4]
 if intro:phrase=[(.75,.13,.062)]
 if outro:phrase=phrase[:1]
 for pos,gate,gain in phrase:
  for i,note in enumerate(chord):keyboard('organ',note,at+pos*BEAT+i*.003,gate,gain,-.32+i*.21)
 # Tiny upper-register answer only at phrase endings; never a continuous melody.
 if bar%4==3 and not breakdown:
  for i,note in enumerate([chord[1]+12,chord[2]+12]):keyboard('organ',note,at+(3+i*.5)*BEAT,.08,.028,(-1)**i*.4)

# Quiet stereo early reflections, confined to keys, instead of a dense sustained pad.
dry=keys.copy()
for seconds,gain,swap in [(.031,.08,False),(.057,.06,True),(BEAT*.75,.14,True),(BEAT*1.5,.055,False)]:
 delay=round(seconds*SR);keys[delay:]+=dry[:-delay,::-1] * gain if swap else dry[:-delay]*gain
t=np.arange(N)/SR
fade=np.minimum(t/.012,1)*np.clip((DUR-t)/1.2,0,1)
keys*=fade[:,None];drums*=fade[:,None]
wav(D/'bateria.wav',drums);wav(D/'teclas.wav',keys)
# Remove low keyboard rumble, while keeping a short drum kick as part of the beat.
run(['ffmpeg','-v','error','-i',D/'bateria.wav','-i',D/'teclas.wav','-filter_complex','[1:a]highpass=f=240[hp];[0:a][hp]amix=inputs=2:normalize=0,acompressor=threshold=0.24:ratio=1.6:attack=18:release=110:makeup=1.08[a]','-map','[a]','-ar',SR,'-c:a','pcm_s24le','-y',D/'instrumental-crudo.wav'])
instrumental=E/'House_Idea_a_Video.wav'
run(['ffmpeg','-v','error','-i',D/'instrumental-crudo.wav','-af',loudnorm(D/'instrumental-crudo.wav',-16.5,-3),'-ar',SR,'-c:a','pcm_s24le','-y',instrumental])
run(['ffmpeg','-v','error','-i',instrumental,'-c:a','aac','-b:a','256k','-movflags','+faststart','-y',E/'House_Idea_a_Video.m4a'])
preview_start=min(4*BAR,DUR/4);preview_duration=min(16*BAR,DUR-preview_start)
run(['ffmpeg','-v','error','-ss',str(preview_start),'-i',instrumental,'-t',str(preview_duration),'-af',f'afade=t=in:d=0.03,afade=t=out:st={preview_duration-1}:d=1','-c:a','aac','-b:a','256k','-movflags','+faststart','-y',E/'Muestra_house_idea_a_video.m4a'])
if args.instrumental_only:
 report={'bpm':BPM,'duration':DUR,'seed':args.seed,'bass_instrument':False,'third_party_samples':False,
         'event_counts':dict(collections.Counter(e['kind'] for e in events)),
         'review':'instrumental generated; listening review pending'}
 (D/'eventos.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
 (E/'procedencia-instrumental.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report));raise SystemExit(0)

# Optional mix against the supplied picture and cleaned microphone stem.
bed=keys+drums
for a,b in P['bw_ranges']:
 depth=np.clip((t-a)/.04,0,1)*np.clip((b-t)/.1,0,1);bed*=1-.78*depth[:,None]
wav(D/'base-reel-cruda.wav',bed)
run(['ffmpeg','-v','error','-i',D/'base-reel-cruda.wav','-af',loudnorm(D/'base-reel-cruda.wav',-25,-7),'-ar',SR,'-c:a','pcm_s24le','-y',D/'base-reel.wav'])
voice=args.voice.resolve()
fc=f'[0:a]apad,atrim=duration={DUR},asplit=2[v][sc];[1:a][sc]sidechaincompress=threshold=0.05:ratio=2.7:attack=12:release=180[m];[v][m]amix=inputs=2:normalize=0:duration=first[a]'
run(['ffmpeg','-v','error','-i',voice,'-i',D/'base-reel.wav','-filter_complex',fc,'-map','[a]','-ar',SR,'-c:a','pcm_s24le','-y',D/'mezcla.wav'])
run(['ffmpeg','-v','error','-i',D/'mezcla.wav','-af',loudnorm(D/'mezcla.wav',-14,-3.5),'-ar',SR,'-c:a','pcm_s24le','-y',D/'master.wav'])
run(['ffmpeg','-v','error','-ss','7.333333333','-i',D/'master.wav','-t','32.7','-af','afade=t=out:st=32.5:d=0.2','-c:a','aac','-b:a','256k','-movflags','+faststart','-y',E/'Muestra_house_idea_a_video_con_tu_voz.m4a'])
source=args.picture.resolve()
video=E/'Idea_a_Video_con_voz.mp4'
run(['ffmpeg','-v','error','-i',source,'-i',D/'master.wav','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','256k','-t',DUR,'-movflags','+faststart','-y',video])
assert not any('bass' in e['kind'] for e in events)
metrics={}
for file in [E/'House_Idea_a_Video.m4a',E/'Muestra_house_idea_a_video.m4a',E/'Muestra_house_idea_a_video_con_tu_voz.m4a',video]:
 m=measure(file);metrics[file.name]={'lufs':float(m['input_i']),'true_peak':float(m['input_tp']),'lra':float(m['input_lra'])}
report={'style':'Idea to video: minimal Chicago-inspired organ house, no bass','bpm':BPM,'duration':DUR,'seed':args.seed,'bass_instrument':False,'sub_bass':False,'kick':'short percussive kick retained','instruments':'percussive organ stabs, woodblock, rim, swung hats, clap and short kick', 'piano_lead':False, 'groove':'122 BPM, sparse rootless chords with dotted stereo delay','minimum_keyboard_midi_note':min(e['note'] for e in events if e['note'] is not None),'third_party_samples':False,'event_counts':dict(collections.Counter(e['kind'] for e in events)),'voice_sha256':hashlib.sha256(voice.read_bytes()).hexdigest(),'picture':'Supplied video stream copied without re-encoding','bw_mix_dips':P['bw_ranges'],'metrics':metrics,'review':'technical measurements; subjective listening not performed'}
(E/'procedencia-y-revision.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(D/'eventos.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False),flush=True)
