#!/usr/bin/env python3
"""Lager fabrikkbanken (128 patcher, A11–B88) i Juno-106 sysex-format.

Kilde: KR106_Presets_JUCE.h fra Ultramaster KR-106 (GPL-3), der J106-banken er
dekodet fra offentlig tilgjengelige fabrikk-sysex-data. Verdiene der står i
KR-106 sin EParams-rekkefølge som rå 7-bit byte; her pakkes de tilbake til
originalformatet (APR, F0 41 30 0n pp [16 slidere] [SW1] [SW2] F7).

Utdata:
  patches/factory_106.syx   – 128 sysex-meldinger, 24 byte hver
  src/factory_bank.h        – samme data kompilert inn i programmet
"""
import re, sys, pathlib

src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                   "../kr106-upstream/Source/KR106_Presets_JUCE.h").read_text()
root = pathlib.Path(__file__).resolve().parent.parent
j106 = src[src.index("=== J106 Bank"):]
ent = re.findall(r'\{"([^"]+)",\s*\{([^}]*)\}\}', j106)[:128]
assert len(ent) == 128, len(ent)

# KR-106 EParams-indekser
(kLfoRate, kLfoDelay, kDcoLfo, kDcoPwm, kDcoSub, kDcoNoise, kHpf, kVcfFreq, kVcfRes,
 kVcfEnv, kVcfLfo, kVcfKbd, kVcaLevel, kA, kD, kS, kR) = (3, 4, 5, 6, 7, 8, 9, 10, 11,
                                                         12, 13, 14, 15, 16, 17, 18, 19)
kPulse, kSaw, kSubSw, kChOff, kChI, kChII, kOct = 23, 24, 25, 26, 27, 28, 29
kPwmMode, kEnvInv, kVcaMode = 33, 34, 35

syx = bytearray(); rows = []
for n, (name, vals) in enumerate(ent):
    v = [int(x) for x in vals.split(",")]
    sliders = [v[kLfoRate], v[kLfoDelay], v[kDcoLfo], v[kDcoPwm], v[kDcoNoise], v[kVcfFreq],
               v[kVcfRes], v[kVcfEnv], v[kVcfLfo], v[kVcfKbd], v[kVcaLevel], v[kA], v[kD],
               v[kS], v[kR], v[kDcoSub]]
    assert all(0 <= s <= 127 for s in sliders), (name, sliders)
    sw1 = {0: 0x01, 1: 0x02, 2: 0x04}[v[kOct]]
    if v[kPulse]: sw1 |= 0x08
    if v[kSaw]: sw1 |= 0x10
    chorus_on = not v[kChOff] and (v[kChI] or v[kChII])
    if not chorus_on: sw1 |= 0x20
    if v[kChI]: sw1 |= 0x40
    sw2 = 0x01 if v[kPwmMode] else 0
    if v[kEnvInv]: sw2 |= 0x02
    if v[kVcaMode]: sw2 |= 0x04
    sw2 |= (3 - v[kHpf]) << 3
    msg = bytes([0xF0, 0x41, 0x30, 0x00, n] + sliders + [sw1, sw2, 0xF7])
    syx += msg
    rows.append((name, msg[5:23]))

(root / "patches").mkdir(exist_ok=True)
(root / "patches/factory_106.syx").write_bytes(syx)
with open(root / "src/factory_bank.h", "w") as f:
    f.write("// Generert av tools/gen_factory_bank.py – ikke rediger for hånd.\n")
    f.write("// Fabrikkbank A11–B88 i Juno-106-format: 16 slidere + SW1 + SW2.\n#pragma once\n#include <cstdint>\n\n")
    f.write("struct FactoryPatch { const char* name; uint8_t data[18]; };\n\n")
    f.write("static const FactoryPatch kFactoryBank[128] = {\n")
    for name, d in rows:
        f.write('  {"%s", {%s}},\n' % (name.replace('"', '\\"'), ", ".join(str(b) for b in d)))
    f.write("};\n")
print("128 patcher skrevet:", len(syx), "byte sysex")
for name, _ in rows[:3] + rows[64:67]:
    print(" ", name)
