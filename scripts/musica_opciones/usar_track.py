"""Use an authorized local track from decoded sample zero with gentle voice ducking.

Usage: python scripts/musica_opciones/usar_track.py --track music.mp3 --voice voice.wav
  --video picture.mp4 --output-dir entregas/new-version --work-dir runtime/new-mix
  --archive-track content/material/music/private-track.mp3 --source-assets-dir prior-delivery
  --video-name final.mp4 --rights-note "Ownership and authorization supplied by user"

Requires NumPy and local FFmpeg. No downloads, uploads, synthesis, loops, retiming,
EQ or timbre changes. Only resampling, constant level, a bounded voice sidechain,
brief final fade and mastering are applied. A source shorter than the video fails.
Video packets are copied unchanged. Existing inputs and nonempty outputs are preserved.
The measured ducking report is not a claim of perceptual listening or approval.
"""
from pathlib import Path
import argparse
from collections import deque
import copy
import math
import shutil
import subprocess
import numpy as np

from _audio import duration, ffmpeg, measure, new_directory, normalize, probe, read, sha, strict_decode, video_hash, write

SR = 48000
HOP = 480
ROOT = Path(__file__).resolve().parents[2]


def resolve_track(explicit, profile, repository_root=ROOT):
    """An explicit track overrides the default; profile defaults require exact identity."""
    if explicit is not None:
        return Path(explicit), {'selection':'explicit_cli_override'}
    config=read(profile);music=config.get('music',{})
    if music.get('mode')!='user_track':
        raise ValueError('Profile music.mode is not user_track; provide --track or select a user-track profile')
    asset=music.get('asset_path');expected=music.get('source_sha256')
    if not asset or not expected:
        raise ValueError('User-track profile must include asset_path and source_sha256')
    path=Path(asset)
    if not path.is_absolute():path=Path(repository_root)/path
    if not path.is_file() or sha(path)!=expected:
        raise ValueError('Profile music source is missing or its SHA256 does not match')
    return path, {'selection':'profile_default','profile':str(Path(profile).resolve()),
                  'profile_sha256':sha(profile),'expected_track_sha256':expected}


def validate_durations(track,voice,video):
    seconds=duration(video,'video')
    if duration(track)+1/SR<seconds:
        raise ValueError('Track is shorter than the video; loops and retiming are not permitted')
    if duration(voice)>seconds+1/SR:
        raise ValueError('Voice would be truncated')
    return seconds,round(seconds*SR)


def extract_prefix(track,destination,count,log=None):
    """Decode from sample0, then trim exact resampled frames; never seek or pad."""
    ffmpeg('-v','error','-n','-i',track,'-vn','-af',f'aresample={SR},atrim=start_sample=0:end_sample={count},asetpts=PTS-STARTPTS',
           '-ac','2','-c:a','pcm_s24le',destination,log=log)
    samples=pcm(destination)
    if len(samples)!=count:
        raise ValueError('Decoded source is shorter than the video; refusing padding or loops')
    return samples


def pcm(path):
    raw=ffmpeg('-v','error','-i',path,'-vn','-ar',str(SR),'-ac','2','-f','f32le','-').stdout
    return np.frombuffer(raw,'<f4').reshape(-1,2).copy()


def save(path, values):
    if not np.isfinite(values).all() or float(np.max(np.abs(values)))>=1:
        raise ValueError(f'Clipping or invalid samples before writing {path.name}')
    result=subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-f','f32le','-ar',str(SR),'-ac','2',
                           '-i','pipe:0','-c:a','pcm_s24le',str(path)],input=values.astype('<f4').tobytes(),capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace'))


def rms_frames(samples):
    mono_power=np.mean(samples.astype(float)**2,axis=1)
    padded=np.pad(mono_power,(0,(-len(mono_power))%HOP))
    return np.sqrt(np.mean(padded.reshape(-1,HOP),axis=1))


def gain_motion_metrics(reduction):
    changes=np.abs(np.diff(reduction))
    return {'total_variation_db':float(changes.sum()),'maximum_change_per10ms_db':float(changes.max()) if len(changes) else 0.,
            'p95_change_per10ms_db':float(np.percentile(changes,95)) if len(changes) else 0.,
            'changes_over025db_per10ms':int((changes>.25).sum()),
            'changes_over1db_per50ms':int((np.abs(reduction[5:]-reduction[:-5])>1).sum())}


