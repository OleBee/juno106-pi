#pragma once
#include "util.h"
#include <alsa/asoundlib.h>

namespace ju6 {

struct BufferLevel { int period; int periods; };
// Trinn fra minst til størst buffer. HDMI-lyd på Pi 5 tåler ikke like små
// perioder som USB, derfor egne trinn.
static const BufferLevel kHdmiLevels[] = { {256, 2}, {256, 3}, {512, 2}, {512, 3}, {1024, 2}, {1024, 3} };
static const BufferLevel kUsbLevels[]  = { {64, 2}, {128, 2}, {128, 3}, {256, 2}, {256, 3}, {512, 2} };
// Raspberry Pi DAC+ (PCM5122 over I2S/DMA): små perioder går fint, starter på 128 x 2 = 5,3 ms.
static const BufferLevel kDacLevels[]  = { {128, 2}, {128, 3}, {256, 2}, {256, 3}, {512, 2}, {512, 3} };
static const BufferLevel kNullLevels[] = { {256, 2} };

// Kortene ALSA ser akkurat nå (fra /proc/asound via ctl-info). Egen struktur,
// så valget av utgang kan testes uten maskinvare.
struct CardInfo { int index; std::string id, name, driver; };

// Bare for test uten lydkort: JU6_FAKE_CARDS=fil med linjer «nummer id driver navn…».
// Alle utganger peker da på ALSA-enheten "null". Filen leses på nytt hver gang (kort kan «dukke opp»).
inline const char* fakeCardsFile() { const char* f = getenv("JU6_FAKE_CARDS"); return f && *f ? f : nullptr; }

inline std::vector<CardInfo> listCards() {
  std::vector<CardInfo> v; int c = -1;
  if (const char* ff = fakeCardsFile()) {
    std::ifstream f(ff); std::string line;
    while (std::getline(f, line)) { std::istringstream is(line); CardInfo ci; if (!(is >> ci.index >> ci.id >> ci.driver)) continue;
      std::getline(is, ci.name); ci.name.erase(0, ci.name.find_first_not_of(' ')); v.push_back(ci); }
    return v;
  }
  while (snd_card_next(&c) == 0 && c >= 0) {
    snd_ctl_t* ctl; char hw[16]; snprintf(hw, sizeof hw, "hw:%d", c);
    if (snd_ctl_open(&ctl, hw, 0) < 0) continue;
    snd_ctl_card_info_t* info; snd_ctl_card_info_alloca(&info);
    if (snd_ctl_card_info(ctl, info) == 0)
      v.push_back({c, snd_ctl_card_info_get_id(info), snd_ctl_card_info_get_name(info), snd_ctl_card_info_get_driver(info)});
    snd_ctl_close(ctl);
  }
  return v;
}

// Raspberry Pi DAC+ (grønt kort, overlay rpi-dacplus): kortnavn «RPi DAC+», ALSA-id «RPiDAC».
// Eldre IQaudIO DAC+ (svart kort, overlay iqaudio-dacplus): «IQaudIODAC». Samme PCM5122-krets.
// Matcher på id/navn, aldri på kortnummer (nummeret avhenger av rekkefølgen kortene dukker opp i).
inline bool isDacPlus(const CardInfo& c) {
  if (c.id == "RPiDAC" || c.id == "IQaudIODAC") return true;
  if (c.name == "RPi DAC+" || c.name == "IQaudIODAC") return true;
  // HiFiBerry DAC+ (snd_rpi_hifiberry_dacplus): id «sndrpihifiberry», navn med «HiFiBerry»/«hifiberry»
  auto has = [](const std::string& s, const char* n) { return s.find(n) != std::string::npos; };
  if (has(c.id, "hifiberry") || has(c.name, "hifiberry") || has(c.name, "HiFiBerry") || has(c.driver, "hifiberry")) return true;
  return false;
}

inline bool cardPresent(const std::string& kind, const std::vector<CardInfo>& cards, const CardInfo** hit = nullptr) {
  for (auto& c : cards) {
    bool ok = kind == "dacplus" ? isDacPlus(c)
            : kind == "hdmi0"   ? c.id == "vc4hdmi0"
            : kind == "hdmi1"   ? c.id == "vc4hdmi1"
            : kind == "usb"     ? c.driver == "USB-Audio"
            : false;
    if (ok) { if (hit) *hit = &c; return true; }
  }
  return kind == "null";
}

// Hvilke utganger som prøves, i rekkefølge, ut fra ju6.conf.
//   audio_output = auto     DAC+ hvis kortet finnes, ellers HDMI0, HDMI1, USB (standard)
//   audio_output = dacplus  DAC+; mangler den: reserve HDMI0, HDMI1, USB + varsel (LED/tone/status.txt)
//   audio_output = hdmi     bare HDMI0, så HDMI1 (som i 1.0.0)
//   audio_output = usb      bare USB-lydkort
//   audio_output = null     ingen lyd (test)
// Er audio_output ikke satt, men den gamle audio_devices er det, brukes den lista som før.
struct OutputPlan {
  std::vector<std::string> order;
  std::string wanted;    // utgangen brukeren ba om eksplisitt ("" = auto/liste, ingen varsel)
  std::string mode;      // for logg/status
  std::string error;     // ukjent verdi
};

inline OutputPlan planOutputs(const Config& cfg) {
  OutputPlan p;
  bool hasMode = cfg.kv.count("audio_output") && !cfg.kv.at("audio_output").empty();
  bool hasList = cfg.kv.count("audio_devices") && !cfg.kv.at("audio_devices").empty();
  if (!hasMode && hasList) {
    p.order = cfg.words("audio_devices", {"hdmi0", "hdmi1", "usb"});
    p.mode = "audio_devices = " + cfg.str("audio_devices", "");
    return p;
  }
  std::string m = cfg.str("audio_output", "auto");
  std::transform(m.begin(), m.end(), m.begin(), ::tolower);
  if (m == "dac" || m == "dac+" || m == "rpi-dacplus") m = "dacplus";
  p.mode = "audio_output = " + m;
  if (m == "auto")         p.order = {"dacplus", "hdmi0", "hdmi1", "usb"};
  else if (m == "dacplus") { p.order = {"dacplus", "hdmi0", "hdmi1", "usb"}; p.wanted = "dacplus"; }
  else if (m == "hdmi")    p.order = {"hdmi0", "hdmi1"};
  else if (m == "hdmi0" || m == "hdmi1") { p.order = {m, m == "hdmi0" ? "hdmi1" : "hdmi0"}; }
  else if (m == "usb")     p.order = {"usb"};
  else if (m == "null")    p.order = {"null"};
  else { p.error = "ukjent audio_output «" + m + "», bruker auto"; p.mode = "audio_output = auto"; p.order = {"dacplus", "hdmi0", "hdmi1", "usb"}; }
  return p;
}

// Første utgang i planen som har et kort nå. "" = ingen.
inline std::string pickKind(const std::vector<std::string>& order, const std::vector<CardInfo>& cards,
                            const std::vector<std::string>& skip = {}) {
  for (auto& k : order) {
    if (std::find(skip.begin(), skip.end(), k) != skip.end()) continue;
    bool known = k == "dacplus" || k == "hdmi0" || k == "hdmi1" || k == "usb" || k == "null";
    if (!known || cardPresent(k, cards)) return k;   // rå ALSA-navn prøves bare
  }
  return "";
}

inline int kindRank(const std::vector<std::string>& order, const std::string& k) {
  auto it = std::find(order.begin(), order.end(), k);
  return it == order.end() ? 1000 : (int)(it - order.begin());
}

struct OutputDevice {
  std::string kind;   // dacplus, hdmi0, hdmi1, usb, null, eller rå ALSA-navn
  std::string pcm;    // ALSA-enhetsnavn
  std::string label;
  std::string card;   // ALSA-kort-id (for mikser), tom hvis ukjent
};

// Finn ALSA-navn for en ønsket utgang. Tom pcm = finnes ikke nå.
inline OutputDevice resolveDevice(const std::string& kind) {
  OutputDevice d{kind, "", kind, ""};
  if (fakeCardsFile()) {
    auto cards = listCards(); const CardInfo* c = nullptr;
    if (cardPresent(kind, cards, &c)) { d.pcm = "null"; d.label = "TEST " + kind; if (c && kind != "null") d.card = c->id; }
    return d;
  }
  if (kind == "hdmi0" || kind == "hdmi1") {
    std::string card = kind == "hdmi0" ? "vc4hdmi0" : "vc4hdmi1";
    if (snd_card_get_index(card.c_str()) >= 0) {
      d.pcm = "lyd_" + kind;            // fra /etc/alsa/conf.d/60-pi5-hdmi-lyd.conf (plug -> hdmi/iec958)
      snd_pcm_t* t;
      if (snd_pcm_open(&t, d.pcm.c_str(), SND_PCM_STREAM_PLAYBACK, SND_PCM_NONBLOCK) == 0) snd_pcm_close(t);
      else d.pcm = "default:CARD=" + card;   // alsa-lib sin vc4-hdmi.conf (plug+iec958)
      d.label = kind == "hdmi0" ? "HDMI0 (ved USB-C)" : "HDMI1";
      d.card = card;
    }
  } else if (kind == "dacplus") {
    auto cards = listCards(); const CardInfo* c = nullptr;
    if (cardPresent("dacplus", cards, &c) && c) {
      // plughw: PCM5122 tar S32_LE/S24_LE/S16_LE og 48 kHz direkte, så plug gjør normalt ingen konvertering.
      d.pcm = "plughw:CARD=" + c->id + ",DEV=0";
      d.label = "Raspberry Pi DAC+ (RCA/hodetelefon)";
      d.card = c->id;
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
          d.card = snd_ctl_card_info_get_id(info);
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

// DAC+: sett maskinvaremikseren til et kjent nivå. Uten dette avhenger nivået av hva
// driveren/alsactl tilfeldigvis har lagret. PCM5122:
//   «Digital»                  -103,5 … 0 dB (+24 dB bare med overlay-parameteren 24db_digital_gain)
//   «Analogue»                 -6 dB eller 0 dB (0 dB = 2 V RMS linjeutgang)
//   «Analogue Playback Boost»  0 eller +0,8 dB (holdes på 0, gir ellers klipping nær fullt utslag)
// Returnerer en kort beskrivelse for loggen.
inline std::string setupDacMixer(const std::string& cardId, double digitalDb) {
  snd_mixer_t* m = nullptr; std::string hw = "hw:CARD=" + cardId, out;
  if (snd_mixer_open(&m, 0) < 0) return "mikser: kunne ikke åpnes";
  if (snd_mixer_attach(m, hw.c_str()) < 0 || snd_mixer_selem_register(m, nullptr, nullptr) < 0 || snd_mixer_load(m) < 0) {
    snd_mixer_close(m); return "mikser: kunne ikke åpnes (" + hw + ")"; }
  auto find = [&](const char* name) { snd_mixer_selem_id_t* sid; snd_mixer_selem_id_alloca(&sid);
    snd_mixer_selem_id_set_index(sid, 0); snd_mixer_selem_id_set_name(sid, name); return snd_mixer_find_selem(m, sid); };
  char buf[160];
  if (auto e = find("Digital")) {
    long lo = 0, hi = 0; snd_mixer_selem_get_playback_dB_range(e, &lo, &hi);
    long want = std::clamp((long)std::lround(digitalDb * 100.0), lo, hi);
    snd_mixer_selem_set_playback_dB_all(e, want, -1);
    if (snd_mixer_selem_has_playback_switch(e)) snd_mixer_selem_set_playback_switch_all(e, 1);
    long got = 0; snd_mixer_selem_get_playback_dB(e, SND_MIXER_SCHN_FRONT_LEFT, &got);
    snprintf(buf, sizeof buf, "Digital %.1f dB (på)", got / 100.0); out += buf;
  } else out += "Digital: finnes ikke";
  if (auto e = find("Analogue")) {   // maks = 0 dB
    long lo = 0, hi = 0; snd_mixer_selem_get_playback_volume_range(e, &lo, &hi);
    snd_mixer_selem_set_playback_volume_all(e, hi); out += ", Analogue 0 dB";
  }
  if (auto e = find("Analogue Playback Boost")) {
    long lo = 0, hi = 0; snd_mixer_selem_get_playback_volume_range(e, &lo, &hi);
    snd_mixer_selem_set_playback_volume_all(e, lo); out += ", Boost 0 dB";
  }
  snd_mixer_close(m);
  return "mikser: " + out;
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
