# Pi 5: HDMI som fast lydutgang

Oppsett for Raspberry Pi 5 (Raspberry Pi OS Bookworm/Trixie, KMS-grafikk) der **lyden alltid
går via HDMI**, også når ingen skjerm er tilkoblet. Lyden skal kunne gå til en lydplanke,
AV-receiver eller HDMI-lydekstraktor.

| Rolle | Fysisk port | DRM-navn | ALSA-kort | PipeWire-node (Pi 5) |
|---|---|---|---|---|
| **Primær** | **HDMI0**, porten **nærmest USB-C-strømmen** | `HDMI-A-1` | `vc4hdmi0` | `alsa_output.platform-107c701400.hdmi.*` |
| Reserve | HDMI1, porten lengst fra strømmen | `HDMI-A-2` | `vc4hdmi1` | `alsa_output.platform-107c706400.hdmi.*` |
| Valgfri reserve | USB-lydkort | – | f.eks. `Device` | `alsa_output.usb-*` |

Pi 5 har ingen analog 3,5 mm-utgang, så HDMI eller USB er de eneste lydutgangene.

## Kort fortalt

```bash
git clone … pi5-hdmi-lyd && cd pi5-hdmi-lyd
sudo ./installer.sh            # eller: sudo ./installer.sh --edid fang  (se under)
sudo reboot
lyd-utgang status              # sjekk at HDMI0 er standard og at eld_valid = 1
lyd-latenstest --last          # finn minste stabile buffer på akkurat ditt oppsett
```

## Hvorfor det trengs mer enn `hdmi_force_hotplug` på Pi 5

På Pi 5 styres HDMI av KMS-driveren `vc4-kms-v3d` i kjernen, ikke av fastvaren. Det betyr:

1. **`hdmi_force_hotplug=1` og `hdmi_drive=2` i `config.txt` leses ikke av kjernen.** De står
   fortsatt i blokken vår (per port: `hdmi_force_hotplug:0=1`, `hdmi_drive:0=2` osv.), men
   de virker bare i fastvarefasen før kjernen tar over.
2. **KMS gir bare HDMI-lyd når EDID-en sier at mottakeren tar imot lyd.** Uten skjerm (eller
   med en receiver i standby som ikke svarer) er det ingen EDID. Da blir det ingen lyd, selv med
   tvunget hotplug.
3. **HDMI kan ikke sende bare lyd.** Lyden legges i pausene i videosignalet, så det må gå et
   videosignal hele tiden.

Dette er det som erstatter de gamle innstillingene under KMS:

| Gammel innstilling (fastvare) | Det som gjelder på Pi 5/KMS (i `cmdline.txt`) |
|---|---|
| `hdmi_force_hotplug=1` | `video=HDMI-A-1:1280x720M@60D` (`D` = tving porten på) |
| `hdmi_drive=2` (HDMI-modus, ikke DVI) | `drm.edid_firmware=HDMI-A-1:edid/pi5-hdmi-lyd-hdmi0.bin`, en EDID med HDMI-blokk og lydblokk |

`installer.sh` legger inn begge deler for HDMI0 og HDMI1. Den setter også
`disable_fw_kms_setup=1`, slik at fastvaren ikke skriver sine egne `video=` over våre. I tillegg
fjerner den eventuell `,noaudio` fra `dtoverlay=vc4-kms-v3d`.

Linjen som legges til på slutten av `cmdline.txt` (alt skal stå på én linje):

```
video=HDMI-A-1:1280x720M@60D video=HDMI-A-2:1280x720M@60D drm.edid_firmware=HDMI-A-1:edid/pi5-hdmi-lyd-hdmi0.bin,HDMI-A-2:edid/pi5-hdmi-lyd-hdmi1.bin
```

720p60 er valgt med vilje. Det er nok båndbredde for 2-kanals LPCM opptil 192 kHz (og 8 kanaler),
og nesten alle mottakere godtar det.

### EDID: generert eller fanget

- **`--edid generert`** (standard): `edid/lag-edid.py` lager en liten EDID som består
  `edid-decode -c`. Den sier at mottakeren er HDMI og tar imot **2-kanals LPCM, 32–192 kHz,
  16/20/24 bit**. Den virker uten noe tilkoblet, mot lydekstraktorer og mot receivere i standby.
