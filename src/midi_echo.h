// Kort vindu der innkommende noter med samme notenummer ignoreres,
// så et ekko av våre egne pad-LED-meldinger ikke trykker på padden på nytt.
#pragma once
#include <atomic>
#include <cstdint>
#include <time.h>

namespace ju6 {

class LedEcho {
public:
  void arm(int note) {
    if (note < 0 || note > 127) return;
    mUntil[note].store(nowNs() + 80000000LL, std::memory_order_release);   // 80 ms
  }
  bool drop(int note) const {
    if (note < 0 || note > 127) return false;
    return nowNs() < mUntil[note].load(std::memory_order_acquire);
  }
private:
  static int64_t nowNs() {
    timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec;
  }
  std::atomic<int64_t> mUntil[128]{};
};

} // namespace ju6
