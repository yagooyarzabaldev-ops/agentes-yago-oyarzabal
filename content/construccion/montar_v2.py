"""Render camera from the source video; final spoken audio comes only from the supplied WAV."""
from pathlib import Path
import json,subprocess,sys,concurrent.futures
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v2'
P=json.loads((D/'params.json').read_text(encoding='utf-8'));edl=json.loads((D/'edl.json').read_text())
def run(cmd):
 p=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,encoding='utf-8',errors='replace')
 if p.returncode:raise RuntimeError(p.stderr[-3000:])
 return p
def clip(c):
 out=D/f'clip-{c["index"]:02}.mp4'
 # All camera clips remain medium; a lossless digital crop adds the second framing in the composite.
 vf='crop=1640:1728:880:0,scale=1080:1138:flags=lanczos,pad=1080:1920:0:250:color=0x0b1830,setsar=1,eq=brightness=0.018:saturation=1.04:contrast=1.025,fps=30,format=yuv420p'
 run(['ffmpeg','-hide_banner','-loglevel','error','-threads','2','-filter_threads','2',
  '-ss',c['camera_start'],'-i',edl['video'],'-an','-vf',vf,'-frames:v',c['frames'],
  '-c:v','h264_qsv','-global_quality','18','-preset','veryfast','-map_metadata','-1','-y',out])
 dur=c['end']-c['start']
 run(['ffmpeg','-hide_banner','-loglevel','error','-ss',c['mic_start'],'-t',dur,'-i',edl['audio'],
  '-vn','-af',f'apad,atrim=duration={dur},afade=t=in:d=0.004,afade=t=out:st={max(0,dur-.006)}:d=0.006',
  '-ar','48000','-ac','2','-c:a','pcm_s24le','-y',D/f'mic-{c["index"]:02}.wav'])
 return c['index']
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for n in pool.map(clip,edl['clips']):print(f'Clip {n+1}/{len(edl["clips"])} sincronizado',flush=True)
(D/'camera-list.txt').write_text('\n'.join(f"file 'clip-{c['index']:02}.mp4'" for c in edl['clips']),encoding='utf-8')
(D/'mic-list.txt').write_text('\n'.join(f"file 'mic-{c['index']:02}.wav'" for c in edl['clips']),encoding='utf-8')
run(['ffmpeg','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',D/'camera-list.txt','-c','copy','-y',D/'camara.mp4'])
run(['ffmpeg','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',D/'mic-list.txt','-c','copy','-y',D/'microfono-editado.wav'])
print(json.dumps({'microphone':str(D/'microfono-editado.wav'),'camera':str(D/'camara.mp4'),'camera_audio_included':False}),flush=True)