- **`--edid fang`**: Bruk dette hvis receiveren eller lydplanken er **på** når du installerer.
  Da lagres mottakerens ekte EDID (`lyd-fang-edid hdmi0`), slik at f.eks. 5.1/7.1 LPCM beholdes
  selv når mottakeren senere er av eller i standby. Porter uten en EDID med lyd får den genererte.

**NB:** `drm.edid_firmware` *erstatter* alltid EDID-en fra det som er koblet til. Bytter du
mottaker, må du fange på nytt. Det gjør du slik: fjern `drm.edid_firmware=…` fra
`cmdline.txt`, start på nytt med mottakeren på og kjør `sudo lyd-fang-edid hdmi0`. Legg så
linjen inn igjen (eller kjør `sudo ./installer.sh --edid fang` på nytt).

EDID-filene ligger i `/lib/firmware/edid/`. En initramfs-krok kopierer dem også inn i initramfs,
siden Pi OS på Pi 5 bruker `auto_initramfs=1`.

## Standard utgang: HDMI0 primær, HDMI1 reserve, USB valgfritt

**Med PipeWire** (standard på Pi OS med skrivebord) setter WirePlumber-regelen
(`/etc/wireplumber/wireplumber.conf.d/51-pi5-hdmi-lyd.conf`, eller `.lua` på WirePlumber 0.4)
disse prioritetene:

- HDMI0 `priority.session = 2000`, så den blir standard
- HDMI1 `1500`
- USB-lydkort `1000`, så det brukes bare hvis ingen HDMI-utgang finnes

Begge HDMI-portene er tvunget på, så begge finnes alltid og HDMI0 vinner. Reserven tar du i bruk
med én kommando, uten omstart:

```bash
lyd-utgang hdmi1     # bytt til reserven (f.eks. ved feil på kabel/port)
lyd-utgang hdmi0     # tilbake til primær
lyd-utgang usb       # valgfritt USB-lydkort
lyd-utgang auto      # første som finnes av hdmi0 → hdmi1 → usb
lyd-utgang status
```

`session.suspend-timeout-seconds = 0` holder HDMI-strømmen åpen hele tiden. Receivere,
lydplanker og ekstraktorer bruker ofte 0,5–2 s på å låse seg på signalet igjen. Uten denne
innstillingen kuttes derfor starten av hver lyd.

**Uten PipeWire** (Pi OS Lite, ren ALSA): `sudo ./installer.sh --uten-pipewire` setter
`pcm.!default lyd_hdmi0` i `/etc/asound.conf`. `lyd-utgang hdmi1/usb` bytter den linjen.
De navngitte enhetene `lyd_hdmi0`, `lyd_hdmi1` og `lyd_usb` (i
`/etc/alsa/conf.d/60-pi5-hdmi-lyd.conf`) finnes uansett. Maskinvaren tar bare
`IEC958_SUBFRAME_LE`, så de går via ALSAs `hdmi:`-enhet (iec958-plugin), som konverterer. Det er
ingen softvol i kjeden, for at forsinkelsen skal bli minst mulig. Volumet styres på mottakeren.

## Buffer og latens

HDMI-lyd på Pi 5 tåler ikke like små buffere som et godt USB-lydkort. Det er tre grunner til det:

- Lyden flyttes med DMA inn i HDMI-FIFO-en og klokkes av videotimingen.
- Dataene må pakkes om til IEC958-subrammer (32 bit per sample).
- Det er kjent at det har vært underløp når minnebussen er travel.

Derfor er oppsettet lagt i nivåer. **Nivå A er standard**, og du går opp ett nivå bare hvis
`lyd-latenstest` finner underløp eller du hører knitring.

| Nivå | PipeWire quantum | ALSA `period-size` / `headroom` | Per syklus | **Beregnet latens i Pi-en** |
|---|---|---|---|---|
| **A (standard)** | 256 | 256 / 256 | 5,3 ms | **ca. 11–16 ms** |
| B | 512 | 512 / 512 | 10,7 ms | ca. 21–32 ms |
| C | 1024 | 1024 / 1024 | 21,3 ms | ca. 43–64 ms |
| Ren ALSA (`lyd_hdmi0`) | – | 256 × 2 perioder | 5,3 ms | buffer 10,7 ms |
| USB-reserve (ALSA) | – | 128 × 2 perioder | 2,7 ms | buffer 5,3 ms |

