// JU-6 Pi – 6-stemmers synth inspirert av Juno-106, for Raspberry Pi 5.
// Lydmotor: Ultramaster KR-106 DSP (GPL-3). Dette programmet: GPL-3.
#include "synth.h"
#include "bank.h"
#include "controller.h"
#include "midi_in.h"
#include "audio_out.h"
#include <csignal>
#include <functional>
#include <sys/resource.h>
#include <thread>
#include <mutex>
#ifndef JU6_VERSION
#define JU6_VERSION "1.1.0"
#endif
#include <pthread.h>
#include <sched.h>
#include <sys/mman.h>
#include <sys/stat.h>

using namespace ju6;

static std::atomic<bool> gRun{true};
static void onSignal(int) { gRun = false; }

static void enableFlushToZero() {
#if defined(__aarch64__)
  uint64_t fpcr; asm volatile("mrs %0, fpcr" : "=r"(fpcr)); fpcr |= (1ull << 24); asm volatile("msr fpcr, %0" :: "r"(fpcr));
#elif defined(__SSE__)
  unsigned csr; asm volatile("stmxcsr %0" : "=m"(csr)); csr |= 0x8040; asm volatile("ldmxcsr %0" :: "m"(csr));
#endif
}

// ------------------------------------------------------------ WAV
static bool writeWav(const std::string& path, const std::vector<float>& L, const std::vector<float>& R, int sr) {
  FILE* f = fopen(path.c_str(), "wb"); if (!f) return false;
  uint32_t n = (uint32_t)L.size(), data = n * 2 * 3;
  auto u32 = [&](uint32_t v) { fwrite(&v, 4, 1, f); }; auto u16 = [&](uint16_t v) { fwrite(&v, 2, 1, f); };
  fwrite("RIFF", 1, 4, f); u32(36 + data); fwrite("WAVEfmt ", 1, 8, f); u32(16); u16(1); u16(2);
  u32(sr); u32(sr * 6); u16(6); u16(24); fwrite("data", 1, 4, f); u32(data);
  for (uint32_t i = 0; i < n; i++) for (float x : { L[i], R[i] }) {
    int32_t v = (int32_t)std::lround(AlsaOut::softClip(x) * 8388607.f);
    uint8_t b[3] = { (uint8_t)v, (uint8_t)(v >> 8), (uint8_t)(v >> 16) }; fwrite(b, 1, 3, f);
  }
  fclose(f); return true;
}

// ------------------------------------------------------------ offline-rendering
struct Ev { double t; std::function<void(Synth&)> f; };
static void render(Synth& s, std::vector<Ev> evs, double seconds, float gain, std::vector<float>& L, std::vector<float>& R) {
  const int sr = 48000, blk = 64;
  std::sort(evs.begin(), evs.end(), [](const Ev& a, const Ev& b) { return a.t < b.t; });
  size_t ei = 0; int total = (int)(seconds * sr);
  L.assign(total, 0.f); R.assign(total, 0.f);
  for (int pos = 0; pos < total; pos += blk) {
    double t = (double)pos / sr;
    while (ei < evs.size() && evs[ei].t <= t) evs[ei++].f(s);
    int n = std::min(blk, total - pos);
    s.process(&L[pos], &R[pos], n);
  }
  for (int i = 0; i < total; i++) { L[i] *= gain; R[i] *= gain; }
}

static const float kOutGain = 0.32f;   // ca. -10 dB: gir god headroom med 6 stemmer (målt topp ≈ 2,6 før gain)

static void chord(std::vector<Ev>& e, double t, double len, std::initializer_list<int> notes) {
  for (int n : notes) { e.push_back({t, [n](Synth& s) { s.noteOn(n, 100); }}); e.push_back({t + len, [n](Synth& s) { s.noteOff(n); }}); }
}

static void loadSlot(Synth& s, Bank& b, int slot) { s.loadPatch(b.patch[slot]); s.set(kMasterVol, 0.5f); }
static int findSlot(Bank& b, const char* name) {
  for (int i = 0; i < 128; i++) if (b.name[i].find(name) != std::string::npos) return i;
  return 0;
}

