#!/usr/bin/env python3
"""Talk to Gemini with your voice — ABR ASR + ABR TTS, Gemini in the cloud.

The pipeline has four steps, repeated in a loop:

    1. LISTEN     record from the microphone           (sounddevice)
    2. TRANSCRIBE speech  -> text                      (ABR niagara ASR, streaming)
    3. THINK      text    -> reply text                (Gemini, cloud API)
    4. SPEAK      reply   -> audio out the speakers    (ABR nith TTS, streamed)

ASR and TTS run locally on the ABR libraries; only the THINK step calls out to
the cloud. The transcript is streamed into the ASR *while you are still talking*
(low post-stop latency), and Gemini's reply is streamed back token-by-token and
fed to the TTS one sentence at a time, so audio starts before the full reply has
arrived.

Usage:
    python voice_chat.py                 # start chatting
    python voice_chat.py --list-devices  # print audio devices, then exit
    python voice_chat.py --input-device 7  # use a specific microphone
    python voice_chat.py --model gemini-3.6-flash-lite
    python voice_chat.py --tts m1        # male voice (default: f1, female)

At the prompt: press Enter to start recording, speak, press Enter again to
stop. Type 'q' then Enter to quit.

One-time setup:

  * ABR libraries must be activated once (needs a license key and network
    access; ASR/TTS afterwards run offline):

        abr-sdk activate niagara-38m-live.en-linux-arm64/libniagara_38m_live.so   --key-file abr_license.key
        abr-sdk activate nith-5m-live.en-f1-linux-arm64/libnith_5m_live.so   --key-file abr_license.key
        abr-sdk activate nith-5m-live.en-m1-linux-arm64/libnith_5m_live.so   --key-file abr_license.key  # for --tts m1

  * A Gemini API key must be on the environment or set in the code below:

        export GEMINI_API_KEY=...      # or GOOGLE_API_KEY
"""
from __future__ import annotations

import argparse
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from math import gcd
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly

from google import genai
from google.genai import types

from abr_sdk.asr import Asr, AsrChunk
from abr_sdk.tts import Tts

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
# Root folder for abr-packages (defaults to "~/abr-packages"), update as necessary.
ABR_PACKAGES_ROOT = Path.home() / "abr-packages"
ASR_LIB = ABR_PACKAGES_ROOT / "niagara-38m-live.en-linux-arm64" / "libniagara_38m_live.so"

# The nith TTS ships one shared library per voice; pick with --tts.
TTS_LIBS = {
    "m1": ABR_PACKAGES_ROOT / "nith-5m-live.en-m1-linux-arm64" / "libnith_5m_live.so",  # male voice
    "f1": ABR_PACKAGES_ROOT / "nith-5m-live.en-f1-linux-arm64" / "libnith_5m_live.so",  # female voice
}
DEFAULT_TTS = "f1"

# Default Gemini model; override with --model. A *-flash model keeps the voice
# round-trip snappy.
GEMINI_MODEL = "gemini-3.6-flash"

# The ABR ASR and TTS engines speak only one audio format: 16 kHz, mono,
# signed 16-bit little-endian PCM. We convert to/from this everywhere.
SAMPLE_RATE = 16_000

# The audio output drops the first few milliseconds while the stream starts up.
# Prepend this much silence so the clipped part is silence, not the first word.
LEAD_IN_SILENCE_S = 0.3

# Keep Gemini's replies short and plain, since they are read aloud.
SYSTEM_PROMPT = (
    "You are a friendly voice assistant. Your replies are read aloud, so keep "
    "them short and conversational: one to three sentences, no lists, no "
    "markdown, no emoji."
)

# Gemini API key.
GEMINI_API_KEY = ""

# --------------------------------------------------------------------------- #
# Step 1 — LISTEN: record the microphone into 16 kHz PCM
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


# --------------------------------------------------------------------------- #
# Step 2 — TRANSCRIBE: ABR niagara turns your speech into text, streaming
# --------------------------------------------------------------------------- #
class StreamingTranscriber:
    """Incremental ASR around a single niagara `Asr` instance.

    Push 16 kHz mono int16 PCM with :meth:`feed`; the transcript grows (and is
    revised in place, e.g. when punctuation/capitalisation is added) and the
    ``on_text`` callback fires with the current text whenever it changes. Call
    :meth:`finish` once all audio is fed to flush the tail and get the final
    text.
    """

    def __init__(self, on_text: Optional[Callable[[str], None]] = None) -> None:
        if not ASR_LIB.exists():
            sys.exit(f"Missing SDK library: {ASR_LIB}")
        self.asr = Asr(str(ASR_LIB))
        self._on_text = on_text
        self._buf = bytearray()   # raw assembled transcript bytes
        self._last = ""           # last text handed to the callback

    def _on_chunk(self, chunk: AsrChunk) -> None:
        # Each chunk may append to or rewrite the tail of the transcript.
        chunk.update(self._buf)
        text = self._buf.decode("utf-8", "replace").strip()
        if text != self._last:
            self._last = text
            if self._on_text is not None:
                self._on_text(text)

    def feed(self, pcm16: bytes) -> None:
        """Push a block of 16 kHz mono int16 PCM into the ASR."""
        if pcm16:
            # on_chunk is only registered on the first push (it creates the
            # internal processor); passing it every time is harmless.
            self.asr.push(pcm16, on_chunk=self._on_chunk)

    def finish(self) -> str:
        """Flush remaining audio and return the final transcript text."""
        self.asr.wait_for_completion()
        return self._buf.decode("utf-8", "replace").strip()

    def close(self) -> None:
        self.asr.close()


