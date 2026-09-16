# Overview

The ABR SDK synthesizes speech from text on-device, with no network round-trip. You push UTF-8 text
bytes and receive synthesized PCM (uncompressed audio) back through a callback as the model produces
it.

The TTS API is provided by the `abr_sdk.tts` module. The main class you interact with is
`abr_sdk.tts.Tts`.

## How synthesis works

TTS accepts raw UTF-8 text bytes and produces mono PCM audio. You push text in pieces and a callback
fires each time the model produces new audio. Output begins arriving before the full text has been
consumed: the model streams audio as it synthesizes, sentence by sentence.

```python title="synthesize.py"
from abr_sdk.tts import Tts

LIBRARY_PATH = "/path/to/nith-5m-live.en-m1/libnith_5m_live.so"  # male voice

text = "Hello, world.".encode("utf-8")

chunks: list[bytes] = []

with Tts(LIBRARY_PATH) as tts:
    tts.push(text, on_pcm=chunks.append)
    tts.wait_for_completion()

pcm = b"".join(chunks)
```

The `abr_sdk.tts.Tts.push` call is non-blocking: it feeds text to the model and returns as
soon as the input is accepted. The `on_pcm` callback fires as PCM becomes available.
`abr_sdk.tts.Tts.wait_for_completion` signals end-of-input, flushes the synthesis
pipeline, and blocks until all audio has been delivered through the callback.

## Output format

The PCM bytes delivered to `on_pcm` are in the same format as the audio the ASR API consumes:

| Property    | Value                       |
| ----------- | --------------------------- |
| Encoding    | Signed 16-bit integer (S16) |
| Byte order  | Little-endian (LE)          |
| Channels    | Mono (1 channel)            |
| Sample rate | 16,000 Hz                   |
| Container   | Raw bytes. No file headers  |

One second of output is 32,000 bytes (16,000 samples × 2 bytes per sample). Each `on_pcm` call may
deliver any number of samples.

## Text normalization

The TTS model itself expects clean, speakable text: no numbers written as digits, no acronyms, no
accented characters. The backend normalizes pushed text into that form automatically, one sentence
at a time, so raw text can be pushed as-is.

```python
tts.push("Dr. Smith owed $42 to the WHO.".encode("utf-8"))
# spoken as "doctor Smith owed forty two dollars to the W H O."
```

See [Input format](../tts/input-format.md) for what normalization does.

## What you need to use TTS

To run TTS you need three things:

1. **The SDK Python package** (`pip install abr-sdk`).
2. **An application package** for your target platform. This archive contains the compiled model,
   the network weights, and supporting files. You download it from the
   [ABR developer portal](https://dev.appliedbrainresearch.com) and extract it on the device. See
   [Application packages](../concepts/application-packages.md).
3. **UTF-8 text.** Numbers, dates, and abbreviations are converted to spoken words by the backend
   automatically.

> **Next steps**
>
> - New to the SDK? Start with [TTS quickstart](../getting-started/tts-quickstart.md).
> - [Input format](../tts/input-format.md): the normalization pipeline and SSML markup.
> - [Voices](../tts/voices.md): the available voices and how to select one.
> - [Examples](../tts/examples.md): full, runnable examples for file output, speaker playback, and
>   more.