static int demo(const std::string& dir, int os) {
  Bank bank; bank.loadFactory();
  std::vector<float> L, R;
  auto fresh = [&](Synth& s) { s.init(48000, 1024, os); };
  auto out = [&](const char* name) {
    std::string p = dir + "/" + name; writeWav(p, L, R, 48000);
    double pk = 0; for (size_t i = 0; i < L.size(); i++) pk = std::max(pk, (double)std::max(std::fabs(L[i]), std::fabs(R[i])));
    printf("  %-28s %5.1f s  topp %.2f dBFS\n", name, L.size() / 48000.0, 20 * std::log10(pk + 1e-9));
  };
  { // Strings – B11 Strings, Am–F–C–G
    Synth s; fresh(s); loadSlot(s, bank, findSlot(bank, "B11 Strings"));
    std::vector<Ev> e; double t = 0.2;
    for (auto c : { std::initializer_list<int>{57, 60, 64, 69}, {53, 57, 60, 65}, {48, 55, 60, 64}, {55, 59, 62, 67} }) { chord(e, t, 2.2, c); t += 2.4; }
    render(s, e, t + 3.0, kOutGain, L, R); out("strings_B11.wav");
  }
  { // Strings 2 – A15 Moving Strings
    Synth s; fresh(s); loadSlot(s, bank, findSlot(bank, "A15 Moving"));
    std::vector<Ev> e; chord(e, 0.2, 4.0, {48, 55, 60, 64, 67}); chord(e, 4.6, 4.0, {50, 57, 62, 65, 69});
    render(s, e, 11.5, kOutGain, L, R); out("strings_A15_moving.wav");
  }
  { // Bass – A48 Synth Bass I, 16-dels-figur 112 bpm
    Synth s; fresh(s); loadSlot(s, bank, findSlot(bank, "A48 Synth Bass I"));
    std::vector<Ev> e; const int pat[16] = {36, 36, 48, 36, 39, 36, 43, 36, 34, 34, 46, 34, 41, 34, 43, 46};
    double step = 60.0 / 112 / 4;
    for (int bar = 0; bar < 4; bar++) for (int i = 0; i < 16; i++) {
      int n = pat[i]; double t = 0.1 + (bar * 16 + i) * step;
      e.push_back({t, [n](Synth& s) { s.noteOn(n, 100); }}); e.push_back({t + step * 0.6, [n](Synth& s) { s.noteOff(n); }});
    }
    render(s, e, 0.1 + 64 * step + 1.0, kOutGain, L, R); out("bass_A48.wav");
  }
  { // Bass 2 – A55 Synth Bass II
    Synth s; fresh(s); loadSlot(s, bank, findSlot(bank, "A55 Synth Bass II"));
    std::vector<Ev> e; const int pat[8] = {28, 40, 28, 40, 31, 43, 33, 45}; double step = 60.0 / 100 / 2;
    for (int r = 0; r < 4; r++) for (int i = 0; i < 8; i++) {
      int n = pat[i]; double t = 0.1 + (r * 8 + i) * step;
      e.push_back({t, [n](Synth& s) { s.noteOn(n, 100); }}); e.push_back({t + step * 0.8, [n](Synth& s) { s.noteOff(n); }});
    }
    render(s, e, 0.1 + 32 * step + 1.0, kOutGain, L, R); out("bass_A55.wav");
  }
  { // Brass – A11 Brass: stikk + svell
    Synth s; fresh(s); loadSlot(s, bank, findSlot(bank, "A11 Brass"));
    std::vector<Ev> e; chord(e, 0.2, 0.35, {55, 60, 64}); chord(e, 0.8, 0.35, {57, 60, 65}); chord(e, 1.4, 0.35, {55, 59, 62});
    chord(e, 2.2, 2.5, {53, 57, 60, 65}); chord(e, 5.0, 2.5, {55, 59, 62, 67});
    render(s, e, 9.0, kOutGain, L, R); out("brass_A11.wav");
  }
  { // Resonant sweep – egen innstilling: sag, høy resonans, filteret sveipes; så selvoscillasjon
    Synth s; fresh(s); loadSlot(s, bank, findSlot(bank, "A88"));
    Patch p{}; uint8_t d[18] = {40, 0, 0, 0, 0, 10, 105, 0, 0, 64, 64, 0, 0, 127, 20, 30, 0x02 | 0x10 | 0x20, (2 << 3)};
    std::memcpy(p.d, d, 18); s.loadPatch(p); s.set(kMasterVol, 0.5f);
    std::vector<Ev> e; chord(e, 0.1, 8.0, {36, 48});
    const int N = 400;
    for (int i = 0; i <= N; i++) { double t = 0.1 + 8.0 * i / N; float x = (float)i / N; float f = x < 0.5f ? x * 2 : 2 - x * 2;
      e.push_back({t, [f](Synth& s) { s.set(kVcfFreq, 0.05f + 0.9f * f); }}); }
    // Del 2: bare filteret (DCO av), resonans helt opp => sinusaktig plystring som følger tangentene
    e.push_back({8.6, [](Synth& s) { s.set(kDcoSaw, 0.f); s.set(kDcoPulse, 0.f); s.set(kDcoSub, 0.f); s.set(kDcoSubSw, 0.f);
                                      s.set(kVcfRes, 1.f); s.set(kVcfKbd, 1.f); s.set(kVcfFreq, 0.45f); }});
    int mel[6] = {60, 64, 67, 72, 67, 64};
    for (int i = 0; i < 6; i++) { int n = mel[i]; double t = 8.8 + i * 0.5;
      e.push_back({t, [n](Synth& s) { s.noteOn(n, 100); }}); e.push_back({t + 0.45, [n](Synth& s) { s.noteOff(n); }}); }
    render(s, e, 12.5, kOutGain, L, R); out("resonant_sweep.wav");
  }
  // Chorus av / I / II / I+II – samme lyd, samme akkord
  const char* names[4] = {"chorus_off.wav", "chorus_I.wav", "chorus_II.wav", "chorus_I+II.wav"};
  std::vector<float> allL, allR;
  for (int m = 0; m < 4; m++) {
    Synth s; fresh(s); loadSlot(s, bank, findSlot(bank, "A88"));
    Patch p{}; uint8_t d[18] = {50, 0, 0, 60, 0, 70, 15, 20, 0, 64, 80, 30, 60, 100, 60, 40, 0x02 | 0x10, (2 << 3)};
    std::memcpy(p.d, d, 18); s.loadPatch(p); s.set(kMasterVol, 0.5f);
    s.set(kChorusI, (m & 1) ? 1.f : 0.f); s.set(kChorusII, (m & 2) ? 1.f : 0.f); s.set(kChorusOff, m == 0 ? 1.f : 0.f);
    std::vector<Ev> e; chord(e, 0.1, 4.0, {48, 55, 60, 64}); chord(e, 4.3, 0.25, {72}); chord(e, 4.6, 0.25, {76}); chord(e, 4.9, 1.2, {79});
    render(s, e, 7.5, kOutGain, L, R); out(names[m]);
    allL.insert(allL.end(), L.begin(), L.end()); allR.insert(allR.end(), R.begin(), R.end());
  }
  L = allL; R = allR; out("chorus_compare_off_I_II_I+II.wav");
  return 0;
}


