// JU-6 Pi – små hjelpere: lås-fri kø, konfig, lagring, logging, LED.
#pragma once
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdarg>
#include <cstring>
#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <time.h>

namespace ju6 {

inline void logf(const char* fmt, ...) {
  char buf[512];
  va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap);
  fprintf(stderr, "ju6pi: %s\n", buf);
}

inline double nowSec() {
  timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
  return ts.tv_sec + ts.tv_nsec * 1e-9;
}

// Én produsent, én konsument, uten låser (trygt mellom MIDI-, lyd- og kontrolltråd).
template <typename T, size_t N>
class SpscQueue {
  static_assert((N & (N - 1)) == 0, "N må være 2^k");
public:
  bool push(const T& v) {
    size_t h = mHead.load(std::memory_order_relaxed);
    if (h - mTail.load(std::memory_order_acquire) >= N) return false;
    mBuf[h & (N - 1)] = v;
    mHead.store(h + 1, std::memory_order_release);
    return true;
  }
  bool pop(T& v) {
    size_t t = mTail.load(std::memory_order_relaxed);
    if (t == mHead.load(std::memory_order_acquire)) return false;
    v = mBuf[t & (N - 1)];
    mTail.store(t + 1, std::memory_order_release);
    return true;
  }
private:
  T mBuf[N];
  std::atomic<size_t> mHead{0}, mTail{0};
};

// MIDI-hendelse fra sequencer-tråden til lydtråden.
struct MidiEvent {
  enum Type : uint8_t { NoteOn, NoteOff, CC, Bend, Program, Sysex, Reset } type;
  uint8_t ch = 0, d1 = 0, d2 = 0;
  int16_t bend = 0;
  uint8_t sxLen = 0;
  uint8_t sx[30] = {};   // Juno-106-sysex er maks 24 byte
};

// Enkel "nøkkel = verdi"-konfig med #-kommentarer.
struct Config {
  std::map<std::string, std::string> kv;
  bool load(const std::string& path) {
    std::ifstream f(path);
    if (!f) return false;
    std::string line;
    while (std::getline(f, line)) {
      auto h = line.find('#'); if (h != std::string::npos) line.resize(h);
      auto e = line.find('='); if (e == std::string::npos) continue;
      auto trim = [](std::string s) {
        s.erase(0, s.find_first_not_of(" \t\r")); s.erase(s.find_last_not_of(" \t\r") + 1); return s; };
      kv[trim(line.substr(0, e))] = trim(line.substr(e + 1));
    }
    return true;
  }
  std::string str(const std::string& k, const std::string& d) const {
    auto it = kv.find(k); return it == kv.end() || it->second.empty() ? d : it->second; }
  int num(const std::string& k, int d) const {
    auto it = kv.find(k); if (it == kv.end()) return d;
    try { return std::stoi(it->second); } catch (...) { return d; } }
  double real(const std::string& k, double d) const {
    auto it = kv.find(k); if (it == kv.end()) return d;
    try { return std::stod(it->second); } catch (...) { return d; } }
  bool flag(const std::string& k, bool d) const {
    auto s = str(k, d ? "on" : "off");
    return s == "on" || s == "1" || s == "yes" || s == "ja" || s == "true" || s == "på"; }
  std::vector<int> list(const std::string& k, std::vector<int> d) const {
    auto it = kv.find(k); if (it == kv.end()) return d;
    std::vector<int> v; std::string s = it->second;
    std::replace(s.begin(), s.end(), ',', ' ');
    std::istringstream is(s); int x; while (is >> x) v.push_back(x);
    return v.empty() ? d : v; }
  std::vector<std::string> words(const std::string& k, std::vector<std::string> d) const {
    auto it = kv.find(k); if (it == kv.end()) return d;
    std::vector<std::string> v; std::string s = it->second;
    std::replace(s.begin(), s.end(), ',', ' ');
    std::istringstream is(s); std::string w; while (is >> w) v.push_back(w);
    return v.empty() ? d : v; }
};

// Strømbruddsikker skriving: tmp-fil, fsync, rename, fsync av katalogen.
inline bool atomicWrite(const std::string& path, const void* data, size_t len) {
  std::string tmp = path + ".tmp";
  int fd = ::open(tmp.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (fd < 0) return false;
  const uint8_t* p = (const uint8_t*)data; size_t left = len;
  while (left) { ssize_t w = ::write(fd, p, left); if (w <= 0) { ::close(fd); return false; } p += w; left -= w; }
  ::fsync(fd); ::close(fd);
  if (::rename(tmp.c_str(), path.c_str()) != 0) return false;
  std::string dir = path.substr(0, path.find_last_of('/'));
  int dfd = ::open(dir.empty() ? "." : dir.c_str(), O_RDONLY | O_DIRECTORY);
  if (dfd >= 0) { ::fsync(dfd); ::close(dfd); }
  return true;
}

inline bool readFile(const std::string& path, std::vector<uint8_t>& out) {
  std::ifstream f(path, std::ios::binary); if (!f) return false;
  out.assign(std::istreambuf_iterator<char>(f), {}); return true;
}

// ACT-LED på Pi (grønn). Tjenesten gir skrivetilgang i ExecStartPre.
class Led {
public:
  explicit Led(std::string base = "/sys/class/leds/ACT") : mBase(std::move(base)) {}
  void trigger(const char* t) { put("trigger", t); }
  void set(bool on) { put("brightness", on ? "1" : "0"); }
  bool available() const { return access((mBase + "/brightness").c_str(), W_OK) == 0; }
private:
  void put(const char* f, const char* v) {
    int fd = ::open((mBase + "/" + f).c_str(), O_WRONLY);
    if (fd >= 0) { ssize_t r = ::write(fd, v, strlen(v)); (void)r; ::close(fd); }
  }
  std::string mBase;
};

} // namespace ju6