def sidechain(voice, preduck, threshold_db, ratio, knee_db, maximum_db, attack_ms, release_ms, hold_ms=0):
    detector=rms_frames(voice)
    level_db=20*np.log10(np.maximum(detector,1e-12))
    over=level_db-threshold_db
    strength=1-1/ratio
    # Quadratic soft knee joined continuously to the ordinary compressor curve.
    target=np.where(over<=-knee_db/2,0,np.where(over>=knee_db/2,strength*over,
                    strength*(over+knee_db/2)**2/(2*knee_db)))
    target=np.clip(target,0,maximum_db)
    raw_target=target.copy()
    # A causal peak hold avoids bringing music up between syllables. It changes
    # only the detector envelope, never source sample order or playback timing.
    hold_frames=round(hold_ms/1000*SR/HOP)
    if hold_frames:
        candidates=deque()
        for index,value in enumerate(raw_target):
            while candidates and candidates[0]<index-hold_frames:candidates.popleft()
            while candidates and raw_target[candidates[-1]]<=value:candidates.pop()
            candidates.append(index)
            target[index]=raw_target[candidates[0]]
    attack=math.exp(-(HOP/SR)/(attack_ms/1000))
    release=math.exp(-(HOP/SR)/(release_ms/1000))
    reduction=np.zeros(len(target))
    state=0.
    for index,desired in enumerate(target):
        coefficient=attack if desired>state else release
        state=coefficient*state+(1-coefficient)*desired
        reduction[index]=state
    positions=np.arange(len(reduction))*HOP
    sample_reduction=np.interp(np.arange(len(voice)),positions,reduction)
    ducked=preduck*10**(-sample_reduction[:,None]/20)
    before_rms=rms_frames(preduck);after_rms=rms_frames(ducked)
    measurable=before_rms>1e-7
    measured=20*np.log10(np.maximum(before_rms,1e-12)/np.maximum(after_rms,1e-12))
    speech=(level_db>=-35)&measurable
    quiet=(level_db<-35)&measurable
    pauses=[]
    start=None
    for index,in_pause in enumerate(np.r_[quiet,False]):
        if in_pause and start is None:start=index
        elif not in_pause and start is not None:
            if (index-start)*HOP/SR>=.15:
                pauses.append({'start_seconds':start*HOP/SR,'end_seconds':index*HOP/SR,
                               'reduction_start_db':float(reduction[start]),'reduction_end_db':float(reduction[index-1]),
                               'recovered_db':float(reduction[start]-reduction[index-1])})
            start=None
    summary={'detector':'Stereo voice RMS in10ms blocks; quadratic soft knee; smoothed reduction in dB interpolated at48kHz.',
             'threshold_dbfs':threshold_db,'ratio':ratio,'knee_db':knee_db,'maximum_reduction_db':maximum_db,
             'attack_ms':attack_ms,'release_ms':release_ms,'hold_ms':hold_ms,'speech_measurement_gate_dbfs':-35,
             'measurement':'Actual pre/post music RMS ratio per10ms; before final fade and master.',
             'speech_reduction_percentiles_db':dict(zip(['p10','p50','p90'],np.percentile(measured[speech],[10,50,90]).tolist())) if speech.any() else None,
             'quiet_reduction_median_db':float(np.median(measured[quiet])) if quiet.any() else None,
             'measured_maximum_db':float(np.max(measured[measurable])) if measurable.any() else None,
             'speech_seconds':float(speech.sum()*HOP/SR),'quiet_seconds':float(quiet.sum()*HOP/SR),
             'pauses_at_least150ms':pauses,'gain_motion':gain_motion_metrics(reduction),'perceptual_listening':False}
    envelope={'hop_samples':HOP,'sample_rate':SR,'seconds':(positions/SR).tolist(),
              'voice_rms_dbfs':level_db.tolist(),'raw_target_reduction_db':raw_target.tolist(),'target_reduction_db':target.tolist(),
              'smoothed_reduction_db':reduction.tolist(),'measured_music_reduction_db':measured.tolist()}
    return ducked,summary,envelope


