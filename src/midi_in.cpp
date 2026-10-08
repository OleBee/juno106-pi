#include "midi_in.h"
#include <alsa/asoundlib.h>
#include <poll.h>
#include <pthread.h>
#include <set>

namespace ju6 {

static void quietAlsaError(const char*, int, const char*, int, const char*, ...) {}


void MidiIn::start() {
  mRun = true;
  // ALSA-biblioteket skriver ellers en linje til stderr for hvert mislykket forsøk (journal-støy).
  snd_lib_error_set_handler(quietAlsaError);
  mThread = std::thread([this] { run(); });
}
void MidiIn::stop() {
  if (!mRun.exchange(false)) return;
  if (mThread.joinable()) mThread.join();
}

static bool wantPort(snd_seq_t* seq, int myClient, snd_seq_port_info_t* pinfo) {
  int client = snd_seq_port_info_get_client(pinfo);
  if (client == myClient || client == SND_SEQ_CLIENT_SYSTEM) return false;
  unsigned caps = snd_seq_port_info_get_capability(pinfo);
  if ((caps & (SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ)) !=
      (SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ)) return false;
  if (caps & SND_SEQ_PORT_CAP_NO_EXPORT) return false;
  snd_seq_client_info_t* cinfo; snd_seq_client_info_alloca(&cinfo);
  if (snd_seq_get_any_client_info(seq, client, cinfo) == 0) {
    const char* name = snd_seq_client_info_get_name(cinfo);
    if (name && strstr(name, "Midi Through")) return false;   // unngå løkker
  }
  unsigned type = snd_seq_port_info_get_type(pinfo);
  return (type & (SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_HARDWARE |
                  SND_SEQ_PORT_TYPE_PORT | SND_SEQ_PORT_TYPE_APPLICATION)) != 0;
}

void MidiIn::run() {
  sched_param sp{}; sp.sched_priority = 70;
  pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);   // feiler stille uten rettigheter
  pthread_setname_np(pthread_self(), "ju6-midi");

