// JU-6 Pi – patchbank (128 plasser, A11–B88) i Juno-106-sysex-format.
#pragma once
#include "util.h"
#include "synth.h"
#include "factory_bank.h"

namespace ju6 {

inline std::string slotName(int slot) {   // 0..127 -> "A11".."B88"
  char b[8]; snprintf(b, sizeof b, "%c%d%d", slot < 64 ? 'A' : 'B', (slot % 64) / 8 + 1, slot % 8 + 1);
  return b;
}

struct Bank {
  Patch patch[128];
  std::string name[128];
  bool user[128] = {};

  void loadFactory() {
    for (int i = 0; i < 128; i++) {
      std::memcpy(patch[i].d, kFactoryBank[i].data, 18); patch[i].ext = 0;
      name[i] = kFactoryBank[i].name; user[i] = false;
    }
  }

  // Leser alle Juno-106 APR-meldinger (F0 41 30/31 0n pp ... F7) fra en .syx-fil.
  // Patchnummeret pp bestemmer plassen. Returnerer antall patcher lest.
  int loadSyx(const std::string& path) {
    std::vector<uint8_t> f;
    if (!readFile(path, f)) return 0;
    int n = 0;
    for (size_t i = 0; i + 23 < f.size(); i++) {
      if (f[i] == 0xF0 && f[i + 1] == 0x41 && (f[i + 2] == 0x30 || f[i + 2] == 0x31) && f[i + 23] == 0xF7) {
        int slot = f[i + 4] & 0x7F;
        bool ok = true;
        for (int k = 0; k < 18; k++) if (f[i + 5 + k] & 0x80) ok = false;
        if (!ok) continue;
        if (std::memcmp(patch[slot].d, &f[i + 5], 18) != 0) { user[slot] = true; name[slot] = slotName(slot) + " Egen"; }
        std::memcpy(patch[slot].d, &f[i + 5], 18);
        n++; i += 23;
      }
    }
    // Navnefil (valgfri): "A11<TAB>Navn[<TAB>ext]" per linje (ext = JU-6 Pi-utvidelse, se Patch)
    std::ifstream nf(path.substr(0, path.find_last_of('/') + 1) + "names.txt");
    std::string line;
    while (std::getline(nf, line)) {
      auto t = line.find('\t'); if (t == std::string::npos || t < 3) continue;
      std::string s = line.substr(0, t);
      std::string rest = line.substr(t + 1); int ext = 0;
      auto t2 = rest.find('\t'); if (t2 != std::string::npos) { ext = std::atoi(rest.c_str() + t2 + 1); rest.resize(t2); }
      for (int k = 0; k < 128; k++) if (slotName(k) == s) { name[k] = s + " " + rest; patch[k].ext = (uint8_t)(ext & 3); }
    }
    return n;
  }

  std::vector<uint8_t> toSyx(int channel = 0) const {
    std::vector<uint8_t> out;
    for (int i = 0; i < 128; i++) {
      out.insert(out.end(), { 0xF0, 0x41, 0x30, (uint8_t)(channel & 15), (uint8_t)i });
      out.insert(out.end(), patch[i].d, patch[i].d + 18);
      out.push_back(0xF7);
    }
    return out;
  }
  bool save(const std::string& dir) const {
    auto s = toSyx();
    std::string names;
    for (int i = 0; i < 128; i++) if (user[i]) {
      names += slotName(i) + "\t" + name[i].substr(name[i].find(' ') + 1);
      if (patch[i].ext) names += "\t" + std::to_string(patch[i].ext);
      names += "\n";
    }
    return atomicWrite(dir + "/patches.syx", s.data(), s.size()) &&
           atomicWrite(dir + "/names.txt", names.data(), names.size());
  }
};

} // namespace ju6
