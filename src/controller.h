// JU-6 Pi – oversetter MIDI fra AKAI MPK Mini Plus (eller annen kontroller) til synth-handlinger.
// Kjører i lydtråden; alt som må til disk sendes som forespørsler til kontrolltråden.
#pragma once
#include "util.h"
#include "synth.h"
#include "bank.h"

namespace ju6 {

struct Request {
  enum Type : uint8_t { SavePatch, CurrentSlot, LedBlink, Log } type;
  int a = 0, b = 0;
  Patch patch{};
};
using RequestQueue = SpscQueue<Request, 256>;

struct ControllerConfig {
  int keyChannel = -1;                      // -1 = alle kanaler unntatt pad-kanalen
  int padChannel = 9;                       // 0-basert (MIDI-kanal 10)
  std::vector<int> knobCC = { 70, 71, 72, 73, 74, 75, 76, 77 };
  std::vector<int> padA = { 36, 37, 38, 39, 40, 41, 42, 43 };   // Pad-bank A: patchnummer 1–8
  std::vector<int> padB = { 44, 45, 46, 47, 48, 49, 50, 51 };   // Pad-bank B: sider, gruppe, Hold, Transpose
  std::vector<int> modCC = { 1 };           // mod-hjul / joystick Y
  bool relative = false;                    // knotter i Relative-modus (to-komplement)
  bool pickup = false;                      // myk overtakelse i stedet for hopp
  double saveHoldSec = 1.5;                 // hold en patch-pad så lenge for å lagre
  void load(const Config& c) {
    std::string kc = c.str("key_channel", "omni");
    keyChannel = (kc == "omni" || kc == "alle") ? -1 : std::clamp(std::atoi(kc.c_str()), 1, 16) - 1;
    padChannel = std::clamp(c.num("pad_channel", 10), 1, 16) - 1;
    knobCC = c.list("knob_cc", knobCC); knobCC.resize(8, -1);
    padA = c.list("pad_notes_a", padA); padA.resize(8, -1);
    padB = c.list("pad_notes_b", padB); padB.resize(8, -1);
    modCC = c.list("mod_cc", modCC);
    relative = c.str("knob_mode", "absolute") == "relative";
    pickup = c.str("knob_takeover", "jump") == "pickup";
    saveHoldSec = c.real("save_hold_seconds", saveHoldSec);
  }
};

// Én knott-tilordning: hvordan 0..127 settes, og hvordan gjeldende verdi leses tilbake.
struct KnobDef {
  const char* name;
  int kind;      // 0 = slider (param), 1 = brytertrinn (n), 2 = spesial
  int param;
  int steps;
};

enum Special { spChorus = 1000, spWave, spSub, spTranspose, spVoiceMode, spVelocity };

// Fire sider × åtte knotter. Side 1 er standard etter oppstart.
static const KnobDef kPages[4][8] = {
  { // Side 1 – LYD: filter, envelope, chorus
    {"VCF FREQ", 0, kVcfFreq, 0}, {"VCF RES", 0, kVcfRes, 0}, {"VCF ENV", 0, kVcfEnv, 0},
    {"ENV A", 0, kEnvA, 0}, {"ENV D", 0, kEnvD, 0}, {"ENV S", 0, kEnvS, 0}, {"ENV R", 0, kEnvR, 0},
    {"CHORUS av/I/II/I+II", 2, spChorus, 4} },
  { // Side 2 – DCO
    {"RANGE 16'/8'/4'", 1, kOctTranspose, 3}, {"DCO LFO", 0, kDcoLfo, 0}, {"PWM", 0, kDcoPwm, 0},
    {"PWM-kilde LFO/MAN/ENV", 1, kPwmMode, 3}, {"BØLGE av/puls/sag/begge", 2, spWave, 4},
    {"SUB", 2, spSub, 0}, {"NOISE", 0, kDcoNoise, 0}, {"VCF KYBD", 0, kVcfKbd, 0} },
  { // Side 3 – MODULASJON, HPF, VCA
    {"LFO RATE", 0, kLfoRate, 0}, {"LFO DELAY", 0, kLfoDelay, 0}, {"VCF LFO", 0, kVcfLfo, 0},
    {"VCF ENV-polaritet +/-", 1, kVcfEnvInv, 2}, {"HPF 0-3", 1, kHpfFreq, 4},
    {"VCA ENV/GATE", 1, kVcaMode, 2}, {"VCA LEVEL", 0, kVcaLevel, 0}, {"LFO AUTO/MANUELL", 1, kLfoMode, 2} },
  { // Side 4 – SPILL: bender, mod, transpose, volum, stemmer
    {"BENDER DCO", 0, kBenderDco, 0}, {"BENDER VCF", 0, kBenderVcf, 0}, {"MOD (LFO-dybde)", 0, kBenderLfo, 0},
    {"TRANSPOSE -12..+12", 2, spTranspose, 25}, {"VOLUM", 0, kMasterVol, 0},
    {"STEMMER Poly I/Poly II/Unison", 2, spVoiceMode, 3}, {"ANSLAG av/på", 2, spVelocity, 2},
    {"PORTAMENTO", 0, kPortaRate, 0} },
};

class Controller {
public:
  Controller(Synth& s, Bank& b, RequestQueue& rq, const ControllerConfig& cfg)
    : mS(s), mB(b), mRq(rq), mCfg(cfg) {
    for (auto& t : mPadDown) t = -1.0;
    for (auto& v : mLastKnob) v = -1;
  }

