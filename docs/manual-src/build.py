import json, re, html, os
from pathlib import Path
REPO = Path(os.environ.get('JU6_REPO', Path(__file__).resolve().parents[2]))
from diagrams import *

T = json.load(open('tutorials.json'))
src = open(REPO / 'src/factory_bank.h').read()
NAMES = re.findall(r'\{"([AB]\d\d) ([^"]*)"', src)
assert len(NAMES) == 128

P1 = ["VCF|FREQ", "VCF|RES", "VCF|ENV", "ENV|A", "ENV|D", "ENV|S", "ENV|R", "CHORUS|off·I·II·I+II"]
P2 = ["RANGE|16'·8'·4'", "DCO|LFO", "DCO|PWM", "PWM SOURCE|LFO·MAN·ENV", "WAVE|off·pulse·saw·both", "DCO|SUB", "DCO|NOISE", "VCF|KYBD"]
P3 = ["LFO|RATE", "LFO|DELAY", "VCF|LFO", "VCF ENV|polarity +/−", "HPF|0·1·2·3", "VCA|ENV/GATE", "VCA|LEVEL", "LFO MODE|AUTO/MANUAL"]
P4 = ["BENDER|→ DCO", "BENDER|→ VCF", "MOD|depth", "TRANSPOSE|−12…+12", "MASTER|VOLUME", "VOICE MODE|PolyI·PolyII·Uni", "VELOCITY|off/on", "PORTA-|MENTO"]

def pg(title, pages):  # generic page wrapper
    return pages

def sect(num, title):
    return f'<h1><span class="num">{num}</span>{title}</h1>'

def note(kind, text):
    return f'<div class="note {kind}"><b>{ {"note":"NOTE","warn":"CAUTION","issue":"KNOWN ISSUE (v1.1.0)","unv":"NOT VERIFIED"}[kind] }</b> {text}</div>'

def val10(v):  # 0..127 -> 0..10 scale for orientation
    return f"{v*10/127:.1f}"

def tut_table(key, swlabels):
    t = T[key]
    rows = ""
    pages = [("PAGE 1 · SOUND", P1, t['p1']), ("PAGE 2 · DCO", P2, t['p2']), ("PAGE 3 · MOD/HPF/VCA", P3, t['p3'])]
    return pages

def knob_fig(title, names, vals, subs):
    return knob_page(title, names, vals, subs)

def sw_text(page, i, v, lab):
    return None

# --- labels for tutorial knob subs (show the value + switch meaning) ---
def subs_for(key):
    t = T[key]; L = t['lab']
    s1 = [str(v) for v in t['p1']]; s1[7] = f"{t['p1'][7]} = {L['chorus']}"
    s2 = [str(v) for v in t['p2']]
    s2[0] = f"{t['p2'][0]} = {L['range']}"; s2[3] = f"{t['p2'][3]} = {L['pwmsrc']}"
    s2[4] = f"{t['p2'][4]} = {L['wave']}"; s2[5] = f"{t['p2'][5]}" + (" (off)" if t['p2'][5] == 0 else "")
    s3 = [str(v) for v in t['p3']]
    s3[3] = f"{t['p3'][3]} = {L['envpol']}"; s3[4] = f"{t['p3'][4]} = HPF {L['hpf']}"
    s3[5] = f"{t['p3'][5]} = {L['vca']}"; s3[7] = f"{t['p3'][7]} = AUTO"
    return s1, s2, s3

