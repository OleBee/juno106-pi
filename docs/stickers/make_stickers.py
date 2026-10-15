# JU-6 Pi sticker sheet generator (A4, mm units, print at 100%)
import cairosvg
BG="#1b1b1b"; W="#f2f2f2"; G="#9a9a9a"; RED="#c8102e"; OR="#e8742a"; YE="#f2c230"; BL="#2f6db5"
F='font-family="Nimbus Sans, Helvetica, Arial, sans-serif"'
out=[]
def cut(x,y,w,h,r=1.5): out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="none" stroke="#000" stroke-width="0.12" stroke-dasharray="1.2 0.8"/>')
def panel(x,y,w,h,bleed=1.0):
    out.append(f'<rect x="{x-bleed}" y="{y-bleed}" width="{w+2*bleed}" height="{h+2*bleed}" fill="{BG}"/>'); cut(x,y,w,h)
def t(x,y,s,size,fill=W,anchor="start",bold=True,ls=0.3):
    out.append(f'<text x="{x}" y="{y}" {F} font-size="{size}" font-weight="{"bold" if bold else "normal"}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{ls}">{s}</text>')
def stripes(x,y,w,h,cols=(RED,OR,YE,BL)):
    sw=w/len(cols)
    for i,c in enumerate(cols): out.append(f'<rect x="{x+i*sw}" y="{y}" width="{sw}" height="{h}" fill="{c}"/>')
def line(x1,y1,x2,y2,c=W,w=0.25): out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{w}"/>')
def logo(x,y,size):
    t(x,y,"JU-6",size,ls=size*0.02); t(x+size*2.4,y,"Pi",size,fill=RED)

# ---- 1. TOP LID 88 x 58
x,y,w,h=12,22,88,58; panel(x,y,w,h)
stripes(x,y+4,w,1.6); logo(x+6,y+19,11)
t(x+6,y+25.5,"POLYPHONIC SYNTHESIZER",3.4,fill=G,ls=0.9)
line(x+6,y+29,x+w-6,y+29,G,0.2)
# slider-bank motif
labs=[("LFO",RED),("DCO",OR),("VCF",YE),("VCA",BL),("ENV",W),("HPF",RED)]
for i,(l,c) in enumerate(labs):
    cx=x+10+i*13.6
    line(cx,y+33,cx,y+47,"#555",0.9); out.append(f'<rect x="{cx-2.4}" y="{y+37+(i*3)%8}" width="4.8" height="2.6" rx="0.4" fill="{c}"/>')
    t(cx,y+51.5,l,2.3,fill=W,anchor="middle",ls=0.2)
t(x+w-6,y+55,"RASPBERRY PI 5 · DAC+",2.0,fill=G,anchor="end",bold=False,ls=0.4)
t(x+6,y+55,"POLYPHONIC",2.0,fill=G,bold=False,ls=0.4)

# ---- 2/3. LONG SIDE STRIPS 88 x 14 (x2)
for k,yy in enumerate((88,106)):
    panel(12,yy,88,14); stripes(12,yy+11,88,1.2); logo(16,yy+8.5,6.5)
    t(96,yy+8.3,"POLYPHONIC SYNTHESIZER",2.6,fill=G,anchor="end",ls=0.6)

# ---- 4/5. SHORT END STRIPS 58 x 14 (x2)
for k,xx in enumerate((110,110)):
    yy=22+k*18; panel(xx,yy,58,14); stripes(xx,yy+11,58,1.2); logo(xx+4,yy+8.5,6.5)
    t(xx+54,yy+8.3,"JU-6 Pi" if False else ("ORIGINAL SOUND" if k==0 else "PROGRAMMABLE"),1.9,fill=G,anchor="end",ls=0.25)

# ---- 6. PORT LABELS (white-on-black tabs with colour tick)
ports=[("POWER",RED,16),("HDMI0 AUDIO",OR,24),("USB MIDI",BL,20),("LINE OUT",YE,20),("L",W,6),("R",RED,6),("HDMI1",G,14),("PHONES",YE,16)]
px,py=110,62
t(px,py-1.5,"PORT LABELS",2.4,fill="#000",ls=0.5)
cx=px; cy=py
for l,c,wd in ports:
    if cx+wd>200: cx=px; cy+=10
    panel(cx,cy,wd,7,bleed=0.6); out.append(f'<rect x="{cx}" y="{cy}" width="{wd}" height="1.1" fill="{c}"/>')
    t(cx+wd/2,cy+5.4,l,2.6,anchor="middle",ls=0.25); cx+=wd+2.5
