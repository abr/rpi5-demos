# Overview

The ABR SDK transcribes speech to text on-device, with no network round-trip. You push audio in as
it arrives and receive text chunks back through a callback in real time.

The ASR API is provided by the `abr_sdk.asr` module. The main class you interact with is
`abr_sdk.asr.Asr`.

## How a transcript is built

ASR produces text incrementally as audio arrives. Each piece of output is an
`abr_sdk.asr.AsrChunk`; the `abr_sdk.asr.AsrTranscript` helper collects chunks
and applies all overwrites automatically if you only need the final text. The full mechanics (chunk
types, model output modes, and replace ranges) are covered in [Transcription
stages](../asr/transcription-stages.md).

## Streaming transcription

Streaming transcription is the primary way to use ASR in the SDK. You push audio in chunks as it
arrives, and a callback fires each time the model produces new text. This works for live microphone
input, network audio streams, and long files you want to start transcribing before they finish
loading, as well as for short clips and complete recordings.

> **Attention**
>
> The snippet below shows the pattern. `audio_source` is a placeholder for any iterable that yields
> raw PCM bytes (a microphone reader, file reader, or network stream). For copy-paste-ready code,
> see
> [Examples](../asr/examples.md).

```python title="streaming.py"
from abr_sdk.asr import Asr, AsrTranscript

LIBRARY_PATH = "/path/to/niagara-38m-live.en/libniagara_38m_live.so"
transcript = AsrTranscript()

with Asr(LIBRARY_PATH) as asr:
    for audio_chunk in audio_source:  # any iterable of raw PCM bytes
        asr.push(audio_chunk, on_chunk=transcript.chunks.append)
    asr.wait_for_completion()

print(transcript.text)
```

The `abr_sdk.asr.Asr.push` call is non-blocking: it hands audio to the model and returns
immediately. The `on_chunk` callback fires as chunks are produced.
`abr_sdk.asr.Asr.wait_for_completion` blocks until the model has finished processing all
audio that has been pushed.

For benchmarking against a fixed dataset, see [Benchmarking](../asr/benchmarking.md).

## Transcription modes

The SDK offers two transcription modes through the `abr_sdk.asr.AsrMode` enum:

- `AsrMode.FAST` emits text as soon as possible, around 150
  milliseconds after the audio arrives. It does not wait for additional context.
- `AsrMode.ACCURATE` uses a small amount of subsequent audio
  as context before emitting, which improves accuracy at the cost of latency.

If you do not specify `mode`, the library defaults to `abr_sdk.asr.AsrMode.ACCURATE`.

You set the mode when constructing the `abr_sdk.asr.Asr` instance:

```python
from abr_sdk.asr import Asr, AsrMode

with Asr(LIBRARY_PATH, mode=AsrMode.FAST) as asr:
    ...
```

The right choice depends on what consumes the transcript. A downstream language model usually does
well with `abr_sdk.asr.AsrMode.FAST` output because the model itself absorbs minor errors.
A subtitle display where text stability matters often does better with
`abr_sdk.asr.AsrMode.ACCURATE`.

See [Transcription stages](../asr/transcription-stages.md) for guidance on picking between them.

## The overwrite model

**Each audio segment produces two chunks in sequence.** The first is the model output, FAST or
ACCURATE depending on your `abr_sdk.asr.AsrMode` setting. The second is a post-processing
chunk that overwrites the model output chunk with punctuated, spell-corrected text. This is how the
SDK delivers low-latency output while still refining it before it is considered final.

How you handle the overwrites depends on where the text is rendered. A terminal can rewrite a line
in place; a web UI tracks byte ranges and updates DOM spans; a downstream language model can consume
the FAST model output directly and discard the post-processing revision.

The full mechanics (chunk types, model output modes, and the replace-range fields) are covered in
[Transcription stages](../asr/transcription-stages.md).

## What you need to use ASR

To run ASR you need three things:

1. **The SDK Python package** (`pip install abr-sdk`).
2. **An application package** for your target platform. This archive contains the compiled model,
   the network weights, and supporting files. You download it from the
   [ABR developer portal](https://dev.appliedbrainresearch.com) and extract it on the device. See
   [Application packages](../concepts/application-packages.md).
3. **Audio in the expected format.** ASR consumes raw PCM bytes at a specific sample rate. The
   required format and sample rates are listed in [Input format](../asr/input-format.md).

The `abr_sdk.asr.Asr` constructor takes the path to the package's shared library.

> **Next steps**
>
> - New to the SDK? Start with [ASR quickstart](../getting-started/asr-quickstart.md).
> - [Transcription stages](../asr/transcription-stages.md): how the model produces and revises
>   output, and how to handle
>   chunk overwrites.
> - [Examples](../asr/examples.md): full, runnable examples for microphone, file, LLM feed, and
>   more.
