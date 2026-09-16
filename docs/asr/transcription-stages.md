# Transcription stages

The ASR model begins processing audio immediately with the first input and emits text incrementally
as audio arrives. Each audio segment produces a model output chunk followed by a post-processing
chunk that overwrites it.

This page is for developers building applications that display or forward text as it arrives: a
terminal renderer, a subtitle overlay, a real-time feed to a downstream service.

If you only need the final transcript after all audio has been processed,
`abr_sdk.asr.AsrTranscript` handles the bookkeeping automatically. See
[Examples](../asr/examples.md) for complete runnable implementations.

## Model output and post-processing

For each segment of audio, the SDK emits two chunks in sequence.

The first is the **model output**, determined by your `abr_sdk.asr.AsrMode` setting:

- `AsrTextChunkType.CAUSAL` (**FAST** mode): emitted
  as soon as possible, roughly 150 milliseconds after the audio arrives. The model uses no
  look-ahead. Lowest latency.
- `AsrTextChunkType.NONCAUSAL` (**ACCURATE**
  mode): emitted after the model has used a small window of subsequent audio as context. Higher
  accuracy, higher latency.

The second is the **post-processing output**
(`AsrTextChunkType.POSTPROC`), applied to the model
output regardless of mode. Adds punctuation, capitalization, and spell correction. Replaces the
model output chunk for the same segment. Punctuation and capitalization can be turned off with
`enable_punctuation=False`, and spell correction with `enable_spellcheck=False`, when constructing
the `abr_sdk.asr.Asr` instance; left unset, both are enabled. Some language packages
ship models that emit punctuation directly rather than in post-processing.

| Chunk type                   | When emitted                | Relative latency |
| ---------------------------- | --------------------------- | ---------------- |
| `AsrTextChunkType.CAUSAL`    | FAST model output           | Lowest           |
| `AsrTextChunkType.NONCAUSAL` | ACCURATE model output       | Medium           |
| `AsrTextChunkType.POSTPROC`  | Post-processed model output | Highest          |

See [Choosing a mode](#choosing-a-mode) for guidance on which model output to use.

## How replace ranges work

Each `abr_sdk.asr.AsrChunk` carries two byte offset fields that tell you where its text
belongs in the running transcript. All text is encoded as UTF-8, and the byte offsets always index
to UTF-8 code-point boundaries: you will never receive an offset that splits a multi-byte character.

- `replace_byte_offset_begin` and `replace_byte_offset_end` are **negative** byte offsets measured
  from the current end of the transcript buffer.
- A value of `0` means "the current end," so a chunk with both offsets at `0` appends new text
  without replacing anything.
- A chunk with `replace_byte_offset_begin = -N` and `replace_byte_offset_end = 0` replaces the last
  `N` bytes.

### Worked example

Consider the phrase "hello world" arriving in FAST mode. The transcript starts as an empty buffer.

**Step 1: CAUSAL chunk arrives.** Both offsets are `0`, the text is appended:

```text
buffer: b"helo wrold"   (10 bytes)
```

**Step 2: POSTPROC chunk arrives.** `replace_byte_offset_begin = -10`, `replace_byte_offset_end =
0`.
The last 10 bytes are replaced:

```text
buffer: b"Hello, world."  (14 bytes)
```

In ACCURATE mode the steps are the same, but the NONCAUSAL chunk in step 1 is more accurate before
post-processing arrives.

### Applying chunks to a buffer

`abr_sdk.asr.AsrChunk.update` applies a chunk to a `bytearray`, handling the slice
replacement in place:

```python
buf = bytearray()

def on_chunk(chunk: AsrChunk) -> None:
    chunk.update(buf)
```

This is equivalent to what `abr_sdk.asr.AsrTranscript` does internally when you call
`.text`. Use `AsrChunk.update()` directly only when you are maintaining a custom buffer for a
renderer that needs per-chunk control.

## Rendering examples

Different output targets need different policies for which chunks to accept.

### FAST output

For a downstream language model, use FAST mode and forward only
`abr_sdk.cabi.AsrTextChunkType.CAUSAL` chunks. Language models are robust to minor
transcription errors, and low-latency FAST output keeps the downstream response time short.

```python
from abr_sdk.asr import Asr, AsrChunk, AsrTextChunkType

def on_chunk(chunk: AsrChunk) -> None:
    if chunk.type == AsrTextChunkType.CAUSAL:
        send_to_llm(chunk.data.decode("utf-8"))
```

### ACCURATE output

For terminal rendering, use ACCURATE mode and accept only
`abr_sdk.cabi.AsrTextChunkType.NONCAUSAL` chunks. This gives corrected output without the
additional latency of post-processing.

```python
from abr_sdk.asr import Asr, AsrChunk, AsrTextChunkType

buf = bytearray()

def on_chunk(chunk: AsrChunk) -> None:
    if chunk.type == AsrTextChunkType.NONCAUSAL:
        chunk.update(buf)
        print(buf.decode("utf-8"), end="\r", flush=True)
```

### Post-processed output

For subtitle or caption display, accept only `abr_sdk.cabi.AsrTextChunkType.POSTPROC`
chunks. Post-processing is applied regardless of mode; use ACCURATE mode for the highest-accuracy
base before post-processing.

```python
from abr_sdk.asr import Asr, AsrChunk, AsrTextChunkType

buf = bytearray()

def on_chunk(chunk: AsrChunk) -> None:
    if chunk.type == AsrTextChunkType.POSTPROC:
        chunk.update(buf)
        print(buf.decode("utf-8"), end="\r", flush=True)
```

## Choosing a mode

The `abr_sdk.asr.AsrMode` enum controls whether you receive FAST
(`abr_sdk.cabi.AsrTextChunkType.CAUSAL`) or ACCURATE
(`abr_sdk.cabi.AsrTextChunkType.NONCAUSAL`) model output. Post-processing is applied in
both modes. Pass `mode` to the `abr_sdk.asr.Asr` constructor:

```python
from abr_sdk.asr import Asr, AsrMode

with Asr(LIBRARY_PATH, mode=AsrMode.ACCURATE) as asr:
    ...
```

If `mode` is not specified, the library defaults to `abr_sdk.asr.AsrMode.ACCURATE`.

| Situation                                                 | Recommended mode |
| --------------------------------------------------------- | ---------------- |
| Transcript consumed by a language model                   | `FAST`           |
| Transcript displayed to a user (subtitles, live captions) | `ACCURATE`       |
| Latency is the primary constraint                         | `FAST`           |
| Accuracy is the primary constraint                        | `ACCURATE`       |

Both modes use the same underlying model. The difference is in when the model commits to its output.

> **Next steps**
>
> - [Examples](../asr/examples.md): Full, runnable examples for each rendering strategy.
> - [Overview](../asr/overview.md): Overview of the ASR API and transcription modes.
