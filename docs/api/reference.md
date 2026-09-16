# Python API reference

The public `abr_sdk` surface, generated from the package source. For
task-oriented walkthroughs start with the
[ASR overview](../asr/overview.md) or the
[TTS overview](../tts/overview.md) instead.

## `abr_sdk.asr`

Automatic speech recognition (ASR) wrapper and chunk parser.

### `AsrMode` (extends `enum.Enum`)

Decoder mode selecting the latency / accuracy trade-off.

#### Members

- `AsrMode.FAST` = `'fast'`
- `AsrMode.ACCURATE` = `'accurate'`

### `Asr` (extends `Application`)

An ABR instance with automatic speech recognition support.

Can be constructed from a library path with keyword arguments:

```python
with Asr("libabr-asr.so") as asr:
```

**Simple (blocking) API** -- process an entire audio clip at once:

```python
transcript = asr.process(pcm_bytes)
print(transcript.text)
```

**Streaming API** -- push audio incrementally:

```python
transcript = AsrTranscript()
asr.push(chunk1, on_chunk=transcript.chunks.append)
asr.push(chunk2, on_chunk=transcript.chunks.append)
asr.wait_for_completion()
print(transcript.text)
```

For finer control over the streaming event loop, use `Processor`
directly.

#### `__init__`

```python
__init__(
    self,
    lib_or_path: str | Path | Library,
    *,
    mode: AsrMode | None=None,
    enable_spellcheck: bool | None=None,
    enable_punctuation: bool | None=None,
    lib_search_paths: list[str | Path] | None=None,
    use_default_lib_search_paths: bool=True,
    resources_dir: str | Path | None=None,
    litert_delegate: str | None=None,
    logger: logging.Logger | None=None,
) -> None
```

#### `flush`

```python
flush(self) -> None
```

Flush the ASR pipeline to finish processing remaining audio.

#### `process`

```python
process(self, data: bytes) -> AsrTranscript
```

Process PCM audio data and return the complete transcript.

This is a synchronous/blocking call that pushes all _data_ through
the ASR pipeline, waits for the neural network to finish, and
returns a `AsrTranscript` containing the result. Cannot be
used while a streaming session started with `push` is in
progress.

##### Parameters

- `data`: PCM audio as a little-endian 16-bit byte array.

#### `push`

```python
push(
    self,
    data: bytes,
    *,
    on_chunk: Callable[[AsrChunk], None] | None=None,
    output_poll_timeout_ms: int=0,
) -> None
```

Push PCM audio data into the ASR network (streaming API).

On the first call an internal `Processor` is created with
_on_chunk_ as the listener callback. Subsequent calls reuse the
same processor (the _on_chunk_ argument is ignored after the first
call). Call `wait_for_completion` after the last audio
chunk has been pushed.

##### Parameters

- `data`: PCM audio as little-endian 16-bit bytes.
- `on_chunk`: Callback invoked for each transcribed text chunk. Only used on the first call (when
  the internal processor is created).
- `output_poll_timeout_ms`: Extra time in milliseconds to spend waiting for output after the input
  has been pushed. `0` (the default) returns as soon as all input bytes have been consumed.

#### `wait_for_completion`

```python
wait_for_completion(self) -> None
```

Block until all previously pushed data is fully processed.

The `on_chunk` callback may be invoked during this call. When
this method returns, the internal processor is closed and a new
streaming session can be started by calling `push` again.

#### `close`

```python
close(self) -> None
```

Release all resources held by this instance.

### `AsrChunk`

A text chunk produced by the ASR subsystem.

Parse from raw buffer output with `parse`. Apply to a running
transcript with `update`.

#### Members

- `AsrChunk.SIZE` = `ctypes.sizeof(cabi.AsrTextChunk)`

#### `parse`

```python
@staticmethod parse(raw: bytes | bytearray) -> AsrChunk
```

Parse _raw_ bytes from the ASR output buffer into an `AsrChunk`.

_raw_ must be exactly `SIZE` bytes.

#### `update`

```python
update(self, buf: bytearray) -> None
```

Apply this chunk to a running transcript `bytearray`.

### `AsrTranscript`

Collected ASR output chunks with text assembly.

#### `__init__`

```python
__init__(self) -> None
```

#### `text`

_Property._ Returns `str`.

Assemble and return the full transcript text from all chunks.

### `Processor`

Event loop for streaming PCM audio through an `Asr` application.

Feeds audio into the ASR pipeline and delivers transcribed text chunks.
Attach to an `Asr` instance and push audio data incrementally.
Output chunks are delivered via the _on_chunk_ callback:

```python
with Processor(asr, on_chunk=my_callback) as proc:
    proc.push(chunk1)
    proc.push(chunk2)
    proc.wait_for_completion()
```

This class is also used internally by `Asr.process`.

#### `__init__`

```python
__init__(self, asr: Asr, on_chunk: Callable[[AsrChunk], None] | None=None) -> None
```

