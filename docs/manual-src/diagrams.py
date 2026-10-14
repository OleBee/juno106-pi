"""Hand-drawn SVG diagrams for the JU-6 Pi Owner's Manual.
MPK mini Plus layout follows the Top/Rear Panel figures in AKAI's MPK mini Plus User Guide v1.2
(drawn from scratch, simplified, not to scale)."""
import math
INK = "#111"; RED = "#c8102e"; GREY = "#8a8a8a"; LIGHT = "#e9e9e9"; PANEL = "#2b2b2b"
FONT = "Nimbus Sans, Helvetica, Arial, sans-serif"

def callout(x, y, n, r=11, fill=INK, fg="#fff", size=12):
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="#fff" stroke-width="1.5"/>'
            f'<text x="{x}" y="{y+size*0.36}" font-size="{size}" font-weight="bold" text-anchor="middle" fill="{fg}">{n}</text>')

def leader(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK}" stroke-width="1"/>'

def svg(w, h, body, cls=""):
    return (f'<svg class="{cls}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f'font-family="{FONT}">{body}</svg>')

def knob(cx, cy, r, val=None, label=None, sub=None, dark=True):
    """360-degree style knob; if val (0-127) given, draw pointer for a 300-degree sweep."""
    s = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{"#1a1a1a" if dark else "#fff"}" stroke="{INK}" stroke-width="1.2"/>'
    s += f'<circle cx="{cx}" cy="{cy}" r="{r*0.72}" fill="{"#3a3a3a" if dark else "#f4f4f4"}" stroke="{INK}" stroke-width="0.6"/>'
    if val is not None:
        a = math.radians(-150 + 300 * val / 127)  # 0 at 7 o'clock, 127 at 5 o'clock
        x2 = cx + r * 0.9 * math.sin(a); y2 = cy - r * 0.9 * math.cos(a)
        s += f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{RED}" stroke-width="{max(1.5, r/7):.1f}" stroke-linecap="round"/>'
        # scale ticks
        for i in range(11):
            t = math.radians(-150 + 30 * i)
            xa = cx + r * 1.12 * math.sin(t); ya = cy - r * 1.12 * math.cos(t)
            xb = cx + r * 1.25 * math.sin(t); yb = cy - r * 1.25 * math.cos(t)
            s += f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" stroke="{INK}" stroke-width="0.6"/>'
    else:
        s += f'<line x1="{cx}" y1="{cy-r*0.25}" x2="{cx}" y2="{cy-r*0.9}" stroke="#fff" stroke-width="1.5"/>'
    if label:
        s += f'<text x="{cx}" y="{cy+r+12}" font-size="9" text-anchor="middle" fill="{INK}">{label}</text>'
    if sub:
        s += f'<text x="{cx}" y="{cy+r+23}" font-size="9" font-weight="bold" text-anchor="middle" fill="{RED}">{sub}</text>'
    return s

def keyboard(x, y, w, h, n_white=22, white_fill="#fff"):
    s = ""; kw = w / n_white
    for i in range(n_white):
        s += f'<rect x="{x+i*kw:.1f}" y="{y}" width="{kw:.1f}" height="{h}" fill="{white_fill}" stroke="{INK}" stroke-width="0.8"/>'
    pattern = [1, 1, 0, 1, 1, 1, 0]  # black key after C, D, (no E), F, G, A, (no B)
    for i in range(n_white - 1):
        if pattern[i % 7]:
            s += f'<rect x="{x+(i+1)*kw-kw*0.3:.1f}" y="{y}" width="{kw*0.6:.1f}" height="{h*0.6:.1f}" fill="{INK}"/>'
    return s

def btn(x, y, w, h, label, fill="#d9d9d9", fs=6.5, tc=INK):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" fill="{fill}" stroke="{INK}" stroke-width="0.8"/>'
            f'<text x="{x+w/2}" y="{y+h/2+fs*0.35}" font-size="{fs}" text-anchor="middle" fill="{tc}">{label}</text>')