// ------------------------------------------------------------ selvtest av MPK-mappingen (uten maskinvare)
static int selftest(const std::string& wavDir) {
  int fails = 0;
  auto check = [&](bool ok, const char* what) { printf("  [%s] %s\n", ok ? " OK " : "FEIL", what); if (!ok) fails++; };
  Bank bank; bank.loadFactory();
  Synth s; s.init(48000, 1024, 2);
  RequestQueue rq; ControllerConfig cc; Controller ctl(s, bank, rq, cc);
  ctl.selectSlot(0, false);
  auto ev = [](MidiEvent::Type ty, int ch, int d1, int d2) { MidiEvent e{}; e.type = ty; e.ch = (uint8_t)ch; e.d1 = (uint8_t)d1; e.d2 = (uint8_t)d2; return e; };
  double t = 0;
  // Pad A3 (note 38, kanal 10) -> patch A13
  ctl.handle(ev(MidiEvent::NoteOn, 9, 38, 100), t); ctl.handle(ev(MidiEvent::NoteOff, 9, 38, 0), t + 0.1);
  check(ctl.currentSlot() == 2, "pad 3 (bank A) velger patch A13");
  // Gruppe + (pad B6, note 49) -> A23
  ctl.handle(ev(MidiEvent::NoteOn, 9, 49, 100), t); ctl.handle(ev(MidiEvent::NoteOff, 9, 49, 0), t);
  check(ctl.currentSlot() == 10, "pad B6 (gruppe +) gir A23");
  // Gruppe − to ganger -> A13, så B83 (wrap)
  for (int i = 0; i < 2; i++) { ctl.handle(ev(MidiEvent::NoteOn, 9, 48, 100), t); ctl.handle(ev(MidiEvent::NoteOff, 9, 48, 0), t); }
  check(ctl.currentSlot() == 64 + 7 * 8 + 2, "gruppe − forbi A1x går rundt til B8x");
  // Program Change 0 -> A11
  ctl.handle(ev(MidiEvent::Program, 0, 0, 0), t);
  check(ctl.currentSlot() == 0, "Program Change 0 gir A11");
  // Side 1, knott 1 (CC70) = VCF FREQ
  ctl.handle(ev(MidiEvent::CC, 0, 70, 127), t);
  check(std::fabs(s.get(kVcfFreq) - 1.f) < 1e-4, "side 1 knott 1 (CC70) = VCF FREQ");
  ctl.handle(ev(MidiEvent::CC, 0, 77, 70), t);
  check(s.get(kChorusI) < 0.5f && s.get(kChorusII) > 0.5f, "side 1 knott 8 = CHORUS (70 -> II)");
  ctl.handle(ev(MidiEvent::CC, 0, 77, 0), t);
  check(s.get(kChorusI) < 0.5f && s.get(kChorusII) < 0.5f, "side 1 knott 8 = CHORUS (0 -> av)");
  // Side 2 (pad B2, note 45): knott 1 = RANGE
  ctl.handle(ev(MidiEvent::NoteOn, 9, 45, 100), t);
  check(ctl.page() == 1, "pad B2 velger side 2");
  ctl.handle(ev(MidiEvent::CC, 0, 70, 127), t);
  check((int)std::lround(s.get(kOctTranspose)) == 2, "side 2 knott 1 = RANGE (127 -> 4')");
  ctl.handle(ev(MidiEvent::CC, 0, 74, 127), t);
  check(s.get(kDcoPulse) > 0.5f && s.get(kDcoSaw) > 0.5f, "side 2 knott 5 = BØLGE (127 -> puls+sag)");
  // Side 3: HPF
  ctl.handle(ev(MidiEvent::NoteOn, 9, 46, 100), t);
  ctl.handle(ev(MidiEvent::CC, 0, 74, 0), t);
  check((int)std::lround(s.get(kHpfFreq)) == 0, "side 3 knott 5 = HPF (0 -> posisjon 0, bassløft)");
  // Side 4: transpose-knott
  ctl.handle(ev(MidiEvent::NoteOn, 9, 47, 100), t);
  ctl.handle(ev(MidiEvent::CC, 0, 73, 127), t);
  check((int)std::lround(s.get(kTransposeOffset)) == 12, "side 4 knott 4 = TRANSPOSE (127 -> +12)");
  ctl.handle(ev(MidiEvent::CC, 0, 73, 64), t);
  check((int)std::lround(s.get(kTransposeOffset)) == 0, "TRANSPOSE midtstilling = 0");
  // Hold-pad og sustain
  ctl.handle(ev(MidiEvent::NoteOn, 9, 50, 100), t);
  check(s.get(kHold) > 0.5f, "pad B7 slår Hold på");
  ctl.handle(ev(MidiEvent::NoteOn, 9, 50, 100), t);
  check(s.get(kHold) < 0.5f, "pad B7 slår Hold av igjen");
  ctl.handle(ev(MidiEvent::CC, 0, 64, 127), t);
  check(s.get(kHold) > 0.5f, "CC64 (sustain) = Hold");
  ctl.handle(ev(MidiEvent::CC, 0, 64, 0), t);
  // Transpose-pad: hold + tangent 65 = +5
  ctl.handle(ev(MidiEvent::NoteOn, 9, 51, 100), 10.0);
  ctl.handle(ev(MidiEvent::NoteOn, 0, 65, 100), 10.1); ctl.handle(ev(MidiEvent::NoteOff, 0, 65, 0), 10.2);
  ctl.handle(ev(MidiEvent::NoteOff, 9, 51, 0), 10.3);
  check((int)std::lround(s.get(kTransposeOffset)) == 5, "Transpose-pad + tangent F4 gir +5");
  ctl.handle(ev(MidiEvent::NoteOn, 9, 51, 100), 11.0); ctl.handle(ev(MidiEvent::NoteOff, 9, 51, 0), 11.1);
  check((int)std::lround(s.get(kTransposeOffset)) == 0, "kort trykk på Transpose-pad slår av");
  ctl.handle(ev(MidiEvent::NoteOn, 9, 51, 100), 12.0); ctl.handle(ev(MidiEvent::NoteOff, 9, 51, 0), 12.1);
  check((int)std::lround(s.get(kTransposeOffset)) == 5, "nytt kort trykk husker +5");
  ctl.handle(ev(MidiEvent::NoteOn, 9, 51, 100), 13.0); ctl.handle(ev(MidiEvent::NoteOff, 9, 51, 0), 13.1);
  // Lagring: hold pad A5 i 1,6 s
  { Request r; while (rq.pop(r)) {} }
  ctl.handle(ev(MidiEvent::NoteOn, 9, 40, 100), 20.0); ctl.tick(20.5);
  bool early = false; { Request r; while (rq.pop(r)) if (r.type == Request::SavePatch) early = true; }
  ctl.tick(21.6);
  bool saved = false; int savedSlot = -1; { Request r; while (rq.pop(r)) if (r.type == Request::SavePatch) { saved = true; savedSlot = r.a; } }
  ctl.handle(ev(MidiEvent::NoteOff, 9, 40, 0), 21.7);
  check(!early && saved && savedSlot == 4, "hold pad A5 >1,5 s lagrer til A15 (ikke før)");
  // Pitch bend / mod
  MidiEvent b{}; b.type = MidiEvent::Bend; b.bend = 16383; ctl.handle(b, t);
  ctl.handle(ev(MidiEvent::CC, 0, 1, 127), t);
  check(true, "pitch bend og CC1 (mod) håndtert uten feil");
  // Sysex: last en patch via APR-melding og les tilbake
  {
    Patch p = bank.patch[findSlot(bank, "A11 Brass")];
    std::vector<uint8_t> m = { 0x41, 0x30, 0x00, 0x00 }; m.insert(m.end(), p.d, p.d + 18);   // som fra MIDI-tråden: uten F0/F7
    MidiEvent sx{}; sx.type = MidiEvent::Sysex; sx.sxLen = (uint8_t)m.size(); std::memcpy(sx.sx, m.data(), m.size());
    ctl.handle(sx, t);
    Patch q = s.capturePatch();
    check(std::memcmp(p.d, q.d, 18) == 0, "sysex APR (F0 41 30 ..) inn -> identisk patch ut");
  }
  // Utvidelse: I+II og PWM ENV overlever lagring til disk
  {
    Synth y; y.init(48000, 256, 2); y.loadPatch(bank.patch[0]);
    y.set(kChorusI, 1.f); y.set(kChorusII, 1.f); y.set(kChorusOff, 0.f); y.set(kPwmMode, 2.f);
    Bank b2; b2.loadFactory(); b2.patch[9] = y.capturePatch(); b2.user[9] = true; b2.name[9] = "A22 Egen";
    std::string dir = "/tmp/ju6-selftest"; mkdir(dir.c_str(), 0755);
    bool ok = b2.save(dir);
    Bank b3; b3.loadFactory(); b3.loadSyx(dir + "/patches.syx");
    Synth z; z.init(48000, 256, 2); z.loadPatch(b3.patch[9]);
    check(ok && z.get(kChorusI) > 0.5f && z.get(kChorusII) > 0.5f && (int)std::lround(z.get(kPwmMode)) == 2 &&
          std::memcmp(b3.patch[9].d, b2.patch[9].d, 18) == 0, "lagret patch med I+II og PWM ENV leses tilbake likt");
  }
  // Tastatur uten anslag: to ulike velocity gir samme nivå
  {
    std::vector<float> L1, R1, L2, R2;
    Synth a; a.init(48000, 1024, 2); a.loadPatch(bank.patch[0]); a.set(kMasterVol, 0.5f);
    Synth c; c.init(48000, 1024, 2); c.loadPatch(bank.patch[0]); c.set(kMasterVol, 0.5f);
    render(a, { {0.0, [](Synth& s) { s.noteOn(60, 20); }} }, 0.5, 1.f, L1, R1);
    render(c, { {0.0, [](Synth& s) { s.noteOn(60, 127); }} }, 0.5, 1.f, L2, R2);
    double e1 = 0, e2 = 0; for (size_t i = 0; i < L1.size(); i++) { e1 += L1[i] * L1[i]; e2 += L2[i] * L2[i]; }
    check(e1 > 0 && std::fabs(10 * std::log10(e1 / e2)) < 0.5, "anslag ignoreres som standard (vel 20 = vel 127)");
  }
  // Simulert MPK-økt -> WAV: pads bytter lyd mens knott 1 sveiper filteret
  if (!wavDir.empty()) {
    Synth x; x.init(48000, 1024, 4); RequestQueue rq2; Controller c2(x, bank, rq2, cc); c2.selectSlot(0, false);
    x.set(kMasterVol, 0.5f);
    std::vector<Ev> e; double tt = 0.1;
    auto send = [&](double at, MidiEvent m) { e.push_back({at, [&c2, m, at](Synth&) { c2.handle(m, at); }}); };
    int pads[4] = {36, 39, 41, 43};
    for (int i = 0; i < 4; i++) {
      send(tt, ev(MidiEvent::NoteOn, 9, pads[i], 100)); send(tt + 0.05, ev(MidiEvent::NoteOff, 9, pads[i], 0));
      for (int n : {48, 55, 60, 64}) { send(tt + 0.1, ev(MidiEvent::NoteOn, 0, n, 64)); send(tt + 2.3, ev(MidiEvent::NoteOff, 0, n, 0)); }
      for (int k = 0; k <= 40; k++) send(tt + 0.1 + k * 0.05, ev(MidiEvent::CC, 0, 70, 30 + k * 2));
      tt += 3.0;
    }
    std::vector<float> L, R; render(x, e, tt + 1.0, kOutGain, L, R);
    writeWav(wavDir + "/mpk_simulert_pads_og_knott.wav", L, R, 48000);
    printf("  skrev %s/mpk_simulert_pads_og_knott.wav\n", wavDir.c_str());
  }
  // Valg av lydutgang mot falske ALSA-kortlister (ingen maskinvare)
  {
    const CardInfo h0{0, "vc4hdmi0", "vc4-hdmi-0", "vc4-hdmi"}, h1{1, "vc4hdmi1", "vc4-hdmi-1", "vc4-hdmi"};
    const CardInfo dac{2, "RPiDAC", "RPi DAC+", "RPi DAC+"}, dacFirst{0, "RPiDAC", "RPi DAC+", "RPi DAC+"};
    const CardInfo iq{2, "IQaudIODAC", "IQaudIODAC", "IQaudIODAC"}, usbc{3, "Device", "USB Audio Device", "USB-Audio"};
    const CardInfo mpk{4, "MPKminiPlus", "MPK mini Plus", "USB-Audio"};   // (MIDI-only har ingen PCM, men test navn)
    auto cfgOf = [](std::initializer_list<std::pair<const char*, const char*>> kv) { Config c; for (auto& p : kv) c.kv[p.first] = p.second; return c; };
    Config none;
    auto pa = planOutputs(none);
    check(pickKind(pa.order, {h0, h1, dac}) == "dacplus", "auto: DAC+ velges når kortet finnes");
    check(pickKind(pa.order, {dacFirst, h0, h1}) == "dacplus", "auto: DAC+ velges uansett kortnummer");
    check(pickKind(pa.order, {h0, h1}) == "hdmi0", "auto: uten DAC+ -> HDMI0");
    check(pickKind(pa.order, {h1}) == "hdmi1", "auto: uten DAC+ og HDMI0 -> HDMI1");
    check(pickKind(pa.order, {usbc}) == "usb", "auto: bare USB-lydkort -> usb");
    check(pickKind(pa.order, {}) == "", "auto: ingen kort -> vent");
    check(pickKind(pa.order, {h0, iq}) == "dacplus", "auto: eldre IQaudIO DAC+ gjenkjennes");
    check(pa.wanted.empty(), "auto: ingen varsel om reserve");
    auto pd = planOutputs(cfgOf({{"audio_output", "dacplus"}}));
    check(pd.wanted == "dacplus" && pickKind(pd.order, {h0, h1}) == "hdmi0", "dacplus uten kort: reserve HDMI0 (med varsel)");
    check(pickKind(pd.order, {h0, h1, dac}) == "dacplus", "dacplus med kort: DAC+");
    auto ph = planOutputs(cfgOf({{"audio_output", "hdmi"}}));
    check(pickKind(ph.order, {h0, h1, dac}) == "hdmi0", "hdmi: DAC+ ignoreres, HDMI0 som før");
    check(pickKind(ph.order, {h1, dac}) == "hdmi1", "hdmi: HDMI1 som reserve, aldri DAC+");
    check(pickKind(ph.order, {dac}) == "", "hdmi: bare DAC+ -> venter (faller ikke til DAC+)");
    auto pu = planOutputs(cfgOf({{"audio_output", "USB"}}));
    check(pickKind(pu.order, {h0, dac, usbc}) == "usb", "usb (store bokstaver ok): USB-lydkort");
    auto pl = planOutputs(cfgOf({{"audio_devices", "hdmi1 hdmi0"}}));
    check(pickKind(pl.order, {h0, h1, dac}) == "hdmi1", "gammel audio_devices-liste virker som i 1.0.0");
    auto pb = planOutputs(cfgOf({{"audio_devices", "hdmi1"}, {"audio_output", "auto"}}));
    check(pickKind(pb.order, {h0, h1, dac}) == "dacplus", "audio_output går foran audio_devices");
    auto px = planOutputs(cfgOf({{"audio_output", "tull"}}));
    check(!px.error.empty() && pickKind(px.order, {h0, dac}) == "dacplus", "ukjent verdi -> auto + advarsel");
    check(!isDacPlus(mpk) && !isDacPlus(h0) && isDacPlus(dac) && isDacPlus(iq), "DAC+ matches på id/navn, ikke andre kort");
    check(kindRank(pa.order, "dacplus") < kindRank(pa.order, "hdmi0"), "DAC+ rangeres over HDMI0 (bytte ved sen oppstart)");
    check(pickKind(pa.order, {h0, dac}, {"dacplus"}) == "hdmi0", "bytte prøves bare én gang per utgang");
  }
  printf("%s (%d feil)\n", fails ? "SELVTEST FEILET" : "SELVTEST OK", fails);
  return fails ? 1 : 0;
}