#### `process_and_wait_for_output`

```python
process_and_wait_for_output(self, data: bytes | None, timeout_ms: int, flush: bool) -> None
```

Push input data and wait for output text chunks.

This is the core event loop. Higher-level methods `push` and
`wait_for_completion` delegate to this method.

##### Parameters

- `data`: PCM input bytes (little-endian 16-bit), or _None_ to push no new data.
- `timeout_ms`: Maximum time in milliseconds to spend waiting for output after all input has been
  pushed. `0` means return immediately once input is consumed. The timeout is measured from when
  this method is called.
- `flush`: If _True_, flush the ASR pipeline after all input is streamed and wait until the neural
  network becomes idle.

#### `push`

```python
push(self, data: bytes, output_poll_timeout_ms: int=0) -> None
```

Push PCM audio data into the ASR network.

This may block briefly if the input buffer is full. The
`on_chunk` callback may be invoked during this call.

##### Parameters

- `data`: PCM audio as little-endian 16-bit bytes.
- `output_poll_timeout_ms`: Extra time in milliseconds to spend waiting for output after the input
  has been consumed. `0` (the default) returns as soon as the input is pushed.

#### `wait_for_completion`

```python
wait_for_completion(self) -> None
```

Block until all previously pushed data is fully processed.

The `on_chunk` callback may be invoked during this call.

#### `close`

```python
close(self) -> None
```

Release all event resources held by this processor.

## `abr_sdk.tts`

API for running TTS (text-to-speech) applications.

### `Tts` (extends `Application`)

Synthesize speech audio from input text.

Push raw UTF-8 text bytes and receive synthesized mono PCM audio,
one signed 16-bit integer per sample in little-endian order at
16 kHz. The backend normalizes pushed text (numbers, dates, currency,
acronyms, and abbreviations become speakable words) one sentence at a
time, so raw text can be pushed as-is.

Streaming usage:

```python
chunks: list[bytes] = []
with Tts("libabr-tts.so") as tts:
    tts.push(b"Hello world.", on_pcm=chunks.append)
    tts.wait_for_completion()
pcm = b"".join(chunks)
```

#### `__init__`

```python
__init__(
    self,
    lib_or_path: str | Path | Library,
    *,
    lib_search_paths: list[str | Path] | None=None,
    use_default_lib_search_paths: bool=True,
    resources_dir: str | Path | None=None,
    litert_delegate: str | None=None,
    logger: logging.Logger | None=None,
) -> None
```

#### `push`

```python
push(
    self,
    data: bytes,
    *,
    on_pcm: Callable[[bytes], None] | None=None,
    output_poll_timeout_ms: int=0,
) -> None
```

Push UTF-8 text bytes into the TTS pipeline.

Advances the event loop until all input has been accepted by the
pipeline. PCM bytes produced while advancing are delivered to
`on_pcm`.

#### `wait_for_completion`

```python
wait_for_completion(self) -> None
```

Block until the TTS pipeline finishes synthesizing all queued text.

Marks the end of input so the pipeline flushes its networks, then
drives the event loop until the application reports idle (every NN
has consumed its input and produced nothing more).

#### `close`

```python
close(self) -> None
```

Close the TTS instance and release any active processor.

### `Processor`

Event loop driving a streaming TTS session.

#### `__init__`

```python
__init__(self, tts: Tts, on_pcm: Callable[[bytes], None] | None=None) -> None
```

#### `process_and_wait_for_output`

```python
process_and_wait_for_output(self, data: bytes | None, timeout_ms: int, drain_to_idle: bool) -> None
```

Push `data` into TTS and advance the event loop until input is drained.

When `drain_to_idle` is true, keeps polling past input
exhaustion until the application-idle event fires (all NNs
finished consuming and produced no further PCM).

#### `close`

```python
close(self) -> None
```

Release the underlying event set; safe to call multiple times.

## `abr_sdk.core`

Wrapper classes around the object hierarchy exposed by the ABR C ABI.

### `BufferDirection` (extends `enum.Enum`)

Enum describing how a buffer is used.

#### Members

- `BufferDirection.Input` = `enum.auto()`
- `BufferDirection.Output` = `enum.auto()`

### `EventFlags`

Flags that influence how `Event` instances behave.

#### `bitset`

_Property._ Returns `int`.

Return a bitset that encodes the flags stored in this class.

The result value may be directly fed into C ABI functions that take an
"event flags" parameter.

### `Library` (extends `Handle`)

Loaded shared library with access to metadata.

#### `get_default_lib_search_paths`

```python
@staticmethod get_default_lib_search_paths() -> list[Path]
```

Return default library search paths from the environment.

#### `find`

```python
@staticmethod find(
    lib_path: str | Path,
    *,
    lib_search_paths: typing.Iterable[str | Path] | None=None,
    use_default_lib_search_paths: bool=True,
) -> typing.Iterable[Path]
```

