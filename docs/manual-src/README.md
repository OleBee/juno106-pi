# JU-6 Pi Owner's Manual – source

English owner's manual (`../JU-6_Pi_Owners_Manual.pdf`) for JU-6 Pi v1.1.1, generated from these scripts.
All mappings are read from the code in this repository (`src/controller.h`, `src/synth.h`, `src/main.cpp`,
`src/audio_out.h`, `src/bank.h`, `src/factory_bank.h`, `image/data/ju6.conf`) and `README.md`.
Diagrams are original SVG drawings (MPK mini Plus layout after AKAI's MPK mini Plus User Guide v1.2).

Build (needs Python 3 and Google Chrome/Chromium; fonts: Nimbus Sans, Nimbus Mono PS):

```sh
cd docs/manual-src
python3 decode.py          # tutorial knob values from src/factory_bank.h -> tutorials.json
python3 build.py           # -> manual.html
google-chrome --headless=new --no-pdf-header-footer --print-to-pdf=../JU-6_Pi_Owners_Manual.pdf manual.html
```
