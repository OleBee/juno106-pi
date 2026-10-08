#!/usr/bin/env bash
# installer.sh – gjør HDMI til fast standard lydutgang på Raspberry Pi 5.
#
#   sudo ./installer.sh [valg]
#     --edid generert   (standard) innebygd 2-kanals EDID – virker uten skjerm/mottaker
#     --edid fang       lagre EKTE EDID fra mottakeren som er PÅ nå (beholder f.eks. 5.1/7.1);
#                       faller tilbake til generert for porter uten lyd-EDID
#     --kun-hdmi0       tving bare HDMI0 (HDMI1 brukes da bare når noe faktisk er koblet til)
#     --uten-pipewire   ren ALSA: sett pcm.!default = HDMI0 i /etc/asound.conf
#     --dry-run         vis hva som ville blitt gjort
#     --avinstaller     fjern alt dette igjen
#   Miljø: ROOT=/sti  installer i et montert image (for testing / SD-kort på en annen maskin)
set -euo pipefail

HER=$(cd "$(dirname "$0")" && pwd)
ROOT=${ROOT:-}
edid=generert; kun0=0; utenpw=0; dry=0; avinst=0
MERKE_START="# >>> pi5-hdmi-lyd >>>"; MERKE_SLUTT="# <<< pi5-hdmi-lyd <<<"
while [[ $# -gt 0 ]]; do
    case $1 in
        --edid) edid=$2; shift 2 ;;
        --kun-hdmi0) kun0=1; shift ;;
        --uten-pipewire) utenpw=1; shift ;;
        --dry-run) dry=1; shift ;;
        --avinstaller) avinst=1; shift ;;
        -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Ukjent valg: $1" >&2; exit 1 ;;
    esac
done
[[ $edid == generert || $edid == fang ]] || { echo "--edid generert|fang" >&2; exit 1; }
[[ -n $ROOT || $dry == 1 || $EUID == 0 ]] || { echo "Kjør med sudo." >&2; exit 1; }

utfor() { if [[ $dry == 1 ]]; then echo "[dry-run] $*"; else "$@"; fi; }
skriv() { # skriv <fil> <innhold fra stdin>
    if [[ $dry == 1 ]]; then echo "[dry-run] skriv $1:"; sed 's/^/    /'; else mkdir -p "$(dirname "$1")"; cat >"$1"; fi
}

if [[ -f $ROOT/boot/firmware/config.txt ]]; then BOOT=$ROOT/boot/firmware
elif [[ -f $ROOT/boot/config.txt ]]; then BOOT=$ROOT/boot
else echo "Fant ikke config.txt under $ROOT/boot/firmware eller $ROOT/boot" >&2; exit 1; fi
CFG=$BOOT/config.txt; CMD=$BOOT/cmdline.txt
FW=$ROOT/lib/firmware/edid
stempel=$(date +%Y%m%d-%H%M%S)

sikkerhetskopi() { if [[ -f $1 ]]; then utfor cp -a "$1" "$1.pi5-hdmi-lyd.bak-$stempel"; fi; }

fjern_blokk() { # fjerner vår blokk fra config.txt (stdout)
    awk -v s="$MERKE_START" -v e="$MERKE_SLUTT" '$0==s{skip=1;next} $0==e{skip=0;next} !skip' "$CFG"
}

rens_cmdline() { # fjerner våre/konfliktende tokens (stdout, én linje)
    tr -s ' \n' '\n' <"$CMD" | grep -vE '^(video=HDMI-A-[12]:|drm\.edid_firmware=)' | grep -v '^$' | paste -sd' '
}

if [[ $avinst == 1 ]]; then
    sikkerhetskopi "$CFG"; sikkerhetskopi "$CMD"
    fjern_blokk | skriv "$CFG"
    rens_cmdline | skriv "$CMD"
    for f in "$FW"/pi5-hdmi-lyd-hdmi0.bin "$FW"/pi5-hdmi-lyd-hdmi1.bin \
             "$ROOT"/etc/initramfs-tools/hooks/pi5-hdmi-lyd-edid \
             "$ROOT"/etc/pipewire/pipewire.conf.d/50-pi5-hdmi-lyd.conf \
             "$ROOT"/etc/wireplumber/wireplumber.conf.d/51-pi5-hdmi-lyd.conf \
             "$ROOT"/etc/wireplumber/main.lua.d/51-pi5-hdmi-lyd.lua \
             "$ROOT"/etc/alsa/conf.d/60-pi5-hdmi-lyd.conf \
             "$ROOT"/usr/local/bin/lyd-utgang "$ROOT"/usr/local/bin/lyd-latenstest "$ROOT"/usr/local/bin/lyd-fang-edid; do
        [[ -e $f ]] && utfor rm -f "$f"
    done
    [[ -f $ROOT/etc/asound.conf ]] && grep -q 'lyd_hdmi' "$ROOT/etc/asound.conf" && \
        echo "NB: /etc/asound.conf peker fortsatt på lyd_hdmi* – fjern pcm.!default-linjen manuelt."
    [[ -z $ROOT && $dry == 0 ]] && command -v update-initramfs >/dev/null && update-initramfs -u || true
    echo "Avinstallert. Start Pi-en på nytt."; exit 0
fi

