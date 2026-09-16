# ASR quickstart

This tutorial takes you from a fresh installation to a running transcript. By the end you will have
a Python script that streams audio from your microphone and prints the transcribed text to stdout.

## Prerequisites

You need:

- **The ABR SDK**: `pip install abr-sdk`
- **An ASR application package** downloaded and extracted from the
  [ABR developer portal](https://dev.appliedbrainresearch.com). You should have a directory
  containing a `.so` shared library file.
- **arecord** (from the `alsa-utils` package, included on most Linux distributions) to capture audio
  from your microphone.
- **A working microphone** connected to your device.
- **An activated license** for this device. See [License
  activation](../getting-started/license-activation.md).

If you have not downloaded a package yet, follow [Installation](../getting-started/installation.md)
first.

## Write the script

Now we'll write a script that streams audio from your microphone and prints the transcribed text to
stdout.

Create a file called `microphone.py`:

```python title="microphone.py"
import sys
from abr_sdk.asr import Asr, AsrChunk

LIBRARY_PATH = "/path/to/niagara-38m-live.en/libniagara_38m_live.so"
CHUNK_BYTES = 16000 * 2 // 10  # 100 ms of 16 kHz mono S16_LE audio

buf = bytearray()

def on_chunk(chunk: AsrChunk) -> None:
    chunk.update(buf)
    print(f"\r{buf.decode('utf-8')}", end="", flush=True)

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

Set `LIBRARY_PATH` to the absolute path of the `.so` file inside your extracted package directory.
For example, the `niagara-38m-live.en` package contains `libniagara_38m_live.so`.

## Run it

```bash
arecord -f S16_LE -c 1 -r 16000 -t raw -q | python microphone.py
```

Speak into your microphone, then press **Ctrl+C** to stop. The final transcript is printed to
stdout.

## What just happened

**`arecord -f S16_LE -c 1 -r 16000 -t raw -q`** captures raw 16-bit mono PCM at 16 kHz, the format
the ASR model expects, and pipes it to the script's standard input.

**`sys.stdin.buffer.read(CHUNK_BYTES)`** pulls the next 100 ms of audio from the pipe. The loop ends
when `arecord` stops and the pipe closes.

**`CHUNK_BYTES = 16000 * 2 // 10`** is 100 milliseconds of audio per push call (16,000 samples per
second × 2 bytes per sample ÷ 10). The model does not require a specific chunk size; smaller chunks
reduce latency.

**`on_chunk` / `chunk.update(buf)`** applies each text chunk to `buf` in place, including the
overwrites that ACCURATE and post-processing passes emit, so the transcript refines on the same line
as it is reprinted with `\r`.

**`asr.push(chunk, on_chunk=on_chunk)`** hands each audio chunk to the model.
`abr_sdk.asr.Asr.push` is non-blocking; it returns as soon as the input bytes are accepted.

**`asr.wait_for_completion()`** signals end-of-audio, flushes the model pipeline, and blocks until
every pending text chunk has been delivered.

> **Next steps**
>
> - Read the [Overview](../asr/overview.md) for a map of the full ASR API.
> - Understand how the model produces and revises output in [Transcription
>   stages](../asr/transcription-stages.md).