def tutorial(key, title, intro, steps):
    t = T[key]; s1, s2, s3 = subs_for(key)
    h = f'<h2>{title}</h2><p>{intro}</p><ol class="steps">'
    for st in steps:
        h += f'<li>{st}</li>'
    h += '</ol>'
    h += '<div class="kp3">' + knob_fig("PAGE 1 · SOUND", P1, t['p1'], s1) + knob_fig("PAGE 2 · DCO", P2, t['p2'], s2) + knob_fig("PAGE 3 · MOD / HPF / VCA", P3, t['p3'], s3) + '</div>'
    rows = ""
    for pname, names, vals, subs in [("Page 1", P1, t['p1'], s1), ("Page 2", P2, t['p2'], s2), ("Page 3", P3, t['p3'], s3)]:
        rows += f"<tr><th>{pname}</th>" + "".join(f"<td><span>{n.replace('|',' ')}</span><b>{s}</b></td>" for n, s in zip(names, subs)) + "</tr>"
    h += f'<table class="grid tiny tsum"><tr><th></th>' + "".join(f"<th>K{i}</th>" for i in range(1, 9)) + f'</tr>{rows}</table>'
    h += f'<p class="cap">Target knob values (0–127) for <b>{t["name"]}</b>, computed from the factory patch data in <code>src/factory_bank.h</code> with the same scaling the synth uses when it loads a patch. Red pointer = approximate knob position on a 0–127 scale.</p>'
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
<div class="cover-foot">Software version 1.1.0 · Played from an AKAI MPK mini Plus over USB · Audio via HDMI or Raspberry Pi DAC+<br>
JU-6 Pi is an independent hobby project inspired by the Juno-106. It is not affiliated with or endorsed by Roland Corporation.</div>
</section>''')

# ---------------- CONTENTS ----------------
toc = [("1", "Introduction"), ("2", "Important Notes"), ("3", "Panel Descriptions"), ("4", "Connections"),
       ("5", "Power-up and Status LED"), ("6", "Playing"), ("7", "Selecting Patches"), ("8", "The Knob Pages"),
       ("9", "Creating Sounds"), ("10", "Writing (Saving) Patches"), ("11", "Audio Output and Latency"),
       ("12", "Settings File (ju6.conf)"), ("13", "MIDI Implementation"), ("14", "Parameter Chart"),
       ("15", "Patch List"), ("16", "Troubleshooting"), ("17", "Specifications"), ("18", "Sources and Credits")]
H.append('<section class="page"><h1 class="plain">Contents</h1><ol class="toc">' +
         "".join(f'<li><a href="#s{n}"><span>{n}</span>{t}</a></li>' for n, t in toc) + '</ol>'
         + note("note", "Everything in this manual about controls, MIDI numbers, patch memory, audio outputs and latency was taken from the JU-6 Pi v1.1.0 source code and README (repository <code>OleBee/juno106-pi</code>, commit <code>ffbce82</code>). Items that could not be confirmed are marked <b>NOT VERIFIED</b>.")
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
<li>Four <b>knob pages</b> give the MPK's eight knobs access to every sound parameter.</li>
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
{note("warn", "This manual describes software version <b>1.1.0</b>. The audio-output selection (<code>audio_output</code>) and DAC+ support do not exist in 1.0.0.")}
</section>''')

# ---------------- 3 PANEL DESCRIPTIONS ----------------
H.append(f'''<section class="page" id="s3">{sect(3, "Panel Descriptions")}
<p>JU-6 Pi has no panel of its own — the <b>AKAI MPK mini Plus</b> is its front panel. The numbers below refer to the drawing; only controls that JU-6 Pi uses are numbered.</p>
<div class="fig-wrap">{mpk_top()}</div>
<p class="cap">AKAI MPK mini Plus, top and rear panel (drawing based on the Top/Rear Panel figures in AKAI's MPK mini Plus User Guide v1.2; simplified, not to scale). Note that pads 1–4 are the <b>lower</b> row and pads 5–8 the <b>upper</b> row.</p>
<table class="callouts">
<tr><td>{callout_html(1)}</td><td><b>Keyboard</b> — 37 keys. Plays JU-6 Pi on every MIDI channel (omni). Velocity is ignored by default, like the original. Also used to set the key with TRANSPOSE (pad bank B, pad 8).</td></tr>
<tr><td>{callout_html(2, True)}</td><td><b>Pitch wheel</b> — BENDER. Bends the DCO (default depth 0.25 ≈ ±2 semitones) and optionally the VCF. Depths: knob page 4, K1/K2.</td></tr>
<tr><td>{callout_html(3, True)}</td><td><b>Modulation wheel</b> (CC 1) — MOD: LFO vibrato on the DCO. Depth follows how far the wheel is moved (scaled by page 4, K3). In LFO MANUAL mode it also starts the LFO.</td></tr>
<tr><td>{callout_html(4, True)}</td><td><b>X-Y joystick</b> — JU-6 Pi reacts to whatever the joystick sends: <b>Pitch Bend</b> acts as BENDER, <b>CC 1</b> acts as MOD. Other CC numbers are ignored unless listed in <code>mod_cc</code>. <span class="unv">NOT VERIFIED: which messages the joystick sends in the MPK's default program.</span></td></tr>
<tr><td>{callout_html(5, True)}</td><td><b>OCT − / OCT +</b> — handled inside the MPK; shifts the keyboard range. Press both to return to the centre octave.</td></tr>
<tr><td>{callout_html(6, True)}</td><td><b>Pads 1–8</b> — bank A: patch number 1–8 (hold 1.5 s to write). Bank B: page select, group −/+, HOLD, TRANSPOSE. See section 7.</td></tr>
<tr><td>{callout_html(7, True)}</td><td><b>BANK A/B</b> — switches the pads between bank A (patches) and bank B (functions).</td></tr>
<tr><td>{callout_html(8, True)}</td><td><b>Knobs K1–K8</b> (CC 70–77) — sound parameters. What each knob does depends on the selected <i>page</i> (section 8).</td></tr>
<tr><td>{callout_html(9, True)}</td><td><b>USB port</b> — connect to any USB port on the Pi. Carries MIDI and powers the MPK.</td></tr>
<tr><td>{callout_html(10, True)}</td><td><b>Sustain input</b> — a sustain pedal (CC 64) works as HOLD.</td></tr>
</table>
{note("note", "The other MPK functions (arpeggiator, scales, chords, note repeat, sequencer, transport buttons, CV/Gate, 5-pin MIDI) are run by the MPK itself. They are not used or tested by JU-6 Pi; any notes they produce over USB are simply played.")}
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
{note("unv", "<b>HiFiBerry DAC+ is not supported in v1.1.0.</b> JU-6 Pi 1.1.0 loads only the <code>rpi-dacplus</code> overlay and recognises only the ALSA cards <code>RPiDAC</code> / <code>IQaudIODAC</code> (<code>src/audio_out.h</code>, <code>image/boot/dacplus.blokk</code>). A HiFiBerry DAC+ uses a different overlay and card name and is <b>not</b> detected by this version; JU-6 Pi would then play on HDMI instead. This manual therefore describes the Raspberry Pi DAC+.")}
</section>''')

