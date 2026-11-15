"""Original upbeat funk/electronic groove, deterministic synthesis, no sampled recordings."""
import math,wave
import numpy as np
def build_score(P,path):
 rate=48000;dur=P['duration'];n=math.ceil(dur*rate);track=np.zeros((n,2));rng=np.random.default_rng(141128)
 def hit(at,length,freq,gain,kind,pan=0):
  off=round(at*rate);count=min(round(length*rate),n-off)
  if off<0 or count<1:return
  t=np.arange(count)/rate;u=t/length
  if kind=='bass':
   phase=2*np.pi*freq*(t+.0007*(1-np.exp(-t*22)))
   raw=np.sin(phase)+.27*np.sin(2*phase)+.12*np.sin(3*phase)
   y=np.tanh(raw*1.2)*np.minimum(t/.006,1)*np.minimum((length-t)/.055,1)*np.exp(-t*1.5)
  elif kind=='rhodes':
   mod=1.1*np.exp(-t*9)*np.sin(2*np.pi*freq*2.001*t)
   y=(np.sin(2*np.pi*freq*t+mod)+.2*np.sin(2*np.pi*freq*3*t))*np.minimum(t/.004,1)*np.exp(-t*5)*np.minimum((length-t)/.07,1)
  elif kind=='kick':
   y=(np.sin(2*np.pi*(48*t+2.1*(1-np.exp(-t*32))))+.12*rng.uniform(-1,1,count)*np.exp(-t*170))*np.exp(-t*20)
  elif kind=='clap':
   noise=rng.uniform(-1,1,count);noise=noise-np.roll(noise,1)
   env=sum(np.where(t>=d,np.exp(-np.maximum(t-d,0)*r),0) for d,r in [(0,260),(.012,230),(.026,38)])
   y=.55*noise*env+.12*np.sin(2*np.pi*190*t)*np.exp(-t*40)
  elif kind=='hat':
   noise=rng.uniform(-1,1,count);y=(noise-np.roll(noise,1))*.45*np.exp(-t*(80 if length>.09 else 160))
  elif kind=='rim':y=(np.sin(2*np.pi*780*t)+.45*np.sin(2*np.pi*1730*t))*np.exp(-t*85)
  elif kind=='pop':y=np.sin(2*np.pi*(freq*t+150*t*t))*np.exp(-t*32)
  elif kind=='whoosh':y=np.convolve(rng.uniform(-1,1,count),np.ones(7)/7,mode='same')*np.sin(np.pi*u)**2
  else:y=np.sin(2*np.pi*freq*t)*np.minimum(t/.08,1)*np.minimum((length-t)/.4,1)*.6
  track[off:off+count,0]+=gain*y*math.cos((pan+1)*math.pi/4)
  track[off:off+count,1]+=gain*y*math.sin((pan+1)*math.pi/4)
 beat=60/114
 # Am7 / Fmaj7 / Cmaj7 / Gadd9: a light syncopated groove under the spoken track.
 roots=[110,87.307,130.813,97.999]
 chords=[[220,261.626,329.628,391.995],[174.614,220,261.626,329.628],
         [196,261.626,329.628,493.883],[195.998,246.942,293.665,440]]
 bars=math.ceil(P['voice_end']/(beat*4))
 for bar in range(bars):
  at=bar*4*beat;root=roots[(bar//2)%4];ch=chords[(bar//2)%4]
  # Brief arrangement changes prevent a static loop.
  energy=.80 if (bar//4)%3==1 else 1
  for p in [0,1.5,2,3.25]:hit(at+p*beat,.29,48,.16*energy,'kick')
  for p in [1,3]:hit(at+p*beat,.18,0,.075*energy,'clap',.08)
  for k in range(16):
   swing=.025 if k%2 else 0
   hit(at+(k/4+swing)*beat,.055 if k%4!=2 else .11,0,(.018 if k%4==0 else .011 if k%2 else .015)*energy,'hat',-.4 if k%2 else .4)
  bass=[(0,root,.42),(.75,root,.18),(1.5,root*1.5,.22),(2,root,.35),(2.75,root*2,.20),(3.5,root*1.5,.18)]
  for p,f,length in bass:hit(at+p*beat,length,f,.10,'bass',0)
  for p in [.5,1.75,2.5,3.5]:
   for i,f in enumerate(ch):hit(at+p*beat+i*.009,.45,f,.020,'rhodes',-.5+i/3)
  if bar%2:hit(at+3.75*beat,.09,780,.04,'rim',-.25)
  if bar%4==3:
   for j in range(3):hit(at+(3.5+j*.17)*beat,.07,800+j*160,.025,'rim',-.4+j*.4)
 # Graphic cuts get short UI-like pops rather than a constant wash of effects.
 for i,s in enumerate(P['shots']):
  if s['view']!='camera':hit(s['start']+.02,.12,500+(i%4)*110,.035,'pop',-.3 if i%2 else .3)
  if s['view'] in ['wires','oops','agent']:hit(max(0,s['start']-.1),.24,0,.12,'whoosh',-.5 if i%2 else .5)
 end=P['voice_end']
 hit(end,.28,48,.17,'kick')
 for i,f in enumerate([110,220,261.626,329.628,391.995]):hit(end+i*.012,dur-end-i*.012,f,.038,'rhodes',-.5+i*.25)
 t=np.arange(n)/rate;track*=np.minimum(t/.06,1)[:,None]*np.clip((dur-t)/.45,0,1)[:,None]
 # A light soft clip rounds drum transients before loudness normalization.
 track=np.tanh(track*1.15)/1.15
 with wave.open(str(path),'wb') as f:
  f.setparams((2,2,rate,0,'NONE','not compressed'));f.writeframes((np.clip(track,-.96,.96)*32767).astype('<i2').tobytes())