def record_and_transcribe(transcriber: StreamingTranscriber, input_device=None) -> str:
    """Record from the mic until Enter, streaming audio into `transcriber`.

    Audio is resampled to 16 kHz and pushed to the ASR in ~0.2 s blocks as it
    arrives, so transcription happens *during* recording. Returns the final
    transcript text.
    """
    capture_rate = _supported_capture_rate(input_device)
    g = gcd(capture_rate, SAMPLE_RATE)
    up, down = SAMPLE_RATE // g, capture_rate // g
    # ~0.2 s blocks, length a multiple of `down` so each block resamples cleanly.
    block_frames = max(down, (int(0.2 * capture_rate) // down) * down)

    buffers: "queue.Queue[np.ndarray]" = queue.Queue()
    stop = threading.Event()
    pending = np.empty(0, dtype=np.int16)

    def on_audio(indata, _frames, _time, status):
        if status:
            print(f"  (audio: {status})", file=sys.stderr)
        buffers.put(indata.copy())

    def emit(block: np.ndarray) -> None:
        if capture_rate != SAMPLE_RATE:
            r = resample_poly(block.astype(np.float32), up, down)
            block = np.clip(np.round(r), -32768, 32767).astype(np.int16)
        transcriber.feed(block.astype("<i2").tobytes())

    def feed_samples(samples: np.ndarray, final: bool = False) -> None:
        nonlocal pending
        if len(samples):
            pending = np.concatenate([pending, samples])
        while len(pending) >= block_frames:
            emit(pending[:block_frames])
            pending = pending[block_frames:]
        if final and len(pending):
            emit(pending)
            pending = pending[:0]

    with sd.InputStream(
        samplerate=capture_rate,
        channels=1,
        dtype="int16",
        device=input_device,
        callback=on_audio,
    ):
        threading.Thread(
            target=lambda: (input("Recording... speak now, press Enter to stop. \n"), stop.set()),
            daemon=True,
        ).start()
        while not stop.is_set():
            try:
                feed_samples(buffers.get(timeout=0.05).reshape(-1))
            except queue.Empty:
                continue

    # Drain anything the callback queued after the stop flag was set.
    while not buffers.empty():
        feed_samples(buffers.get().reshape(-1))
    feed_samples(np.empty(0, dtype=np.int16), final=True)
    return transcriber.finish()


# --------------------------------------------------------------------------- #
# Step 3 — THINK: Gemini turns your words into a reply (cloud API)
# --------------------------------------------------------------------------- #
class GeminiChat:
    """Wraps a Gemini chat session and remembers the conversation across turns.

    History is kept server-side by the SDK's chat object; ``reply_stream`` yields
    the reply text token-by-token so the caller can start speaking it early.
    """

    def __init__(self, model: str = GEMINI_MODEL) -> None:
        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            if "GEMINI_API_KEY" == "":
                sys.exit(("Set GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment or "
                          "in code above."))
            else:
                os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

        print(f"Connecting to Gemini ({model})...")
        # Client reads GEMINI_API_KEY / GOOGLE_API_KEY from the environment.
        self.client = genai.Client()
        self.chat = self.client.chats.create(
            model=model,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )

    def reply_stream(self, user_text: str) -> Iterator[str]:
        """Send the user's text and yield the reply in streamed text pieces."""
        for chunk in self.chat.send_message_stream(user_text):
            if chunk.text:
                yield chunk.text


# --------------------------------------------------------------------------- #
# Step 4 — SPEAK: synthesize the reply and play it out the speakers
# --------------------------------------------------------------------------- #
# Sentence-ish boundaries: a run ending in . ? ! (optionally with closing quote)
# followed by whitespace, or a newline. Used to chop the token stream into
# speakable units so the TTS can start before the whole reply has arrived.
_SENTENCE_END = re.compile(r'.*?[.!?]["\')\]]?(?:\s+|$)|.+?\n', re.DOTALL)


def _sentences(pieces: Iterable[str]) -> Iterator[str]:
    """Yield complete sentences from a stream of text fragments.

    Buffers incoming fragments and emits each time one or more sentence
    boundaries are crossed; flushes any remainder when the stream ends.
    """
    buf = ""
    for piece in pieces:
        buf += piece
        while True:
            m = _SENTENCE_END.match(buf)
            if not m:
                break
            sentence = m.group(0).strip()
            buf = buf[m.end():]
            if sentence:
                yield sentence
    tail = buf.strip()
    if tail:
        yield tail


def speak_stream(tts: Tts, output_device: int, pieces: Iterable[str]) -> str:
    """Speak a streamed reply sentence-by-sentence; return the full text.

    Each completed sentence is pushed to the TTS as soon as it is available
    (the backend normalizes numbers, dates, and abbreviations internally),
    and the PCM it produces is played immediately, so speech begins before
    the rest of the reply has been generated.
    """
    spoken_chunks: list[str] = []
    player = _StreamPlayer(output_device)
    try:
        for sentence in _sentences(pieces):
            spoken_chunks.append(sentence)
            tts.push(sentence.encode("utf-8"), on_pcm=player.write)
        tts.wait_for_completion()
    finally:
        player.close()
    return " ".join(spoken_chunks).strip()


class _StreamPlayer:
    """Play 16 kHz mono int16 PCM as it arrives, via the system audio player.

    We pipe to the system player (aplay) rather than use sounddevice for output:
    that follows the output device set in the OS sound settings and lets the
    sound server handle buffering and resampling, which avoids dropouts on
    HDMI/other sinks.
    """

    def __init__(self, output_device: int | None = None) -> None:
        if output_device is None:
            output_device = "default"
        else:
            output_device = f"plughw:{output_device},0"

        if shutil.which("aplay"):
            cmd = ["aplay", "-q", "-D", output_device, "-f", "S16_LE", "-c", "1", "-r", str(SAMPLE_RATE), "-"]
        else:
            print("  (no audio player found; install pipewire or alsa-utils)", file=sys.stderr)
            self.proc = None
            return
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Pad the start with silence so the stream's startup clipping is harmless.
        self.write(bytes(int(SAMPLE_RATE * LEAD_IN_SILENCE_S) * 2))

    def write(self, pcm: bytes) -> None:
        if self.proc is not None and pcm:
            try:
                self.proc.stdin.write(pcm)
            except BrokenPipeError:
                pass

    def close(self) -> None:
        if self.proc is not None:
            try:
                self.proc.stdin.close()
            except BrokenPipeError:
                pass
            self.proc.wait()
            self.proc = None


# --------------------------------------------------------------------------- #
# The conversation loop
# --------------------------------------------------------------------------- #
def chat_loop(gemini: GeminiChat, input_device: int | None = None,
              output_device: int | None = None,
              tts_lib: Path = TTS_LIBS[DEFAULT_TTS]) -> None:
    """Record -> stream-transcribe -> Gemini -> speak, until the user quits.

    Press Enter to start recording, Enter again to stop; 'q' then Enter quits.
    """
    if not tts_lib.exists():
        sys.exit(f"Missing SDK library: {tts_lib}")

    print(f"Loading nith TTS ({tts_lib.parent.name})...")
    with Tts(str(tts_lib)) as tts:
        print("\nReady. Press Enter to record, or type 'q' then Enter to quit.\n")
        while True:
            if input("[Enter]=record  q=quit > ").strip().lower() == "q":
                break

            def on_text(text: str) -> None:
                print(f"\r  You:   {text}", end="", flush=True)

            transcriber = StreamingTranscriber(on_text=on_text)
            try:
                user_text = record_and_transcribe(transcriber, input_device)  # 1+2 LISTEN+TRANSCRIBE
            finally:
                transcriber.close()

            print()  # end the live "You:" line
            if not user_text:
                print("  (didn't catch that)\n")
                continue

            print("  Gemini: ", end="", flush=True)
            spoken = speak_stream(tts, output_device, _echo(gemini.reply_stream(user_text)))  # 3+4 THINK+SPEAK
            print(f"\r  Gemini: {spoken}\n")
    print("Bye.")


def _echo(pieces: Iterable[str]) -> Iterator[str]:
    """Pass text fragments through, printing them live as they stream by."""
    for piece in pieces:
        print(piece, end="", flush=True)
        yield piece


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input-device", type=int, default=None, help="microphone device index")
    parser.add_argument("--output-device", type=int, default=None, help="aplay plughw output device index")
    parser.add_argument("--list-devices", action="store_true", help="list audio devices and exit")
    parser.add_argument("--model", default=GEMINI_MODEL, help=f"Gemini model (default {GEMINI_MODEL})")
    parser.add_argument("--tts", choices=sorted(TTS_LIBS), default=DEFAULT_TTS,
                        help=f"TTS voice (default {DEFAULT_TTS}): f1=female, m1=male")
    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return

    chat_loop(GeminiChat(args.model), args.input_device, args.output_device, TTS_LIBS[args.tts])


if __name__ == "__main__":
    main()
