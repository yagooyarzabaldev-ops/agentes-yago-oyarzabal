"""Compose an original electronic/big-beat cue and mix an unchanged voice input.

Usage: python scripts/musica_opciones/bigbeat.py --duration 34.066667
  --output-dir runtime/new-electronic --voice path/to/voice.wav
  --delivery-dir entregas/new-electronic --reference-note "Direction and review scope"

NumPy + local FFmpeg only. No samples, downloads, APIs or reproduced melodies.
The authored score uses middle-register filtered oscillators and short kick drums,
not sustained sub-bass. Outputs include events, stems, solo music, a voice master
and an audition with 8 seconds of music followed by the complete narration.
Omit --voice for an instrumental-only render. Output folders must be new or empty.
Measurement is technical evidence; the manifest never claims perceptual listening.
"""
from pathlib import Path
import argparse
import collections
import math
import shutil
import subprocess
import numpy as np

from _audio import duration as media_duration, ffmpeg, measure, new_directory, normalize, sha, strict_decode, write

SR = 48000


def noise(rng, count, low=900, high=5500):
    values = rng.normal(size=count)
    frequencies = np.fft.rfftfreq(count, 1 / SR)
    band = (1 - np.exp(-(frequencies / low)**4)) * np.exp(-(frequencies / high)**6)
    values = np.fft.irfft(np.fft.rfft(values) * band, n=count)
    return values / max(float(np.std(values)), .001)


def tone(kind, rng, note=60, gate=.2, openness=.4):
    length = gate + (.09 if kind == 'pulse' else .05)
    if kind == 'kick': length = .20
    if kind == 'snare': length = .17
    if kind in ('hat', 'tick'): length = .08
    if kind == 'air': length = .28
    t = np.arange(round(length * SR)) / SR
    hz = 440 * 2**((note - 69)/12)
    if kind == 'pulse':
        # Original gated oscillator: moving harmonic cutoff creates the filter sweep.
        cutoff = 240 + (850 + 3900 * openness) * np.exp(-6.8*t)
        signal = np.zeros(len(t))
        for harmonic in range(1, 25):
            frequency = hz * harmonic
            attenuation = 1 / (1 + (frequency / cutoff)**6)
            resonance = 1 + 1.10 * np.exp(-((frequency-.79*cutoff)/(.32*cutoff))**2)
            body = .48 if harmonic == 1 else 1.0
            signal += np.sin(2*np.pi*frequency*t + .06*harmonic) * attenuation * resonance * body / harmonic**.78
            signal += .22*np.sin(2*np.pi*frequency*1.0035*t+.09) * attenuation * body / harmonic**.85
        envelope = (1-np.exp(-620*t)) * (.80+.20*np.exp(-18*t))
        envelope *= np.exp(-38*np.maximum(t-gate, 0))
        signal = np.tanh(signal*1.08)*.78
    elif kind == 'stab':
        signal = np.zeros(len(t))
        for harmonic, gain in ((1,.65),(2,.25),(3,.16),(5,.04)):
            signal += gain*np.sin(2*np.pi*hz*harmonic*t)*np.exp(-harmonic*2*t)
        envelope = (1-np.exp(-300*t))*np.exp(-10*t)
    elif kind == 'kick':
        phase = 2*np.pi*(57*t + 1.0*(1-np.exp(-110*t)))
        signal = np.tanh(1.2*np.sin(phase)) + .075*noise(rng,len(t),700,2300)*np.exp(-135*t)
        envelope = (1-np.exp(-1700*t))*np.exp(-27*t)
    elif kind == 'snare':
        signal = .58*noise(rng,len(t),700,5100) + .28*np.sin(2*np.pi*205*t) + .13*np.sin(2*np.pi*360*t)
        envelope = (1-np.exp(-1500*t))*np.exp(-34*t)
    elif kind == 'hat':
        signal = noise(rng,len(t),2600,5800)
        envelope = (1-np.exp(-1400*t))*np.exp(-91*t)
    elif kind == 'tick':
        signal = np.sin(2*np.pi*1020*t)+.32*np.sin(2*np.pi*1680*t)
        envelope = (1-np.exp(-1700*t))*np.exp(-94*t)
    elif kind == 'air':
        signal = noise(rng,len(t),700,4200)
        envelope = np.sin(np.pi*np.minimum(t/length,1))**2 * np.exp(-7*t)
    else:
        raise ValueError(kind)
    envelope *= np.minimum(1,(length-t)/.012)
    return (signal*envelope).astype(np.float32)


