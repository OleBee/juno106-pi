// JU-6 Pi – lydmotor-innpakning rundt KR-106-DSP (GPL-3).
// Inspirert av Juno-106. Ingen tilknytning til Roland Corporation.
#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include "../third_party/kr106/DSP/KR106_DSP.h"
#include "../third_party/kr106/DSP/KR106SysEx.h"

namespace ju6 {

// Parameterindekser – må stemme med KR106DSP::SetParam sin interne enum.
enum Param {
  kBenderDco = 0, kBenderVcf, kArpRate, kLfoRate, kLfoDelay,
  kDcoLfo, kDcoPwm, kDcoSub, kDcoNoise, kHpfFreq,
  kVcfFreq, kVcfRes, kVcfEnv, kVcfLfo, kVcfKbd,
  kVcaLevel, kEnvA, kEnvD, kEnvS, kEnvR,
  kTranspose, kHold, kArpeggio, kDcoPulse, kDcoSaw, kDcoSubSw,
  kChorusOff, kChorusI, kChorusII,
  kOctTranspose, kArpMode, kArpRange, kLfoMode, kPwmMode,
  kVcfEnvInv, kVcaMode,
  kBender, kTuning, kPower,
  kPortaMode, kPortaRate,
  kTransposeOffset, kBenderLfo,
  kAdsrMode,
  kMasterVol,
  kSettingVoices, kSettingOversample, kSettingIgnoreVel,
  kSettingArpLimitKbd, kSettingArpSync, kSettingLfoSync,
  kSettingMonoRetrig, kSettingMidiSysEx,
  kArpQuantize, kLfoQuantize, kSettingOscMode,
  kNumParams
};

// En Juno-106-patch: 16 slidere (0-127) + SW1 + SW2, nøyaktig som i sysex (APR).
// ext: JU-6 Pi-utvidelse for det 106-formatet ikke har plass til (lagres i names.txt):
//   bit 0 = chorus I+II, bit 1 = PWM fra ENV
struct Patch { uint8_t d[18]; uint8_t ext = 0; };

class Synth {
public:
  Synth() : mDsp(6) {}

  void init(double sampleRate, int maxBlock, int oversample = 4) {
    mSr = sampleRate;
    mDsp.Reset(sampleRate, maxBlock);
    // Standardverdier (samme som KR-106-pluginens), Juno-106-modus.
    const float defs[kNumParams] = {
      0.f, 0.f, 30.f / 128.f, 0.24f, 0.f,      // bender dco/vcf, arp rate, lfo rate/delay
      0.f, 0.5f, 1.f, 0.f, 1.f,                // dco lfo, pwm, sub, noise, hpf (flat)
      1.f, 0.f, 0.f, 0.f, 0.f,                 // vcf freq/res/env/lfo/kbd
      0.5f, 0.25f, 0.25f, 0.9f, 0.25f,         // vca, A D S R
      0.f, 0.f, 0.f, 1.f, 1.f, 1.f,            // transpose, hold, arp, pulse, saw, subsw
      0.f, 1.f, 0.f,                           // chorus off / I / II
      1.f, 0.f, 0.f, 0.f, 1.f,                 // oct (8'), arp mode/range, lfo mode, pwm mode
      0.f, 1.f,                                // vcf env inv, vca mode
      0.f, 0.f, 1.f,                           // bender, tuning, power
      1.f, 0.f,                                // porta mode (Poly I = Juno-106), porta rate
      0.f, 0.f,                                // transpose offset, bender lfo
      1.f,                                     // ADSR/model = J106
      0.5f,                                    // master volume
      6.f, (float)oversample, 1.f,             // 6 stemmer, VCF-oversampling, ignorer anslag
      1.f, 0.f, 0.f, 1.f, 0.f,
      (float)kr106::kDiv16, (float)kr106::kLfoDiv4, 1.f
    };
    // Modellen først, så alle kurver regnes i J106-modus.
    set(kAdsrMode, 1.f);
    for (int i = 0; i < kNumParams; i++) set(i, defs[i]);
    mDsp.mMasterVolSmooth = mDsp.mMasterVol;
    mDsp.mVcaLevelSmooth = mDsp.mVcaLevel;
  }

  // Sett en parameter med "ekte" verdi (0–1 for slidere, heltall for brytere).
  void set(int idx, float v) {
    if (idx < 0 || idx >= kNumParams) return;
    mCur[idx] = v;
    switch (idx) {
      case kTransposeOffset: mDsp.SetKeyTranspose((int)std::lround(v)); break;
      case kMasterVol: mDsp.mMasterVol = v * v; break;
      case kSettingVoices: mDsp.SetActiveVoices((int)std::lround(v)); break;
      case kSettingOversample: { int o = (int)std::lround(v); mDsp.SetOversample(o <= 1 ? 1 : o <= 3 ? 2 : 4); break; }
      case kSettingIgnoreVel: mDsp.mIgnoreVelocity = v > 0.5f; break;
      case kSettingMonoRetrig: mDsp.mMonoRetrigger = v > 0.5f; break;
      case kSettingOscMode: { int m = (int)std::lround(v); mDsp.ForEachVoice([m](kr106::Voice<float>& vc) { vc.mOscMode = m; }); break; }
      case kSettingArpLimitKbd: mDsp.mArp.mLimitToKeyboard = v > 0.5f; break;
      case kChorusI: case kChorusII:
        mDsp.SetParam(idx, v);
        if (v > 0.5f) mCur[kChorusOff] = 0.f;
        break;
      default: mDsp.SetParam(idx, v); break;
    }
  }
  float get(int idx) const { return (idx >= 0 && idx < kNumParams) ? mCur[idx] : 0.f; }