Alt er ved 48 kHz (grafen er låst til 48 kHz, så det blir ingen resampling eller ratebytte).
Latensen i Pi-en er omtrent graf-quantum + det som ligger i ALSA-bufferen
(periode + headroom).

Slik bytter du nivå: endre `default.clock.quantum`/`min-quantum` i
`/etc/pipewire/pipewire.conf.d/50-pi5-hdmi-lyd.conf` og `api.alsa.period-size`/`api.alsa.headroom`
i WirePlumber-regelen. Kjør så `systemctl --user restart wireplumber pipewire`.

**Måling på ditt oppsett:**

```bash
lyd-latenstest --last                        # ren ALSA: periode 64…1024 × 2/3 perioder, med CPU-last
lyd-latenstest --modus pipewire --last       # PipeWire: quantum 256/512/1024
lyd-latenstest --utgang usb                  # det valgfrie USB-kortet
```

Testen spiller **stillhet**, så det kommer ikke høy støy ut av receiveren. Den teller underløp,
viser hvilke periode- og bufferstørrelser driveren faktisk godtok, og foreslår den minste
stabile. Legg på én periode ekstra som margin til daglig bruk.

**Mottakeren kommer i tillegg** og styres ikke av Pi-en:

- HDMI-lydekstraktorer: typisk 0–2 ms
- AV-receivere i Direct/Pure Direct: typisk noen få ms. Med DSP eller romkorreksjon ofte 10–50 ms
  eller mer.
- Lydplanker: ofte 30–100 ms eller mer. Mange har en «AV sync»- eller «lip sync»-innstilling.

Total latens = Pi-en (tabellen over) + mottakeren.

## Tilkobling

- Lydplanke: Koble til lydplankens **HDMI IN**, ikke ARC/eARC-porten mot TV-en. Har lydplanken
  ikke HDMI-inngang, bruk en HDMI-lydekstraktor (HDMI inn, optisk/analog ut).
- AV-receiver: Bruk en vanlig HDMI-inngang. Fang gjerne den ekte EDID-en med `--edid fang`, så
  får du flerkanal.
- HDMI-til-DVI-adaptere har ikke lyd.

## Feilsøking

| Symptom | Sjekk |
|---|---|
| Ingen `vc4hdmi0` i `aplay -l` | `tr ' ' '\n' </proc/cmdline \| grep -E 'video=HDMI\|edid'`, så `dmesg \| grep -i edid` (ser du `failed with error -2`, mangler EDID-filen eller den mangler i initramfs) |
| `eld_valid 0` i `lyd-utgang status` | EDID-en mangler lydblokk (f.eks. fanget fra en skjerm uten lyd). Kjør `sudo ./installer.sh` på nytt med `--edid generert` |
| Starten av lyden kuttes | `session.suspend-timeout-seconds = 0` mangler, eller mottakeren låser seg tregt |
| Knitring | Gå til nivå B, og så C. Sjekk `pw-top` (ERR-kolonnen) |
| Feil port brukes | `lyd-utgang hdmi0`. Sjekk at kabelen står i porten **nærmest USB-C** |

## Filer

```
installer.sh                      installer / --avinstaller / --dry-run / ROOT=… for SD-kort
boot/config.txt.blokk             blokken som legges i config.txt
boot/cmdline-tillegg.txt          det som legges til i cmdline.txt
edid/lag-edid.py, pi5-hdmi-lyd.bin  generert EDID (2 kanaler LPCM, HDMI, 720p/1080p)
pipewire/50-pi5-hdmi-lyd.conf     48 kHz, quantum 256
wireplumber/51-pi5-hdmi-lyd.conf  prioritet HDMI0 > HDMI1 > USB, buffer, ingen suspend (WP 0.5)
wireplumber/51-pi5-hdmi-lyd.lua   samme for WirePlumber 0.4
alsa/60-pi5-hdmi-lyd.conf         lyd_hdmi0 / lyd_hdmi1 / lyd_usb
initramfs/pi5-hdmi-lyd-edid       tar med EDID-filene i initramfs
bin/lyd-utgang                    vis/bytt utgang
bin/lyd-latenstest                finn minste stabile buffer og latens
bin/lyd-fang-edid                 lagre mottakerens ekte EDID
```

Installeren tar sikkerhetskopi av `config.txt` og `cmdline.txt`
(`*.pi5-hdmi-lyd.bak-<tidspunkt>`) før den endrer noe, og den kan trygt kjøres flere ganger.
