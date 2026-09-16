# Examples

Each example below is a complete, runnable script. Set `LIBRARY_PATH` to the path of the `.so` file
inside your extracted application package directory before running.

## Live microphone

Transcribes audio from a live microphone and displays the transcript in the terminal as speech is
recognized. `chunk.update(buf)` applies each overwrite in place, so the transcript refines on the
same line as ACCURATE and post-processing revisions arrive.

Run with:

```bash
arecord -f S16_LE -c 1 -r 16000 -t raw -q | python microphone.py
```

```python title="microphone.py"
import sys
from abr_sdk.asr import Asr, AsrChunk

LIBRARY_PATH = "/path/to/niagara-38m-live.en/libniagara_38m_live.so"
CHUNK_BYTES = 16000 * 2 // 10  # 100 ms of 16 kHz mono S16_LE audio

buf = bytearray()

def on_chunk(chunk: AsrChunk) -> None:
    chunk.update(buf)
    print(buf.decode("utf-8"), end="\r", flush=True)

with Asr(LIBRARY_PATH) as asr:
    print("Listening... press Ctrl+C to stop.", flush=True)
    try:
        while chunk := sys.stdin.buffer.read(CHUNK_BYTES):
            asr.push(chunk, on_chunk=on_chunk)
    except KeyboardInterrupt:
        pass
    asr.wait_for_completion()

print()
```

## Audio file via ffmpeg

Transcribes any audio file by piping it through `ffmpeg`. `ffmpeg` handles format conversion, so
this works with WAV, MP3, FLAC, or any other format it supports.

Run with:

```bash
ffmpeg -loglevel quiet -i recording.wav -f s16le -ar 16000 -ac 1 - | python stream_file.py
```

```python title="stream_file.py"
import sys
from abr_sdk.asr import Asr, AsrTranscript

LIBRARY_PATH = "/path/to/niagara-38m-live.en/libniagara_38m_live.so"
CHUNK_BYTES = 16000 * 2 // 10  # 100 ms of 16 kHz mono S16_LE audio

transcript = AsrTranscript()

with Asr(LIBRARY_PATH) as asr:
    while chunk := sys.stdin.buffer.read(CHUNK_BYTES):
        asr.push(chunk, on_chunk=transcript.chunks.append)
    asr.wait_for_completion()

print(transcript.text)
```

## WAV file with the `wave` module

Reads a WAV file using the standard library `wave` module and streams it through the ASR pipeline in
100-millisecond chunks. The assertions confirm the file is already in the required format before
transcription begins. See [Input format](../asr/input-format.md) for format requirements.

Run with:

```bash
python from_wav.py
```

```python title="from_wav.py"
import wave
from abr_sdk.asr import Asr, AsrTranscript

LIBRARY_PATH = "/path/to/niagara-38m-live.en/libniagara_38m_live.so"
CHUNK_FRAMES = 1600  # 100 ms at 16 kHz

transcript = AsrTranscript()

with wave.open("recording.wav", "rb") as wf:
    assert wf.getsampwidth() == 2, "expected 16-bit PCM"
    assert wf.getnchannels() == 1, "expected mono"
    assert wf.getframerate() == 16000, "expected 16 kHz"

    with Asr(LIBRARY_PATH) as asr:
        while frames := wf.readframes(CHUNK_FRAMES):
            asr.push(bytes(frames), on_chunk=transcript.chunks.append)
        asr.wait_for_completion()

print(transcript.text)
```

## WAV or FLAC file with `soundfile`

Reads a WAV or FLAC file using the `soundfile` library. `soundfile` returns the file's native sample
rate alongside the data, which is used here to size the chunks. The SDK expects 16,000 Hz audio and
does not resample: if the file is not at 16,000 Hz, resample it before passing.

Run with:

```bash
python from_soundfile.py
```

```python title="from_soundfile.py"
import soundfile as sf
from abr_sdk.asr import Asr, AsrTranscript

LIBRARY_PATH = "/path/to/niagara-38m-live.en/libniagara_38m_live.so"

data, sample_rate = sf.read("recording.wav", dtype="int16", always_2d=False)
assert data.ndim == 1, "expected mono audio"

CHUNK_FRAMES = sample_rate // 10  # 100 ms

transcript = AsrTranscript()

with Asr(LIBRARY_PATH) as asr:
    for i in range(0, len(data), CHUNK_FRAMES):
        asr.push(data[i : i + CHUNK_FRAMES].tobytes(), on_chunk=transcript.chunks.append)
    asr.wait_for_completion()

print(transcript.text)
```

