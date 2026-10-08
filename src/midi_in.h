#pragma once
#include "util.h"
#include <thread>

namespace ju6 {
// ALSA-sequencer: kobler seg automatisk til alle MIDI-kilder (også de som plugges
// inn senere) og legger hendelsene i en lås-fri kø til lydtråden.
class MidiIn {
public:
  using Queue = SpscQueue<MidiEvent, 1024>;
  explicit MidiIn(Queue& q) : mQ(q) {}
  ~MidiIn() { stop(); }
  void start();
  void stop();
  int connectedCount() const { return mConnected.load(); }
private:
  void run();
  Queue& mQ;
  std::thread mThread;
  std::atomic<bool> mRun{false};
  std::atomic<int> mConnected{0};
};
}
