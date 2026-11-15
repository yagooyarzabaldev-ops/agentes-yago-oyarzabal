"""Reframe the original camera to 1080x960 with the verified V3 edit timings."""
from pathlib import Path
import json,subprocess,concurrent.futures
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'runtime/construccion-v8';edl=json.loads((ROOT/'runtime/construccion-v3/edl.json').read_text())
def run(args):
 r=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace')
 if r.returncode:raise RuntimeError(r.stderr[-4000:])
def clip(s):
 out=D/f'camera-{s["index"]:02}.mp4'
 vf='crop=1944:1728:728:0,scale=1080:960:flags=lanczos,setsar=1,eq=brightness=0.018:saturation=1.04:contrast=1.025,fps=30,format=yuv420p'
 run(['ffmpeg','-v','error','-threads','2','-filter_threads','2','-ss',s['camera_start'],'-i',edl['video'],'-an','-vf',vf,'-frames:v',s['frames'],'-c:v','h264_qsv','-global_quality','18','-preset','veryfast','-map_metadata','-1','-y',out])
 return s['index']
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for i in pool.map(clip,edl['clips']):print(f'Camera {i+1}/{len(edl["clips"])}',flush=True)
(D/'camera-list.txt').write_text('\n'.join(f"file 'camera-{s['index']:02}.mp4'" for s in edl['clips']),encoding='utf-8')
run(['ffmpeg','-v','error','-f','concat','-safe','0','-i',D/'camera-list.txt','-c','copy','-y',D/'camara.mp4'])
(D/'revision-sincronizacion.json').write_text(json.dumps({'timings_source':'runtime/construccion-v3/edl.json','offset_seconds':edl['offset'],'speed':edl['speed'],'frame_count':sum(s['frames'] for s in edl['clips']),'crop':'1944:1728:728:0','output':'1080x960','camera_audio_used':False},indent=2),encoding='utf-8')
print('Camera reframed; same edit and original microphone sync.',flush=True)
