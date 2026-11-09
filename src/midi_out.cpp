#include "midi_out.h"
#include <alsa/asoundlib.h>
#include <pthread.h>
#include <cctype>
#include <cstring>
#include <set>

namespace ju6 {

static bool nameHas(const char* name, const char* needle) {
  if (!name || !needle) return false;
  std::string a = name, b = needle;
  for (char& c : a) c = (char)std::tolower((unsigned char)c);
  for (char& c : b) c = (char)std::tolower((unsigned char)c);
  return a.find(b) != std::string::npos;
}

// 5-pins-brua på MPK mini Plus (port «MIDI 2») skal ikke få pad-noter.
static bool isDinBridge(const char* name) {
  return nameHas(name, "midi 2") || nameHas(name, "din") || nameHas(name, "midi2");
}

void MidiOut::start() {
  mRun = true;
  mThread = std::thread([this] { run(); });
}
void MidiOut::stop() {
  if (!mRun.exchange(false)) return;
  if (mThread.joinable()) mThread.join();
}

void MidiOut::sendNote(int channel, int note, int velocity) {
  if (note < 0 || note > 127 || channel < 0 || channel > 15) return;
  Msg m{ (uint8_t)channel, (uint8_t)note, (uint8_t)std::clamp(velocity, 0, 127) };
  mQ.push(m);
}

void MidiOut::run() {
  pthread_setname_np(pthread_self(), "ju6-midiout");
  while (mRun) {
    snd_seq_t* seq = nullptr;
    if (snd_seq_open(&seq, "default", SND_SEQ_OPEN_OUTPUT, 0) < 0) {
      for (int i = 0; i < 20 && mRun; i++) usleep(100000);
      continue;
    }
    snd_seq_set_client_name(seq, "JU-6 Pi LED");
    int myClient = snd_seq_client_id(seq);
    int port = snd_seq_create_simple_port(seq, "JU-6 Pi pad-LED",
        SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ,
        SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_APPLICATION);
    std::set<std::pair<int,int>> connected;
    double nextScan = 0;
    while (mRun) {
      double t = nowSec();
      if (t >= nextScan) {
        nextScan = t + 1.0;
        snd_seq_client_info_t* cinfo; snd_seq_client_info_alloca(&cinfo);
        snd_seq_port_info_t* pinfo; snd_seq_port_info_alloca(&pinfo);
        snd_seq_client_info_set_client(cinfo, -1);
        while (snd_seq_query_next_client(seq, cinfo) >= 0) {
          int c = snd_seq_client_info_get_client(cinfo);
          if (c == myClient || c == SND_SEQ_CLIENT_SYSTEM) continue;
          const char* cname = snd_seq_client_info_get_name(cinfo);
          if (cname && strstr(cname, "Midi Through")) continue;
          if (!mAny && !nameHas(cname, "mpk")) continue;
          snd_seq_port_info_set_client(pinfo, c);
          snd_seq_port_info_set_port(pinfo, -1);
          while (snd_seq_query_next_port(seq, pinfo) >= 0) {
            unsigned caps = snd_seq_port_info_get_capability(pinfo);
            if ((caps & (SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE)) !=
                (SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE)) continue;
            const char* pname = snd_seq_port_info_get_name(pinfo);
            if (isDinBridge(pname) || isDinBridge(cname)) continue;
            int p = snd_seq_port_info_get_port(pinfo);
            if (connected.count({c, p})) continue;
            if (snd_seq_connect_to(seq, port, c, p) == 0) {
              connected.insert({c, p});
              mTargets = (int)connected.size();
              logf("pad-LED: sender til %d:%d %s", c, p, pname ? pname : "");
            }
          }
        }
      }
      Msg m;
      bool sent = false;
      while (mQ.pop(m)) {
        snd_seq_event_t ev;
        snd_seq_ev_clear(&ev);
        snd_seq_ev_set_source(&ev, port);
        snd_seq_ev_set_subs(&ev);
        snd_seq_ev_set_direct(&ev);
        if (m.vel == 0) snd_seq_ev_set_noteoff(&ev, m.ch, m.note, 0);
        else snd_seq_ev_set_noteon(&ev, m.ch, m.note, m.vel);
        snd_seq_event_output_direct(seq, &ev);
        mEcho.arm(m.note);
        sent = true;
      }
      if (!sent) usleep(4000);
    }
    snd_seq_close(seq);
    mTargets = 0;
    connected.clear();
  }
}

} // namespace ju6
