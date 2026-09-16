# Running on a Raspberry Pi 5

Written for this hackathon, not part of the upstream SDK documentation. The
[FAQ](faq.md) covers the SDK itself; this page covers the Pi around it.

## Picking the right package

A Pi 5 runs 64-bit ARM, so you want the packages whose names end in
`linux-arm64`. The `linux-x86_64` builds will not load, and the error you get is
a dynamic loader complaint rather than anything about architecture. Check with
`uname -m`, which should print `aarch64`.

Unpack each `.tar.gz` into its own directory. The demos expect a layout like
this, under `~/abr-packages` by default:

```text
~/abr-packages/
  niagara-38m-live.en-linux-arm64/   ASR library plus model blobs
  nith-5m-live.en-f1-linux-arm64/    TTS, female voice
  nith-5m-live.en-m1-linux-arm64/    TTS, male voice
```

To use a different directory, edit `ABR_PACKAGES_ROOT` near the top of each
demo script.

## Audio

Audio is where most of the first hour goes. A few things to know.

**The Pi has no microphone.** You need a USB microphone or a USB headset. Run
`arecord -l` to confirm the kernel sees it. If nothing is listed, the device is
not enumerating and no amount of software configuration will help.

**Output goes somewhere you did not expect.** A Pi 5 can play through HDMI or a
USB or Bluetooth device. There is no 3.5 mm jack on the Pi 5, unlike earlier
models. Pick the default with `raspi-config` under System Options, or list what
is available with `aplay -l`.

**Device indices move.** Both demos accept `--list-devices` to print what
`sounddevice` sees, and `--input-device N` to pin one. Prefer a `plughw:` device
over a raw `hw:` device, because `plughw` will resample and reformat for you
while `hw` fails outright if the rate does not match.

**PortAudio must be installed.** The Python `sounddevice` package is a binding,
not an implementation:

```bash
sudo apt install -y libportaudio2
```

**Everything is 16 kHz mono.** The ASR takes signed 16-bit little-endian PCM at
16 kHz mono, and the TTS produces the same. If a transcript comes back as
gibberish rather than empty, a format mismatch is the first thing to suspect.
See [ASR input format](asr/input-format.md).

**Test without a microphone.** The `samples/` directory holds two clips in the
right format, so you can prove the ASR works before debugging capture.

## GPIO

The LED demo uses `gpiozero`, whose backend on a Pi 5 is `lgpio`. The Pi 5
changed its GPIO hardware, so backends that worked on a Pi 4 may not work here.
Installing `lgpio` compiles a native extension, which needs `swig`:

```bash
sudo apt install -y swig
```

Pin numbers in the demo are BCM numbering, not physical pin positions. Wire each
LED through a current-limiting resistor of roughly 330 ohms. Driving an LED
directly from a pin without one will eventually damage the pin.

## Performance

The models are small enough to run comfortably on a Pi 5, but a few things help:

- Use a good power supply. An undervolted Pi throttles, and throttling shows up
  as audio dropouts and latency spikes rather than an obvious error. Check with
  `vcgencmd get_throttled`, which should print `throttled=0x0`.
- Keep it cool. A Pi 5 under sustained load without a heatsink or fan will
  thermal throttle.
- The ASR has a fast mode and an accurate mode. See
  [Transcription stages](asr/transcription-stages.md) for the trade-off, and
  [Benchmarking](asr/benchmarking.md) for how to measure it on your own hardware.

## First run is slow

Both demos are single-file scripts with inline dependency metadata, so `uv`
builds an environment the first time you run one. That download and build takes
a while, especially `lgpio`, which compiles from source. Subsequent runs reuse
the cached environment and start quickly.

## Licensing

Activation needs network access and happens once per device:

```bash
abr-sdk activate ~/abr-packages/niagara-38m-live.en-linux-arm64/libniagara_38m_live.so \
  --key-file abr_license.key
```

Inference is fully offline afterwards. You point the command at some package's
`.so` because part of the check lives in the compiled library, but the license
is device-wide: any package works, and packages you unpack later need nothing.
The license lands in `~/.local/state/abr-sdk/license`. See [License activation](getting-started/license-activation.md).
