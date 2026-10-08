# JU-6 Pi
CXX      ?= g++
CXXFLAGS ?= -O3 -ffast-math -fno-finite-math-only
CXXFLAGS += -std=c++17 -Wall -Wno-unused-variable -Wno-unused-but-set-variable -pthread
LDLIBS   += -lasound -pthread
SRC = src/main.cpp src/midi_in.cpp
HDR = $(wildcard src/*.h third_party/kr106/DSP/*.h)

all: build/ju6pi

build/ju6pi: $(SRC) $(HDR)
	@mkdir -p build
	$(CXX) $(CXXFLAGS) $(SRC) -o $@ $(LDLIBS)

# Krysskompilering for Raspberry Pi 5 (Cortex-A76)
arm64: build/ju6pi-arm64
build/ju6pi-arm64: $(SRC) $(HDR)
	@mkdir -p build
	aarch64-linux-gnu-g++ $(CXXFLAGS) -mcpu=cortex-a76 $(SRC) -o $@ $(LDLIBS)
	aarch64-linux-gnu-strip $@

samples: build/ju6pi
	@mkdir -p samples
	./build/ju6pi demo samples

clean:
	rm -rf build
.PHONY: all arm64 samples clean
