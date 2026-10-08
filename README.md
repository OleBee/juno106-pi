# JU-6 Pi – 6-stemmers synth inspirert av Juno-106, for Raspberry Pi 5

Et ferdig SD-kort-image som gjør en **Raspberry Pi 5 (8 GB)** til en frittstående
polysynth i Juno-106-stil. Skriv imaget, koble til en **AKAI MPK Mini Plus** med USB og en
HDMI-lydmottaker, og slå på. Du trenger ikke skjerm, nettverk eller oppsett.

> **Juridisk:** JU-6 Pi er et uavhengig hobbyprosjekt. Det er *inspirert av* Juno-106,
> men har ingen tilknytning til Roland Corporation. «Roland» og «Juno» er varemerker som
> tilhører sine eiere, og de brukes her bare til å beskrive hva synthen etterligner.
> Det finnes ingen ROM-dumper eller samples i prosjektet: all lyd lages av DSP-kode i sanntid.

---

## 1. Kort fortalt

1. Last ned `ju6pi-1.0.0.img.xz` fra [Releases](../../releases). Er den delt i
   `.part-aa`, `.part-ab` …, slår du delene sammen først (se punkt 2).
2. Skriv imaget til et microSD-kort (minst 8 GB) med **Raspberry Pi Imager** eller **balenaEtcher**.
3. Koble til:
   - **HDMI0** (porten **nærmest USB-C-strømkontakten**) går til TV, lydplanke, AV-receiver eller HDMI-lydekstraktor.
     HDMI1 brukes automatisk som reserve.
   - **AKAI MPK Mini Plus** kobles i en hvilken som helst USB-port.
     Andre USB-MIDI-enheter kobles også til automatisk, og du kan plugge dem inn og ut mens synthen går.
   - Strøm: offisiell 27 W USB-C-lader anbefales.
4. Slå på. Etter ca. 10–15 sekunder hører du **to korte toner** (A–E), og den grønne LED-en lyser fast. Da er synthen klar.

| Grønn LED (ACT) | Betyr |
|---|---|
| blinker sakte (1 Hz) | starter, eller venter på lydutgang |
| lyser fast | klar til å spille |
| lyser, med kort pause hvert 2. sekund | klar, men ingen MIDI-enhet funnet |
| raske blink | side/gruppe byttet (antall blink = nummer), eller patch lagret |

## 2. Skrive SD-kortet

**Raspberry Pi Imager:** *Choose Device* → Raspberry Pi 5. *Choose OS* → *Use Custom* → velg
`ju6pi-1.0.0.img.xz`. *Choose Storage* → SD-kortet. Når Imager spør om du vil bruke
OS-tilpasning, svarer du **Nei / No**. Imaget er ferdig konfigurert, og tilpasningen blir ikke brukt.

**balenaEtcher:** *Flash from file* → `ju6pi-1.0.0.img.xz` → *Select target* → *Flash!*

**Hvis filen er delt opp** (GitHub tillater maks 2 GB per fil):
```sh
cat ju6pi-1.0.0.img.xz.part-* > ju6pi-1.0.0.img.xz     # Linux/macOS
copy /b ju6pi-1.0.0.img.xz.part-aa + ju6pi-1.0.0.img.xz.part-ab ju6pi-1.0.0.img.xz   # Windows
sha256sum -c ju6pi-1.0.0.img.xz.sha256
```

## 3. Lydmotoren

