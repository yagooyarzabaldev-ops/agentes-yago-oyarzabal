"""Measure a complete local reference and an optional original cue, without listening claims.

Usage: python scripts/musica_opciones/analizar_referencia.py --reference local.mp3
  --proposal original.wav --output runtime/audio-analysis.json

The reference is always decoded in full. Only the proposal may use --proposal-start
and --proposal-duration for a comparable excerpt. Reports FFT energy bands, onset
periodicity candidates, spectral motion, dynamics and hashes. No pitch transcription,
samples, network calls or reference audio are written into the generated cue.
"""
from pathlib import Path
import argparse
import math
import numpy as np

from _audio import ffmpeg, measure, sha, write

RATE = 24000
BANDS = [(20,80),(80,160),(160,400),(400,1200),(1200,3500),(3500,7000),(7000,12000)]


def analyze(path, start=0, seconds=None):
    args=['-v','error','-i',path,'-vn']
    if start or seconds:
        args+=['-af',f'atrim=start={start}'+(f':duration={seconds}' if seconds is not None else '')]
    decoded=ffmpeg(*args,'-ac','1','-ar',str(RATE),'-f','f32le','-').stdout
    samples=np.frombuffer(decoded,'<f4').astype(float)
    if len(samples)<RATE or not np.isfinite(samples).all():raise ValueError('At least one second of finite audio required')
    window,hop=2048,256
    frames=np.lib.stride_tricks.sliding_window_view(samples,window)[::hop]
    spectrum=np.abs(np.fft.rfft(frames*np.hanning(window),axis=1))
    power=spectrum*spectrum
    frequencies=np.fft.rfftfreq(window,1/RATE)
    average_power=np.mean(power,axis=0)
    total=max(float(np.sum(average_power)),1e-15)
    bands={f'{low}-{high}Hz':100*float(average_power[(frequencies>=low)&(frequencies<high)].sum())/total for low,high in BANDS}
    rms=float(np.sqrt(np.mean(samples*samples)))
    peak=float(np.max(np.abs(samples)))
    centroid=(spectrum*frequencies[None,:]).sum(axis=1)/np.maximum(spectrum.sum(axis=1),1e-15)
    middle=(frequencies>=160)&(frequencies<=3500)
    middle_centroid=(spectrum[:,middle]*frequencies[middle]).sum(axis=1)/np.maximum(spectrum[:,middle].sum(axis=1),1e-15)
    # Log-magnitude positive spectral flux captures attacks without transcribing notes.
    active=(frequencies>=60)&(frequencies<=6000)
    compressed=np.log1p(spectrum[:,active]*8)
    flux=np.maximum(np.diff(compressed,axis=0),0).sum(axis=1)
    flux-=np.mean(flux)
    fft_length=1<<(2*len(flux)-1).bit_length()
    autocorrelation=np.fft.irfft(np.abs(np.fft.rfft(flux,n=fft_length))**2,n=fft_length)[:len(flux)]
    autocorrelation/=np.maximum(1,np.arange(len(flux),0,-1))
    autocorrelation/=max(float(autocorrelation[0]),1e-15)
    frame_rate=RATE/hop
    lower=round(60*frame_rate/160);upper=round(60*frame_rate/85)
    peaks=[lag for lag in range(lower+1,min(upper,len(flux)-1))
           if autocorrelation[lag]>=autocorrelation[lag-1] and autocorrelation[lag]>autocorrelation[lag+1]]
    candidates=[]
    for lag in sorted(peaks,key=lambda value:autocorrelation[value],reverse=True):
        estimate=60*frame_rate/lag
        if all(abs(estimate-item['bpm'])>3 for item in candidates):
            candidates.append({'bpm':round(estimate,2),'onset_periodicity_strength':round(float(autocorrelation[lag]),4)})
        if len(candidates)==5:break
    per_second=[]
    for second in range(math.ceil(len(samples)/RATE)):
        block=samples[second*RATE:(second+1)*RATE]
        if not len(block):continue
        mask=(np.arange(len(frames))*hop/RATE>=second)&(np.arange(len(frames))*hop/RATE<second+1)
        per_second.append({'second':second,'rms_dbfs':20*math.log10(max(float(np.sqrt(np.mean(block*block))),1e-15)),
                           'spectral_centroid_hz':float(np.median(centroid[mask])) if np.any(mask) else None,
                           'middle_centroid_hz':float(np.median(middle_centroid[mask])) if np.any(mask) else None})
    loudness=measure(path,start=start,seconds=seconds)
    return {'source_name':Path(path).name,'sha256':sha(path),'decoded_seconds':len(samples)/RATE,
            'analyzed_start':start,'analyzed_duration':seconds,'rms_dbfs':20*math.log10(max(rms,1e-15)),
            'sample_peak_dbfs':20*math.log10(max(peak,1e-15)),'crest_db':20*math.log10(max(peak/rms,1e-15)),
            'integrated_lufs':float(loudness['input_i']),'true_peak_dbtp':float(loudness['input_tp']),
            'energy_band_percent':bands,'spectral_centroid_percentiles_hz':dict(zip(['p10','p50','p90'],np.percentile(centroid,[10,50,90]).tolist())),
            'middle_centroid_percentiles_hz':dict(zip(['p10','p50','p90'],np.percentile(middle_centroid,[10,50,90]).tolist())),
            'power_rolloff_90_hz':float(frequencies[min(np.searchsorted(np.cumsum(average_power),.9*total),len(frequencies)-1)]),
            'tempo_candidates_85_160_bpm':candidates,'per_second':per_second}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--proposal',type=Path)
    parser.add_argument('--proposal-start',type=float,default=0)
    parser.add_argument('--proposal-duration',type=float)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.output.exists():parser.error('Output report already exists; preserve prior measurements')
    if not math.isfinite(args.proposal_start) or args.proposal_start<0:parser.error('Proposal start must be finite and nonnegative')
    if args.proposal_duration is not None and (not math.isfinite(args.proposal_duration) or args.proposal_duration<1):parser.error('Proposal duration must be at least one second')
    report={'method':'Local FFmpeg mono24k decode, NumPy2048-window/256-hop FFT, spectral-flux autocorrelation, loudnorm measurement.',
            'reference_scope':'Complete supplied local excerpt; no seek applied to the reference.',
            'perceptual_listening':False,
            'limitations':['Tempo is a numerical periodicity candidate, not a confirmed beat transcription.',
                           'Full mixes contain drums, possible vocals and tonal instruments; bands do not isolate a synthesizer.',
                           'Spectral similarity does not prove matching sound, musical quality or listener preference.'],
            'reference':analyze(args.reference)}
    if args.proposal:report['proposal']=analyze(args.proposal,args.proposal_start,args.proposal_duration)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    write(args.output,report)
    for key in ('reference','proposal'):
        if key in report:
            result=report[key]
            print(key,{field:result[field] for field in ('decoded_seconds','integrated_lufs','crest_db','energy_band_percent','middle_centroid_percentiles_hz','tempo_candidates_85_160_bpm')},flush=True)


if __name__=='__main__':main()
