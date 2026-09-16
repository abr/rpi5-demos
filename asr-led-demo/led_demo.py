#!/usr/bin/env -S env -u UV_NO_SYNC uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "abr-sdk",
#     "sounddevice",
#     "scipy",
#     "numpy",
#     "gpiozero",
#     "lgpio",
# ]
# ///
"""Control GPIO LEDs with your voice — ABR ASR, no cloud involved.

The mic is always listening; there is no start/stop step. Audio is streamed
into the ASR continuously and transcribed as it arrives, and each LED
reacts as soon as a colour word and an on/off/blink word appear together.

    1. LISTEN     microphone, continuously                   (sounddevice)
    2. TRANSCRIBE speech -> text, streaming                  (ABR niagara ASR)
    3. ACT        colour + action words heard -> drive an LED (gpiozero)

Everything runs locally and offline (after the one-time ABR activation below).

Say the colour before the action, e.g.:
    "red on"
    "blue blink"
    "all lights off"

Usage (uv resolves and caches the dependencies above automatically):
    uv run led_demo.py                    # start listening, Ctrl+C to quit
    uv run led_demo.py --list-devices     # print audio devices, then exit
    uv run led_demo.py --input-device 7   # use a specific microphone

or, since the shebang invokes `uv run --script`, directly:
    ./led_demo.py

Say "quit" or "exit" at any time to stop the program, same as Ctrl+C.
Say "reset" or "clear" to bail out of a command said by mistake.

One-time setup:

  * ABR library must be activated once (needs a license key and network
    access; ASR afterwards runs offline):

        abr-sdk activate niagara-38m-live.en-linux-arm64/libniagara_38m_live.so   --key-file abr_license.key

  * Wire an LED (with a current-limiting resistor) from each pin in LED_PINS
    below to ground, and update the pin numbers to match your wiring.
"""
from __future__ import annotations

import argparse
import queue
import re
import sys
import time
from collections import deque
from math import gcd
from pathlib import Path

import numpy as np
import sounddevice as sd
from gpiozero import LED
from scipy.signal import resample_poly

from abr_sdk.asr import Asr, AsrChunk

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
# Root folder for abr-packages (defaults to "~/abr-packages"), update as necessary.
ABR_PACKAGES_ROOT = Path.home() / "abr-packages"
ASR_LIB = ABR_PACKAGES_ROOT / "niagara-38m-live.en-linux-arm64" / "libniagara_38m_live.so"

# BCM GPIO pin for each LED. Update these to match your wiring. Each key
# doubles as the word the voice reactor listens for.
LED_PINS = {
    "red": 17,
    "green": 27,
    "blue": 22,
}

# How fast a "blink" command flashes an LED, in seconds per on/off phase.
BLINK_PERIOD_S = 0.5

# The ABR ASR engine speaks only one audio format: 16 kHz, mono,
# signed 16-bit little-endian PCM. We convert to it as audio is captured.
SAMPLE_RATE = 16_000

# Saying any of these words stops the program, same as Ctrl+C.
QUIT_WORDS = {"quit", "exit"}

# Saying any of these words clears the trailing word window without
# stopping the program, e.g. to bail out of a command said by mistake.
RESET_WORDS = {"reset", "clear"}

# A colour+action combo is recognized if both appear within this many of the
# most recently heard words.
RECENT_WINDOW = 8

# How long the trailing (possibly still-being-recognized) word must go
# unchanged before it's treated as finished, e.g. after a pause with nothing
# following it (see VoiceCommandReactor).
SEAL_TIMEOUT_S = 0.2

ALL_WORDS = {"all", "everything", "every", "light", "lights", "leds"}
ON_WORDS = {"on", "activate", "enable"}
OFF_WORDS = {"off", "deactivate", "disable", "stop"}
BLINK_WORDS = {"blink", "blinking", "flash", "flashing"}

