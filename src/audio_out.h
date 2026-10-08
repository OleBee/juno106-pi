#pragma once
#include "util.h"
#include <alsa/asoundlib.h>

namespace ju6 {

struct BufferLevel { int period; int periods; };
// Trinn fra minst til størst buffer. HDMI-lyd på Pi 5 tåler ikke like små
// perioder som USB, derfor egne trinn.
static const BufferLevel kHdmiLevels[] = { {256, 2}, {256, 3}, {512, 2}, {512, 3}, {1024, 2}, {1024, 3} };
static const BufferLevel kUsbLevels[]  = { {64, 2}, {128, 2}, {128, 3}, {256, 2}, {256, 3}, {512, 2} };
static const BufferLevel kNullLevels[] = { {256, 2} };

struct OutputDevice {
  std::string kind;   // hdmi0, hdmi1, usb, null, eller rå ALSA-navn
  std::string pcm;    // ALSA-enhetsnavn
  std::string label;
};

// Finn ALSA-navn for en ønsket utgang. Tom pcm = finnes ikke nå.
inline OutputDevice resolveDevice(const std::string& kind) {
  OutputDevice d{kind, "", kind};
  if (kind == "hdmi0" || kind == "hdmi1") {
    std::string card = kind == "hdmi0" ? "vc4hdmi0" : "vc4hdmi1";
    if (snd_card_get_index(card.c_str()) >= 0) {
      d.pcm = "lyd_" + kind;            // fra /etc/alsa/conf.d/60-pi5-hdmi-lyd.conf (plug -> hdmi/iec958)
      snd_pcm_t* t;
      if (snd_pcm_open(&t, d.pcm.c_str(), SND_PCM_STREAM_PLAYBACK, SND_PCM_NONBLOCK) == 0) snd_pcm_close(t);
      else d.pcm = "default:CARD=" + card;   // alsa-lib sin vc4-hdmi.conf (plug+iec958)
      d.label = kind == "hdmi0" ? "HDMI0 (ved USB-C)" : "HDMI1";
    }
  } else if (kind == "usb") {
    int c = -1;
    while (snd_card_next(&c) == 0 && c >= 0) {
      snd_ctl_t* ctl; char hw[16]; snprintf(hw, sizeof hw, "hw:%d", c);
      if (snd_ctl_open(&ctl, hw, 0) < 0) continue;
      snd_ctl_card_info_t* info; snd_ctl_card_info_alloca(&info);
      if (snd_ctl_card_info(ctl, info) == 0 && std::string(snd_ctl_card_info_get_driver(info)) == "USB-Audio") {
        snd_pcm_info_t* pi; snd_pcm_info_alloca(&pi);
        snd_pcm_info_set_device(pi, 0); snd_pcm_info_set_stream(pi, SND_PCM_STREAM_PLAYBACK);
        if (snd_ctl_pcm_info(ctl, pi) == 0) {
          d.pcm = std::string("plughw:CARD=") + snd_ctl_card_info_get_id(info) + ",DEV=0";
          d.label = std::string("USB: ") + snd_ctl_card_info_get_name(info);
          snd_ctl_close(ctl); break;
        }
      }
      snd_ctl_close(ctl);
    }
  } else if (kind == "null") {
    d.pcm = "null"; d.label = "null (ingen lyd, test)";
  } else {
    d.pcm = kind;
  }
  return d;
}

class AlsaOut {
public:
  ~AlsaOut() { close(); }
  bool open(const std::string& pcm, int rate, BufferLevel want, std::string& err) {
    close();
    int r = snd_pcm_open(&mPcm, pcm.c_str(), SND_PCM_STREAM_PLAYBACK, 0);
    if (r < 0) { err = snd_strerror(r); mPcm = nullptr; return false; }
    snd_pcm_hw_params_t* hw; snd_pcm_hw_params_alloca(&hw);
    snd_pcm_hw_params_any(mPcm, hw);
    snd_pcm_hw_params_set_access(mPcm, hw, SND_PCM_ACCESS_RW_INTERLEAVED);
    mS32 = snd_pcm_hw_params_set_format(mPcm, hw, SND_PCM_FORMAT_S32_LE) == 0;
    if (!mS32 && snd_pcm_hw_params_set_format(mPcm, hw, SND_PCM_FORMAT_S16_LE) < 0) { err = "format"; close(); return false; }
    snd_pcm_hw_params_set_channels(mPcm, hw, 2);
    unsigned rr = rate; snd_pcm_hw_params_set_rate_near(mPcm, hw, &rr, nullptr);
    snd_pcm_uframes_t per = want.period, buf = (snd_pcm_uframes_t)want.period * want.periods;
    snd_pcm_hw_params_set_period_size_near(mPcm, hw, &per, nullptr);
    snd_pcm_hw_params_set_buffer_size_near(mPcm, hw, &buf);
    if ((r = snd_pcm_hw_params(mPcm, hw)) < 0) { err = std::string("hw_params: ") + snd_strerror(r); close(); return false; }
    snd_pcm_hw_params_get_period_size(hw, &per, nullptr);
    snd_pcm_hw_params_get_buffer_size(hw, &buf);
    snd_pcm_hw_params_get_rate(hw, &rr, nullptr);
    mPeriod = (int)per; mBuffer = (int)buf; mRate = (int)rr;
    snd_pcm_sw_params_t* sw; snd_pcm_sw_params_alloca(&sw);
    snd_pcm_sw_params_current(mPcm, sw);
    snd_pcm_sw_params_set_avail_min(mPcm, sw, per);
    snd_pcm_sw_params_set_start_threshold(mPcm, sw, buf);
    snd_pcm_sw_params(mPcm, sw);
    mIl.assign((size_t)mPeriod * 2, 0);
    return true;
  }
  void close() { if (mPcm) { snd_pcm_drop(mPcm); snd_pcm_close(mPcm); mPcm = nullptr; } }

