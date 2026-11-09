// MIDI ut til AKAI MPK mini Plus: pad-LED som Note On/Off.
// Bruksanvisningen til MPK mini Plus (v1.2) beskriver bare farger lagret i
// programmet (On/Off Color 0–31). Den beskriver ikke sanntids-feedback.
// JU-6 Pi sender likevel Note On på pad-kanalen, med velocity som rød styrke
// (0 = Note Off). Det er samme familie som den første MPK mini (note styrer
// den røde LED-en) og MPD-ene (note-on velocity = farge). IKKE VERIFISERT
// på ekte MPK mini Plus. Meldinger går bare til porter hvis navn inneholder
// "MPK", og aldri til "MIDI 2" (5-pins-brua). pad_leds = any sender til alle
// skrivbare porter unntatt MIDI 2. pad_leds = off sender ingenting.
#pragma once
#include "midi_echo.h"
#include "util.h"
#include <thread>

namespace ju6 {

class MidiOut {
public:
  MidiOut(LedEcho& echo, bool anyDevice) : mEcho(echo), mAny(anyDevice) {}
  ~MidiOut() { stop(); }
  void start();
  void stop();
  // velocity 0 = Note Off. channel er 0-basert.
  void sendNote(int channel, int note, int velocity);
  int targets() const { return mTargets.load(); }
private:
  void run();
  LedEcho& mEcho;
  bool mAny;
  struct Msg { uint8_t ch, note, vel; };
  SpscQueue<Msg, 256> mQ;
  std::thread mThread;
  std::atomic<bool> mRun{false};
  std::atomic<int> mTargets{0};
};

} // namespace ju6