  int currentSlot() const { return mSlot; }
  int page() const { return mPage; }

  void selectSlot(int slot, bool notify = true) {
    mSlot = std::clamp(slot, 0, 127);
    mBankB = mSlot >= 64; mGroup = (mSlot % 64) / 8; mNumber = mSlot % 8;
    float vol = mS.get(kMasterVol);
    mS.loadPatch(mB.patch[mSlot]);
    mS.set(kMasterVol, vol);
    resetPickup();
    if (notify) { Request r{}; r.type = Request::CurrentSlot; r.a = mSlot; mRq.push(r); }
  }

  void handle(const MidiEvent& e, double t) {
    switch (e.type) {
      case MidiEvent::NoteOn:
      case MidiEvent::NoteOff: {
        int pad = padIndex(e);
        if (pad >= 0) { padEvent(pad, e.type == MidiEvent::NoteOn, t); return; }
        if (mCfg.keyChannel >= 0 && e.ch != mCfg.keyChannel) return;
        if (e.type == MidiEvent::NoteOn) mS.noteOn(e.d1, e.d2); else mS.noteOff(e.d1);
        return;
      }
      case MidiEvent::CC: {
        int cc = e.d1, v = e.d2;
        if (std::find(mCfg.modCC.begin(), mCfg.modCC.end(), cc) != mCfg.modCC.end()) { mS.modulation(v / 127.f); return; }
        if (cc == 64) { mS.hold(v >= 64); return; }
        if (cc == 120 || cc == 123) { mS.allNotesOff(); return; }
        if (cc == 121) { mS.modulation(0.f); mS.pitchBend(8192); return; }
        for (int k = 0; k < 8; k++) if (mCfg.knobCC[k] == cc) { knob(k, v); return; }
        if (cc == 7) { mS.set(kMasterVol, v / 127.f); return; }
        return;
      }
      case MidiEvent::Bend: mS.pitchBend(e.bend); return;
      case MidiEvent::Program: selectSlot(e.d1); return;
      case MidiEvent::Sysex: mS.sysex(e.sx, e.sxLen); return;
      case MidiEvent::Reset: mS.allNotesOff(); mS.modulation(0.f); mS.pitchBend(8192); return;
    }
  }

  // Kalles hvert lydblokk: oppdager lange pad-trykk (lagring).
  void tick(double t) {
    for (int i = 0; i < 8; i++) {
      if (mPadDown[i] >= 0 && !mSaved[i] && t - mPadDown[i] >= mCfg.saveHoldSec) {
        mSaved[i] = true;
        int slot = (mBankB ? 64 : 0) + mGroup * 8 + i;
        Request r{}; r.type = Request::SavePatch; r.a = slot; r.patch = mS.capturePatch();
        mB.patch[slot] = r.patch;
        mSlot = slot; mNumber = i;
        mRq.push(r);
        { Request c{}; c.type = Request::CurrentSlot; c.a = slot; mRq.push(c); }
      }
    }
  }

private:
  int padIndex(const MidiEvent& e) const {
    if (e.ch != mCfg.padChannel) return -1;
    for (int i = 0; i < 8; i++) {
      if (mCfg.padA[i] == e.d1) return i;
      if (mCfg.padB[i] == e.d1) return 8 + i;
    }
    return -1;
  }

  void blink(int n) { Request r{}; r.type = Request::LedBlink; r.a = n; mRq.push(r); }

  void padEvent(int pad, bool down, double t) {
    if (pad < 8) {                                   // Pad-bank A: patchnummer 1–8
      // Trykk: ingenting lastes ennå, så lydene du har skrudd fram beholdes.
      // Kort slipp: last patchen. Hold (saveHoldSec): lagre DEN NÅVÆRENDE lyden.
      if (down) { mPadDown[pad] = t; mSaved[pad] = false; }
      else {
        if (mPadDown[pad] >= 0 && !mSaved[pad]) selectSlot((mBankB ? 64 : 0) + mGroup * 8 + pad);
        mPadDown[pad] = -1.0;
      }
      return;
    }
    int f = pad - 8;                                 // Pad-bank B: funksjoner
    if (f <= 3) { if (down) { mPage = f; resetPickup(); blink(f + 1); } return; }
    if (f == 4 || f == 5) {                          // gruppe − / + (A1…A8, B1…B8)
      if (!down) return;
      int g = (mBankB ? 8 : 0) + mGroup + (f == 4 ? -1 : 1);
      g = (g + 16) % 16;
      mBankB = g >= 8; mGroup = g % 8;
      selectSlot((mBankB ? 64 : 0) + mGroup * 8 + mNumber);
      blink(mGroup + 1);
      return;
    }
    if (f == 6) { if (down) { bool h = mS.get(kHold) < 0.5f; mS.hold(h); blink(h ? 2 : 1); } return; }
    if (f == 7) {                                    // Transpose: hold pad + tangent = sett; trykk = av/på
      if (down) { mTransposeDownAt = t; mTransposeBefore = mS.get(kTransposeOffset); mS.armTranspose(true); }
      else {
        mS.armTranspose(false);
        bool changed = mS.get(kTransposeOffset) != mTransposeBefore;
        if (!changed && t - mTransposeDownAt < 0.6) {       // kort trykk: av/på
          if (mS.get(kTransposeOffset) != 0.f) { mTransposeMem = mS.get(kTransposeOffset); mS.set(kTransposeOffset, 0.f); }
          else mS.set(kTransposeOffset, mTransposeMem);
        } else mTransposeMem = mS.get(kTransposeOffset);
        mS.set(kTranspose, mS.get(kTransposeOffset) != 0.f ? 1.f : 0.f);
      }
    }
  }

