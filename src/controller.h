// JU-6 Pi – oversetter MIDI fra AKAI MPK Mini Plus (eller annen kontroller) til synth-handlinger.
// Kjører i lydtråden; alt som må til disk eller ut på MIDI sendes som forespørsler til kontrolltråden.
//
// To sider (eierens skisse, 2026). Pad 6 (øverste rad) = SIDE 1, pad 2 (rett under) = SIDE 2.
// Skissen navngir begge som sidebyttere og tegner SIDE 1 over SIDE 2; den sier ikke eksplisitt
// hvilken av de to som er hvilken, så øverste pad følger øverste side.
// Pad-bank A er uendret (patchvalg og lagring). Pad-bank B er panelet.
#pragma once
#include "util.h"
#include "synth.h"
#include "bank.h"
#include <atomic>

namespace ju6 {

struct Request {
  enum Type : uint8_t { SavePatch, CurrentSlot, LedBlink, Log, PadLed } type;
  int a = 0, b = 0;
  Patch patch{};
};
using RequestQueue = SpscQueue<Request, 256>;

// Velocity som sendes som Note On for pad-LED (0 = Note Off, padden slukket).
// Tre røde trinn pluss av, samme trapp som chorus-padden i skissen.
constexpr int kLedOff = 0;
constexpr int kLedWeak = 42;     // svak rød
constexpr int kLedRed = 84;      // rød
constexpr int kLedStrong = 127;  // sterk rød
constexpr int kLevelStep = 8;    // VCA LEVEL +/− per trykk

// 0 = svak (MIN), 127 = sterk (MAX), lineært imellom.
inline int levelLedVelocity(int midi) {
  midi = std::clamp(midi, 0, 127);
  return kLedWeak + (midi * (kLedStrong - kLedWeak)) / 127;
}

struct ControllerConfig {
  int keyChannel = -1;                      // -1 = alle kanaler unntatt pad-kanalen
  int padChannel = 9;                       // 0-basert (MIDI-kanal 10)
  std::vector<int> knobCC = { 70, 71, 72, 73, 74, 75, 76, 77 };
  std::vector<int> padA = { 36, 37, 38, 39, 40, 41, 42, 43 };   // Pad-bank A: patchnummer 1–8
  std::vector<int> padB = { 44, 45, 46, 47, 48, 49, 50, 51 };   // Pad-bank B: panelet
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

enum Special { spSub = 1 };

// To sider × åtte knotter. Side 1 er standard etter oppstart.
// Fysiske knotter: K1–K4 øverst (CC 70–73), K5–K8 nederst (CC 74–77).
static const KnobDef kPages[2][8] = {
  { // SIDE 1 – envelope, sub, støy, filterets frekvens og resonans
    {"ENV A", 0, kEnvA, 0}, {"ENV D", 0, kEnvD, 0}, {"ENV S", 0, kEnvS, 0}, {"ENV R", 0, kEnvR, 0},
    {"SUB", 2, spSub, 0}, {"NOISE", 0, kDcoNoise, 0}, {"VCF FREQ", 0, kVcfFreq, 0}, {"VCF RES", 0, kVcfRes, 0} },
  { // SIDE 2 – DCO-modulasjon, LFO, HPF, filterets øvrige dybder
    {"DCO LFO", 0, kDcoLfo, 0}, {"DCO PWM", 0, kDcoPwm, 0}, {"LFO RATE", 0, kLfoRate, 0}, {"LFO DELAY", 0, kLfoDelay, 0},
    {"HPF 0-3", 1, kHpfFreq, 4}, {"VCF ENV", 0, kVcfEnv, 0}, {"VCF LFO", 0, kVcfLfo, 0}, {"VCF KYBD", 0, kVcfKbd, 0} },
};

// Pad-funksjon per side. Indeks 0 = pad 1 (nederst til venstre) … 7 = pad 8.
// Pad 2 og pad 6 bytter side på begge sider. Pad 8 er gruppe+ (kort) og transpose (hold + tangent).
enum PadFn : uint8_t {
  pfNone = 0,
  pfSide1, pfSide2,
  pfLevelUp, pfLevelDown, pfChorus, pfVcaMode,
  pfRange, pfPwm, pfPulse, pfSaw, pfEnvPol,
  pfGroupTranspose
};

// SIDE 1: 5 LEVEL+, 6 SIDE 1, 7 CHORUS, 8 GRUPPE/TRANSPOSE
//         1 LEVEL−, 2 SIDE 2, 3 ENV/GATE, 4 ubrukt
// SIDE 2: 5 RANGE,  6 SIDE 1, 7 LFO/MAN, 8 GRUPPE/TRANSPOSE
//         1 PULS,   2 SIDE 2, 3 SAG,      4 VCF ENV-polaritet
// RANGE er padden skissen lot stå uten navn (eierens avgjørelse 2026-11-09).
static const PadFn kPadFn[2][8] = {
  { pfLevelDown, pfSide2, pfVcaMode, pfNone, pfLevelUp, pfSide1, pfChorus, pfGroupTranspose },
  { pfPulse, pfSide2, pfSaw, pfEnvPol, pfRange, pfSide1, pfPwm, pfGroupTranspose },
};

class Controller {
public:
  Controller(Synth& s, Bank& b, RequestQueue& rq, const ControllerConfig& cfg)
    : mS(s), mB(b), mRq(rq), mCfg(cfg) {
    for (auto& t : mPadDown) t = -1.0;
    for (auto& v : mLastKnob) v = -1;
    for (auto& v : mLastLed) v = -1;
  }