# ---------------- 4 CONNECTIONS ----------------
H.append(f'''<section class="page" id="s4">{sect(4, "Connections")}
{note("warn", "To prevent damage, turn the volume of your amplifier or TV all the way down and leave the Pi unpowered while making connections.")}
<h2>Preparing the SD card</h2>
<ol class="steps">
<li>Download <code>ju6pi-1.1.0.img.xz</code> from the project's Releases page. If it is split into <code>.part-aa</code>, <code>.part-ab</code> … join the parts first (<code>cat ju6pi-1.1.0.img.xz.part-* &gt; ju6pi-1.1.0.img.xz</code>) and check it with <code>sha256sum -c ju6pi-1.1.0.img.xz.sha256</code>.</li>
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
 ("Rapid blinks", [(on, .09), (off, .09)] * 6, "Page or group changed (number of blinks = page or group number), HOLD switched, or a patch written (5 blinks)."),
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
<p>The keyboard plays on all MIDI channels (<code>key_channel = omni</code>); only the pad notes on the pad channel are reserved. <b>Velocity is off</b> by default, as on the original; switch it on with page 4, K7 or <code>velocity = on</code>. Use the MPK's OCT −/+ buttons to reach higher and lower octaves.</p>
<h2>BENDER (pitch wheel / joystick X)</h2>
<p>Pitch Bend bends the DCO pitch by up to ±2 semitones (default <code>bender_dco = 0.25</code>) and, if set, the VCF cutoff (default <code>bender_vcf = 0</code>). Change the depths on page 4 with K1 (→ DCO) and K2 (→ VCF).</p>
<h2>MOD (mod wheel / CC 1)</h2>
<p>MOD applies LFO vibrato to the DCO. Unlike the 106's spring-loaded lever with fixed depth, MOD here is <b>continuous</b>: the depth follows how far the wheel or joystick is pushed, scaled by page 4, K3 (default <code>mod_depth = 0.5</code>). When the LFO is in MANUAL mode (page 3, K8), moving MOD away from zero also triggers the LFO.</p>
<h2>HOLD</h2>
<p>A sustain pedal (CC 64) holds the notes while pressed. Pad 7 in bank B switches HOLD on and off as a latch (LED: 2 blinks = on, 1 blink = off).</p>
<h2>TRANSPOSE</h2>
<ol class="steps">
<li>Press and <b>hold pad 8</b> (bank B).</li>
<li>Press a key. That key becomes the new tonic: <b>C4 (middle C, note 60) = no transposition</b>; F4 gives +5 semitones, for example. The key itself does not sound.</li>
<li>Release the pad.</li>
</ol>
<p>A <b>short press</b> (under 0.6 s, no key) on pad 8 switches the transposition off — and the next short press brings back the last value. Page 4, K4 sets the transposition directly from −12 to +12 semitones (centre = 0).</p>
<h2>Voice modes</h2>
<table class="grid">
<tr><th>Mode</th><th>Page 4, K6 zone</th><th>Description</th></tr>
<tr><td><b>Poly I</b> (default)</td><td>0–42</td><td>Juno-106 voice assignment, as on the hardware.</td></tr>
<tr><td><b>Poly II</b></td><td>43–85</td><td>Alternative polyphonic assignment (an addition — not on the 106).</td></tr>
<tr><td><b>Unison</b></td><td>86–127</td><td>All voices on one note (an addition — not on the 106).</td></tr>
</table>
<p>PORTAMENTO (page 4, K8) adds glide; it is 0 (off) by default. Neither portamento, Unison nor velocity exist on the original instrument.</p>
<h2>Other controls</h2>
<p>MIDI CC 7 sets the master volume (as does page 4, K5). CC 120 and 123 silence all notes; CC 121 resets bender and MOD.</p>
</section>''')