// ------------------------------------------------------------ ytelsestest
static double benchRT(int os, double seconds) {
  Synth s; s.init(48000, 256, os);
  Bank b; b.loadFactory(); s.loadPatch(b.patch[findSlot(b, "A15 Moving")]);
  for (int n : {48, 52, 55, 59, 62, 64}) s.noteOn(n, 100);
  float L[256], R[256]; int blocks = (int)(seconds * 48000 / 256);
  double t0 = nowSec();
  for (int i = 0; i < blocks; i++) s.process(L, R, 256);
  return seconds / (nowSec() - t0);
}

// ------------------------------------------------------------ sanntid
struct Ready {
  std::atomic<bool> audio{false}; std::atomic<int> xruns{0}; std::atomic<int> period{0}, buffer{0};
  std::atomic<bool> fallback{false};   // ønsket utgang (audio_output = dacplus) mangler, går på reserve
  std::atomic<bool> upgrade{false};    // en høyere prioritert utgang har dukket opp: åpne på nytt
  std::mutex m; std::string label, kind, mixer;   // settes bare når enheten åpnes (ikke i sanntidsløkken)
};

// Står det et DAC-kort i HAT-EEPROM-en? (fastvaren legger det i /proc/device-tree/hat)
static bool hatSaysDac() {
  std::vector<uint8_t> b; if (!readFile("/proc/device-tree/hat/product", b)) return false;
  std::string s(b.begin(), b.end()); return s.find("DAC") != std::string::npos;
}