Resolve `lib_path` to a list of candidates.

See `__init__` for a detailed description of the parameters.

#### `path`

_Property._ Returns `Path`.

Location of the loaded library.

#### `abi_version`

_Property._ Returns `tuple[int, int]`.

ABI version as a `(major, minor)` tuple.

### `Buffer` (extends `Handle`)

FIFO buffer for I/O.

Write data into input buffers via `push`, read data from output buffers via
`pull`.

#### `dir`

_Property._ Returns `BufferDirection`.

Buffer input/output direction.

#### `size`

_Property._ Returns `int`.

Total buffer capacity in bytes.

#### `level`

_Property._ Returns `int`.

Current fill level in bytes.

#### `push`

```python
push(self, data: bytes | bytearray | memoryview) -> int
```

Push data into the buffer.

##### Parameters

- `data`: Data to push onto the buffer.
- `flush`: Instructs the application to flush the processing pipeline once all bytes in `data` have
  been processed. Note that the "flush" flag only takes effect if there is enough space for all data
  in "data" in the buffer.

##### Returns

- `int`: The number of bytes actually written. This may be less than `len(data)` if the buffer is
  full.

#### `pull`

```python
pull(self, max_n_bytes: int) -> bytes
```

Pull data from the buffer.

##### Parameters

- `max_n_bytes`: Maximum number of bytes to read from the buffer at once. Fewer bytes than this may
  be returned if the buffer is empty or a "flush" boundary is reached.

##### Returns

- `data`: Data pulled from the buffer.

#### `clear`

```python
clear(self) -> None
```

Discard all data in the buffer.

### `EventSet` (extends `Handle`)

A set of events that can be polled together.

Create events with `create_buffer_level_event` or
`create_nn_idle_event`, then call `poll` to wait.

#### `platform_handle`

_Property._ Returns `int`.

Platform-specific handle (e.g. a file descriptor on POSIX).

#### `poll`

```python
poll(self, timeout_ms: int) -> bool
```

Block until an event fires or _timeout_ms_ elapses.

A negative timeout waits forever; zero returns immediately.
Returns `True` if at least one event triggered.
Raises `InterruptedError` on signal interruption.

#### `interrupt`

```python
interrupt(self) -> None
```

Interrupts a blocking call to `poll`.

#### `create_buffer_level_event`

```python
create_buffer_level_event(
    self,
    buf: Buffer,
    threshold: int,
    flags: EventFlags | None=None,
) -> 'Event'
```

Register a buffer level event for the given buffer.

The I/O event is triggered if there are `threshold` bytes available for
reading from or writing to the buffer.

#### `create_application_idle_event`

```python
create_application_idle_event(self, flags: EventFlags | None=None) -> 'Event'
```

Create an application-level idle event.

This event is triggered whenever the following conditions are met:

- All neural networks in the application are idle.

- All pre- and post-processing processes are idle.

As with the neural network idle event, "idle" means that the
corresponding component cannot make any progress without more input
being fed into the pipeline. If a component could still emit data, but
is blocked by doing so because of full output buffers, then this event
is not triggered.

Note that there may still be data in the output buffers once this event
triggers; "idle" just means that no more data will be written to the
application output buffers as long as no new data is being fed in.

#### `close`

```python
close(self) -> None
```

Release this event set and all its events.

### `Event` (extends `Handle`)

An event that can be polled for a condition.

Created by `EventSet` factory methods.

#### `is_triggered`

_Property._ Returns `bool`.

`True` if this event's condition currently holds.

#### `enable`

```python
enable(self) -> None
```

Enable this event so it can cause `EventSet.poll` to return.

#### `disable`

```python
disable(self) -> None
```

Ignore this event in `EventSet.poll`.

#### `close`

```python
close(self) -> None
```

Release this event.

### `Application` (extends `Handle`)

A time-series application instance.

Can be constructed directly with keyword arguments (auto-discovers and
loads a suitable library).

#### `make_log_callback`

```python
@staticmethod make_log_callback(logger: logging.Logger | None) -> typing.Any
```

Return a log callback that may be called from C.

#### `make_config`

```python
@staticmethod make_config(config: VariantDict) -> tuple[typing.Any, int]
```

Convert a Python dictionary into a C-compatible config object.

#### `create_event_set`

```python
create_event_set(self) -> EventSet
```

Create a new `EventSet` for polling buffer/network events.

#### `reset`

```python
reset(self) -> None
```

Reset the application to its initial state.

#### `close`

```python
close(self) -> None
```

Release all resources held by this instance.

## `abr_sdk.exceptions`

Common exceptions classes used throughout the SDK.

### `AbrSdkError` (extends `RuntimeError`)

Base class for all exceptions thrown in the SDK.

### `AbrSdkUnexpectedState` (extends `AbrSdkError`)

Exception indicating that something has reached an unexpected state.

This may suggest that there is a bug in the SDK, and not in the code using
the SDK.