# --------------------------------------------------------------------------- #
# LEDs
# --------------------------------------------------------------------------- #
class LedBoard:
    """The set of LEDs this demo controls, one gpiozero.LED per colour."""

    def __init__(self, pins: dict[str, int]) -> None:
        self.leds = {name: LED(pin) for name, pin in pins.items()}

    def apply(self, colours: list[str], action: str) -> None:
        for name in colours:
            led = self.leds[name]
            if action == "on":
                led.on()
            elif action == "off":
                led.off()
            elif action == "blink":
                led.blink(on_time=BLINK_PERIOD_S, off_time=BLINK_PERIOD_S)

    def close(self) -> None:
        for led in self.leds.values():
            led.close()


# --------------------------------------------------------------------------- #
# ASR -> LEDs: react to colour+action words as the transcript streams in
# --------------------------------------------------------------------------- #
class VoiceCommandReactor:
    """Watches a live-growing ASR transcript and drives LEDs on voice commands.

    Feed ABR `AsrChunk`s to :meth:`on_chunk` (e.g. as the `on_chunk` callback
    of `Asr.push`). There are no utterance boundaries in a continuous stream,
    so instead of parsing one command per recording, this keeps a trailing
    window of the last `RECENT_WINDOW` words; once that window contains both
    an on/off/blink word and either a colour word or a word from
    `ALL_WORDS` (meaning every LED), the action fires and the window is
    cleared so the same words don't immediately refire it. Commands should
    name the colour (or an `ALL_WORDS` word) before the action word, e.g.
    "red on" rather than "turn on red" -- an action word alone, with no
    colour or `ALL_WORDS` word yet, just keeps listening rather than
    defaulting to every LED. Hearing a
    word in `QUIT_WORDS` sets `stop_requested`, which the caller should
    poll to end the session; hearing a word in `RESET_WORDS` instead just
    clears the window, e.g. to bail out of a command said by mistake
    without ending the session.

    A chunk's text can end mid-word (e.g. "li" on its way to becoming
    "light"), so the trailing word in the buffer is never immediately fed
    into the trigger window -- it's held as "pending" until something else
    confirms it: either more text is appended after it (:meth:`on_chunk`,
    called for every chunk regardless of type), or `SEAL_TIMEOUT_S` passes
    with no change (:meth:`seal_idle`, which the caller should poll
    regularly, e.g. from the audio capture loop). The latter matters
    because the trailing word of an utterance -- including a lone "quit"
    or "exit" -- would otherwise never be confirmed if nothing is said
    afterward.
    """

    def __init__(self, leds: LedBoard) -> None:
        self.leds = leds
        self._buf = bytearray()
        self._seen_word_count = 0        # sealed words already committed
        self._pending_word: str | None = None   # trailing, not-yet-sealed word
        self._pending_since: float | None = None
        self._recent: deque[str] = deque(maxlen=RECENT_WINDOW)
        self.stop_requested = False

    def on_chunk(self, chunk: AsrChunk) -> None:
        chunk.update(self._buf)
        text = self._buf.decode("utf-8", "replace").lower()
        print(f"\r  heard: {text.strip()[-60:]}", end="", flush=True)
        self._resync(text, time.monotonic())

    def seal_idle(self) -> None:
        """Force-commit the trailing word once it's gone quiet for a bit.

        Call this regularly (e.g. once per audio-capture loop iteration) so
        a command's last word -- including "quit"/"exit" -- fires even when
        nothing more is said afterward.
        """
        if self._pending_word is None or self.stop_requested:
            return
        if time.monotonic() - self._pending_since >= SEAL_TIMEOUT_S:
            word, self._pending_word = self._pending_word, None
            self._seen_word_count += 1
            self._commit(word)

    def _resync(self, text: str, now: float) -> None:
        matches = list(re.finditer(r"[a-z']+", text))
        sealed_count = len(matches)
        tail: str | None = None

        if matches and matches[-1].end() == len(text):
            # the last word touches the end of the buffer -- it may still be growing
            sealed_count -= 1
            tail = matches[-1].group(0)

        sealed_words = [m.group(0) for m in matches[:sealed_count]]
        for word in sealed_words[self._seen_word_count:]:
            self._commit(word)
        self._seen_word_count = len(sealed_words)

        if tail != self._pending_word:
            self._pending_word = tail
            self._pending_since = now if tail is not None else None

    def _commit(self, word: str) -> None:
        self._recent.append(word)
        if word in QUIT_WORDS:
            self.stop_requested = True
            print(f"\n  -> stopping (heard {word!r})")
            return
        if word in RESET_WORDS:
            self._recent.clear()
            print(f"\n  -> cleared recent word list (heard {word!r})")
            return
        self._maybe_trigger()

    def _maybe_trigger(self) -> None:
        window = set(self._recent)

        if window & OFF_WORDS:
            action = "off"
        elif window & ON_WORDS:
            action = "on"
        elif window & BLINK_WORDS:
            action = "blink"
        else:
            return

        colours = [name for name in LED_PINS if name in window]
        if not colours:
            if not (window & ALL_WORDS):
                return  # heard the action before naming a colour/"all" -- say the colour first, e.g. "red on"
            colours = list(LED_PINS)

        self.leds.apply(colours, action)
        print(f"\n  -> {action}: {', '.join(colours)}")
        self._recent.clear()


