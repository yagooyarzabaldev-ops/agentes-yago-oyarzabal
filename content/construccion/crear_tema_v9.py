from pathlib import Path
B=Path(__file__).resolve().parent
s=(B/'escena_v8.html').read_text(encoding='utf-8')
s=s.replace("const W=1080,H=1920,Y=960,HH=960,F='#fff6ed',N='#0a0b10';", "const W=1080,H=1920,F='#fff6ed',N='#0a0b10';let Y=960,HH=960;")
s=s.replace('function stage(s,u){','function stageBase8(s,u){')
at=s.rindex('Promise.all(')
s=s[:at]+(B/'v9-motion.js').read_text(encoding='utf-8')+'\n'+s[at:]
(B/'escena_v9.html').write_text(s,encoding='utf-8')
print('V9 template: alternating camera blocks and full-screen visuals, faster motion and stable titles.')