# ---------------- 7 SELECTING PATCHES ----------------
H.append(f'''<section class="page" id="s7">{sect(7, "Selecting Patches")}
<p>As on the 106, the 128 memories are organised as two <b>banks</b> (A and B), each with eight <b>groups</b> of eight <b>patches</b>: A11 … A88 and B11 … B88. The first digit is the group, the second the patch number.</p>
<div class="fig-wrap">{pad_map()}</div>
<p class="cap">Pad functions. Press the MPK's <b>BANK A/B</b> button to switch the pad row. Pads 1–4 are the lower row.</p>
<h2>Selecting a patch</h2>
<ol class="steps">
<li>Press BANK A/B so the pads are in <b>bank B</b>.</li>
<li>Press pad 5 (<b>GROUP −</b>) or pad 6 (<b>GROUP +</b>) to step through the 16 groups A1 → A8 → B1 → B8 (it wraps round). The LED blinks the group number (1–8) and the patch with the same number in the new group is selected.</li>
<li>Press BANK A/B to return to <b>bank A</b>.</li>
<li>Press pad 1–8 to select patch 1–8 in that group. The sound changes immediately.</li>
</ol>
<p><b>Example:</b> group A4, pad 8 → <b>A48 Synth Bass I</b>.</p>
{note("note", "The LED shows only the group number, not whether you are in bank A or B. Starting from group A1, GROUP + seven times reaches A8; once more reaches B1.")}
<h2>Program Change</h2>
<p>MIDI Program Change 0–127 selects A11 … B88 directly (0 = A11, 63 = A88, 64 = B11, 127 = B88). The MPK can send program changes from its pads (pad Play Mode "ProgCh" in the MPK's program editor, per AKAI's guide).</p>
<h2>SysEx</h2>
<p>A Juno-106 patch dump (APR, <code>F0 41 30 0n …</code>) or single-parameter message (IPR, <code>F0 41 32 0n …</code>) received over MIDI is loaded into the current sound, just as on a 106. This lets you audition sounds from Juno-106 editors and librarians.</p>
<h2>Master volume across patches</h2>
<p>Selecting a patch changes every sound parameter but keeps the master volume (page 4, K5) where it was.</p>
</section>''')

# ---------------- 8 KNOB PAGES ----------------
H.append(f'''<section class="page" id="s8">{sect(8, "The Knob Pages")}
<p>The eight knobs send <b>CC 70–77</b>. Their function depends on the selected <b>page</b>. Page 1 is active after power-up; select a page with pads 1–4 in <b>bank B</b> (the LED blinks the page number).</p>
<div class="kp2">{knob_page("PAGE 1 · SOUND  (bank B, pad 1)", P1)}{knob_page("PAGE 2 · DCO  (bank B, pad 2)", P2)}{knob_page("PAGE 3 · MOD / HPF / VCA  (bank B, pad 3)", P3)}{knob_page("PAGE 4 · PLAY  (bank B, pad 4)", P4)}</div>
<h2>Switch-type knobs</h2>
<p>Knobs that replace a switch divide the knob's 0–127 travel into equal zones:</p>
<table class="grid small">
<tr><th>Knob</th><th>Zones (value sent by the knob)</th></tr>
<tr><td>P1 K8 CHORUS</td><td>0–31 off · 32–63 I · 64–95 II · 96–127 I+II</td></tr>
<tr><td>P2 K1 RANGE</td><td>0–42 16' · 43–85 8' · 86–127 4'</td></tr>
<tr><td>P2 K4 PWM SOURCE</td><td>0–42 LFO · 43–85 MAN · 86–127 ENV</td></tr>
<tr><td>P2 K5 WAVE</td><td>0–31 off · 32–63 pulse · 64–95 saw · 96–127 pulse + saw</td></tr>
<tr><td>P2 K6 SUB</td><td>0 = sub off; 1–127 = sub level</td></tr>
<tr><td>P3 K4 VCF ENV polarity</td><td>0–63 + (normal) · 64–127 − (inverted)</td></tr>
<tr><td>P3 K5 HPF</td><td>0–31 pos. 0 (bass boost) · 32–63 pos. 1 (flat) · 64–95 pos. 2 · 96–127 pos. 3</td></tr>
<tr><td>P3 K6 VCA</td><td>0–63 ENV · 64–127 GATE</td></tr>
<tr><td>P3 K8 LFO MODE</td><td>0–63 AUTO · 64–127 MANUAL (triggered by MOD)</td></tr>
<tr><td>P4 K4 TRANSPOSE</td><td>25 zones, −12 … +12 semitones (centre ≈ 64 = 0)</td></tr>
<tr><td>P4 K6 VOICE MODE</td><td>0–42 Poly I · 43–85 Poly II · 86–127 Unison</td></tr>
<tr><td>P4 K7 VELOCITY</td><td>0–63 off · 64–127 on</td></tr>
</table>
<h2>Knob behaviour</h2>
<p>By default the knobs <b>jump</b>: the parameter takes the knob's value as soon as the knob is moved (<code>knob_takeover = jump</code>). With <code>knob_takeover = pickup</code> a knob does nothing until it passes the current value (soft takeover; this resets on every page or patch change). With <code>knob_mode = relative</code> JU-6 Pi reads the knobs as relative (two's complement: 1–63 = up, 65–127 = down). <span class="unv">NOT VERIFIED: that this matches the MPK mini Plus's own "Relative" knob mode.</span></p>
</section>''')

