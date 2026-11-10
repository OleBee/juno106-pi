import json, re, html, os
from pathlib import Path
REPO = Path(os.environ.get('JU6_REPO', Path(__file__).resolve().parents[2]))
from diagrams import *

T = json.load(open('tutorials.json'))
src = open(REPO / 'src/factory_bank.h').read()
NAMES = re.findall(r'\{"([AB]\d\d) ([^"]*)"', src)
assert len(NAMES) == 128

# Two knob sides, laid out like the MPK: K1–K4 on the top row, K5–K8 on the bottom.
S1 = ["ENV|A", "ENV|D", "ENV|S", "ENV|R", "DCO|SUB", "DCO|NOISE", "VCF|FREQ", "VCF|RES"]
S2 = ["DCO|LFO", "DCO|PWM", "LFO|RATE", "LFO|DELAY", "HPF|0·1·2·3", "VCF|ENV", "VCF|LFO", "VCF|KYBD"]
# Pad labels, index 0 = pad 1 (lower row, left). Pads 1–4 are the lower row.
SIDE1_PADS = [("PREVIOUS", "sound −1"), ("SIDE 2", "off on side 1"), ("LEVEL −", "VCA, step 8"), ("ENV / GATE", "red = ENV"),
              ("NEXT", "sound +1"), ("SIDE 1", "lit when active"), ("LEVEL +", "VCA, step 8"), ("CHORUS", "off · I · II · I+II")]
SIDE2_PADS = [("PREVIOUS", "sound −1"), ("SIDE 2", "lit when active"), ("PULSE", "red = on"), ("SAW", "red = on"),
              ("NEXT", "sound +1"), ("SIDE 1", "off on side 2"), ("ENV POL", "red = on"), ("LFO / MAN", "red = LFO")]

def pg(title, pages):  # generic page wrapper
    return pages

def sect(num, title):
    return f'<h1><span class="num">{num}</span>{title}</h1>'

def note(kind, text):
    return f'<div class="note {kind}"><b>{ {"note":"NOTE","warn":"CAUTION","issue":"KNOWN ISSUE","unv":"NOT VERIFIED"}[kind] }</b> {text}</div>'

def val10(v):  # 0..127 -> 0..10 scale for orientation
    return f"{v*10/127:.1f}"

def knob_fig(title, names, vals, subs):
    return knob_page(title, names, vals, subs)

def sides_for(key):
    """Map the old three-page factory numbers onto the two knob sides."""
    t = T[key]; L = t['lab']; a, b, c = t['p1'], t['p2'], t['p3']
    v1 = [a[3], a[4], a[5], a[6], b[5], b[6], a[0], a[1]]
    v2 = [b[1], b[2], c[0], c[1], c[4], a[2], c[2], b[7]]
    s1 = [str(x) for x in v1]
    if v1[4] == 0: s1[4] += " (off)"
    s2 = [str(x) for x in v2]
    s2[4] = f"{v2[4]} = HPF {L['hpf']}"
    pads = (f"pulse/saw {L['wave']} · PWM {L['pwmsrc']} · "
            f"CHORUS {L['chorus']} · VCA {L['vca']} · ENV polarity {L['envpol']} · LEVEL {c[6]} · RANGE stays {L['range']} (stored in the patch, not on a pad)")
    return v1, v2, s1, s2, pads

def tutorial(key, title, intro, steps):
    t = T[key]; v1, v2, s1, s2, pads = sides_for(key)
    h = f'<h2>{title}</h2><p>{intro}</p><ol class="steps">'
    for st in steps:
        h += f'<li>{st}</li>'
    h += '</ol>'
    h += '<div class="kp2">' + knob_fig("SIDE 1", S1, v1, s1) + knob_fig("SIDE 2", S2, v2, s2) + '</div>'
    h += f'<p class="cap">Pads for <b>{t["name"]}</b>: {pads}. LEVEL moves in steps of 8, so aim for the nearest step to the factory value. Knob numbers are 0–127, computed from <code>src/factory_bank.h</code> with the same scaling the synth uses when it loads a patch.</p>'
    return h

css = open('style.css').read()

H = []
# ---------------- COVER ----------------
H.append(f'''<section class="cover">
<div class="stripes"><i></i><i></i><i></i></div>
<div class="brand">JU-6 Pi</div>
<div class="sub">6-VOICE POLYPHONIC SYNTHESIZER · RASPBERRY PI 5</div>
<div class="om">OWNER'S MANUAL</div>
<div class="cover-fig">{mpk_top(False)}</div>
<div class="cover-foot">Software version 1.2.0 · Played from an AKAI MPK mini Plus over USB · Audio via HDMI or Raspberry Pi DAC+<br>
JU-6 Pi is an independent hobby project inspired by the Juno-106. It is not affiliated with or endorsed by Roland Corporation.</div>
</section>''')

# ---------------- CONTENTS ----------------
toc = [("1", "Introduction"), ("2", "Important Notes"), ("3", "Panel Descriptions"), ("4", "Connections"),
       ("5", "Power-up and Status LED"), ("6", "Playing"), ("7", "Selecting Patches"), ("8", "Knobs and Takeover"),
       ("9", "Creating Sounds"), ("10", "Writing (Saving) Patches"), ("11", "Audio Output and Latency"),
       ("12", "Settings File (ju6.conf)"), ("13", "MIDI Implementation"), ("14", "Parameter Chart"),
       ("15", "Patch List"), ("16", "Troubleshooting"), ("17", "Specifications"), ("18", "Sources and Credits")]
H.append('<section class="page"><h1 class="plain">Contents</h1><ol class="toc">' +
         "".join(f'<li><a href="#s{n}"><span>{n}</span>{t}</a></li>' for n, t in toc) + '</ol>'
         + note("note", "Everything in this manual about controls, MIDI numbers, patch memory, audio outputs and latency was taken from the JU-6 Pi v1.2.0 source code and README (repository <code>OleBee/juno106-pi</code>). Items that could not be confirmed are marked <b>NOT VERIFIED</b>.")
         + '</section>')

# ---------------- 1 INTRODUCTION ----------------
H.append(f'''<section class="page" id="s1">{sect(1, "Introduction")}
<p class="lead">Thank you for building the <b>JU-6 Pi</b>. It turns a Raspberry Pi 5 (8 GB) into a stand-alone, six-voice polyphonic synthesizer in the spirit of the classic 1984 Juno-106. There is no screen, no network and no setup: write the SD card, plug in an AKAI MPK mini Plus and an audio output, switch on and play.</p>
<p>The sound is generated in real time by the <b>Ultramaster KR-106</b> DSP engine (GPL-3), a component-level model of the Juno-106 calibrated against measurements of real hardware. JU-6 Pi wraps that engine in its own headless real-time program (<code>ju6pi</code>, C++17, direct ALSA, no JACK or PipeWire). No ROM dumps or samples are used — every sound is computed.</p>
<h2>Main features</h2>
<ul class="feat">
<li><b>6 voices</b> with Juno-106 style voice assignment (Poly I), plus Poly II and Unison.</li>
<li><b>DCO</b> with pulse (PWM from LFO, manual or ENV), sawtooth, sub-oscillator (square, one octave down), noise; RANGE 16' / 8' / 4'.</li>
<li><b>VCF</b> — 4-pole resonant low-pass that self-oscillates, with ENV (±polarity), LFO and keyboard follow; 2× or 4× oversampled.</li>
<li><b>HPF</b> with four positions; position 0 is the 106's bass boost.</li>
<li><b>VCA</b> switchable between ENV and GATE, with LEVEL. One <b>ADSR envelope</b> and a triangle <b>LFO</b> with RATE and DELAY.</li>
<li><b>Chorus</b> I, II and I+II, modelled as a bucket-brigade (BBD) circuit with companding and noise.</li>
<li><b>128 patch memories</b> (A11–B88) pre-loaded with the factory sounds, stored in genuine Juno-106 SysEx format.</li>
<li>Two <b>panel sides</b> on the MPK pads and knobs cover the Juno-106 sound parameters. Pad 6 and pad 2 select the side, and their LEDs show which side is active.</li>
<li>Read-only system on the SD card — you may pull the power at any time.</li>
</ul>
<p>To get the most out of the instrument, please read this manual from beginning to end. Keep it handy for later reference.</p>
<div class="cap">The DSP engine follows the Juno-106 closely, but JU-6 Pi is <i>not</i> a Roland product. "Roland" and "Juno" are trademarks of their respective owners and are used here only to describe what the synthesizer emulates.</div>
</section>''')