def save_float(path, samples):
    if not np.isfinite(samples).all() or np.max(np.abs(samples)) >= 1:
        raise ValueError('Nonfinite samples or clipping before PCM export')
    result = subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-f','f32le','-ar',str(SR),
                             '-ac','2','-i','pipe:0','-c:a','pcm_s24le',str(path)],
                            input=samples.astype('<f4').tobytes(),capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8','replace'))


def read_float(path):
    raw = ffmpeg('-v','error','-i',path,'-ar',str(SR),'-ac','2','-f','f32le','-').stdout
    return np.frombuffer(raw,dtype='<f4').reshape(-1,2).copy()


def compose(output, seconds, bpm, seed):
    count = round(seconds*SR)
    beat = 60/bpm
    rng = np.random.default_rng(seed)
    stems = {name:np.zeros((count,2),np.float32) for name in ('drums','pulse','accents')}
    events = []
    # Section proportions retain the phrase shape when the requested duration changes.
    boundaries = [0, 1.875, 11.25, 16.875, 20.625, 30, 34.066666667]
    boundaries = [value*seconds/boundaries[-1] for value in boundaries]
    labels = ['entrada','groove','apertura','respiracion','regreso','cierre']

    def section(at):
        return min(5,next((i-1 for i,v in enumerate(boundaries) if v>at),6))

    def hit(at, kind, gain, pan=0, note=None, gate=.2, openness=.4):
        if at<0 or at>seconds-.4:return
        if note is not None and note<55:raise ValueError('Middle register starts at MIDI55')
        signal = tone(kind,rng,note or 60,gate,openness)
        start=round(at*SR);signal=signal[:count-start]
        target=stems['pulse' if kind=='pulse' else 'accents' if kind in ('stab','air') else 'drums']
        angle=(pan+1)*np.pi/4
        target[start:start+len(signal),0] += signal*gain*math.cos(angle)
        target[start:start+len(signal),1] += signal*gain*math.sin(angle)
        events.append({'seconds':round(at,6),'instrument':kind,'note_midi':note,
                       'gain':gain,'pan':pan,'gate':gate,'filter_openness':openness,'section':labels[section(at)]})

    # Own melodic sequences and rhythms: no transcription of a reference track.
    phrases = [
        [(0,57),(.75,64),(1.25,60),(2,57),(2.75,62),(3.5,64)],
        [(.25,57),(1,60),(1.75,67),(2.5,64),(3.25,62)],
        [(0,60),(.5,64),(1.5,62),(2.25,57),(3,60),(3.75,64)],
        [(.25,57),(1.25,62),(2,64),(2.75,60),(3.5,55)],
    ]
    for bar in range(math.ceil(seconds/(4*beat))):
        start=bar*4*beat
        current=section(start)
        kick_pattern=[0,1,2,3]
        if current==3:kick_pattern=[0,2.5]
        if current==0 and bar==0:kick_pattern=[0,2]
        for value in kick_pattern:hit(start+value*beat,'kick',.47)
        if current in (1,2,4,5):
            for value in (1,3):hit(start+value*beat,'snare',.19,.02)
            if bar%4==3:hit(start+2.75*beat,'kick',.20)
        if current!=0:
            for index in range(8):
                if current==3 and index not in (1,5):continue
                hit(start+(index*.5+(.025 if index%2 else 0))*beat,'hat',.055 if index%2 else .022,.32 if index%2 else -.22)
        if current in (2,4) and bar%2:
            for value in (1.75,3.25,3.75):hit(start+value*beat,'tick',.075,-.4)
        for index,(value,note) in enumerate(phrases[bar%4]):
            at=start+value*beat
            zone=section(at)
            if zone==3 and index not in (0,3):continue
            # Two-bar opening/closing is present from the first note, without a long intro.
            cycle=.5+.5*math.sin(2*np.pi*(at/(8*beat))-.2)
            openness=[.40,.32,.48,.21,.52,.30][zone]+.40*cycle
            openness=min(.96,openness)
            gain=.255 if zone in (0,1,2,4) else .19
            gate=.18 if zone!=3 else .25
            hit(at,'pulse',gain,(-.12 if index%2 else .12),note,gate,openness)
            if zone==4 and index in (1,4):hit(at+.375*beat,'pulse',.055,.42,note+12,.1,.35)
        if current in (1,2,4) and bar%2==0:
            for index,note in enumerate((69,72,76)):
                hit(start+1.5*beat+index*.003,'stab',.055,(index-1)*.45,note,.3)
        if current in (2,4) and bar%4==3:
            for index,value in enumerate((3.5,3.75)):
                hit(start+value*beat,'snare',.08+index*.025,(-1 if index%2 else 1)*.12)
    for index in (2,4,5):hit(boundaries[index],'air',.09,-.18)
    # No long reverberant bed. A short reflection keeps synth attacks wider than kick.
    delay=round(.041*SR)
    stems['pulse'][delay:] += stems['pulse'][:-delay,::-1].copy()*.09
    raw_peak=max(1.,*(float(np.abs(v).max()) for v in stems.values()))
    for name,data in stems.items():
        raw=output/f'{name}_raw.wav';filtered=output/f'{name}.wav'
        save_float(raw,data*.80/raw_peak)
        filt='highpass=f=43,lowpass=f=6500' if name=='drums' else 'highpass=f=155,lowpass=f=5100,equalizer=f=2100:t=q:w=0.9:g=-1.5'
        ffmpeg('-v','error','-n','-i',raw,'-af',filt,'-c:a','pcm_s24le',filtered)
        stems[name]=read_float(filtered)
    mix=sum(stems.values())
    # Modest saturation catches simultaneous percussion transients before mastering.
    mix=np.tanh(mix*1.25)/1.25
    mix*=.76/max(float(np.abs(mix).max()),.001)
    fade=np.ones(count)
    fade[:round(.008*SR)]=np.linspace(0,1,round(.008*SR))
    fade[-round(.42*SR):]=np.linspace(1,0,round(.42*SR))**1.3
    mix*=fade[:,None]
    source=output/'electronica_original.wav'
    save_float(source,mix)
    write(output/'eventos.json',events)
    return {'file':source.name,'sha256':sha(source),'bpm':bpm,'seed':seed,'duration_seconds':count/SR,
            'sections':[{'name':label,'start':boundaries[i],'end':boundaries[i+1]} for i,label in enumerate(labels)],
            'event_count':len(events),'instrument_counts':dict(collections.Counter(e['instrument'] for e in events)),
            'minimum_tonal_midi':min(e['note_midi'] for e in events if e['note_midi'] is not None),
            'score_scope':'Original phrases, beats and synthesis; no reference recording, samples, lyrics or copied riff.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--delivery-dir',type=Path)
    parser.add_argument('--duration',type=float,required=True)
    parser.add_argument('--voice',type=Path)
    parser.add_argument('--bpm',type=float,default=128)
    parser.add_argument('--seed',type=int,default=281128)
    parser.add_argument('--music-gain',type=float,default=.20,help='Linear instrumental gain before voice-triggered ducking.')
    parser.add_argument('--reference-note',default='Direction supplied by user; reference not perceptually inspected.')
    parser.add_argument('--reference-audio',type=Path,help='Local reference metadata only; never sampled or incorporated into the score.')
    parser.add_argument('--sample-start',type=float,default=8)
    parser.add_argument('--sample-duration',type=float,default=8)
    args=parser.parse_args(argv)
    numbers=[args.duration,args.bpm,args.music_gain,args.sample_start,args.sample_duration]
    if not all(math.isfinite(value) for value in numbers):parser.error('All numerical arguments must be finite')
    if not 2<=args.duration<=180 or not 80<=args.bpm<=160:parser.error('Duration2–180s and BPM80–160 required')
    if not .01<=args.music_gain<=.8:parser.error('--music-gain must be between0.01 and0.8')
    if args.sample_start<0 or args.sample_duration<=0 or args.sample_start+args.sample_duration>args.duration:
        parser.error('Solo sample must fit within the instrumental')
    voice_hash=sha(args.voice) if args.voice else None
    if args.voice and media_duration(args.voice)>args.duration+1/SR:parser.error('Duration would truncate the voice')
    if args.delivery_dir:
        if args.delivery_dir.resolve()==args.output_dir.resolve():parser.error('Delivery and work directories must differ')
        if args.delivery_dir.exists() and any(args.delivery_dir.iterdir()):parser.error('Delivery directory must be new or empty')
    output=new_directory(args.output_dir);logs=output/'logs';logs.mkdir()
    score=compose(output,args.duration,args.bpm,args.seed)
    source=output/score['file'];music=output/'Electronica_original_instrumental.wav'
    music_metrics=normalize(source,music,-16.5,-3,logs)
    mp3=output/'Electronica_original_instrumental.mp3'
    ffmpeg('-v','error','-n','-i',music,'-c:a','libmp3lame','-b:a','256k',mp3)
    deliveries=[music,mp3]
    manifest={'schema_version':1,'score':score,'reference_note':args.reference_note,'voice_sha256':voice_hash,
              'source_voice_unchanged':None,'instrumental_metrics':music_metrics,
              'style_scope':'Direction for this piece only; global baseline is not modified.',
              'third_party_samples':False,'perceptual_listening':False,'script_sha256':sha(Path(__file__)),
              'limitations':['No listening or claimed perceptual match to a reference.','No sustained sub-bass oscillator; short kick transients contain low frequencies.']}
    if args.reference_audio:
        manifest['local_reference']={'name':args.reference_audio.name,'sha256':sha(args.reference_audio),
                                     'container_seconds':media_duration(args.reference_audio),
                                     'scope':'Complete excerpt supplied by user, no seek40; numerical analysis only, no perceptual audition.',
                                     'reference_audio_in_score':False}
    synth_full=output/'sinte_solo_normalizado.wav'
    normalize(output/'pulse.wav',synth_full,-16.5,-3.3,logs)
    synth_sample=output/'Sinte_filtrado_solo.wav'
    synth_mp3=output/'Sinte_filtrado_solo.mp3'
    synth_seconds=min(8,args.duration)
    ffmpeg('-v','error','-n','-i',synth_full,'-t',synth_seconds,'-c:a','pcm_s24le',synth_sample)
    ffmpeg('-v','error','-n','-i',synth_sample,'-c:a','libmp3lame','-b:a','256k',synth_mp3)
    manifest['synth_only_preview']={'start':0,'seconds':synth_seconds,'description':'Only original middle-register synth; two-bar filter movement plus note-envelope opening/closing, no drums or voice.'}
    deliveries += [synth_sample,synth_mp3]
    if args.voice:
        raw=output/'mezcla_cruda.wav'
        graph=(f'[0:a]apad,atrim=duration={args.duration},asplit=2[v][sc];'
               f'[1:a]volume={args.music_gain}[m];'
               '[m][sc]sidechaincompress=threshold=0.035:ratio=4:attack=8:release=170[duck];'
               '[v][duck]amix=inputs=2:normalize=0:duration=first[a]')
        ffmpeg('-v','error','-n','-i',args.voice,'-i',music,'-filter_complex',graph,'-map','[a]',
               '-ar',str(SR),'-ac','2','-c:a','pcm_s24le',raw)
        master=output/'Electronica_original_master.wav'
        manifest['master_metrics']=normalize(raw,master,-14,-2.7,logs)
        manifest['mix_method']={'music_gain':args.music_gain,'master_target_lufs':-14,'master_peak_ceiling_dbtp':-2.7,
                                'ducking':{'threshold':.035,'ratio':4,'attack_ms':8,'release_ms':170}}
        audition=output/'Electronica_original_comparacion.mp3'
        fade=min(.25,args.sample_duration/3)
        graph=(f'[0:a]atrim=start={args.sample_start}:duration={args.sample_duration},asetpts=PTS-STARTPTS,'
               f'afade=t=in:d=0.015,afade=t=out:st={args.sample_duration-fade}:d={fade}[solo];'
               'anullsrc=r=48000:cl=stereo,atrim=duration=0.3[gap];'
               '[1:a]asetpts=PTS-STARTPTS[voice];[solo][gap][voice]concat=n=3:v=0:a=1[a]')
        ffmpeg('-v','error','-n','-i',music,'-i',master,'-filter_complex',graph,'-map','[a]',
               '-ar',str(SR),'-c:a','libmp3lame','-b:a','256k',audition)
        manifest['audition']={'solo_start':args.sample_start,'solo_seconds':args.sample_duration,'gap_seconds':.3,
                              'complete_mix_seconds':args.duration,'file':audition.name}
        deliveries += [master,audition]
        manifest['source_voice_unchanged']=sha(args.voice)==voice_hash
        if not manifest['source_voice_unchanged']:raise RuntimeError('Voice input changed during rendering')
    manifest['artifacts']={}
    for path in deliveries:
        strict_decode(path,logs/(path.stem+'-strict-decode.log'))
        metrics=measure(path,log=logs/(path.stem+'-final-measure.log'))
        manifest['artifacts'][path.name]={'sha256':sha(path),'bytes':path.stat().st_size,'duration_seconds':media_duration(path),
                                        'lufs':float(metrics['input_i']),'true_peak_dbtp':float(metrics['input_tp']),
                                        'strict_decode_passed':True}
        if float(metrics['input_tp'])>=-2:raise RuntimeError(f'Encoded audio peak exceeds ceiling: {path.name}')
        if path.name=='Electronica_original_master.wav' and abs(float(metrics['input_i'])+14)>.7:
            raise RuntimeError('Master loudness differs from the -14 LUFS target')
    manifest_path=output/'procedencia-y-mezcla.json';write(manifest_path,manifest)
    if args.delivery_dir:
        delivery=new_directory(args.delivery_dir)
        for path in deliveries+[manifest_path]:shutil.copy2(path,delivery/path.name)
    print('COMPLETE',flush=True)
    for name,metrics in manifest['artifacts'].items():print(name,metrics,flush=True)


if __name__=='__main__':
    main()