  // Last en patch i Juno-106-format (samme skalering som en ekte 106 som tar imot sysex).
  void loadPatch(const Patch& p) {
    uint8_t msg[22] = { 0x41, 0x30, 0x00, 0x00 };
    std::memcpy(msg + 4, p.d, 18);
    decoder().decodeAPR(msg, 22, [this](int idx, float val) {
      if (idx == kDcoLfo) val = kr106::Voice<float>::dcoLfoDepth106_inverseTaper(val);
      set(idx, val);
    });
    if (p.ext & 1) { set(kChorusI, 1.f); set(kChorusII, 1.f); set(kChorusOff, 0.f); }
    if (p.ext & 2) set(kPwmMode, 2.f);
  }

  // Les ut gjeldende lyd som Juno-106-patch.
  Patch capturePatch() const {
    Patch p{};
    auto b = [](float v, float s) { return (uint8_t)std::clamp((int)std::lround(v * s), 0, 127); };
    float lfo = mCur[kDcoLfo]; lfo = lfo / (1.f + 5.f * lfo - 5.f * lfo * lfo);
    const float sl[16] = { mCur[kLfoRate], mCur[kLfoDelay], lfo, mCur[kDcoPwm], mCur[kDcoNoise],
                           mCur[kVcfFreq], mCur[kVcfRes], mCur[kVcfEnv], mCur[kVcfLfo], mCur[kVcfKbd],
                           mCur[kVcaLevel], mCur[kEnvA], mCur[kEnvD], mCur[kEnvS], mCur[kEnvR],
                           mCur[kDcoSubSw] > 0.5f ? mCur[kDcoSub] : 0.f };
    for (int i = 0; i < 16; i++) p.d[i] = b(sl[i], i == 3 ? 105.f : 127.f);
    int oct = (int)std::lround(mCur[kOctTranspose]);
    uint8_t sw1 = oct >= 2 ? 0x04 : oct == 1 ? 0x02 : 0x01;
    if (mCur[kDcoPulse] > 0.5f) sw1 |= 0x08;
    if (mCur[kDcoSaw] > 0.5f) sw1 |= 0x10;
    bool cI = mCur[kChorusI] > 0.5f, cII = mCur[kChorusII] > 0.5f;
    if (!cI && !cII) sw1 |= 0x20;
    if (cI) sw1 |= 0x40;   // I+II lagres som I (106-formatet har ikke I+II)
    uint8_t sw2 = 0;
    if ((int)std::lround(mCur[kPwmMode]) != 0) sw2 |= 0x01;
    if (mCur[kVcfEnvInv] > 0.5f) sw2 |= 0x02;
    if ((int)std::lround(mCur[kVcaMode]) != 0) sw2 |= 0x04;
    sw2 |= (uint8_t)((3 - std::clamp((int)std::lround(mCur[kHpfFreq]), 0, 3)) << 3);
    p.d[16] = sw1; p.d[17] = sw2;
    p.ext = (uint8_t)((cI && cII ? 1 : 0) | ((int)std::lround(mCur[kPwmMode]) == 2 ? 2 : 0));
    return p;
  }

  // Sysex inn (data etter F0, uten F7): APR (patch) og IPR (enkeltparameter).
  bool sysex(const uint8_t* data, int len) {
    return decoder().decode(data, len, [this](int idx, float val) {
      if (idx == kDcoLfo) val = kr106::Voice<float>::dcoLfoDepth106_inverseTaper(val);
      set(idx, val);
    });
  }

  // --- spillehandlinger ---
  void noteOn(int note, int vel) {
    if (mTransposeArmed) {             // som på 106: hold Transpose og trykk en tangent
      set(kTransposeOffset, (float)std::clamp(note - 60, -24, 36));
      return;
    }
    mDsp.NoteOn(note, vel);
  }
  void noteOff(int note) { mDsp.NoteOff(note); }
  void pitchBend(int v14) { set(kBender, std::clamp((v14 - 8192) / 8192.f, -1.f, 1.f)); }
  // Mod (joystick/hjul opp): LFO-trigger + dybde. Originalen har en fjærbelastet spak;
  // her er dybden proporsjonal med hvor langt spaken/hjulet skyves.
  void modulation(float v) {
    mDsp.mLFO.SetTrigger(v > 0.f);
    mDsp.ForEachVoice([v](kr106::Voice<float>& vc) { vc.mBenderModAmt = v; });
  }
  void hold(bool on) { set(kHold, on ? 1.f : 0.f); }
  void allNotesOff() { mDsp.AllNotesOff(); }
  void armTranspose(bool a) { mTransposeArmed = a; }

  void process(float* L, float* R, int n) {
    float* out[2] = { L, R };
    mDsp.ProcessBlock(nullptr, out, 2, n);
  }

  KR106DSP<float>& dsp() { return mDsp; }

private:
  static kr106::SysExDecoder decoder() {
    return kr106::SysExDecoder{ kLfoRate, kLfoDelay, kDcoLfo, kDcoPwm, kDcoNoise, kVcfFreq, kVcfRes,
      kVcfEnv, kVcfLfo, kVcfKbd, kVcaLevel, kEnvA, kEnvD, kEnvS, kEnvR, kDcoSub,
      kOctTranspose, kDcoPulse, kDcoSaw, kChorusOff, kChorusI, kChorusII,
      kPwmMode, kVcfEnvInv, kVcaMode, kHpfFreq, kDcoSubSw, true };
  }
  KR106DSP<float> mDsp;
  double mSr = 48000.0;
  float mCur[kNumParams] = {};
  bool mTransposeArmed = false;
};

} // namespace ju6