# ---------------- 9 CREATING SOUNDS ----------------
H.append(f'''<section class="page" id="s9">{sect(9, "Creating Sounds")}
<p>Each of the six voices has its own DCO, VCF and VCA. The voices are summed and pass through the common HPF and chorus. A single envelope (ENV) and a single LFO control all voices.</p>
<div class="fig-wrap">{signal_flow()}</div>
<table class="grid small">
<tr><th>Section</th><th>What it does</th><th>Where</th></tr>
<tr><td><b>DCO</b></td><td>The sound source. Pulse (width set by PWM, modulated by LFO, set manually or by ENV), sawtooth, sub-oscillator one octave down, and noise are mixed. RANGE sets the octave; DCO LFO adds vibrato.</td><td>Page 2</td></tr>
<tr><td><b>VCF</b></td><td>Low-pass filter, 24 dB/octave. FREQ = cutoff, RES = resonance (self-oscillates near maximum), ENV = how much the envelope opens the filter (polarity on P3 K4), LFO = filter wobble, KYBD = cutoff follows the keyboard.</td><td>Pages 1–3</td></tr>
<tr><td><b>VCA</b></td><td>Loudness. ENV: follows the ADSR. GATE: full level while a key is held. LEVEL sets the patch volume (about −10 … +10 dB).</td><td>Page 3</td></tr>
<tr><td><b>ENV</b></td><td>One ADSR envelope with Juno-106 curves: A = attack, D = decay, S = sustain level, R = release.</td><td>Page 1</td></tr>
<tr><td><b>LFO</b></td><td>Triangle wave. RATE = speed, DELAY = fade-in time after a key is pressed (AUTO), or triggered by MOD (MANUAL).</td><td>Page 3</td></tr>
<tr><td><b>HPF</b></td><td>Position 0 = bass boost (about +9.4 dB low shelf), 1 = flat, 2 ≈ 236 Hz, 3 ≈ 754 Hz high-pass.</td><td>P3 K5</td></tr>
<tr><td><b>Chorus</b></td><td>I = slow, wide; II = faster, deeper; I+II = a third, distinct mode (fast, shallow, vibrato-like).</td><td>P1 K8</td></tr>
</table>
<h2>How to use the tutorials</h2>
<p>There is no "initialise patch" function, so every tutorial lists the value for <b>all 24 knobs</b> on pages 1–3. Work page by page: select the page with its pad in bank B, then turn each knob until it sends the target value (0–127). The patches are re-creations of factory sounds, so you can press the original's pad at any time to compare — but note that this replaces what you have dialled in.</p>
{note("note", "Start from a patch in a group you don't mind experimenting in. Because the knobs jump by default, each knob must actually be turned at least a little so it sends its value.")}
</section>''')