# ---------------- 2 IMPORTANT NOTES ----------------
H.append(f'''<section class="page" id="s2">{sect(2, "Important Notes")}
<h2>Power supply</h2>
<ul>
<li>Use the official Raspberry Pi <b>27 W USB-C</b> power supply (recommended in the project README). The Pi also powers the MPK mini Plus through its USB port.</li>
<li>The root file system is read-only (overlayroot). The only thing the synthesizer writes to is the <b>JU6DATA</b> partition, and it writes atomically (new file, fsync, rename). It is therefore safe to switch off simply by pulling the power — there is no shut-down procedure.</li>
</ul>
<h2>Placement and handling</h2>
<ul>
<li>Use the Pi with adequate cooling (the project is built around a Pi 5 with the <b>Active Cooler</b>; the audio thread keeps one CPU core busy and the CPU is held at full clock).</li>
<li>When fitting a DAC+ board, check that no GPIO pin is shifted by one row <b>before</b> applying power.</li>
<li>Do not connect or disconnect the DAC+ board while the Pi is powered.</li>
</ul>
<h2>Listening level</h2>
<ul>
<li>Turn down the amplifier, TV or monitors before switching on. Two short <b>ready tones</b> are played about 10–15 seconds after power-up.</li>
<li>The VCF can self-oscillate at high RES settings and the HPF bass boost (position 0) adds low end. Keep the volume moderate while experimenting.</li>
</ul>
<h2>Memory backup</h2>
<ul>
<li>Your patches are stored in <code>ju6/patches.syx</code> and <code>ju6/names.txt</code> on the JU6DATA partition. Put the SD card in a computer from time to time and copy these files to a safe place.</li>
<li>Deleting <code>patches.syx</code> and <code>names.txt</code> restores the factory sounds.</li>
</ul>
<h2>What is not on board</h2>
<p>For a clean, fast boot the image has Wi-Fi, Bluetooth, SSH, NetworkManager, cloud-init, avahi, cron, apt timers and swap switched off. The system log is kept in RAM only. All configuration is done by editing a text file on the SD card (see section 12).</p>
{note("warn", "This manual describes software version <b>1.2.0</b>. The panel is two sides (section 3). Sounds are chosen one patch at a time with pad 5 and pad 1. The panel does not write patches and has no transpose control. DAC+ support arrived in 1.1.0.")}
</section>''')

# ---------------- 3 PANEL DESCRIPTIONS ----------------
H.append(f'''<section class="page" id="s3">{sect(3, "Panel Descriptions")}
<p>JU-6 Pi has no panel of its own — the <b>AKAI MPK mini Plus</b> is its front panel. The numbers below refer to the drawing; only controls that JU-6 Pi uses are numbered.</p>
<div class="fig-wrap">{mpk_top()}</div>
<p class="cap">AKAI MPK mini Plus, top and rear panel (drawing based on the Top/Rear Panel figures in AKAI's MPK mini Plus User Guide v1.2; simplified, not to scale). Note that pads 1–4 are the <b>lower</b> row and pads 5–8 the <b>upper</b> row.</p>
<table class="callouts">
<tr><td>{callout_html(1)}</td><td><b>Keyboard</b> — 37 keys. Plays JU-6 Pi on every MIDI channel (omni). Velocity is ignored by default, like the original. Also used to set the key with TRANSPOSE (pad bank B, pad 8).</td></tr>
<tr><td>{callout_html(2, True)}</td><td><b>Pitch wheel</b> — BENDER. Bends the DCO (default depth 0.25 ≈ ±2 semitones) and optionally the VCF. Depths are <code>bender_dco</code> and <code>bender_vcf</code> in <code>ju6.conf</code>.</td></tr>
<tr><td>{callout_html(3, True)}</td><td><b>Modulation wheel</b> (CC 1) — MOD: LFO vibrato on the DCO. Depth follows how far the wheel is moved (scaled by <code>mod_depth</code>, default 0.5).</td></tr>
<tr><td>{callout_html(4, True)}</td><td><b>X-Y joystick</b> — JU-6 Pi reacts to whatever the joystick sends: <b>Pitch Bend</b> acts as BENDER, <b>CC 1</b> acts as MOD. Other CC numbers are ignored unless listed in <code>mod_cc</code>. <span class="unv">NOT VERIFIED: which messages the joystick sends in the MPK's default program.</span></td></tr>
<tr><td>{callout_html(5, True)}</td><td><b>OCT − / OCT +</b> — handled inside the MPK; shifts the keyboard range. Press both to return to the centre octave.</td></tr>
<tr><td>{callout_html(6, True)}</td><td><b>Pads 1–8</b> — the two panel sides below. Bank A and bank B send different notes, and both are the same panel. <b>Pad 6</b> (upper row) selects SIDE 1. <b>Pad 2</b> (lower row, directly under pad 6) selects SIDE 2. The pad for the active side stays lit strong red; the other stays off. <b>Pad 5</b> is the next sound and <b>pad 1</b> the previous sound.</td></tr>
<tr><td>{callout_html(7, True)}</td><td><b>BANK A/B</b> — switches which notes the pads send. JU-6 Pi treats both banks as this panel, so the layout does not change. LEDs are sent for both banks’ notes.</td></tr>
<tr><td>{callout_html(8, True)}</td><td><b>Knobs K1–K8</b> (CC 70–77) — sound parameters. What each knob does depends on the selected side (below).</td></tr>
<tr><td>{callout_html(9, True)}</td><td><b>USB port</b> — connect to any USB port on the Pi. Carries MIDI and powers the MPK.</td></tr>
<tr><td>{callout_html(10, True)}</td><td><b>Sustain input</b> — a sustain pedal (CC 64) works as HOLD.</td></tr>
</table>
{note("note", "The other MPK functions (arpeggiator, scales, chords, note repeat, sequencer, transport buttons, CV/Gate, 5-pin MIDI) are run by the MPK itself. They are not used or tested by JU-6 Pi; any notes they produce over USB are simply played. OCT −/+ still shift the keyboard inside the MPK. DCO RANGE is stored in each patch and is not on the panel. The modulation wheel is still LFO vibrato on the DCO.")}
</section>''')

# ---------------- 3c two sides ----------------
H.append(f'''<section class="page">
<h2>The two sides</h2>
<p>JU-6 Pi starts on <b>SIDE 1</b>. On pad bank B, press <b>pad 6</b> for SIDE 1 or <b>pad 2</b> for SIDE 2. Both presses work from either side. The green ACT LED on the Pi blinks once for SIDE 1 and twice for SIDE 2.</p>
<p><b>The page pads themselves show which side is active.</b> While SIDE 1 is selected, pad 6 stays lit strong red and pad 2 stays off. While SIDE 2 is selected, pad 2 stays lit strong red and pad 6 stays off. Switching sides updates these two LEDs immediately, together with the LEDs of the pads whose job changes. The same two notes are sent for bank A and bank B, so the active side stays visible after you press BANK A/B.</p>
{note("note", "The sketch names pad 2 and pad 6 as the page switches and draws SIDE 1 above SIDE 2. It does not spell out which pad is which. Pad 6 is the upper pad of the pair and selects the upper side; pad 2, directly beneath it, selects SIDE 2.")}
<div class="kp2">{side_pads("SIDE 1", SIDE1_PADS, "lower row = pads 1–4")}{side_pads("SIDE 2", SIDE2_PADS, "same next/previous and page pads")}</div>
<p class="cap">A <b>sound</b> is one patch memory: slot 0 is A11, slot 7 is A18, slot 8 is A21, slot 63 is A88, slot 64 is B11 and slot 127 is B88. Next adds one and wraps from B88 to A11. Previous subtracts one and wraps from A11 to B88. The step crosses group and bank boundaries. The Pi LED does not blink for a sound step; it blinks only when the side changes.</p>
<div class="kp2">{knob_page("SIDE 1  ·  K1–K4 top, K5–K8 bottom", S1)}{knob_page("SIDE 2  ·  K1–K4 top, K5–K8 bottom", S2)}</div>
<h2>What the pad LEDs mean</h2>
<p>Brightness is one red lamp in four steps: <b>off</b>, <b>weak red</b>, <b>red</b>, <b>strong red</b>. On a page change, every pad LED is set again for the side you just selected.</p>
<table class="grid small">
<tr><th>Pad</th><th>SIDE 1</th><th>SIDE 2</th></tr>
<tr><td>6 / 2</td><td colspan="2">The active side is <b>strong red</b>. The other page pad is <b>off</b>. This pair is updated on every page change and is sent for both pad banks.</td></tr>
<tr><td>5 and 1</td><td colspan="2"><b>Next sound</b> (pad 5) and <b>previous sound</b> (pad 1). One patch per press, wrapping through all 128. The LEDs stay off. Both sides.</td></tr>
<tr><td>7 and 3</td><td><b>VCA LEVEL +</b> (pad 7) and <b>LEVEL −</b> (pad 3). Each press moves the level by 8; holding repeats. Both LEDs show the level: weak red at 0, strong red at 127, scaled in between.</td><td>Pad 7 = <b>VCF polarity</b>. Red = on (inverted), unlit = off (normal). Pad 3 = <b>pulse</b> on/off: red = on, unlit = off.</td></tr>
<tr><td>8 and 4</td><td>Pad 8 = <b>CHORUS</b>, each press cycles off → I → II → I+II → off. LED off / weak red / red / strong red. Pad 4 = <b>ENV / GATE</b>. Red = ENV, unlit = GATE.</td><td>Pad 8 = <b>PWM LFO / MAN</b>. Red = LFO, unlit = MAN. Pad 4 = <b>saw</b> on/off. Red = on, unlit = off. Pulse and saw are independent.</td></tr>
</table>
{note("unv", "Pad LEDs are sent as Note On (pad channel, the pad’s note, velocity 0 = off, 42 = weak red, 84 = red, 127 = strong red) to USB-MIDI ports whose name contains “MPK”, never to a port named MIDI 2. AKAI’s MPK mini Plus User Guide v1.2 only documents colours stored in the program, not live feedback, so this has <b>not been verified on the hardware</b>. If the pads do not respond, set <code>pad_leds = off</code>. The Pi’s ACT LED still blinks the side number. <code>pad_leds = any</code> sends the same notes to every MIDI output except MIDI 2.")}
{note("note", "A patch can store PWM from the envelope. The LFO/MAN pad only selects LFO or MAN: if the patch is on ENV the LED stays off, and the next press selects LFO. Loading the patch again brings ENV back. Voice mode, velocity, portamento, bender depths and MOD depth are not on the panel; they stay as set in <code>ju6.conf</code>. CC 7 is still the master volume, and a sustain pedal (CC 64) is still HOLD.")}
</section>''')