def mpk_top(callouts=True):
    """Top panel of the AKAI MPK mini Plus with JU-6 Pi callouts."""
    W, H = 900, 470
    b = ""
    bx, by, bw, bh = 40, 60, 820, 330
    b += f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="10" fill="{PANEL}" stroke="{INK}" stroke-width="2"/>'
    b += f'<text x="{bx+18}" y="{by+26}" font-size="15" font-weight="bold" fill="#fff" letter-spacing="2">AKAI</text>'
    b += f'<text x="{bx+18}" y="{by+36}" font-size="5.5" fill="#bbb" letter-spacing="1">PROFESSIONAL</text>'
    # wheels
    for i, lab in enumerate(["PITCH", "MOD"]):
        wx = bx + 18 + i * 30
        b += f'<rect x="{wx}" y="{by+70}" width="20" height="78" rx="4" fill="#111" stroke="#777"/>'
        for k in range(9):
            b += f'<line x1="{wx+3}" y1="{by+80+k*7}" x2="{wx+17}" y2="{by+80+k*7}" stroke="#555"/>'
        b += f'<text x="{wx+10}" y="{by+160}" font-size="6.5" fill="#ddd" text-anchor="middle">{lab}</text>'
    # joystick
    jx, jy = bx + 115, by + 32
    b += f'<circle cx="{jx}" cy="{jy}" r="17" fill="#111" stroke="#888" stroke-width="1.5"/><circle cx="{jx}" cy="{jy}" r="8" fill="#555"/>'
    # left buttons
    labs = [("ARP", "TAP TEMPO"), ("NOTE RPT", "FULL LEVEL"), ("OCT −", "OCT +")]
    for r_, (l1, l2) in enumerate(labs):
        b += btn(bx + 90, by + 62 + r_ * 30, 24, 16, l1, fs=5)
        b += btn(bx + 120, by + 62 + r_ * 30, 24, 16, l2, fs=5)
    # pads (top row 5-8, bottom row 1-4)
    px0, py0, ps, gap = bx + 170, by + 18, 52, 10
    for row in range(2):
        for col in range(4):
            n = (5 + col) if row == 0 else (1 + col)
            x = px0 + col * (ps + gap); y = py0 + row * (ps + gap + 6)
            b += f'<rect x="{x}" y="{y}" width="{ps}" height="{ps}" rx="5" fill="#3d3d3d" stroke="#999" stroke-width="1.2"/>'
            b += f'<text x="{x+4}" y="{y-2}" font-size="6" fill="#ccc">PAD {n}</text>'
    # display + encoder + buttons
    dx = bx + 430
    b += f'<rect x="{dx}" y="{by+20}" width="62" height="26" rx="2" fill="#0d1b2a" stroke="#888"/>'
    b += f'<circle cx="{dx+88}" cy="{by+33}" r="13" fill="#1a1a1a" stroke="#999"/>'
    b += btn(dx, by + 62, 26, 17, "BANK A/B", fill="#f2f2f2", fs=4.8)
    b += btn(dx + 32, by + 62, 26, 17, "SCALES", fs=4.8)
    b += btn(dx + 64, by + 62, 26, 17, "CHORDS", fs=4.8)
    b += btn(dx, by + 98, 26, 17, "SHIFT", fs=4.8)
    b += btn(dx + 32, by + 98, 26, 17, "HOME", fs=4.8)
    b += btn(dx + 64, by + 98, 26, 17, "PROG SEL", fs=4.8)
    # knobs
    kx0 = bx + 560
    for row in range(2):
        for col in range(4):
            n = 1 + col + row * 4
            b += knob(kx0 + col * 62 + 30, by + 34 + row * 56, 17)
            b += f'<text x="{kx0+col*62+30}" y="{by+12+row*56}" font-size="7" fill="#ddd" text-anchor="middle">K{n}</text>'
    for i, lab in enumerate(["◀◀", "▶▶", "STOP", "PLAY", "REC", "SEQ"]):
        b += btn(kx0 + 6 + i * 41, by + 140, 32, 14, lab, fs=5.5)
    # keyboard
    b += keyboard(bx + 12, by + 172, bw - 24, 148)
    # callouts with leaders  (number, target x,y, label x,y)
    C = [
        (1, bx + 400, by + 290, bx + 400, by + 290),
        (2, bx + 28, by + 110, bx + 28, by - 25),
        (3, bx + 58, by + 110, bx + 62, by - 25),
        (4, jx, jy, jx, by - 25),
        (5, bx + 132, by + 130, bx + 200, by - 25),
        (6, px0 + 120, py0 + 60, px0 + 120, by - 25),
        (7, dx + 13, by + 70, dx + 13, by - 25),
        (8, kx0 + 123, by + 62, kx0 + 123, by - 25),
    ]
    for n, tx, ty, lx, ly in (C if callouts else []):
        if (tx, ty) != (lx, ly):
            b += leader(tx, ty, lx, ly)
        b += callout(lx, ly, n, fill=RED if n != 1 else INK)
    # rear panel strip
    ry = 420
    b += f'<rect x="{bx}" y="{ry}" width="{bw}" height="34" rx="5" fill="{PANEL}" stroke="{INK}" stroke-width="2"/>'
    b += f'<text x="{bx+110}" y="{ry-6}" font-size="9" fill="{INK}" font-weight="bold">REAR PANEL</text>'
    b += f'<rect x="{bx+20}" y="{ry+9}" width="18" height="14" rx="2" fill="#bbb" stroke="#fff"/><text x="{bx+29}" y="{ry+31}" font-size="5.5" fill="#ddd" text-anchor="middle">USB</text>'
    b += f'<circle cx="{bx+62}" cy="{ry+16}" r="6" fill="#111" stroke="#bbb"/><text x="{bx+62}" y="{ry+31}" font-size="5.5" fill="#ddd" text-anchor="middle">SUSTAIN</text>'
    for i, l in enumerate(["PITCH", "GATE", "MOD", "CLK IN", "CLK OUT"]):
        b += f'<circle cx="{bx+100+i*22}" cy="{ry+16}" r="5" fill="#111" stroke="#bbb"/><text x="{bx+100+i*22}" y="{ry+31}" font-size="4.5" fill="#ddd" text-anchor="middle">{l}</text>'
    for i, l in enumerate(["MIDI IN", "MIDI OUT"]):
        b += f'<circle cx="{bx+228+i*30}" cy="{ry+16}" r="9" fill="#111" stroke="#bbb"/><text x="{bx+228+i*30}" y="{ry+32}" font-size="4.5" fill="#ddd" text-anchor="middle">{l}</text>'
    b += f'<text x="{bx+bw-20}" y="{ry+22}" font-size="12" fill="#fff" text-anchor="end" font-weight="bold">MPK mini plus</text>'
    if callouts:
        b += leader(bx + 29, ry + 9, bx + 29, ry - 14) + callout(bx + 29, ry - 14, 9, fill=RED)
        b += leader(bx + 62, ry + 10, bx + 68, ry - 14) + callout(bx + 68, ry - 14, 10, fill=RED)
    return svg(W, H + 10, b, "fig")

