"""Three original instrumental scores, locally synthesized without samples.
Usage: python scripts/musica_opciones/componer.py --output-dir runtime/new-score --duration 65
Activate the project's tools first. NumPy and FFmpeg are required, without installs.
A: warm electric keys118BPM. B: organic percussion114BPM. C: soft plucks124BPM.
Fixed seeds reproduce each score; changing duration does not invent a new score.
No production runs or file writes occur on import or --help.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import math
import subprocess
import wave
import numpy as np

SR = 48000


def wavwrite(path, data):
    data = np.asarray(data)
    assert np.isfinite(data).all() and abs(data).max() < 1
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(np.round(data * 32767).astype('<i2').tobytes())


def wavread(path):
    with wave.open(str(path), 'rb') as f:
        assert f.getframerate() == SR and f.getnchannels() == 2
        return np.frombuffer(f.readframes(f.getnframes()), '<i2').reshape(-1, 2) / 32768.


def ffmpeg(*args):
    return subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', *map(str, args)],
                          capture_output=True, text=True, check=True)


def smooth_noise(rng, count, low=700, high=6500):
    noise = rng.normal(0, 1, count)
    freq = np.fft.rfftfreq(count, 1 / SR)
    shape = (1 - np.exp(-(freq / low) ** 4)) * np.exp(-(freq / high) ** 6)
    result = np.fft.irfft(np.fft.rfft(noise) * shape, n=count)
    return result / max(np.std(result), .001)


def synth(kind, note=72, duration=.4, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(round(duration * SR)) / SR
    hz = 440 * 2 ** ((note - 69) / 12)
    if kind == 'rhodes':
        # Soft electric tine: decaying FM strike, then almost sinusoidal body.
        phase = 2 * np.pi * hz * t
        x = (.76 * np.sin(phase + .36 * np.exp(-8*t) * np.sin(2*phase))
             + .13 * np.sin(2*phase + .2) * np.exp(-7*t)
             + .035 * np.sin(3.996*phase) * np.exp(-16*t))
        env = np.exp(-3.1*t) * (1-np.exp(-420*t))
    elif kind == 'marimba':
        x = np.sin(2*np.pi*hz*t) + .24*np.sin(2*np.pi*2.756*hz*t)*np.exp(-20*t)
        env = np.exp(-8.5*t) * (1-np.exp(-650*t))
    elif kind == 'pluck':
        phase = 2*np.pi*hz*t
        x = np.sin(phase) + .22*np.sin(2*phase)*np.exp(-12*t) + .06*np.sin(3*phase)*np.exp(-20*t)
        env = np.exp(-11*t) * (1-np.exp(-500*t))
    elif kind == 'airchord':
        x = .7*np.sin(2*np.pi*hz*t) + .24*np.sin(2*np.pi*hz*1.002*t)
        env = (1-np.exp(-32*t))*np.exp(-8*t)
    elif kind in ('kick_warm', 'kick_organic', 'kick_dry'):
        decay = {'kick_warm': 27, 'kick_organic': 34, 'kick_dry': 44}[kind]
        bottom = {'kick_warm': 70, 'kick_organic': 82, 'kick_dry': 86}[kind]
        phase = 2*np.pi*(bottom*t + 1.4*(1-np.exp(-60*t)))
        x = np.sin(phase) + .07*smooth_noise(rng, len(t), 600, 2200)*np.exp(-120*t)
        env = (1-np.exp(-1500*t))*np.exp(-decay*t)
    elif kind == 'clap':
        x = smooth_noise(rng, len(t), 650, 4800)
        env = np.zeros(len(t))
        for delay, amp, decay in [(0, .6, 180), (.012, .5, 150), (.024, .9, 44)]:
            local = t-delay
            env += np.where(local >= 0, amp*np.exp(-decay*np.maximum(local, 0)), 0)
        env *= (1-np.exp(-1800*t))
    elif kind == 'snare_dry':
        x = .66*smooth_noise(rng, len(t), 1000, 4500) + .35*np.sin(2*np.pi*320*t)
        env = (1-np.exp(-1500*t))*np.exp(-51*t)
    elif kind in ('hat', 'shaker'):
        x = smooth_noise(rng, len(t), 2400 if kind == 'hat' else 1300, 6200 if kind == 'hat' else 4700)
        env = (1-np.exp(-700*t))*np.exp(-(85 if kind == 'hat' else 47)*t)
    elif kind == 'wood':
        x = np.sin(2*np.pi*940*t) + .32*np.sin(2*np.pi*1585*t)
        env = (1-np.exp(-1800*t))*np.exp(-79*t)
    elif kind in ('conga_low', 'conga_high'):
        hz = 207 if kind == 'conga_low' else 282
        x = .72*np.sin(2*np.pi*(hz*t+.23*(1-np.exp(-75*t)))) + .22*np.sin(2*np.pi*hz*1.49*t)
        x += .10*smooth_noise(rng, len(t), 650, 2800)*np.exp(-75*t)
        env = (1-np.exp(-1100*t))*np.exp(-26*t)
    else:
        raise ValueError(kind)
    release = np.minimum(1, (duration-t)/.018)
    return (x * env * release).astype(np.float32)


class Score:
    def __init__(self, key, name, bpm, seed, output_dir, duration):
        self.out = Path(output_dir)
        self.duration = duration
        self.n = round(duration * SR)
        self.key, self.name, self.bpm = key, name, bpm
        self.beat = 60/bpm
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.music = np.zeros((self.n,2), np.float32)
        self.drums = np.zeros((self.n,2), np.float32)
        self.events = []

    def hit(self, beat, kind, gain, pan=0, note=None, duration=None):
        at = beat*self.beat
        if at < 0 or at > self.duration-.72:
            return
        melodic = note is not None
        if melodic:
            assert note >= 60, 'No bass-register melodic notes'
        length = duration or ({'rhodes': .90, 'marimba': .43, 'pluck': .34, 'airchord': .43}.get(kind, .24))
        signal = synth(kind, note or 72, length, int(self.rng.integers(1, 1000000)))
        offset = round(at*SR)
        signal = signal[:self.n-offset]
        left, right = math.cos((pan+1)*np.pi/4), math.sin((pan+1)*np.pi/4)
        target = self.music if melodic else self.drums
        target[offset:offset+len(signal), 0] += signal*gain*left
        target[offset:offset+len(signal), 1] += signal*gain*right
        self.events.append({'seconds': round(at,6), 'beat': beat, 'instrument': kind,
                            'note_midi': note, 'gain': gain, 'pan': pan, 'length': length})

    def chord(self, beat, notes, kind='rhodes', gain=.13, duration=None):
        for i, note in enumerate(notes):
            self.hit(beat + .007*i, kind, gain, (i/(len(notes)-1)-.5)*.8, note, duration)

    def finish(self, arrangement):
        folder = self.out/self.key
        folder.mkdir(exist_ok=True)
        # Low-level early reflections add width without long reverb or a pad.
        for delay, gain in ((.039, .10), (.077, .065)):
            d = round(delay*SR)
            self.music[d:] += self.music[:-d, ::-1].copy()*gain
        initial_peak = max(float(abs(self.music).max()), float(abs(self.drums).max()), 1.)
        for name, data in [('tonal',self.music),('percusion',self.drums)]:
            wavwrite(folder/f'{name}_raw.wav', data/initial_peak*.8)
            filt = 'highpass=f=235,lowpass=f=6500' if name == 'tonal' else 'highpass=f=48,lowpass=f=6800'
            ffmpeg('-y','-i', folder/f'{name}_raw.wav','-af',filt,'-c:a','pcm_s16le',folder/f'{name}.wav')
        tonal, drums = wavread(folder/'tonal.wav'), wavread(folder/'percusion.wav')
        mix = tonal + drums
        fade = np.ones(self.n)
        a,b = round(.012*SR), round(.75*SR)
        fade[:a] = np.linspace(0,1,a)
        fade[-b:] = np.linspace(1,0,b)**1.25
        mix *= fade[:,None]
        scale = .70 / max(float(abs(mix).max()),.0001)
        mix *= scale
        final = self.out/self.name
        temp = folder/'mix_pcm16.wav'
        wavwrite(temp,mix)
        ffmpeg('-y','-i',temp,'-c:a','pcm_s24le',final)
        measurement = ffmpeg('-i',final,'-af','loudnorm=I=-16.5:TP=-3:LRA=9:print_format=json','-f','null','-')
        loudness, _ = json.JSONDecoder().raw_decode(measurement.stderr[measurement.stderr.rfind('{'):])
        probe = subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(final)], capture_output=True,text=True,check=True)
        counts = dict(collections.Counter(e['instrument'] for e in self.events))
        notes = [e['note_midi'] for e in self.events if e['note_midi'] is not None]
        result = {'id':self.key,'file':self.name,'bpm':self.bpm,'duration_seconds':self.duration,
                  'sample_rate':SR,'channels':2,'peak_dbfs':20*math.log10(float(abs(mix).max())),
                  'rms_dbfs':20*math.log10(float(np.sqrt(np.mean(mix**2)))),
                  'integrated_lufs':float(loudness['input_i']),'true_peak_dbtp':float(loudness['input_tp']),
                  'lra_lu':float(loudness['input_lra']),'events':len(self.events),'instrument_counts':counts,
                  'minimum_pitched_midi':min(notes),'maximum_pitched_midi':max(notes),
                  'seed':self.seed,'arrangement':arrangement,'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),
                  'technical_decode':'FFmpeg complete decode and loudness analysis succeeded',
                  'listening_status':'No perceptual listening performed; numerical checks only'}
        (folder/'eventos.json').write_text(json.dumps(self.events,indent=2,ensure_ascii=False),encoding='utf-8')
        (folder/'ffprobe.json').write_text(probe.stdout,encoding='utf-8')
        (folder/'mediciones.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False),flush=True)
        return result


def option_a(output_dir, duration):
    s = Score('A','A_house_calido.wav',118,118211,output_dir,duration)
    chords = [[64,69,72,79],[65,69,72,76],[62,65,69,74],[64,67,72,77]]
    for bar in range(math.ceil(duration / (4*s.beat))):
        base=4*bar
        breath = bar in (8,)
        for beat in ([0,2] if bar==0 else ([0] if breath else [0,1,2,3])):
            s.hit(base+beat,'kick_warm',.46)
        if bar>0 and not breath:
            for beat in [1,3]: s.hit(base+beat,'clap',.15, .08)
        if bar>0:
            for i in range(8):
                if breath and i not in (1,5): continue
                s.hit(base+i*.5+(.075 if i%2 else 0),'hat',.055 if i%2 else .023,(-.28 if i%2 else .2))
        pattern = [[.25,2.75],[.75,2.5],[.25,1.75,3.25],[.75,2.75]][bar%4]
        if breath: pattern=[.25]
        for j,beat in enumerate(pattern):
            s.chord(base+beat,chords[bar%4],gain=.112 if j==0 else .086,duration=1.05 if breath else .85)
        if bar in (3,7,11,15):
            for b,n in zip([3,3.5],[79,76]):s.hit(base+b,'rhodes',.073,.25,n,.48)
        if bar%4==3 and not breath:s.hit(base+3.75,'wood',.05,-.32)
    return s.finish('Teclas electricas de ataque suave; armonia Fmaj9/Dm9/Bbmaj9/Csus sin raiz grave. Entrada con bombo espaciado; cuatro al piso, clap suave y hats con swing; respiracion en compas 9, vuelta y cierre fundido. Sin piano lider ni bajo.')


def option_b(output_dir, duration):
    s = Score('B','B_groove_organico.wav',114,114221,output_dir,duration)
    harmony=[[63,67,70,74],[65,69,72,75],[62,67,70,74],[65,70,74,77]]
    for bar in range(math.ceil(duration / (4*s.beat))):
        base=4*bar
        breath=bar==7
        for beat in ([0] if breath or bar==0 else ([0,1.75,2.5] if bar%2==0 else [0,2.25,3.5])):
            s.hit(base+beat,'kick_organic',.39)
        woods = [0,1.5,3] if bar%2==0 else [.75,2,3.5]
        for beat in woods:s.hit(base+beat,'wood',.16,-.38)
        if bar>0 and not breath:
            for j,beat in enumerate([.75,1.25,2.75,3.25] if bar%2==0 else [.5,1.75,2.5,3.75]):
                s.hit(base+beat,'conga_low' if j%2==0 else 'conga_high',.19 if j%2==0 else .14,.22 if j%2==0 else .44)
        for i in range(16):
            if i%4==2 or (breath and i%4!=3):continue
            s.hit(base+i*.25+(.026 if i%2 else 0),'shaker',.033 if i%2 else .023,-.15 if i%2 else .12)
        if bar%2==0:
            s.chord(base+.5,harmony[(bar//2)%4],'marimba',.105,.48)
            s.chord(base+2.75,harmony[(bar//2)%4][::-1],'marimba',.074,.4)
        else:
            for beat,note in zip([.25,1.5,3], [74,77,75] if bar%4==1 else [79,77,74]):
                s.hit(base+beat,'marimba',.125,.18,note,.5)
        if bar in (3,11,15):
            for j,b in enumerate([3.25,3.5,3.75]):s.hit(base+b,'conga_high',.10+j*.012,.35)
    return s.finish('Groove quebrado a 114 BPM con congas sintetizadas de 207/282 Hz, madera en tresillo alternado y shaker discreto. Marimba suave responde en compases alternos; respiracion en compas 8, fills de conga al cerrar frases. Sin cuatro al piso continuo ni bajo.')


def option_c(output_dir, duration):
    s = Score('C','C_minimal_electronico.wav',124,124231,output_dir,duration)
    motifs=[[69,76,72],[67,74,79],[72,79,76],[71,74,81]]
    for bar in range(math.ceil(duration / (4*s.beat))):
        base=4*bar
        breath=bar in (8,9)
        for beat in ([0] if breath else [0,1,2,3]):s.hit(base+beat,'kick_dry',.42)
        if bar>0 and not breath:
            for beat in [1,3]:s.hit(base+beat,'snare_dry',.125)
        if bar>1 and not breath:
            for beat in [.5,1.5,2.5,3.5]:s.hit(base+beat,'hat',.054,.30)
            if bar%2:s.hit(base+3.75,'hat',.025,-.25)
        pattern=[.75,1.5,2.75] if bar%2==0 else [.25,2.25,3.5]
        if breath:pattern=[.75,2.75]
        notes=motifs[bar%4]
        for j,beat in enumerate(pattern):
            s.hit(base+beat,'pluck',.215 if j==0 else .17,[-.32,.24,.08][j],notes[j],.40)
            if bar>3 and not breath:
                s.hit(base+beat+.75,'pluck',.055,-[-.32,.24,.08][j],notes[j],.27)
        if bar%2==0:
            s.chord(base+.125,[72,76,79] if bar%4==0 else [71,74,79],'airchord',.069,.55)
        if bar%4==3:s.hit(base+3.25,'wood',.07,-.32)
    return s.finish('Pluck electronico breve en registro G4-A5, motivo sincopado de tres notas que cambia respuesta cada compas. Bombo corto, caja seca, hats contenidos; ecos discretos solo en desarrollo. Dos compases de espacio central y regreso con figuras nuevas. Sin subgrave sostenido ni bajo.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output-dir', type=Path, required=True, help='New or empty local output directory; audio stays outside Git.')
    parser.add_argument('--duration', type=float, required=True, help='Exact score duration in seconds, from 2 to 180.')
    parser.add_argument('--options', nargs='+', choices=['A','B','C'], default=['A','B','C'])
    parser.add_argument('--tempo-reason', default='Explicit exploration of alternative arrangements.', help='Reason for exploring 118/114/124 BPM instead of the project baseline.')
    args=parser.parse_args(argv)
    if not math.isfinite(args.duration) or not 2 <= args.duration <= 180:
        parser.error('--duration must be finite and between 2 and 180 seconds')
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error('--output-dir must be empty to preserve existing artifacts')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    recipes={'A':option_a,'B':option_b,'C':option_c}
    results=[recipes[key](args.output_dir,args.duration) for key in dict.fromkeys(args.options)]
    manifest={
        'schema_version':1, 'duration_seconds':args.duration,
        'tempo_reason':args.tempo_reason,
        'origin':'Original mathematical synthesis and authored A/B/C scores: NumPy oscillators and filtered noise. No recordings, samples, APIs or external services.',
        'method':'48 kHz stereo PCM24; tonal highpass235Hz; percussion highpass48Hz; lowpass6500/6800Hz. Short fades and fixed seeds. No bass instrument events; low-frequency kick transients remain.',
        'limitations':'No perceptual audition. These are three reusable scores, not automatic composition from a narration. Durations extend or trim their phrases; review musical endings and longer arrangements.',
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'options':results}
    (args.output_dir/'procedencia.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Complete: original scores, stems, events and provenance.',flush=True)


if __name__ == '__main__':
    main()
