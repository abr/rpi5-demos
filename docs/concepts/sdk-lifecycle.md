# SDK lifecycle

Every ABR SDK object wraps a native handle. Releasing that handle correctly is the caller's
responsibility. This page explains how object lifetimes work, why the `with` block is the
recommended pattern, and what happens to child resources when a parent is closed.

## Application and its subclasses

`abr_sdk.core.Application` is the base class for all ABR runtime objects. When you use
ASR, you create an `abr_sdk.asr.Asr` instance; when you use TTS, you create a
`abr_sdk.tts.Tts` instance. Both inherit from `abr_sdk.core.Application`.

You rarely interact with `abr_sdk.core.Application` directly. Its lifecycle methods
(`abr_sdk.core.Application.close` and
`abr_sdk.core.Application.create_event_set`) are inherited by `abr_sdk.asr.Asr`
and `abr_sdk.tts.Tts` and behave the same way on any instance.

## The context manager pattern

The recommended way to use any ABR object is inside a `with` block:

```python title="recommended.py"
from abr_sdk.asr import Asr

with Asr("/path/to/libniagara_38m_live.so") as asr:
    # use asr here
    ...
# close() is called here, whether the block exits normally or raises
```

When the `with` block exits, Python calls `abr_sdk.core.Application.__exit__`, which calls
`abr_sdk.core.Application.close`. This happens on both normal exit and on exceptions. The
`with` block is the safest pattern because cleanup is guaranteed even if your code raises partway
through. The same applies to `abr_sdk.tts.Tts`; use a `with` block and
`abr_sdk.core.Application.close` is called automatically on exit.

## What `abr_sdk.core.Application.close` does

`abr_sdk.core.Application.close` releases the native handle and all child resources. The
sequence is the same for `abr_sdk.asr.Asr` and `abr_sdk.tts.Tts`:

1. Any in-progress session is closed.
2. All `abr_sdk.core.EventSet` objects owned by the application are closed, which closes
   their associated `abr_sdk.core.Event` objects.
3. The native application handle is freed.

After `abr_sdk.core.Application.close` returns, calling any method on the object raises
`abr_sdk.exceptions.AbrSdkError`, a subclass of the built-in `RuntimeError`. Calling
`abr_sdk.core.Application.close` a second time has no effect.

## Explicit `abr_sdk.core.Application.close`

When a context manager is not practical, for example when an `abr_sdk.asr.Asr` or
`abr_sdk.tts.Tts` instance is owned by a longer-lived class, call
`abr_sdk.core.Application.close` explicitly:

```python title="explicit_close.py"
from abr_sdk.asr import Asr

class Transcriber:
    def __init__(self, library_path: str) -> None:
        self._asr = Asr(library_path)

    def transcribe(self, audio: bytes) -> str:
        return self._asr.process(audio).text

    def shutdown(self) -> None:
        self._asr.close()
```

Call `abr_sdk.core.Application.close` before the object goes out of scope. If
`abr_sdk.core.Application.close` is never called, the native handle will not be freed
until the process exits. The same pattern applies to `abr_sdk.tts.Tts`.

> **Next steps**
>
> - [Streaming and chunks](../concepts/streaming-and-chunks.md): how `abr_sdk.core.EventSet`,
>   `abr_sdk.core.Event`, and `abr_sdk.core.Buffer` work together underneath the
>   high-level API.
> - `abr_sdk.asr.Asr`: full method reference for
>   `abr_sdk.core.Application.close`, `abr_sdk.asr.Asr.push`, and
>   `abr_sdk.asr.Asr.wait_for_completion`.
> - `abr_sdk.tts.Tts`: full method reference for `abr_sdk.core.Application.close`
>   and TTS synthesis methods.