# ---------------- 3b Pi panel ----------------
H.append(f'''<section class="page">
<h2>Raspberry Pi 5 (the sound module)</h2>
<div class="fig-wrap">{pi5_connections()}</div>
<p class="cap">Simplified connection drawing (not to scale). The DAC+ board is optional.</p>
<table class="callouts">
<tr><td>{callout_html("A")}</td><td><b>USB-C power</b> — 27 W supply recommended.</td></tr>
<tr><td>{callout_html("B")}</td><td><b>HDMI0</b> (micro-HDMI, the port <b>nearest the USB-C power connector</b>) — primary HDMI audio output.</td></tr>
<tr><td>{callout_html("C")}</td><td><b>HDMI1</b> — used automatically as a reserve if HDMI0 is not available.</td></tr>
<tr><td>{callout_html("D")}</td><td><b>USB ports</b> — MPK mini Plus (any port). Other class-compliant USB-MIDI devices are connected automatically and can be hot-plugged. A USB audio interface can be used as an output.</td></tr>
<tr><td>{callout_html("E")}</td><td><b>ACT LED (green)</b> — the synthesizer's status display (section 5).</td></tr>
<tr><td>{callout_html("F")}</td><td><b>microSD slot</b> — the JU-6 Pi card (system + JU6DATA partition).</td></tr>
<tr><td>{callout_html("G")}</td><td><b>40-pin GPIO header</b> — mount the optional Raspberry Pi DAC+ here (on a stacking header if you use the Active Cooler).</td></tr>
</table>
<h2>Raspberry Pi DAC+ (optional)</h2>
<p>The <b>Raspberry Pi DAC+</b> (formerly IQaudIO DAC+) is a sound card that sits on the GPIO pins. It has a TI PCM5122 converter, two RCA line outputs (0–2 V RMS) and a 3.5 mm headphone output carrying the same stereo signal. It has no input. Older black IQaudIO DAC+ boards work with the same overlay.</p>
{note("note", "<b>HiFiBerry DAC+:</b> from v1.1.1 the ALSA card of a HiFiBerry DAC+ (<code>snd_rpi_hifiberry_dacplus</code>) is recognised as a DAC+ output. The image still loads only the <code>rpi-dacplus</code> overlay, so for a HiFiBerry board change the line <code>dtoverlay=rpi-dacplus</code> in <code>config.txt</code> on the boot partition to <code>dtoverlay=hifiberry-dacplus</code>. NOT VERIFIED on hardware. This manual describes the Raspberry Pi DAC+.")}
</section>''')

# ---------------- 4 CONNECTIONS ----------------
H.append(f'''<section class="page" id="s4">{sect(4, "Connections")}
{note("warn", "To prevent damage, turn the volume of your amplifier or TV all the way down and leave the Pi unpowered while making connections.")}
<h2>Preparing the SD card</h2>
<ol class="steps">
<li>Download <code>ju6pi-1.2.0.img.xz</code> from the project's Releases page. If it is split into <code>.part-aa</code>, <code>.part-ab</code> … join the parts first (<code>cat ju6pi-1.2.0.img.xz.part-* &gt; ju6pi-1.2.0.img.xz</code>) and check it with <code>sha256sum -c ju6pi-1.2.0.img.xz.sha256</code>.</li>
<li>Write it to a microSD card (8 GB or more). <b>Raspberry Pi Imager:</b> Choose Device → Raspberry Pi 5; Choose OS → Use Custom → the .img.xz file; Choose Storage → the card. When asked about OS customisation, answer <b>No</b>. <b>balenaEtcher:</b> Flash from file → Select target → Flash!</li>
<li>Insert the card into the Pi.</li>
</ol>
<h2>Connecting the equipment</h2>
<ol class="steps">
<li><b>Audio, with DAC+:</b> connect the RCA outputs to an amplifier, mixer or active monitors. The synthesizer uses the board automatically when it is fitted.</li>
<li><b>Audio, without DAC+:</b> connect <b>HDMI0</b> — the micro-HDMI port nearest the USB-C power connector — to a TV, soundbar, AV receiver or HDMI audio extractor. No screen is needed; the image supplies its own EDID and forces stereo PCM at 48 kHz on both ports.</li>
<li><b>Controller:</b> connect the AKAI MPK mini Plus to any USB port on the Pi.</li>
<li>Optionally connect a sustain pedal to the MPK's SUSTAIN input.</li>
<li>Connect the USB-C power supply last.</li>
</ol>
<h2>Mounting the DAC+ in a KKSB case with Active Cooler</h2>
<ol class="steps">
<li>Fit the Active Cooler and connect its cable to the FAN connector.</li>
<li>Press the 40-pin stacking header supplied with the case onto the GPIO pins; it lifts the DAC above the cooler.</li>
<li>Fit the DAC+ on top with its RCA sockets towards the case openings, and secure it with the supplied standoffs and screws.</li>
<li>Check that no pin is offset by a row before switching on.</li>
</ol>
{note("note", "An HDMI audio extractor typically adds 0–2 ms. TVs and AV receivers can add 20–100 ms of their own processing — choose a <b>Game</b>, <b>Direct</b> or <b>Pure</b> mode on such devices.")}
</section>''')

# ---------------- 5 POWER UP ----------------
on, off = True, False
leds = [
 ("Slow blinking (1 Hz)", [(on, .5), (off, .5)] * 3, "Starting up, or waiting for an audio output."),
 ("Steady on", [(on, 3)], "Ready to play."),
 ("On, two short gaps every 3 s", [(off, .15), (on, .15), (off, .15), (on, 2.55)] * 1, "Ready, but on a <b>reserve output</b>: <code>audio_output = dacplus</code> is set and the DAC+ was not found."),
 ("On, one short gap every 2 s", [(on, 1.8), (off, .2)] * 2, "Ready, but <b>no MIDI device</b> found — check the MPK's USB cable."),
 ("Rapid blinks", [(on, .09), (off, .09)] * 6, "Side or group changed (one blink = SIDE 1, two blinks = SIDE 2, or the group number 1–8), or a patch written (5 blinks)."),
]
ledrows = "".join(f'<tr><td>{led_icon(p)}</td><td><b>{a}</b></td><td>{c}</td></tr>' for a, p, c in leds)
H.append(f'''<section class="page" id="s5">{sect(5, "Power-up and Status LED")}
<ol class="steps">
<li>Turn the amplifier or TV volume down.</li>
<li>Connect the power supply. The green ACT LED blinks slowly while the system starts.</li>
<li>After about <b>10–15 seconds</b> two short <b>rising</b> ready tones (A–E) are heard and the LED lights steadily. The synthesizer is now ready.</li>
<li>Raise the volume gradually while playing.</li>
</ol>
<p>The last selected patch is recalled at power-up (it is remembered in <code>ju6/state.txt</code>; on the very first start, <code>start_patch</code> decides). The program is a systemd service that restarts automatically within one second if it ever stops.</p>
<h2>Status LED (green ACT LED on the Pi)</h2>
<table class="grid led">{ledrows}</table>
<p>If the ready tones are <b>falling</b> (E–A) instead of rising, the synthesizer is playing on a reserve output because the DAC+ you asked for was not found (see section 11).</p>
<h2>Checking without a screen</h2>
<p>Every few seconds the synthesizer writes <code>ju6/status.txt</code> on the JU6DATA partition: software version, chosen audio output, sound cards found, buffer size and latency, VCF oversampling, number of MIDI devices and underrun count. Put the SD card in a computer to read it. With DAC+ it should contain lines like:</p>
<pre>lyd: Raspberry Pi DAC+ (RCA/hodetelefon) (plughw:CARD=RPiDAC,DEV=0)
lydkort funnet: vc4hdmi0, vc4hdmi1, RPiDAC</pre>
<p class="cap">The status file is written in Norwegian: <i>lyd</i> = audio, <i>lydkort funnet</i> = sound cards found, <i>ADVARSEL</i> = warning.</p>
</section>''')