def pad_map():
    W, H = 900, 300
    b = ""
    def grid(x0, title, labels, sub, color):
        s = f'<text x="{x0}" y="22" font-size="15" font-weight="bold" fill="{INK}">{title}</text>'
        s += f'<text x="{x0}" y="38" font-size="10" fill="{GREY}">{sub}</text>'
        for row in range(2):
            for col in range(4):
                n = (5 + col) if row == 0 else (1 + col)
                x = x0 + col * 102; y = 52 + row * 112
                s += f'<rect x="{x}" y="{y}" width="94" height="100" rx="8" fill="{color}" stroke="{INK}" stroke-width="1.5"/>'
                s += f'<text x="{x+8}" y="{y+16}" font-size="9" fill="#fff" opacity="0.8">PAD {n}</text>'
                l1, l2 = labels[n - 1]
                s += f'<text x="{x+47}" y="{y+56}" font-size="{15 if len(l1) < 9 else 12.5}" font-weight="bold" fill="#fff" text-anchor="middle">{l1}</text>'
                s += f'<text x="{x+47}" y="{y+74}" font-size="9" fill="#fff" text-anchor="middle">{l2}</text>'
        return s
    A = [(f"x{i}", f"patch number {i}") for i in range(1, 9)]
    B = [("PAGE 1", "SOUND"), ("PAGE 2", "DCO"), ("PAGE 3", "MOD/HPF/VCA"), ("PAGE 4", "PLAY"),
         ("GROUP −", "previous group"), ("GROUP +", "next group"), ("HOLD", "on / off"), ("TRANSPOSE", "hold + key")]
    b += grid(10, "PAD BANK A", A, "notes 36–43 on ch. 10 · hold 1.5 s = WRITE", "#4a4a4a")
    b += grid(470, "PAD BANK B", B, "notes 44–51 on ch. 10 · function pads", RED)
    return svg(W, H, b, "fig")