static std::string cardList(const std::vector<CardInfo>& cards) {
  std::string s; for (auto& c : cards) s += (s.empty() ? "" : ", ") + c.id;
  return s.empty() ? "ingen" : s;
}

struct ChimeGen {   // kort klarsignal: to toner (A5, E6), ca. -20 dBFS. Reserveutgang: synkende (E6, A5).
  int pos = -1; float sr = 48000; bool down = false;
  void start(bool fallingTones = false) { pos = 0; down = fallingTones; }
  void add(float* L, float* R, int n) {
    if (pos < 0) return;
    for (int i = 0; i < n; i++, pos++) {
      float t = pos / sr; float v = 0;
      auto tone = [&](float t0, float f) { float u = t - t0; if (u < 0 || u > 0.35f) return 0.f;
        return std::sin(6.2831853f * f * u) * std::min(1.f, u / 0.004f) * std::exp(-u * 9.f); };
      v = down ? 0.1f * (tone(0.f, 1318.5f) + tone(0.14f, 880.f)) : 0.1f * (tone(0.f, 880.f) + tone(0.14f, 1318.5f));
      L[i] += v / kOutGain; R[i] += v / kOutGain;
      if (t > 0.6f) { pos = -1; return; }
    }
  }
};

static int runRealtime(const Config& cfg, const std::string& dataDir, double exitAfter) {
  {  // Lås minnet (unngå sidefeil i lydtråden). MCL_FUTURE bare når grensen er ubegrenset,
     // ellers feiler senere allokeringer (trådstabler) med EAGAIN.
    rlimit rl{}; getrlimit(RLIMIT_MEMLOCK, &rl);
    int fl = rl.rlim_cur == RLIM_INFINITY ? (MCL_CURRENT | MCL_FUTURE) : MCL_CURRENT;
    if (rl.rlim_cur == RLIM_INFINITY || rl.rlim_cur >= (rlim_t)256 << 20) { if (mlockall(fl) != 0) logf("advarsel: mlockall feilet"); }
    else logf("merk: RLIMIT_MEMLOCK er lav – låser ikke minnet");
  }
  const int rate = cfg.num("sample_rate", 48000);

  // Oversampling i VCF: 4x hvis CPU-en tåler det med god margin, ellers 2x.
  int os = 4;
  std::string osc = cfg.str("oversample", "auto");
  if (osc == "auto") { double rt = benchRT(4, 0.5); os = rt >= 2.5 ? 4 : 2; logf("ytelse: 4x oversampling gir %.1fx sanntid -> bruker %dx", rt, os); }
  else os = std::atoi(osc.c_str()) >= 4 ? 4 : 2;

  Bank bank; bank.loadFactory();
  int n = bank.loadSyx(dataDir + "/patches.syx");
  logf("patcher: fabrikkbank lastet%s", n ? (", " + std::to_string(n) + " fra patches.syx").c_str() : "");

  // Tilstand: siste patch og bufferetrinn
  Config state; state.load(dataDir + "/state.txt");
  int startSlot = std::clamp(state.num("slot", cfg.num("start_patch", 0)), 0, 127);
  std::map<std::string, int> levelIdx;
  for (auto k : {"dacplus", "hdmi0", "hdmi1", "usb"}) levelIdx[k] = state.num(std::string("level_") + k, 0);

  Synth synth; synth.init(rate, 1024, os);
  synth.set(kSettingVoices, (float)std::clamp(cfg.num("voices", 6), 1, 10));
  synth.set(kSettingIgnoreVel, cfg.flag("velocity", false) ? 0.f : 1.f);
  synth.set(kPortaMode, (float)std::clamp(cfg.num("voice_mode", 1), 0, 2));
  synth.set(kBenderDco, (float)cfg.real("bender_dco", 0.25));     // ca. ±2 halvtoner som utgangspunkt
  synth.set(kBenderVcf, (float)cfg.real("bender_vcf", 0.0));
  synth.set(kBenderLfo, (float)cfg.real("mod_depth", 0.5));
  synth.set(kMasterVol, (float)cfg.real("master_volume", 0.5));
  const float outGain = kOutGain * std::pow(10.f, (float)cfg.real("output_gain_db", 0.0) / 20.f);

  ControllerConfig ccfg; ccfg.load(cfg);
  RequestQueue reqs;
  Controller ctl(synth, bank, reqs, ccfg);
  ctl.selectSlot(startSlot, false);

  MidiIn::Queue midiQ;
  MidiIn midi(midiQ);
  midi.start();

  Ready ready;
  const OutputPlan plan = planOutputs(cfg);
  if (!plan.error.empty()) logf("advarsel: %s", plan.error.c_str());
  const std::vector<std::string>& devs = plan.order;
  std::string devsText; for (auto& k : devs) devsText += (devsText.empty() ? "" : " ") + k;
  logf("utgangsvalg: %s -> prøver %s", plan.mode.c_str(), devsText.c_str());
  const double dacDb = std::min(0.0, cfg.real("dacplus_volume_db", 0.0));
  // Ved oppstart kan DAC+-driveren komme litt etter HDMI. Vent på den en kort stund hvis den
  // er ønsket eksplisitt eller HAT-EEPROM-en sier at et DAC-kort sitter på.
  const double dacWait = (!devs.empty() && devs[0] == "dacplus" && (plan.wanted == "dacplus" || hatSaysDac()))
                         ? cfg.real("dacplus_wait", 8.0) : 0.0;
  const double startedAt = nowSec();
  std::string bufCfg = cfg.str("buffer", "auto");
  bool chimeOn = cfg.flag("chime", true);
  int audioCpu = cfg.num("audio_cpu", 3);

  std::thread audio([&] {
    pthread_setname_np(pthread_self(), "ju6-audio");
    sched_param sp{}; sp.sched_priority = cfg.num("rt_priority", 80);
    if (pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp) != 0) logf("advarsel: fikk ikke sanntidsprioritet (SCHED_FIFO)");
    if (audioCpu >= 0 && audioCpu < (int)std::thread::hardware_concurrency()) {
      cpu_set_t set; CPU_ZERO(&set); CPU_SET(audioCpu, &set); pthread_setaffinity_np(pthread_self(), sizeof set, &set);
    }
    enableFlushToZero();
    std::vector<float> L(1024), R(1024);
    ChimeGen chime; chime.sr = (float)rate; bool chimed = false;
    AlsaOut out;
    std::map<std::string, double> failedUntil;   // utgang som ikke kunne åpnes, hoppes over en stund
    while (gRun) {
      // Finn første tilgjengelige utgang i prioritert rekkefølge.
      OutputDevice dev; std::string err;
      bool waitingForDac = false;
      for (auto& k : devs) {
        if (failedUntil.count(k) && failedUntil[k] > nowSec()) continue;
        dev = resolveDevice(k); if (!dev.pcm.empty()) break;
        if (k == "dacplus" && nowSec() - startedAt < dacWait) { waitingForDac = true; break; }
      }
      if (waitingForDac) { dev = OutputDevice{}; usleep(250000); MidiEvent e; while (midiQ.pop(e)) {} continue; }
      if (dev.pcm.empty()) {
        static double lastMsg = 0; if (nowSec() - lastMsg > 10) { logf("venter på lydenhet (%s) ...", devsText.c_str()); lastMsg = nowSec(); }
        MidiEvent e; while (midiQ.pop(e)) {}  // ikke la køen fylles mens vi venter
        usleep(500000); continue;
      }
      const BufferLevel* lv = dev.kind == "usb" ? kUsbLevels : dev.kind == "dacplus" ? kDacLevels : dev.kind == "null" ? kNullLevels : kHdmiLevels;
      int nlv = dev.kind == "null" ? 1 : 6;
      int li = std::clamp(levelIdx.count(dev.kind) ? levelIdx[dev.kind] : 0, 0, nlv - 1);
      BufferLevel want = lv[li];
      bool adaptive = bufCfg == "auto";
      if (!adaptive) { int p = 256, q = 2; sscanf(bufCfg.c_str(), "%dx%d", &p, &q); want = {p, q}; }
      if (!out.open(dev.pcm, rate, want, err)) {
        logf("kunne ikke åpne %s (%s): %s – prøver neste utgang", dev.label.c_str(), dev.pcm.c_str(), err.c_str());
        failedUntil[dev.kind] = nowSec() + 5.0; usleep(300000); continue;
      }
      failedUntil.erase(dev.kind);
      std::string mixer;
      if (dev.kind == "dacplus" && !dev.card.empty()) { mixer = setupDacMixer(dev.card, dacDb); logf("DAC+ %s", mixer.c_str()); }
      bool fb = !plan.wanted.empty() && dev.kind != plan.wanted;
      if (fb) logf("ADVARSEL: %s ble ikke funnet – bruker reserveutgangen %s", plan.wanted.c_str(), dev.label.c_str());
      ready.fallback = fb;
      int per = std::min(out.period(), 1024);
      logf("lyd: %s, %d Hz, periode %d x %d = buffer %d rammer (%.1f ms)", dev.label.c_str(), out.rate(), out.period(),
           out.buffer() / std::max(1, out.period()), out.buffer(), out.buffer() * 1000.0 / out.rate());
      { std::lock_guard<std::mutex> g(ready.m); ready.label = dev.label + " (" + dev.pcm + ")"; ready.kind = dev.kind; ready.mixer = mixer; }
      ready.period = out.period(); ready.buffer = out.buffer(); ready.audio = true;
      // Klarsignalet spilles på den utgangen som faktisk ble valgt (også etter bytte til DAC+).
      if (chimeOn && (!chimed || ready.upgrade.load())) { chime.start(fb); chimed = true; }
      ready.upgrade = false;
      std::vector<double> xrunTimes; double openedAt = nowSec(); bool reopen = false;
      while (gRun && !reopen) {
        double t = nowSec();
        MidiEvent e; while (midiQ.pop(e)) ctl.handle(e, t);
        ctl.tick(t);
        synth.process(L.data(), R.data(), per);
        chime.add(L.data(), R.data(), per);
        int r = out.write(L.data(), R.data(), per, outGain);
        if (r < 0) { logf("lydenheten forsvant – prøver på nytt"); reopen = true; break; }
        if (ready.upgrade.load(std::memory_order_relaxed)) { logf("bedre utgang funnet – bytter"); reopen = true; break; }
        if (r == 1) {
          ready.xruns++;
          if (t - openedAt > 3.0) xrunTimes.push_back(t);
          while (!xrunTimes.empty() && t - xrunTimes.front() > 30.0) xrunTimes.erase(xrunTimes.begin());
          if (adaptive && xrunTimes.size() >= 3 && li + 1 < nlv) {
            levelIdx[dev.kind] = li + 1;
            logf("for mange underløp på %d x %d – øker bufferen", want.period, want.periods);
            Request q{}; q.type = Request::Log; q.a = li + 1; q.b = dev.kind == "dacplus" ? 3 : dev.kind == "usb" ? 2 : dev.kind == "hdmi1" ? 1 : 0; reqs.push(q);
            reopen = true;
          }
        }
        if (exitAfter > 0 && t - openedAt > exitAfter) gRun = false;
      }
      ready.audio = false;
      out.close();
    }
  });

  // Kontrolltråd: lagring, tilstand, LED.
  Led led(getenv("JU6_LED_DIR") ? getenv("JU6_LED_DIR") : "/sys/class/leds/ACT"); bool ledOk = led.available();   // JU6_LED_DIR: bare for test
  if (ledOk) led.trigger("none");
  int lastSlot = startSlot; double slotChangedAt = -1; int blinkLeft = 0; double nextBlink = 0;
  bool wasReady = false;
  std::string lastStatus; double lastStatusAt = -100; bool statusAudio = false;
  while (gRun) {
    double t = nowSec();
    if (ready.audio.load() != statusAudio) { statusAudio = ready.audio.load(); lastStatusAt = -100; }
    if (t - lastStatusAt > 5.0) {   // status.txt på data-partisjonen: nyttig uten skjerm/nettverk
      lastStatusAt = t;
      std::string lbl, mix; { std::lock_guard<std::mutex> g(ready.m); lbl = ready.label; mix = ready.mixer; }
      char buf[512];
      snprintf(buf, sizeof buf,
               "JU-6 Pi " JU6_VERSION "\nlyd: %s\nperiode: %d rammer, buffer: %d rammer (%.1f ms) ved %d Hz\n"
               "VCF-oversampling: %dx\nMIDI-enheter tilkoblet: %d\nunderløp (xruns) siden start, gruppert: %d\n",
               ready.audio ? lbl.c_str() : "venter på lydenhet", ready.period.load(), ready.buffer.load(),
               ready.buffer.load() * 1000.0 / rate, rate, os, midi.connectedCount(), ready.xruns.load() / 10 * 10);
      std::string st = buf;
      st += "utgangsvalg: " + plan.mode + " (rekkefølge: " + devsText + ")\n";
      st += "lydkort funnet: " + cardList(listCards()) + "\n";
      if (!mix.empty()) st += "DAC+ " + mix + "\n";
      if (ready.audio && ready.fallback) st += "ADVARSEL: " + plan.wanted + " ble ikke funnet, spiller på reserveutgangen over\n";
      if (st != lastStatus) { atomicWrite(dataDir + "/status.txt", st.data(), st.size()); lastStatus = st; }
    }
    Request q;
    while (reqs.pop(q)) {
      if (q.type == Request::CurrentSlot) { lastSlot = q.a; slotChangedAt = t; }
      else if (q.type == Request::SavePatch) {
        bank.patch[q.a] = q.patch; bank.user[q.a] = true; bank.name[q.a] = slotName(q.a) + " Egen";
        bool ok = bank.save(dataDir);
        logf("lagret patch %s %s", slotName(q.a).c_str(), ok ? "" : "(FEIL: data-partisjonen er ikke skrivbar)");
        blinkLeft = 10; lastSlot = q.a; slotChangedAt = t;
      } else if (q.type == Request::LedBlink) { blinkLeft = q.a * 2; }
      else if (q.type == Request::Log) {
        const char* k = q.b == 3 ? "dacplus" : q.b == 2 ? "usb" : q.b == 1 ? "hdmi1" : "hdmi0";
        levelIdx[k] = q.a; slotChangedAt = t;   // lagres sammen med tilstand
      }
    }
    if (slotChangedAt > 0 && t - slotChangedAt > 2.0) {   // samle skriving, skån SD-kortet
      std::string s = "slot = " + std::to_string(lastSlot) + "\n";
      for (auto& kv : levelIdx) s += "level_" + kv.first + " = " + std::to_string(kv.second) + "\n";
      atomicWrite(dataDir + "/state.txt", s.data(), s.size());
      slotChangedAt = -1;
    }
    // Første minuttet: hvis vi spiller på en lavere prioritert utgang (f.eks. HDMI fordi DAC+-driveren
    // kom sent), og en bedre dukker opp, bytt til den.
    static double lastUpgradeCheck = 0; static std::vector<std::string> upgradeTried;
    if (ready.audio && !ready.upgrade && t - startedAt < cfg.real("upgrade_window", 60.0) && t - lastUpgradeCheck > 2.0) {
      lastUpgradeCheck = t;
      std::string cur; { std::lock_guard<std::mutex> g(ready.m); cur = ready.kind; }
      std::string best = pickKind(devs, listCards(), upgradeTried);
      if (!best.empty() && kindRank(devs, best) < kindRank(devs, cur)) { logf("%s er nå tilgjengelig (spiller på %s)", best.c_str(), cur.c_str()); upgradeTried.push_back(best); ready.upgrade = true; }
    }
    if (ledOk) {
      bool r = ready.audio.load();
      if (r && !wasReady) { blinkLeft = 6; logf("KLAR – spill!"); }
      wasReady = r;
      if (blinkLeft > 0 && t >= nextBlink) { led.set(blinkLeft % 2 == 0 ? false : true); blinkLeft--; nextBlink = t + 0.09; }
      else if (blinkLeft == 0 && t >= nextBlink) {
        if (!r) led.set(std::fmod(t, 1.0) < 0.5);                         // blinker sakte: venter på lyd
        else if (ready.fallback) { double u = std::fmod(t, 3.0);              // to korte pauser hvert 3. s: reserveutgang
          led.set(!((u < 0.15) || (u >= 0.3 && u < 0.45))); }
        else if (midi.connectedCount() == 0) led.set(std::fmod(t, 2.0) < 1.8); // kort pause: ingen MIDI-enhet
        else led.set(true);                                                // fast lys: klar
        nextBlink = t + 0.05;
      }
    } else if (ready.audio && !wasReady) { wasReady = true; logf("KLAR – spill!"); }
    usleep(20000);
  }
  audio.join();
  midi.stop();
  if (ledOk) led.trigger("mmc0");
  logf("avsluttet (xruns: %d)", ready.xruns.load());
  return 0;
}