# ---------------- 6 PLAYING ----------------
H.append(f'''<section class="page" id="s6">{sect(6, "Playing")}
<h2>Keyboard</h2>
<p>The keyboard plays on all MIDI channels (<code>key_channel = omni</code>); only the pad notes on the pad channel are reserved. <b>Velocity is off</b> by default, as on the original; switch it on with <code>velocity = on</code>. Use the MPK's OCT −/+ buttons to reach higher and lower octaves. Those buttons do not change DCO RANGE. There is no transpose control on the panel: a key always plays.</p>
<h2>BENDER (pitch wheel / joystick X)</h2>
<p>Pitch Bend bends the DCO pitch by up to ±2 semitones (default <code>bender_dco = 0.25</code>) and, if set, the VCF cutoff (default <code>bender_vcf = 0</code>). The depths are set in <code>ju6.conf</code>.</p>
<h2>MOD (mod wheel / CC 1)</h2>
<p>MOD applies LFO vibrato to the DCO. Unlike the 106's spring-loaded lever with fixed depth, MOD here is <b>continuous</b>: the depth follows how far the wheel or joystick is pushed, scaled by <code>mod_depth</code> (default 0.5). The LFO runs in AUTO mode (it fades in after a key, using LFO DELAY on SIDE 2).</p>
<h2>HOLD</h2>
<p>A sustain pedal (CC 64) holds the notes while pressed. There is no HOLD pad on the two sides; CC 120 or 123 silences hung notes.</p>
<h2>Voice modes</h2>
<table class="grid">
<tr><th>Mode</th><th><code>voice_mode</code></th><th>Description</th></tr>
<tr><td><b>Poly I</b> (default)</td><td>1</td><td>Juno-106 voice assignment, as on the hardware.</td></tr>
<tr><td><b>Poly II</b></td><td>2</td><td>Alternative polyphonic assignment (an addition — not on the 106).</td></tr>
<tr><td><b>Unison</b></td><td>0</td><td>All voices on one note (an addition — not on the 106).</td></tr>
</table>
<p>PORTAMENTO is not on the panel and starts at 0. Neither portamento, Unison nor velocity exist on the original instrument. They are not stored in a patch.</p>
<h2>Other controls</h2>
<p>MIDI CC 7 sets the master volume. CC 120 and 123 silence all notes; CC 121 resets bender and MOD.</p>
</section>''')

# ---------------- 7 SELECTING PATCHES ----------------
H.append(f'''<section class="page" id="s7">{sect(7, "Selecting Patches")}
<p>As on the 106, the 128 memories are organised as two <b>banks</b> (A and B), each with eight <b>groups</b> of eight <b>patches</b>: A11 … A88 and B11 … B88. The first digit is the group, the second the patch number.</p>
<div class="fig-wrap">{pad_map()}</div>
<p class="cap">Both MPK pad banks are this panel. Pad 5 steps forward one sound. Pad 1 steps back one sound. Pad 6 stays lit on SIDE 1; pad 2 stays lit on SIDE 2.</p>
<h2>What a sound is</h2>
<p>A sound is <b>one patch</b>, not a group of eight. The 128 memories stay numbered as on the 106 — two banks, eight groups, eight patches — but next and previous move a single step:</p>
<table class="grid small">
<tr><th>Slot</th><th>Name</th><th>Next</th><th>Previous</th></tr>
<tr><td>0</td><td>A11</td><td>A12</td><td>B88</td></tr>
<tr><td>7</td><td>A18</td><td>A21</td><td>A17</td></tr>
<tr><td>63</td><td>A88</td><td>B11</td><td>A87</td></tr>
<tr><td>127</td><td>B88</td><td>A11</td><td>B87</td></tr>
</table>
<p>The step crosses from patch 8 of a group into patch 1 of the next group, and from A88 into B11. It loads the stored patch and keeps the master volume. Knob edits that were not part of that memory are replaced. The Pi’s green LED does not blink for this; it blinks only for a side change (one blink = SIDE 1, two = SIDE 2).</p>
<p><b>Example:</b> from A11, press NEXT seven times to reach A18, once more to reach A21. Thirty-nine presses from A11 reach A48 Synth Bass I. PREVIOUS from A11 lands on B88.</p>
<h2>Program Change</h2>
<p>MIDI Program Change 0–127 selects A11 … B88 directly (0 = A11, 63 = A88, 64 = B11, 127 = B88). The MPK can send program changes from its pads (pad Play Mode "ProgCh" in the MPK's program editor, per AKAI's guide).</p>
<h2>SysEx</h2>
<p>A Juno-106 patch dump (APR, <code>F0 41 30 0n …</code>) or single-parameter message (IPR, <code>F0 41 32 0n …</code>) received over MIDI is loaded into the current sound, just as on a 106. This lets you audition sounds from Juno-106 editors and librarians.</p>
<h2>Master volume across patches</h2>
<p>Selecting a patch changes every sound parameter but keeps the master volume where it was. Pad LEDs are refreshed to match the new sound and the side you are on, including pad 2 and pad 6.</p>
</section>''')

# ---------------- 8 KNOB PAGES ----------------
H.append(f'''<section class="page" id="s8">{sect(8, "Knobs and Takeover")}
<p>The eight knobs send <b>CC 70–77</b> (K1–K4 on the top row, K5–K8 on the bottom). Their function is the side selected with pad 6 or pad 2 (section 3). SIDE 1 is active after power-up. The drawings of both sides are in section 3.</p>
<h2>The one switched knob</h2>
<p>Most knobs are continuous, 0–127. Two are not:</p>
<table class="grid small">
<tr><th>Control</th><th>How it moves</th></tr>
<tr><td>SIDE 1, K5 SUB</td><td>0 = sub off; 1–127 = sub level</td></tr>
<tr><td>SIDE 2, K5 HPF</td><td>0–31 position 0 (bass boost) · 32–63 position 1 (flat) · 64–95 position 2 · 96–127 position 3</td></tr>
</table>
<p>Chorus, pulse, saw, PWM source, VCA mode and envelope polarity are pads, not knobs (section 3). DCO RANGE is stored in the patch and has no panel control.</p>
<h2>Knob behaviour</h2>
<p>By default the knobs <b>jump</b>: the parameter takes the knob's value as soon as the knob is moved (<code>knob_takeover = jump</code>). With <code>knob_takeover = pickup</code> a knob does nothing until it passes the current value (soft takeover; this resets on every side or patch change). With <code>knob_mode = relative</code> JU-6 Pi reads the knobs as relative (two's complement: 1–63 = up, 65–127 = down). <span class="unv">NOT VERIFIED: that this matches the MPK mini Plus's own "Relative" knob mode.</span></p>
</section>''')

