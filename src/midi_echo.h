// Kort vindu der et ekko av våre egne pad-LED-meldinger ignoreres,
// så det ikke trykker på padden på nytt.
// Vinduet gjelder bare pad-kanalen og bare den noten som nettopp ble sendt.
// Samme notenummer på en annen kanal (lave tangenter, C2 = 36) og andre
// pad-noter slipper igjennom.
#pragma once
#include <atomic>
#include <cstdint>
#include <time.h>

namespace ju6 {

class LedEcho {
public:
  void arm(int channel, int note) {
    if (note < 0 || note > 127 || channel < 0 || channel > 15) return;
    mCh[note].store(channel, std::memory_order_relaxed);
    mUntil[note].store(nowNs() + 80000000LL, std::memory_order_release);   // 80 ms
  }
  bool drop(int channel, int note) const {
    if (note < 0 || note > 127 || channel < 0 || channel > 15) return false;
    int64_t until = mUntil[note].load(std::memory_order_acquire);
    if (nowNs() >= until) return false;
    return mCh[note].load(std::memory_order_relaxed) == channel;
  }
private:
  static int64_t nowNs() {
    timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec;
  }
  std::atomic<int64_t> mUntil[128]{};
  std::atomic<int> mCh[128]{};
};

} // namespace ju6
