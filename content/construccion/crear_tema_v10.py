from pathlib import Path
B=Path(__file__).resolve().parent
s=(B/'escena_v8.html').read_text(encoding='utf-8')
s=s.replace('file:///C:/Users/oyarz/.agents/skills/motion-graphics-reels/templates/runtime.js', 'motion-runtime.js')
s=s.replace("const W=1080,H=1920,Y=960,HH=960,F='#fff6ed',N='#0a0b10';", "const W=1080,H=1920,F='#fff6ed',N='#0a0b10';let Y=960,HH=960;")
at=s.index('function stage(s,u)')
s=s[:at]+(B/'v10-motion.js').read_text(encoding='utf-8')+"\nPromise.all(Object.values(images).map(im=>im.decode())).then(()=>{MG.onFrame(render);MG.ready()});\n</script></html>"
(B/'escena_v10.html').write_text(s,encoding='utf-8')
print('V10 standalone visual renderer built.')