# ---------------- 9 CREATING SOUNDS ----------------
H.append(f'''<section class="page" id="s9">{sect(9, "Creating Sounds")}
<p>Each of the six voices has its own DCO, VCF and VCA. The voices are summed and pass through the common HPF and chorus. A single envelope (ENV) and a single LFO control all voices.</p>
<div class="fig-wrap">{signal_flow()}</div>
<table class="grid small">
<tr><th>Section</th><th>What it does</th><th>Where</th></tr>
<tr><td><b>DCO</b></td><td>The sound source. Pulse (width set by PWM, from LFO or set manually), sawtooth, sub-oscillator one octave down, and noise are mixed. RANGE is the octave stored in the patch. DCO LFO adds vibrato.</td><td>SIDE 2, plus SUB and NOISE on SIDE 1</td></tr>
<tr><td><b>VCF</b></td><td>Low-pass filter, 24 dB/octave. FREQ = cutoff, RES = resonance (self-oscillates near maximum), ENV = how much the envelope opens the filter, LFO = filter wobble, KYBD = cutoff follows the keyboard. Polarity is the SIDE 2 pad (red = inverted).</td><td>Both sides</td></tr>
<tr><td><b>VCA</b></td><td>Loudness. ENV: follows the ADSR. GATE: full level while a key is held. LEVEL sets the patch volume (about −10 … +10 dB), in steps of 8 from the LEVEL pads.</td><td>SIDE 1 pads</td></tr>
<tr><td><b>ENV</b></td><td>One ADSR envelope with Juno-106 curves: A = attack, D = decay, S = sustain level, R = release.</td><td>SIDE 1, K1–K4</td></tr>
<tr><td><b>LFO</b></td><td>Triangle wave. RATE = speed, DELAY = fade-in time after a key is pressed.</td><td>SIDE 2, K3–K4</td></tr>
<tr><td><b>HPF</b></td><td>Position 0 = bass boost (about +9.4 dB low shelf), 1 = flat, 2 ≈ 236 Hz, 3 ≈ 754 Hz high-pass.</td><td>SIDE 2, K5</td></tr>
<tr><td><b>Chorus</b></td><td>I = slow, wide; II = faster, deeper; I+II = a third, distinct mode (fast, shallow, vibrato-like). The pad cycles off → I → II → I+II.</td><td>SIDE 1, pad 7</td></tr>
</table>
<h2>How to use the tutorials</h2>
<p>There is no "initialise patch" function, so every tutorial lists the knobs on both sides and the pad states. Select the side with pad 6 or pad 2, then turn each knob until it sends the target value (0–127). The patches are re-creations of factory sounds, so you can recall the original from bank A at any time to compare — but note that this replaces what you have dialled in.</p>
{note("note", "Start from a patch in a group you don't mind experimenting in. Because the knobs jump by default, each knob must actually be turned at least a little so it sends its value.")}
</section>''')

H.append(f'''<section class="page">
{tutorial("A48", "Tutorial 1 — Synth bass (A48 Synth Bass I)",
 "A punchy, mono-style bass made from a narrow pulse, a strong sub-oscillator and a short filter envelope.",
 ["Recall A48 first (or step to it) so DCO RANGE is already 16'. SIDE 2: pad 3 pulse on (red), pad 4 saw off, pad 8 LFO/MAN unlit (MAN). Knob PWM (K2) = 69. DCO LFO (K1) = 1.",
  "SIDE 1: sub-oscillator K5 = 102 for weight, and a touch of NOISE (K6 = 50) for attack. Filter closed: FREQ 32, RES 0.",
  "SIDE 2: let the envelope open the filter (VCF ENV 66). KYBD 35. HPF position 0 (K5 = 16) for the bass boost. LFO RATE 58, DELAY 16, VCF LFO 0.",
  "SIDE 1: envelope A = 0, D = 34, S = 0, R = 36 — a plucked shape with no sustain. CHORUS (pad 8) until the LED is off. ENV/GATE (pad 4) until it is red (ENV). LEVEL pads (7 and 3) toward 75 (steps of 8; 72 or 80 is close).",
  "Play low on the keyboard. Try more RES or VCF ENV for a squelchier bass."])}
</section>''')
H.append(f'''<section class="page">
{tutorial("B11", "Tutorial 2 — Strings (B11 Strings)",
 "A classic ensemble: pulse and saw together, slowly swept by the LFO, softened by the envelope and widened by chorus II.",
 ["Recall B11 first so RANGE is already 8'. SIDE 2: pad 3 and pad 4 both on (pulse and saw, both red). Pad 8: LFO/MAN red (LFO), PWM knob 67 — the LFO sweeps the pulse width. VCF KYBD 108. HPF position 0 (K5 = 16). LFO RATE 57, DELAY 45, VCF LFO 0. VCF ENV 0.",
  "SIDE 1: SUB 0 (off), NOISE 0. Open the filter fairly far (FREQ 85), RES 0 — the tone stays constant.",
  "SIDE 1: slow envelope: A = 59, D = 32, S = 86, R = 40. CHORUS (pad 8) until the LED is red (II). Compare with weak red (I) and strong red (I+II).",
  "ENV/GATE pad red (ENV). LEVEL pads toward 52.",
  "Play chords. Raise ENV A for slower bowing, or ENV R for longer tails."])}
</section>''')
H.append(f'''<section class="page">
{tutorial("A11", "Tutorial 3 — Brass (A11 Brass)",
 "Synth brass relies on a sawtooth and a filter that opens with the envelope and settles back, giving the 'blat' of a horn attack.",
 ["Recall A11 first so RANGE is already 16'. SIDE 2: pad 4 saw on (red), pad 3 pulse off, pad 8 unlit (MAN). The PWM knob has no audible effect while the pulse is off. VCF KYBD 86. VCF ENV 58 — the envelope does the work. LFO RATE 20, DELAY 49, VCF LFO 0. HPF position 1 = flat (K5 = 48).",
  "SIDE 1: SUB 0, NOISE 0. FREQ 35, RES 13. Envelope A = 3, D = 49, S = 45, R = 32: fast attack, the filter falls back to a sustained level.",
  "CHORUS (pad 8) until the LED is weak red (I). ENV/GATE (pad 4) red (ENV). LEVEL pads toward 108.",
  "Use the mod wheel for vibrato on held notes. For a slower swell, raise ENV A to about 60."])}
</section>''')

# ---------------- 10 WRITING ----------------
H.append(f'''<section class="page" id="s10">{sect(10, "Writing (Saving) Patches")}
<p>The two-page panel does not write patches. Next and previous load the stored sound; they do not keep unsaved knob edits in the memory you just left. A file already on the card is still read at power-up. In 1.1.1 a held bank-A pad wrote the edited sound; that gesture is gone.</p>
<ol class="steps">
<li>Edit the sound with the knobs and pads.</li>
<li>To hear a stored memory again, step to it with pad 5 or pad 1, or send Program Change.</li>
<li>Stepping away replaces the edit with the stored patch. The master volume stays where it was.</li>
</ol>
{note("note", "1.1.1 wrote a patch when a bank-A pad was held. 1.2.0 does not. <code>patches.syx</code> on the card is still loaded if it is there; deleting it restores the factory sounds.")}
<h2>Patch files on the JU6DATA partition</h2>
<table class="grid small">
<tr><th>File</th><th>Contents</th></tr>
<tr><td><code>ju6/patches.syx</code></td><td>All 128 memories as standard Juno-106 SysEx (APR) messages; created the first time you write. Can be opened in Juno-106 editors.</td></tr>
<tr><td><code>ju6/names.txt</code></td><td>One line per user patch: <code>A11&lt;TAB&gt;name[&lt;TAB&gt;ext]</code>. <i>ext</i> bit 0 = chorus I+II, bit 1 = PWM from ENV.</td></tr>
<tr><td><code>ju6/fabrikk-A-B.syx</code></td><td>Copy of factory banks A and B for reference.</td></tr>
<tr><td><code>ju6/state.txt</code></td><td>Last selected patch and buffer setting (automatic).</td></tr>
<tr><td><code>ju6/status.txt</code></td><td>What the synth found at the last start-up.</td></tr>
<tr><td><code>ju6/ju6.conf</code></td><td>Your settings (section 12).</td></tr>
</table>
<h2>Juno-106 format compatibility</h2>
<p>The Juno-106 patch format has no room for chorus <b>I+II</b> or <b>PWM from ENV</b>. JU-6 Pi stores these in the extra column of <code>names.txt</code>, so they come back on JU-6 Pi; a real 106 or an editor sees the nearest valid setting (chorus I, PWM MAN).</p>
<h2>Restoring factory sounds</h2>
<p>Delete <code>patches.syx</code> and <code>names.txt</code> from the JU6DATA partition. Deleting <code>state.txt</code> resets the last-patch and buffer memory.</p>
</section>''')