  int currentSlot() const { return mSlot; }
  int page() const { return mPage; }
  // 0 = slukket, ellers velocityen som ville blitt sendt til padden (0–7 = pad 1–8).
  int padLedVelocity(int pad) const {
    if (pad < 0 || pad > 7) return 0;
    return ledFor(kPadFn[mPage][pad]);
  }
  void setEmitLeds(bool on) {
    mEmitLeds = on;
    if (on) { for (auto& v : mLastLed) v = -1; mLedDirty = true; flushLeds(); }
  }
  // Kontrolltråden øker denne når en MIDI-enhet kobles til, så LED-ene sendes på nytt.
  void setLedRefresh(std::atomic<int>* flag) { mRefresh = flag; }

  void selectSlot(int slot, bool notify = true) {
    mSlot = std::clamp(slot, 0, 127);
    mBankB = mSlot >= 64; mGroup = (mSlot % 64) / 8; mNumber = mSlot % 8;
    float vol = mS.get(kMasterVol);
    mS.loadPatch(mB.patch[mSlot]);
    mS.set(kMasterVol, vol);
    resetPickup();
    mLedDirty = true;
    if (notify) { Request r{}; r.type = Request::CurrentSlot; r.a = mSlot; mRq.push(r); }
    flushLeds();
  }