H.append(f'''<section class="page">
{tutorial("A48", "Tutorial 1 — Synth bass (A48 Synth Bass I)",
 "A punchy, mono-style bass made from a narrow pulse, a strong sub-oscillator and a short filter envelope.",
 ["Page 2: set RANGE to 16' (K1 = 21) and WAVE to pulse only (K5 = 48). Set PWM SOURCE to MAN (K4 = 64) and PWM to 69 for a fairly narrow pulse.",
  "Page 2: add the sub-oscillator (K6 = 102) for weight and a touch of NOISE (K7 = 50) for attack. VCF KYBD 35.",
  "Page 1: close the filter (FREQ 32, RES 0) and let the envelope open it (VCF ENV 66).",
  "Page 1: envelope A = 0, D = 34, S = 0, R = 36 — a plucked shape with no sustain. CHORUS off (K8 = 16).",
  "Page 3: HPF position 0 (K5 = 16) for the bass boost, VCA = ENV (K6 = 32), LEVEL 75. LFO RATE 58 / DELAY 16 / VCF LFO 0 (barely used).",
  "Play low on the keyboard. Try more RES or VCF ENV for a squelchier bass."])}
</section>''')
H.append(f'''<section class="page">
{tutorial("B11", "Tutorial 2 — Strings (B11 Strings)",
 "A classic ensemble: pulse and saw together, slowly swept by the LFO, softened by the envelope and widened by chorus II.",
 ["Page 2: RANGE 8' (K1 = 64), WAVE pulse + saw (K5 = 112). PWM SOURCE LFO (K4 = 21) with PWM 67 — the LFO sweeps the pulse width for movement. SUB 0 (off), NOISE 0, VCF KYBD 108.",
  "Page 3: LFO RATE 57, DELAY 45, VCF LFO 0. HPF position 0 (K5 = 16). VCA ENV (K6 = 32), LEVEL 52.",
  "Page 1: open the filter fairly far (FREQ 85), RES 0, VCF ENV 0 — the tone stays constant.",
  "Page 1: slow envelope: A = 59, D = 32, S = 86, R = 40.",
  "Page 1: CHORUS II (K8 = 80). Compare with I (48) and I+II (112).",
  "Play chords. Raise ENV A for slower bowing, or ENV R for longer tails."])}
</section>''')
H.append(f'''<section class="page">
{tutorial("A11", "Tutorial 3 — Brass (A11 Brass)",
 "Synth brass relies on a sawtooth and a filter that opens with the envelope and settles back, giving the 'blat' of a horn attack.",
 ["Page 2: RANGE 16' (K1 = 21), WAVE saw only (K5 = 80). PWM SOURCE MAN (K4 = 64); PWM 123 has no audible effect while the pulse is off. SUB 0, NOISE 0, VCF KYBD 86.",
  "Page 1: FREQ 35, RES 13 and a generous VCF ENV 58 — the envelope does the work.",
  "Page 1: envelope A = 3, D = 49, S = 45, R = 32: fast attack, the filter falls back to a sustained level.",
  "Page 1: CHORUS I (K8 = 48).",
  "Page 3: LFO RATE 20, DELAY 49, VCF LFO 0. HPF position 1 = flat (K5 = 48). VCA ENV (K6 = 32), LEVEL 108.",
  "Use the mod wheel for delayed vibrato on held notes. For a slower swell, raise ENV A to about 60."])}
</section>''')

# ---------------- 10 WRITING ----------------
H.append(f'''<section class="page" id="s10">{sect(10, "Writing (Saving) Patches")}
<p>As implemented in v1.1.0, the write procedure is:</p>
<ol class="steps">
<li>Select the target group with GROUP −/+ (bank B, pads 5/6).</li>
<li>Switch the pads to bank A and <b>hold</b> the pad of the target patch number for <b>1.5 seconds</b> (<code>save_hold_seconds</code>).</li>
<li>The LED blinks rapidly to confirm. The memory is written to <code>ju6/patches.syx</code> and named "<i>A15 Egen</i>" ("Egen" = user) in <code>ju6/names.txt</code>.</li>
</ol>
{note("issue", "Reading <code>src/controller.h</code> shows that pressing a bank-A pad <b>first recalls the patch stored on that pad</b> (<code>selectSlot()</code> on note-on), and the save 1.5 s later captures the sound <i>as it is then</i>. Edits made before pressing the pad are therefore replaced by the stored patch and are <b>not</b> written; only knob changes made while the pad is held (within the 1.5 s) end up in memory. The built-in self-test checks only that the save happens to the right slot, not that edits are kept. Until this is fixed in the software, do not rely on the write function to keep a sound you have edited — write the knob values down (the tutorial pages can be used as patch sheets).")}
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
("save_hold_seconds", "1.5", "how long a pad is held to write")]
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
<tr><td>Note 36–43</td><td>10</td><td>pad bank A: patch 1–8 (hold 1.5 s = write)</td></tr>
<tr><td>Note 44–47</td><td>10</td><td>pad bank B 1–4: knob page 1–4</td></tr>
<tr><td>Note 48 / 49</td><td>10</td><td>pad bank B 5/6: group − / +</td></tr>
<tr><td>Note 50</td><td>10</td><td>pad bank B 7: HOLD on/off</td></tr>
<tr><td>Note 51</td><td>10</td><td>pad bank B 8: TRANSPOSE (hold + key; short press = on/off)</td></tr>
<tr><td>Pitch Bend</td><td>any</td><td>BENDER (DCO and VCF depth)</td></tr>
<tr><td>CC 1 (and other <code>mod_cc</code>)</td><td>any</td><td>MOD (LFO depth; LFO trigger in MANUAL)</td></tr>
<tr><td>CC 7</td><td>any</td><td>master volume</td></tr>
<tr><td>CC 64</td><td>any</td><td>HOLD (≥ 64 = on)</td></tr>
<tr><td>CC 70–77</td><td>any</td><td>knobs K1–K8, current page</td></tr>
<tr><td>CC 120, 123</td><td>any</td><td>all notes off</td></tr>
<tr><td>CC 121</td><td>any</td><td>reset bender and MOD</td></tr>
<tr><td>Program Change 0–127</td><td>any</td><td>select A11 … B88</td></tr>
<tr><td>SysEx <code>F0 41 30 0n pp …F7</code></td><td>—</td><td>Juno-106 patch (APR) into the current sound</td></tr>
<tr><td>SysEx <code>F0 41 32 0n cc vv F7</code></td><td>—</td><td>Juno-106 single parameter (IPR)</td></tr>
</table>
<p class="cap">Pad notes are recognised only on the pad channel; notes on other channels (and pad-channel notes that are not pad notes) play the synth. JU-6 Pi transmits no MIDI.</p>
<h2>Patch data format</h2>
<p>Each patch is 18 bytes, as in the Juno-106 APR message: 16 slider values (0–127) in the order LFO RATE, LFO DELAY, DCO LFO, DCO PWM, DCO NOISE, VCF FREQ, VCF RES, VCF ENV, VCF LFO, VCF KYBD, VCA LEVEL, ENV A, ENV D, ENV S, ENV R, DCO SUB, followed by two switch bytes:</p>
<ul><li><b>SW1:</b> bits 0–2 = range 16'/8'/4'; bit 3 = pulse; bit 4 = saw; bit 5 = chorus off (0 = on); bit 6 = chorus I (0 = II).</li>
<li><b>SW2:</b> bit 0 = PWM MAN (0 = LFO); bit 1 = VCF ENV inverted; bit 2 = VCA GATE (0 = ENV); bits 3–4 = HPF (3 − position).</li></ul>
</section>''')