# ---------------- 11 AUDIO ----------------
H.append(f'''<section class="page" id="s11">{sect(11, "Audio Output and Latency")}
<p>The output is chosen with <code>audio_output</code> in <code>ju6/ju6.conf</code>. Cards are found by name, not number, so ALSA's card order doesn't matter.</p>
<table class="grid">
<tr><th><code>audio_output</code></th><th>Behaviour</th></tr>
<tr><td><code>auto</code> (default)</td><td>Raspberry Pi DAC+ if fitted, otherwise HDMI0, then HDMI1, then a USB audio interface.</td></tr>
<tr><td><code>dacplus</code></td><td>Raspberry Pi DAC+. If it is missing, plays on HDMI0/HDMI1/USB but warns: falling ready tones, LED with two short gaps every 3 s, and an <code>ADVARSEL</code> (warning) line in <code>status.txt</code>.</td></tr>
<tr><td><code>hdmi</code></td><td>Only HDMI0, then HDMI1 — exactly as in 1.0.0. The DAC+ is ignored even if fitted.</td></tr>
<tr><td><code>usb</code></td><td>Only a USB audio interface.</td></tr>
<tr><td><code>null</code></td><td>No audio (testing).</td></tr>
</table>
<p>At start-up the synth waits up to <code>dacplus_wait</code> = 8 s for the DAC driver when the board's HAT EEPROM reports a DAC or <code>audio_output = dacplus</code>. If it started on HDMI and the DAC+ appears within the first minute, it switches over and plays the ready tones again there. DAC+ output is 48 kHz, 32-bit; the mixer is set to 0 dB at start-up (2 V RMS). Lower it with <code>dacplus_volume_db</code> (0 or negative). HDMI output is 2-channel PCM at 48 kHz.</p>
<h2>Buffer sizes (48 kHz)</h2>
<p>The synth starts with the smallest buffer and moves up one step automatically after repeated underruns (3 or more within 30 s). The step is remembered for the next start.</p>
<table class="grid small c">
<tr><th>Step</th><th>HDMI</th><th>HDMI buffer</th><th>DAC+</th><th>DAC+ buffer</th><th>USB</th><th>USB buffer</th></tr>
<tr><td>1 (start)</td><td>256 × 2</td><td><b>10.7 ms</b></td><td>128 × 2</td><td><b>5.3 ms</b></td><td>64 × 2</td><td><b>2.7 ms</b></td></tr>
<tr><td>2</td><td>256 × 3</td><td>16.0 ms</td><td>128 × 3</td><td>8.0 ms</td><td>128 × 2</td><td>5.3 ms</td></tr>
<tr><td>3</td><td>512 × 2</td><td>21.3 ms</td><td>256 × 2</td><td>10.7 ms</td><td>128 × 3</td><td>8.0 ms</td></tr>
<tr><td>4</td><td>512 × 3</td><td>32.0 ms</td><td>256 × 3</td><td>16.0 ms</td><td>256 × 2</td><td>10.7 ms</td></tr>
<tr><td>5</td><td>1024 × 2</td><td>42.7 ms</td><td>512 × 2</td><td>21.3 ms</td><td>256 × 3</td><td>16.0 ms</td></tr>
<tr><td>6</td><td>1024 × 3</td><td>64.0 ms</td><td>512 × 3</td><td>32.0 ms</td><td>512 × 2</td><td>21.3 ms</td></tr>
</table>
<p class="cap">Period × number of periods, from <code>src/audio_out.h</code>. A fixed size can be forced with e.g. <code>buffer = 512x2</code>.</p>
<h2>Key-to-sound latency</h2>
<p>Estimated as USB-MIDI (≈1 ms) + one period of processing + the buffer + the receiving device:</p>
<table class="grid small">
<tr><th>Output (step 1)</th><th>Estimated latency out of the Pi</th></tr>
<tr><td>Raspberry Pi DAC+ (RCA)</td><td>≈ 8–10 ms</td></tr>
<tr><td>HDMI</td><td>≈ 12–17 ms, plus the receiver (extractor 0–2 ms; TV/AVR 20–100 ms)</td></tr>
<tr><td>USB audio interface (step 2)</td><td>≈ 7–10 ms total</td></tr>
</table>
{note("unv", "These latency figures are <b>calculated, not measured</b> on hardware — the project README states that none of them has been measured yet. The actual output and buffer chosen are reported in <code>ju6/status.txt</code>.")}
<h2>Real-time setup</h2>
<p>The audio thread runs with SCHED_FIFO priority 80, locked memory, pinned to CPU 3, which is isolated from other processes (<code>isolcpus=3</code>). The CPU governor is fixed at <i>performance</i> and USB autosuspend is off so the controller never sleeps. VCF oversampling is chosen at start-up: 4× if the CPU manages it with a good margin (≥ 2.5× real time), otherwise 2×.</p>
</section>''')

# ---------------- 12 SETTINGS ----------------
conf = [("audio_output", "auto", "auto, dacplus, hdmi, usb or null (section 11)"),
("dacplus_volume_db", "0", "DAC+ “Digital” mixer level in dB (0 or negative)"),
("dacplus_wait", "8", "seconds to wait for the DAC+ at start-up"),
("audio_devices", "(not set)", "legacy priority list (dacplus hdmi0 hdmi1 usb null); used only without audio_output"),
("buffer", "auto", "auto, or fixed PERIODxCOUNT, e.g. 512x2"),
("oversample", "auto", "VCF oversampling 2 or 4"),
("chime", "on", "ready tones"),
("output_gain_db", "0", "extra output level"),
("voices", "6", "number of voices (1–10)"),
("voice_mode", "1", "1 = Poly I, 2 = Poly II, 0 = Unison"),
("velocity", "off", "velocity sensitivity"),
("bender_dco / bender_vcf", "0.25 / 0.0", "bender depths (0–1)"),
("mod_depth", "0.5", "MOD depth"),
("master_volume", "0.5", "volume"),
("start_patch", "0", "patch at the very first start (afterwards the last one is remembered)"),
("key_channel", "omni", "keyboard channel (omni or 1–16)"),
("pad_channel", "10", "pad channel"),
("knob_cc", "70 … 77", "CC numbers for K1–K8"),
("pad_notes_a / pad_notes_b", "36 … 43 / 44 … 51", "pad notes for bank A / bank B"),
("mod_cc", "1", "CCs that drive MOD (several may be listed)"),
("knob_mode", "absolute", "or relative"),
("knob_takeover", "jump", "or pickup"),
("save_hold_seconds", "1.5", "ignored in 1.2.0; the panel does not write patches"),
("pad_leds", "on", "on = MPK pad LEDs, any = every MIDI out except MIDI 2, off = none")]
H.append(f'''<section class="page" id="s12">{sect(12, "Settings File (ju6.conf)")}
<p>All settings live in <code>ju6/ju6.conf</code> on the <b>JU6DATA</b> partition (FAT, 256 MB), which any computer can read. Every line is commented out; remove the <code>#</code> in front of a line and change the value. No recompiling is needed — the new settings apply at the next power-up.</p>
<table class="grid tiny conf"><tr><th>Key</th><th>Default</th><th>Meaning</th></tr>
{"".join(f"<tr><td><code>{k}</code></td><td>{d}</td><td>{m}</td></tr>" for k, d, m in conf)}
</table>
<h2>If your MPK sends different numbers</h2>
<p>AKAI does not publish a factory-default table for the MPK mini Plus. JU-6 Pi assumes the MPK family's usual defaults: knobs CC 70–77, pads on MIDI channel 10 with notes 36–43 (bank A) and 44–51 (bank B), mod wheel CC 1, sustain CC 64. <span class="unv">NOT VERIFIED on the hardware for this manual.</span> If your unit differs, either</p>
<ul><li>change <code>knob_cc</code>, <code>pad_notes_a</code>, <code>pad_notes_b</code> and <code>pad_channel</code> in <code>ju6.conf</code>, or</li>
<li>edit the MPK program (Shift + Prog Select, or AKAI's Program Editor) so the pads send those notes and the knobs those CCs in <b>Absolute</b> mode.</li></ul>
<h2>The three partitions</h2>
<table class="grid small"><tr><th>Partition</th><th>Contents</th><th>Mounted</th></tr>
<tr><td>bootfs (FAT)</td><td>firmware, kernel, config.txt, cmdline.txt</td><td>read-only</td></tr>
<tr><td>rootfs (ext4)</td><td>Raspberry Pi OS Lite (arm64, Debian 13 "trixie", 2026-10-06) + JU-6 Pi</td><td>read-only (overlayroot, changes in RAM)</td></tr>
<tr><td>JU6DATA (FAT, 256 MB)</td><td>ju6/ju6.conf, patches.syx, names.txt, state.txt, status.txt</td><td>read/write</td></tr></table>
</section>''')

