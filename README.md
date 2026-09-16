# ABR SDK demos for the Raspberry Pi 5

Starting point for building with the [ABR SDK](https://docs.appliedbrainresearch.com/sdk/)
on a Raspberry Pi 5. The SDK runs streaming speech recognition and speech
synthesis entirely on the device, with no cloud call at inference time.

Two working demos, the full SDK documentation as local markdown, and sample
audio to test against.

## Demos

| Demo                                    | What it does                                                                                                                                     |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| [asr-led-demo](asr-led-demo/)           | Always-listening voice control. Say "red on" or "all lights off" and GPIO-wired LEDs react as you speak. Speech recognition only, fully offline. |
| [llm-pipeline-demo](llm-pipeline-demo/) | Spoken conversation. Your speech is transcribed locally, sent to Gemini, and the reply is spoken back locally.                                   |

Each demo is one self-contained file with inline dependency metadata, so `uv`
builds its environment on first run. Copy one and start hacking; there is no
shared library to understand first.

## Setup

**Install uv**, once per machine:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Install the system libraries** the demos need. PortAudio backs audio capture
and playback; `swig` is only needed for the LED demo, which compiles the `lgpio`
GPIO backend from source:

```bash
sudo apt update
sudo apt install -y libportaudio2 swig
```

**Unpack the application packages** you were given. These hold the models and
the compiled inference engine, and are not in this repository. Put each one in
its own directory under `~/abr-packages`:

```text
~/abr-packages/
  niagara-38m-live.en-linux-arm64/   ASR
  nith-5m-live.en-f1-linux-arm64/    TTS, female voice
  nith-5m-live.en-m1-linux-arm64/    TTS, male voice
```

A Pi 5 needs the `linux-arm64` builds. If you keep them somewhere else, edit
`ABR_PACKAGES_ROOT` at the top of each demo script.

**Activate the device**, once. This is the only step that needs network access:

```bash
abr-sdk activate ~/abr-packages/niagara-38m-live.en-linux-arm64/libniagara_38m_live.so \
  --key-file abr_license.key
```

Activation is per device, not per package. You point it at some package's `.so`
because part of the check lives in the compiled library, but any package will
do, and every package you unpack later is already activated.

## What the API looks like

Transcribing a clip is three lines. `process` blocks until the whole clip is
done:

```python
from abr_sdk.asr import Asr

with Asr("niagara-38m-live.en-linux-arm64/libniagara_38m_live.so") as asr:
    print(asr.process(pcm_bytes).text)
```

Streaming is the interesting mode, and the one both demos use. Push audio as it
arrives and a callback fires as text appears:

```python
from abr_sdk.asr import Asr, AsrTranscript

transcript = AsrTranscript()
with Asr(LIBRARY_PATH) as asr:
    while chunk := mic.read(1600):
        asr.push(chunk, on_chunk=transcript.chunks.append)
    asr.wait_for_completion()
print(transcript.text)
```

A chunk can **replace** trailing text rather than append to it, because later
passes revise earlier guesses. Apply each chunk with `chunk.update(buf)` to a
running buffer rather than concatenating.

Synthesis mirrors it. Push text, receive PCM through a callback:

```python
from abr_sdk.tts import Tts

pcm = []
with Tts(TTS_LIBRARY_PATH) as tts:
    tts.push(b"Hello from the Pi.", on_pcm=pcm.append)
    tts.wait_for_completion()
```

Audio is 16 kHz mono signed 16-bit little-endian PCM on both sides.

## Documentation

The SDK documentation is copied into [`docs/`](docs/) as plain markdown, so you
and your coding assistant can read it without leaving the repository. It matches
<https://docs.appliedbrainresearch.com/sdk/>, which stays authoritative. See
[docs/SOURCE.md](docs/SOURCE.md) for when it was copied and how to refresh it.

|                                                               |                                       |
| ------------------------------------------------------------- | ------------------------------------- |
| [Introduction and contents](docs/index.md)                    | Map of everything below               |
| [Installation](docs/getting-started/installation.md)          | Install the SDK and get a package     |
| [ASR quickstart](docs/getting-started/asr-quickstart.md)      | Transcribe from a microphone          |
| [TTS quickstart](docs/getting-started/tts-quickstart.md)      | Speak a sentence                      |
| [Streaming and chunks](docs/concepts/streaming-and-chunks.md) | The model behind both APIs            |
| [Transcription stages](docs/asr/transcription-stages.md)      | Why text gets revised                 |
| [Python API reference](docs/api/reference.md)                 | Every public class and method         |
| [Raspberry Pi notes](docs/raspberry-pi.md)                    | Audio, GPIO, and throttling on a Pi 5 |
| [FAQ](docs/faq.md)                                            | Common questions                      |

[`samples/`](samples/) holds two short clips in the exact format the ASR wants,
so you can test without fighting your microphone first.

## Working with a coding assistant

[CLAUDE.md](CLAUDE.md) holds the facts an assistant gets wrong about this SDK:
the audio format, the chunk revision semantics, where the libraries live, and
which documentation page answers which question. `AGENTS.md` is a symlink to the
same file, so assistants that look for that name find it too.

## Ideas to build

- Swap Gemini for a local model and make the conversation demo fully offline.
- Drive something other than LEDs: a servo, a relay, a display.
- Add a wake word so the LED demo only listens after you say its name.
- Log every transcript with a timestamp and build a searchable voice journal.
- Use the TTS to read notifications, a feed, or sensor readings aloud.
