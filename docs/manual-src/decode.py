import re, math, json, os
from pathlib import Path
REPO = Path(os.environ.get('JU6_REPO', Path(__file__).resolve().parents[2]))
src=open(REPO / 'src/factory_bank.h').read()
bank={m.group(1):list(map(int,m.group(3).split(','))) for m in re.finditer(r'\{"(([AB]\d\d) [^"]*)", \{([^}]*)\}\}',src)}
bank={k.split()[0]:(k,v) for k,v in bank.items()}
def inv(t):
    if t<=0: return 0.0
    if t>=1: return 1.0
    a=5*t;b=1-5*t;c=-t
    return (-b+math.sqrt(b*b-4*a*c))/(2*a)
zone=lambda i,n: min(127,int((i+0.5)*128/n))
def knobs(slot):
    name,d=bank[slot]; s=d[:16]; sw1,sw2=d[16],d[17]
    oct=2 if sw1&4 else 1 if sw1&2 else 0
    pulse=bool(sw1&8); saw=bool(sw1&16); chon=not(sw1&0x20); c1=bool(sw1&0x40)
    chorus=0 if not chon else (1 if c1 else 2)
    pwm=1 if sw2&1 else 0; inv_=1 if sw2&2 else 0; vca=1 if sw2&4 else 0; hpf=3-((sw2>>3)&3)
    r=lambda x: int(round(x))
    p1=[s[5],s[6],s[7],s[11],s[12],s[13],s[14],zone(chorus,4)]
    p2=[zone(oct,3),r(inv(s[2]/127)*127),r(min(s[3],105)/105*127),zone(pwm,3),zone((1 if pulse else 0)+(2 if saw else 0),4),s[15],s[4],s[9]]
    p3=[s[0],s[1],s[8],zone(inv_,2),zone(hpf,4),zone(vca,2),s[10],zone(0,2)]
    lab=dict(range=["16'","8'","4'"][oct],wave=["off","pulse","saw","pulse+saw"][(1 if pulse else 0)+(2 if saw else 0)],
      chorus=["off","I","II"][chorus],pwmsrc=["LFO","MAN"][pwm],envpol="+-"[inv_],vca=["ENV","GATE"][vca],hpf=hpf)
    return dict(name=name,p1=p1,p2=p2,p3=p3,lab=lab,raw=d)
out={s:knobs(s) for s in ['A48','B11','A11']}
for k,v in out.items(): print(k,v)
json.dump(out,open('tutorials.json','w'),indent=1)