# ---------------- 13 MIDI ----------------
H.append(f'''<section class="page" id="s13">{sect(13, "MIDI Implementation")}
<table class="grid small">
<tr><th>Message</th><th>Channel</th><th>Function</th></tr>
<tr><td>Note On / Off</td><td>omni (or <code>key_channel</code>)</td><td>play; velocity used only when VELOCITY is on</td></tr>
<tr><td>Notes 36 and 44</td><td>10</td><td>pad 1, both banks: previous sound (−1, wraps)</td></tr>
<tr><td>Notes 37 and 45</td><td>10</td><td>pad 2: SIDE 2. LED velocity 127 when that side is active, otherwise 0. Sent for both banks</td></tr>
<tr><td>Notes 38 and 46</td><td>10</td><td>pad 3: SIDE 1 = VCA LEVEL −; SIDE 2 = pulse on/off</td></tr>
<tr><td>Notes 39 and 47</td><td>10</td><td>pad 4: SIDE 1 = ENV/GATE; SIDE 2 = saw on/off</td></tr>
<tr><td>Notes 40 and 48</td><td>10</td><td>pad 5, both banks: next sound (+1, wraps)</td></tr>
<tr><td>Notes 41 and 49</td><td>10</td><td>pad 6: SIDE 1. LED velocity 127 when that side is active, otherwise 0</td></tr>
<tr><td>Notes 42 and 50</td><td>10</td><td>pad 7: SIDE 1 = VCA LEVEL +; SIDE 2 = VCF polarity</td></tr>
<tr><td>Notes 43 and 51</td><td>10</td><td>pad 8: SIDE 1 = CHORUS cycle; SIDE 2 = PWM LFO/MAN</td></tr>
<tr><td>Pitch Bend</td><td>any</td><td>BENDER (DCO and VCF depth)</td></tr>
<tr><td>CC 1 (and other <code>mod_cc</code>)</td><td>any</td><td>MOD (LFO depth on the DCO)</td></tr>
<tr><td>CC 7</td><td>any</td><td>master volume</td></tr>
<tr><td>CC 64</td><td>any</td><td>HOLD (≥ 64 = on)</td></tr>
<tr><td>CC 70–77</td><td>any</td><td>knobs K1–K8, current side</td></tr>
<tr><td>CC 120, 123</td><td>any</td><td>all notes off</td></tr>
<tr><td>CC 121</td><td>any</td><td>reset bender and MOD</td></tr>
<tr><td>Program Change 0–127</td><td>any</td><td>select A11 … B88</td></tr>
<tr><td>SysEx <code>F0 41 30 0n pp …F7</code></td><td>—</td><td>Juno-106 patch (APR) into the current sound</td></tr>
<tr><td>SysEx <code>F0 41 32 0n cc vv F7</code></td><td>—</td><td>Juno-106 single parameter (IPR)</td></tr>
</table>
<p class="cap">Pad notes are recognised only on the pad channel; notes on other channels (and pad-channel notes that are not pad notes) play the synth. With <code>pad_leds = on</code> (the default) JU-6 Pi transmits Note On/Off for every pad on both banks, so the LEDs match the side whichever bank the MPK is showing. Velocity 0 is Note Off. An echo of those notes is ignored for about 80 ms. NOT VERIFIED on an MPK mini Plus.</p>
<h2>Patch data format</h2>
<p>Each patch is 18 bytes, as in the Juno-106 APR message: 16 slider values (0–127) in the order LFO RATE, LFO DELAY, DCO LFO, DCO PWM, DCO NOISE, VCF FREQ, VCF RES, VCF ENV, VCF LFO, VCF KYBD, VCA LEVEL, ENV A, ENV D, ENV S, ENV R, DCO SUB, followed by two switch bytes:</p>
<ul><li><b>SW1:</b> bits 0–2 = range 16'/8'/4'; bit 3 = pulse; bit 4 = saw; bit 5 = chorus off (0 = on); bit 6 = chorus I (0 = II).</li>
<li><b>SW2:</b> bit 0 = PWM MAN (0 = LFO); bit 1 = VCF ENV inverted; bit 2 = VCA GATE (0 = ENV); bits 3–4 = HPF (3 − position).</li></ul>
</section>''')

# ---------------- 14 PARAMETER CHART ----------------
chart = [("ENV A", "1", "K1", "CC 70", "0–127", "slider 12"), ("ENV D", "1", "K2", "CC 71", "0–127", "slider 13"),
("ENV S", "1", "K3", "CC 72", "0–127", "slider 14"), ("ENV R", "1", "K4", "CC 73", "0–127", "slider 15"),
("DCO SUB", "1", "K5", "CC 74", "0 = off, 1–127", "slider 16"), ("DCO NOISE", "1", "K6", "CC 75", "0–127", "slider 5"),
("VCF FREQ", "1", "K7", "CC 76", "0–127", "slider 6"), ("VCF RES", "1", "K8", "CC 77", "0–127", "slider 7"),
("VCA LEVEL +/−", "1", "pads 7 / 3", "notes 50 / 46", "steps of 8, 0–127", "slider 11"),
("CHORUS", "1", "pad 8", "note 51", "off · I · II · I+II", "SW1 b5, b6 (+ ext b0)"),
("VCA ENV/GATE", "1", "pad 4", "note 47", "ENV · GATE", "SW2 b2"),
("NEXT / PREVIOUS", "both", "pads 5 / 1", "notes 48 / 44", "one patch, wraps 0–127", "selects a memory"),
("DCO LFO", "2", "K1", "CC 70", "0–127", "slider 3"), ("DCO PWM", "2", "K2", "CC 71", "0–127", "slider 4 (0–105 in 106 format)"),
("LFO RATE", "2", "K3", "CC 72", "0–127", "slider 1"), ("LFO DELAY", "2", "K4", "CC 73", "0–127", "slider 2"),
("HPF", "2", "K5", "CC 74", "0 · 1 · 2 · 3", "SW2 b3–4"), ("VCF ENV", "2", "K6", "CC 75", "0–127", "slider 8"),
("VCF LFO", "2", "K7", "CC 76", "0–127", "slider 9"), ("VCF KYBD", "2", "K8", "CC 77", "0–127", "slider 10"),
("PULSE", "2", "pad 3", "note 46", "on · off", "SW1 b3"), ("SAW", "2", "pad 4", "note 47", "on · off", "SW1 b4"),
("PWM LFO/MAN", "2", "pad 8", "note 51", "LFO · MAN", "SW2 b0 (+ ext b1 for ENV)"),
("VCF polarity", "2", "pad 7", "note 50", "on = inverted, off = normal", "SW2 b1"),
("DCO RANGE", "—", "—", "—", "16' · 8' · 4', from the patch", "SW1 b0–2"),
("SIDE 1 / SIDE 2", "both", "pad 6 / pad 2", "notes 49 / 45", "active pad strong red, the other off", "not stored")]
H.append(f'''<section class="page" id="s14">{sect(14, "Parameter Chart")}
<table class="grid tiny chart"><tr><th>Parameter</th><th>Side</th><th>Control</th><th>MIDI</th><th>Range / positions</th><th>Stored in patch</th></tr>
{"".join(f"<tr><td><b>{a}</b></td><td class='c'>{p}</td><td class='c'>{k}</td><td>{m}</td><td>{r}</td><td>{s}</td></tr>" for a, p, k, m, r, s in chart)}
</table>
<p class="cap">Side = the panel selected with bank B pad 6 (SIDE 1) or pad 2 (SIDE 2). Slider numbers refer to the 16 slider bytes of the patch data (section 13). "ext" = JU-6 Pi extension column in <code>names.txt</code>. Bender depth, MOD depth, master volume, voice mode, velocity and portamento are not on the panel; their start values come from <code>ju6.conf</code> and they are not written with a patch.</p>
<h2>Patch sheet</h2>
<table class="grid sheet"><tr><th>Patch</th><th colspan="8">SIDE 1 knobs: A · D · S · R · SUB · NOISE · FREQ · RES</th></tr>
<tr><td class="blank"></td>{"<td></td>"*8}</tr>
<tr><th></th><th colspan="8">SIDE 2 knobs: DCO LFO · PWM · LFO RATE · DELAY · HPF · VCF ENV · VCF LFO · KYBD</th></tr>
<tr><td class="blank"></td>{"<td></td>"*8}</tr>
<tr><th></th><th colspan="8">Pads: NEXT · PREV · LEVEL · CHORUS · ENV/GATE · PULSE · SAW · LFO/MAN · POLARITY</th></tr>
<tr><td class="blank"></td>{"<td></td>"*8}</tr></table>
<p class="cap">Copy this sheet to note down your own sounds.</p>
</section>''')

# ---------------- 15 PATCH LIST ----------------
def bank_table(letter):
    rows = ""
    for g in range(1, 9):
        cells = "".join(f"<td>{n}</td>" for s, n in NAMES if s[0] == letter and s[1] == str(g))
        rows += f"<tr><th>{letter}{g}x</th>{cells}</tr>"
    return f'<table class="grid tiny patches"><tr><th>Bank {letter}</th>' + "".join(f"<th>{i}</th>" for i in range(1, 9)) + f"</tr>{rows}</table>"
H.append(f'''<section class="page" id="s15">{sect(15, "Patch List")}
<p>Banks A and B contain the Juno-106 factory patches as provided by the KR-106 project (parameter values, not samples), in exact 106 format (<code>patches/factory_106.syx</code>). Columns are the patch number inside the group. Reach a row by stepping one sound at a time (section 7) or with Program Change.</p>
{bank_table("A")}{bank_table("B")}
<p class="cap">Names from <code>src/factory_bank.h</code>. Memories you write are renamed "<i>xNN Egen</i>".</p>
</section>''')

