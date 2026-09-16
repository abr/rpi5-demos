# TTS quickstart

This page walks you from a fresh install to synthesized audio. You will write a short Python script,
run it, and understand what each part does.

## Prerequisites

You need:

- **Python 3.10+** and `pip` or `uv`
- **The ABR SDK**: `pip install abr-sdk`
- **A TTS application package** downloaded and extracted from the
  [ABR developer portal](https://dev.appliedbrainresearch.com). You should have a directory
  containing a `.so` shared library file.
- **An activated license** for this device. See [License
  activation](../getting-started/license-activation.md).

If you have not downloaded an application package yet, follow
[Installation](../getting-started/installation.md)
first.

## Write the script

Create a file called `tts_quickstart.py`:

```python title="tts_quickstart.py"
import subprocess
from abr_sdk.tts import Tts

LIBRARY_PATH = "/path/to/nith-5m-live.en-f1/libnith_5m_live.so"  # female voice

text = "Hello, world. Welcome to on-device text-to-speech.".encode("utf-8")

chunks: list[bytes] = []

with Tts(LIBRARY_PATH) as tts:
    tts.push(text, on_pcm=chunks.append)
    tts.wait_for_completion()

with open("output.pcm", "wb") as f:
    f.write(b"".join(chunks))

print("Wrote output.pcm")
subprocess.run(["aplay", "-f", "S16_LE", "-r", "16000", "-c", "1", "output.pcm"])
```

Replace `LIBRARY_PATH` with the path to the shared library inside your extracted application
package.

## Run it

```bash
python tts_quickstart.py
```

You should see `Wrote output.pcm` and hear the synthesized audio play automatically. To play back
the
audio from the generated audio file, run:

```bash
aplay -f S16_LE -r 16000 -c 1 output.pcm   # Linux
```

## What just happened

**`"...".encode("utf-8")`**: `abr_sdk.tts.Tts.push` takes UTF-8 `bytes`. The text can
contain digits, currency amounts, and abbreviations; the backend converts them to spoken words
before synthesis.

**`with Tts(LIBRARY_PATH) as tts:`**: The `with` block opens the application package and loads the
neural network on entry. On exit, whether normal or on exception, the SDK releases the loaded
library
and all internal buffers.

**`tts.push(text, on_pcm=chunks.append)`**: Feeds the text to the model. The call returns
immediately. The `on_pcm` callback fires as the model produces PCM audio; here it appends each chunk
to the `chunks` list.

**`tts.wait_for_completion()`**: Signals end-of-input, flushes the synthesis pipeline, and blocks
until all audio has been delivered through `on_pcm`.

**`b"".join(chunks)`**: Concatenates the individual PCM chunks into one continuous byte string.

**`subprocess.run(["aplay", ...])`**: Plays back the saved file immediately using `aplay`. The
`-f S16_LE -r 16000 -c 1` flags tell `aplay` to interpret the raw bytes as signed 16-bit
little-endian mono audio at 16 kHz, matching the format the TTS model produces.

> **Next steps**
>
> - [Input format](../tts/input-format.md): how the backend normalizes numbers, acronyms, and
>   abbreviations, and
>   the SSML markup it supports.
> - [Examples](../tts/examples.md): ready-to-run examples for streaming to speakers, synthesizing
>   multiple
>   sentences, and reading from stdin.
> - [Overview](../tts/overview.md): how the streaming model works and the PCM output format in
>   detail.
