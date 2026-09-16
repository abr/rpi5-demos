# Streaming and chunks

The ABR SDK's streaming pipeline is built on three low-level primitives:
`abr_sdk.core.Buffer`, `abr_sdk.core.EventSet`, and
`abr_sdk.core.Event`. The `abr_sdk.asr.Asr.push` and
`abr_sdk.asr.Asr.wait_for_completion` manage these primitives internally, so most callers
never interact with them directly. This page explains how they work and how they fit together
underneath the high-level API.

## The layered model

The streaming pipeline has two layers, from lowest to highest:

1. **Buffers:** FIFO byte queues that carry audio in and text chunks out.
2. **Events and EventSets:** a signaling system for blocking efficiently until a buffer reaches a
   threshold or the neural network becomes idle.

`abr_sdk.asr.Asr.push` and `abr_sdk.tts.Tts.push` manage both layers internally.
Most callers never need to interact with them directly.

## Buffers

A `abr_sdk.core.Buffer` is a fixed-capacity FIFO byte queue inside the neural network
pipeline. The `abr_sdk.asr.Asr` class exposes two:

- **`abr_sdk.asr.Asr.input_buffer`:** receives raw PCM audio bytes that you write in.
- **`abr_sdk.asr.Asr.text_chunk_output_buffer`:** emits serialized
  `abr_sdk.asr.AsrChunk` structs as the model produces them.

| Property or method         | Description                                                                                                                          |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `buffer.size`              | Total capacity in bytes (fixed for the lifetime of the buffer).                                                                      |
| `buffer.level`             | Current fill level in bytes.                                                                                                         |
| `buffer.push(data)`        | Write bytes into the buffer. Returns the number of bytes actually written, which may be less than `len(data)` if the buffer is full. |
| `buffer.pull(max_n_bytes)` | Read up to `max_n_bytes` bytes from the buffer.                                                                                      |
| `buffer.clear()`           | Discard all data currently in the buffer.                                                                                            |

In normal usage you do not call `abr_sdk.core.Buffer.push`,
`abr_sdk.core.Buffer.pull`, or `abr_sdk.core.Buffer.clear` directly.
`abr_sdk.asr.Asr.push` manages both buffers for you.

## Events and EventSets

Polling `abr_sdk.core.Buffer.level` in a loop would waste CPU cycles. The event system
provides a blocking interface: your code waits until a condition is met, then acts.

An `abr_sdk.core.EventSet` groups one or more `abr_sdk.core.Event` objects
into a single poll target. Call `evset.poll()` to block until
at least one event fires or the timeout elapses. It returns `True` if an event fired, `False` if the
timeout expired. A negative timeout waits forever; a timeout of zero returns immediately without
blocking. `abr_sdk.core.EventSet.poll` raises `InterruptedError` if interrupted by a
signal.

Call `evset.interrupt()` to unblock a
`abr_sdk.core.EventSet.poll` call that is waiting on another thread.

Create events from an `abr_sdk.core.EventSet` using these factory methods:

**`create_buffer_level_event()`** fires
when at least `threshold` bytes are available. For an output buffer, "available" means `threshold`
bytes of data ready to read. For an input buffer, "available" means `threshold` bytes of write space
free. Use an output buffer event to know when a chunk is ready; use an input buffer event to know
when the buffer has space to accept more audio.

**`create_application_idle_event()`**
fires when all neural networks and all processing stages are idle, meaning no further output will be
written to the output buffer until new input arrives. This is the signal to use after flushing, to
know that the model has finished. Note that the output buffer may still contain unread data when
this event fires; drain the buffer after receiving it.

### Event flags and state

Pass `abr_sdk.core.EventFlags` when creating an event to control its initial behavior:

| Flag                            | Effect                                                                                                                          |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `EventFlags(auto_disable=True)` | The event disables itself after firing. Call `abr_sdk.core.Event.enable` to arm it again before the next wait.                  |
| `EventFlags(disabled=True)`     | The event starts disabled and will not cause `abr_sdk.core.EventSet.poll` to return until you call `abr_sdk.core.Event.enable`. |

Call `abr_sdk.core.Event.enable` and `abr_sdk.core.Event.disable` at any time to
include or exclude an event from the next `abr_sdk.core.EventSet.poll`.
`abr_sdk.core.Event.is_triggered` reflects whether the event's condition currently holds,
independent of whether the event is enabled.

> **Next steps**
>
> - [Transcription stages](../asr/transcription-stages.md): how the model produces and revises text,
>   and how to handle chunk
>   overwrites.
> - [Overview](../tts/overview.md): TTS overview and the PCM output format.
