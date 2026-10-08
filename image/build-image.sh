#!/bin/bash
# JU-6 Pi – bygger et ferdig SD-kort-image fra det offisielle Raspberry Pi OS Lite (arm64).
# Bruk (som root, på en x86-64- eller arm64-Linux med qemu-user-static + binfmt):
#   sudo image/build-image.sh <raspios-lite-arm64.img[.xz]> <ju6pi-arm64-binær> <ut.img>
# Krever: sfdisk, e2fsprogs (e2fsck, resize2fs), dosfstools, mtools, zerofree, losetup, qemu-aarch64-static.
set -euo pipefail
export MTOOLS_SKIP_CHECK=1
export PATH=$PATH:/usr/sbin:/sbin
BASE=$1; BIN=$2; OUT=$3
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/.." && pwd)
ROOT_GROW_MIB=${ROOT_GROW_MIB:-512}
DATA_MIB=${DATA_MIB:-256}
MNT=$(mktemp -d /tmp/ju6root.XXXX)
LOOP=""
say() { echo "== $*"; }
cleanup() {
  set +e
  for d in dev/pts dev sys proc; do mountpoint -q "$MNT/$d" && umount "$MNT/$d"; done
  mountpoint -q "$MNT" && umount "$MNT"
  [ -n "$LOOP" ] && losetup -d "$LOOP"
  rmdir "$MNT" 2>/dev/null
}
trap cleanup EXIT

say "pakker ut grunnimage"
case "$BASE" in *.xz) xz -dc "$BASE" > "$OUT" ;; *) cp --sparse=always "$BASE" "$OUT" ;; esac

# ---------- partisjoner: 1 = boot (FAT), 2 = rot (ext4, utvidet), 3 = JU6DATA (FAT) ----------
read -r P1S P1N < <(sfdisk -d "$OUT" | awk -F'[=,]' '/img1 :/{gsub(/ /,"");print $2, $4}')
read -r P2S P2N < <(sfdisk -d "$OUT" | awk -F'[=,]' '/img2 :/{gsub(/ /,"");print $2, $4}')
LABELID=$(sfdisk -d "$OUT" | awk '/label-id/{print $2}')
P2N_NEW=$(( P2N + ROOT_GROW_MIB * 2048 ))
P3S=$(( (P2S + P2N_NEW + 2047) / 2048 * 2048 ))
P3N=$(( DATA_MIB * 2048 ))
TOTAL=$(( P3S + P3N ))
truncate -s $(( TOTAL * 512 )) "$OUT"
say "partisjonstabell: rot $((P2N_NEW/2048)) MiB, data ${DATA_MIB} MiB (label-id $LABELID beholdes)"
sfdisk --no-reread --no-tell-kernel "$OUT" <<EOF
label: dos
label-id: $LABELID
unit: sectors
start=$P1S, size=$P1N, type=c
start=$P2S, size=$P2N_NEW, type=83
start=$P3S, size=$P3N, type=c
EOF

LOOP=$(losetup -f --show -o $(( P2S * 512 )) --sizelimit $(( P2N_NEW * 512 )) "$OUT")
e2fsck -fy "$LOOP" >/dev/null || true
resize2fs "$LOOP" >/dev/null
mount "$LOOP" "$MNT"
BOOTIMG="$OUT@@$(( P1S * 512 ))"

say "henter boot-partisjonen inn i /boot/firmware (for update-initramfs)"
mkdir -p "$MNT/boot/firmware"
mcopy -s -n -i "$BOOTIMG" "::/*" "$MNT/boot/firmware/"

# ---------- filer ----------
say "installerer JU-6 Pi"
install -D -m 0755 "$BIN" "$MNT/opt/ju6pi/bin/ju6pi"
# root:root, og eksisterende kataloger (/, /etc, /usr …) beholder eier og rettigheter
tar -C "$HERE/rootfs" --owner=0 --group=0 -cf - . | tar -C "$MNT" --no-overwrite-dir -xf -
install -D -m 0644 "$REPO/hdmi/alsa/60-pi5-hdmi-lyd.conf" "$MNT/etc/alsa/conf.d/60-pi5-hdmi-lyd.conf"
install -D -m 0644 "$REPO/hdmi/edid/pi5-hdmi-lyd.bin" "$MNT/lib/firmware/edid/pi5-hdmi-lyd-hdmi0.bin"
install -D -m 0644 "$REPO/hdmi/edid/pi5-hdmi-lyd.bin" "$MNT/lib/firmware/edid/pi5-hdmi-lyd-hdmi1.bin"
install -D -m 0755 "$REPO/hdmi/initramfs/pi5-hdmi-lyd-edid" "$MNT/etc/initramfs-tools/hooks/pi5-hdmi-lyd-edid"
for b in lyd-utgang lyd-latenstest; do install -D -m 0755 "$REPO/hdmi/bin/$b" "$MNT/usr/local/bin/$b"; done
install -D -m 0644 "$REPO/patches/factory_106.syx" "$MNT/opt/ju6pi/share/factory_106.syx"
install -D -m 0644 "$REPO/LICENSE" "$MNT/opt/ju6pi/share/LICENSE"
install -D -m 0644 "$REPO/third_party/kr106/LICENSE" "$MNT/opt/ju6pi/share/KR106-LICENSE"
mkdir -p "$MNT/data"
mkdir -p "$MNT/etc/rpi/swap.conf.d"
printf '[Main]\nMechanism=none\n' > "$MNT/etc/rpi/swap.conf.d/90-ju6pi.conf"
# journald: bare i RAM (rot er uansett skrivebeskyttet)
mkdir -p "$MNT/etc/systemd/journald.conf.d"
printf '[Journal]\nStorage=volatile\nRuntimeMaxUse=16M\n' > "$MNT/etc/systemd/journald.conf.d/90-ju6pi.conf"