  void handle(const MidiEvent& e, double t) {
    switch (e.type) {
      case MidiEvent::NoteOn:
      case MidiEvent::NoteOff: {
        int pad = padIndex(e);
        if (pad >= 0) { padEvent(pad, e.type == MidiEvent::NoteOn, t); flushLeds(); return; }
        if (mCfg.keyChannel >= 0 && e.ch != mCfg.keyChannel) return;
        if (e.type == MidiEvent::NoteOn) {
          float before = mS.get(kTransposeOffset);
          mS.noteOn(e.d1, e.d2);
          if (mS.get(kTransposeOffset) != before) { mLedDirty = true; flushLeds(); }
        } else mS.noteOff(e.d1);
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
      case MidiEvent::Sysex: mS.sysex(e.sx, e.sxLen); mLedDirty = true; flushLeds(); return;
      case MidiEvent::Reset: mS.allNotesOff(); mS.modulation(0.f); mS.pitchBend(8192); return;
    }
  }

  // Kalles hvert lydblokk: lange pad-trykk (lagring) og gjentakelse av LEVEL +/−.
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
    if (mLevelPad >= 0 && t >= mLevelNext) {
      nudgeLevel(mLevelDir);
      mLevelNext = t + 0.09;
      mLedDirty = true;
    }
    if (mRefresh) {
      int v = mRefresh->load(std::memory_order_acquire);
      if (v != mRefreshSeen) { mRefreshSeen = v; for (auto& x : mLastLed) x = -1; mLedDirty = true; }
    }
    flushLeds();
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

  void setPage(int p) {
    p = p ? 1 : 0;
    mPage = p;
    resetPickup();
    blink(p + 1);
    mLedDirty = true;
  }

  void nudgeLevel(int dir) {
    int cur = std::clamp((int)std::lround(mS.get(kVcaLevel) * 127.f), 0, 127);
    int n = std::clamp(cur + dir * kLevelStep, 0, 127);
    mS.set(kVcaLevel, n / 127.f);
  }

  void cycleChorus() {
    int m = (mS.get(kChorusI) > 0.5f ? 1 : 0) + (mS.get(kChorusII) > 0.5f ? 2 : 0);
    m = (m + 1) & 3;
    mS.set(kChorusI, (m & 1) ? 1.f : 0.f);
    mS.set(kChorusII, (m & 2) ? 1.f : 0.f);
    mS.set(kChorusOff, m == 0 ? 1.f : 0.f);
  }

  void cycleRange() {
    int o = (int)std::lround(mS.get(kOctTranspose));
    o = (o + 1) % 3;
    if (o < 0) o += 3;
    mS.set(kOctTranspose, (float)o);
  }

  void toggleFloat(int param) {
    mS.set(param, mS.get(param) > 0.5f ? 0.f : 1.f);
  }

  // LFO (0) ↔ MAN (1). PWM fra ENV (2) finnes i patchformatet, men ikke på padden:
  // ett trykk derfra velger LFO. LED lyser bare for LFO.
  void togglePwm() {
    int m = (int)std::lround(mS.get(kPwmMode));
    mS.set(kPwmMode, m == 0 ? 1.f : 0.f);
  }

  void toggleVca() {
    int m = (int)std::lround(mS.get(kVcaMode));
    mS.set(kVcaMode, m == 0 ? 1.f : 0.f);
  }

  void groupPlus() {
    int g = (mBankB ? 8 : 0) + mGroup + 1;
    g %= 16;
    mBankB = g >= 8; mGroup = g % 8;
    selectSlot((mBankB ? 64 : 0) + mGroup * 8 + mNumber);
    blink(mGroup + 1);
  }

  void padEvent(int pad, bool down, double t) {
    if (pad < 8) {                                   // Pad-bank A: patchnummer 1–8
      if (down) { mPadDown[pad] = t; mSaved[pad] = false; }
      else {
        if (mPadDown[pad] >= 0 && !mSaved[pad]) selectSlot((mBankB ? 64 : 0) + mGroup * 8 + pad);
        mPadDown[pad] = -1.0;
      }
      return;
    }
    int f = pad - 8;
    PadFn fn = kPadFn[mPage][f];
    if (!down) {
      if (fn == pfGroupTranspose) {
        mS.armTranspose(false);
        bool changed = mS.get(kTransposeOffset) != mTransposeBefore;
        if (!changed && t - mTransposeDownAt < 0.6) groupPlus();
        mS.set(kTranspose, mS.get(kTransposeOffset) != 0.f ? 1.f : 0.f);
        mLedDirty = true;
      }
      if (mLevelPad == f) mLevelPad = -1;
      return;
    }
    switch (fn) {
      case pfSide1: setPage(0); break;
      case pfSide2: setPage(1); break;
      case pfLevelUp: nudgeLevel(+1); mLevelPad = f; mLevelDir = +1; mLevelNext = t + 0.40; break;
      case pfLevelDown: nudgeLevel(-1); mLevelPad = f; mLevelDir = -1; mLevelNext = t + 0.40; break;
      case pfChorus: cycleChorus(); break;
      case pfVcaMode: toggleVca(); break;
      case pfRange: cycleRange(); break;
      case pfPwm: togglePwm(); break;
      case pfPulse: toggleFloat(kDcoPulse); break;
      case pfSaw: toggleFloat(kDcoSaw); break;
      case pfEnvPol: toggleFloat(kVcfEnvInv); break;
      case pfGroupTranspose:
        mTransposeDownAt = t; mTransposeBefore = mS.get(kTransposeOffset); mS.armTranspose(true); break;
      case pfNone: break;
    }
    mLedDirty = true;
  }

  int ledFor(PadFn fn) const {
    auto onOff = [](bool on) { return on ? kLedRed : kLedOff; };
    switch (fn) {
      case pfSide1: return mPage == 0 ? kLedStrong : kLedOff;
      case pfSide2: return mPage == 1 ? kLedStrong : kLedOff;
      case pfLevelUp:
      case pfLevelDown: return levelLedVelocity((int)std::lround(mS.get(kVcaLevel) * 127.f));
      case pfChorus: {
        int m = (mS.get(kChorusI) > 0.5f ? 1 : 0) + (mS.get(kChorusII) > 0.5f ? 2 : 0);
        return m == 0 ? kLedOff : m == 1 ? kLedWeak : m == 2 ? kLedRed : kLedStrong;
      }
      case pfVcaMode: return onOff((int)std::lround(mS.get(kVcaMode)) == 0);   // rød = ENV
      case pfRange: {
        int o = std::clamp((int)std::lround(mS.get(kOctTranspose)), 0, 2);
        return o == 0 ? kLedWeak : o == 1 ? kLedRed : kLedStrong;             // 16' / 8' / 4'
      }
      case pfPwm: return onOff((int)std::lround(mS.get(kPwmMode)) == 0);       // rød = LFO
      case pfPulse: return onOff(mS.get(kDcoPulse) > 0.5f);
      case pfSaw: return onOff(mS.get(kDcoSaw) > 0.5f);
      case pfEnvPol: return onOff(mS.get(kVcfEnvInv) > 0.5f);                  // rød = invertert
      case pfGroupTranspose: return mS.get(kTransposeOffset) != 0.f ? kLedStrong : kLedOff;
      case pfNone: return kLedOff;
    }
    return kLedOff;
  }

  void flushLeds() {
    if (!mEmitLeds || !mLedDirty) return;
    mLedDirty = false;
    for (int i = 0; i < 8; i++) {
      int vel = padLedVelocity(i);
      if (mLastLed[i] == vel) continue;
      mLastLed[i] = vel;
      auto push = [&](int note) {
        if (note < 0) return;
        Request r{}; r.type = Request::PadLed; r.a = note; r.b = vel;
        mRq.push(r);
      };
      push(mCfg.padB[i]);
      // Side-padene skal vise aktiv side uansett om MPK står i bank A eller B.
      bool pagePad = kPadFn[0][i] == pfSide1 || kPadFn[0][i] == pfSide2;
      if (pagePad && mCfg.padA[i] != mCfg.padB[i]) push(mCfg.padA[i]);
    }
  }

  int currentValue(const KnobDef& d) const {
    auto zone = [](int i, int n) { return std::clamp((int)((i + 0.5f) * 128.f / n), 0, 127); };
    if (d.kind == 0) return std::clamp((int)std::lround(mS.get(d.param) * 127.f), 0, 127);
    if (d.kind == 1) return zone((int)std::lround(mS.get(d.param)), d.steps);
    if (d.param == spSub) return mS.get(kDcoSubSw) > 0.5f ? std::clamp((int)std::lround(mS.get(kDcoSub) * 127.f), 0, 127) : 0;
    return 0;
  }

  void apply(const KnobDef& d, int v) {
    auto step = [](int v, int n) { return std::clamp(v * n / 128, 0, n - 1); };
    if (d.kind == 0) { mS.set(d.param, v / 127.f); return; }
    if (d.kind == 1) { mS.set(d.param, (float)step(v, d.steps)); return; }
    if (d.param == spSub) { mS.set(kDcoSub, v / 127.f); mS.set(kDcoSubSw, v > 0 ? 1.f : 0.f); }
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
  double mTransposeDownAt = 0; float mTransposeBefore = 0.f;
  int mLevelPad = -1, mLevelDir = 0; double mLevelNext = 0;
  bool mEmitLeds = true, mLedDirty = true;
  int mLastLed[8];
  std::atomic<int>* mRefresh = nullptr;
  int mRefreshSeen = 0;
};

} // namespace ju6