Lyden lages av **[Ultramaster KR-106](https://github.com/kayrockscreenprinting/ultramaster_kr106)** sin DSP-kjerne (GPL-3).
Den er en komponentnivå-modell av Juno-106, kalibrert mot målinger av ekte maskinvare,
analyse av 106-firmwaren og SPICE-simuleringer av kretsene. JU-6 Pi pakker denne kjernen inn i et eget,
hodeløst sanntidsprogram (`ju6pi`, C++17, ALSA direkte, ingen JACK/PipeWire). Det er skrevet for Pi 5.

| Del | Hva som er modellert |
|---|---|
| Stemmer | 6 stemmer med 106-ens stemmetildeling (Poly I, som i maskinvaren); Poly II og Unison er tillegg |
| DCO | sag, puls med PWM (MAN / LFO / ENV), sub-oscillator (firkant, én oktav ned), støy, RANGE 16'/8'/4', 106-ens DCO-LFO-kurve |
| VCF | 4-polet resonant lavpass med IR3109-karakter, selvoscillasjon, ENV-modulasjon med polaritet, LFO, KYBD; 2x/4x oversampling |
| HPF | 4 trinn (0–3). Trinn 0 = bassløft, som på 106 |
| VCA | ENV eller GATE, med LEVEL |
| ENV | én ADSR med 106-ens kurver og tider (J106-modus) |
| LFO | triangel med RATE og DELAY (auto-trigger), eller manuell trigger via MOD |
| Chorus | BBD-modell (MN3009-type) med kompander, støy og klokkelekkasje. Modusene I, II og I+II med stereospredning |
| Spill | bender (DCO- og VCF-dybde), MOD (LFO-dybde), Hold, Transpose (hold + tangent, som på 106) |
| Patcher | 128 fabrikkpatcher (bank A og B), lagring til 128 plasser, Juno-106-sysex (APR/IPR) inn |

**Avvik fra en ekte 106** (det jeg vet om):
- Modusene Chorus II og I+II har ikke fått sine hastigheter verifisert mot maskinvare av KR-106-prosjektet ennå.
  Chorus-kretsen er modellert etter Juno-6/60-familien, som deler topologi med 106.
- MOD-spaken på 106 er fjærbelastet og har bare av/på-dybde satt av en knapp. Her er MOD
  kontinuerlig: dybden følger hvor langt mod-hjulet eller joysticken skyves.
- Juno-106-patchformatet kan ikke lagre chorus «I+II» eller «PWM fra ENV». (106 har bare chorus I/II og PWM LFO/MAN på panelet.)
  JU-6 Pi lagrer disse i en egen kolonne i `names.txt`, så de kommer tilbake her.
  En ekte 106 eller en editor ser i stedet nærmeste gyldige verdi (I og MAN).
- Portamento, Unison og anslag (velocity) finnes ikke på 106. Alle er av som standard.
- Analog spredning mellom stemmer (små avvik i filter/envelope fra kort til kort) er bare tilnærmet.

## 4. AKAI MPK Mini Plus – mapping

AKAI publiserer ikke en tabell over fabrikkoppsettet. JU-6 Pi bruker MPK-familiens vanlige standardverdier:
knotter **CC 70–77**, pads på **MIDI-kanal 10** med noter **36–43 (bank A)** og
**44–51 (bank B)**, pitch-hjul = pitch bend, mod-hjul = CC 1 og sustain = CC 64.
Gir din MPK andre verdier, endrer du `ju6.conf` på datapartisjonen (punkt 6). Du trenger ikke kompilere noe på nytt.

**Tangenter:** spiller synthen på alle MIDI-kanaler. Anslag er **av** (som originalen).
Oktav-knappene på MPK virker som vanlig.

**Pitch-hjul / joystick X (Pitch):** BENDER, med DCO-dybde ±2 halvtoner og VCF-dybde 0 som standard (endres på side 4).
**Mod-hjul / joystick Y (CC 1):** MOD (LFO til DCO). I manuell LFO-modus starter MOD også LFO-en.
**Sustain-pedal (CC 64):** HOLD.

### Pads

Trykk **Bank A/B** på MPK for å bytte mellom de to pad-radene.

| Pad | Bank A (patchvalg) | Bank B (funksjoner) |
|---|---|---|
| 1 | patch x1 | side 1: LYD |
| 2 | patch x2 | side 2: DCO |
| 3 | patch x3 | side 3: MOD / HPF / VCA |
| 4 | patch x4 | side 4: SPILL |
| 5 | patch x5 | gruppe − |
| 6 | patch x6 | gruppe + |
| 7 | patch x7 | HOLD av/på |
| 8 | patch x8 | TRANSPOSE (se under) |

- **Patchvalg:** synthen har 16 grupper på 8 patcher: A1x … A8x og B1x … B8x, som på 106.
  Bruk *gruppe −/+* for å velge gruppe og pad 1–8 i bank A for å velge patch.
  Eksempel: gruppe A4, pad 8 gir A48 Synth Bass I. LED-en blinker gruppenummeret.
- **Lagre:** hold en pad i bank A i **1,5 sekunder**. Lyden slik den er nå, med alle knottendringer,
  lagres på den plassen. LED-en blinker raskt for å bekrefte. Lagrede patcher ligger i `ju6/patches.syx` på
  datapartisjonen. Fabrikklyden kommer tilbake hvis du sletter den filen.
- **Transpose:** hold pad 8 (bank B) og trykk en tangent. Tangenten blir ny grunntone (C4 = ingen transponering).
  Et kort trykk på pad 8 slår transponeringen av og på.
- **Program Change** 0–127 velger patch A11 … B88 direkte.

### Knotter (K1–K8): fire sider

Side 1 er aktiv etter oppstart. Bytt side med pad 1–4 i bank B.

| | K1 | K2 | K3 | K4 | K5 | K6 | K7 | K8 |
|---|---|---|---|---|---|---|---|---|
| **1 LYD** | VCF FREQ | VCF RES | VCF ENV | ENV A | ENV D | ENV S | ENV R | CHORUS av / I / II / I+II |
| **2 DCO** | RANGE 16'/8'/4' | DCO LFO | PWM | PWM-kilde LFO / MAN / ENV | BØLGE av / puls / sag / begge | SUB (0 = av) | NOISE | VCF KYBD |
| **3 MOD** | LFO RATE | LFO DELAY | VCF LFO | VCF ENV-polaritet + / − | HPF 0 / 1 / 2 / 3 | VCA ENV / GATE | VCA LEVEL | LFO AUTO / MANUELL |
| **4 SPILL** | BENDER → DCO | BENDER → VCF | MOD-dybde | TRANSPOSE −12 … +12 | VOLUM | STEMMER Poly I / Poly II / Unison | ANSLAG av / på | PORTAMENTO |

Brytere med flere trinn deler knottens vei i like store soner. CHORUS har for eksempel fire soner:
0–31 = av, 32–63 = I, 64–95 = II og 96–127 = I+II. Knottene hopper som standard rett til ny verdi.
Med `knob_takeover = pickup` må knotten først passere gjeldende verdi, og med `knob_mode = relative`
følger den MPK-ens Relative-modus.

**Andre MIDI-meldinger:** CC 7 = volum, CC 120/123 = alle toner av, CC 121 = nullstill bender/MOD,
Juno-106-sysex (`F0 41 30 0n …` patch og `F0 41 32 0n …` parameter) lastes inn som på en 106.

## 5. Lyd ut og latens

### HDMI (standard)

Pi 5 har ingen analog lydutgang. JU-6 Pi sender derfor lyden digitalt over HDMI, som 2-kanals PCM ved 48 kHz.
- **HDMI0** (nærmest USB-C) er primær. **HDMI1** er reserve. **USB-lydkort** er valgfri tredje utgang.
  Rekkefølgen styres med `audio_devices` i `ju6.conf`.
- Lyden virker **uten skjerm**. Imaget har en egen EDID (skjerm-ID) som lover 2-kanals LPCM 32–192 kHz,
  og den tvinges på begge porter via kjernen:
  `video=HDMI-A-1:1280x720M@60D drm.edid_firmware=HDMI-A-1:edid/pi5-hdmi-lyd-hdmi0.bin` (tilsvarende for HDMI-A-2).
  På Pi 5 med KMS er dette det som tilsvarer `hdmi_force_hotplug=1` og `hdmi_drive=2`. De to linjene står også i
  `config.txt` for fastvaren, men leses ikke av KMS-driveren.
- Mottakeren får alltid stereo PCM. Det virker med TV, lydplanke, AV-receiver og
  HDMI-lydekstraktor (HDMI → analog/optisk).
- Hele HDMI-oppsettet er også tilgjengelig som egen pakke i [`hdmi/`](hdmi/) (EDID-generator, ALSA-enheter, verktøy).

### Latens (48 kHz)

Synthen starter med minste buffer og øker selv ett trinn hvis det blir gjentatte underløp
(≥ 3 på 30 sekunder). Trinnet huskes til neste oppstart.

| Trinn | HDMI periode × antall | HDMI buffer | USB-lydkort periode × antall | USB buffer |
|---|---|---|---|---|
| 1 (start) | 256 × 2 | **10,7 ms** | 64 × 2 | **2,7 ms** |
| 2 | 256 × 3 | 16,0 ms | 128 × 2 | 5,3 ms |
| 3 | 512 × 2 | 21,3 ms | 128 × 3 | 8,0 ms |
| 4 | 512 × 3 | 32,0 ms | 256 × 2 | 10,7 ms |
| 5 | 1024 × 2 | 42,7 ms | 256 × 3 | 16,0 ms |
| 6 | 1024 × 3 | 64,0 ms | 512 × 2 | 21,3 ms |

**Total tid fra tangent til lyd** (beregnet, ikke målt på maskinvare):
USB-MIDI ca. 1 ms + én periode for behandling + bufferen + mottakeren.
Med HDMI på trinn 1 blir det ca. **12–17 ms ut av Pi-en**. Selve mottakeren kommer i tillegg:
en HDMI-lydekstraktor bruker typisk 0–2 ms, mens TV-er og AV-receivere kan bruke 20–100 ms.
Velg da «Game»-, «Direct»- eller «Pure»-modus. USB-lydkort på trinn 2 gir ca. 7–10 ms totalt.
Hvilken utgang og buffer synthen faktisk valgte, står i `ju6/status.txt` på datapartisjonen.

### Sanntid

- Lydtråden kjører med `SCHED_FIFO` prioritet 80, låst minne (`mlockall`) og er bundet til CPU 3.
  CPU 3 er isolert fra andre prosesser med `isolcpus=3`.
- CPU-styringen står på `performance` (fast klokke). USB-strømsparing er av, så MIDI-kontrolleren ikke sovner.
- VCF-oversampling velges ved oppstart: 4x hvis CPU-en tåler det med god margin, ellers 2x.
  På boksen der dette ble bygget gikk 4x ca. 7x raskere enn sanntid med 6 stemmer på én kjerne.

## 6. SD-kortet: skrivebeskyttet rot og datapartisjon

| Partisjon | Innhold | Montert |
|---|---|---|
| `bootfs` (FAT) | fastvare, kjerne, `config.txt`, `cmdline.txt` | skrivebeskyttet |
| `rootfs` (ext4) | Raspberry Pi OS Lite (arm64, Debian 13 «trixie», 2026-10-06) + JU-6 Pi | skrivebeskyttet med **overlayroot** (endringer havner i RAM) |
| `JU6DATA` (FAT, 256 MB) | `ju6/ju6.conf`, `ju6/patches.syx`, `ju6/status.txt` … | lese/skrive, `flush` |

Du kan trygt trekke ut strømmen når som helst. Det eneste synthen skriver til, er
`JU6DATA`, og den skriver atomisk (ny fil, fsync, rename). Sett SD-kortet i en PC for å redigere
`ju6/ju6.conf` eller ta sikkerhetskopi av patchene. Se `LES-MEG.txt` på partisjonen.

**Slått av:** Wi-Fi og Bluetooth (`dtoverlay=disable-wifi/disable-bt`), SSH, NetworkManager, cloud-init,
avahi, cron, apt-timere, swap, oppstartsveiviseren (userconfig) og automatisk utvidelse av rotpartisjonen.
Systemloggen ligger bare i RAM.

**Innstillinger** (`ju6/ju6.conf`, alle valg):

| Nøkkel | Standard | Forklaring |
|---|---|---|
| `audio_devices` | `hdmi0 hdmi1 usb` | utganger i prioritert rekkefølge (`null` = ingen lyd) |
| `buffer` | `auto` | `auto` eller fast `PERIODExANTALL`, f.eks. `512x2` |
| `oversample` | `auto` | VCF-oversampling `2` eller `4` |
| `chime` | `on` | klarsignal (to toner) |
| `output_gain_db` | `0` | ekstra nivå ut |
| `voices` | `6` | antall stemmer (1–10) |
| `voice_mode` | `1` | 1 = Poly I, 2 = Poly II, 0 = Unison |
| `velocity` | `off` | anslag |
| `bender_dco` / `bender_vcf` | `0.25` / `0.0` | bender-dybder (0–1) |
| `mod_depth` | `0.5` | MOD-dybde |
| `master_volume` | `0.5` | volum |
| `start_patch` | `0` | patch ved første oppstart (siden huskes siste valgte) |
| `key_channel` | `omni` | tangentkanal (`omni` eller 1–16) |
| `pad_channel` | `10` | pad-kanal |
| `knob_cc` | `70 … 77` | CC-numre for K1–K8 |
| `pad_notes_a` / `pad_notes_b` | `36 … 43` / `44 … 51` | pad-noter |
| `mod_cc` | `1` | CC-er som styrer MOD (flere kan listes) |
| `knob_mode` | `absolute` | eller `relative` |
| `knob_takeover` | `jump` | eller `pickup` |
| `save_hold_seconds` | `1.5` | hvor lenge en pad holdes for å lagre |

## 7. Patchliste

Bank A og B er fabrikkpatchene fra Juno-106, slik KR-106-prosjektet har dem (parameterverdier, ikke samples).
De ligger i nøyaktig 106-format i [`patches/factory_106.syx`](patches/factory_106.syx).

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| **A1x** | Brass | Brass Swell | Trumpet | Flutes | Moving Strings | Brass & Strings | Choir | Piano I |
| **A2x** | Organ I | Organ II | Combo Organ | Calliope | Donald Pluck | Celeste | E Piano I | E Piano II |
| **A3x** | Clock Chimes | Steel Drums | Xylophone | Brass III | Fanfare | Strings III | Pizzicato | High Strings |
| **A4x** | Bass Clarinet | English Horn | Brass Ensemble | Guitar | Koto | Dark Pluck | Funky I | Synth Bass I |
| **A5x** | Lead I | Lead II | Lead III | Funky II | Synth Bass II | Funky III | Thud Wah | Going Up |
| **A6x** | Piano II | Clav. | Frontier Organ | Snare Drum | Tom Toms | Timpani | Shaker | Synth Pad |
| **A7x** | Sweep I | Pluck Sweep | Repeater | Sweep II | Pluck Bell | Dark Synth Piano | Sustainer | Wah Release |
| **A8x** | Gong | Resonance Funk | Drum Booms | Dust Storm | Rocket Men | Hand Claps | FX Sweep | Caverns |

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| **B1x** | Strings | Violin | Chorus Vibes | Organ I | Harpsichord I | Recorder | Perc Pluck | Noise Sweep |
| **B2x** | Space Chimes | Nylon Guitar | Orchestral Pad | Bright Pluck | Organ Bell | Accordion | FX Rise 1 | FX Rise 2 |
| **B3x** | Brass | Helicopter | Lute | Chorus Funk | Tomita | FX Sweep 1 | Sharp Reed | Bass Pluck |
| **B4x** | Resonant Rise | Harpsichord 2 | Dark Ensemble | Contact Wah | Noise Sweep 2 | Glassy Wah | Phase Ensemble | Chorused Bell |
| **B5x** | Clav | Organ 2 | Bassoon | Auto Noise Sweep | Brass Ensemble | Ethereal | Chorus Bell 2 | Blizzard |
| **B6x** | E Piano Trem | Clarinet | Thunder | Reedy Organ | Flute / Horn | Toy Rhodes | Surf's Up | OW Bass |
| **B7x** | Piccolo | Melodic Taps | Meow Bass | Violin (high) | High Bells | Rolling Wah | Ping Bell | Brassy Organ |
| **B8x** | Low Dark Strings | Piccolo Trumpet | Cello | High Strings | Rocket Men | Forbidden Planet | Froggy | Owgan |

### Sysex-format

Hver patch er 18 byte, som i Juno-106-meldingen *APR* (`F0 41 30 0n pp` + 18 byte + `F7`, der `pp` = patchnummer 0–127):
16 slidere (0–127, i rekkefølgen LFO RATE, LFO DELAY, DCO LFO, DCO PWM, DCO NOISE, VCF FREQ, VCF RES,
VCF ENV, VCF LFO, VCF KYBD, VCA LEVEL, ENV A, ENV D, ENV S, ENV R, DCO SUB), deretter to bryterbytes:

- **SW1:** bit 0–2 = range 16'/8'/4'. Bit 3 = puls og bit 4 = sag. Bit 5 = chorus av (0 = på). Bit 6 = chorus I (0 = II).
- **SW2:** bit 0 = PWM MAN (0 = LFO). Bit 1 = VCF ENV invertert. Bit 2 = VCA GATE (0 = ENV).
  Bit 3–4 = HPF (3 − posisjon).

`ju6/patches.syx` er 128 slike meldinger etter hverandre. `names.txt` har én linje per egen patch:
`A11<TAB>navn[<TAB>ext]`, der `ext` bit 0 = chorus I+II og bit 1 = PWM fra ENV.
Filen kan lastes inn i vanlige Juno-106-editorer.

## 8. Bygge selv

```sh
sudo apt install g++ make libasound2-dev g++-aarch64-linux-gnu libasound2-dev:arm64 \
                 qemu-user-static fdisk dosfstools mtools e2fsprogs zerofree xz-utils
make                    # vert-binær: build/ju6pi
make samples            # WAV-prøver til samples/
./build/ju6pi selftest  # tester MPK-mapping, lagring, transpose, sysex …
make arm64              # build/ju6pi-arm64 (Cortex-A76)
sudo image/build-image.sh 2026-10-06-raspios-trixie-arm64-lite.img.xz build/ju6pi-arm64 ju6pi.img
xz -T0 -9 ju6pi.img
```
`build-image.sh` tar det offisielle Raspberry Pi OS Lite-imaget og bygger resten i en qemu-chroot:
utvider rotpartisjonen, lager JU6DATA, installerer overlayroot, ju6pi, EDID og ALSA-oppsett, og slår av tjenester.

Kommandoer på Pi-en (krever skjerm og tastatur, eller å montere SD-kortet):
`ju6pi list` (patcher), `ju6pi bench` (CPU-margin), `ju6pi demo KATALOG` (WAV), `journalctl -u ju6pi` (logg).

## 9. Lisens og kreditering

- **GPL-3.0** (se `LICENSE`), fordi lydmotoren er GPL-3.
- Lydmotor: **Ultramaster KR-106** av Karl LaRocca (og den opprinnelige Ultramaster-gruppen, se `third_party/kr106/AUTHORS`).
  Ligger uendret i `third_party/kr106/`; se `UPSTREAM.txt` for commit.
- Raspberry Pi OS © Raspberry Pi Ltd. og Debian-prosjektet, med egne lisenser.
- Navnet «JU-6 Pi» er valgt for å ikke bruke Rolands varemerker.
