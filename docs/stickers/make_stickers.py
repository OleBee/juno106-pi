# JU-6 Pi sticker sheet v2 — understated, Juno-106 panel palette. Print A4 at 100 %.
import cairosvg
PANEL="#3b3d40"   # cool charcoal-grey panel
W="#f4f4f2"       # white legends
RED="#c62b2b"     # red "belt" + section graphics
BLUE="#2a63b0"    # blue bank stripe / buttons
ORANGE="#e07a22"  # orange buttons
G="#a7a9ac"
F='font-family="Nimbus Sans, Helvetica, Arial, sans-serif"'
o=[]
def cut(x,y,w,h,r=1.2): o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="none" stroke="#000" stroke-width="0.12" stroke-dasharray="1.2 0.8"/>')
def panel(x,y,w,h,b=1.0): o.append(f'<rect x="{x-b}" y="{y-b}" width="{w+2*b}" height="{h+2*b}" fill="{PANEL}"/>'); cut(x,y,w,h)
def t(x,y,s,sz,fill=W,a="start",bold=True,ls=0.3,ital=False):
    o.append(f'<text x="{x}" y="{y}" {F} font-size="{sz}" font-weight="{"bold" if bold else "normal"}" font-style="{"italic" if ital else "normal"}" fill="{fill}" text-anchor="{a}" letter-spacing="{ls}">{s}</text>')
def bar(x,y,w,h,c): o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}"/>')
def logo(x,y,sz,a="start"): t(x,y,"JU-6 Pi",sz,a=a,ls=sz*0.06)
def lab(x,y,s): t(x,y,s,1.9,fill="#777",bold=False,ls=0.2)

# 1 top lid 88x58
x,y,w,h=12,24,88,58; lab(x,y-2,"1 · TOP LID 88×58"); panel(x,y,w,h)
bar(x,y+8,w,0.8,RED)
logo(x+7,y+36,10); t(x+7,y+42.5,"PROGRAMMABLE POLYPHONIC SYNTHESIZER",2.3,fill=G,bold=False,ls=0.55)
bar(x+7,y+w*0+50,14,0.8,BLUE); bar(x+22,y+50,6,0.8,ORANGE)
# 2,3 long sides 88x12
for i,yy in enumerate((92,111)):
    lab(12,yy-2,f"{2+i} · LONG SIDE 88×12"); panel(12,yy,88,12); bar(12,yy+2.2,88,0.5,RED)
    logo(17,yy+8.9,5.2); t(95,yy+8.6,"POLYPHONIC SYNTHESIZER",1.9,fill=G,a="end",bold=False,ls=0.45)
# 4,5 ends 58x12
for i,yy in enumerate((24,43)):
    lab(110,yy-2,f"{4+i} · END 58×12"); panel(110,yy,58,12); bar(110,yy+2.2,58,0.5,RED); logo(139,yy+8.9,5.2,a="middle")
# 6 port labels
lab(110,60,"6 · PORT LABELS")
ports=[("POWER",15),("HDMI0 AUDIO",22),("HDMI1",13),("USB MIDI",17),("LINE OUT",17),("L",6),("R",6),("PHONES",15)]
cx,cy=110,62
for s,wd in ports:
    if cx+wd>199: cx=110; cy+=9.5
    panel(cx,cy,wd,6,b=0.6); t(cx+wd/2,cy+4.1,s,2.3,a="middle",ls=0.3); cx+=wd+2.5
# 7 section headers (red graphic like the 106 section names)
lab(110,cy+13.5,"7 · SECTION LABELS")
cx=110; cy+=15.5
for s in ("LFO","DCO","HPF","VCF","VCA","ENV","CHORUS"):
    wd=8+len(s)*1.6
    if cx+wd>199: cx=110; cy+=8
    panel(cx,cy,wd,5,b=0.6); bar(cx,cy,wd,5,RED); t(cx+wd/2,cy+3.6,s,2.3,a="middle",ls=0.3); cx+=wd+2.5
# 8 small badges
lab(12,129,"8 · BADGES 30×10")
for i in range(3):
    bx=12+i*33; panel(bx,131,30,10); logo(bx+15,131+6.8,4.6,a="middle")
# header/footer
t(12,12,"JU-6 Pi · STICKER SHEET",4.2,fill="#111",ls=0.3)
t(198,12,"A4 · PRINT AT 100 % (ACTUAL SIZE)",2.4,fill="#111",a="end",bold=False)
t(12,16.5,"For the KKSB case for Raspberry Pi 5 + DAC+/DAC Pro. Sizes are estimates; measure your case before cutting.",2.2,fill="#555",bold=False,ls=0)
sy=272; o.append(f'<rect x="12" y="{sy}" width="50" height="2.5" fill="none" stroke="#000" stroke-width="0.25"/>')
for i in range(5): bar(12+i*10,sy,5,2.5,"#000")
t(12,sy+7,"Scale check: this bar must measure exactly 50 mm",2.3,fill="#111",bold=False,ls=0)
t(198,sy+2.5,"Dashed line = cut line (1 mm bleed outside).",2.2,fill="#555",a="end",bold=False,ls=0)
t(198,sy+6.5,"Not affiliated with Roland Corporation.",2.2,fill="#555",a="end",bold=False,ls=0)
svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297"><rect width="210" height="297" fill="#fff"/>{"".join(o)}</svg>'
open("JU-6_Pi_Stickers_A4.svg","w").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode(),write_to="JU-6_Pi_Stickers_A4.pdf")
cairosvg.svg2png(bytestring=svg.encode(),write_to="JU-6_Pi_Stickers_preview.png",output_width=1654)