# ---------- chroot: pakker, bruker, tjenester, initramfs ----------
for d in proc sys dev dev/pts; do mount --bind "/$d" "$MNT/$d"; done
cp "$MNT/etc/resolv.conf" "$MNT/etc/resolv.conf.ju6bak"
cp /etc/resolv.conf "$MNT/etc/resolv.conf"
cat > "$MNT/tmp/ju6-chroot.sh" <<'EOC'
#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8
echo "-- overlayroot"
if ls /tmp/debs/*.deb >/dev/null 2>&1; then
  # Ferdig nedlastede pakker (apt over nett i qemu-chroot henger av og til)
  dpkg -i /tmp/debs/*.deb >/dev/null
else
  APTOPT="-o Acquire::Retries=5 -o Acquire::http::Timeout=30"
  for i in 1 2 3; do apt-get $APTOPT update -qq && break || sleep 5; done
  apt-get $APTOPT install -y -qq --no-install-recommends overlayroot >/dev/null
fi
dpkg -s overlayroot >/dev/null
dpkg -s alsa-utils >/dev/null 2>&1 || echo "merk: alsa-utils mangler (bare for feilsøking)"
rm -rf /tmp/debs
echo "-- bruker ju6"
id ju6 >/dev/null 2>&1 || useradd --system --user-group --no-create-home --home-dir /data/ju6 --shell /usr/sbin/nologin ju6
usermod -aG audio ju6
echo "-- tjenester"
systemctl enable ju6pi.service
OFF="ssh.service ssh.socket sshswitch.service regenerate_ssh_host_keys.service userconfig.service
 NetworkManager.service NetworkManager-wait-online.service wpa_supplicant.service ModemManager.service
 bluetooth.service hciuart.service avahi-daemon.service avahi-daemon.socket cron.service
 apt-daily.timer apt-daily-upgrade.timer dpkg-db-backup.timer e2scrub_all.timer e2scrub_reap.service fstrim.timer
 logrotate.timer man-db.timer rpi-eeprom-update.service udisks2.service triggerhappy.service triggerhappy.socket
 cloud-init-local.service cloud-init-main.service cloud-init-network.service cloud-config.service cloud-final.service
 cloud-init-hotplugd.socket rpi-resize.service rpi-resize-swap-file.service rpi-zram-writeback.service
 systemd-growfs-root.service keyboard-setup.service apparmor.service systemd-timesyncd.service
 console-setup.service remote-fs.target"
for u in $OFF; do systemctl disable "$u" >/dev/null 2>&1 || true; done
for u in cloud-init-local.service cloud-init-main.service cloud-init-network.service cloud-config.service cloud-final.service \
         userconfig.service sshswitch.service ssh.service ssh.socket NetworkManager-wait-online.service \
         rpi-resize.service systemd-growfs-root.service apt-daily.service apt-daily-upgrade.service \
         man-db.service e2scrub_all.service fstrim.service \
         systemd-zram-setup@zram0.service rpi-resize-swap-file.service; do
  systemctl mask "$u" >/dev/null 2>&1 || true
done
mkdir -p /etc/cloud && touch /etc/cloud/cloud-init.disabled
# Fast maskin-ID: hindrer at systemd tror hver oppstart er «første oppstart» (rot er skrivebeskyttet)
rm -f /etc/machine-id /var/lib/dbus/machine-id
systemd-machine-id-setup >/dev/null
systemctl set-default multi-user.target >/dev/null
ln -sf /usr/share/zoneinfo/Europe/Oslo /etc/localtime && echo Europe/Oslo > /etc/timezone
echo "-- overlayroot (skrivebeskyttet rot, endringer i RAM)"
if [ -f /etc/overlayroot.conf ]; then
  sed -i 's/^overlayroot=.*/overlayroot=""/' /etc/overlayroot.conf   # styres fra cmdline.txt
