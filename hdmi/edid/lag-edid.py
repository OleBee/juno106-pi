#!/usr/bin/env python3
"""Lager en minimal, gyldig EDID (EDID 1.4 + CTA-861-utvidelse) som sier:
"jeg er en HDMI-mottaker (ikke DVI) og tar imot 2-kanals LPCM 32-192 kHz".

Brukes med drm.edid_firmware= i cmdline.txt slik at vc4-driveren på Pi 5
gir HDMI-lyd selv om ingen skjerm er tilkoblet, eller når lydplanken/
receiveren står i standby og ikke svarer på EDID. Dette er KMS-ekvivalenten
til de gamle hdmi_force_hotplug=1 + hdmi_drive=2.

Bruk:  python3 lag-edid.py [utfil]   (standard: pi5-hdmi-lyd.bin)
"""
import sys


def sjekksum(blokk: bytearray) -> None:
    blokk[127] = (-sum(blokk[:127])) & 0xFF


def produsent_id(tre_bokstaver: str) -> bytes:
    a, b, c = (ord(ch) - 64 for ch in tre_bokstaver)
    return ((a << 10) | (b << 5) | c).to_bytes(2, "big")


def tekst_descriptor(tag: int, tekst: str) -> bytes:
    data = (tekst[:13] + "\n").encode("ascii")[:13].ljust(13, b" ")
    return bytes([0, 0, 0, tag, 0]) + data


def basisblokk() -> bytearray:
    b = bytearray(128)
    b[0:8] = bytes([0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00])
    b[8:10] = produsent_id("LYD")
    b[10:12] = (0x0001).to_bytes(2, "little")       # produktkode
    b[12:16] = (0).to_bytes(4, "little")            # serienummer
    b[16] = 40                                      # uke
    b[17] = 2026 - 1990                             # år
    b[18], b[19] = 1, 3                             # EDID 1.3 (HDMI-spesifikasjonen krever 1.3)
    b[20] = 0x80   # digital inngang
    b[21], b[22] = 80, 45                           # 80 x 45 cm (16:9)
    b[23] = 0x78                                    # gamma 2.2
    b[24] = 0x0E   # RGB, sRGB-standard, foretrukket timing i DTD 1, kontinuerlig frekvens
    b[25:35] = bytes([0xEE, 0x91, 0xA3, 0x54, 0x4C, 0x99, 0x26, 0x0F, 0x50, 0x54])  # sRGB
    b[35:38] = bytes([0x20, 0x00, 0x00])            # etablert: 640x480@60
    std = [(0x81, 0xC0), (0xD1, 0xC0)] + [(0x01, 0x01)] * 6  # 1280x720@60, 1920x1080@60
    for i, (x, y) in enumerate(std):
        b[38 + 2 * i], b[39 + 2 * i] = x, y
    # DTD 1 (foretrukket): 1280x720@60, 74,25 MHz (CEA VIC 4)
    b[54:72] = bytes([0x01, 0x1D, 0x00, 0x72, 0x51, 0xD0, 0x1E, 0x20, 0x6E, 0x28,
                      0x55, 0x00, 0x20, 0xC2, 0x31, 0x00, 0x00, 0x1E])
    # DTD 2: 1920x1080@60, 148,5 MHz (CEA VIC 16)
    b[72:90] = bytes([0x02, 0x3A, 0x80, 0x18, 0x71, 0x38, 0x2D, 0x40, 0x58, 0x2C,
                      0x45, 0x00, 0x20, 0xC2, 0x31, 0x00, 0x00, 0x1E])
    b[90:108] = tekst_descriptor(0xFC, "Pi5 HDMI-lyd")   # monitornavn
    # Områdegrenser: 23-61 Hz V, 15-70 kHz H, maks 150 MHz pikselklokke
    b[108:126] = bytes([0, 0, 0, 0xFD, 0, 23, 61, 15, 70, 15, 0x00, 0x0A,
                        0x20, 0x20, 0x20, 0x20, 0x20, 0x20])
    b[126] = 1                                       # én utvidelsesblokk
    sjekksum(b)
    return b


def cta_blokk() -> bytearray:
    vdb = bytes([0x40 | 3, 0x04, 0x10, 0x01])        # VIC 4, 16, 1
    # Audio Data Block: LPCM, 2 kanaler, 32/44,1/48/88,2/96/176,4/192 kHz, 16/20/24 bit
    adb = bytes([0x20 | 3, (1 << 3) | (2 - 1), 0x7F, 0x07])
    sadb = bytes([0x80 | 3, 0x01, 0x00, 0x00])       # høyttalere: FL/FR
    # HDMI Vendor-Specific Data Block (OUI 00-0C-03) => "HDMI, ikke DVI"
    vsdb = bytes([0x60 | 7, 0x03, 0x0C, 0x00, 0x10, 0x00, 0x00, 0x1E])
    vcdb = bytes([0xE0 | 2, 0x00, 0x4A])             # Video Capability: RGB-kvantisering valgbar, underscan
    data = vdb + adb + sadb + vsdb + vcdb
    c = bytearray(128)
    c[0], c[1] = 0x02, 0x03
    c[2] = 4 + len(data)                              # DTD-offset (ingen DTD her)
    c[3] = 0xC1   # underscan, basic audio, 1 native DTD
    c[4:4 + len(data)] = data
    sjekksum(c)
    return c


def main() -> None:
    ut = sys.argv[1] if len(sys.argv) > 1 else "pi5-hdmi-lyd.bin"
    with open(ut, "wb") as f:
        f.write(basisblokk() + cta_blokk())
    print(f"Skrev {ut} (256 byte)")


if __name__ == "__main__":
    main()
