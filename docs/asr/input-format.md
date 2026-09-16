# Input format

The ASR API accepts raw PCM (uncompressed audio) bytes. This page describes the required format
and how to size the audio buffers you pass to `abr_sdk.asr.Asr.push`.

## Sizing audio buffers

`abr_sdk.asr.Asr.push` expects audio in fixed-duration chunks. Compute the byte length
for a chunk, use it as the read size when pulling from your audio source, then pass the resulting
bytes to `abr_sdk.asr.Asr.push`:

```python
SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
CHUNK_DURATION_S = 0.1  # 100 ms

CHUNK_BYTES = int(SAMPLE_RATE * BYTES_PER_SAMPLE * CHUNK_DURATION_S)  # 3200

with Asr(LIBRARY_PATH) as asr:
    while chunk := sys.stdin.buffer.read(CHUNK_BYTES):
        asr.push(chunk, on_chunk=on_chunk)
    asr.wait_for_completion()
```

To compute the byte length for a given duration:

```text
bytes = sample_rate × bytes_per_sample × duration_in_seconds
      = 16000 × 2 × duration_in_seconds
```

For example, 100 milliseconds of audio at 16,000 Hz is 3,200 bytes. Smaller chunks reduce per-chunk
latency; larger chunks reduce the number of `abr_sdk.asr.Asr.push` calls. The model does
not require a specific chunk size.

## Required format

All PCM data passed to `abr_sdk.asr.Asr.push` must conform to the following specification.

| Property    | Value                       |
| ----------- | --------------------------- |
| Encoding    | Signed 16-bit integer (S16) |
| Byte order  | Little-endian (LE)          |
| Channels    | Mono (1 channel)            |
| Sample rate | 16,000 Hz                   |
| Container   | Raw bytes. No file headers  |

The format is commonly written as **S16_LE** or **s16le** in audio tool documentation. Each sample
is 2 bytes. One second of audio is 32,000 bytes (16,000 samples × 2 bytes per sample).

Audio must currently be 16 kHz mono before it is passed to the SDK. The SDK does not resample. If
your audio source uses a different sample rate or channel layout, you are responsible for converting
it before calling `push()`. See [Examples](../asr/examples.md) for examples using `ffmpeg`, the
`wave` module,
and `soundfile`.

> **Note**
>
> The SDK does not validate the audio content or detect format mismatches. Passing audio in the
> wrong
> format (wrong sample rate, wrong bit depth, stereo instead of mono) produces incorrect transcripts
> without raising an error.

## Sample rate

The SDK expects 16,000 Hz audio. It does not resample: audio passed to
`abr_sdk.asr.Asr.push` must already be at 16,000 Hz. Passing audio at a different sample
rate does not trigger conversion; it produces incorrect transcripts without raising an error.

> **Next steps**
>
> - [Examples](../asr/examples.md): Full examples showing how to read audio from a microphone, a WAV
>   file, and
>   other sources.
> - [Overview](../asr/overview.md): Overview of the ASR API.