  // Skriv én periode. Returnerer 0 ok, 1 = xrun (gjenopprettet), -1 = enheten borte.
  int write(const float* L, const float* R, int n, float gain) {
    int32_t* o32 = (int32_t*)mIl.data(); int16_t* o16 = (int16_t*)mIl.data();
    for (int i = 0; i < n; i++) {
      float a = softClip(L[i] * gain), b = softClip(R[i] * gain);
      if (mS32) { o32[2 * i] = (int32_t)(a * 2147483520.f); o32[2 * i + 1] = (int32_t)(b * 2147483520.f); }
      else { o16[2 * i] = (int16_t)(a * 32767.f); o16[2 * i + 1] = (int16_t)(b * 32767.f); }
    }
    int xr = 0;
    const char* p = (const char*)mIl.data(); int left = n; int fb = mS32 ? 8 : 4;
    while (left > 0) {
      snd_pcm_sframes_t w = snd_pcm_writei(mPcm, p, left);
      if (w == -EAGAIN) continue;
      if (w == -EPIPE || w == -ESTRPIPE) { xr = 1; if (snd_pcm_recover(mPcm, (int)w, 1) < 0) return -1; continue; }
      if (w < 0) { if (snd_pcm_recover(mPcm, (int)w, 1) < 0) return -1; xr = 1; continue; }
      p += w * fb; left -= (int)w;
    }
    return xr;
  }
  static float softClip(float x) {   // lineær opp til -1 dBFS, så myk metning
    const float k = 0.89f;
    float a = std::fabs(x);
    if (a <= k) return x;
    float y = k + (1.f - k) * std::tanh((a - k) / (1.f - k));
    return x < 0 ? -y : y;
  }
  int period() const { return mPeriod; }
  int buffer() const { return mBuffer; }
  int rate() const { return mRate; }
  bool isOpen() const { return mPcm != nullptr; }
private:
  snd_pcm_t* mPcm = nullptr;
  bool mS32 = true;
  int mPeriod = 0, mBuffer = 0, mRate = 0;
  std::vector<int32_t> mIl;
};

} // namespace ju6
