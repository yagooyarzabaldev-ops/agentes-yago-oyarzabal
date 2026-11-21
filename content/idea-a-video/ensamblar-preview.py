"""Export the visual preview. This deliberately does not produce a voiced final."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B = Path(__file__).resolve().parent
version=3 if '--v3' in sys.argv else 2 if '--v2' in sys.argv else 1
v2=version>=2
D = ROOT / f'runtime/idea-a-video-v{version}'
E = ROOT / f'entregas/idea-a-video-v{version}'
video = E / (f'De_una_idea_a_un_video_V{version}_14_IMAGENES.mp4' if v2 else 'De_una_idea_a_un_video_PREVISUALIZACION.mp4')

def run(args):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError(result.stderr[-5000:])
    return result

# Gentle dip around the human-decision aside. No microphone recording is used here.
dip = "volume='if(lt(t,55.8),1,if(lt(t,56.2),1-0.72*(t-55.8)/0.4,if(lt(t,59.8),0.28,if(lt(t,60.2),0.28+0.72*(t-59.8)/0.4,1))))':eval=frame"
source_probe=json.loads(run(['ffprobe','-v','error','-select_streams','v:0','-show_streams','-of','json',D/'imagen.mp4']).stdout)['streams'][0]
video_options=['-c:v','copy']
if source_probe['pix_fmt']=='yuvj420p' or source_probe.get('color_range')=='pc':
    video_options=['-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p',
                   '-c:v','libx264','-preset','fast','-crf','18','-threads','3','-pix_fmt','yuv420p',
                   '-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709']
run(['ffmpeg','-hide_banner','-loglevel','error','-i',D/'imagen.mp4','-i',E/'House_Idea_a_Video.wav',
     '-map','0:v:0','-map','1:a:0',*video_options,'-af',dip,'-c:a','aac','-b:a','256k','-ar','48000',
     '-t','70','-movflags','+faststart','-y',video])
probe = json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',video]).stdout)
picture = next(s for s in probe['streams'] if s['codec_type']=='video')
sound = next(s for s in probe['streams'] if s['codec_type']=='audio')
assert (picture['width'],picture['height'],picture['r_frame_rate']) == (1080,1920,'30/1')
assert picture['codec_name']=='h264' and sound['codec_name']=='aac'
assert picture['pix_fmt']=='yuv420p' and picture.get('color_range')=='tv'
assert abs(float(probe['format']['duration'])-70)<0.1
scan = run(['ffmpeg','-hide_banner','-nostats','-i',video,
            '-vf','blackdetect=d=0.25:pic_th=0.97,freezedetect=n=0.001:d=1.5',
            '-af','silencedetect=n=-50dB:d=0.5,loudnorm=I=-14:TP=-2:LRA=8:print_format=json',
            '-f','null','-'])
(D/'export-scan.log').write_text(scan.stderr,encoding='utf-8')
measure = json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}',scan.stderr,re.S).group())
events = [line for line in scan.stderr.splitlines() if any(k in line for k in ['black_start:','freeze_start:','silence_start:'])]
assert float(measure['input_tp']) < -2, 'Audio peak exceeds the project ceiling'
frames = D/'export-review'; frames.mkdir(exist_ok=True)
for time in ([1,19,20.1,25,26.1,57,65,69] if version==3 else [1,14.2,29,38.3,46.2,57,65,69]):
    run(['ffmpeg','-v','error','-ss',time,'-i',video,'-frames:v','1','-q:v','2','-y',frames/f'{time:04.1f}.jpg'])
run(['ffmpeg','-v','error','-ss','1','-i',video,'-frames:v','1','-q:v','2','-y',E/'portada-previsualizacion.jpg'])
report = {
    'status':'preview_exported_waiting_for_new_recording',
    'file':str(video.relative_to(ROOT)), 'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
    'duration_seconds':float(probe['format']['duration']), 'width':1080,'height':1920,'fps':30,
    'video_codec':picture['codec_name'],'audio_codec':sound['codec_name'],
    'pixel_format':picture['pix_fmt'],'color_range':picture.get('color_range'),
    'bytes':video.stat().st_size,'full_file_decoded':True,
    'audio':{'integrated_lufs':float(measure['input_i']),'true_peak_dbtp':float(measure['input_tp']),'lra':float(measure['input_lra'])},
    'detector_events':events,
    'layout_review':json.loads((D/'review.json').read_text(encoding='utf-8')),
    'scope':'Instrumental visual preview; not the finished reel',
    'voice_present':False,'camera_present':False,'subtitle_timing':'estimated guide only',
    'final_camera_plan_seconds':34,'final_camera_plan_fraction':34/70,
    'pending':['new microphone and camera recording','cleaning and real word alignment','camera composition and lip sync','voice/music mixing','complete perceptual review'],
    'publication_authorized':False,
}
(E/'revision.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
production_path=B/(f'produccion-v{version}.json' if v2 else 'produccion.json')
production=json.loads(production_path.read_text(encoding='utf-8'))
production['status']=report['status'];production['preview_file']=report['file']
production_path.write_text(json.dumps(production,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if v2:
    report['distinct_image_assets']=production['distinct_images']
    report['image_seconds']=production['image_seconds']
    report['image_asset_sha256']=production['image_asset_sha256']
    if production.get('changed_ranges'):
        report['changed_ranges']=production['changed_ranges']
        report['replacement_image']=production['replacement_image']
    (E/'revision.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