def fixed_master(source,destination,log_dir,target=-14,peak=-2.8):
    """Constant loudness-derived gain, then oversampled peak limiting without auto-level."""
    before=measure(source,log=log_dir/'fixed-master-before.log')
    gain_db=target-float(before['input_i'])
    ceiling=10**(peak/20)
    graph=(f'volume={gain_db}dB,aresample=192000,'
           f'alimiter=limit={ceiling}:attack=5:release=80:level=false:asc=false:latency=true,aresample={SR}')
    ffmpeg('-v','error','-n','-i',source,'-af',graph,'-ar',str(SR),'-ac','2','-c:a','pcm_s24le',destination,
           log=log_dir/'fixed-master-render.log')
    after=measure(destination,log=log_dir/'fixed-master-after.log')
    if abs(duration(source)-duration(destination))>1/SR:
        raise RuntimeError('Master limiter changed duration despite latency compensation')
    return after,{'mode':'fixed_gain_peak_limiter','constant_gain_db':gain_db,
                  'peak_limit_dbtp':peak,'oversample_rate':192000,'limiter_attack_ms':5,'limiter_release_ms':80,
                  'automatic_level':False,'automatic_release':False,'latency_compensation':True,
                  'raw_metrics':before,'target_lufs':target}


def update_plan(source_plan,result,master,video,music_manifest):
    """Keep the proven visual plan and replace every current audio attribution."""
    plan=copy.deepcopy(read(source_plan))
    # A new review is not a publication receipt. Do not inherit stale destination IDs,
    # published flags or claims that belonged to the source delivery.
    for key in list(plan):
        if key.lower().startswith(('publication','published','instagram')):plan.pop(key)
    previous={'source_plan_sha256':sha(source_plan),'source_plan':str(Path(source_plan).resolve()),
              'scope':'Historical audio only; superseded by current plan.music and plan.audio.',
              'audio':plan.get('audio'),'audio_stage':plan.get('audio_stage'),'revision':plan.get('revision')}
    for key in ('music','music_direction','music_selection','stems'):
        if key in plan:previous[key]=plan.pop(key)
    plan['audio_history']=[*plan.get('audio_history',[]),previous]
    plan.update({'audio':str(master.resolve()),'audio_stage':'Authorized supplied track from0 at1x; gentle voice sidechain; mastered once; AAC192k mux.',
                 'music':{'mode':'user_track','source':result['source_track'],'source_sha256':result['track_sha256'],
                          'source_start_seconds':0,'playback_rate':1,'loop':False,'trim_to_video_duration':True,
                          'out_seconds':result['music_edit']['out_seconds'],'rights_basis':result['rights_basis'],
                          'ducking':result['ducking']},
                 'profile_scope':'Inherited profile describes preserved visuals/timing. Any former music direction is historical; current audio is plan.music.',
                 'current_editorial_profile':result['track_selection'],
                 'master_sha256':sha(master),'final_file':str(video.resolve()),'final_sha256':sha(video),'final_bytes':video.stat().st_size,
                 'encoded_info':probe(video),'audio_revision':{'source_plan_sha256':sha(source_plan),
                 'music_manifest':str(music_manifest.resolve()),'image_packets_preserved':True},
                 'revision':f'Audio revision: {video.stem}; authorized source track from0; image packets unchanged.',
                 'plan_state':'final_export_with_authorized_track','publication_performed':False,'perceptual_listening':False})
    return plan


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('voice','video','output-dir','work-dir'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--track',type=Path,help='Explicit source override. Omit to load the verified user_track default from --profile.')
    parser.add_argument('--profile',type=Path,default=ROOT/'config/video-style.json')
    parser.add_argument('--archive-track',type=Path)
    parser.add_argument('--source-assets-dir',type=Path)
    parser.add_argument('--video-name',default='video.mp4')
    parser.add_argument('--rights-note',required=True)
    parser.add_argument('--music-lufs',type=float,default=-23.5,help='Constant gain target before ducking; no music compressor/EQ.')
    parser.add_argument('--threshold-db',type=float,default=-28)
    parser.add_argument('--ratio',type=float,default=2)
    parser.add_argument('--knee-db',type=float,default=8)
    parser.add_argument('--max-reduction-db',type=float,default=6)
    parser.add_argument('--attack-ms',type=float,default=20)
    parser.add_argument('--release-ms',type=float,default=280)
    parser.add_argument('--hold-ms',type=float,default=0,help='Causal detector hold0–250ms; stabilizes music between syllables without delaying audio.')
    parser.add_argument('--mastering',choices=['loudnorm','fixed-limiter'],default='loudnorm',help='Historical dynamic loudnorm or fixed gain plus latency-compensated peak limiting.')
    parser.add_argument('--fade-out',type=float,default=.4)
    args=parser.parse_args(argv)
    values=[args.music_lufs,args.threshold_db,args.ratio,args.knee_db,args.max_reduction_db,args.attack_ms,args.release_ms,args.hold_ms,args.fade_out]
    if not all(math.isfinite(value) for value in values):parser.error('Numerical parameters must be finite')
    if not -40<=args.music_lufs<=-12 or not -50<=args.threshold_db<=-8:parser.error('Invalid music or detector level')
    if not 1<args.ratio<=10 or not 1<=args.knee_db<=20 or not 0<args.max_reduction_db<=12:parser.error('Invalid compressor curve')
    if not 15<=args.attack_ms<=25 or not 220<=args.release_ms<=320:parser.error('Use gentle attack15–25ms and release220–320ms')
    if not 0<=args.hold_ms<=250:parser.error('Detector hold must be between0 and250ms')
    if not 0<=args.fade_out<=1:parser.error('Fadeout must be between0 and1second')
    if Path(args.video_name).name!=args.video_name or Path(args.video_name).suffix.lower()!='.mp4':parser.error('--video-name must be an MP4 basename')
    try:
        args.track,selection=resolve_track(args.track,args.profile)
        seconds,count=validate_durations(args.track,args.voice,args.video)
    except (ValueError,FileNotFoundError) as error:parser.error(str(error))
    if args.fade_out>=seconds:parser.error('Fadeout must be shorter than the video')
    if args.output_dir.resolve()==args.work_dir.resolve():parser.error('Delivery and work directories must differ')
    for path in (args.output_dir,args.work_dir):
        if path.exists() and (not path.is_dir() or any(path.iterdir())):parser.error(f'Output must be new or empty: {path}')
    hashes={'track':sha(args.track),'voice':sha(args.voice),'video':sha(args.video)}
    source_video_packets=video_hash(args.video)
    stored_track=args.track
    if args.archive_track:
        if args.archive_track.exists() and sha(args.archive_track)!=hashes['track']:parser.error('Archive destination contains a different track')
        args.archive_track.parent.mkdir(parents=True,exist_ok=True)
        if not args.archive_track.exists():shutil.copy2(args.track,args.archive_track)
        if sha(args.archive_track)!=hashes['track']:raise RuntimeError('Archive hash mismatch')
        stored_track=args.archive_track
    work=new_directory(args.work_dir);out=new_directory(args.output_dir)
    music_dir=out/'musica';music_dir.mkdir();logs=work/'logs';logs.mkdir()
    excerpt=work/'track_desde_cero.wav'
    # Decoder removes MP3 encoder padding; there is deliberately no input seek.
    track=extract_prefix(stored_track,excerpt,count,log=logs/'decode-track-from-zero.log')
    voice=pcm(args.voice)
    if len(voice)>count:raise RuntimeError('Decoded voice would be truncated')
    voice=np.pad(voice,((0,count-len(voice)),(0,0)))
    save(work/'voz_alineada.wav',voice)
    excerpt_metrics=measure(excerpt)
    gain_db=args.music_lufs-float(excerpt_metrics['input_i'])
    preduck=track*10**(gain_db/20)
    save(work/'musica_preduck.wav',preduck)
    ducked,duck_metrics,envelope=sidechain(voice,preduck,args.threshold_db,args.ratio,args.knee_db,
                                         args.max_reduction_db,args.attack_ms,args.release_ms,args.hold_ms)
    save(work/'musica_postduck_sin_fade.wav',ducked)
    write(work/'envolvente-ducking.json',envelope);write(work/'mediciones-ducking.json',duck_metrics)
    fade=np.ones(count)
    if args.fade_out:
        length=round(args.fade_out*SR);fade[-length:]=np.linspace(1,0,length)
    music=ducked*fade[:,None]
    save(work/'musica_postduck.wav',music)
    mix=voice+music
    # A uniform preparatory gain only prevents PCM overflow; no input is edited.
    pre_master_gain=min(1.,.95/max(float(np.max(np.abs(mix))),1e-12))
    raw=work/'mezcla_sin_master.wav';save(raw,mix*pre_master_gain)
    master=music_dir/'master.wav'
    if args.mastering=='fixed-limiter':
        master_metrics,mastering_method=fixed_master(raw,master,logs)
    else:
        master_metrics=normalize(raw,master,-14,-2.7,logs)
        mastering_method={'mode':'two_pass_loudnorm','target_lufs':-14,'peak_ceiling_dbtp':-2.7,
                          'note':'linear requested; FFmpeg may use dynamic normalization when peak/headroom requires it.'}
    master_mp3=music_dir/'master.mp3'
    ffmpeg('-v','error','-n','-i',master,'-c:a','libmp3lame','-b:a','256k',master_mp3)
    video=out/args.video_name
    ffmpeg('-v','error','-n','-i',args.video,'-i',master,'-map','0:v:0','-map','1:a:0',
           '-c:v','copy','-c:a','aac','-b:a','192k','-t',seconds,'-movflags','+faststart',video,log=logs/'mux-video.log')
    encoded_metrics=measure(video,log=logs/'encoded-video-loudness.log')
    if abs(float(encoded_metrics['input_i'])+14)>.8 or float(encoded_metrics['input_tp'])>=-2:
        raise RuntimeError('Encoded reel misses loudness/peak target')
    if video_hash(video)!=source_video_packets:raise RuntimeError('Copied video packet identity differs')
    for path in (master,master_mp3,video):strict_decode(path,logs/(path.stem+'-strict-decode.log'))
    copied={}
    if args.source_assets_dir:
        for name in ('portada.jpg','copy.txt','subtitulos.srt','subtitulos-renderizados.ass'):
            source=args.source_assets_dir/name
            if not source.is_file():raise FileNotFoundError(source)
            shutil.copy2(source,out/name)
            copied[name]={'source_sha256':sha(source),'output_sha256':sha(out/name)}
    result={'schema_version':1,'source_track':str(stored_track.resolve()),'original_track':str(args.track.resolve()),'track_selection':selection,
            'track_sha256':hashes['track'],'rights_basis':args.rights_note,'source_track_seconds':duration(stored_track),
            'source_voice':str(args.voice.resolve()),'voice_sha256':hashes['voice'],
            'source_video':str(args.video.resolve()),'source_video_sha256':hashes['video'],
            'music_edit':{'in_seconds':0,'out_seconds':count/SR,'decoded_start_sample':0,'decoded_sample_rate':SR,
                          'speed':1,'loops':0,'internal_cuts':0,'equalization':False,'fade_out_seconds':args.fade_out,
                          'constant_gain_db':gain_db,'preduck_lufs_target':args.music_lufs},
            'ducking':duck_metrics,'pre_master_uniform_gain':pre_master_gain,
            'voice_edit':{'speed':1,'cuts':0,'pitch_change':False,'padding_only_at_end_samples':count-round(duration(args.voice)*SR)},
            'master_metrics':master_metrics,'mastering_method':mastering_method,'encoded_metrics':encoded_metrics,
            'editing_order':{'supplied_picture_and_voice_treated_as_final':True,'clean_voice_review':'operator_required',
                             'music_added_over_supplied_timeline':True,
                             'reused_previous_mixed_audio':False,'track_edl_applied':False},
            'video_packet_hash':source_video_packets,'video_packets_identical':True,
            'master':str(master.resolve()),'master_sha256':sha(master),'video':str(video.resolve()),'video_sha256':sha(video),
            'copied_assets':copied,'script_sha256':sha(Path(__file__)),'perceptual_listening':False,
            'publication_performed':False,'checks':{'full_decode':True,'no_source_edits':False},
            'work_files':{name:str((work/name).resolve()) for name in ('track_desde_cero.wav','voz_alineada.wav','musica_preduck.wav','musica_postduck_sin_fade.wav','musica_postduck.wav','envolvente-ducking.json','mediciones-ducking.json')},
            'limitations':['Gain measurements do not certify audible comfort or absence of perceived pumping.','Mastering and AAC encoding change samples, but no narration timing/content or image packets are edited.']}
    result['checks']['no_source_edits']=hashes=={'track':sha(args.track),'voice':sha(args.voice),'video':sha(args.video)}
    if not result['checks']['no_source_edits']:raise RuntimeError('An input changed during rendering')
    write(work/'procedencia-y-mezcla.json',result);write(music_dir/'procedencia-y-mezcla.json',result)
    if args.source_assets_dir and (args.source_assets_dir/'plan-y-procedencia.json').is_file():
        source_plan=args.source_assets_dir/'plan-y-procedencia.json'
        plan=update_plan(source_plan,result,master,video,music_dir/'procedencia-y-mezcla.json')
        write(out/'plan-y-procedencia.json',plan)
    print('COMPLETE',flush=True)
    print({'master':str(master),'video':str(video),'constant_music_gain_db':gain_db,
           'speech_reduction_db':duck_metrics['speech_reduction_percentiles_db'],
           'encoded_lufs':encoded_metrics['input_i'],'encoded_peak_dbtp':encoded_metrics['input_tp'],
           'video_packets_identical':True},flush=True)


if __name__=='__main__':main()