# --------------------------------------------------------------------------- #
# Continuous mic capture, resampled and streamed into the ASR
# --------------------------------------------------------------------------- #
def _supported_capture_rate(input_device: int | None) -> int:
    """Return a sample rate the microphone accepts (prefer 16 kHz)."""
    for rate in (SAMPLE_RATE, 48_000, 44_100):
        try:
            sd.check_input_settings(device=input_device, samplerate=rate, channels=1, dtype="int16")
            return rate
        except Exception:
            continue
    return int(sd.query_devices(input_device, "input")["default_samplerate"])


def listen_forever(asr: Asr, leds: LedBoard, input_device: int | None = None) -> None:
    """Stream the microphone into the ASR until interrupted, reacting live."""
    capture_rate = _supported_capture_rate(input_device)
    g = gcd(capture_rate, SAMPLE_RATE)
    up, down = SAMPLE_RATE // g, capture_rate // g
    # ~0.2 s blocks, length a multiple of `down` so each block resamples cleanly.
    block_frames = max(down, (int(0.2 * capture_rate) // down) * down)

    reactor = VoiceCommandReactor(leds)
    audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()
    pending = np.empty(0, dtype=np.int16)

    def on_audio(indata, _frames, _time, status):
        if status:
            print(f"  (audio: {status})", file=sys.stderr)
        audio_queue.put(indata.copy())

    def feed_samples(samples: np.ndarray) -> None:
        nonlocal pending
        pending = np.concatenate([pending, samples])
        while len(pending) >= block_frames:
            block, pending = pending[:block_frames], pending[block_frames:]
            if capture_rate != SAMPLE_RATE:
                resampled = resample_poly(block.astype(np.float32), up, down)
                block = np.clip(np.round(resampled), -32768, 32767).astype(np.int16)
            asr.push(block.astype("<i2").tobytes(), on_chunk=reactor.on_chunk)

    print(f"\nListening for voice commands over {', '.join(LED_PINS)}... "
          f"(say {' or '.join(sorted(QUIT_WORDS))}, or Ctrl+C, to quit)\n")
    with sd.InputStream(
        samplerate=capture_rate,
        channels=1,
        dtype="int16",
        device=input_device,
        callback=on_audio,
    ):
        try:
            while not reactor.stop_requested:
                try:
                    feed_samples(audio_queue.get(timeout=0.1).reshape(-1))
                except queue.Empty:
                    pass
                reactor.seal_idle()
        except KeyboardInterrupt:
            print("\nStopping...")
    asr.wait_for_completion()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input-device", type=int, default=None, help="microphone device index")
    parser.add_argument("--list-devices", action="store_true", help="list audio devices and exit")
    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return

    if not ASR_LIB.exists():
        sys.exit(f"Missing SDK library: {ASR_LIB}")

    print("Loading niagara ASR...")
    asr = Asr(str(ASR_LIB), enable_punctuation=False)
    leds = LedBoard(LED_PINS)
    try:
        listen_forever(asr, leds, args.input_device)
    finally:
        leds.close()
        asr.close()


if __name__ == "__main__":
    main()