def knob_page(title, names, values=None, subs=None):
    """One knob page laid out like the MPK's 2×4 knob block."""
    W, H = 440, 250
    b = f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="8" fill="#fff" stroke="{INK}" stroke-width="1.5"/>'
    b += f'<rect x="1" y="1" width="{W-2}" height="24" rx="8" fill="{INK}"/><rect x="1" y="16" width="{W-2}" height="9" fill="{INK}"/>'
    b += f'<text x="14" y="18" font-size="12" font-weight="bold" fill="#fff" letter-spacing="1">{title}</text>'
    for row in range(2):
        for col in range(4):
            i = col + row * 4
            cx = 60 + col * 107; cy = 66 + row * 108
            v = values[i] if values else None
            b += knob(cx, cy, 20, v, None, None, dark=True)
            b += f'<text x="{cx-32}" y="{cy-22}" font-size="9" fill="{GREY}">K{i+1}</text>'
            lines = names[i].split("|")
            for j, ln in enumerate(lines):
                b += f'<text x="{cx}" y="{cy+36+j*11}" font-size="10" font-weight="bold" text-anchor="middle" fill="{INK}">{ln}</text>'
            if subs:
                b += f'<text x="{cx}" y="{cy+37+len(lines)*11}" font-size="10.5" font-weight="bold" text-anchor="middle" fill="{RED}">{subs[i]}</text>'
    return svg(W, H, b, "kp")