# ---------- 1) EDID ----------
utfor mkdir -p "$FW"
porter=(hdmi0); [[ $kun0 == 0 ]] && porter+=(hdmi1)
for port in "${porter[@]}"; do
    maal_fil="$FW/pi5-hdmi-lyd-$port.bin"
    if [[ $edid == fang && -z $ROOT ]] && \
       { [[ $dry == 1 ]] && echo "[dry-run] fang EDID for $port" || MAAL="$maal_fil" "$HER/bin/lyd-fang-edid" "$port"; }; then
        echo "$port: bruker mottakerens ekte EDID"
    else
        [[ $edid == fang ]] && echo "$port: ingen lyd-EDID å fange – bruker generert EDID"
        utfor python3 "$HER/edid/lag-edid.py" "$maal_fil"
    fi
done

# ---------- 2) config.txt ----------
sikkerhetskopi "$CFG"
ny_cfg=$(fjern_blokk)
if grep -qE '^[[:space:]]*dtoverlay=vc4-fkms-v3d' <<<"$ny_cfg"; then
    echo "ADVARSEL: config.txt bruker vc4-fkms-v3d (utgått). Bytt til vc4-kms-v3d." >&2
fi
ny_cfg=$(sed -E 's/^([[:space:]]*dtoverlay=vc4-kms-v3d.*),noaudio/\1/' <<<"$ny_cfg")
blokk=$(cat "$HER/boot/config.txt.blokk")
# Finnes vc4-kms-v3d allerede? Da ikke last overlayet en gang til.
grep -qE '^[[:space:]]*dtoverlay=vc4-kms-v3d' <<<"$ny_cfg" && blokk=$(grep -v '^dtoverlay=vc4-kms-v3d$' <<<"$blokk")
[[ $kun0 == 1 ]] && blokk=$(grep -vE '^hdmi_(force_hotplug|drive):1=' <<<"$blokk")
# [all] først, så blokken ikke havner under en [cm4]/[cm5]-seksjon
blokk=$(sed "s/^$MERKE_START\$/$MERKE_START\n[all]/" <<<"$blokk")
printf '%s\n%s\n' "$ny_cfg" "$blokk" | skriv "$CFG"

# ---------- 3) cmdline.txt (én linje!) ----------
sikkerhetskopi "$CMD"
tillegg="video=HDMI-A-1:1280x720M@60D"
edidarg="drm.edid_firmware=HDMI-A-1:edid/pi5-hdmi-lyd-hdmi0.bin"
if [[ $kun0 == 0 ]]; then
    tillegg+=" video=HDMI-A-2:1280x720M@60D"
    edidarg+=",HDMI-A-2:edid/pi5-hdmi-lyd-hdmi1.bin"
fi
echo "$(rens_cmdline) $tillegg $edidarg" | skriv "$CMD"

# ---------- 4) initramfs ----------
if [[ -d $ROOT/etc/initramfs-tools ]]; then
    utfor install -D -m 0755 "$HER/initramfs/pi5-hdmi-lyd-edid" "$ROOT/etc/initramfs-tools/hooks/pi5-hdmi-lyd-edid"
    [[ -z $ROOT ]] && command -v update-initramfs >/dev/null && utfor update-initramfs -u
fi

# ---------- 5) PipeWire / WirePlumber ----------
if [[ $utenpw == 0 ]]; then
    utfor install -D -m 0644 "$HER/pipewire/50-pi5-hdmi-lyd.conf" "$ROOT/etc/pipewire/pipewire.conf.d/50-pi5-hdmi-lyd.conf"
    wpver=$( { [[ -z $ROOT ]] && wireplumber --version 2>/dev/null; } | grep -oE '[0-9]+\.[0-9]+' | head -n1 || true)
    if [[ $wpver == 0.4 ]]; then
        utfor install -D -m 0644 "$HER/wireplumber/51-pi5-hdmi-lyd.lua" "$ROOT/etc/wireplumber/main.lua.d/51-pi5-hdmi-lyd.lua"
    else
        utfor install -D -m 0644 "$HER/wireplumber/51-pi5-hdmi-lyd.conf" "$ROOT/etc/wireplumber/wireplumber.conf.d/51-pi5-hdmi-lyd.conf"
    fi
fi

# ---------- 6) ALSA ----------
utfor install -D -m 0644 "$HER/alsa/60-pi5-hdmi-lyd.conf" "$ROOT/etc/alsa/conf.d/60-pi5-hdmi-lyd.conf"
if [[ $utenpw == 1 ]]; then
    sikkerhetskopi "$ROOT/etc/asound.conf"
    { [[ -f $ROOT/etc/asound.conf ]] && grep -vE '^(pcm|ctl)\.!default' "$ROOT/etc/asound.conf"; cat "$HER/alsa/asound-uten-pipewire.conf"; } \
        | skriv "$ROOT/etc/asound.conf"
fi

# ---------- 7) Verktøy ----------
for v in lyd-utgang lyd-latenstest lyd-fang-edid; do
    utfor install -D -m 0755 "$HER/bin/$v" "$ROOT/usr/local/bin/$v"
done

cat <<TXT

Ferdig. Neste steg:
  1. sudo reboot
  2. lyd-utgang status            – HDMI0/HDMI1 skal vise eld_valid 1 og monitor_present 1
  3. speaker-test -D lyd_hdmi0 -c2 -t sine -l1   (eller spill av noe vanlig)
  4. lyd-latenstest --last        – finn minste stabile buffer på akkurat ditt oppsett
TXT