static void usage() {
  printf("JU-6 Pi – synth inspirert av Juno-106 (lydmotor: KR-106 DSP, GPL-3)\n"
         "  ju6pi [--config FIL] [--data KATALOG] [--exit-after SEK]   kjør synthen (standard)\n"
         "  ju6pi demo KATALOG [--oversample 2|4]                      render WAV-prøver\n"
         "  ju6pi bench                                                mål CPU-margin\n"
         "  ju6pi selftest [KATALOG]                                   test MPK-mapping, sysex m.m.\n"
         "  ju6pi list                                                 vis patchlisten\n"
         "  ju6pi utganger [--config FIL] [--data KATALOG]             vis lydkort og hvilken utgang som velges\n");
}

int main(int argc, char** argv) {
  signal(SIGINT, onSignal); signal(SIGTERM, onSignal);
  enableFlushToZero();
  std::string cmd = argc > 1 && argv[1][0] != '-' ? argv[1] : "run";
  std::string cfgPath = "/etc/ju6pi/ju6.conf", dataDir = "/data/ju6"; double exitAfter = 0; int os = 4;
  for (int i = 1; i < argc; i++) {
    std::string a = argv[i];
    if (a == "--config" && i + 1 < argc) cfgPath = argv[++i];
    else if (a == "--data" && i + 1 < argc) dataDir = argv[++i];
    else if (a == "--exit-after" && i + 1 < argc) exitAfter = std::atof(argv[++i]);
    else if (a == "--oversample" && i + 1 < argc) os = std::atoi(argv[++i]);
    else if (a == "-h" || a == "--help") { usage(); return 0; }
  }
  if (cmd == "demo") { std::string dir = argc > 2 ? argv[2] : "."; printf("Rendrer prøver til %s (oversampling %dx):\n", dir.c_str(), os); return demo(dir, os); }
  if (cmd == "selftest") return selftest(argc > 2 && argv[2][0] != '-' ? argv[2] : "");
  if (cmd == "bench") { for (int o : {2, 4}) printf("VCF-oversampling %dx: %.1fx sanntid (6 stemmer, én kjerne)\n", o, benchRT(o, 3.0)); return 0; }
  if (cmd == "list") { Bank b; b.loadFactory(); for (int i = 0; i < 128; i++) printf("%3d  %s\n", i, b.name[i].c_str()); return 0; }
  if (cmd == "utganger" || cmd == "outputs") {
    Config cfg; cfg.load(cfgPath); cfg.load(dataDir + "/ju6.conf");
    auto cards = listCards(); OutputPlan p = planOutputs(cfg);
    printf("Lydkort ALSA ser nå:\n");
    for (auto& c : cards) printf("  %d  id=%-12s navn=%-22s driver=%s%s\n", c.index, c.id.c_str(), c.name.c_str(), c.driver.c_str(), isDacPlus(c) ? "   <- Raspberry Pi DAC+" : "");
    if (cards.empty()) printf("  (ingen)\n");
    if (!p.error.empty()) printf("advarsel: %s\n", p.error.c_str());
    std::string k = pickKind(p.order, cards);
    printf("Valg: %s\nVelger nå: %s%s\n", p.mode.c_str(), k.empty() ? "ingen (venter)" : k.c_str(),
           !p.wanted.empty() && !k.empty() && k != p.wanted ? "  (RESERVE – ønsket utgang mangler)" : "");
    if (!k.empty()) { OutputDevice d = resolveDevice(k); printf("ALSA-enhet: %s\n", d.pcm.c_str()); }
    printf("HAT-EEPROM sier DAC: %s\n", hatSaysDac() ? "ja" : "nei");
    return 0;
  }
  if (cmd != "run") { usage(); return 1; }
  Config cfg; cfg.load(cfgPath);
  cfg.load(dataDir + "/ju6.conf");      // brukerens fil på data-partisjonen overstyrer
  logf("starter (konfig %s + %s/ju6.conf)", cfgPath.c_str(), dataDir.c_str());
  return runRealtime(cfg, dataDir, exitAfter);
}