  while (mRun) {
    snd_seq_t* seq = nullptr;
    if (snd_seq_open(&seq, "default", SND_SEQ_OPEN_INPUT, SND_SEQ_NONBLOCK) < 0) {
      static bool warned = false;
      if (!warned) { logf("MIDI: fant ikke ALSA-sequencer, prøver igjen"); warned = true; }
      for (int i = 0; i < 20 && mRun; i++) usleep(100000);
      continue;
    }
    snd_seq_set_client_name(seq, "JU-6 Pi");
    int myClient = snd_seq_client_id(seq);
    int port = snd_seq_create_simple_port(seq, "JU-6 Pi inn",
        SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE,
        SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_SYNTHESIZER | SND_SEQ_PORT_TYPE_APPLICATION);
    snd_seq_connect_from(seq, port, SND_SEQ_CLIENT_SYSTEM, SND_SEQ_PORT_SYSTEM_ANNOUNCE);

    std::set<std::pair<int,int>> connected;
    auto tryConnect = [&](int client, int p) {
      snd_seq_port_info_t* pinfo; snd_seq_port_info_alloca(&pinfo);
      if (snd_seq_get_any_port_info(seq, client, p, pinfo) < 0) return;
      if (!wantPort(seq, myClient, pinfo)) return;
      if (connected.count({client, p})) return;
      if (snd_seq_connect_from(seq, port, client, p) == 0) {
        connected.insert({client, p});
        mConnected = (int)connected.size();
        logf("MIDI: koblet til %d:%d %s", client, p, snd_seq_port_info_get_name(pinfo));
      }
    };
    // Koble til alt som finnes nå.
    {
      snd_seq_client_info_t* cinfo; snd_seq_client_info_alloca(&cinfo);
      snd_seq_port_info_t* pinfo; snd_seq_port_info_alloca(&pinfo);
      snd_seq_client_info_set_client(cinfo, -1);
      while (snd_seq_query_next_client(seq, cinfo) >= 0) {
        int c = snd_seq_client_info_get_client(cinfo);
        snd_seq_port_info_set_client(pinfo, c);
        snd_seq_port_info_set_port(pinfo, -1);
        while (snd_seq_query_next_port(seq, pinfo) >= 0) tryConnect(c, snd_seq_port_info_get_port(pinfo));
      }
    }

    int npfd = snd_seq_poll_descriptors_count(seq, POLLIN);
    std::vector<pollfd> pfd(npfd);
    snd_seq_poll_descriptors(seq, pfd.data(), npfd, POLLIN);
    std::vector<uint8_t> sysexBuf;
    bool alive = true;

    while (mRun && alive) {
      if (poll(pfd.data(), npfd, 200) <= 0) continue;
      snd_seq_event_t* ev = nullptr;
      int r;
      while ((r = snd_seq_event_input(seq, &ev)) >= 0 && ev) {
        MidiEvent m{};
        bool send = true;
        switch (ev->type) {
          case SND_SEQ_EVENT_NOTEON:
            m.type = ev->data.note.velocity ? MidiEvent::NoteOn : MidiEvent::NoteOff;
            m.ch = ev->data.note.channel; m.d1 = ev->data.note.note; m.d2 = ev->data.note.velocity; break;
          case SND_SEQ_EVENT_NOTEOFF:
            m.type = MidiEvent::NoteOff; m.ch = ev->data.note.channel; m.d1 = ev->data.note.note; break;
          case SND_SEQ_EVENT_CONTROLLER:
            m.type = MidiEvent::CC; m.ch = ev->data.control.channel;
            m.d1 = (uint8_t)ev->data.control.param; m.d2 = (uint8_t)ev->data.control.value; break;
          case SND_SEQ_EVENT_PITCHBEND:
            m.type = MidiEvent::Bend; m.ch = ev->data.control.channel;
            m.bend = (int16_t)(ev->data.control.value + 8192); break;
          case SND_SEQ_EVENT_PGMCHANGE:
            m.type = MidiEvent::Program; m.ch = ev->data.control.channel; m.d1 = (uint8_t)ev->data.control.value; break;
          case SND_SEQ_EVENT_SYSEX: {
            const uint8_t* d = (const uint8_t*)ev->data.ext.ptr;
            for (unsigned i = 0; i < ev->data.ext.len; i++) {
              if (d[i] == 0xF0) sysexBuf.clear();
              else if (d[i] == 0xF7) {
                if (!sysexBuf.empty() && sysexBuf.size() <= sizeof(m.sx)) {
                  MidiEvent s{}; s.type = MidiEvent::Sysex; s.sxLen = (uint8_t)sysexBuf.size();
                  memcpy(s.sx, sysexBuf.data(), sysexBuf.size()); mQ.push(s);
                }
                sysexBuf.clear();
              } else if (sysexBuf.size() < 64) sysexBuf.push_back(d[i]);
            }
            send = false; break;
          }
          case SND_SEQ_EVENT_PORT_START:
          case SND_SEQ_EVENT_CLIENT_START:
            if (ev->type == SND_SEQ_EVENT_PORT_START) tryConnect(ev->data.addr.client, ev->data.addr.port);
            else {
              snd_seq_port_info_t* pinfo; snd_seq_port_info_alloca(&pinfo);
              snd_seq_port_info_set_client(pinfo, ev->data.addr.client);
              snd_seq_port_info_set_port(pinfo, -1);
              while (snd_seq_query_next_port(seq, pinfo) >= 0)
                tryConnect(ev->data.addr.client, snd_seq_port_info_get_port(pinfo));
            }
            send = false; break;
          case SND_SEQ_EVENT_PORT_EXIT:
          case SND_SEQ_EVENT_CLIENT_EXIT: {
            int c = ev->data.addr.client;
            for (auto it = connected.begin(); it != connected.end();)
              if (it->first == c && (ev->type == SND_SEQ_EVENT_CLIENT_EXIT || it->second == ev->data.addr.port)) {
                logf("MIDI: %d:%d koblet fra", it->first, it->second); it = connected.erase(it);
              } else ++it;
            mConnected = (int)connected.size();
            if (connected.empty()) { MidiEvent rst{}; rst.type = MidiEvent::Reset; mQ.push(rst); }  // ingen hengende toner
            send = false; break;
          }
          default: send = false; break;
        }
        if (send) mQ.push(m);
      }
      if (r < 0 && r != -EAGAIN && r != -ENOSPC) { logf("MIDI: feil %s, starter på nytt", snd_strerror(r)); alive = false; }
    }
    snd_seq_close(seq);
    mConnected = 0;
  }
}

} // namespace ju6