## Language model feed (FAST stream)

When the transcript goes to a downstream language model, the FAST stream is recommended. Language
models absorb minor transcription errors, and low-latency FAST output keeps the downstream response
time short. This example filters to `abr_sdk.cabi.AsrTextChunkType.CAUSAL` chunks only and
discards ACCURATE and post-processing revisions.

Run with:

```bash
arecord -f S16_LE -c 1 -r 16000 -t raw -q | python llm_feed.py
```

```python title="llm_feed.py"
import sys
from abr_sdk.asr import Asr, AsrChunk, AsrTextChunkType

LIBRARY_PATH = "/path/to/niagara-38m-live.en/libniagara_38m_live.so"
CHUNK_BYTES = 16000 * 2 // 10

def on_chunk(chunk: AsrChunk) -> None:
    if chunk.type == AsrTextChunkType.CAUSAL:
        send_to_llm(chunk.data.decode("utf-8"))  # replace with your LLM handler

with Asr(LIBRARY_PATH) as asr:
    try:
        while chunk := sys.stdin.buffer.read(CHUNK_BYTES):
            asr.push(chunk, on_chunk=on_chunk)
    except KeyboardInterrupt:
        pass
    asr.wait_for_completion()
```

## Subtitle display (POST-PROC stream)

For subtitle or caption display, where text stability matters most, update the display only on
`abr_sdk.cabi.AsrTextChunkType.POSTPROC` chunks. This trades some latency for the
highest-accuracy, punctuated output.

Run with:

```bash
arecord -f S16_LE -c 1 -r 16000 -t raw -q | python subtitle.py
```

```python title="subtitle.py"
import sys
from abr_sdk.asr import Asr, AsrChunk, AsrTextChunkType

LIBRARY_PATH = "/path/to/niagara-38m-live.en/libniagara_38m_live.so"
CHUNK_BYTES = 16000 * 2 // 10

buf = bytearray()

def on_chunk(chunk: AsrChunk) -> None:
    if chunk.type == AsrTextChunkType.POSTPROC:
        chunk.update(buf)
        print(buf.decode("utf-8"), end="\r", flush=True)

with Asr(LIBRARY_PATH) as asr:
    try:
        while chunk := sys.stdin.buffer.read(CHUNK_BYTES):
            asr.push(chunk, on_chunk=on_chunk)
    except KeyboardInterrupt:
        pass
    asr.wait_for_completion()

print()
```

## Terminal live display with `rich`

Uses the `rich` library to display the full transcript in the terminal as it arrives, showing
revision through all three passes. The transcript visibly improves as FAST output is overwritten by
ACCURATE and then post-processed text.

Run with:

```bash
arecord -f S16_LE -c 1 -r 16000 -t raw -q | python rich_display.py
```

```python title="rich_display.py"
import sys
from rich.live import Live
from rich.text import Text
from abr_sdk.asr import Asr, AsrChunk

LIBRARY_PATH = "/path/to/niagara-38m-live.en/libniagara_38m_live.so"
CHUNK_BYTES = 16000 * 2 // 10

buf = bytearray()

def on_chunk(chunk: AsrChunk) -> None:
    chunk.update(buf)

with Asr(LIBRARY_PATH) as asr:
    with Live() as live:
        try:
            while chunk := sys.stdin.buffer.read(CHUNK_BYTES):
                asr.push(chunk, on_chunk=on_chunk)
                live.update(Text(buf.decode("utf-8")))
        except KeyboardInterrupt:
            pass
        asr.wait_for_completion()
        live.update(Text(buf.decode("utf-8")))
```

## Benchmarking

For benchmarking the model or batch-processing a collection of pre-loaded audio clips,
`abr_sdk.asr.Asr.process` takes a complete clip as a single `bytes` object and returns the
final `abr_sdk.asr.AsrTranscript`. It blocks until the neural network has finished.

Run with:

```bash
python benchmark.py
```

```python title="benchmark.py"
from pathlib import Path
from abr_sdk.asr import Asr

LIBRARY_PATH = "/path/to/niagara-38m-live.en/libniagara_38m_live.so"

with Asr(LIBRARY_PATH) as asr:
    transcript = asr.process(Path("recording.pcm").read_bytes())
    print(transcript.text)
```

`recording.pcm` must contain raw PCM audio in the [required format](../asr/input-format.md):
little-endian 16-bit mono at 16,000 Hz. For batch workloads, call `asr.process()` multiple times on
the same `Asr` instance; each call is independent.