def pi5_connections(dac=False):
    """Simplified Raspberry Pi 5 + MPK + output connection diagram (not to scale)."""
    W, H = 900, 400
    b = ""
    # Pi board
    x, y, w, h = 300, 120, 300, 200
    b += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#1f6f43" stroke="{INK}" stroke-width="2"/>'
    b += f'<text x="{x+w/2}" y="{y+h/2-6}" font-size="16" font-weight="bold" fill="#fff" text-anchor="middle">Raspberry Pi 5</text>'
    b += f'<text x="{x+w/2}" y="{y+h/2+12}" font-size="10" fill="#e6f2ea" text-anchor="middle">8 GB · JU-6 Pi v1.1.0 microSD</text>'
    # GPIO header along top edge
    b += f'<rect x="{x+40}" y="{y+8}" width="200" height="16" fill="#111"/>'
    for i in range(20):
        b += f'<circle cx="{x+45+i*10}" cy="{y+16}" r="2.2" fill="#d4af37"/>'
    b += f'<text x="{x+140}" y="{y+36}" font-size="8" fill="#fff" text-anchor="middle">40-pin GPIO</text>'
    # bottom edge: USB-C, HDMI0, HDMI1
    b += f'<rect x="{x+30}" y="{y+h-6}" width="34" height="16" rx="5" fill="#ccc" stroke="{INK}"/>'
    b += f'<rect x="{x+90}" y="{y+h-6}" width="30" height="14" rx="3" fill="#ccc" stroke="{INK}"/>'
    b += f'<rect x="{x+140}" y="{y+h-6}" width="30" height="14" rx="3" fill="#ccc" stroke="{INK}"/>'
    b += f'<text x="{x+47}" y="{y+h-12}" font-size="7.5" fill="#fff" text-anchor="middle">USB-C</text>'
    b += f'<text x="{x+105}" y="{y+h-12}" font-size="7.5" fill="#fff" text-anchor="middle">HDMI0</text>'
    b += f'<text x="{x+155}" y="{y+h-12}" font-size="7.5" fill="#fff" text-anchor="middle">HDMI1</text>'
    # right edge: USB ports + Ethernet
    for i in range(2):
        b += f'<rect x="{x+w-14}" y="{y+22+i*50}" width="28" height="40" rx="3" fill="#bbb" stroke="{INK}"/>'
        b += f'<text x="{x+w-22}" y="{y+46+i*50}" font-size="7" fill="#fff" text-anchor="end">USB</text>'
    b += f'<rect x="{x+w-14}" y="{y+132}" width="28" height="52" rx="3" fill="#ddd" stroke="{INK}"/>'
    b += f'<text x="{x+w-22}" y="{y+162}" font-size="7" fill="#fff" text-anchor="end">LAN (unused)</text>'
    # left edge: LEDs + microSD (underside)
    b += f'<circle cx="{x+14}" cy="{y+60}" r="4" fill="#3f3"/><text x="{x+22}" y="{y+63}" font-size="7" fill="#fff">ACT (green)</text>'
    b += f'<circle cx="{x+14}" cy="{y+76}" r="4" fill="#f33"/><text x="{x+22}" y="{y+79}" font-size="7" fill="#fff">PWR</text>'
    b += f'<rect x="{x-10}" y="{y+95}" width="14" height="30" fill="#777" stroke="{INK}"/><text x="{x+8}" y="{y+114}" font-size="7" fill="#fff">microSD</text>'
    # MPK
    b += f'<rect x="690" y="40" width="190" height="80" rx="6" fill="{PANEL}" stroke="{INK}" stroke-width="1.5"/>'
    b += keyboard(698, 78, 174, 36, 15)
    b += f'<text x="785" y="62" font-size="11" fill="#fff" text-anchor="middle" font-weight="bold">AKAI MPK mini Plus</text>'
    b += f'<path d="M 700 120 C 700 170, {x+w+60} 160, {x+w+14} {y+42}" fill="none" stroke="{INK}" stroke-width="3"/>'
    b += f'<text x="640" y="205" font-size="9" fill="{INK}">USB cable</text><text x="640" y="217" font-size="8" fill="{GREY}">(MIDI + power for the MPK)</text>'
    # pedal
    b += f'<rect x="780" y="230" width="70" height="30" rx="4" fill="#444" stroke="{INK}"/><text x="815" y="275" font-size="9" text-anchor="middle">sustain pedal (optional)</text>'
    b += f'<path d="M 815 230 C 815 180, 850 150, 850 120" fill="none" stroke="{INK}" stroke-width="2" stroke-dasharray="4 3"/>'
    # Power
    b += f'<rect x="{x}" y="{y+h+40}" width="95" height="36" rx="6" fill="#fff" stroke="{INK}" stroke-width="1.5"/>'
    b += f'<text x="{x+47}" y="{y+h+56}" font-size="9" text-anchor="middle">27 W USB-C</text><text x="{x+47}" y="{y+h+68}" font-size="9" text-anchor="middle">power supply</text>'
    b += leader(x + 47, y + h + 10, x + 47, y + h + 40)
    # HDMI output
    b += f'<rect x="20" y="{y+h+30}" width="210" height="44" rx="6" fill="#fff" stroke="{INK}" stroke-width="1.5"/>'
    b += f'<text x="125" y="{y+h+48}" font-size="9" text-anchor="middle">TV / soundbar / AV receiver /</text><text x="125" y="{y+h+61}" font-size="9" text-anchor="middle">HDMI audio extractor</text>'
    b += f'<path d="M {x+105} {y+h+8} C {x+105} {y+h+30}, 260 {y+h+50}, 230 {y+h+52}" fill="none" stroke="{RED}" stroke-width="3"/>'
    b += f'<text x="240" y="{y+h+24}" font-size="9" fill="{RED}" font-weight="bold">micro-HDMI → HDMI</text>'
    # DAC+
    b += f'<rect x="{x+40}" y="30" width="200" height="60" rx="6" fill="#0f3d2e" stroke="{INK}" stroke-width="1.5" stroke-dasharray="5 3"/>'
    b += f'<text x="{x+140}" y="52" font-size="11" fill="#fff" text-anchor="middle" font-weight="bold">Raspberry Pi DAC+ (optional)</text>'
    b += f'<text x="{x+140}" y="66" font-size="8" fill="#ddd" text-anchor="middle">sits on the GPIO header (stacking header)</text>'
    for i, c in enumerate(["#eee", RED]):
        b += f'<circle cx="{x+75+i*30}" cy="80" r="6" fill="{c}" stroke="{INK}"/>'
    b += f'<text x="{x+125}" y="84" font-size="7" fill="#fff">L / R RCA · 3.5 mm phones</text>'
    b += leader(x + 140, 90, x + 140, y + 8)
    b += f'<rect x="20" y="40" width="210" height="44" rx="6" fill="#fff" stroke="{INK}" stroke-width="1.5"/>'
    b += f'<text x="125" y="58" font-size="9" text-anchor="middle">amplifier / mixer / active monitors</text><text x="125" y="71" font-size="9" text-anchor="middle">(line level, RCA)</text>'
    b += f'<path d="M {x+75} 74 C {x+20} 60, 260 60, 230 62" fill="none" stroke="{INK}" stroke-width="3"/>'
    # callouts
    for n, cx, cy in [("A", x + 47, y + h + 24), ("B", x + 105, y + h + 26), ("C", x + 155, y + h + 26),
                      ("D", x + w + 30, y + 10), ("E", x - 2, y + 60), ("F", x - 22, y + 110), ("G", x + 260, y + 16)]:
        b += callout(cx, cy, n, r=10, fill=INK, size=10)
    return svg(W, H, b, "fig")