  // Gjeldende verdi for en knott, i 0..127 (brukes av pickup og relativ modus).
  int currentValue(const KnobDef& d) const {
    auto zone = [](int i, int n) { return std::clamp((int)((i + 0.5f) * 128.f / n), 0, 127); };
    if (d.kind == 0) return std::clamp((int)std::lround(mS.get(d.param) * 127.f), 0, 127);
    if (d.kind == 1) return zone((int)std::lround(mS.get(d.param)), d.steps);
    switch (d.param) {
      case spChorus: return zone((mS.get(kChorusI) > 0.5f ? 1 : 0) + (mS.get(kChorusII) > 0.5f ? 2 : 0), 4);
      case spWave: return zone((mS.get(kDcoPulse) > 0.5f ? 1 : 0) + (mS.get(kDcoSaw) > 0.5f ? 2 : 0), 4);
      case spSub: return mS.get(kDcoSubSw) > 0.5f ? std::clamp((int)std::lround(mS.get(kDcoSub) * 127.f), 0, 127) : 0;
      case spTranspose: return zone((int)std::lround(mS.get(kTransposeOffset)) + 12, 25);
      case spVoiceMode: { int m = (int)std::lround(mS.get(kPortaMode)); return zone(m == 1 ? 0 : m == 2 ? 1 : 2, 3); }
      case spVelocity: return zone(mS.get(kSettingIgnoreVel) > 0.5f ? 0 : 1, 2);
    }
    return 0;
  }

  void apply(const KnobDef& d, int v) {
    auto step = [](int v, int n) { return std::clamp(v * n / 128, 0, n - 1); };
    if (d.kind == 0) { mS.set(d.param, v / 127.f); return; }
    if (d.kind == 1) { mS.set(d.param, (float)step(v, d.steps)); return; }
    switch (d.param) {
      case spChorus: { int m = step(v, 4); mS.set(kChorusI, (m & 1) ? 1.f : 0.f); mS.set(kChorusII, (m & 2) ? 1.f : 0.f);
                       mS.set(kChorusOff, m == 0 ? 1.f : 0.f); break; }
      case spWave: { int m = step(v, 4); mS.set(kDcoPulse, (m & 1) ? 1.f : 0.f); mS.set(kDcoSaw, (m & 2) ? 1.f : 0.f); break; }
      case spSub: mS.set(kDcoSub, v / 127.f); mS.set(kDcoSubSw, v > 0 ? 1.f : 0.f); break;
      case spTranspose: { int tr = step(v, 25) - 12; mS.set(kTransposeOffset, (float)tr); mS.set(kTranspose, tr ? 1.f : 0.f); break; }
      case spVoiceMode: { int m = step(v, 3); mS.set(kPortaMode, m == 0 ? 1.f : m == 1 ? 2.f : 0.f); break; }
      case spVelocity: mS.set(kSettingIgnoreVel, step(v, 2) ? 0.f : 1.f); break;
    }
  }

  void knob(int k, int v) {
    const KnobDef& d = kPages[mPage][k];
    if (mCfg.relative) {
      int delta = v < 64 ? v : v - 128;
      apply(d, std::clamp(currentValue(d) + delta, 0, 127));
      return;
    }
    if (mCfg.pickup && !mPicked[k]) {
      int cur = currentValue(d), last = mLastKnob[k];
      bool crossed = last >= 0 && ((last <= cur && v >= cur) || (last >= cur && v <= cur));
      mLastKnob[k] = v;
      if (!(std::abs(v - cur) <= 2 || crossed)) return;
      mPicked[k] = true;
    }
    mLastKnob[k] = v;
    apply(d, v);
  }

  void resetPickup() { for (int k = 0; k < 8; k++) mPicked[k] = false; }

  Synth& mS; Bank& mB; RequestQueue& mRq; ControllerConfig mCfg;
  int mPage = 0, mSlot = 0, mGroup = 0, mNumber = 0;
  bool mBankB = false;
  double mPadDown[8]; bool mSaved[8] = {};
  int mLastKnob[8]; bool mPicked[8] = {};
  double mTransposeDownAt = 0; float mTransposeBefore = 0.f, mTransposeMem = 0.f;
};

} // namespace ju6
