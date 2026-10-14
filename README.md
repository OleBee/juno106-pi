# JU-6 Pi – 6-stemmers synth inspirert av Juno-106, for Raspberry Pi 5

Et ferdig SD-kort-image som gjør en **Raspberry Pi 5 (8 GB)** til en frittstående
polysynth i Juno-106-stil. Skriv imaget, koble til en **AKAI MPK Mini Plus** med USB og en
HDMI-lydmottaker eller et **Raspberry Pi DAC+**-lydkort (fra 1.1.0), og slå på. Du trenger ikke skjerm, nettverk eller oppsett.

> **Juridisk:** JU-6 Pi er et uavhengig hobbyprosjekt. Det er *inspirert av* Juno-106,
> men har ingen tilknytning til Roland Corporation. «Roland» og «Juno» er varemerker som
> tilhører sine eiere, og de brukes her bare til å beskrive hva synthen etterligner.
> Det finnes ingen ROM-dumper eller samples i prosjektet: all lyd lages av DSP-kode i sanntid.

> **Bruksanvisning (engelsk):** [JU-6 Pi Owner's Manual (PDF)](docs/JU-6_Pi_Owners_Manual.pdf) – panel, pads og knotter på MPK Mini Plus, patchvalg, lydutganger, oppskrifter på lyder og parameterliste.

---

## 1. Kort fortalt

1. Last ned `ju6pi-1.1.0.img.xz` fra [Releases](../../releases). Er den delt i
   `.part-aa`, `.part-ab` …, slår du delene sammen først (se punkt 2).
2. Skriv imaget til et microSD-kort (minst 8 GB) med **Raspberry Pi Imager** eller **balenaEtcher**.
3. Koble til:
   - **Raspberry Pi DAC+** (hvis du har det): RCA-utgangene går til forsterker, mikser eller aktive høyttalere.
     Synthen bruker kortet automatisk når det sitter på. Se punkt 5.
   - Uten DAC+: **HDMI0** (porten **nærmest USB-C-strømkontakten**) går til TV, lydplanke, AV-receiver eller HDMI-lydekstraktor.
     HDMI1 brukes automatisk som reserve.
   - **AKAI MPK Mini Plus** kobles i en hvilken som helst USB-port.
     Andre USB-MIDI-enheter kobles også til automatisk, og du kan plugge dem inn og ut mens synthen går.
   - Strøm: offisiell 27 W USB-C-lader anbefales.
4. Slå på. Etter ca. 10–15 sekunder hører du **to korte toner** (A–E), og den grønne LED-en lyser fast. Da er synthen klar.

| Grønn LED (ACT) | Betyr |
|---|---|
| blinker sakte (1 Hz) | starter, eller venter på lydutgang |
| lyser fast | klar til å spille |
| lyser, med to korte pauser hvert 3. sekund | klar, men på reserveutgang: `audio_output = dacplus`, og DAC+ ble ikke funnet |
| lyser, med kort pause hvert 2. sekund | klar, men ingen MIDI-enhet funnet |
| raske blink | side/gruppe byttet (antall blink = nummer), eller patch lagret |

## 2. Skrive SD-kortet

**Raspberry Pi Imager:** *Choose Device* → Raspberry Pi 5. *Choose OS* → *Use Custom* → velg
`ju6pi-1.1.0.img.xz`. *Choose Storage* → SD-kortet. Når Imager spør om du vil bruke
OS-tilpasning, svarer du **Nei / No**. Imaget er ferdig konfigurert, og tilpasningen blir ikke brukt.

**balenaEtcher:** *Flash from file* → `ju6pi-1.1.0.img.xz` → *Select target* → *Flash!*

**Hvis filen er delt opp** (GitHub tillater maks 2 GB per fil):
```sh
cat ju6pi-1.1.0.img.xz.part-* > ju6pi-1.1.0.img.xz     # Linux/macOS
copy /b ju6pi-1.1.0.img.xz.part-aa + ju6pi-1.1.0.img.xz.part-ab ju6pi-1.1.0.img.xz   # Windows
sha256sum -c ju6pi-1.1.0.img.xz.sha256
```

## 3. Lydmotoren

Lyden lages av **[Ultramaster KR-106](https://github.com/kayrockscreenprinting/ultramaster_kr106)** sin DSP-kjerne (GPL-3).
Den er en komponentnivå-modell av Juno-106, kalibrert mot målinger av ekte maskinvare,
analyse av 106-firmwaren og SPICE-simuleringer av kretsene. JU-6 Pi pakker denne kjernen inn i et eget,
hodeløst sanntidsprogram (`ju6pi`, C++17, ALSA direkte, ingen JACK/PipeWire). Det er skrevet for Pi 5.
Lyden går ut på Raspberry Pi DAC+ (hvis det sitter på) eller HDMI.

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

Hvilken utgang synthen bruker, styres med `audio_output` i `ju6/ju6.conf` på datapartisjonen.
Du trenger ikke kompilere noe på nytt.

| `audio_output` | Betyr |
|---|---|
| `auto` (standard) | Raspberry Pi DAC+ hvis kortet sitter på, ellers HDMI0, så HDMI1, så USB-lydkort |
| `dacplus` | Raspberry Pi DAC+. Mangler kortet, spiller synthen på HDMI0/HDMI1/USB i stedet, men varsler (se under) |
| `hdmi` | bare HDMI0, så HDMI1, akkurat som i 1.0.0. DAC+ brukes ikke selv om det sitter på |
| `usb` | bare USB-lydkort |
| `null` | ingen lyd (test) |

Kortene finnes etter navn, ikke nummer, så rekkefølgen ALSA nummererer dem i spiller ingen rolle.
Den gamle innstillingen `audio_devices = hdmi0 hdmi1 usb` virker fortsatt (nå også med `dacplus` i lista),
men bare når `audio_output` ikke er satt.

### Raspberry Pi DAC+

[Raspberry Pi DAC+](https://www.raspberrypi.com/products/dac-plus/) (tidligere IQaudIO DAC+) er et lydkort som settes
på GPIO-pinnene. Det har en TI PCM5122 DAC-krets, to RCA-kontakter (linje ut, 0–2 V RMS) og en 3,5 mm
hodetelefonutgang. Det har ingen inngang.

**Montering i KKSB Højt Case med Active Cooler:**
1. Monter Active Cooler på Pi 5 som vanlig, og koble viftekabelen til FAN-kontakten.
2. Sett den 40-pins stacking headeren (forlengeren) som følger med kabinettet på GPIO-pinnene på Pi-en.
   Den løfter DAC-kortet over kjøleren.
3. Sett DAC+ på toppen av forlengeren, med RCA-kontaktene mot åpningene i kabinettet.
   Bruk avstandsstykkene og skruene som følger med kabinettet, så kortet ikke henger bare i pinnene.
4. Sjekk at ingen pinner er forskjøvet én rad før du setter på strøm.

**Imaget er klart for kortet.** `config.txt` laster overlayet `rpi-dacplus` hver gang. Uten kortet skjer det ingenting
med HDMI-lyden. Overlayet rører bare I2S, I2C1 og lydkort-noden, og kortet dukker bare ikke opp.
Linjen `dtoverlay=` øverst i `config.txt` gjør at fastvaren ikke i tillegg laster overlayet fra kortets HAT-EEPROM,
slik at det ikke lastes to ganger. (Det betyr også at andre HAT-kort ikke får overlayet sitt automatisk.)
Eldre svarte IQaudIO DAC+-kort virker med det samme overlayet. De er elektrisk like.

**Lyd:** 48 kHz, 32 bit til kretsen, og bufferen starter på 128 × 2 rammer (5,3 ms). Ved oppstart setter synthen kortets
mikser: «Digital» til 0 dB (ikke dempet), «Analogue» til 0 dB (2 V RMS ut) og «Analogue Playback Boost» til 0 dB.
Vil du ha lavere nivå ut, sett `dacplus_volume_db = -6` (eller annen negativ verdi). Positive verdier brukes ikke,
for de kan gi klipping. RCA-utgangen og hodetelefonutgangen får samme stereosignal.

**Oppstart:** DAC-driveren kan komme litt senere enn HDMI. Står det et DAC-kort i HAT-EEPROM-en, eller er
`audio_output = dacplus`, venter synthen opptil 8 sekunder (`dacplus_wait`) på kortet. Startet den likevel på HDMI,
og DAC+ dukker opp i løpet av det første minuttet, bytter den over til DAC+ og spiller klartonene på nytt der.

**Når `audio_output = dacplus`, og kortet ikke blir funnet,** spiller synthen på HDMI0, HDMI1 eller USB i stedet, og
- klartonene er **synkende** (E–A) i stedet for stigende (A–E),
- den grønne LED-en lyser med **to korte pauser hvert 3. sekund**,
- `ju6/status.txt` har en linje som starter med `ADVARSEL`.

**Sjekke at kortet virker.** Imaget har ikke SSH eller nettverk, så du sjekker det slik:
1. Slå på med DAC+ montert og RCA koblet til forsterkeren. Etter 10–15 sekunder skal du høre to **stigende** toner
   fra RCA-utgangen, og LED-en skal lyse fast (eller med én kort pause hvis ingen MIDI-enhet er koblet til).
2. Ta ut SD-kortet, sett det i en PC og åpne `ju6/status.txt` på JU6DATA. Der skal det stå
   `lyd: Raspberry Pi DAC+ (RCA/hodetelefon) (plughw:CARD=RPiDAC,DEV=0)` og `lydkort funnet: vc4hdmi0, vc4hdmi1, RPiDAC`,
   pluss en linje om mikseren.
3. Har du skjerm og tastatur på Pi-en, viser `ju6pi utganger` kortene ALSA ser, og hvilken utgang som blir valgt.
   `aplay -l` skal vise `card N: RPiDAC [RPi DAC+]`. Med SSH (finnes ikke i imaget som standard) gjelder de samme kommandoene.

### HDMI

Pi 5 har ingen analog lydutgang. Uten DAC+ sender JU-6 Pi derfor lyden digitalt over HDMI, som 2-kanals PCM ved 48 kHz.
- **HDMI0** (nærmest USB-C) er primær. **HDMI1** er reserve. **USB-lydkort** er valgfri tredje utgang.
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

| Trinn | HDMI periode × antall | HDMI buffer | DAC+ periode × antall | DAC+ buffer | USB-lydkort periode × antall | USB buffer |
|---|---|---|---|---|---|---|
| 1 (start) | 256 × 2 | **10,7 ms** | 128 × 2 | **5,3 ms** | 64 × 2 | **2,7 ms** |
| 2 | 256 × 3 | 16,0 ms | 128 × 3 | 8,0 ms | 128 × 2 | 5,3 ms |
| 3 | 512 × 2 | 21,3 ms | 256 × 2 | 10,7 ms | 128 × 3 | 8,0 ms |
| 4 | 512 × 3 | 32,0 ms | 256 × 3 | 16,0 ms | 256 × 2 | 10,7 ms |
| 5 | 1024 × 2 | 42,7 ms | 512 × 2 | 21,3 ms | 256 × 3 | 16,0 ms |
| 6 | 1024 × 3 | 64,0 ms | 512 × 3 | 32,0 ms | 512 × 2 | 21,3 ms |

**Total tid fra tangent til lyd** (beregnet, ikke målt på maskinvare):
USB-MIDI ca. 1 ms + én periode for behandling + bufferen + mottakeren.
Med HDMI på trinn 1 blir det ca. **12–17 ms ut av Pi-en**. Selve mottakeren kommer i tillegg:
en HDMI-lydekstraktor bruker typisk 0–2 ms, mens TV-er og AV-receivere kan bruke 20–100 ms.
Velg da «Game»-, «Direct»- eller «Pure»-modus. USB-lydkort på trinn 2 gir ca. 7–10 ms totalt.
DAC+ på trinn 1 gir ca. 8–10 ms ut av RCA-kontaktene, og en analog forsterker legger ikke til noe å snakke om.
Ingen av tallene er målt på maskinvare ennå.
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
| `audio_output` | `auto` | `auto`, `dacplus`, `hdmi`, `usb` eller `null` (se punkt 5) |
| `dacplus_volume_db` | `0` | DAC+-mikseren «Digital» i dB (0 eller negativ) |
| `dacplus_wait` | `8` | sekunder å vente på DAC+ ved oppstart |
| `audio_devices` | (ikke satt) | gammel liste i prioritert rekkefølge (`dacplus hdmi0 hdmi1 usb null`), brukes bare uten `audio_output` |
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
Henger apt i qemu-chrooten, kan du laste ned `overlayroot` (all) og `cryptsetup`/`cryptsetup-bin` (arm64)
til en katalog og kjøre `sudo DEBS=katalog image/build-image.sh …`.

`build-image.sh` tar det offisielle Raspberry Pi OS Lite-imaget og bygger resten i en qemu-chroot:
utvider rotpartisjonen, lager JU6DATA, installerer overlayroot, ju6pi, EDID og ALSA-oppsett, legger inn
DAC+-overlayet i `config.txt` (fra `image/boot/dacplus.blokk`) og slår av tjenester.

`./build/ju6pi selftest` tester også valget av lydutgang mot falske ALSA-kortlister. Hele sanntidsløkka kan kjøres
uten lydkort med `JU6_FAKE_CARDS=fil` (linjer `nummer id driver navn`, alle utganger blir ALSA `null`)
og `JU6_LED_DIR=katalog` (falsk LED).

Kommandoer på Pi-en (krever skjerm og tastatur, eller å montere SD-kortet):
`ju6pi list` (patcher), `ju6pi bench` (CPU-margin), `ju6pi demo KATALOG` (WAV), `ju6pi utganger` (lydkort og valgt utgang),
`journalctl -u ju6pi` (logg).

## 9. Endringer

**1.1.0 (9. oktober 2026)**
- Støtte for Raspberry Pi DAC+ (PCM5122, RCA og hodetelefon). Overlayet `rpi-dacplus` lastes alltid, og
  HAT-EEPROM-overlayet slås av så det ikke lastes to ganger.
- Ny innstilling `audio_output = auto | dacplus | hdmi | usb | null`. Standard `auto` bruker DAC+ hvis det sitter på,
  ellers HDMI0 og så HDMI1. Kortene finnes etter navn, ikke nummer.
- DAC+: 48 kHz, 32 bit, start på 128 × 2 rammer (5,3 ms), og mikseren settes til 0 dB uten demping ved oppstart.
  Nivået kan senkes med `dacplus_volume_db`.
- Venter på DAC-driveren ved oppstart, og bytter til DAC+ hvis den kommer etter at synthen har startet på HDMI.
- Reserveutgang varsles med synkende klartoner, egen LED-rytme og `ADVARSEL` i `status.txt`.
- `status.txt` viser utgangsvalg, lydkortene som ble funnet og DAC-mikseren.
- Ny kommando: `ju6pi utganger`. Selvtesten dekker nå valg av lydutgang.
- HDMI-oppsettet er uendret. `audio_output = hdmi` gir samme oppførsel som 1.0.0.

**1.0.0 (8. oktober 2026)**
- Første utgave: KR-106-lydmotor, 128 fabrikkpatcher, Juno-106-sysex, AKAI MPK Mini Plus-mapping, HDMI-lyd,
  skrivebeskyttet SD-kort med datapartisjon.

## 10. Lisens og kreditering

- **GPL-3.0** (se `LICENSE`), fordi lydmotoren er GPL-3.
- Lydmotor: **Ultramaster KR-106** av Karl LaRocca (og den opprinnelige Ultramaster-gruppen, se `third_party/kr106/AUTHORS`).
  Ligger uendret i `third_party/kr106/`; se `UPSTREAM.txt` for commit.
- Raspberry Pi OS © Raspberry Pi Ltd. og Debian-prosjektet, med egne lisenser.
- Navnet «JU-6 Pi» er valgt for å ikke bruke Rolands varemerker.
