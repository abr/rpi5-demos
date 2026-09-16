# Benchmarking

`abr_sdk.asr.Asr.process` is a blocking call that takes a complete audio clip and returns
the final transcript. It is suited for benchmarking throughput and accuracy against a fixed audio
dataset.

For real-time or streaming use, see [Overview](../asr/overview.md).

## `Asr.process()`

```python
Asr.process(data: bytes) -> AsrTranscript
```

Pushes all of `data` through the ASR pipeline, waits for the neural network to finish, and returns
the transcript. The call blocks until the entire input has been processed; it does not return
partial results.

`abr_sdk.asr.Asr.process` can be called multiple times on the same
`abr_sdk.asr.Asr` instance. Each call is self-contained: no audio state carries over
between clips, so you can process a batch of clips back to back.

### Parameters

| Parameter | Type    | Description                                                                                                                              |
| --------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `data`    | `bytes` | PCM audio encoded as a little-endian 16-bit byte array at 16,000 Hz. See [Input format](../asr/input-format.md) for format requirements. |

### Return value

Returns an `abr_sdk.asr.AsrTranscript`. Call `.text` to get the final string.

## Example

```python title="benchmark.py"
from pathlib import Path
from abr_sdk.asr import Asr

LIBRARY_PATH = "/path/to/niagara-38m-live.en/libniagara_38m_live.so"
CLIP_PATHS = ["clip1.pcm", "clip2.pcm"]

with Asr(LIBRARY_PATH) as asr:
    for path in CLIP_PATHS:
        transcript = asr.process(Path(path).read_bytes())
        print(transcript.text)
```

Each `.pcm` file must contain raw PCM audio in the format the `Asr` instance expects. See
[Input format](../asr/input-format.md) for details on sample rate, bit depth, and channel layout.

## Errors

| Exception                        | When raised                                                                                                                    |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `abr_sdk.exceptions.AbrSdkError` | Called on a closed `Asr` instance, for example after the `with` block has exited or after `asr.close()` was called explicitly. |
| `abr_sdk.cabi.AbrSdkCAbiError`   | The underlying C library returned a failure status. Check the log output for details.                                          |