def signal_flow():
    W, H = 900, 190
    b = ""
    blocks = [("DCO", "pulse / PWM · saw\nsub · noise\nrange 16'·8'·4'", 20),
              ("VCF", "24 dB/oct low-pass\nresonance · ENV\nLFO · KYBD", 190),
              ("VCA", "ENV or GATE", 360),
              ("HPF", "0 = bass boost\n1 = flat · 2 · 3", 530),
              ("CHORUS", "off · I · II · I+II\nstereo", 700)]
    for name, sub, x in blocks:
        b += f'<rect x="{x}" y="40" width="140" height="56" rx="4" fill="{INK}"/>'
        b += f'<text x="{x+70}" y="76" font-size="20" font-weight="bold" fill="#fff" text-anchor="middle" letter-spacing="2">{name}</text>'
        for j, ln in enumerate(sub.split("\n")):
            b += f'<text x="{x+70}" y="{114+j*13}" font-size="11" fill="{INK}" text-anchor="middle">{ln}</text>'
        if x < 700:
            b += f'<line x1="{x+140}" y1="68" x2="{x+190}" y2="68" stroke="{INK}" stroke-width="2"/><polygon points="{x+190},68 {x+182},63 {x+182},73" fill="{INK}"/>'
    b += f'<rect x="10" y="22" width="500" height="138" fill="none" stroke="{RED}" stroke-width="1.2" stroke-dasharray="5 3"/>'
    b += f'<text x="16" y="17" font-size="9.5" fill="{RED}" font-weight="bold">PER VOICE ×6</text>'
    b += f'<text x="530" y="17" font-size="9.5" fill="{GREY}" font-weight="bold">COMMON (after the voices are summed)</text>'
    b += f'<rect x="190" y="166" width="310" height="20" rx="3" fill="#fff" stroke="{INK}"/><text x="345" y="180" font-size="9.5" text-anchor="middle">ENV (one ADSR) · LFO (triangle, RATE, DELAY)</text>'
    b += f'<text x="890" y="80" font-size="9" text-anchor="end" fill="{INK}"></text>'
    return svg(W, H, b, "fig")

def led_icon(pattern):
    """Small timeline of the green ACT LED (list of (on, seconds))."""
    W = 220; H = 18; total = sum(d for _, d in pattern); x = 0; s = ""
    for on, d in pattern:
        w = W * d / total
        s += f'<rect x="{x:.1f}" y="3" width="{w:.1f}" height="12" fill="{"#2bb24c" if on else "#e5e5e5"}" stroke="#999" stroke-width="0.4"/>'
        x += w
    return svg(W, H, s, "led")

def callout_html(n, red=False):
    c = RED if red else INK
    return (f'<svg class="co" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="{c}"/>'
            f'<text x="12" y="16.3" font-size="12" font-weight="bold" text-anchor="middle" fill="#fff" font-family="{FONT}">{n}</text></svg>')
