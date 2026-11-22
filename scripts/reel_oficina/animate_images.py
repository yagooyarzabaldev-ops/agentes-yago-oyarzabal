"""Render contained stills with two independent actions via the installed motion renderer.

Config: assets[{id,file,duration,camera,action,accent}], relative image paths.
`--stills` prepares entry/mid/end frames before video. No assets are generated or
downloaded. A contextual animation is explanatory artwork, never real telemetry.
Requires existing Node/motion renderer, browser, Pillow and FFmpeg/ffprobe.
"""
import argparse
from pathlib import Path
import re

from common import digest, input_file, output_path, probe, read_json, resolve, run, stream, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True);p.add_argument('--renderer',required=True);p.add_argument('--output',required=True)
    p.add_argument('--stills',action='store_true');p.add_argument('--node',default='node');p.add_argument('--ffmpeg',default='ffmpeg');p.add_argument('--ffprobe',default='ffprobe')
    p.add_argument('--overwrite',action='store_true');args=p.parse_args()
    config_path=Path(args.config).resolve();config=read_json(config_path);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    renderer=input_file(args.renderer);template=Path(__file__).with_name('image_action.html').resolve();fps=int(config.get('fps',30))
    records=[]
    for item in config['assets']:
        ident=item['id']
        if not re.fullmatch(r'[a-zA-Z0-9_-]+',ident):raise ValueError('Unsafe asset ID')
        image=input_file(resolve(config_path.parent,item['file']));duration=float(item.get('duration',1.6));frames=round(duration*fps)
        if frames<2 or abs(duration*fps-frames)>1e-6:raise ValueError('Duration must be an exact positive frame count')
        params={k:item[k] for k in ('camera','action')};params.update(image_url=image.as_uri(),duration=duration,accent=item.get('accent','#91e2c0'))
        parameter_file=out/(ident+'.json');write_json(parameter_file,params)
        command=[args.node,renderer,'--marca','infinite-process','--template',template,'--params-file',parameter_file,'--fps',fps,'--workers','2']
        if args.stills:
            run(command+['--stills',','.join(str(v) for v in (.1,duration/2,duration-1/fps)),'--out',out/ident],log=out/(ident+'-stills.log'))
        else:
            movie=output_path(out/(ident+'.mp4'),args.overwrite);alpha=out/(ident+'.mov')
            run(command+['--out',alpha],log=out/(ident+'-render.log'))
            run([args.ffmpeg,'-v','error','-i',alpha,'-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart','-y',movie])
            info=probe(movie,args.ffprobe);video=stream(info,'video')
            if int(video['nb_frames'])!=frames:raise ValueError('Unexpected insert frame count')
            run([args.ffmpeg,'-v','error','-i',movie,'-f','null','-'])
        records.append({'id':ident,'file':str(image),'source_sha256':digest(image),'frames':frames,'fps':fps,'duration':frames/fps,
                        'camera':{'type':item['camera'],'range':[0,duration]},'context_action':{'parameters':item['action'],'range':[.1,duration-1/fps]},
                        'independent_actions':2,'unobscured_by_transitions':True,'interpretation':'Illustration, not execution evidence',
                        'insert':str(out/(ident+'.mp4')) if not args.stills else None})
        print(f'{ident}: {"stills" if args.stills else str(frames)+" frames"} / camera + {item["action"]["type"]}',flush=True)
    write_json(out/('preflight.json' if args.stills else 'inserts.json'),records)
    if args.stills:
        from PIL import Image,ImageDraw
        sheet=Image.new('RGB',(1080,len(records)*380),'#11141c');draw=ImageDraw.Draw(sheet)
        for row,item in enumerate(records):
            files=sorted((out/item['id']).glob('*.png'))
            for col,file in enumerate(files[:3]):
                with Image.open(file) as im:sheet.paste(im.convert('RGB').resize((202,360)),(col*360+79,row*380+20))
            draw.text((8,row*380+4),item['id']+' / '+item['context_action']['parameters']['type'],fill='white')
        sheet.save(out/'contacto-preflight.jpg',quality=94)
    print('Finished: '+str(out),flush=True)


if __name__=='__main__':main()