# ---------------- 14 PARAMETER CHART ----------------
chart = [("VCF FREQ", "1", "K1", "CC 70", "0–127", "slider 6"), ("VCF RES", "1", "K2", "CC 71", "0–127", "slider 7"),
("VCF ENV", "1", "K3", "CC 72", "0–127", "slider 8"), ("ENV A / D / S / R", "1", "K4–K7", "CC 73–76", "0–127", "sliders 12–15"),
("CHORUS", "1", "K8", "CC 77", "off · I · II · I+II", "SW1 b5, b6 (+ ext b0)"),
("RANGE", "2", "K1", "CC 70", "16' · 8' · 4'", "SW1 b0–2"), ("DCO LFO", "2", "K2", "CC 71", "0–127", "slider 3"),
("DCO PWM", "2", "K3", "CC 72", "0–127", "slider 4 (0–105 in 106 format)"), ("PWM SOURCE", "2", "K4", "CC 73", "LFO · MAN · ENV", "SW2 b0 (+ ext b1)"),
("WAVE (pulse/saw)", "2", "K5", "CC 74", "off · pulse · saw · both", "SW1 b3, b4"), ("DCO SUB", "2", "K6", "CC 75", "0 = off, 1–127", "slider 16"),
("DCO NOISE", "2", "K7", "CC 76", "0–127", "slider 5"), ("VCF KYBD", "2", "K8", "CC 77", "0–127", "slider 10"),
("LFO RATE", "3", "K1", "CC 70", "0–127", "slider 1"), ("LFO DELAY", "3", "K2", "CC 71", "0–127", "slider 2"),
("VCF LFO", "3", "K3", "CC 72", "0–127", "slider 9"), ("VCF ENV polarity", "3", "K4", "CC 73", "+ · −", "SW2 b1"),
("HPF", "3", "K5", "CC 74", "0 · 1 · 2 · 3", "SW2 b3–4"), ("VCA mode", "3", "K6", "CC 75", "ENV · GATE", "SW2 b2"),
("VCA LEVEL", "3", "K7", "CC 76", "0–127 (≈ −10 … +10 dB)", "slider 11"), ("LFO MODE", "3", "K8", "CC 77", "AUTO · MANUAL", "not stored"),
("BENDER → DCO", "4", "K1", "CC 70", "0–127", "not stored"), ("BENDER → VCF", "4", "K2", "CC 71", "0–127", "not stored"),
("MOD depth", "4", "K3", "CC 72", "0–127", "not stored"), ("TRANSPOSE", "4", "K4", "CC 73", "−12 … +12", "not stored"),
("MASTER VOLUME", "4", "K5", "CC 74", "0–127", "not stored"), ("VOICE MODE", "4", "K6", "CC 75", "Poly I · Poly II · Unison", "not stored"),
("VELOCITY", "4", "K7", "CC 76", "off · on", "not stored"), ("PORTAMENTO", "4", "K8", "CC 77", "0–127", "not stored")]
H.append(f'''<section class="page" id="s14">{sect(14, "Parameter Chart")}
<table class="grid tiny chart"><tr><th>Parameter</th><th>Page</th><th>Knob</th><th>MIDI</th><th>Range / positions</th><th>Stored in patch</th></tr>
{"".join(f"<tr><td><b>{a}</b></td><td class='c'>{p}</td><td class='c'>{k}</td><td>{m}</td><td>{r}</td><td>{s}</td></tr>" for a, p, k, m, r, s in chart)}
</table>
<p class="cap">Page = knob page selected with bank B pads 1–4. Slider numbers refer to the 16 slider bytes of the patch data (section 13). "ext" = JU-6 Pi extension column in <code>names.txt</code>. Page-4 settings are performance settings and are not written with a patch; their start values come from <code>ju6.conf</code>.</p>
<h2>Patch sheet</h2>
<table class="grid sheet"><tr><th>Patch</th><th colspan="8">Page 1: FREQ · RES · ENV · A · D · S · R · CHORUS</th></tr>
<tr><td class="blank"></td>{"<td></td>"*8}</tr>
<tr><th></th><th colspan="8">Page 2: RANGE · DCO LFO · PWM · PWM SRC · WAVE · SUB · NOISE · KYBD</th></tr>
<tr><td class="blank"></td>{"<td></td>"*8}</tr>
<tr><th></th><th colspan="8">Page 3: LFO RATE · DELAY · VCF LFO · ENV POL · HPF · VCA · LEVEL · LFO MODE</th></tr>
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
<p>Banks A and B contain the Juno-106 factory patches as provided by the KR-106 project (parameter values, not samples), in exact 106 format (<code>patches/factory_106.syx</code>). Columns = patch number (pad 1–8), rows = group.</p>
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
<tr><td>Everything sounds transposed</td><td>TRANSPOSE active: short-press pad 8 (bank B), or set page 4, K4 to the centre.</td></tr>
<tr><td>Notes hang</td><td>Press HOLD (bank B, pad 7) to release, or check the sustain pedal.</td></tr>
<tr><td>An edited sound was not kept after writing</td><td>Known issue in v1.1.0 (section 10).</td></tr>
<tr><td>Want factory sounds back</td><td>Delete <code>patches.syx</code> and <code>names.txt</code> on JU6DATA.</td></tr>
</table>
<h2>With a screen and keyboard on the Pi</h2>
<p><code>ju6pi list</code> (patch names), <code>ju6pi bench</code> (CPU margin), <code>ju6pi demo DIR</code> (render WAV examples), <code>ju6pi utganger</code> (sound cards and chosen output), <code>ju6pi selftest</code> (MPK mapping, writing, transpose, SysEx, output selection), <code>journalctl -u ju6pi</code> (log). <code>aplay -l</code> should list <code>RPiDAC [RPi DAC+]</code> when the DAC+ is fitted.</p>
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
("Software", "ju6pi 1.1.0 (9 October 2026), C++17, ALSA; SCHED_FIFO 80 on isolated CPU 3"),
("Licence", "GPL-3.0")]
H.append(f'''<section class="page" id="s17">{sect(17, "Specifications")}
<table class="grid spec">{"".join(f"<tr><th>{a}</th><td>{b_}</td></tr>" for a, b_ in specs)}</table>
<p class="cap">Specifications are taken from the v1.1.0 source and README and are subject to change.</p>
{note("note", "Chorus II and I+II speeds have not yet been verified against hardware by the KR-106 project; the chorus circuit is modelled on the Juno-6/60 family, which shares its topology with the 106. Analogue voice-to-voice variation is only approximated.")}
</section>''')

# ---------------- 18 CREDITS ----------------
H.append(f'''<section class="page" id="s18">{sect(18, "Sources and Credits")}
<h2>What this manual is based on</h2>
<table class="grid small">
<tr><th>Topic</th><th>Source (repository OleBee/juno106-pi, v1.1.0, commit ffbce82)</th></tr>
<tr><td>Knob pages, pad functions, CC/notes, write, transpose, Program Change</td><td><code>src/controller.h</code></td></tr>
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
<div class="endmark"><div class="stripes small"><i></i><i></i><i></i></div>JU-6 Pi · Owner's Manual · v1.1.0 · October 2026</div>
</section>''')

doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>JU-6 Pi Owner's Manual</title><style>{css}</style></head><body>{"".join(H)}</body></html>'''
open('manual.html', 'w').write(doc)
print("written", len(doc))
