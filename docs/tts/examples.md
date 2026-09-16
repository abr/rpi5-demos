# Examples

All examples assume the TTS application package has been extracted and `LIBRARY_PATH` points to the
shared library inside it. Replace the path with the actual location on your device.

The examples below alternate between the two available English voices; see
[Voices](../tts/voices.md).

Text is pushed raw: the backend converts numbers, dates, and abbreviations to spoken words itself
(see the [input format](input-format.md) page).

## Synthesize to a raw PCM file

Collect all audio chunks and write them to a `.pcm` file. The file contains raw S16 LE mono 16 kHz
samples with no container headers. Play it back with `aplay -f S16_LE -r 16000 -c 1 output.pcm` on
Linux.

Run with:

```bash
python synthesize_pcm.py
aplay -f S16_LE -r 16000 -c 1 output.pcm
```

```python title="synthesize_pcm.py"
from abr_sdk.tts import Tts

LIBRARY_PATH = "/path/to/nith-5m-live.en-f1/libnith_5m_live.so"  # female voice

text = "Hello, world. This is on-device text-to-speech.".encode("utf-8")

chunks: list[bytes] = []

with Tts(LIBRARY_PATH) as tts:
    tts.push(text, on_pcm=chunks.append)
    tts.wait_for_completion()

with open("output.pcm", "wb") as f:
    f.write(b"".join(chunks))
```

## Stream audio directly to speakers

Stream PCM bytes to your default audio output device as they arrive using `sounddevice`. The first
audio plays before synthesis has finished.

Run with:

```bash
python stream_speakers.py
```

```python title="stream_speakers.py"
import sounddevice as sd
from abr_sdk.tts import Tts

LIBRARY_PATH = "/path/to/nith-5m-live.en-m1/libnith_5m_live.so"  # male voice
SAMPLE_RATE = 16000

text = "Streaming speech output to speakers.".encode("utf-8")

with sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
    with Tts(LIBRARY_PATH) as tts:
        tts.push(text, on_pcm=stream.write)
        tts.wait_for_completion()
```

## Synthesize multiple sentences

Push each sentence separately. The model flushes synthesis at sentence boundaries, so splitting
input at natural breaks reduces latency to first audio.

Run with:

```bash
python synthesize_sentences.py
```

```python title="synthesize_sentences.py"
import sounddevice as sd
from abr_sdk.tts import Tts

LIBRARY_PATH = "/path/to/nith-5m-live.en-f1/libnith_5m_live.so"  # female voice
SAMPLE_RATE = 16000

sentences = [
    "The ABR SDK runs entirely on-device.",
    "No audio data is sent to an external server.",
    "It uses a state-space model architecture.",
]

with sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
    with Tts(LIBRARY_PATH) as tts:
        for sentence in sentences:
            tts.push(sentence.encode("utf-8"), on_pcm=stream.write)
        tts.wait_for_completion()
```

## Read text from stdin

Read lines from stdin and synthesize each one. Useful for testing or for piping text from another
process.

Run with:

```bash
echo "Hello world" | python synthesize_stdin.py
```

```python title="synthesize_stdin.py"
import sys
import sounddevice as sd
from abr_sdk.tts import Tts

LIBRARY_PATH = "/path/to/nith-5m-live.en-m1/libnith_5m_live.so"  # male voice
SAMPLE_RATE = 16000

with sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
    with Tts(LIBRARY_PATH) as tts:
        for line in sys.stdin:
            line = line.rstrip("\n")
            if line:
                tts.push(line.encode("utf-8"), on_pcm=stream.write)
        tts.wait_for_completion()
```

## Synthesize LLM output token by token

Push tokens directly as the LLM produces them. The backend buffers text to sentence boundaries
before synthesizing, so no sentence assembly is needed on the Python side, and the first spoken
sentence plays before the LLM has produced the full response.

```python
from abr_sdk.tts import Tts

LIBRARY_PATH = "/path/to/nith-5m-live.en-f1/libnith_5m_live.so"  # female voice

def speak_llm_stream(token_iterator, on_pcm):
    with Tts(LIBRARY_PATH) as tts:
        for token in token_iterator:
            tts.push(token.encode("utf-8"), on_pcm=on_pcm)
        tts.wait_for_completion()
```

Pass any iterator of token strings and a callback that receives raw PCM bytes:

```python
# token_iterator: any iterable of string tokens from an LLM
# on_pcm: called with each bytes chunk as audio is synthesized

speak_llm_stream(
    token_iterator=llm.stream("Tell me a story."),
    on_pcm=audio_output.write,
)
```

> **Next steps**
>
> - [Input format](../tts/input-format.md): the normalization pipeline and SSML markup.
> - [Overview](../tts/overview.md): output format and how the streaming model works.