fi
echo "-- initramfs"
for k in /lib/modules/*; do update-initramfs -c -k "$(basename "$k")" >/dev/null 2>&1 || update-initramfs -u -k "$(basename "$k")"; done
apt-get clean
rm -rf /var/lib/apt/lists/* /var/cache/debconf/*-old /var/log/*.log /tmp/ju6-chroot.sh
EOC
chmod +x "$MNT/tmp/ju6-chroot.sh"
# Valgfritt: DEBS=katalog med overlayroot + cryptsetup(-bin) arm64-.deb for bygging uten nett i chrooten
if [ -n "${DEBS:-}" ] && ls "$DEBS"/*.deb >/dev/null 2>&1; then mkdir -p "$MNT/tmp/debs"; cp "$DEBS"/*.deb "$MNT/tmp/debs/"; fi
chroot "$MNT" /tmp/ju6-chroot.sh
mv "$MNT/etc/resolv.conf.ju6bak" "$MNT/etc/resolv.conf"

JU6UID=$(chroot "$MNT" id -u ju6); JU6GID=$(chroot "$MNT" id -g ju6)
say "fstab (ju6 = $JU6UID:$JU6GID)"
cat > "$MNT/etc/fstab" <<EOF
proc                  /proc           proc  defaults                0  0
PARTUUID=${LABELID#0x}-01  /boot/firmware  vfat  ro,defaults,nofail       0  2
PARTUUID=${LABELID#0x}-02  /               ext4  defaults,noatime         0  1
# JU6DATA: lagrede patcher og innstillinger. FAT, så den kan leses/skrives fra en PC.
# flush = skriv straks (tåler strømbrudd bedre); nofail = start uansett.
PARTUUID=${LABELID#0x}-03  /data           vfat  defaults,nofail,noatime,flush,uid=$JU6UID,gid=$JU6GID,umask=0022,x-systemd.device-timeout=10s  0  2
EOF

# ---------- boot: config.txt og cmdline.txt ----------
say "config.txt og cmdline.txt"
BF="$MNT/boot/firmware"
python3 - "$BF/config.txt" "$REPO/hdmi/boot/config.txt.blokk" <<'EOP'
import sys,re
p,blk=sys.argv[1],open(sys.argv[2]).read()
s=open(p).read()
s=re.sub(r'(?m)^dtparam=audio=on', '#dtparam=audio=on  # (Pi 5 har ingen analog lydutgang)', s)
s=re.sub(r'(?m)^camera_auto_detect=1', 'camera_auto_detect=0', s)
s=re.sub(r'(?m)^display_auto_detect=1', 'display_auto_detect=0', s)
s=s.rstrip()+"\n\n[all]\n"+blk.strip()+"\n\n# >>> ju6pi >>>\n# JU-6 Pi: ingen radio (Wi-Fi/Bluetooth av), stille oppstart\ndtoverlay=disable-wifi\ndtoverlay=disable-bt\ndisable_splash=1\n# <<< ju6pi <<<\n"
open(p,'w').write(s)
EOP
HDMI_ARGS=$(tr -d '\n' < "$REPO/hdmi/boot/cmdline-tillegg.txt")
echo "console=tty1 root=PARTUUID=${LABELID#0x}-02 rootfstype=ext4 fsck.repair=yes rootwait quiet loglevel=3 overlayroot=tmpfs:recurse=0 cpufreq.default_governor=performance isolcpus=3 usbcore.autosuspend=-1 consoleblank=0 $HDMI_ARGS" > "$BF/cmdline.txt"
cat "$BF/cmdline.txt"

say "skriver boot-partisjonen tilbake"
( cd "$BF" && mcopy -o -s -i "$BOOTIMG" ./* ::/ )
# rydd bort cloud-init-filer som ikke brukes
for f in user-data meta-data network-config; do mdel -i "$BOOTIMG" "::/$f" 2>/dev/null || true; done
rm -rf "$BF"/* 

for d in dev/pts dev sys proc; do umount "$MNT/$d"; done
umount "$MNT"
e2fsck -fy "$LOOP" >/dev/null || true
zerofree "$LOOP" || true
losetup -d "$LOOP"; LOOP=""

# ---------- JU6DATA ----------
say "lager JU6DATA-partisjonen"
DIMG=$(mktemp /tmp/ju6data.XXXX)
truncate -s $(( P3N * 512 )) "$DIMG"
mkfs.vfat -n JU6DATA "$DIMG" >/dev/null
mmd -i "$DIMG" ::/ju6
mcopy -i "$DIMG" "$HERE/data/LES-MEG.txt" ::/LES-MEG.txt
mcopy -i "$DIMG" "$HERE/data/ju6.conf" ::/ju6/ju6.conf
mcopy -i "$DIMG" "$REPO/patches/factory_106.syx" ::/ju6/fabrikk-A-B.syx
dd if="$DIMG" of="$OUT" bs=1M seek=$(( P3S * 512 / 1048576 )) conv=notrunc,fsync status=none
rm -f "$DIMG"
sfdisk -d "$OUT"
say "ferdig: $OUT"