# duplicate arrow tabs
cy+=10; cx=px
for l in ("▲ USB MIDI","▲ USB MIDI","POWER ▲","LINE OUT ▼"):
    panel(cx,cy,21,7,bleed=0.6); t(cx+10.5,cy+5,l,2.4,anchor="middle"); cx+=23.5

# ---- 7. EXTRAS
ey=130
t(12,ey-1.5,"EXTRAS",2.4,fill="#000",ls=0.5)
panel(12,ey,88,9); secs=[("LFO",RED),("DCO",OR),("VCF",YE),("VCA",BL),("ENV",W),("CHORUS",RED)]
for i,(l,c) in enumerate(secs):
    sx=12+i*88/6; out.append(f'<rect x="{sx+1}" y="{ey+1}" width="{88/6-2}" height="1.2" fill="{c}"/>'); t(sx+88/12,ey+6.8,l,2.7,anchor="middle")
    if i: line(sx,ey+2.5,sx,ey+8,G,0.2)
panel(12,ey+13,88,9); t(16,ey+19.6,"CHORUS",3.2); 
for i,(l,c) in enumerate((("I",OR),("II",YE),("I+II",BL))):
    out.append(f'<rect x="{40+i*20}" y="{ey+15}" width="16" height="5" rx="0.6" fill="{c}"/>'); t(48+i*20,ey+19,l,3,fill="#111",anchor="middle")
# small logo badges
for i in range(3):
    bx=110+i*31; panel(bx,ey,28,12); stripes(bx,ey+9.6,28,1); logo(bx+3,ey+7.4,5.2)
# round dots (slider-cap colours)
for i,c in enumerate((RED,OR,YE,BL,W,RED,OR,YE,BL)):
    cx_=114+i*9.5
    out.append(f'<circle cx="{cx_}" cy="{ey+19}" r="3.6" fill="{c}"/><circle cx="{cx_}" cy="{ey+19}" r="3.6" fill="none" stroke="#000" stroke-width="0.12" stroke-dasharray="1.2 0.8"/>')
# big banner sticker
panel(12,ey+28,186,22); stripes(12,ey+28,186,2); logo(18,ey+44,13)
t(194,ey+38.5,"POLYPHONIC SYNTHESIZER",4.2,fill=W,anchor="end",ls=1.0)
t(194,ey+45,"RASPBERRY PI 5 · DAC+ · CHORUS I / II",2.6,fill=G,anchor="end",ls=0.5)

# ---- header / footer
t(12,12,"JU-6 Pi — STICKER SHEET",5,fill="#000"); 
t(198,12,"A4 · PRINT AT 100% / ACTUAL SIZE · NO SCALING",2.6,fill="#000",anchor="end",bold=False)
t(12,17,"Case: KKSB case for Raspberry Pi 5 + DAC+/DAC Pro. Measure your lid/sides before cutting — sizes are estimates (see README).",2.4,fill="#444",bold=False,ls=0)
sy=270; out.append(f'<rect x="12" y="{sy}" width="50" height="3" fill="none" stroke="#000" stroke-width="0.25"/>')
for i in range(6): line(12+i*10,sy,12+i*10,sy+(4.5 if i in (0,5) else 3.8),"#000",0.25)
for i in range(5): out.append(f'<rect x="{12+i*10}" y="{sy}" width="5" height="3" fill="#000"/>')
t(12,sy+8.5,"SCALE CHECK: this bar must measure exactly 50 mm",2.6,fill="#000",anchor="start",bold=False,ls=0)
t(198,sy+3,"Dashed line = cut line (1 mm black bleed outside).",2.4,fill="#444",anchor="end",bold=False,ls=0)
t(198,sy+7,"Glossy/matte vinyl sticker paper, laser or inkjet. Not affiliated with Roland.",2.4,fill="#444",anchor="end",bold=False,ls=0)
t(12,90-70+0,"",1)
labels=[(12,20,"1 · TOP LID 88×58"),(12,86.3,"2 · LONG SIDE 88×14"),(12,104.3,"3 · LONG SIDE 88×14"),(110,20,"4 · END 58×14"),(110,38.3,"5 · END 58×14")]
for lx,ly,l in labels: t(lx,ly,l,1.9,fill="#666",bold=False,ls=0.2)
svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297"><rect width="210" height="297" fill="#fff"/>{"".join(out)}</svg>'
open("JU-6_Pi_Stickers_A4.svg","w").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode(),write_to="JU-6_Pi_Stickers_A4.pdf")
cairosvg.svg2png(bytestring=svg.encode(),write_to="JU-6_Pi_Stickers_preview.png",output_width=1654)