# ---------------- 16 TROUBLESHOOTING ----------------
H.append(f'''<section class="page" id="s16">{sect(16, "Troubleshooting")}
<table class="grid small">
<tr><th>Symptom</th><th>Check</th></tr>
<tr><td>No ready tones, LED keeps blinking slowly</td><td>No audio output found. With HDMI, use <b>HDMI0</b> (nearest USB-C). Check the receiver's input. Read <code>ju6/status.txt</code>.</td></tr>
<tr><td>Ready tones fall (E–A) instead of rising</td><td><code>audio_output = dacplus</code> but the DAC+ was not found — check that it is seated correctly. Output is on HDMI/USB meanwhile.</td></tr>
<tr><td>LED on with a short gap every 2 s</td><td>No MIDI device: check the MPK's USB cable. Devices can be plugged in while running.</td></tr>
<tr><td>Keys play but knobs/pads do nothing or do the wrong thing</td><td>The MPK program sends other CC/note numbers or another pad channel. Adjust <code>ju6.conf</code> or the MPK program (section 12). Make sure the pads are in the bank you expect (BANK A/B).</td></tr>
<tr><td>Pad presses play notes</td><td>Pads not on the pad channel (default 10) — set <code>pad_channel</code> to match.</td></tr>
<tr><td>Knobs have no effect until turned past a point</td><td><code>knob_takeover = pickup</code> is set — this is soft takeover.</td></tr>
<tr><td>Noticeable delay with a TV or AV receiver</td><td>Select Game/Direct/Pure mode, or use a DAC+ or HDMI audio extractor.</td></tr>
<tr><td>Clicks or drop-outs</td><td>The buffer grows automatically after repeated underruns; you can also set <code>buffer = 512x2</code>.</td></tr>
<tr><td>The octave is wrong for this patch</td><td>DCO RANGE is stored in the patch and is not on the panel. Step to another sound, or load a SysEx patch with the range you want. OCT −/+ only shifts the MPK keyboard.</td></tr>
<tr><td>Notes hang</td><td>Release the sustain pedal, or send CC 123 (all notes off).</td></tr>
<tr><td>Pad LEDs do not show the side</td><td>Set <code>pad_leds = on</code> (default). The MPK must appear as a USB-MIDI port with “MPK” in the name. NOT VERIFIED on hardware; the Pi LED still blinks once for SIDE 1 and twice for SIDE 2. <code>pad_leds = off</code> stops the messages.</td></tr>
<tr><td>An edited sound was not kept after writing</td><td>Fixed in v1.1.1 (section 10); update the SD card.</td></tr>
<tr><td>Want factory sounds back</td><td>Delete <code>patches.syx</code> and <code>names.txt</code> on JU6DATA.</td></tr>
</table>
<h2>With a screen and keyboard on the Pi</h2>
<p><code>ju6pi list</code> (patch names), <code>ju6pi bench</code> (CPU margin), <code>ju6pi demo DIR</code> (render WAV examples), <code>ju6pi utganger</code> (sound cards and chosen output), <code>ju6pi selftest</code> (MPK mapping, sound step, SysEx, output selection), <code>journalctl -u ju6pi</code> (log). <code>aplay -l</code> should list <code>RPiDAC [RPi DAC+]</code> when the DAC+ is fitted.</p>
</section>''')

# ---------------- 17 SPECS ----------------
specs = [("Sound engine", "Ultramaster KR-106 DSP (component-level Juno-106 model), GPL-3, unmodified in third_party/kr106"),
("Polyphony", "6 voices (configurable 1–10); Poly I, Poly II, Unison"),
("DCO", "Pulse with PWM (LFO / MAN / ENV), sawtooth, sub-oscillator (square, −1 oct), noise; range 16' / 8' / 4'"),
("VCF", "4-pole resonant low-pass (IR3109 character), self-oscillating; ENV ±, LFO, KYBD; 2× or 4× oversampling"),
("HPF", "4 positions: 0 bass boost (≈ +9.4 dB shelf), 1 flat, 2 ≈ 236 Hz, 3 ≈ 754 Hz"),
("VCA", "ENV or GATE; LEVEL ≈ −10 … +10 dB"),
("ENV / LFO", "One ADSR (Juno-106 curves); triangle LFO with RATE and DELAY, AUTO or MANUAL trigger"),
("Chorus", "BBD model (MN3009 type), modes off / I / II / I+II, stereo"),
("Memory", "128 patches (A11–B88), Juno-106 SysEx (APR) format; factory banks A and B"),
("Controller", "AKAI MPK mini Plus over USB (any class-compliant USB-MIDI device, hot-plug)"),
("Audio outputs", "Raspberry Pi DAC+ (RCA + 3.5 mm, 48 kHz/32-bit) · HDMI0 / HDMI1 (2-ch PCM, 48 kHz) · USB audio"),
("Sample rate", "48 kHz"),
("Buffer at start", "DAC+ 5.3 ms · HDMI 10.7 ms · USB 2.7 ms (automatically increased on underruns)"),
("Latency", "≈ 8–10 ms (DAC+), ≈ 12–17 ms (HDMI) — calculated, not measured"),
("Start-up time", "≈ 10–15 s to ready tones"),
("Hardware", "Raspberry Pi 5, 8 GB; microSD ≥ 8 GB; 27 W USB-C supply recommended"),
("Operating system", "Raspberry Pi OS Lite arm64 (Debian 13 “trixie”), read-only root (overlayroot)"),
("Software", "ju6pi 1.2.0 (9 November 2026), C++17, ALSA; SCHED_FIFO 80 on isolated CPU 3"),
("Licence", "GPL-3.0")]
H.append(f'''<section class="page" id="s17">{sect(17, "Specifications")}
<table class="grid spec">{"".join(f"<tr><th>{a}</th><td>{b_}</td></tr>" for a, b_ in specs)}</table>
<p class="cap">Specifications are taken from the v1.2.0 source and README and are subject to change.</p>
{note("note", "Chorus II and I+II speeds have not yet been verified against hardware by the KR-106 project; the chorus circuit is modelled on the Juno-6/60 family, which shares its topology with the 106. Analogue voice-to-voice variation is only approximated.")}
</section>''')

# ---------------- 18 CREDITS ----------------
H.append(f'''<section class="page" id="s18">{sect(18, "Sources and Credits")}
<h2>What this manual is based on</h2>
<table class="grid small">
<tr><th>Topic</th><th>Source (repository OleBee/juno106-pi, v1.2.0)</th></tr>
<tr><td>Two sides, pad functions, page LEDs, next/previous sound, Program Change</td><td><code>src/controller.h</code>, <code>src/midi_out.cpp</code></td></tr>
<tr><td>Parameter scaling, patch format, MOD/bender, transpose key</td><td><code>src/synth.h</code>, <code>third_party/kr106/DSP/KR106SysEx.h</code>, <code>KR106_DSP_SetParam.h</code>, <code>KR106_HPF.h</code>, <code>KR106LFO.h</code></td></tr>
<tr><td>Defaults, LED, ready tones, status file, oversampling, buffer step-up</td><td><code>src/main.cpp</code>, <code>image/data/ju6.conf</code></td></tr>
<tr><td>Audio outputs, DAC+ detection, buffer tables</td><td><code>src/audio_out.h</code>, <code>image/boot/dacplus.blokk</code></td></tr>
<tr><td>Patch memory and files</td><td><code>src/bank.h</code>, <code>src/factory_bank.h</code>, <code>image/data/LES-MEG.txt</code></td></tr>
<tr><td>Installation, latency estimates, MPK defaults, changelog</td><td><code>README.md</code></td></tr>
<tr><td>MPK mini Plus layout and controls</td><td>AKAI Professional, <i>MPK mini Plus User Guide v1.2</i> (diagram redrawn)</td></tr>
</table>
<h2>Credits</h2>
<ul>
<li>Sound engine: <b>Ultramaster KR-106</b> by Karl LaRocca and the original Ultramaster group (GPL-3).</li>
<li>Raspberry Pi OS © Raspberry Pi Ltd. and the Debian project.</li>
<li>AKAI Professional and MPK are trademarks of inMusic Brands. Diagrams in this manual are original drawings.</li>
<li>The layout of this manual is inspired by 1980s synthesizer owner's manuals; no text has been copied.</li>
<li>JU-6 Pi is not affiliated with Roland Corporation. "Roland" and "Juno" are trademarks of their owners.</li>
</ul>
<div class="endmark"><div class="stripes small"><i></i><i></i><i></i></div>JU-6 Pi · Owner's Manual · v1.2.0 · November 2026</div>
</section>''')

doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>JU-6 Pi Owner's Manual</title><style>{css}</style></head><body>{"".join(H)}</body></html>'''
open('manual.html', 'w').write(doc)
print("written", len(doc))
